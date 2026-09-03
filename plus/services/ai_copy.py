"""商品文案：設定 OPENAI_API_KEY 後即可從後台產生短介紹。"""
import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

OPENAI_URL = 'https://api.openai.com/v1/chat/completions'


def generate_product_copy(product):
    """
    依商品名稱與分類產生繁中短介紹。
    回傳 (text, error_message)。未設定金鑰時 error_message 會說明申請位置。
    """
    api_key = getattr(settings, 'OPENAI_API_KEY', '') or ''
    if not api_key:
        return '', '尚未設定 OPENAI_API_KEY，請見 docs/integrations.md'

    model = getattr(settings, 'OPENAI_MODEL', 'gpt-4o-mini') or 'gpt-4o-mini'
    category = ''
    if getattr(product, 'category_id', None) and product.category:
        category = product.category.name
    prompt = (
        f'請為台灣健身電商「好健健」撰寫商品介紹，80～150 字，繁體中文，'
        f'語氣專業可信，不要價格與誇大療效。\n'
        f'商品名稱：{product.name}\n'
        f'分類：{category or "未分類"}\n'
        f'現有簡述：{(product.short_description or "")[:200]}'
    )
    try:
        response = requests.post(
            OPENAI_URL,
            headers={
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json',
            },
            json={
                'model': model,
                'messages': [
                    {'role': 'system', 'content': '你是台灣電商文案編輯。'},
                    {'role': 'user', 'content': prompt},
                ],
                'temperature': 0.6,
                'max_tokens': 400,
            },
            timeout=30,
        )
        response.raise_for_status()
        text = response.json()['choices'][0]['message']['content'].strip()
        return text, ''
    except Exception as exc:
        logger.error('OpenAI product copy failed: %s', exc)
        return '', 'AI 文案產生失敗，請檢查金鑰與額度'
