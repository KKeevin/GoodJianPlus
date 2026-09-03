from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from decimal import Decimal
import uuid

from plus.models.users import CustomUser, UserProfile

class Food(models.Model):
    """食物營養資料"""
    CATEGORY_CHOICES = [
        ('grains', '穀物類'),
        ('vegetables', '蔬菜類'),
        ('fruits', '水果類'),
        ('meat', '肉類'),
        ('seafood', '海鮮類'),
        ('dairy', '乳製品'),
        ('nuts', '堅果類'),
        ('beverages', '飲品'),
        ('snacks', '零食'),
        ('others', '其他'),
    ]
    
    name = models.CharField(max_length=200, verbose_name='食物名稱')
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, verbose_name='分類')
    serving_size = models.CharField(max_length=50, default='100g', verbose_name='份量')
    calories = models.DecimalField(max_digits=7, decimal_places=2, verbose_name='熱量（大卡）')
    protein = models.DecimalField(max_digits=7, decimal_places=2, default=0, verbose_name='蛋白質（g）')
    carbs = models.DecimalField(max_digits=7, decimal_places=2, default=0, verbose_name='碳水化合物（g）')
    fat = models.DecimalField(max_digits=7, decimal_places=2, default=0, verbose_name='脂肪（g）')
    fiber = models.DecimalField(max_digits=7, decimal_places=2, default=0, verbose_name='纖維（g）')
    sugar = models.DecimalField(max_digits=7, decimal_places=2, default=0, verbose_name='糖（g）')
    sodium = models.DecimalField(max_digits=7, decimal_places=2, default=0, verbose_name='鈉（mg）')
    is_active = models.BooleanField(default=True, verbose_name='是否啟用')
    owner = models.ForeignKey(
        CustomUser, on_delete=models.CASCADE, null=True, blank=True,
        related_name='custom_foods', verbose_name='自訂者'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='建立時間')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新時間')

    class Meta:
        verbose_name = '食物營養資料'
        verbose_name_plural = '食物營養資料管理'
        ordering = ['category', 'name']

    def __str__(self):
        return f"{self.name} ({self.serving_size})"


