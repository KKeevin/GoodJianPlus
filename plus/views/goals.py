from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.db.models import Avg, Q, Sum
from decimal import Decimal
from datetime import timedelta
import logging

from plus.models import (
    DailyHealthLog, DailyNutritionTarget, Food, NutritionLog, Notification,
    UserGoal, UserProfile, WaterLog, WeightLog, WorkoutLog,
)
from plus.decorators import verified_required
from plus.services.nutrition import (
    calculate_bmr, calculate_tdee, calculate_nutrition_targets,
    get_or_create_daily_nutrition_target,
)

logger = logging.getLogger(__name__)

@verified_required
def goal_management_view(request):
    """目標管理主頁面"""
    user = request.user
    
    # 獲取或創建用戶目標
    goal, created = UserGoal.objects.get_or_create(user=user)
    
    # 獲取用戶資料並同步到目標（雙向同步：如果目標數據為空，從會員資料填充）
    try:
        profile = user.profile  # related_name 是 'profile'，不是 'userprofile'
        if profile:
            # 同步身高（如果目標中沒有，從會員資料填充）
            # UserProfile 現在直接存儲為小數
            # 身高／體重已改為從 UserProfile 讀取的 property，不可寫回 UserGoal
            
            # 同步年齡（如果目標中沒有，從生日計算）
            if not goal.age and user.birthday:
                from datetime import date
                today = date.today()
                goal.age = today.year - user.birthday.year - ((today.month, today.day) < (user.birthday.month, user.birthday.day))
            
            # 同步性別（如果目標中沒有，從會員資料填充）
            if not goal.gender and profile.gender:
                # 轉換 UserProfile 的 gender ('M'/'F'/'O') 到 UserGoal 的 gender ('male'/'female')
                gender_map = {'M': 'male', 'F': 'female', 'O': None}
                goal.gender = gender_map.get(profile.gender)
            # 如果目標中有性別但會員資料沒有，同步到會員資料
            elif goal.gender and not profile.gender:
                gender_map = {'male': 'M', 'female': 'F'}
                profile.gender = gender_map.get(goal.gender, '')
            
            # 保存同步後的會員資料
            profile.save()
    except (UserProfile.DoesNotExist, AttributeError):
        profile = None
    
    # 計算 BMR 和 TDEE
    if goal.current_weight and goal.height and goal.age and goal.gender:
        bmr = calculate_bmr(goal.current_weight, goal.height, goal.age, goal.gender)
        if bmr:
            goal.bmr = bmr
            tdee = calculate_tdee(bmr, goal.activity_level)
            if tdee:
                goal.tdee = tdee
                target_calories, target_protein, target_carbs, target_fat = calculate_nutrition_targets(tdee, goal.goal_type)
                if target_calories:
                    goal.target_calories = target_calories
                    goal.target_protein = target_protein
                    goal.target_carbs = target_carbs
                    goal.target_fat = target_fat
                    goal.save()
    
    # 獲取最近的體重記錄（降序，用於列表顯示）
    recent_weight_logs = WeightLog.objects.filter(user=user).order_by('-recorded_at')[:10]
    # 獲取體重記錄（從最新開始，用於圖表顯示，最多10筆）
    # 先獲取最新的10筆（降序），然後反轉為升序以便圖表從左到右顯示
    weight_logs_for_chart = WeightLog.objects.filter(user=user).order_by('-recorded_at')[:10]
    weight_logs_for_chart = list(reversed(weight_logs_for_chart))  # 反轉為升序
    
    # 獲取今天的營養記錄 - 使用本地時區的日期範圍查詢
    from datetime import datetime as dt
    local_now = timezone.localtime(timezone.now())
    today = local_now.date()
    
    # 獲取或創建今天的每日營養目標
    today_target = get_or_create_daily_nutrition_target(user, today)
    
    # 使用日期範圍查詢以確保包含所有記錄
    today_start = timezone.make_aware(dt.combine(today, dt.min.time()))
    today_end = timezone.make_aware(dt.combine(today, dt.max.time()))
    
    today_nutrition_logs = NutritionLog.objects.filter(
        user=user,
        logged_at__gte=today_start,
        logged_at__lte=today_end
    ).select_related('food').order_by('-logged_at')
    
    from plus.services.nutrition import sum_nutrition_logs
    from plus.services.body_metrics import body_metrics_summary
    today_totals = sum_nutrition_logs(today_nutrition_logs)
    body_metrics = body_metrics_summary(
        goal.current_weight, goal.height, goal.goal_type
    )
    today_workouts = WorkoutLog.objects.filter(
        user=user, logged_at__gte=today_start, logged_at__lte=today_end
    )
    today_workout_kcal = sum(w.calories_burned for w in today_workouts)
    today_water_ml = sum(
        WaterLog.objects.filter(
            user=user, logged_at__gte=today_start, logged_at__lte=today_end
        ).values_list('amount_ml', flat=True)
    )

    # 今日整體健康與最近 7 天行動進度
    today_health_log = DailyHealthLog.objects.filter(user=user, recorded_date=today).first()
    week_start = today - timedelta(days=6)
    week_start_dt = timezone.make_aware(dt.combine(week_start, dt.min.time()))
    health_week = DailyHealthLog.objects.filter(
        user=user, recorded_date__gte=week_start, recorded_date__lte=today
    )
    weekly_health = health_week.aggregate(
        avg_sleep=Avg('sleep_hours'),
        avg_steps=Avg('steps'),
    )
    weekly_workout_minutes = WorkoutLog.objects.filter(
        user=user, logged_at__gte=week_start_dt, logged_at__lte=today_end
    ).aggregate(total=Sum('duration_minutes'))['total'] or 0
    water_goal_ml = goal.daily_water_goal_ml or body_metrics.get('water_ml') or 2000
    today_steps = today_health_log.steps if today_health_log and today_health_log.steps is not None else 0
    weekly_progress = {
        'workout_minutes': weekly_workout_minutes,
        'workout_percent': min(100, round(weekly_workout_minutes / max(goal.weekly_workout_goal_minutes, 1) * 100)),
        'avg_sleep': weekly_health['avg_sleep'],
        'sleep_percent': min(100, round(float(weekly_health['avg_sleep'] or 0) / max(float(goal.sleep_goal_hours), 0.1) * 100)),
        'avg_steps': round(weekly_health['avg_steps'] or 0),
        'steps_percent': min(100, round(today_steps / max(goal.daily_steps_goal, 1) * 100)),
        'water_percent': min(100, round(today_water_ml / max(water_goal_ml, 1) * 100)),
        'checkin_days': health_week.count(),
    }

    goal_days_remaining = None
    if goal.target_date:
        goal_days_remaining = (goal.target_date - today).days

    # -------------------------------------------------------------
    # 計算目前體重與目標體重的絕對差距
    # -------------------------------------------------------------
    weight_diff = None
    if goal.current_weight and goal.target_weight:
        weight_diff = abs(goal.current_weight - goal.target_weight)
    
    context = {
        'goal': goal,
        'weight_diff': weight_diff,  # <--- 新增這行傳給 Template
        'recent_weight_logs': recent_weight_logs,
        'weight_logs_for_chart': weight_logs_for_chart,
        'today_nutrition_logs': today_nutrition_logs,
        'today_totals': today_totals,
        'today_target': today_target,  # 今天的營養目標
        'body_metrics': body_metrics,
        'today_workouts': today_workouts,
        'today_workout_kcal': today_workout_kcal,
        'today_water_ml': today_water_ml,
        'workout_choices': WorkoutLog.ACTIVITY_CHOICES,
        'food_categories': Food.CATEGORY_CHOICES,
        'today': today,
        'today_health_log': today_health_log,
        'weekly_progress': weekly_progress,
        'water_goal_ml': water_goal_ml,
        'goal_days_remaining': goal_days_remaining,
        'rating_options': range(1, 6),
        'mood_options': [
            (1, '😞', '低落'),
            (2, '😕', '不太好'),
            (3, '😐', '普通'),
            (4, '🙂', '不錯'),
            (5, '😄', '很好'),
        ],
    }
    return render(request, 'goals/goal_management.html', context)


