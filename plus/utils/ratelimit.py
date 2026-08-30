from functools import wraps

from django.contrib import messages
from django.core.cache import cache
from django.http import JsonResponse
from django.shortcuts import redirect

from plus.utils.request import get_client_ip


def ratelimit(limit=10, window=60, methods=('POST',)):
    """以 IP 為鍵的簡易限流（使用 Django cache）。"""

    def decorator(view_func):
        @wraps(view_func)
        def wrapped(request, *args, **kwargs):
            if request.method not in methods:
                return view_func(request, *args, **kwargs)
            ident = get_client_ip(request) or 'unknown'
            cache_key = f'rl:{view_func.__module__}.{view_func.__name__}:{ident}'
            count = cache.get(cache_key, 0)
            if count >= limit:
                wants_json = (
                    request.headers.get('x-requested-with') == 'XMLHttpRequest'
                    or 'application/json' in request.headers.get('Accept', '')
                )
                if wants_json:
                    return JsonResponse({
                        'success': False,
                        'message': '嘗試次數過多，請稍後再試',
                    }, status=429)
                messages.error(request, '嘗試次數過多，請稍後再試')
                return redirect(request.path)
            cache.set(cache_key, count + 1, window)
            return view_func(request, *args, **kwargs)
        return wrapped
    return decorator