class UserGoal(models.Model):
    """用戶目標設定"""
    GOAL_TYPE_CHOICES = [
        ('lose_weight', '減重'),
        ('maintain', '維持體重'),
        ('gain_weight', '增重'),
        ('build_muscle', '增肌'),
    ]
    
    ACTIVITY_LEVEL_CHOICES = [
        ('sedentary', '久坐不動（幾乎不運動）'),
        ('light', '輕度活動（每週1-3天運動）'),
        ('moderate', '中度活動（每週3-5天運動）'),
        ('active', '高度活動（每週6-7天運動）'),
        ('very_active', '極高度活動（每天劇烈運動）'),
    ]
    
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='goal', verbose_name='用戶')
    goal_type = models.CharField(max_length=20, choices=GOAL_TYPE_CHOICES, default='maintain', verbose_name='目標類型')
    target_weight = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, verbose_name='目標體重（kg）')
    age = models.PositiveIntegerField(null=True, blank=True, verbose_name='年齡')
    gender = models.CharField(max_length=10, choices=[('male', '男性'), ('female', '女性')], null=True, blank=True, verbose_name='性別')
    activity_level = models.CharField(max_length=20, choices=ACTIVITY_LEVEL_CHOICES, default='sedentary', verbose_name='活動強度')
    bmr = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True, verbose_name='基礎代謝率（BMR）')
    tdee = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True, verbose_name='總每日能量消耗（TDEE）')
    target_calories = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True, verbose_name='目標熱量（大卡）')
    target_protein = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True, verbose_name='目標蛋白質（g）')
    target_carbs = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True, verbose_name='目標碳水化合物（g）')
    target_fat = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True, verbose_name='目標脂肪（g）')
    # 身體組成目標（佔體重的百分比）
    current_muscle_percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, verbose_name='目前肌肉比例（%）')
    target_muscle_percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, verbose_name='目標肌肉比例（%）')
    current_fat_percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, verbose_name='目前脂肪比例（%）')
    target_fat_percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, verbose_name='目標脂肪比例（%）')
    current_bone_percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, verbose_name='目前骨骼比例（%）')
    target_bone_percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, verbose_name='目標骨骼比例（%）')
    current_water_percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, verbose_name='目前水分比例（%）')
    target_water_percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, verbose_name='目標水分比例（%）')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='建立時間')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新時間')

    class Meta:
        verbose_name = '用戶目標'
        verbose_name_plural = '用戶目標管理'

    def __str__(self):
        return f"{self.user.username} - {self.get_goal_type_display()}"
    
    # 直接從會員資料讀取目前體重和身高（連動）
    @property
    def current_weight(self):
        """目前體重（直接從 UserProfile 讀取）"""
        try:
            profile = self.user.profile
            if profile.weight is not None:
                return profile.weight
        except UserProfile.DoesNotExist:
            pass
        # 如果會員資料沒有，返回 None（不從字段讀取，保持連動）
        return None
    
    @property
    def height(self):
        """身高（直接從 UserProfile 讀取）"""
        try:
            profile = self.user.profile
            if profile.height is not None:
                return profile.height
        except UserProfile.DoesNotExist:
            pass
        # 如果會員資料沒有，返回 None（不從字段讀取，保持連動）
        return None
    
    # 計算目前身體組成重量（kg）
    @property
    def current_muscle_weight(self):
        """目前肌肉重量（kg）"""
        if self.current_weight and self.current_muscle_percentage:
            return (self.current_weight * self.current_muscle_percentage / Decimal('100')).quantize(Decimal('0.1'))
        return None
    
    @property
    def current_fat_weight(self):
        """目前脂肪重量（kg）"""
        if self.current_weight and self.current_fat_percentage:
            return (self.current_weight * self.current_fat_percentage / Decimal('100')).quantize(Decimal('0.1'))
        return None
    
    @property
    def current_bone_weight(self):
        """目前骨骼重量（kg）"""
        if self.current_weight and self.current_bone_percentage:
            return (self.current_weight * self.current_bone_percentage / Decimal('100')).quantize(Decimal('0.1'))
        return None
    
    @property
    def current_water_weight(self):
        """目前水分重量（kg）"""
        if self.current_weight and self.current_water_percentage:
            return (self.current_weight * self.current_water_percentage / Decimal('100')).quantize(Decimal('0.1'))
        return None
    
    # 計算目標身體組成重量（kg）
    @property
    def target_muscle_weight(self):
        """目標肌肉重量（kg）"""
        if self.target_weight and self.target_muscle_percentage:
            return (self.target_weight * self.target_muscle_percentage / Decimal('100')).quantize(Decimal('0.1'))
        return None
    
    @property
    def target_fat_weight(self):
        """目標脂肪重量（kg）"""
        if self.target_weight and self.target_fat_percentage:
            return (self.target_weight * self.target_fat_percentage / Decimal('100')).quantize(Decimal('0.1'))
        return None
    
    @property
    def target_bone_weight(self):
        """目標骨骼重量（kg）"""
        if self.target_weight and self.target_bone_percentage:
            return (self.target_weight * self.target_bone_percentage / Decimal('100')).quantize(Decimal('0.1'))
        return None
    
    @property
    def target_water_weight(self):
        """目標水分重量（kg）"""
        if self.target_weight and self.target_water_percentage:
            return (self.target_weight * self.target_water_percentage / Decimal('100')).quantize(Decimal('0.1'))
        return None


class WeightLog(models.Model):
    """體重記錄"""
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='weight_logs', verbose_name='用戶')
    weight = models.DecimalField(max_digits=5, decimal_places=2, verbose_name='體重（kg）')
    body_fat = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, verbose_name='體脂率（%）')
    muscle_mass = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, verbose_name='肌肉量（kg）')
    # 身體組成數據（佔體重的百分比）
    muscle_percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, verbose_name='肌肉比例（%）')
    fat_percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, verbose_name='脂肪比例（%）')
    bone_percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, verbose_name='骨骼比例（%）')
    water_percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, verbose_name='水分比例（%）')
    notes = models.TextField(blank=True, verbose_name='備註')
    recorded_at = models.DateTimeField(default=timezone.now, verbose_name='記錄時間')

    class Meta:
        verbose_name = '體重記錄'
        verbose_name_plural = '體重記錄管理'
        ordering = ['-recorded_at']

    def __str__(self):
        return f"{self.user.username} - {self.weight}kg ({self.recorded_at.date()})"


