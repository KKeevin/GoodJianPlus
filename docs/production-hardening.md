# 商用安全與部署調整（2026-09-06）

## 已實作

- 修正全域圖片 pre-save 訊號存取尚未建立會員關聯的錯誤；只處理實體圖片欄位與 Summernote 附件。
- WebP 最長邊 2048px、UUID 名稱、EXIF 方向、索引色透明度、10MB／4000 萬像素限制。動畫取第一幀。SVG、HEIC 等未安裝解碼器的格式不接受；2048px 是像素上限，不是 2KB 檔案大小保證。
- 編輯器上傳需後台身分與商品／文章編輯權限。文章 HTML 使用白名單過濾，移除 script、事件屬性、危險網址；舊內文仍保留於資料庫。部分自訂行內樣式會移除。
- 封面縮圖依封面 → 相關圖片 → 內文第一張圖片選取。
- 綠界回傳驗證簽章、MerchantID、訂單、金額、交易編號及模擬付款旗標。瀏覽器導回不修改付款狀態。正式收款依後端通知。
- 付款處理集中於 services/payments.py，交易編號在供應商內唯一；重複回傳不重複通知、不把已出貨／取消訂單改回已確認。
- 遲到付款或重複收款進「付款對帳紀錄」，保留既有訂單狀態。人工處理時填寫處理紀錄，Django admin 留存操作者變更紀錄。
- LINE Pay 送出的 JSON 位元組與簽章使用同一格式；確認逾時不視為失敗，不直接釋放庫存。需要實際平台對帳才能判定結果。
- LINE Pay 建立付款採原子標記，阻止重複點擊建立多筆交易；未決請求不自動重試。已在平台確認付款但通知遺失時，可使用下方人工對帳命令。
- 優惠券預留旗標確保一次返還；庫存改成帶數量條件的原子更新。SQLite 使用 IMMEDIATE 交易及 20 秒忙碌等待，仍只有單一寫入者。
- 退款需已付款訂單、合理退貨狀態及退款憑證；只有已收回且驗收可販售的商品才退庫。**標記退款不會呼叫金流退款 API**，必須先在金流平台完成實際退款。
- 登入限流計數使用資料庫，各 worker 共用；只信任設定的代理網段，由右向左取可信來源。
- 後台驗證器 TOTP、第一次綁定需密碼＋有效代碼、代碼不可重用，提供 SSH 遺失恢復指令。
- 商品編輯、專欄編輯、出貨人員、財務對帳四個群組，線上金流付款狀態不提供直接編輯。
- SQLite + media 備份、SHA256 驗證、暫存還原完整性檢查、健康檢查、CI 測試與依賴漏洞檢查。
- 修正手機 footer 規則被後續 CSS 覆蓋的順序；付款 view 移除複製遺留的未使用引用。

## 正式機部署

以下以現有 `/home/ubuntu/GoodJianPlus`、`goodjian.service` 為準。此次尚未連入正式機或修改正式資料。

1. 上傳完整變更（含 requirements.txt、兩個 plus migration、新增模組、模板、CI 與文件），不要只單獨上傳 apps.py。
2. 在維護時段停止流量／worker，避免舊程式與 migration 同時寫入。維護期間金流回呼可能重送；啟動後至供應商檢查未處理交易。
3. 安裝套件、先備份再遷移：

```bash
cd ~/GoodJianPlus
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
sudo systemctl stop goodjian.service
python manage.py backup_site --output "$HOME/goodjian-backups/pre-hardening-$(date +%Y%m%d-%H%M%S).zip"
python manage.py migrate
python manage.py setup_staff_roles
python manage.py check --deploy
python manage.py collectstatic --noinput
sudo systemctl start goodjian.service
sudo systemctl status goodjian.service --no-pager
```

如果中間任一步失敗，不要繼續後續步驟。確認資料庫與版本後再啟動服務。

正式 `.env` 應明確設定：

```dotenv
DJANGO_ENV=production
DEBUG=False
ADMIN_REQUIRE_OTP=True
DB_ENGINE=sqlite
TRUSTED_PROXY_NETWORKS=127.0.0.1/32,::1/128
```

保留既有 SECRET_KEY、實際域名 ALLOWED_HOSTS、CSRF 信任來源、金流及郵件設定。啟用 production 卻仍 DEBUG=True 會拒絕啟動。不要把完整 .env 或驗證器密鑰貼到公開處。

第一次進後台會要求綁定驗證器，帳戶必須具有可使用的本機密碼。若是只有第三方登入的後台帳戶，先透過可信 SSH `python manage.py changepassword 帳號` 設定密碼。遺失驗證器時，確認管理者身分後使用：

```bash
python manage.py reset_staff_mfa 帳號 --confirm
```

這會清除該帳戶所有 TOTP 裝置，下次登入必須重新綁定。平常不要使用這個指令。

Nginx 的 X-Forwarded-For 範本改為 `$remote_addr`。如果前方另有 CDN／負載平衡器，先設定 Nginx real_ip 的可信範圍；不要直接信任所有來源。修改 Nginx 後先 `sudo nginx -t` 再 reload。

