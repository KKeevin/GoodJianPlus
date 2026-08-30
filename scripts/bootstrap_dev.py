"""
專案初始化腳本
用於快速設置開發環境
"""
import os
import subprocess
import sys
from pathlib import Path

def create_env_file():
    """創建 .env 文件（如果不存在）"""
    env_file = Path('.env')
    env_example = Path('.env.example')
    
    if env_file.exists():
        print('✓ .env 文件已存在')
        return
    
    if env_example.exists():
        print('正在創建 .env 文件...')
        with open(env_example, 'r', encoding='utf-8') as f:
            content = f.read()
        with open(env_file, 'w', encoding='utf-8') as f:
            f.write(content)
        print('✓ .env 文件已創建，請編輯並填入實際值')
    else:
        print('⚠ .env.example 文件不存在')

def create_directories():
    """創建必要的目錄"""
    directories = ['logs', 'media', 'staticfiles']
    for dir_name in directories:
        dir_path = Path(dir_name)
        if not dir_path.exists():
            dir_path.mkdir(parents=True, exist_ok=True)
            print(f'✓ 創建目錄: {dir_name}')
        else:
            print(f'✓ 目錄已存在: {dir_name}')

def check_dependencies():
    """檢查必要的依賴"""
    try:
        import django
        print(f'✓ Django {django.__version__} 已安裝')
    except ImportError:
        print('⚠ Django 未安裝，請運行: pip install -r requirements.txt')
        return False
    
    try:
        import pymysql
        print('✓ pymysql 已安裝')
    except ImportError:
        print('⚠ pymysql 未安裝，請運行: pip install -r requirements.txt')
        return False
    
    return True

def main():
    print('=' * 50)
    print('好健健 GoodJian Plus - 專案初始化')
    print('=' * 50)
    print()
    
    # 創建目錄
    print('1. 檢查目錄結構...')
    create_directories()
    print()
    
    # 創建 .env 文件
    print('2. 檢查環境變數配置...')
    create_env_file()
    print()
    
    # 檢查依賴
    print('3. 檢查依賴套件...')
    if not check_dependencies():
        print()
        print('請先安裝依賴: pip install -r requirements.txt')
        return
    print()
    
    print('=' * 50)
    print('初始化完成！')
    print('=' * 50)
    print()
    print('下一步：')
    print('1. 編輯 .env 文件，填入資料庫等配置')
    print('2. 運行: python manage.py migrate')
    print('3. 運行: python manage.py createsuperuser')
    print('4. 運行: python manage.py collectstatic')
    print('5. 運行: python manage.py runserver')
    print()

if __name__ == '__main__':
    main()

