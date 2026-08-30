"""
自定義裝飾器
"""
from functools import wraps
from django.shortcuts import render
from django.contrib.auth.decorators import login_required


def verified_required(view_func):
    """
    檢查用戶是否已驗證電子郵件的裝飾器
    如果未驗證，顯示驗證提示頁面
    """
    @wraps(view_func)
    @login_required
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_verified:
            # 根據視圖函數名稱決定功能名稱
            feature_name_map = {
                'goal_management_view': '目標管理',
                'wishlist_view': '我的收藏',
            }
            feature_name = feature_name_map.get(view_func.__name__, '此功能')
            return render(request, 'registration/verification_required.html', {
                'feature_name': feature_name,
                'user_email': request.user.email
            })
        return view_func(request, *args, **kwargs)
    return _wrapped_view

