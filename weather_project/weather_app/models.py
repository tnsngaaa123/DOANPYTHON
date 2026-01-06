from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class SearchHistory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    city = models.CharField(max_length=100)
    search_time = models.DateTimeField(default=timezone.now)
    
    # 10 chỉ số chi tiết
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
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    avatar = models.ImageField(default='default.jpg', upload_to='profile_pics')

    def __str__(self):
        return f'{self.user.username} Profile'