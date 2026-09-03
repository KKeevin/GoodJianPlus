# 部署與本機操作

本文件只說明如何在本機跑、以及正式環境的**一般做法**。真實伺服器帳號、IP、SSH、資料庫密碼請放在本機的 `docs/operations.local.md`（已列入 `.gitignore`，不會進公開倉庫）。

日常 **SSH 登入、git pull、重啟 Gunicorn** 逐步說明見 [deploy.md](deploy.md)。

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
- 設定：`DJANGO_ENV=production`、`DEBUG=False`，並在環境變數設定 `SECRET_KEY`、`ALLOWED_HOSTS`、`SITE_DOMAIN`、`CSRF_TRUSTED_ORIGINS`、資料庫與金流／簡訊金鑰
- HTTPS：Let’s Encrypt；`DEBUG=False` 時 Django 會啟用導向 HTTPS 與 Secure Cookie
- 金流、SMTP、OAuth、Sentry、OpenAI 申請位置與要貼的變數：[integrations.md](integrations.md)
- 前台購物、訪客購物車、BMI／飲食／運動紀錄：[storefront.md](storefront.md)
- 靜態檔：`python manage.py collectstatic`

請勿把正式機的 `.env`、SSH 私鑰、資料庫傾印提交到 Git。

## Oracle Cloud（Always Free）

目前東京區 **A1.Flex 常常沒容量**，先用暫時小機把站裝起來。之後有位子要換成這台：

- Shape：**VM.Standard.A1.Flex**（Always Free、Ampere ARM）
- 規格：**2 OCPU / 12 GB**（Always Free 上限是 4 OCPU / 24 GB，先開一半）
- Image：Canonical Ubuntu 24.04
- 區域：Japan East (Tokyo)；此區只有 **1 個 Availability Domain**，無法換 AD 搶位
- Always Free 只能開在註冊時的 Home Region，不能改去大阪

換機時：Compute → Create instance，選上述 shape。舊的 E2.1.Micro 確認新機 SSH 通、資料搬完再 Terminate。IP、VCN、SSH 檔名等寫在本機的 `docs/operations.local.md`。
