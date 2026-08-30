from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.utils.text import slugify

from plus.models import Brand, Category, Food, Product


PARENTS = [
    {'name': '健身用品', 'slug': 'equipment', 'order': 1, 'desc': '運動器材、瑜珈用品與健身配件'},
    {'name': '健身食品', 'slug': 'food', 'order': 2, 'desc': '蛋白質、餐盒、零食與運動飲品'},
]

CHILDREN = [
    {'name': '有氧器材', 'slug': 'cardio', 'parent': 'equipment', 'order': 1, 'desc': '跑步機、飛輪與居家有氧器材'},
    {'name': '重訓器材', 'slug': 'strength', 'parent': 'equipment', 'order': 2, 'desc': '啞鈴、槓鈴、重訓椅與阻力訓練'},
    {'name': '瑜珈用品', 'slug': 'yoga', 'parent': 'equipment', 'order': 3, 'desc': '瑜珈墊、輔具與伸展用品'},
    {'name': '運動配件', 'slug': 'accessories', 'parent': 'equipment', 'order': 4, 'desc': '護具、水壺、毛巾與訓練配件'},
    {'name': '蛋白質補充', 'slug': 'protein', 'parent': 'food', 'order': 1, 'desc': '乳清、植物蛋白與增肌補給'},
    {'name': '健身餐盒', 'slug': 'meals', 'parent': 'food', 'order': 2, 'desc': '高蛋白低脂餐盒與雞胸料理'},
    {'name': '健康零食', 'slug': 'snacks', 'parent': 'food', 'order': 3, 'desc': '蛋白棒、堅果與低糖點心'},
    {'name': '運動飲品', 'slug': 'drinks', 'parent': 'food', 'order': 4, 'desc': '電解質、BCAA 與運動飲料'},
]

BRANDS = [
    {'name': '好健健', 'slug': 'goodjian', 'desc': '好健健自有品牌'},
    {'name': '專業健身', 'slug': 'pro-fitness', 'desc': '專業訓練器材'},
    {'name': '健康生活', 'slug': 'healthy-life', 'desc': '日常健康補給'},
]