@login_required
@require_http_methods(["POST"])
def update_goal_view(request):
    """更新用戶目標"""
    try:
        goal, created = UserGoal.objects.get_or_create(user=request.user)
        
        # 獲取會員資料（體重和身高直接從這裡讀取和更新）
        profile, profile_created = UserProfile.objects.get_or_create(user=request.user)
        
        # 保存舊的體重和身高值，用於比較是否有變化（從 UserProfile 讀取）
        old_weight = profile.weight
        old_height = profile.height
        
        # 更新基本資料（體重和身高直接更新到 UserProfile）
        weight_changed = False
        height_changed = False
        
        if request.POST.get('current_weight'):
            new_weight = Decimal(request.POST.get('current_weight'))
            if old_weight is None or new_weight != old_weight:
                profile.weight = new_weight
                weight_changed = True
        
        if request.POST.get('height'):
            new_height = Decimal(request.POST.get('height'))
            if old_height is None or new_height != old_height:
                profile.height = new_height
                height_changed = True
        
        if request.POST.get('target_weight'):
            goal.target_weight = Decimal(request.POST.get('target_weight'))
        if request.POST.get('age'):
            goal.age = int(request.POST.get('age'))
        if request.POST.get('gender'):
            goal.gender = request.POST.get('gender')
        if request.POST.get('activity_level'):
            goal.activity_level = request.POST.get('activity_level')
        if request.POST.get('goal_type'):
            goal.goal_type = request.POST.get('goal_type')

        if request.POST.get('target_date'):
            from datetime import date
            target_date = date.fromisoformat(request.POST.get('target_date'))
            if target_date < timezone.localdate():
                return JsonResponse({'success': False, 'message': '目標日期不能早於今天'})
            goal.target_date = target_date
        elif 'target_date' in request.POST:
            goal.target_date = None

        numeric_goals = {
            'daily_water_goal_ml': (500, 6000),
            'daily_steps_goal': (1000, 50000),
            'weekly_workout_goal_minutes': (10, 3000),
        }
        for field, (minimum, maximum) in numeric_goals.items():
            if request.POST.get(field):
                value = int(request.POST[field])
                if value < minimum or value > maximum:
                    return JsonResponse({'success': False, 'message': f'{goal._meta.get_field(field).verbose_name}超出合理範圍'})
                setattr(goal, field, value)
        if request.POST.get('sleep_goal_hours'):
            sleep_goal = Decimal(request.POST['sleep_goal_hours'])
            if sleep_goal < Decimal('4') or sleep_goal > Decimal('12'):
                return JsonResponse({'success': False, 'message': '睡眠目標請設定在 4–12 小時'})
            goal.sleep_goal_hours = sleep_goal
        
        # 更新身體組成目標
        if request.POST.get('current_muscle_percentage'):
            goal.current_muscle_percentage = Decimal(request.POST.get('current_muscle_percentage'))
        if request.POST.get('target_muscle_percentage'):
            goal.target_muscle_percentage = Decimal(request.POST.get('target_muscle_percentage'))
        if request.POST.get('current_fat_percentage'):
            goal.current_fat_percentage = Decimal(request.POST.get('current_fat_percentage'))
        if request.POST.get('target_fat_percentage'):
            goal.target_fat_percentage = Decimal(request.POST.get('target_fat_percentage'))
        if request.POST.get('current_bone_percentage'):
            goal.current_bone_percentage = Decimal(request.POST.get('current_bone_percentage'))
        if request.POST.get('target_bone_percentage'):
            goal.target_bone_percentage = Decimal(request.POST.get('target_bone_percentage'))
        if request.POST.get('current_water_percentage'):
            goal.current_water_percentage = Decimal(request.POST.get('current_water_percentage'))
        if request.POST.get('target_water_percentage'):
            goal.target_water_percentage = Decimal(request.POST.get('target_water_percentage'))
        
        # 重新計算 BMR 和 TDEE（使用 UserProfile 中的體重和身高）
        if profile.weight and profile.height and goal.age and goal.gender:
            bmr = calculate_bmr(profile.weight, profile.height, goal.age, goal.gender)
            if bmr:
                goal.bmr = bmr
                tdee = calculate_tdee(bmr, goal.activity_level)
                if tdee:
                    goal.tdee = tdee
                    target_calories, target_protein, target_carbs, target_fat = calculate_nutrition_targets(tdee, goal.goal_type)
                    if target_calories:
                        goal.target_calories = target_calories
                        goal.target_protein = target_protein
                        goal.target_carbs = target_carbs
                        goal.target_fat = target_fat
        
        # 保存會員資料（如果體重或身高有變化）
        if weight_changed or height_changed:
            profile.save()
            
            # 創建新的體重記錄（至少需要體重值）
            if profile.weight is not None:
                change_notes = []
                if weight_changed:
                    change_notes.append('體重')
                if height_changed:
                    change_notes.append('身高')
                notes_text = '、'.join(change_notes) + '變更' if change_notes else '資料更新'
                
                WeightLog.objects.create(
                    user=request.user,
                    weight=profile.weight,
                    notes=f'從目標設定更新：{notes_text}'
                )
        
        goal.save()
        
        # 如果更新了影響營養目標的數據（體重、身高、年齡、性別、活動強度、目標類型），重新計算今天的每日營養目標
        from datetime import datetime as dt
        local_now = timezone.localtime(timezone.now())
        today = local_now.date()
        
        # 檢查是否更新了影響營養目標的字段（體重和身高從 UserProfile 讀取）
        weight_updated = weight_changed
        height_updated = height_changed
        age_updated = request.POST.get('age') is not None
        gender_updated = request.POST.get('gender') is not None
        activity_updated = request.POST.get('activity_level') is not None
        goal_type_updated = request.POST.get('goal_type') is not None
        
        if weight_updated or height_updated or age_updated or gender_updated or activity_updated or goal_type_updated:
            # 刪除今天的每日營養目標（如果存在），以便重新計算
            try:
                today_target = DailyNutritionTarget.objects.get(user=request.user, target_date=today)
                today_target.delete()
            except DailyNutritionTarget.DoesNotExist:
                pass
            
            # 重新創建今天的每日營養目標
            get_or_create_daily_nutrition_target(request.user, today)
        
        # 計算身體組成重量
        current_muscle_weight = goal.current_muscle_weight
        current_fat_weight = goal.current_fat_weight
        current_bone_weight = goal.current_bone_weight
        current_water_weight = goal.current_water_weight
        target_muscle_weight = goal.target_muscle_weight
        target_fat_weight = goal.target_fat_weight
        target_bone_weight = goal.target_bone_weight
        target_water_weight = goal.target_water_weight
        
        # 同步更新到會員資料 (UserProfile 和 CustomUser)
        try:
            profile, profile_created = UserProfile.objects.get_or_create(user=request.user)
            user = request.user
            profile_needs_save = False
            user_needs_save = False
            
            # 體重和身高已經直接從 UserProfile 更新，不需要同步
            
            # 同步性別 (UserGoal: 'male'/'female' -> UserProfile: 'M'/'F')
            if goal.gender:
                gender_map = {'male': 'M', 'female': 'F'}
                profile.gender = gender_map.get(goal.gender, '')
                profile_needs_save = True
            
            # 同步年齡到生日 (如果年齡有更新，計算生日)
            if goal.age:
                from datetime import date
                today = date.today()
                # 計算出生年份
                birth_year = today.year - goal.age
                # 如果生日不存在，使用1月1日作為默認日期
                if not user.birthday:
                    user.birthday = date(birth_year, 1, 1)
                    user_needs_save = True
                else:
                    # 如果生日已存在，只更新年份（保持月日不變）
                    new_birthday = date(birth_year, user.birthday.month, user.birthday.day)
                    if new_birthday != user.birthday:
                        user.birthday = new_birthday
                        user_needs_save = True
            
            # 保存更新
            if profile_needs_save:
                profile.save()
            if user_needs_save:
                user.save()
                
            logger.info(f'Synced goal data to profile for user {request.user.id}: height={profile.height}, weight={profile.weight}, gender={profile.gender}')
        except Exception as e:
            logger.error(f'Sync goal to profile error: {str(e)}')
            # 不影響目標更新的成功返回
        
        return JsonResponse({
            'success': True,
            'message': '目標設定已更新',
            'goal': {
                'goal_type': goal.goal_type,
                'goal_type_display': goal.get_goal_type_display(),
                'current_weight': float(goal.current_weight) if goal.current_weight else None,
                'target_weight': float(goal.target_weight) if goal.target_weight else None,
                'height': float(goal.height) if goal.height else None,
                'age': goal.age if goal.age else None,
                'gender': goal.gender if goal.gender else None,
                'activity_level': goal.activity_level,
                'activity_level_display': goal.get_activity_level_display(),
                'bmr': float(goal.bmr) if goal.bmr else None,
                'tdee': float(goal.tdee) if goal.tdee else None,
                'target_calories': float(goal.target_calories) if goal.target_calories else None,
                'target_protein': float(goal.target_protein) if goal.target_protein else None,
                'target_carbs': float(goal.target_carbs) if goal.target_carbs else None,
                'target_fat': float(goal.target_fat) if goal.target_fat else None,
                'target_date': goal.target_date.isoformat() if goal.target_date else None,
                'daily_water_goal_ml': goal.daily_water_goal_ml,
                'daily_steps_goal': goal.daily_steps_goal,
                'weekly_workout_goal_minutes': goal.weekly_workout_goal_minutes,
                'sleep_goal_hours': float(goal.sleep_goal_hours),
                'current_muscle_percentage': float(goal.current_muscle_percentage) if goal.current_muscle_percentage else None,
                'target_muscle_percentage': float(goal.target_muscle_percentage) if goal.target_muscle_percentage else None,
                'current_fat_percentage': float(goal.current_fat_percentage) if goal.current_fat_percentage else None,
                'target_fat_percentage': float(goal.target_fat_percentage) if goal.target_fat_percentage else None,
                'current_bone_percentage': float(goal.current_bone_percentage) if goal.current_bone_percentage else None,
                'target_bone_percentage': float(goal.target_bone_percentage) if goal.target_bone_percentage else None,
                'current_water_percentage': float(goal.current_water_percentage) if goal.current_water_percentage else None,
                'target_water_percentage': float(goal.target_water_percentage) if goal.target_water_percentage else None,
                # 計算出的重量
                'current_muscle_weight': float(current_muscle_weight) if current_muscle_weight else None,
                'current_fat_weight': float(current_fat_weight) if current_fat_weight else None,
                'current_bone_weight': float(current_bone_weight) if current_bone_weight else None,
                'current_water_weight': float(current_water_weight) if current_water_weight else None,
                'target_muscle_weight': float(target_muscle_weight) if target_muscle_weight else None,
                'target_fat_weight': float(target_fat_weight) if target_fat_weight else None,
                'target_bone_weight': float(target_bone_weight) if target_bone_weight else None,
                'target_water_weight': float(target_water_weight) if target_water_weight else None,
            }
        })
    except Exception as e:
        logger.error(f'Update goal error: {str(e)}')
        return JsonResponse({
            'success': False,
            'message': '更新失敗，請稍後再試'
        })


