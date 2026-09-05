import csv
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from plus.models import DailyHealthLog, Food, NutritionLog, UserProfile, WaterLog, WeightLog, WorkoutLog
from plus.services.body_metrics import estimate_workout_calories
from plus.services.nutrition import local_day_range


def bmi_calculator_view(request):
    return redirect('goal_management')


@login_required
def health_export_view(request):
    days = min(int(request.GET.get('days') or 30), 365)
    since = timezone.now() - timedelta(days=days)
    response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
    response['Content-Disposition'] = 'attachment; filename="goodjian-health.csv"'
    writer = csv.writer(response)
    writer.writerow(['類型', '時間', '項目', '數值', '單位', '備註'])

    for log in WeightLog.objects.filter(user=request.user, recorded_at__gte=since):
        writer.writerow(['體重', timezone.localtime(log.recorded_at).strftime('%Y-%m-%d %H:%M'), '體重', log.weight, 'kg', log.notes])

    for log in NutritionLog.objects.filter(user=request.user, logged_at__gte=since).select_related('food'):
        writer.writerow([
            '飲食',
            timezone.localtime(log.logged_at).strftime('%Y-%m-%d %H:%M'),
            log.food.name,
            log.total_calories,
            'kcal',
            log.get_meal_type_display(),
        ])

    for log in WorkoutLog.objects.filter(user=request.user, logged_at__gte=since):
        writer.writerow([
            '運動',
            timezone.localtime(log.logged_at).strftime('%Y-%m-%d %H:%M'),
            log.get_activity_display(),
            log.calories_burned,
            'kcal',
            f'{log.duration_minutes} 分',
        ])

    for log in WaterLog.objects.filter(user=request.user, logged_at__gte=since):
        writer.writerow([
            '飲水',
            timezone.localtime(log.logged_at).strftime('%Y-%m-%d %H:%M'),
            '飲水',
            log.amount_ml,
            'ml',
            '',
        ])
    for log in DailyHealthLog.objects.filter(user=request.user, recorded_date__gte=since.date()):
        values = [
            ('睡眠', log.sleep_hours, '小時'),
            ('步數', log.steps, '步'),
            ('靜止心率', log.resting_heart_rate, 'bpm'),
            ('血壓', log.blood_pressure, 'mmHg'),
            ('心情', log.get_mood_display() if log.mood else None, '1–5'),
            ('精神', log.energy_level, '1–5'),
        ]
        for item, value, unit in values:
            if value is not None:
                writer.writerow(['每日健康', log.recorded_date.isoformat(), item, value, unit, log.notes])
    return response


@login_required
@require_http_methods(['POST'])
def save_daily_health_log_view(request):
    """建立或更新指定日期的每日健康 check-in。"""
    try:
        recorded_date = date.fromisoformat(
            request.POST.get('recorded_date') or timezone.localdate().isoformat()
        )
    except (TypeError, ValueError):
        return JsonResponse({'success': False, 'message': '日期格式不正確'}, status=400)
    if recorded_date > timezone.localdate():
        return JsonResponse({'success': False, 'message': '無法記錄未來日期'}, status=400)

    def optional_decimal(name):
        value = (request.POST.get(name) or '').strip()
        return Decimal(value) if value else None

    def optional_int(name):
        value = (request.POST.get(name) or '').strip()
        return int(value) if value else None

    try:
        log, _created = DailyHealthLog.objects.get_or_create(
            user=request.user,
            recorded_date=recorded_date,
        )
        log.sleep_hours = optional_decimal('sleep_hours')
        log.sleep_quality = optional_int('sleep_quality')
        log.steps = optional_int('steps')
        log.resting_heart_rate = optional_int('resting_heart_rate')
        log.systolic_bp = optional_int('systolic_bp')
        log.diastolic_bp = optional_int('diastolic_bp')
        log.mood = optional_int('mood')
        log.energy_level = optional_int('energy_level')
        log.notes = (request.POST.get('notes') or '').strip()[:500]
        if log.systolic_bp and log.diastolic_bp and log.systolic_bp <= log.diastolic_bp:
            return JsonResponse({'success': False, 'message': '收縮壓應高於舒張壓'}, status=400)
        log.full_clean()
        log.save()
    except (InvalidOperation, TypeError, ValueError, ValidationError) as exc:
        message = '請確認健康數值是否在合理範圍'
        if isinstance(exc, ValidationError) and exc.messages:
            message = exc.messages[0]
        return JsonResponse({'success': False, 'message': message}, status=400)

    return JsonResponse({
        'success': True,
        'message': '今日健康紀錄已儲存',
        'log': {
            'recorded_date': log.recorded_date.isoformat(),
            'sleep_hours': float(log.sleep_hours) if log.sleep_hours is not None else None,
            'steps': log.steps,
            'mood': log.mood,
            'mood_display': log.get_mood_display() if log.mood else None,
            'energy_level': log.energy_level,
            'heart_rate': log.resting_heart_rate,
            'blood_pressure': log.blood_pressure,
        },
    })


