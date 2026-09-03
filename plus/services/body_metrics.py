from decimal import Decimal


def calculate_bmi(weight_kg, height_cm):
    if not weight_kg or not height_cm:
        return None
    height_m = Decimal(str(height_cm)) / Decimal('100')
    if height_m <= 0:
        return None
    bmi = Decimal(str(weight_kg)) / (height_m * height_m)
    return bmi.quantize(Decimal('0.1'))


def bmi_category(bmi):
    if bmi is None:
        return '', ''
    value = float(bmi)
    if value < 18.5:
        return 'underweight', '過輕'
    if value < 24:
        return 'normal', '健康'
    if value < 27:
        return 'overweight', '過重'
    return 'obese', '肥胖'


def ideal_weight_range(height_cm):
    """衛福部常用 BMI 18.5–24 對應體重區間。"""
    if not height_cm:
        return None, None
    height_m = Decimal(str(height_cm)) / Decimal('100')
    sq = height_m * height_m
    low = (Decimal('18.5') * sq).quantize(Decimal('0.1'))
    high = (Decimal('24') * sq).quantize(Decimal('0.1'))
    return low, high


def water_target_ml(weight_kg):
    if not weight_kg:
        return None
    return int(Decimal(str(weight_kg)) * Decimal('33'))


def protein_per_kg(weight_kg, goal_type='maintain'):
    if not weight_kg:
        return None
    grams = {
        'lose_weight': Decimal('1.6'),
        'maintain': Decimal('1.4'),
        'gain_weight': Decimal('1.6'),
        'build_muscle': Decimal('2.0'),
    }.get(goal_type, Decimal('1.4'))
    return (Decimal(str(weight_kg)) * grams).quantize(Decimal('0.1'))


def estimate_workout_calories(weight_kg, duration_minutes, met=5):
    if not weight_kg or not duration_minutes:
        return Decimal('0')
    hours = Decimal(str(duration_minutes)) / Decimal('60')
    kcal = Decimal(str(met)) * Decimal(str(weight_kg)) * hours
    return kcal.quantize(Decimal('1'))


def body_metrics_summary(weight_kg, height_cm, goal_type='maintain'):
    bmi = calculate_bmi(weight_kg, height_cm)
    code, label = bmi_category(bmi)
    low, high = ideal_weight_range(height_cm)
    return {
        'bmi': bmi,
        'bmi_code': code,
        'bmi_label': label,
        'ideal_low': low,
        'ideal_high': high,
        'water_ml': water_target_ml(weight_kg),
        'protein_g': protein_per_kg(weight_kg, goal_type),
    }
