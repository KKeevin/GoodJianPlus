# 申請金鑰後即可啟用的串接

程式已經接好。你只要到各平台申請、把金鑰貼進專案根目錄的 `.env`（可從 `.env.example` 複製），重啟 Gunicorn 或 `runserver`，該功能就會開始運作。

**不要把填好的 `.env` 提交到 Git。**

正式機除了本機 `.env`，也要在伺服器 `/home/ubuntu/GoodJianPlus/.env` 貼同一組（或正式環境專用）金鑰。

---

## 1. 網站網址與 CSRF（正式站必做）

`.env`：

```
DEBUG=False
ALLOWED_HOSTS=goodjian.shop,www.goodjian.shop
SITE_DOMAIN=goodjian.shop
CSRF_TRUSTED_ORIGINS=https://goodjian.shop,https://www.goodjian.shop
```

`CSRF_TRUSTED_ORIGINS` 留空時，程式會用 `SITE_DOMAIN` 與 `ALLOWED_HOSTS` 自動產生。正式機建議**明確寫上**，再開 `DEBUG=False`。

---

## 2. 電子郵件（訂單確認、狀態更新、重設密碼、客服留言）

建議用 Gmail **應用程式密碼**（不是一般登入密碼）。

1. 用寄信帳號登入 Google 帳戶  
2. 開啟[兩步驟驗證](https://myaccount.google.com/signinoptions/two-step-verification)  
3. 到[應用程式密碼](https://myaccount.google.com/apppasswords) 產生一組 16 碼  
4. 貼到 `.env`：

```
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=你的Gmail@gmail.com
EMAIL_HOST_PASSWORD=十六碼應用程式密碼
DEFAULT_FROM_EMAIL=好健健 GoodJian Plus <你的Gmail@gmail.com>
```

下單後會寄「訂單確認」；後台改訂單狀態會寄「狀態更新」（含物流單號）。客服頁留言會寄到後台「網站設定」的聯絡信箱。

其他 SMTP（例如 SendGrid、Cloudflare Email Routing）只要改 `EMAIL_HOST` / 帳密即可，不必改程式。

---

## 3. LINE Pay

1. 到 [LINE Pay 商家中心](https://pay.line.me/) 申請商家  
2. 開發文件：[LINE Pay Developers](https://pay.line.me/documents/online_v3_zh_tw.html)  
3. 取得 Channel ID、Channel Secret（先用 sandbox 測試）  
4. 回調網址（正式網域）：
   - Confirm：`https://你的網域/payment/<訂單id>/linepay/confirm/`
   - Cancel：`https://你的網域/payment/<訂單id>/linepay/cancel/`

```
LINE_PAY_CHANNEL_ID=
LINE_PAY_CHANNEL_SECRET=
LINE_PAY_SANDBOX=True
```

上線改 `LINE_PAY_SANDBOX=False`。結帳可選 LINE Pay，付款頁會導向 LINE。

---

## 4. 綠界科技 ECPay（信用卡／ATM／超商代碼）

1. 到 [綠界官網](https://www.ecpay.com.tw/) 申請特約商店  
2. 廠商後台 → 系統開發管理 → 取得 **MerchantID、HashKey、HashIV**  
3. 開發文件：[ECPay Developers](https://developers.ecpay.com.tw/)  
4. 測試可先用綠界 stage 金鑰，並維持 `ECPAY_SANDBOX=True`  
5. 在綠界後台登記：
   - ReturnURL（背景通知，必填）：`https://你的網域/payment/ecpay/return/`
   - OrderResultURL（瀏覽器導回）：`https://你的網域/payment/<訂單id>/ecpay/result/`（程式會依訂單自動帶）

```
ECPAY_MERCHANT_ID=
ECPAY_HASH_KEY=
ECPAY_HASH_IV=
ECPAY_SANDBOX=True
```

上線改 `ECPAY_SANDBOX=False`。程式會自動組 CheckMacValue 並送出 AIO 表單。沒填金鑰時前台仍看得到選項，按下會提示尚未設定。

電子發票若要用綠界發票 API，需另申請發票模組；目前結帳已蒐集抬頭、統編、載具，可先匯出後到財政部／加值中心開立。

---

## 5. 社群登入（Google／Facebook／LINE Login）

回調路徑已存在，只要在各平台填「已授權重新導向 URI」。

| 平台 | 申請 | `.env` | 回調 URI |
| --- | --- | --- | --- |
| Google | [Google Cloud Console](https://console.cloud.google.com/apis/credentials) OAuth 用戶端 | `GOOGLE_OAUTH2_CLIENT_ID` `GOOGLE_OAUTH2_CLIENT_SECRET` | `https://你的網域/auth/complete/google-oauth2/` |
| Facebook | [Meta 開發人員](https://developers.facebook.com/) 應用程式 | `FACEBOOK_APP_ID` `FACEBOOK_APP_SECRET` | `https://你的網域/auth/complete/facebook/` |
| LINE Login | [LINE Developers](https://developers.line.biz/) Login channel | `LINE_CHANNEL_ID` `LINE_CHANNEL_SECRET` | `https://你的網域/auth/complete/line/` |

本機測試把網域改成 `http://localhost:8000`。

---

## 6. 簡訊／手機登入

`.env` 已接 ClickSend。申請：[ClickSend](https://www.clicksend.com/)

```
SMS_TEST_MODE=True
SMS_PROVIDER=clicksend
CLICKSEND_USERNAME=
CLICKSEND_API_KEY=
CLICKSEND_FROM_NUMBER=
```

先維持 `SMS_TEST_MODE=True`（驗證碼寫進 log、不真的寄簡訊）。要真寄時改 `False` 並填帳密。

---

## 7. 錯誤監控 Sentry

1. [sentry.io](https://sentry.io/) 免費專案 → Django DSN  
2. `.env`：`SENTRY_DSN=https://...@....ingest.sentry.io/...`  
3. `requirements.txt` 已含 `sentry-sdk`，有 DSN 才會啟用。

---

## 8. OpenAI 商品文案

1. [OpenAI API keys](https://platform.openai.com/api-keys) 建立金鑰（需付費額度）  
2. `.env`：

```
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
```

後台 → 商品 → 勾選商品 → 動作「以 AI 產生商品短介紹」。沒金鑰時會提示去申請。

其他相容 API（例如 Groq、自架 OpenAI 相容端點）若要接，可之後只改 `plus/services/ai_copy.py` 的網址。

---

## 9. 物流與出貨進度（不必先申請 API）

後台訂單填 **物流商 + 物流單號**（可再填查詢網址），狀態改成「已出貨」：

- 自動記下出貨時間  
- 會員訂單頁顯示進度與「查詢貨態」  
- 寄出狀態信（含單號）

目前連到各物流**公開查詢頁**（新竹、黑貓、嘉里、7-11、全家）。若要系統自動抓貨態，需另與物流商簽 B2B API，再把回傳寫進 `plus/services/shipping.py`。

---

## 10. 電子報

前台訂閱會寫入後台「電子報訂閱」。之後可匯出 CSV 貼到 [Mailchimp](https://mailchimp.com/) 或 [Brevo](https://www.brevo.com/)，不必改結帳流程。

---

## 套用後請做

```bash
python manage.py migrate
python manage.py check
```

正式機：更新 `.env` → `sudo systemctl restart goodjian`（服務名稱以你機上為準）。

逐步 SSH／部署見 [deploy.md](deploy.md)。
