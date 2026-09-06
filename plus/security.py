"""Staff MFA gate and shared-process login throttling."""
from base64 import b32encode
from django import forms
from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.cache import never_cache
from django_otp import login as otp_login
from django_otp.plugins.otp_totp.models import TOTPDevice
from plus.utils.ratelimit import consume_limit
from plus.utils.request import get_client_ip


@never_cache
def health_check(request):
    from django.db import connection
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
            cursor.fetchone()
    except Exception:
        return HttpResponse('unavailable', status=503, content_type='text/plain')
    return HttpResponse('ok', content_type='text/plain')


class AdminSecurityMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def process_exception(self, request, exception):
        from plus.image_processing import ImageUploadError
        if isinstance(exception, ImageUploadError):
            return HttpResponse(str(exception), status=400, content_type='text/plain; charset=utf-8')

    def __call__(self, request):
        protected = request.path.startswith(('/admin/', '/summernote/'))
        if request.method == 'POST' and request.path in ('/admin/login/', '/admin-mfa/'):
            identity = f'admin:{get_client_ip(request)}'
            if not consume_limit(identity, 8, 60):
                return HttpResponse('嘗試次數過多，請稍後再試。', status=429)
        if (protected and settings.ADMIN_REQUIRE_OTP and request.user.is_authenticated
                and request.user.is_staff and not request.user.is_verified()
                and request.path != '/admin/logout/'):
            return redirect('admin_mfa')
        return self.get_response(request)


class MFAForm(forms.Form):
    password = forms.CharField(label='目前密碼', widget=forms.PasswordInput(attrs={'autocomplete': 'current-password'}))
    token = forms.RegexField(r'^\d{6}$', label='驗證器六位數代碼', widget=forms.TextInput(attrs={
        'inputmode': 'numeric', 'autocomplete': 'one-time-code', 'maxlength': '6'}))


@never_cache
@staff_member_required
def admin_mfa(request):
    if request.user.is_verified():
        return redirect('admin:index')
    form = MFAForm(request.POST or None)
    with transaction.atomic():
        # Serialize enrollment per account, including competing sessions.
        from django.contrib.auth import get_user_model
        get_user_model().objects.select_for_update().get(pk=request.user.pk)
        device = TOTPDevice.objects.filter(user=request.user, confirmed=True).first()
        if device is None:
            device, _ = TOTPDevice.objects.get_or_create(user=request.user, name='admin', confirmed=False)
        device = TOTPDevice.objects.select_for_update().get(pk=device.pk)
        if request.method == 'POST' and form.is_valid():
            if request.user.check_password(form.cleaned_data['password']) and device.verify_token(form.cleaned_data['token']):
                device.confirmed = True
                device.save(update_fields=['confirmed'])
                otp_login(request, device)
                request.session.cycle_key()
                return redirect('admin:index')
            form.add_error(None, '密碼或驗證碼不正確，請稍後重試。')
        secret = b32encode(device.bin_key).decode().rstrip('=') if not device.confirmed else ''
    response = render(request, 'admin/mfa.html', {'form': form, 'secret': secret})
    response['Referrer-Policy'] = 'no-referrer'
    return response
