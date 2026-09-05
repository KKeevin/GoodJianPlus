from django import forms

from plus.models import ShippingAddress, UserProfile


class FitnessProfileForm(forms.ModelForm):
    height = forms.DecimalField(label='身高（cm）', required=False, min_value=50,
                                max_value=250, max_digits=5, decimal_places=2,
                                widget=forms.NumberInput(attrs={'step': '0.01', 'placeholder': '例如：170'}))
    weight = forms.DecimalField(label='體重（kg）', required=False, min_value=20,
                                max_value=300, max_digits=5, decimal_places=2,
                                widget=forms.NumberInput(attrs={'step': '0.01', 'placeholder': '例如：65.5'}))

    class Meta:
        model = UserProfile
        fields = ['gender', 'height', 'weight', 'fitness_goal', 'dietary_restrictions',
                  'emergency_contact', 'emergency_phone']
        widgets = {
            'fitness_goal': forms.TextInput(attrs={'placeholder': '例如：增肌、提升體能、維持運動習慣'}),
            'dietary_restrictions': forms.Textarea(attrs={'rows': 3, 'placeholder': '例如：素食、乳糖不耐；沒有可留白'}),
            'emergency_phone': forms.TextInput(attrs={'type': 'tel'}),
        }


class ShippingAddressForm(forms.ModelForm):
    class Meta:
        model = ShippingAddress
        fields = ['label', 'name', 'phone', 'address', 'is_default']
        labels = {'label': '地址名稱', 'name': '收件人', 'phone': '收件電話',
                  'address': '完整收件地址', 'is_default': '設為預設收件地址'}
        widgets = {
            'label': forms.TextInput(attrs={'placeholder': '例如：住家、公司'}),
            'name': forms.TextInput(attrs={'autocomplete': 'shipping name'}),
            'phone': forms.TextInput(attrs={'type': 'tel', 'autocomplete': 'shipping tel'}),
            'address': forms.Textarea(attrs={'rows': 3, 'autocomplete': 'shipping street-address',
                                            'placeholder': '縣市、區域、路名、門牌與樓層'}),
        }
