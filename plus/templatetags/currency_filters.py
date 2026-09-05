from decimal import Decimal, InvalidOperation

from django import template

register = template.Library()


@register.filter

def money(value):
    """Format a monetary value as a whole NT dollar amount."""
    try:
        amount = Decimal(str(value or 0))
    except (InvalidOperation, TypeError, ValueError):
        amount = Decimal('0')
    return f'NT${amount:,.0f}'
