import bleach
from django import template
from django.utils.safestring import mark_safe

register = template.Library()


@register.filter
def clean_article_html(value):
    """Allow editorial formatting while stripping scripts, handlers and unsafe URLs."""
    return mark_safe(bleach.clean(str(value or ''), tags=[
        'p', 'br', 'hr', 'div', 'span', 'h2', 'h3', 'h4', 'h5', 'h6',
        'strong', 'b', 'em', 'i', 'u', 's', 'blockquote', 'ul', 'ol', 'li',
        'a', 'img', 'figure', 'figcaption', 'table', 'thead', 'tbody', 'tr', 'th', 'td',
    ], attributes={'a': ['href', 'title'], 'img': ['src', 'alt', 'width', 'height'],
                   'th': ['colspan', 'rowspan'], 'td': ['colspan', 'rowspan']},
       protocols=['http', 'https'], strip=True))
