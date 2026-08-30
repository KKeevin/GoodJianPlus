# 部署與本機操作

本文件只說明如何在本機跑、以及正式環境的**一般做法**。真實伺服器帳號、IP、SSH、資料庫密碼請放在本機的 `docs/operations.local.md`（已列入 `.gitignore`，不會進公開倉庫）。

## 本機

見根目錄 [README.md](../README.md)。憑證只放 `.env`，從 `.env.example` 複製後自行填入。

常用：

```bash
python manage.py migrate
python manage.py runserver
python manage.py createsuperuser
python manage.py check
```

若 `migrate` 出現 `KeyError: ('social_django', 'code')`，先跑一次（可重複執行）：

```bash
python manage.py repair_social_migrations
python manage.py migrate
```

## 正式環境（占位，請換成你自己的主機）

- Web：Gunicorn（`gunicorn_config.py`）+ Nginx 反向代理（`nginx_https.conf.example`）
- 設定：`DJANGO_ENV=production`、`DEBUG=False`，並在環境變數設定 `SECRET_KEY`、`ALLOWED_HOSTS`、`SITE_DOMAIN`、資料庫與金流／簡訊金鑰
- HTTPS：Let’s Encrypt；`DEBUG=False` 時 Django 會啟用導向 HTTPS 與 Secure Cookie
- 靜態檔：`python manage.py collectstatic`

請勿把正式機的 `.env`、SSH 私鑰、資料庫傾印提交到 Git。
