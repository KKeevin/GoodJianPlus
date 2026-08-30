# 郵件設定

在 `.env` 填入 SMTP 設定（見 `.env.example`）：

- `EMAIL_HOST` / `EMAIL_PORT` / `EMAIL_USE_TLS`
- `EMAIL_HOST_USER` / `EMAIL_HOST_PASSWORD`（Gmail 請用應用程式密碼）
- `DEFAULT_FROM_EMAIL`

測試：

```bash
python manage.py test_email
```

正式機可用 `scripts/test_email_production.sh`，或在該環境執行同一個 management command。

相關範本位於 `plus/templates/emails/`。
