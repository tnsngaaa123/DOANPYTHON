from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import UserProfile
# 

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
class ProfilePicForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ['avatar']
        widgets = {
             'avatar': forms.FileInput(attrs={'class': 'form-control glass-input mt-2'}),
        }