from decimal import Decimal
from datetime import datetime as dt

from plus.models import DailyNutritionTarget, UserGoal, WeightLog


def calculate_bmr(weight, height, age, gender):
    """計算基礎代謝率（BMR）- 使用 Mifflin-St Jeor 公式"""
    if not all([weight, height, age, gender]):
        return None

    weight = float(weight)
    height = float(height)
    age = int(age)

    if gender == 'male':
        bmr = Decimal('10') * Decimal(str(weight)) + Decimal('6.25') * Decimal(str(height)) - Decimal('5') * Decimal(str(age)) + Decimal('5')
    else:  # female
        bmr = Decimal('10') * Decimal(str(weight)) + Decimal('6.25') * Decimal(str(height)) - Decimal('5') * Decimal(str(age)) - Decimal('161')

    return bmr.quantize(Decimal('0.01'))


def calculate_tdee(bmr, activity_level):
    """計算總每日能量消耗（TDEE）"""
    if not bmr:
        return None

    activity_multipliers = {
        'sedentary': Decimal('1.2'),
        'light': Decimal('1.375'),
        'moderate': Decimal('1.55'),
        'active': Decimal('1.725'),
        'very_active': Decimal('1.9'),
    }

    multiplier = activity_multipliers.get(activity_level, Decimal('1.2'))
    tdee = bmr * multiplier
    return tdee.quantize(Decimal('0.01'))


def calculate_nutrition_targets(tdee, goal_type):
    """計算營養目標（蛋白質、碳水化合物、脂肪）"""
    if not tdee:
        return None, None, None, None

    # 根據目標類型調整熱量
    goal_adjustments = {
        'lose_weight': Decimal('0.85'),  # 減少15%熱量
        'maintain': Decimal('1.0'),
        'gain_weight': Decimal('1.15'),  # 增加15%熱量
        'build_muscle': Decimal('1.1'),  # 增加10%熱量
    }

    target_calories = tdee * goal_adjustments.get(goal_type, Decimal('1.0'))
    target_calories = target_calories.quantize(Decimal('0.01'))

    # 蛋白質：每公斤體重1.6-2.2g（增肌時更高）
    # 這裡使用目標熱量的25-30%作為蛋白質
    if goal_type == 'build_muscle':
        protein_ratio = Decimal('0.30')
    else:
        protein_ratio = Decimal('0.25')

    # 脂肪：目標熱量的25-30%
    fat_ratio = Decimal('0.30')

    # 碳水化合物：剩餘的熱量
    carbs_ratio = Decimal('1') - protein_ratio - fat_ratio

    # 1g 蛋白質 = 4大卡，1g 碳水化合物 = 4大卡，1g 脂肪 = 9大卡
    target_protein = (target_calories * protein_ratio / Decimal('4')).quantize(Decimal('0.01'))
    target_fat = (target_calories * fat_ratio / Decimal('9')).quantize(Decimal('0.01'))
    target_carbs = (target_calories * carbs_ratio / Decimal('4')).quantize(Decimal('0.01'))

    return target_calories, target_protein, target_carbs, target_fat


def get_or_create_daily_nutrition_target(user, target_date):
    """
    獲取或創建指定日期的每日營養目標
    如果該日期沒有目標記錄，則根據該日期最近的體重記錄和目標設定來計算
    """
    try:
        daily_target = DailyNutritionTarget.objects.get(user=user, target_date=target_date)
        return daily_target
    except DailyNutritionTarget.DoesNotExist:
        pass

    try:
        goal = UserGoal.objects.get(user=user)
    except UserGoal.DoesNotExist:
        return None

    weight_log = WeightLog.objects.filter(
        user=user,
        recorded_at__date__lte=target_date
    ).order_by('-recorded_at').first()

    weight = weight_log.weight if weight_log else goal.current_weight
    height = goal.height
    age = goal.age
    gender = goal.gender
    activity_level = goal.activity_level
    goal_type = goal.goal_type

    if not all([weight, height, age, gender]):
        return None

    bmr = calculate_bmr(weight, height, age, gender)
    if not bmr:
        return None

    tdee = calculate_tdee(bmr, activity_level)
    if not tdee:
        return None

    target_calories, target_protein, target_carbs, target_fat = calculate_nutrition_targets(tdee, goal_type)
    if not target_calories:
        return None

    daily_target = DailyNutritionTarget.objects.create(
        user=user,
        target_date=target_date,
        weight=weight,
        height=height,
        age=age,
        gender=gender,
        activity_level=activity_level,
        goal_type=goal_type,
        bmr=bmr,
        tdee=tdee,
        target_calories=target_calories,
        target_protein=target_protein,
        target_carbs=target_carbs,
        target_fat=target_fat,
    )

    return daily_target