# sku, name, category, brand, price, original_price, stock, featured, short, desc
# optional: calories, protein, carbs, fat
PRODUCTS = [
    ('GJ-CD-001', '家用折疊跑步機', 'cardio', 'goodjian', 12800, 15800, 8, True, '靜音折疊、適合小坪數', '馬達靜音、收折後可立放，內建坡度與心率感測，適合居家有氧。'),
    ('GJ-CD-002', '飛輪健身車', 'cardio', 'pro-fitness', 6900, 8500, 12, True, '18kg 飛輪、磁控阻力', '磁控阻力飛輪車，踏頻穩定、座墊可調，適合間歇訓練。'),
    ('GJ-CD-003', '橢圓交叉訓練機', 'cardio', 'pro-fitness', 18900, 21900, 5, False, '低衝擊全身有氧', '橢圓軌跡減少膝蓋負擔，雙手把可同步訓練上半身。'),
    ('GJ-CD-004', '踏步機 Mini Stepper', 'cardio', 'healthy-life', 1590, 1990, 25, False, '輕巧踏步、可計步', '占用空間小，附阻力彈力繩，適合客廳快速有氧。'),
    ('GJ-CD-005', '跳繩訓練組', 'cardio', 'goodjian', 390, 490, 60, False, '鋼索跳繩＋收納袋', '可調長度鋼索跳繩，軸承順暢，適合燃脂與敏捷訓練。'),
    ('GJ-ST-001', '可調式啞鈴 24kg', 'strength', 'goodjian', 3290, 3990, 18, True, '快速轉盤調重', '一對可調 2–24kg，節省空間，適合居家重量訓練。'),
    ('GJ-ST-002', '奧林匹克槓鈴 20kg', 'strength', 'pro-fitness', 4590, 5200, 10, False, '標準 220cm 槓身', '滾花防滑、軸套順暢，適合深蹲與臥推。'),
    ('GJ-ST-003', '可調重訓椅', 'strength', 'pro-fitness', 2890, 3490, 14, False, '多段椅背角度', '平躺／傾斜／直立多段調整，穩固鋼管結構。'),
    ('GJ-ST-004', '壺鈴 16kg', 'strength', 'goodjian', 1290, 1490, 20, False, '鑄鐵烤漆、防滑握把', '適合擺盪、深蹲與核心訓練的入門壺鈴。'),
    ('GJ-ST-005', '阻力帶五件組', 'strength', 'healthy-life', 590, 790, 40, False, '5 種阻力色碼', '乳膠阻力帶，附門錨與握把，可練全身。'),
    ('GJ-ST-006', '仰臥起坐輔助器', 'strength', 'goodjian', 790, 990, 22, False, '吸盤固定、護頸設計', '居家腹肌訓練輔具，角度可調、膝蓋減壓。'),
    ('GJ-YG-001', 'TPE 瑜珈墊 8mm', 'yoga', 'healthy-life', 680, 880, 45, True, '雙色防滑、附揹帶', '8mm 緩衝厚度，雙面防滑紋路，適合瑜珈與皮拉提斯。'),
    ('GJ-YG-002', '瑜珈磚兩入組', 'yoga', 'healthy-life', 320, 420, 50, False, '高密度EVA', '輔助下犬式與平衡體位，輕量好收納。'),
    ('GJ-YG-003', '伸展帶與拉力帶組', 'yoga', 'goodjian', 280, 360, 55, False, '伸展＋開肩訓練', '含棉織伸展帶與環狀拉力帶，適合熱身放鬆。'),
    ('GJ-YG-004', '瑜珈輪', 'yoga', 'healthy-life', 890, 1090, 16, False, '開胸、放鬆背肌', 'TPE 包覆ABS輪體，直徑 33cm，輔助後彎。'),
    ('GJ-YG-005', '平衡球 65cm', 'yoga', 'pro-fitness', 490, 650, 28, False, '防爆材質、含打氣筒', '核心訓練與辦公室坐姿交替使用。'),
    ('GJ-AC-001', '不鏽鋼保溫運動瓶 750ml', 'accessories', 'goodjian', 450, 590, 80, False, '保冷24小時', '食品級不鏽鋼內膽，寬口好清洗，健身房必備。'),
    ('GJ-AC-002', '重訓護腕一對', 'accessories', 'pro-fitness', 390, 490, 36, False, '加壓支撐、魔鬼氈', '臥推與划船時穩定手腕，可調鬆緊。'),
    ('GJ-AC-003', '舉重手套', 'accessories', 'goodjian', 320, 420, 42, False, '防滑掌墊、透氣', '減少槓鈴滑動與手繭，適合中高重量。'),
    ('GJ-AC-004', '速乾運動毛巾', 'accessories', 'healthy-life', 220, 280, 90, False, '吸汗快乾、掛扣', '健身房擦汗用，輕薄可掛水壺。'),
    ('GJ-AC-005', '筋膜泡沫滾筒', 'accessories', 'pro-fitness', 560, 720, 24, False, '肌肉放鬆按摩', '中空EVA滾筒，訓練後放鬆大腿與背肌。'),
    ('GJ-AC-006', '計數跳繩握把組', 'accessories', 'goodjian', 350, 450, 33, False, '電子計次、卡路里', '握把內建計次，適合居家燃脂挑戰。'),
    ('GJ-PR-001', '乳清蛋白 香草 2kg', 'protein', 'goodjian', 1680, 1980, 30, True, '每份24g蛋白質', '分離乳清為主，好溶解、低糖，訓練後補充。', 390, 24, 4, 1.5),
    ('GJ-PR-002', '乳清蛋白 巧克力 2kg', 'protein', 'goodjian', 1680, 1980, 28, False, '可可風味、好沖泡', '適合增肌期，可搭配牛奶或燕麥。', 395, 24, 5, 2),
    ('GJ-PR-003', '植物蛋白 豌豆 1kg', 'protein', 'healthy-life', 1280, 1480, 20, False, '素食可、無乳糖', '豌豆分離蛋白，添加消化酵素。', 370, 22, 6, 2),
    ('GJ-PR-004', '酪蛋白夜用蛋白 1kg', 'protein', 'pro-fitness', 1450, 1690, 15, False, '緩慢釋放胺基酸', '睡前補充，幫助夜間修復。', 360, 24, 3, 1.2),
    ('GJ-PR-005', 'BCAA 胺基酸粉 300g', 'protein', 'pro-fitness', 890, 1090, 26, False, '訓練中防分解', '2:1:1 配方，檸檬風味，訓練中補充。', 20, 5, 0, 0),
    ('GJ-ML-001', '舒肥雞胸原味 10入', 'meals', 'goodjian', 599, 720, 40, True, '高蛋白低脂、即食', '舒肥低溫烹調，拆封即可吃，適合備餐。', 110, 23, 1, 2),
    ('GJ-ML-002', '舒肥雞胸黑胡椒 10入', 'meals', 'goodjian', 619, 750, 35, False, '黑胡椒香、不柴', '調味適中，可搭配糙米或沙拉。', 115, 23, 2, 2),
    ('GJ-ML-003', '雞胸餐盒 藜麥時蔬', 'meals', 'healthy-life', 189, 220, 48, False, '單人份冷鏈餐盒', '雞胸＋藜麥＋季節蔬菜，約 450 kcal。', 450, 38, 42, 10),
    ('GJ-ML-004', '鮭魚糙米飯餐盒', 'meals', 'healthy-life', 219, 259, 32, False, 'Omega-3 健身餐', '烤鮭魚搭配糙米與青花菜。', 520, 36, 48, 16),
    ('GJ-ML-005', '牛肉蔬菜餐盒', 'meals', 'goodjian', 209, 249, 30, False, '紅肉補鐵選擇', '瘦牛肉佐烤時蔬，適合重訓日。', 480, 40, 35, 14),
    ('GJ-SN-001', '蛋白棒 花生巧克力 12入', 'snacks', 'goodjian', 720, 860, 50, False, '每條 20g 蛋白', '訓練前後點心，低糖配方。', 210, 20, 18, 7),
    ('GJ-SN-002', '烘烤雞胸脆片', 'snacks', 'healthy-life', 149, 189, 70, False, '非油炸高蛋白零食', '薄片烘烤，海鹽風味。', 320, 55, 4, 6),
    ('GJ-SN-003', '無調味綜合堅果 500g', 'snacks', 'healthy-life', 390, 450, 44, False, '隨身好油脂', '杏仁、核桃、腰果綜合，無添加鹽糖。', 600, 18, 16, 52),
    ('GJ-SN-004', '高蛋白優格杯 6入', 'snacks', 'goodjian', 259, 320, 38, False, '冷藏、每杯 15g 蛋白', '原味無糖優格，早餐或點心。', 90, 15, 6, 0.5),
    ('GJ-DR-001', '電解質沖泡粉 20包', 'drinks', 'pro-fitness', 490, 590, 40, False, '補充電解質、無糖', '訓練中或炎熱天氣補充鈉鉀鎂。', 15, 0, 2, 0),
    ('GJ-DR-002', 'BCAA 運動飲料 24瓶', 'drinks', 'goodjian', 799, 960, 22, False, '即開即飲', '葡萄風味，訓練中好入口。', 25, 5, 2, 0),
    ('GJ-DR-003', '黑咖啡無糖 24入', 'drinks', 'healthy-life', 429, 499, 36, False, '訓練前提神', '濾掛式無糖黑咖啡，低卡。', 5, 0.3, 0, 0),
    ('GJ-DR-004', '分離乳清即飲 6瓶', 'drinks', 'goodjian', 540, 660, 27, False, '出門免沖泡', '香草口味即飲瓶，約 25g 蛋白。', 140, 25, 4, 1),
]


