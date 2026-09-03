from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from plus.models import ShippingAddress


@login_required
def address_book_view(request):
    if request.method == 'POST':
        label = (request.POST.get('label') or '住家').strip()[:40]
        name = (request.POST.get('name') or '').strip()
        phone = (request.POST.get('phone') or '').strip()
        address = (request.POST.get('address') or '').strip()
        is_default = request.POST.get('is_default') == 'on'
        if not all([name, phone, address]):
            messages.error(request, '請填寫收件人、電話與地址')
            return redirect('address_book')
        ShippingAddress.objects.create(
            user=request.user,
            label=label or '住家',
            name=name,
            phone=phone,
            address=address,
            is_default=is_default or not request.user.shipping_addresses.exists(),
        )
        messages.success(request, '已新增常用地址')
        return redirect('address_book')

    addresses = request.user.shipping_addresses.all()
    return render(request, 'account/address_book.html', {
        'addresses': addresses,
        'user': request.user,
    })


@login_required
@require_http_methods(['POST'])
def address_set_default_view(request, address_id):
    addr = get_object_or_404(ShippingAddress, id=address_id, user=request.user)
    addr.is_default = True
    addr.save()
    messages.success(request, f'已將「{addr.label}」設為預設地址')
    return redirect('address_book')


@login_required
@require_http_methods(['POST'])
def address_delete_view(request, address_id):
    addr = get_object_or_404(ShippingAddress, id=address_id, user=request.user)
    addr.delete()
    messages.success(request, '已刪除地址')
    return redirect('address_book')


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
