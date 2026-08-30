from django import template

register = template.Library()

@register.filter
def mul(value, arg):
    """乘法過濾器"""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0

@register.filter
def div(value, arg):
    """除法過濾器"""
    try:
        arg = float(arg)
        if arg == 0:
            return 0
        return float(value) / arg
    except (ValueError, TypeError):
        return 0

@register.filter
def sub(value, arg):
    """減法過濾器"""
    try:
        return float(value) - float(arg)
    except (ValueError, TypeError):
        return 0