@login_required
@require_http_methods(["POST"])
def add_weight_log_view(request):
    """添加體重記錄"""
    try:
        weight = Decimal(request.POST.get('weight'))
        body_fat = request.POST.get('body_fat')
        muscle_mass = request.POST.get('muscle_mass')
        muscle_percentage = request.POST.get('muscle_percentage')
        fat_percentage = request.POST.get('fat_percentage')
        bone_percentage = request.POST.get('bone_percentage')
        water_percentage = request.POST.get('water_percentage')
        notes = request.POST.get('notes', '')
        
        weight_log = WeightLog.objects.create(
            user=request.user,
            weight=weight,
            body_fat=Decimal(body_fat) if body_fat else None,
            muscle_mass=Decimal(muscle_mass) if muscle_mass else None,
            muscle_percentage=Decimal(muscle_percentage) if muscle_percentage else None,
            fat_percentage=Decimal(fat_percentage) if fat_percentage else None,
            bone_percentage=Decimal(bone_percentage) if bone_percentage else None,
            water_percentage=Decimal(water_percentage) if water_percentage else None,
            notes=notes
        )
        
        # 更新用戶目標的當前體重和身體組成數據
        goal, created = UserGoal.objects.get_or_create(user=request.user)
        # 體重直接更新到 UserProfile（通過 property 連動）
        profile, profile_created = UserProfile.objects.get_or_create(user=request.user)
        profile.weight = weight
        profile.save()
        if muscle_percentage:
            goal.current_muscle_percentage = Decimal(muscle_percentage)
        if fat_percentage:
            goal.current_fat_percentage = Decimal(fat_percentage)
        if bone_percentage:
            goal.current_bone_percentage = Decimal(bone_percentage)
        if water_percentage:
            goal.current_water_percentage = Decimal(water_percentage)
        goal.save()
        
        # 同步更新到會員資料 (UserProfile)
        try:
            profile, profile_created = UserProfile.objects.get_or_create(user=request.user)
            profile.weight = weight
            profile.save()
            logger.info(f'Synced weight from weight log to profile for user {request.user.id}: weight={weight}')
        except Exception as e:
            logger.error(f'Sync weight log to profile error: {str(e)}')
            # 不影響體重記錄創建的成功返回
        
        # 檢查是否達成目標
        goal, _ = UserGoal.objects.get_or_create(user=request.user)
        if goal.target_weight:
            weight_diff = goal.target_weight - weight
            # 如果距離目標體重在0.5kg以內，視為達成目標
            if abs(weight_diff) <= Decimal('0.5'):
                Notification.objects.create(
                    user=request.user,
                    type='goal',
                    title='🎉 恭喜達成體重目標！',
                    message=f'您已達成目標體重！目前體重 {weight}kg，目標體重 {goal.target_weight}kg。繼續保持！'
                )
        
        # 如果記錄的日期是今天，重新計算今天的每日營養目標
        from datetime import datetime as dt
        local_now = timezone.localtime(timezone.now())
        today = local_now.date()
        record_date = timezone.localtime(weight_log.recorded_at).date()
        
        if record_date == today:
            # 刪除今天的每日營養目標（如果存在），以便重新計算
            try:
                today_target = DailyNutritionTarget.objects.get(user=request.user, target_date=today)
                today_target.delete()
            except DailyNutritionTarget.DoesNotExist:
                pass
            
            # 重新創建今天的每日營養目標
            get_or_create_daily_nutrition_target(request.user, today)
        
        return JsonResponse({
            'success': True,
            'message': '體重記錄已添加',
            'weight_log': {
                'id': weight_log.id,
                'weight': float(weight_log.weight),
                'body_fat': float(weight_log.body_fat) if weight_log.body_fat else None,
                'muscle_mass': float(weight_log.muscle_mass) if weight_log.muscle_mass else None,
                'muscle_percentage': float(weight_log.muscle_percentage) if weight_log.muscle_percentage else None,
                'fat_percentage': float(weight_log.fat_percentage) if weight_log.fat_percentage else None,
                'bone_percentage': float(weight_log.bone_percentage) if weight_log.bone_percentage else None,
                'water_percentage': float(weight_log.water_percentage) if weight_log.water_percentage else None,
                'recorded_at': weight_log.recorded_at.strftime('%Y-%m-%d %H:%M'),
            }
        })
    except Exception as e:
        logger.error(f'Add weight log error: {str(e)}')
        return JsonResponse({
            'success': False,
            'message': f'添加體重記錄失敗：{str(e)}'
        }, status=400)


