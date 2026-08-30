from django.shortcuts import resolve_url
from django.utils.http import url_has_allowed_host_and_scheme


def safe_redirect_url(request, next_url, fallback='home'):
    """只允許站內路徑或本站主機，避免開放式重導向。"""
    fallback_url = resolve_url(fallback)
    if not next_url:
        return fallback_url
    next_url = str(next_url).strip()
    if url_has_allowed_host_and_scheme(
        next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return next_url
    try:
        resolved = resolve_url(next_url)
    except Exception:
        return fallback_url
    if url_has_allowed_host_and_scheme(
        resolved,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return resolved
    return fallback_url
