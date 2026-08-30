"""
Gunicorn 配置文件
用於生產環境部署
"""

import multiprocessing

# 綁定地址和端口
bind = "127.0.0.1:8000"

# Worker 數量依主機 CPU／記憶體調整
workers = 2

# Worker 類型
worker_class = "sync"

# 超時設置（減少超時時間以提高響應速度）
timeout = 60
keepalive = 2

# 請求限制
max_requests = 1000
max_requests_jitter = 50

# 日誌設置
accesslog = "logs/gunicorn_access.log"
errorlog = "logs/gunicorn_error.log"
loglevel = "info"

# 進程名稱
proc_name = "goodjian"

# 用戶和組（在 systemd 中設置，這裡註釋掉）
# user = "www-data"
# group = "www-data"

# PID 文件（在 systemd 中管理，這裡註釋掉）
# pidfile = "/var/run/gunicorn/goodjian.pid"

# 重啟設置
preload_app = True
reload = False