## 日常維護

```bash
python manage.py backup_site --output "$HOME/goodjian-backups/site-$(date +%Y%m%d-%H%M%S).zip"
python manage.py verify_site_backup /完整路徑/備份.zip
python manage.py cleanup_request_limits
```

僅在可信 SSH 主機、已於金流平台確認「實際成功付款」時，才能執行人工補記；請替換所有範例值：

```bash
python manage.py reconcile_payment GJ實際訂單編號 --provider linepay --transaction 實際交易編號 --amount 實際金額 --reference 對帳憑證 --confirmed
```

訂單若已取消／釋放庫存，仍只列入人工處理，不會直接復活訂單。此指令不會查詢金流或扣款；不可把失敗／未確定交易當作成功輸入。

備份需另存異機並設定保存期、磁碟用量告警；本工具不自動刪除舊備份。SQLite 快照可在線上建立，media 檔案與 DB 不具跨系統原子快照；需要嚴格一致的還原點時應在維護模式禁止上傳／寫入。備份內有個資及 OTP 裝置密鑰，須限制存取。`.env` 不打包，另存安全密鑰管理位置。

還原演練：先 verify，再於獨立測試專案／目錄解壓，指向還原的 database.sqlite3 與 media，確認登入、文章圖片及訂單可查詢；不要直接覆蓋正在運作的 SQLite 或混用 WAL 檔。正式回復必須先停止應用並使用相符版本。備份驗證會暫時還原 SQLite 並執行 integrity_check，但不等同完整業務演練。

`/health/` 檢查應用及資料庫可用性（200/503），可交給現有監控平台；它不驗證金流／SMTP／磁碟容量。設定既有 SENTRY_DSN 可收集例外與付款待對帳錯誤，告警接收人需在實際監控平台設定。建議每日檢查待人工對帳紀錄與失敗／未決付款。

## 資料庫與驗收邊界

- migration 0028 只為既有「庫存仍預留、非取消／退款、有優惠券」訂單補上預留標記；歷史已失敗訂單的優惠券計數不猜測修復，需人工對帳。
- SQLite 在小流量時可繼續使用；IMMEDIATE 改善交易一致性，不提供高併發寫入。高流量／多台應用前先在 staging 搬至 MySQL/PostgreSQL、驗證數量／總金額／關聯與併發結帳，再安排切換；此次未搬移資料庫。
- 上線前仍需使用商戶自己的 sandbox 完成付款、重複通知、取消後付款、退款與物流實際驗收；自動測試不會扣真錢或呼叫商戶 API。
- 自動退款 API、完整銀行對帳匯入、CDN 圖片遷移及所有頁面視覺回歸屬於後續整合；目前退款採有憑證的人工流程。

參考：[綠界付款通知](https://developers.ecpay.com.tw/2878/)、[綠界全方位金流](https://developers.ecpay.com.tw/2864/)、[Django SQLite 限制](https://docs.djangoproject.com/en/5.2/ref/databases/#sqlite-notes)。


## 可選的每日備份排程

`scripts/systemd/goodjian-backup.service` / `.timer` 是正式機範本，預設每天主機時區 03:30 執行（加最多五分鐘延遲）。確認路徑、容量與異機保存方式後才啟用：

```bash
mkdir -p ~/goodjian-backups
chmod 700 ~/goodjian-backups
sudo cp scripts/systemd/goodjian-backup.service scripts/systemd/goodjian-backup.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl start goodjian-backup.service
sudo systemctl status goodjian-backup.service --no-pager
sudo systemctl enable --now goodjian-backup.timer
systemctl list-timers goodjian-backup.timer
```

成功的 oneshot 服務可能顯示 inactive (dead)，重點是上一回執行 `status=0/SUCCESS`。失敗時查看 `journalctl -u goodjian-backup.service`。此排程尚未在正式機安裝。


## 本次驗證結果

- Django 完整測試 78 項通過（包含會員新增、圖片轉檔、付款重送／跨訂單隔離、庫存／優惠券、MFA、HTML 過濾及備份驗證）。
- `makemigrations --check --dry-run` 無遺漏遷移；`pip check` 無衝突；本機依賴 `pip-audit` 未發現已知漏洞（此結果不代表所有程式碼皆無漏洞）。
- 本機已建立 `backups/pre-hardening-20260906.zip`，驗證 70 個檔案，並套用 OTP／0028／0029 遷移及四個職務群組。
- 使用本機環境模擬 production 設定時，`check --deploy` 仍提醒 SQLite 及本機 SECRET_KEY 強度。正式機必須另跑檢查；若有 W009，應在維護時段產生足夠長的隨機 SECRET_KEY，保存在正式 .env。金鑰更換會影響既有登入／簽章，須依部署規劃執行。
- 沒有連入正式機、沒有執行真實扣款／退款，也尚未安裝正式備份 timer。高併發壓測及完整頁面視覺回歸仍需 staging 驗收。
