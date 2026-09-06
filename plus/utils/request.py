from ipaddress import ip_address, ip_network
from django.conf import settings


def get_client_ip(request):
    """Walk proxy hops from the server; never trust a client-supplied first hop."""
    networks = [ip_network(value) for value in getattr(settings, 'TRUSTED_PROXY_NETWORKS', [])]
    try:
        peer = ip_address(request.META.get('REMOTE_ADDR', ''))
        if any(peer in network for network in networks):
            for hop in reversed(request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')):
                if not hop.strip():
                    continue
                peer = ip_address(hop.strip())
                if not any(peer in network for network in networks):
                    break
        return str(peer)
    except ValueError:
        return request.META.get('REMOTE_ADDR', 'unknown')
