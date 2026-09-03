RECENT_KEY = 'recently_viewed'
MAX_ITEMS = 8


def track_product(request, product_id):
    ids = request.session.get(RECENT_KEY, [])
    product_id = int(product_id)
    ids = [pk for pk in ids if pk != product_id]
    ids.insert(0, product_id)
    request.session[RECENT_KEY] = ids[:MAX_ITEMS]
    request.session.modified = True


def recent_product_ids(request, exclude_id=None):
    ids = list(request.session.get(RECENT_KEY, []))
    if exclude_id:
        ids = [pk for pk in ids if pk != int(exclude_id)]
    return ids


def recent_products(request, exclude_id=None, limit=8):
    from plus.models import Product

    ids = recent_product_ids(request, exclude_id)[:limit]
    if not ids:
        return []
    found = {
        p.id: p
        for p in Product.objects.filter(id__in=ids, status='published').select_related(
            'category', 'brand'
        ).prefetch_related('images')
    }
    return [found[pk] for pk in ids if pk in found]
