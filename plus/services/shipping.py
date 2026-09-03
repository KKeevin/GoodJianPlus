"""物流單號查詢網址。實際 API 需與物流商簽約後才能查貨態，這裡先給公開查詢頁。"""

CARRIER_TRACKING_TEMPLATES = {
    'hct': 'https://www.hct.com.tw/Search/SearchGoods?no={no}',
    'tcat': 'https://www.t-cat.com.tw/inquire/trace.aspx?no={no}',
    'kerry': 'https://www.kerrytj.com/zh/search/search_track.aspx?TrackNo={no}',
    'seven_eleven': 'https://eservice.7-11.com.tw/e-tracking/search.aspx?eslno={no}',
    'family_mart': 'https://fmec.famiport.com.tw/ccor03/index.php?barcode={no}',
}


def resolve_tracking_url(order):
    """優先使用後台手動填的網址，否則依物流商組公開查詢連結。"""
    if getattr(order, 'tracking_url', ''):
        return order.tracking_url
    tracking_number = (getattr(order, 'tracking_number', '') or '').strip()
    carrier = getattr(order, 'carrier', '') or ''
    template = CARRIER_TRACKING_TEMPLATES.get(carrier)
    if tracking_number and template:
        return template.format(no=tracking_number)
    return ''
