from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_http_methods
from django.urls import reverse
from django.db import transaction

from plus.models import ShippingAddress
from plus.forms_account import ShippingAddressForm


def account_addresses_redirect():
    return redirect(reverse('profile') + '?tab=addresses')


@login_required
def address_book_view(request):
    from plus.views.profile import user_profile_view
    editing_address = None
    address_id = request.POST.get('address_id') if request.method == 'POST' else request.GET.get('edit')
    if address_id:
        if not address_id.isdecimal():
            from django.http import Http404
            raise Http404
        editing_address = get_object_or_404(ShippingAddress, id=address_id, user=request.user)
    if request.method == 'POST':
        form = ShippingAddressForm(request.POST, instance=editing_address,
                                   prefix='shipping' if 'shipping-name' in request.POST else None)
        if form.is_valid():
            with transaction.atomic():
                addr = form.save(commit=False)
                addr.user = request.user
                if not request.user.shipping_addresses.exclude(pk=addr.pk).filter(is_default=True).exists():
                    addr.is_default = True
                addr.save()
            messages.success(request, '已更新常用地址' if editing_address else '已新增常用地址')
            return account_addresses_redirect()
        return user_profile_view(request, address_form=form, editing_address=editing_address, active_tab='addresses')
    if editing_address:
        return user_profile_view(request, address_form=ShippingAddressForm(instance=editing_address, prefix='shipping'),
                                 editing_address=editing_address, active_tab='addresses')
    return account_addresses_redirect()


@login_required
@require_http_methods(['POST'])
def address_set_default_view(request, address_id):
    addr = get_object_or_404(ShippingAddress, id=address_id, user=request.user)
    with transaction.atomic():
        addr.is_default = True
        addr.save()
    messages.success(request, f'已將「{addr.label}」設為預設地址')
    return account_addresses_redirect()


@login_required
@require_http_methods(['POST'])
def address_delete_view(request, address_id):
    addr = get_object_or_404(ShippingAddress, id=address_id, user=request.user)
    with transaction.atomic():
        addr.delete()
        if not request.user.shipping_addresses.filter(is_default=True).exists():
            replacement = request.user.shipping_addresses.first()
            if replacement:
                replacement.is_default = True
                replacement.save()
    messages.success(request, '已刪除地址')
    return account_addresses_redirect()


@login_required
def address_json_api(request):
    data = [
        {
            'id': a.id,
            'label': a.label,
            'name': a.name,
            'phone': a.phone,
            'address': a.address,
            'is_default': a.is_default,
        }
        for a in request.user.shipping_addresses.all()
    ]
    return JsonResponse({'success': True, 'addresses': data})