@login_required
def weight_log_api(request):
    """獲取體重記錄 API（支持偏移量）"""
    try:
        # 獲取偏移量參數（從最新記錄開始的偏移量）
        offset = int(request.GET.get('offset', 0))
        limit = 10  # 每次顯示10筆
        
        # 確保 offset 不為負數
        if offset < 0:
            offset = 0
        
        # 獲取總記錄數
        total_count = WeightLog.objects.filter(user=request.user).count()
        
        # 獲取指定範圍的記錄（從最新開始，降序）
        weight_logs = WeightLog.objects.filter(user=request.user).order_by('-recorded_at')[offset:offset + limit]
        
        # 轉換為列表並反轉為升序（用於圖表顯示，最新在右邊）
        weight_logs_list = list(reversed(list(weight_logs)))
        
        # 檢查是否有更舊的記錄
        has_older = offset + limit < total_count
        # 檢查是否有更新的記錄
        has_newer = offset > 0
        
        return JsonResponse({
            'success': True,
            'weight_logs': [
                {
                    'id': log.id,
                    'weight': float(log.weight),
                    'body_fat': float(log.body_fat) if log.body_fat else None,
                    'muscle_mass': float(log.muscle_mass) if log.muscle_mass else None,
                    'muscle_percentage': float(log.muscle_percentage) if log.muscle_percentage else None,
                    'fat_percentage': float(log.fat_percentage) if log.fat_percentage else None,
                    'bone_percentage': float(log.bone_percentage) if log.bone_percentage else None,
                    'water_percentage': float(log.water_percentage) if log.water_percentage else None,
                    'recorded_at': timezone.localtime(log.recorded_at).strftime('%Y-%m-%d %H:%M'),
                    'recorded_at_date': timezone.localtime(log.recorded_at).strftime('%Y-%m-%d'),
                    'recorded_at_short': timezone.localtime(log.recorded_at).strftime('%m/%d'),
                }
                for log in weight_logs_list
            ],
            'offset': offset,
            'has_older': has_older,
            'has_newer': has_newer,
            'total_count': total_count
        })
    except Exception as e:
        logger.error(f'Weight log API error: {str(e)}')
        return JsonResponse({
            'success': False,
            'message': '載入失敗，請稍後再試'
        })


