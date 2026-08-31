<div align="center">
<img src="static/img/common/Logo.png" alt="好健健 GoodJian Plus" width="180">

# 好健健 GoodJian Plus - 電商平台系統

[![Site](https://img.shields.io/badge/site-goodjian.shop-16d3b4?style=flat-square)](https://goodjian.shop)
[![Django](https://img.shields.io/badge/Django-5.2-092E20?style=flat-square&logo=django&logoColor=white)](https://www.djangoproject.com/)
[![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![zh-TW](https://img.shields.io/badge/lang-zh--TW-red?style=flat-square)](#)

[![SQLite](https://img.shields.io/badge/dev-SQLite-003B57?style=flat-square)](#本機啟動)
[![MySQL](https://img.shields.io/badge/prod-MySQL-4479A1?style=flat-square)](docs/operations.md)
[![License](https://img.shields.io/badge/License-Non--Commercial%20Educational-yellow?style=flat-square)](LICENSE)

健身用品與營養餐食電商。教材／作品集原始碼，禁止商用與正式上線。
</div>

## 本機啟動

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements-dev.txt
copy .env.example .env
python manage.py migrate
python manage.py runserver
```

地端預設 SQLite（`.env` 的 `DB_ENGINE=sqlite`）。本機後台路徑見 Django Admin。

## 文件

- [本機與部署概要](docs/operations.md)
- [正式機 SSH 與更新程式](docs/deploy.md)
- [安全](docs/security.md)
- [郵件](docs/email.md)
- [手機登入 / SMS](docs/sms-phone-login.md)
- [版本紀錄](docs/changelog.md)

## 常用指令

```bash
python manage.py test_email
python manage.py check_sms_config
python -m pytest
python scripts/bootstrap_dev.py
```

## License

[非商業學術教材授權](LICENSE)（**不是** MIT／OSI 開源）。Copyright (c) 2026 KKeevin。

允許下載、學習、改作業與課堂使用；**禁止商用、禁止當成正式對外網站／電商上線**。第三方套件（如 Django）仍依其原授權。
