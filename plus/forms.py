from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.core.validators import RegexValidator
from django.contrib.auth.password_validation import validate_password
from .models import CustomUser, UserProfile


class CustomUserRegistrationForm(UserCreationForm):
    """擴展的用戶註冊表單"""
    
    # 基本資訊
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': '請輸入電子郵件',
            'autocomplete': 'email'
        }),
        help_text='我們將使用此信箱發送重要通知'
    )
    
    first_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '請輸入您的姓名',
            'autocomplete': 'given-name'
        }),
        help_text='請輸入真實姓名'
    )
    
    phone = forms.CharField(
        max_length=20,
        required=True,
        validators=[
            RegexValidator(
                regex=r'^09\d{8}$',
                message='請輸入正確的台灣手機號碼格式（例：0912345678）'
            )
        ],
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '0912345678',
            'autocomplete': 'tel'
        })
    )
    
    birthday = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control date-input-enhanced',
            'type': 'date',
            'max': '2010-12-31',  # 限制最小年齡
            'min': '1920-01-01',   # 限制最大年齡
            'style': 'cursor: pointer;',
            'onclick': 'this.showPicker && this.showPicker()'
        }),
        help_text='用於提供個人化的健身建議'
    )
    
    address = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'placeholder': '請輸入完整地址（包含縣市、鄉鎮市區、路段號碼）',
            'rows': 3,
            'autocomplete': 'address-line1'
        })
    )
    
    # 個人資訊
    GENDER_CHOICES = [
        ('', '請選擇性別'),
        ('M', '男性'),
        ('F', '女性'),
        ('O', '不願透露'),
    ]
    
    gender = forms.ChoiceField(
        choices=GENDER_CHOICES,
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-control'
        })
    )
    
    height = forms.IntegerField(
        required=False,
        min_value=100,
        max_value=250,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': '請輸入身高（公分）',
            'min': '100',
            'max': '250'
        }),
        help_text='範圍：100-250 公分'
    )
    
    weight = forms.IntegerField(
        required=False,
        min_value=30,
        max_value=300,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': '請輸入體重（公斤）',
            'min': '30',
            'max': '300'
        }),
        help_text='範圍：30-300 公斤'
    )
    
    fitness_goal = forms.CharField(
        required=False,
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '例如：減重10公斤、增肌、提升體能等'
        }),
        help_text='描述您的健身目標，我們將提供個人化建議'
    )

    class Meta:
        model = CustomUser
        fields = (
            'username', 'email', 'first_name', 'phone', 
            'birthday', 'address', 'password1', 'password2'
        )
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # 自訂表單欄位屬性
        self.fields['username'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': '請輸入使用者名稱',
            'autocomplete': 'username',
            'minlength': '3',
            'maxlength': '20'
        })
        self.fields['username'].help_text = '3-20個字元，只能使用英文、數字和底線'
        
        self.fields['password1'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': '請輸入密碼',
            'autocomplete': 'new-password'
        })
        self.fields['password1'].help_text = '密碼必須至少8個字元，建議包含大小寫字母、數字和特殊符號'
        
        self.fields['password2'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': '請再次輸入密碼',
            'autocomplete': 'new-password'
        })
        self.fields['password2'].help_text = '請再次輸入相同的密碼以確認'

    def clean_email(self):
        """驗證 email 是否已存在"""
        email = self.cleaned_data['email']
        if CustomUser.objects.filter(email=email).exists():
            raise forms.ValidationError('此電子郵件已被註冊，請使用其他信箱或前往登入頁面')
        return email

    def clean_phone(self):
        """驗證手機號碼是否已被其他帳號認證"""
        phone = self.cleaned_data['phone']
        # 檢查該手機號碼是否已被其他帳號認證
        # 如果已被認證，則不允許註冊時使用
        if CustomUser.objects.filter(phone=phone, phone_verified=True).exists():
            raise forms.ValidationError('此手機號碼已被其他帳號認證，無法使用。請使用其他手機號碼。')
        return phone

    def clean_username(self):
        """驗證使用者名稱"""
        username = self.cleaned_data['username']
        
        # 檢查是否包含不當字詞
        forbidden_words = ['admin', 'root', 'administrator', 'goodjian', '管理員']
        if any(word in username.lower() for word in forbidden_words):
            raise forms.ValidationError('使用者名稱包含不允許的字詞')
            
        return username

    def clean_birthday(self):
        """驗證生日"""
        birthday = self.cleaned_data.get('birthday')
        if birthday:
            from datetime import date
            today = date.today()
            age = today.year - birthday.year - ((today.month, today.day) < (birthday.month, birthday.day))
            
            if age < 13:
                raise forms.ValidationError('年齡必須滿13歲才能註冊')
            if age > 100:
                raise forms.ValidationError('請輸入正確的生日')
                
        return birthday

    def save(self, commit=True):
        """保存用戶和個人資料"""
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.phone = self.cleaned_data['phone']
        user.birthday = self.cleaned_data.get('birthday')
        user.address = self.cleaned_data.get('address', '')
        
        if commit:
            user.save()
            
            # 建立或更新用戶資料
            profile, created = UserProfile.objects.get_or_create(user=user)
            profile.gender = self.cleaned_data.get('gender', '')
            profile.height = self.cleaned_data.get('height')
            profile.weight = self.cleaned_data.get('weight')
            profile.fitness_goal = self.cleaned_data.get('fitness_goal', '')
            profile.save()
            
        return user


class QuickRegistrationForm(forms.ModelForm):
    """快速註冊表單（簡化版）"""
    
    password1 = forms.CharField(
        label='密碼',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': '請輸入密碼'
        })
    )
    
    password2 = forms.CharField(
        label='確認密碼',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': '請再次輸入密碼'
        })
    )

    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'first_name', 'phone']
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '使用者名稱'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': '電子郵件'
            }),
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '姓名'
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '手機號碼'
            }),
        }

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("密碼不一致")
        return password2

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
            # 建立基本的用戶資料
            UserProfile.objects.create(user=user)
        return user


class CustomAuthenticationForm(AuthenticationForm):
    """自訂登入表單，支援email或username登入"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': '請輸入使用者名稱或電子郵件',
            'autocomplete': 'username'
        })
        self.fields['password'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': '請輸入密碼',
            'autocomplete': 'current-password'
        })
    
    def clean_username(self):
        username = self.cleaned_data['username']
        if '@' in username:
            try:
                user = CustomUser.objects.get(email=username)
                return user.username
            except CustomUser.DoesNotExist:
                pass
        return username