@login_required
def food_search_api(request):
    """食物搜尋API"""
    query = request.GET.get('q', '')
    category = request.GET.get('category', '')
    
    foods = Food.objects.filter(is_active=True)
    if request.user.is_authenticated:
        foods = foods.filter(Q(owner__isnull=True) | Q(owner=request.user))
    else:
        foods = foods.filter(owner__isnull=True)
    
    if query:
        foods = foods.filter(name__icontains=query)
    
    if category:
        foods = foods.filter(category=category)
    
    foods = foods[:50]  # 限制返回50筆
    
    data = []
    for food in foods:
        data.append({
            'id': food.id,
            'name': food.name,
            'category': food.get_category_display(),
            'serving_size': food.serving_size,
            'calories': float(food.calories),
            'protein': float(food.protein),
            'carbs': float(food.carbs),
            'fat': float(food.fat),
            'fiber': float(food.fiber),
            'sugar': float(food.sugar),
            'sodium': float(food.sodium),
        })
    
    return JsonResponse({
        'success': True,
        'foods': data
    })


@login_required
@require_http_methods(["POST"])
def add_nutrition_log_view(request):
    """添加營養記錄"""
    try:
        food_id = request.POST.get('food_id')
        quantity = Decimal(request.POST.get('quantity', '1'))
        meal_type = request.POST.get('meal_type', 'breakfast')
        notes = request.POST.get('notes', '')
        logged_date_str = request.POST.get('logged_date')  # 獲取選擇的日期
        
        food = Food.objects.get(id=food_id, is_active=True)
        
        # 處理記錄時間：如果提供了日期，使用該日期的當前時間；否則使用當前時間
        from datetime import datetime as dt
        local_now = timezone.localtime(timezone.now())
        
        if logged_date_str:
            # 解析選擇的日期
            try:
                selected_date = dt.strptime(logged_date_str, '%Y-%m-%d').date()
                # 使用選擇的日期，但保留當前時間的小時和分鐘
                logged_at = timezone.make_aware(
                    dt.combine(selected_date, local_now.time())
                )
            except (ValueError, TypeError):
                # 如果日期格式錯誤，使用當前時間
                logged_at = local_now
        else:
            # 如果沒有提供日期，使用當前時間
            logged_at = local_now
        
        nutrition_log = NutritionLog.objects.create(
            user=request.user,
            food=food,
            quantity=quantity,
            meal_type=meal_type,
            notes=notes,
            logged_at=logged_at  # 設置記錄時間
        )
        
        # 確保記錄已保存
        nutrition_log.refresh_from_db()
        
        # 獲取記錄日期的營養記錄和總計 - 使用記錄的日期
        record_date = timezone.localtime(nutrition_log.logged_at).date()
        
        # 查詢記錄日期的記錄，使用日期範圍查詢以確保包含所有記錄
        record_start = timezone.make_aware(dt.combine(record_date, dt.min.time()))
        record_end = timezone.make_aware(dt.combine(record_date, dt.max.time()))
        
        record_nutrition_logs = NutritionLog.objects.filter(
            user=request.user,
            logged_at__gte=record_start,
            logged_at__lte=record_end
        ).order_by('-logged_at')
        
        # 計算記錄日期的總營養攝取
        record_totals = {
            'calories': Decimal('0'),
            'protein': Decimal('0'),
            'carbs': Decimal('0'),
            'fat': Decimal('0'),
        }
        for log in record_nutrition_logs:
            record_totals['calories'] += log.total_calories
            record_totals['protein'] += log.total_protein
            record_totals['carbs'] += log.total_carbs
            record_totals['fat'] += log.total_fat
        
        # 檢查是否達成營養目標
        try:
            daily_target = DailyNutritionTarget.objects.get(user=request.user, target_date=record_date)
            # 如果達成熱量目標（在目標的90%-110%範圍內）
            if daily_target.target_calories:
                calories_ratio = record_totals['calories'] / daily_target.target_calories
                if 0.9 <= calories_ratio <= 1.1:
                    Notification.objects.create(
                        user=request.user,
                        type='goal',
                        title='🎉 達成熱量目標！',
                        message=f'恭喜！您今天已達成熱量目標（{float(record_totals["calories"]):.0f} / {float(daily_target.target_calories):.0f} 大卡）。繼續保持！'
                    )
        except DailyNutritionTarget.DoesNotExist:
            pass
        
        # 構建所有記錄的數據
        logs_data = []
        for log in record_nutrition_logs:
            logs_data.append({
                'id': log.id,
                'food_name': log.food.name,
                'food_id': log.food.id,
                'quantity': float(log.quantity),
                'meal_type': log.meal_type,
                'meal_type_display': log.get_meal_type_display(),
                'calories': float(log.total_calories),
                'protein': float(log.total_protein),
                'carbs': float(log.total_carbs),
                'fat': float(log.total_fat),
                'notes': log.notes,
                'logged_at': timezone.localtime(log.logged_at).strftime('%H:%M'),
            })
        
        return JsonResponse({
            'success': True,
            'message': '營養記錄已添加',
            'nutrition_log': {
                'id': nutrition_log.id,
                'food_name': food.name,
                'quantity': float(quantity),
                'meal_type': nutrition_log.get_meal_type_display(),
                'calories': float(nutrition_log.total_calories),
                'protein': float(nutrition_log.total_protein),
                'carbs': float(nutrition_log.total_carbs),
                'fat': float(nutrition_log.total_fat),
                'logged_at': timezone.localtime(nutrition_log.logged_at).strftime('%H:%M'),
            },
            'today_totals': {
                'calories': float(record_totals['calories']),
                'protein': float(record_totals['protein']),
                'carbs': float(record_totals['carbs']),
                'fat': float(record_totals['fat']),
            },
            'logs': logs_data
        })
    except Food.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': '食物不存在'
        })
    except Exception as e:
        logger.error(f'Add nutrition log error: {str(e)}')
        return JsonResponse({
            'success': False,
            'message': '添加失敗，請稍後再試'
        })


