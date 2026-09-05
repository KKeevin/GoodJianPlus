from django import template

register = template.Library()


@register.simple_tag(takes_context=True)
def query_update(context, **changes):
    """Preserve and safely encode filters when paginating or removing a chip."""
    query = context['request'].GET.copy()
    for key, value in changes.items():
        if value is None or value == '':
            query.pop(key, None)
        else:
            query[key] = value
    return '?' + query.urlencode()