FOODS = [
    ('雞胸肉', 'meat', '100g', 165, 31, 0, 3.6),
    ('舒肥雞胸', 'meat', '100g', 110, 23, 1, 2),
    ('烤雞腿排（去皮）', 'meat', '100g', 175, 27, 0, 7),
    ('雞里肌', 'meat', '100g', 120, 23, 0, 3),
    ('雞蛋', 'meat', '1顆（50g）', 78, 6.5, 0.6, 5.3),
    ('蛋白', 'meat', '1顆', 17, 3.6, 0.2, 0.1),
    ('蛋黃', 'meat', '1顆', 55, 2.7, 0.6, 4.5),
    ('茶葉蛋', 'meat', '1顆', 90, 7, 1, 6),
    ('瘦牛肉', 'meat', '100g', 250, 26, 0, 15),
    ('牛腱', 'meat', '100g', 175, 31, 0, 5),
    ('牛五花', 'meat', '100g', 337, 15, 0, 31),
    ('豬里肌', 'meat', '100g', 143, 21, 0, 6),
    ('豬菲力', 'meat', '100g', 136, 22, 0, 5),
    ('瘦絞肉（豬）', 'meat', '100g', 185, 20, 0, 11),
    ('火雞肉', 'meat', '100g', 135, 30, 0, 1),
    ('鴨胸', 'meat', '100g', 195, 24, 0, 11),
    ('羊肉', 'meat', '100g', 206, 25, 0, 11),
    ('火腿片', 'meat', '2片（30g）', 45, 5, 1, 2),
    ('培根', 'meat', '2片（16g）', 86, 3, 0.2, 8),
    ('雞胸肉絲便當', 'meat', '1份', 420, 38, 45, 8),
    ('滷雞腿', 'meat', '1隻', 280, 28, 4, 16),
    ('鮭魚', 'seafood', '100g', 208, 20, 0, 13),
    ('鯖魚', 'seafood', '100g', 205, 19, 0, 14),
    ('鯛魚', 'seafood', '100g', 96, 20, 0, 1.5),
    ('鱸魚', 'seafood', '100g', 97, 18, 0, 2.5),
    ('鱈魚', 'seafood', '100g', 82, 18, 0, 0.7),
    ('蝦仁', 'seafood', '100g', 99, 24, 0.2, 0.3),
    ('草蝦', 'seafood', '100g', 85, 20, 0.5, 0.5),
    ('白蝦', 'seafood', '100g', 87, 20, 0.2, 0.5),
    ('蛤蜊', 'seafood', '100g', 74, 13, 3, 1),
    ('牡蠣', 'seafood', '100g', 81, 9, 4, 2.5),
    ('透抽', 'seafood', '100g', 92, 16, 3, 1.4),
    ('花枝', 'seafood', '100g', 79, 16, 1, 1),
    ('鮪魚', 'seafood', '100g', 132, 28, 0, 1.3),
    ('鮪魚罐頭（水煮）', 'seafood', '1罐（100g）', 116, 26, 0, 1),
    ('秋刀魚', 'seafood', '100g', 231, 18, 0, 17),
    ('虱目魚', 'seafood', '100g', 126, 20, 0, 5),
    ('吳郭魚', 'seafood', '100g', 96, 20, 0, 1.7),
    ('干貝', 'seafood', '100g', 69, 12, 3, 0.5),
    ('白米飯', 'grains', '一碗（200g）', 260, 4.8, 56, 0.6),
    ('糙米飯', 'grains', '一碗（200g）', 222, 5.2, 46, 1.8),
    ('五穀飯', 'grains', '一碗（200g）', 230, 6, 46, 2),
    ('紫米飯', 'grains', '一碗（200g）', 218, 5, 45, 1.5),
    ('燕麥', 'grains', '40g', 156, 6.8, 26, 3.2),
    ('即食燕麥片', 'grains', '40g', 150, 5, 27, 3),
    ('全麥吐司', 'grains', '1片', 80, 4, 14, 1),
    ('白吐司', 'grains', '1片', 75, 2.5, 14, 1),
    ('貝果', 'grains', '1個', 250, 10, 48, 1.5),
    ('義大利麵（熟）', 'grains', '100g', 131, 5, 25, 1.1),
    ('全麥義大利麵（熟）', 'grains', '100g', 124, 5.3, 26, 0.5),
    ('冬粉（熟）', 'grains', '100g', 80, 0.1, 20, 0),
    ('米粉（熟）', 'grains', '100g', 109, 1, 25, 0.2),
    ('麵條（熟）', 'grains', '100g', 138, 4.5, 25, 2),
    ('地瓜', 'grains', '100g', 86, 1.6, 20, 0.1),
    ('紫地瓜', 'grains', '100g', 123, 1.5, 29, 0.2),
    ('馬鈴薯', 'grains', '100g', 77, 2, 17, 0.1),
    ('玉米', 'grains', '1根', 86, 3.2, 19, 1.2),
    ('南瓜', 'grains', '100g', 26, 1, 7, 0.1),
    ('藜麥（熟）', 'grains', '100g', 120, 4.4, 21, 1.9),
    ('糙米粥', 'grains', '一碗', 150, 3.5, 32, 1),
    ('花椰菜', 'vegetables', '100g', 25, 3, 5, 0.3),
    ('青花菜', 'vegetables', '100g', 34, 2.8, 7, 0.4),
    ('菠菜', 'vegetables', '100g', 23, 2.9, 3.6, 0.4),
    ('番茄', 'vegetables', '100g', 18, 0.9, 3.9, 0.2),
    ('小番茄', 'vegetables', '100g', 18, 0.9, 3.9, 0.2),
    ('高麗菜', 'vegetables', '100g', 25, 1.3, 6, 0.1),
    ('青江菜', 'vegetables', '100g', 13, 1.5, 2.2, 0.2),
    ('空心菜', 'vegetables', '100g', 19, 2.6, 3.1, 0.2),
    ('A菜', 'vegetables', '100g', 16, 1.4, 2.5, 0.2),
    ('生菜', 'vegetables', '100g', 15, 1.4, 2.9, 0.2),
    ('小黃瓜', 'vegetables', '100g', 15, 0.7, 3.6, 0.1),
    ('櫛瓜', 'vegetables', '100g', 17, 1.2, 3.1, 0.3),
    ('茄子', 'vegetables', '100g', 25, 1, 6, 0.2),
    ('青椒', 'vegetables', '100g', 20, 0.9, 4.6, 0.2),
    ('甜椒', 'vegetables', '100g', 31, 1, 6, 0.3),
    ('蘆筍', 'vegetables', '100g', 20, 2.2, 3.9, 0.1),
    ('蘑菇', 'vegetables', '100g', 22, 3.1, 3.3, 0.3),
    ('杏鮑菇', 'vegetables', '100g', 35, 1.7, 7.5, 0.2),
    ('金針菇', 'vegetables', '100g', 37, 2.7, 7.8, 0.2),
    ('海帶芽', 'vegetables', '100g', 35, 1.7, 8, 0.5),
    ('毛豆', 'vegetables', '100g', 122, 11, 10, 5),
    ('四季豆', 'vegetables', '100g', 31, 1.8, 7, 0.1),
    ('胡蘿蔔', 'vegetables', '100g', 41, 0.9, 10, 0.2),
    ('洋蔥', 'vegetables', '100g', 40, 1.1, 9, 0.1),
    ('香蕉', 'fruits', '1根（120g）', 107, 1.3, 27, 0.4),
    ('蘋果', 'fruits', '1顆（180g）', 95, 0.5, 25, 0.3),
    ('藍莓', 'fruits', '100g', 57, 0.7, 14, 0.3),
    ('草莓', 'fruits', '100g', 32, 0.7, 7.7, 0.3),
    ('酪梨', 'fruits', '100g', 160, 2, 9, 15),
    ('奇異果', 'fruits', '1顆', 42, 0.8, 10, 0.4),
    ('橘子', 'fruits', '1顆', 47, 0.9, 12, 0.1),
    ('柳丁', 'fruits', '1顆', 62, 1.2, 15, 0.2),
    ('葡萄柚', 'fruits', '半顆', 52, 0.9, 13, 0.2),
    ('葡萄', 'fruits', '100g', 69, 0.7, 18, 0.2),
    ('西瓜', 'fruits', '100g', 30, 0.6, 8, 0.2),
    ('哈密瓜', 'fruits', '100g', 34, 0.8, 8, 0.2),
    ('木瓜', 'fruits', '100g', 43, 0.5, 11, 0.3),
    ('芒果', 'fruits', '100g', 60, 0.8, 15, 0.4),
    ('鳳梨', 'fruits', '100g', 50, 0.5, 13, 0.1),
    ('火龍果', 'fruits', '100g', 60, 1.2, 13, 0.4),
    ('芭樂', 'fruits', '1顆', 68, 2.6, 14, 1),
    ('梨子', 'fruits', '1顆', 101, 0.6, 27, 0.2),
    ('希臘優格', 'dairy', '100g', 59, 10, 3.6, 0.4),
    ('原味優格', 'dairy', '100g', 61, 3.5, 4.7, 3.3),
    ('低脂鮮奶', 'dairy', '240ml', 102, 8, 12, 2.4),
    ('全脂鮮奶', 'dairy', '240ml', 149, 8, 12, 8),
    ('無糖優酪乳', 'dairy', '200ml', 80, 6, 8, 2),
    ('起司', 'dairy', '30g', 113, 7, 0.4, 9),
    ('低脂起司片', 'dairy', '1片', 50, 6, 1, 2.5),
    ('茅屋起司', 'dairy', '100g', 98, 11, 3.4, 4.3),
    ('雞蛋布丁（無糖）', 'dairy', '100g', 105, 6, 8, 5),
    ('杏仁', 'nuts', '30g', 174, 6, 6, 15),
    ('核桃', 'nuts', '30g', 196, 4.6, 4, 20),
    ('腰果', 'nuts', '30g', 166, 5, 9, 13),
    ('開心果', 'nuts', '30g', 168, 6, 8, 14),
    ('夏威夷豆', 'nuts', '30g', 215, 2.4, 4, 23),
    ('花生', 'nuts', '30g', 170, 7, 5, 14),
    ('花生醬', 'nuts', '15g', 90, 4, 3, 8),
    ('杏仁醬', 'nuts', '15g', 98, 3.4, 3, 9),
    ('奇亞籽', 'nuts', '15g', 73, 2.5, 6, 4.5),
    ('亞麻仁籽', 'nuts', '15g', 80, 2.7, 4, 6),
    ('南瓜籽', 'nuts', '30g', 163, 9, 4, 14),
    ('葵花籽', 'nuts', '30g', 175, 6, 6, 15),
    ('蛋白棒', 'snacks', '1條', 210, 20, 18, 7),
    ('雞胸脆片', 'snacks', '30g', 96, 16, 1, 2),
    ('米餅', 'snacks', '3片', 35, 0.7, 7, 0.3),
    ('蘇打餅乾', 'snacks', '4片', 70, 1.5, 12, 2),
    ('無調味爆米花', 'snacks', '30g', 110, 3, 22, 1),
    ('海苔', 'snacks', '1包（3g）', 10, 1.2, 1, 0.1),
    ('黑巧克力（70%）', 'snacks', '20g', 120, 1.6, 9, 8),
    ('果乾（無糖芒果）', 'snacks', '30g', 96, 0.6, 23, 0.3),
    ('能量球', 'snacks', '1顆', 80, 3, 8, 4),
    ('黑咖啡', 'beverages', '240ml', 2, 0.3, 0, 0),
    ('美式咖啡', 'beverages', '240ml', 5, 0.3, 0, 0),
    ('拿鐵（全脂）', 'beverages', '240ml', 140, 7, 11, 7),
    ('綠茶', 'beverages', '240ml', 2, 0, 0, 0),
    ('烏龍茶', 'beverages', '240ml', 2, 0, 0, 0),
    ('無糖豆漿', 'beverages', '240ml', 80, 7, 4, 4),
    ('有糖豆漿', 'beverages', '240ml', 130, 7, 16, 4),
    ('電解質飲料', 'beverages', '500ml', 50, 0, 12, 0),
    ('運動飲料', 'beverages', '500ml', 125, 0, 30, 0),
    ('椰子水', 'beverages', '240ml', 46, 1.7, 9, 0.5),
    ('氣泡水', 'beverages', '240ml', 0, 0, 0, 0),
    ('無糖紅茶', 'beverages', '240ml', 2, 0, 0.5, 0),
    ('蛋白奶昔', 'beverages', '1杯', 180, 25, 8, 3),
    ('乳清蛋白粉', 'others', '1匙（30g）', 120, 24, 3, 1.5),
    ('酪蛋白粉', 'others', '1匙（30g）', 110, 24, 3, 1),
    ('植物蛋白粉', 'others', '1匙（30g）', 110, 22, 4, 2),
    ('BCAA', 'others', '1份', 10, 5, 0, 0),
    ('乳清即飲', 'others', '1瓶', 140, 25, 4, 1),
    ('雞胸餐盒', 'others', '1份', 450, 38, 42, 10),
    ('沙拉（無醬）', 'others', '1份', 80, 4, 10, 2),
    ('油醋醬', 'others', '1匙（15g）', 45, 0, 1, 4.5),
    ('橄欖油', 'others', '1匙（15ml）', 119, 0, 0, 13.5),
    ('味噌湯', 'others', '1碗', 40, 3, 5, 1),
    ('清湯', 'others', '1碗', 15, 1, 2, 0.3),
    ('韓式泡菜', 'others', '50g', 15, 1, 2.5, 0.3),
]