@login_required
@require_http_methods(["POST"])
def update_nutrition_log_view(request, log_id):
    """更新營養記錄"""
    try:
        nutrition_log = NutritionLog.objects.get(id=log_id, user=request.user)
        
        quantity = request.POST.get('quantity')
        meal_type = request.POST.get('meal_type')
        notes = request.POST.get('notes', '')
        
        if quantity:
            nutrition_log.quantity = Decimal(quantity)
        if meal_type:
            nutrition_log.meal_type = meal_type
        if notes is not None:
            nutrition_log.notes = notes
        
        nutrition_log.save()
        
        # 獲取記錄日期的營養記錄和總計 - 使用記錄的日期
        from datetime import datetime as dt
        record_date = timezone.localtime(nutrition_log.logged_at).date()
        
        # 獲取或創建該日期的每日營養目標
        daily_target = get_or_create_daily_nutrition_target(request.user, record_date)
        
        record_start = timezone.make_aware(dt.combine(record_date, dt.min.time()))
        record_end = timezone.make_aware(dt.combine(record_date, dt.max.time()))
        
        record_nutrition_logs = NutritionLog.objects.filter(
            user=request.user,
            logged_at__gte=record_start,
            logged_at__lte=record_end
        ).order_by('-logged_at')
        
        # 計算記錄日期的總營養攝取
        record_totals = {
            'calories': Decimal('0'),
            'protein': Decimal('0'),
            'carbs': Decimal('0'),
            'fat': Decimal('0'),
        }
        for log in record_nutrition_logs:
            record_totals['calories'] += log.total_calories
            record_totals['protein'] += log.total_protein
            record_totals['carbs'] += log.total_carbs
            record_totals['fat'] += log.total_fat
        
        # 構建所有記錄的數據
        logs_data = []
        for log in record_nutrition_logs:
            logs_data.append({
                'id': log.id,
                'food_name': log.food.name,
                'food_id': log.food.id,
                'quantity': float(log.quantity),
                'meal_type': log.meal_type,
                'meal_type_display': log.get_meal_type_display(),
                'calories': float(log.total_calories),
                'protein': float(log.total_protein),
                'carbs': float(log.total_carbs),
                'fat': float(log.total_fat),
                'notes': log.notes,
                'logged_at': timezone.localtime(log.logged_at).strftime('%H:%M'),
            })
        
        # 構建目標數據
        target_data = None
        if daily_target:
            target_data = {
                'calories': float(daily_target.target_calories) if daily_target.target_calories else None,
                'protein': float(daily_target.target_protein) if daily_target.target_protein else None,
                'carbs': float(daily_target.target_carbs) if daily_target.target_carbs else None,
                'fat': float(daily_target.target_fat) if daily_target.target_fat else None,
            }
        
        return JsonResponse({
            'success': True,
            'message': '營養記錄已更新',
            'today_totals': {
                'calories': float(record_totals['calories']),
                'protein': float(record_totals['protein']),
                'carbs': float(record_totals['carbs']),
                'fat': float(record_totals['fat']),
            },
            'targets': target_data,  # 該日期的營養目標
            'logs': logs_data
        })
    except NutritionLog.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': '記錄不存在'
        })
    except Exception as e:
        logger.error(f'Update nutrition log error: {str(e)}')
        return JsonResponse({
            'success': False,
            'message': '更新失敗，請稍後再試'
        })


