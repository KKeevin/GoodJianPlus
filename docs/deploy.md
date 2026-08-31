# 正式機：SSH 與更新程式

本機帳號、公網 IP、SSH 私鑰路徑寫在 [operations.local.md](operations.local.md)（gitignore，不會進 Git）。下面指令裡的 `公網IP`、`私鑰.key` 請換成那份裡的值。

目前站在 Oracle 暫時機：Nginx + Gunicorn（`goodjian.service`）+ SQLite。網址 https://goodjian.shop 。

## 從 Windows 登入 SSH

開 **PowerShell**（不要用瀏覽器）。

```powershell
ssh -i "私鑰的完整路徑.key" ubuntu@公網IP
```

- 使用者固定是 **`ubuntu`**，不是 Oracle 帳號、也不是網站後台帳號。
- 第一次連會問 `Are you sure you want to continue connecting`，打 `yes`。
- 成功後提示變成 `ubuntu@goodjian:~$`。

私鑰權限太開時會出現 `UNPROTECTED PRIVATE KEY FILE`，在 **本機** PowerShell 跑（路徑改成你的 `.key`）：

```powershell
icacls "私鑰的完整路徑.key" /inheritance:r
icacls "私鑰的完整路徑.key" /grant:r "$env:USERNAME:(R)"
```

再重跑 `ssh`。

連進去後要操作專案，先進入目錄並啟用虛擬環境：

```bash
cd ~/GoodJianPlus
source .venv/bin/activate
```

提示應變成 `(.venv) ubuntu@goodjian:~/GoodJianPlus$`。

離開 SSH：打 `exit`。關掉視窗也可以，網站不會停（Gunicorn 由 systemd 管）。

## 更新程式（日常部署）

先在**本機**把要上線的變更 commit，並推到 GitHub `main`：

```powershell
git push origin main
```

再到伺服器 SSH，依序執行（一次一行也行）：

```bash
cd ~/GoodJianPlus
source .venv/bin/activate
git pull origin main
pip install -r requirements.txt
python manage.py repair_social_migrations
python manage.py migrate
python manage.py collectstatic --noinput
sudo systemctl restart goodjian
```

`repair_social_migrations` 可重複執行；新庫或不需要時會顯示「不需修復」，沒關係。

`requirements.txt` 沒改時，`pip install` 幾乎秒過，留著比較保險。

**不要**在正式機改程式再 commit。正式機的 `.env`、`db.sqlite3`、上傳的 `media/` 不在 Git 裡，`git pull` 不會覆蓋它們。

### 這次有改什麼，才需要多做

| 你改了 | 伺服器還要 |
|--------|------------|
| 只改 Python／模板／靜態檔 | 上面那套即可 |
| `requirements.txt` | 一定要 `pip install` |
| 新增 migration | 一定要 `migrate` |
| 靜態 CSS／JS／圖 | 一定要 `collectstatic` |
| 只改伺服器 `.env` | 只要 `sudo systemctl restart goodjian` |
| Nginx 設定 | `sudo nginx -t` 再 `sudo systemctl reload nginx` |

不要在正式機重跑 `seed_catalog`（會再灌示範商品）。不要把本機 `.env` 整份覆蓋上去。

## 常用檢查

```bash
sudo systemctl status goodjian --no-pager
sudo nginx -t
tail -n 50 ~/GoodJianPlus/logs/gunicorn_error.log
```

瀏覽器開 https://goodjian.shop 。後台 https://goodjian.shop/admin/ 。

服務沒起來：

```bash
sudo journalctl -u goodjian -n 80 --no-pager
sudo systemctl restart goodjian
```

## 不要做的事

- 不要在聊天或 Git 貼正式機 `.env`、SSH 私鑰、資料庫檔。
- 不要按 Oracle **Upgrade**（會變付費帳號）。
- 暫時機只有 1 GB，不要在這台裝 MySQL。
- 換 A1 大機後公網 IP 會變：改 GoDaddy 的 A 紀錄，並改 [operations.local.md](operations.local.md) 裡的 IP。SSH 指令裡的 IP 也要一起改。憑證（Let's Encrypt）網域沒變就不用重申請。
