from .base import *

# 生產環境仍依 DEBUG 決定 HTTPS（與原本 settings.py 行為相同）。
# 部署時請設置 DJANGO_ENV=production 且 DEBUG=False。
