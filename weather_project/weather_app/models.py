from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models.signals import post_save
from django.dispatch import receiver

class SearchHistory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    city = models.CharField(max_length=100)
    search_time = models.DateTimeField(default=timezone.now)
    
    temp = models.FloatField()
    humidity = models.IntegerField()
    wind_speed = models.FloatField()
    pressure = models.FloatField()
    uv_index = models.FloatField(default=0)
    visibility = models.FloatField()
    feels_like = models.FloatField()
    description = models.CharField(max_length=200)
    
    def __str__(self):
        return f"{self.city} - {self.search_time}"

class UserProfile(models.Model):
    # THÊM related_name='profile' ĐỂ DÙNG ĐƯỢC user.profile VỀ SAU
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    alert_city = models.CharField(max_length=100, default="Hanoi", help_text="Thành phố nhận cảnh báo")
    alert_lat = models.FloatField(null=True, blank=True) # Lưu vĩ độ
    alert_lon = models.FloatField(null=True, blank=True) # Lưu kinh độ
    receive_alerts = models.BooleanField(default=True, help_text="Có nhận mail cảnh báo không?")
    
    # Lưu ý: Cần cài thư viện Pillow mới dùng được ImageField
    avatar = models.ImageField(default='default.jpg', upload_to='profile_pics')

    def __str__(self):
        return f'{self.user.username} Profile'

# --- Tín hiệu tự động tạo Profile ---

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        # Sửa lỗi: Phải gọi đúng tên class UserProfile
        UserProfile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    # Dùng try/except để tránh lỗi nếu dữ liệu cũ chưa có profile
    try:
        instance.profile.save()
    except UserProfile.DoesNotExist:
        UserProfile.objects.create(user=instance)