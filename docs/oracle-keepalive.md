# Oracle 免費機保活（避免閒置被回收）

> **提醒：正式機上有一支程式一直在吃 CPU，這是故意的。** 2026-10-04 安裝。要拿主機跑別的東西、覺得網站變慢、或換主機時，先看這份。

## 為什麼要裝

Oracle Always Free 會回收閒置主機。7 天內以下條件**同時**成立就算閒置：

- CPU 使用率 95 百分位 < 20%
- 網路使用率 < 20%
- 記憶體使用率 < 20%（只有 A1 機型才看）

網站流量小時 CPU 幾乎是 0%，放著會被當成閒置、被刪主機。只要 CPU 穩定 > 20% 就不算閒置。

## 裝了什麼

| 項目 | 位置 |
|------|------|
| 程式 | `scripts/oracle_keepalive.py`（只用 Python 標準庫） |
| 服務範本 | `scripts/systemd/goodjian-keepalive.service` |
| 伺服器上的服務 | `/etc/systemd/system/goodjian-keepalive.service`（開機自動啟動，掛掉 30 秒自動重啟） |
| 覆蓋設定（可選） | `/etc/systemd/system/goodjian-keepalive.service.d/override.conf`（目前**沒有**，用預設值） |

原理：每顆 vCPU 每 0.1 秒忙固定比例的時間。排程等級是 `idle`（`top` 裡 `NI` 欄是 19），主機內其他程式要 CPU 時會優先讓出。

## 目前狀態（2026-10-04 實測）

- 主機：`VM.Standard.E2.1.Micro`（2 vCPU、1 GB），東京區
- 設定：`KEEPALIVE_CPU_PERCENT=25`（預設值）、`KEEPALIVE_MEM_MB=0`
- Oracle Console 顯示的 CPU Utilization：約 **30～35%**
- 設 35% 時 Console 顯示約 40～60%，太多，已調回 25%
- 記憶體平常就約 45～50%

E2.1.Micro 是可短暫衝高的機型，會有 steal（`top` 的 `st`），Oracle 的數字會比 `top` 的 `ni` 高，所以看 Console 為準。

## 之後要用主機時怎麼調

以下都在 SSH 進主機後執行。

### 看現在的狀態

```bash
sudo systemctl status goodjian-keepalive.service --no-pager
journalctl -u goodjian-keepalive -n 1 --no-pager
```

最後一行會顯示 `keepalive: 2 vCPU x 25% CPU, memory hold 0 MB`。

### 調整強度

```bash
sudo mkdir -p /etc/systemd/system/goodjian-keepalive.service.d
printf '[Service]\nEnvironment=KEEPALIVE_CPU_PERCENT=20\n' | sudo tee /etc/systemd/system/goodjian-keepalive.service.d/override.conf
sudo systemctl daemon-reload
sudo systemctl restart goodjian-keepalive.service
journalctl -u goodjian-keepalive -n 1 --no-pager
```

把 `20` 換成想要的數字（1～90）。用 `sudo systemctl edit` 也可以，但內容要寫在 `### Lines below this comment will be discarded` **上面**，不然不會存。

回到預設 25%：

```bash
sudo rm /etc/systemd/system/goodjian-keepalive.service.d/override.conf
sudo systemctl daemon-reload
sudo systemctl restart goodjian-keepalive.service
```

### 暫時停掉（例如要跑很吃 CPU 的工作）

```bash
sudo systemctl stop goodjian-keepalive.service
```

做完記得開回來：

```bash
sudo systemctl start goodjian-keepalive.service
```

`stop` 只停到下次開機，重開機會自動再啟動。短時間停一兩天沒關係（Oracle 看的是 7 天）。

### 主機本身已經夠忙了，不需要保活

如果網站或其他服務平常就讓 Console 的 CPU 穩定 > 20%，可以整個停用：

```bash
sudo systemctl disable --now goodjian-keepalive.service
```

停用後要觀察一週 Console 的 CPU Utilization，確定沒掉到 20% 以下。要恢復：

```bash
sudo systemctl enable --now goodjian-keepalive.service
```

### 換成 A1 大機（或新主機）

新主機要重裝一次：

```bash
cd ~/GoodJianPlus
sudo cp scripts/systemd/goodjian-keepalive.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now goodjian-keepalive.service
```

A1 的 vCPU 比較多、沒有 steal，裝完一小時後到 Console 看 CPU，再決定要不要調整 `KEEPALIVE_CPU_PERCENT`。A1 也會看記憶體，如果記憶體用量很低，可以加 `Environment=KEEPALIVE_MEM_MB=...` 佔住一些記憶體（只要 CPU 達標就不算閒置，這只是額外保險）。舊主機刪掉前不用特別處理。

## 怎麼確認有效

Oracle Console → Compute → Instances → **goodjian** → 上方分頁 **Monitoring** → **CPU Utilization**。曲線一直在 20% 以上就沒問題。建議每 1～2 週看一次，也留意 Oracle 寄來的閒置通知信。

圖表如果是空的，到 **Management** 分頁確認 Oracle Cloud Agent 的 **Compute Instance Monitoring** 有開啟。

## 網站變慢時

1. `top` 看是不是別的程式吃 CPU（保活程式是 `python3`、`NI` 19）。
2. 先暫停保活（`sudo systemctl stop goodjian-keepalive.service`）看網站有沒有變快。
3. 有變快：把強度調低到 20 試試，並到 Console 確認仍 > 20%。
