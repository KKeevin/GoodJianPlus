# 手機登入與 SMS

登入頁支援帳號密碼與手機驗證碼。簡訊由 `plus/services/sms.py` 依 `SMS_PROVIDER` 發送。

## 環境變數

見 `.env.example`：

- `SMS_TEST_MODE=True`：只寫 log，不真的發簡訊（地端建議維持 True）
- `SMS_PROVIDER`：`clicksend`、`twilio`、`aws_sns`、`mitake`
- ClickSend：`CLICKSEND_USERNAME`、`CLICKSEND_API_KEY`、可選 `CLICKSEND_FROM_NUMBER`

檢查設定：

```bash
python manage.py check_sms_config
```

請勿把 API 金鑰寫進文件或版控。憑證只放在本機 `.env`。