@login_required
@require_http_methods(["POST"])
def delete_nutrition_log_view(request, log_id):
    """刪除營養記錄"""
    try:
        log = NutritionLog.objects.get(id=log_id, user=request.user)
        food_name = log.food.name
        record_date = timezone.localtime(log.logged_at).date()  # 保存記錄日期
        log.delete()
        
        # 獲取或創建該日期的每日營養目標
        daily_target = get_or_create_daily_nutrition_target(request.user, record_date)
        
        # 獲取記錄日期的營養記錄和總計 - 使用記錄的日期
        from datetime import datetime as dt
        
        # 查詢記錄日期的記錄，使用日期範圍查詢
        record_start = timezone.make_aware(dt.combine(record_date, dt.min.time()))
        record_end = timezone.make_aware(dt.combine(record_date, dt.max.time()))
        
        record_nutrition_logs = NutritionLog.objects.filter(
            user=request.user,
            logged_at__gte=record_start,
            logged_at__lte=record_end
        ).order_by('-logged_at')
        
        # 計算記錄日期的總營養攝取
        record_totals = {
            'calories': Decimal('0'),
            'protein': Decimal('0'),
            'carbs': Decimal('0'),
            'fat': Decimal('0'),
        }
        for nutrition_log in record_nutrition_logs:
            record_totals['calories'] += nutrition_log.total_calories
            record_totals['protein'] += nutrition_log.total_protein
            record_totals['carbs'] += nutrition_log.total_carbs
            record_totals['fat'] += nutrition_log.total_fat
        
        # 構建所有記錄的數據
        logs_data = []
        for nutrition_log in record_nutrition_logs:
            logs_data.append({
                'id': nutrition_log.id,
                'food_name': nutrition_log.food.name,
                'food_id': nutrition_log.food.id,
                'quantity': float(nutrition_log.quantity),
                'meal_type': nutrition_log.meal_type,
                'meal_type_display': nutrition_log.get_meal_type_display(),
                'calories': float(nutrition_log.total_calories),
                'protein': float(nutrition_log.total_protein),
                'carbs': float(nutrition_log.total_carbs),
                'fat': float(nutrition_log.total_fat),
                'notes': nutrition_log.notes,
                'logged_at': timezone.localtime(nutrition_log.logged_at).strftime('%H:%M'),
            })
        
        # 構建目標數據
        target_data = None
        if daily_target:
            target_data = {
                'calories': float(daily_target.target_calories) if daily_target.target_calories else None,
                'protein': float(daily_target.target_protein) if daily_target.target_protein else None,
                'carbs': float(daily_target.target_carbs) if daily_target.target_carbs else None,
                'fat': float(daily_target.target_fat) if daily_target.target_fat else None,
            }
        
        return JsonResponse({
            'success': True,
            'message': f'已刪除 {food_name} 記錄',
            'today_totals': {
                'calories': float(record_totals['calories']),
                'protein': float(record_totals['protein']),
                'carbs': float(record_totals['carbs']),
                'fat': float(record_totals['fat']),
            },
            'targets': target_data,  # 該日期的營養目標
            'logs': logs_data
        })
    except NutritionLog.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': '記錄不存在'
        })
    except Exception as e:
        logger.error(f'Delete nutrition log error: {str(e)}')
        return JsonResponse({
            'success': False,
            'message': '刪除失敗，請稍後再試'
        })