@login_required
@require_http_methods(['POST'])
def add_custom_food_view(request):
    name = (request.POST.get('name') or '').strip()
    if not name:
        return JsonResponse({'success': False, 'message': '請輸入食物名稱'})
    try:
        food = Food.objects.create(
            owner=request.user,
            name=name[:200],
            category=request.POST.get('category') or 'others',
            serving_size=(request.POST.get('serving_size') or '100g')[:50],
            calories=Decimal(request.POST.get('calories') or '0'),
            protein=Decimal(request.POST.get('protein') or '0'),
            carbs=Decimal(request.POST.get('carbs') or '0'),
            fat=Decimal(request.POST.get('fat') or '0'),
            fiber=Decimal(request.POST.get('fiber') or '0'),
            sugar=Decimal(request.POST.get('sugar') or '0'),
            sodium=Decimal(request.POST.get('sodium') or '0'),
        )
    except (InvalidOperation, ValueError):
        return JsonResponse({'success': False, 'message': '營養數值格式不正確'})
    return JsonResponse({
        'success': True,
        'message': f'已新增自訂食物「{food.name}」',
        'food': {
            'id': food.id,
            'name': food.name,
            'category': food.get_category_display(),
            'serving_size': food.serving_size,
            'calories': float(food.calories),
            'protein': float(food.protein),
            'carbs': float(food.carbs),
            'fat': float(food.fat),
        },
    })


@login_required
@require_http_methods(['POST'])
def add_workout_log_view(request):
    activity = request.POST.get('activity') or 'other'
    if activity not in dict(WorkoutLog.ACTIVITY_CHOICES):
        activity = 'other'
    try:
        duration = int(request.POST.get('duration_minutes') or 0)
    except (TypeError, ValueError):
        duration = 0
    if duration < 1:
        return JsonResponse({'success': False, 'message': '請輸入運動時間'})
    weight = None
    try:
        weight = request.user.profile.weight
    except UserProfile.DoesNotExist:
        pass
    met = WorkoutLog.MET.get(activity, 4.5)
    calories = int(estimate_workout_calories(weight, duration, met) or 0)
    log = WorkoutLog.objects.create(
        user=request.user,
        activity=activity,
        duration_minutes=duration,
        calories_burned=calories,
        notes=(request.POST.get('notes') or '')[:200],
    )
    return JsonResponse({
        'success': True,
        'message': f'已記錄{log.get_activity_display()} {duration} 分鐘（約 {calories} 大卡）',
        'calories_burned': calories,
    })


@login_required
@require_http_methods(['POST'])
def add_water_log_view(request):
    try:
        amount = int(request.POST.get('amount_ml') or 250)
    except (TypeError, ValueError):
        amount = 250
    if amount < 1 or amount > 3000:
        return JsonResponse({'success': False, 'message': '單次飲水量請介於 1–3000 ml'})
    WaterLog.objects.create(user=request.user, amount_ml=amount)
    _, start, end = local_day_range()
    today_ml = WaterLog.objects.filter(
        user=request.user, logged_at__gte=start, logged_at__lte=end
    ).values_list('amount_ml', flat=True)
    total = sum(today_ml)
    return JsonResponse({
        'success': True,
        'message': f'已記錄 {amount} ml',
        'today_ml': total,
    })


@login_required
@require_http_methods(['POST'])
def log_product_nutrition_view(request):
    from plus.models import Product

    product_id = request.POST.get('product_id')
    try:
        product = Product.objects.get(id=product_id, status='published')
    except (Product.DoesNotExist, ValueError, TypeError):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'message': '商品不存在'})
        messages.error(request, '商品不存在')
        return redirect('products')
    if not product.calories_per_100g:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'message': '此商品尚未標示營養成分'})
        messages.error(request, '此商品尚未標示營養成分')
        return redirect('product_detail', product_id=product.id)
    food, _created = Food.objects.get_or_create(
        owner=request.user,
        name=product.name[:200],
        defaults={
            'category': 'others',
            'serving_size': '100g',
            'calories': product.calories_per_100g,
            'protein': product.protein_per_100g or 0,
            'carbs': product.carbs_per_100g or 0,
            'fat': product.fat_per_100g or 0,
        },
    )
    NutritionLog.objects.create(
        user=request.user,
        food=food,
        quantity=Decimal(request.POST.get('quantity') or '1'),
        meal_type=request.POST.get('meal_type') or 'snack',
        notes=f'來自商品 #{product.id}',
    )
    message = f'已將「{product.name}」加入今日飲食記錄'
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True, 'message': message})
    messages.success(request, message)
    return redirect('goal_management')
