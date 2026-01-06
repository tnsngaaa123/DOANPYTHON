from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import UserProfile # Import thêm cái này

# ======================================================
# 1. FORM ĐĂNG KÝ (Code gốc của bạn - Đã thêm Họ/Tên)
# ======================================================
# Tôi bổ sung thêm first_name và last_name vào đây 
# để khi Đăng ký xong, vào trang Sửa hồ sơ sẽ có dữ liệu luôn.

class RegisterForm(UserCreationForm): 
    email = forms.EmailField(label="Địa chỉ Email", required=True)
    first_name = forms.CharField(label="Tên", required=True) # Thêm mới
    last_name = forms.CharField(label="Họ đệm", required=True) # Thêm mới

    class Meta:
        model = User
        # Thêm first_name, last_name vào danh sách fields
        fields = ['username', 'email', 'first_name', 'last_name']

    # Hàm lưu mở rộng để lưu cả Họ và Tên vào Database
    def save(self, commit=True):
        user = super(RegisterForm, self).save(commit=False)
        user.email = self.cleaned_data["email"]
        user.first_name = self.cleaned_data["first_name"]
        user.last_name = self.cleaned_data["last_name"]
        if commit:
            user.save()
        return user

# ======================================================
# 2. FORM SỬA HỒ SƠ (Phần mới bắt buộc phải có)
# ======================================================
class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        # Cho phép sửa: Họ, Tên, Email
        fields = ['last_name', 'first_name', 'email'] 
        
        # Cấu hình giao diện input trong suốt (Glassmorphism)
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
class ProfilePicForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ['avatar']
        widgets = {
             'avatar': forms.FileInput(attrs={'class': 'form-control glass-input mt-2'}),
        }