class DailyNutritionTarget(models.Model):
    """每日營養目標（記錄每天的營養需求目標）"""
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='daily_nutrition_targets', verbose_name='用戶')
    target_date = models.DateField(verbose_name='目標日期')
    # 當天的體重和設定（用於計算目標）
    weight = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, verbose_name='當天體重（kg）')
    height = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, verbose_name='身高（cm）')
    age = models.PositiveIntegerField(null=True, blank=True, verbose_name='年齡')
    gender = models.CharField(max_length=10, choices=[('male', '男性'), ('female', '女性')], null=True, blank=True, verbose_name='性別')
    activity_level = models.CharField(max_length=20, choices=UserGoal.ACTIVITY_LEVEL_CHOICES, default='sedentary', verbose_name='活動強度')
    goal_type = models.CharField(max_length=20, choices=UserGoal.GOAL_TYPE_CHOICES, default='maintain', verbose_name='目標類型')
    # 計算出的目標值
    target_calories = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True, verbose_name='目標熱量（大卡）')
    target_protein = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True, verbose_name='目標蛋白質（g）')
    target_carbs = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True, verbose_name='目標碳水化合物（g）')
    target_fat = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True, verbose_name='目標脂肪（g）')
    bmr = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True, verbose_name='基礎代謝率（BMR）')
    tdee = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True, verbose_name='總每日能量消耗（TDEE）')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='建立時間')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新時間')
    
    class Meta:
        verbose_name = '每日營養目標'
        verbose_name_plural = '每日營養目標管理'
        unique_together = ['user', 'target_date']  # 每個用戶每天只有一筆目標記錄
        ordering = ['-target_date']
        indexes = [
            models.Index(fields=['user', 'target_date']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.target_date} - {self.target_calories or 0} 大卡"


class NutritionLog(models.Model):
    """營養記錄（每日飲食記錄）"""
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='nutrition_logs', verbose_name='用戶')
    food = models.ForeignKey(Food, on_delete=models.CASCADE, verbose_name='食物')
    quantity = models.DecimalField(max_digits=7, decimal_places=2, default=1, verbose_name='數量（份）')
    meal_type = models.CharField(max_length=20, choices=[
        ('breakfast', '早餐'),
        ('lunch', '午餐'),
        ('dinner', '晚餐'),
        ('snack', '點心'),
    ], verbose_name='餐點類型')
    logged_at = models.DateTimeField(default=timezone.now, verbose_name='記錄時間')
    notes = models.TextField(blank=True, verbose_name='備註')

    class Meta:
        verbose_name = '營養記錄'
        verbose_name_plural = '營養記錄管理'
        ordering = ['-logged_at']

    def __str__(self):
        return f"{self.user.username} - {self.food.name} ({self.logged_at.date()})"
    
    @property
    def total_calories(self):
        """計算總熱量"""
        return (self.food.calories * self.quantity).quantize(Decimal('0.01'))
    
    @property
    def total_protein(self):
        """計算總蛋白質"""
        return (self.food.protein * self.quantity).quantize(Decimal('0.01'))
    
    @property
    def total_carbs(self):
        """計算總碳水化合物"""
        return (self.food.carbs * self.quantity).quantize(Decimal('0.01'))
    
    @property
    def total_fat(self):
        """計算總脂肪"""
        return (self.food.fat * self.quantity).quantize(Decimal('0.01'))

    @property
    def total_fiber(self):
        return (self.food.fiber * self.quantity).quantize(Decimal('0.01'))

    @property
    def total_sugar(self):
        return (self.food.sugar * self.quantity).quantize(Decimal('0.01'))

    @property
    def total_sodium(self):
        return (self.food.sodium * self.quantity).quantize(Decimal('0.01'))


class WorkoutLog(models.Model):
    ACTIVITY_CHOICES = [
        ('walk', '走路／散步'),
        ('run', '跑步'),
        ('cycle', '騎車'),
        ('swim', '游泳'),
        ('weight', '重量訓練'),
        ('yoga', '瑜珈／伸展'),
        ('hiit', 'HIIT'),
        ('other', '其他'),
    ]
    MET = {
        'walk': 3.5,
        'run': 8.0,
        'cycle': 6.8,
        'swim': 7.0,
        'weight': 6.0,
        'yoga': 3.0,
        'hiit': 9.0,
        'other': 4.5,
    }
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='workout_logs', verbose_name='用戶')
    activity = models.CharField(max_length=20, choices=ACTIVITY_CHOICES, verbose_name='活動')
    duration_minutes = models.PositiveIntegerField(verbose_name='時間（分鐘）')
    calories_burned = models.PositiveIntegerField(default=0, verbose_name='消耗熱量')
    notes = models.CharField(max_length=200, blank=True, verbose_name='備註')
    logged_at = models.DateTimeField(default=timezone.now, verbose_name='記錄時間')

    class Meta:
        verbose_name = '運動記錄'
        verbose_name_plural = '運動記錄'
        ordering = ['-logged_at']

    def __str__(self):
        return f'{self.user.username} {self.get_activity_display()} {self.duration_minutes}分'


class WaterLog(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='water_logs', verbose_name='用戶')
    amount_ml = models.PositiveIntegerField(default=250, verbose_name='水量（ml）')
    logged_at = models.DateTimeField(default=timezone.now, verbose_name='記錄時間')

    class Meta:
        verbose_name = '飲水記錄'
        verbose_name_plural = '飲水記錄'
        ordering = ['-logged_at']

    def __str__(self):
        return f'{self.user.username} {self.amount_ml}ml'

