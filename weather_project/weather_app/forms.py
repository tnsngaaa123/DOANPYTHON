from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import UserProfile

# --- Form Đăng ký (Giữ nguyên) ---
class RegisterForm(UserCreationForm): 
    email = forms.EmailField(label="Địa chỉ Email", required=True)
    first_name = forms.CharField(label="Tên", required=True) 
    last_name = forms.CharField(label="Họ đệm", required=True) 

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name']

    def save(self, commit=True):
        user = super(RegisterForm, self).save(commit=False)
        user.email = self.cleaned_data["email"]
        user.first_name = self.cleaned_data["first_name"]
        user.last_name = self.cleaned_data["last_name"]
        if commit:
            user.save()
        return user

# --- Form cập nhật User (Tên, Email) - Giữ nguyên ---
class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['last_name', 'first_name', 'email'] 
        
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control glass-input', 'placeholder': 'Tên của bạn'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control glass-input', 'placeholder': 'Họ'}),
            'email': forms.EmailInput(attrs={'class': 'form-control glass-input', 'placeholder': 'Email'}),
        }
        labels = {
            'first_name': 'Tên',
            'last_name': 'Họ đệm',
            'email': 'Địa chỉ Email',
        }

# --- Form cập nhật UserProfile (Avatar + Cảnh báo) - ĐÃ SỬA ---
class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        # Thêm alert_city và receive_alerts vào đây
        fields = ['avatar', 'alert_city', 'receive_alerts']
        
        widgets = {
             'avatar': forms.FileInput(attrs={'class': 'form-control glass-input mt-2'}),
             'alert_city': forms.TextInput(attrs={'class': 'form-control glass-input', 'placeholder': 'VD: Hanoi (Nhập không dấu)'}),
             # Checkbox dùng class của Bootstrap
             'receive_alerts': forms.CheckboxInput(attrs={'class': 'form-check-input ms-2', 'style': 'width: 20px; height: 20px;'}),
        }
        labels = {
             'avatar': 'Ảnh đại diện',
             'alert_city': 'Thành phố nhận cảnh báo',
             'receive_alerts': 'Nhận email cảnh báo thời tiết xấu?',
        }