class Command(BaseCommand):
    help = '建立網站選單對應的分類，以及測試用商品（不含圖片）'

    def handle(self, *args, **options):
        categories = self._ensure_categories()
        brands = self._ensure_brands()
        created, updated = self._ensure_products(categories, brands)
        foods_created = self._ensure_foods()
        published = Product.objects.filter(status='published').count()
        self.stdout.write(self.style.SUCCESS(
            f'完成：商品新增 {created}、更新 {updated}；食物新增 {foods_created}。'
            f'目前已上架商品 {published} 件。'
        ))

    def _ensure_categories(self):
        categories = {}
        for data in PARENTS:
            category, created = Category.objects.update_or_create(
                slug=data['slug'],
                defaults={
                    'name': data['name'],
                    'description': data['desc'],
                    'parent': None,
                    'is_active': True,
                    'sort_order': data['order'],
                },
            )
            categories[data['slug']] = category
            self.stdout.write(('建立' if created else '更新') + f'父分類：{category.name}')

        for data in CHILDREN:
            parent = categories[data['parent']]
            category, created = Category.objects.update_or_create(
                slug=data['slug'],
                defaults={
                    'name': data['name'],
                    'description': data['desc'],
                    'parent': parent,
                    'is_active': True,
                    'sort_order': data['order'],
                },
            )
            categories[data['slug']] = category
            self.stdout.write(('建立' if created else '更新') + f'子分類：{parent.name} > {category.name}')
        return categories

    def _ensure_brands(self):
        brands = {}
        for data in BRANDS:
            brand, created = Brand.objects.update_or_create(
                slug=data['slug'],
                defaults={
                    'name': data['name'],
                    'description': data['desc'],
                    'is_active': True,
                },
            )
            brands[data['slug']] = brand
            if created:
                self.stdout.write(f'建立品牌：{brand.name}')
        return brands

    def _ensure_products(self, categories, brands):
        created_count = 0
        updated_count = 0
        now = timezone.now()
        for row in PRODUCTS:
            sku, name, cat_slug, brand_slug, price, original, stock, featured, short, desc = row[:10]
            nutrition = row[10:] if len(row) > 10 else ()
            slug = slugify(sku)
            defaults = {
                'name': name,
                'slug': slug,
                'category': categories[cat_slug],
                'brand': brands[brand_slug],
                'price': Decimal(str(price)),
                'original_price': Decimal(str(original)),
                'stock_quantity': stock,
                'description': desc,
                'short_description': short,
                'status': 'published',
                'is_featured': featured,
                'published_at': now,
                'requires_shipping': True,
            }
            if nutrition:
                calories, protein, carbs, fat = nutrition
                defaults.update({
                    'calories_per_100g': calories,
                    'protein_per_100g': Decimal(str(protein)),
                    'carbs_per_100g': Decimal(str(carbs)),
                    'fat_per_100g': Decimal(str(fat)),
                })
            _product, created = Product.objects.update_or_create(sku=sku, defaults=defaults)
            if created:
                created_count += 1
                self.stdout.write(f'  商品：{name}  NT${price}')
            else:
                updated_count += 1
        return created_count, updated_count

    def _ensure_foods(self):
        created_count = 0
        for name, category, serving, calories, protein, carbs, fat in FOODS:
            _food, created = Food.objects.get_or_create(
                name=name,
                defaults={
                    'category': category,
                    'serving_size': serving,
                    'calories': Decimal(str(calories)),
                    'protein': Decimal(str(protein)),
                    'carbs': Decimal(str(carbs)),
                    'fat': Decimal(str(fat)),
                    'is_active': True,
                },
            )
            if created:
                created_count += 1
                self.stdout.write(f'  食物：{name}')
        return created_count