@login_required
def nutrition_log_api(request):
    """獲取營養記錄API"""
    from datetime import datetime as dt
    date_str = request.GET.get('date')
    if date_str:
        try:
            target_date = dt.strptime(date_str, '%Y-%m-%d').date()
        except:
            local_now = timezone.localtime(timezone.now())
            target_date = local_now.date()
    else:
        local_now = timezone.localtime(timezone.now())
        target_date = local_now.date()
    
    # 獲取或創建該日期的每日營養目標
    daily_target = get_or_create_daily_nutrition_target(request.user, target_date)
    
    # 使用日期範圍查詢
    target_start = timezone.make_aware(dt.combine(target_date, dt.min.time()))
    target_end = timezone.make_aware(dt.combine(target_date, dt.max.time()))
    
    logs = NutritionLog.objects.filter(
        user=request.user,
        logged_at__gte=target_start,
        logged_at__lte=target_end
    ).order_by('-logged_at')
    
    totals = {
        'calories': Decimal('0'),
        'protein': Decimal('0'),
        'carbs': Decimal('0'),
        'fat': Decimal('0'),
    }
    
    data = []
    for log in logs:
        totals['calories'] += log.total_calories
        totals['protein'] += log.total_protein
        totals['carbs'] += log.total_carbs
        totals['fat'] += log.total_fat
        
        data.append({
            'id': log.id,
            'food_name': log.food.name,
            'food_id': log.food.id,
            'quantity': float(log.quantity),
            'meal_type': log.meal_type,
            'meal_type_display': log.get_meal_type_display(),
            'calories': float(log.total_calories),
            'protein': float(log.total_protein),
            'carbs': float(log.total_carbs),
            'fat': float(log.total_fat),
            'notes': log.notes,
            'logged_at': timezone.localtime(log.logged_at).strftime('%H:%M'),
        })
    
    # 構建目標數據
    target_data = None
    if daily_target:
        target_data = {
            'calories': float(daily_target.target_calories) if daily_target.target_calories else None,
            'protein': float(daily_target.target_protein) if daily_target.target_protein else None,
            'carbs': float(daily_target.target_carbs) if daily_target.target_carbs else None,
            'fat': float(daily_target.target_fat) if daily_target.target_fat else None,
        }
    
    return JsonResponse({
        'success': True,
        'date': target_date.strftime('%Y-%m-%d'),
        'logs': data,
        'totals': {
            'calories': float(totals['calories']),
            'protein': float(totals['protein']),
            'carbs': float(totals['carbs']),
            'fat': float(totals['fat']),
        },
        'targets': target_data  # 該日期的營養目標
    })
