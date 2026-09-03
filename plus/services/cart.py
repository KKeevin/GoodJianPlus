from plus.models import Cart, CartItem


def ensure_session(request):
    if not request.session.session_key:
        request.session.create()
    return request.session.session_key


def get_or_create_cart(request):
    if request.user.is_authenticated:
        cart, _ = Cart.objects.get_or_create(user=request.user)
        return cart
    session_key = ensure_session(request)
    cart = Cart.objects.filter(user__isnull=True, session_key=session_key).first()
    if cart:
        return cart
    return Cart.objects.create(user=None, session_key=session_key)


def merge_session_cart(request, user, session_key=None):
    session_key = session_key or request.session.session_key
    if not session_key:
        return
    guest = Cart.objects.filter(user__isnull=True, session_key=session_key).first()
    if not guest:
        return
    user_cart, _ = Cart.objects.get_or_create(user=user)
    for item in guest.items.select_related('product'):
        existing = user_cart.items.filter(product=item.product).first()
        if existing:
            existing.quantity += item.quantity
            existing.save(update_fields=['quantity'])
        else:
            CartItem.objects.create(cart=user_cart, product=item.product, quantity=item.quantity)
    guest.delete()
