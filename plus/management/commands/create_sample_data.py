"""
創建範例數據的管理命令
用法：python manage.py create_sample_data
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from decimal import Decimal
from plus.models import (
    Category, Brand, Product, ProductImage,
    ArticleCategory, Article, ArticleImage,
    Food
)

CustomUser = get_user_model()


class Command(BaseCommand):
    help = '創建範例數據（分類、品牌、商品、文章、食物資料）'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='清除現有範例數據後再創建',
        )

    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write(self.style.WARNING('清除現有範例數據...'))
            # 只清除範例數據，保留用戶數據
            Product.objects.filter(sku__startswith='SAMPLE-').delete()
            Article.objects.filter(slug__startswith='sample-').delete()
            self.stdout.write(self.style.SUCCESS('清除完成'))

        self.stdout.write(self.style.SUCCESS('開始創建範例數據...'))

        # 1. 創建分類
        categories = self.create_categories()
        
        # 2. 創建品牌
        brands = self.create_brands()
        
        # 3. 創建商品
        self.create_products(categories, brands)
        
        # 4. 創建文章分類和文章
        self.create_articles()
        
        # 5. 創建食物資料
        self.create_foods()

        self.stdout.write(self.style.SUCCESS('\n✅ 範例數據創建完成！'))

    def create_categories(self):
        """創建商品分類"""
        self.stdout.write('創建商品分類...')
        
        categories_data = [
            {'name': '有氧器材', 'slug': 'cardio-equipment', 'order': 1, 'desc': '各種有氧運動器材'},
            {'name': '重訓器材', 'slug': 'strength-equipment', 'order': 2, 'desc': '重量訓練器材'},
            {'name': '瑜珈用品', 'slug': 'yoga-supplies', 'order': 3, 'desc': '瑜珈相關用品'},
            {'name': '運動配件', 'slug': 'fitness-accessories', 'order': 4, 'desc': '運動配件和裝備'},
            {'name': '營養補給', 'slug': 'nutrition-supplements', 'order': 5, 'desc': '運動營養補給品'},
        ]
        
        categories = {}
        for data in categories_data:
            category, created = Category.objects.get_or_create(
                slug=data['slug'],
                defaults={
                    'name': data['name'],
                    'description': data['desc'],
                    'is_active': True,
                    'sort_order': data['order']
                }
            )
            categories[data['slug']] = category
            if created:
                self.stdout.write(f'  ✓ 創建分類：{data["name"]}')
            else:
                self.stdout.write(f'  - 分類已存在：{data["name"]}')
        
        return categories

    def create_brands(self):
        """創建品牌"""
        self.stdout.write('創建品牌...')
        
        brands_data = [
            {'name': '好健健', 'slug': 'goodjian', 'desc': '好健健專業品牌'},
            {'name': '專業健身', 'slug': 'pro-fitness', 'desc': '專業健身器材品牌'},
            {'name': '健康生活', 'slug': 'healthy-life', 'desc': '健康生活品牌'},
        ]
        
        brands = {}
        for data in brands_data:
            brand, created = Brand.objects.get_or_create(
                slug=data['slug'],
                defaults={
                    'name': data['name'],
                    'description': data['desc'],
                    'is_active': True
                }
            )
            brands[data['slug']] = brand
            if created:
                self.stdout.write(f'  ✓ 創建品牌：{data["name"]}')
            else:
                self.stdout.write(f'  - 品牌已存在：{data["name"]}')
        
        return brands

    def create_products(self, categories, brands):
        """創建商品"""
        self.stdout.write('創建商品...')
        
        products_data = [
            {
                'name': '專業跑步機', 'sku': 'SAMPLE-TM-001',
                'category': 'cardio-equipment', 'brand': 'goodjian',
                'price': 15000, 'original_price': 18000, 'stock': 10,
                'desc': '專業級跑步機，適合家庭使用，多種運動模式',
                'short_desc': '專業級跑步機'
            },
            {
                'name': '動感單車', 'sku': 'SAMPLE-BC-001',
                'category': 'cardio-equipment', 'brand': 'pro-fitness',
                'price': 8000, 'original_price': 10000, 'stock': 15,
                'desc': '高品質動感單車，靜音設計，適合居家運動',
                'short_desc': '高品質動感單車'
            },
            {
                'name': '可調節啞鈴組', 'sku': 'SAMPLE-DB-001',
                'category': 'strength-equipment', 'brand': 'goodjian',
                'price': 2000, 'original_price': 2500, 'stock': 20,
                'desc': '可調節重量啞鈴組，節省空間，適合各種訓練',
                'short_desc': '可調節重量啞鈴組'
            },
            {
                'name': '專業瑜伽墊', 'sku': 'SAMPLE-YM-001',
                'category': 'yoga-supplies', 'brand': 'healthy-life',
                'price': 500, 'original_price': 600, 'stock': 50,
                'desc': '防滑專業瑜伽墊，厚度適中，適合各種瑜伽動作',
                'short_desc': '防滑專業瑜伽墊'
            },
            {
                'name': '運動水壺', 'sku': 'SAMPLE-BT-001',
                'category': 'fitness-accessories', 'brand': 'goodjian',
                'price': 300, 'original_price': 350, 'stock': 100,
                'desc': '不鏽鋼運動水壺，保溫保冷，適合各種運動',
                'short_desc': '不鏽鋼運動水壺'
            },
            {
                'name': '乳清蛋白粉', 'sku': 'SAMPLE-PP-001',
                'category': 'nutrition-supplements', 'brand': 'pro-fitness',
                'price': 800, 'original_price': 1000, 'stock': 30,
                'desc': '高品質乳清蛋白粉，快速吸收，適合運動後補充',
                'short_desc': '高品質乳清蛋白粉'
            },
        ]
        
        for data in products_data:
            category = categories.get(data['category'])
            brand = brands.get(data['brand'])
            
            if not category or not brand:
                self.stdout.write(self.style.WARNING(f'  ⚠ 跳過商品 {data["name"]}：缺少分類或品牌'))
                continue
            
            product, created = Product.objects.get_or_create(
                sku=data['sku'],
                defaults={
                    'name': data['name'],
                    'category': category,
                    'brand': brand,
                    'price': Decimal(str(data['price'])),
                    'original_price': Decimal(str(data['original_price'])),
                    'stock_quantity': data['stock'],
                    'description': data['desc'],
                    'short_description': data['short_desc'],
                    'status': 'published',
                    'is_featured': True
                }
            )
            
            if created:
                self.stdout.write(f'  ✓ 創建商品：{data["name"]} (NT${data["price"]})')
            else:
                self.stdout.write(f'  - 商品已存在：{data["name"]}')

    def create_articles(self):
        """創建文章分類和文章"""
        self.stdout.write('創建文章...')
        
        # 創建文章分類
        article_category, created = ArticleCategory.objects.get_or_create(
            slug='sample-fitness-knowledge',
            defaults={
                'name': '運動知識',
                'description': '運動相關知識文章',
                'is_active': True,
                'sort_order': 1
            }
        )
        
        if created:
            self.stdout.write(f'  ✓ 創建文章分類：運動知識')
        
        # 獲取或創建作者（使用第一個超級用戶）
        author = CustomUser.objects.filter(is_superuser=True).first()
        if not author:
            # 如果沒有超級用戶，創建一個測試用戶
            author = CustomUser.objects.create_user(
                username='admin_author',
                email='admin@example.com',
                password='admin123',
                is_staff=True,
                is_superuser=True
            )
            self.stdout.write(f'  ✓ 創建作者：{author.username}')
        
        # 創建文章
        articles_data = [
            {
                'title': '如何開始你的健身之旅',
                'slug': 'sample-how-to-start-fitness',
                'excerpt': '這是一篇關於如何開始健身的完整指南，適合初學者閱讀。',
                'content': '''
                <h2>為什麼要開始健身？</h2>
                <p>健身不僅能改善身體健康，還能提升心理狀態和生活品質。</p>
                
                <h2>第一步：設定目標</h2>
                <p>明確的目標是成功的一半。無論是減重、增肌還是提升體能，都需要具體的目標。</p>
                
                <h2>第二步：選擇適合的運動</h2>
                <p>根據你的目標和身體狀況，選擇適合的運動方式。可以從簡單的有氧運動開始。</p>
                
                <h2>第三步：制定計劃</h2>
                <p>制定一個可行的運動計劃，並堅持執行。記住，持之以恆比強度更重要。</p>
                ''',
            },
            {
                'title': '運動營養補充指南',
                'slug': 'sample-nutrition-guide',
                'excerpt': '了解運動前後如何正確補充營養，讓你的訓練效果事半功倍。',
                'content': '''
                <h2>運動前補充</h2>
                <p>運動前1-2小時可以補充一些碳水化合物，提供運動所需的能量。</p>
                
                <h2>運動中補充</h2>
                <p>長時間運動時，記得補充水分和電解質，避免脫水。</p>
                
                <h2>運動後補充</h2>
                <p>運動後30分鐘內是補充蛋白質的黃金時間，有助於肌肉修復和生長。</p>
                ''',
            },
        ]
        
        for data in articles_data:
            article, created = Article.objects.get_or_create(
                slug=data['slug'],
                defaults={
                    'title': data['title'],
                    'category': article_category,
                    'author': author,
                    'excerpt': data['excerpt'],
                    'content': data['content'],
                    'status': 'published',
                    'published_at': timezone.now()
                }
            )
            
            if created:
                self.stdout.write(f'  ✓ 創建文章：{data["title"]}')
            else:
                self.stdout.write(f'  - 文章已存在：{data["title"]}')

    def create_foods(self):
        """創建食物營養資料"""
        self.stdout.write('創建食物資料...')
        
        foods_data = [
            {'name': '雞胸肉', 'category': 'meat', 'calories': 165, 'protein': 31, 'carbs': 0, 'fat': 3.6},
            {'name': '白米飯', 'category': 'grains', 'calories': 130, 'protein': 2.7, 'carbs': 28, 'fat': 0.3},
            {'name': '雞蛋', 'category': 'meat', 'calories': 155, 'protein': 13, 'carbs': 1.1, 'fat': 11},
            {'name': '香蕉', 'category': 'fruits', 'calories': 89, 'protein': 1.1, 'carbs': 23, 'fat': 0.3},
            {'name': '花椰菜', 'category': 'vegetables', 'calories': 25, 'protein': 3, 'carbs': 5, 'fat': 0.3},
            {'name': '鮭魚', 'category': 'seafood', 'calories': 208, 'protein': 20, 'carbs': 0, 'fat': 12},
            {'name': '燕麥', 'category': 'grains', 'calories': 389, 'protein': 17, 'carbs': 66, 'fat': 7},
            {'name': '希臘優格', 'category': 'dairy', 'calories': 59, 'protein': 10, 'carbs': 3.6, 'fat': 0.4},
        ]
        
        for data in foods_data:
            food, created = Food.objects.get_or_create(
                name=data['name'],
                defaults={
                    'category': data['category'],
                    'serving_size': '100g',
                    'calories': Decimal(str(data['calories'])),
                    'protein': Decimal(str(data['protein'])),
                    'carbs': Decimal(str(data['carbs'])),
                    'fat': Decimal(str(data['fat'])),
                    'is_active': True
                }
            )
            
            if created:
                self.stdout.write(f'  ✓ 創建食物：{data["name"]}')
            else:
                self.stdout.write(f'  - 食物已存在：{data["name"]}')

