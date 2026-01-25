from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth.models import User
from django.utils import timezone
import requests
import urllib3
import time
from datetime import datetime

# Tắt cảnh báo bảo mật API
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class Command(BaseCommand):
    help = 'Module phân tích thiên tai và gửi mail cảnh báo'

    def get_coordinates(self, city_name):
        """Lấy tọa độ từ tên thành phố"""
        try:
            headers = {'User-Agent': 'ExtremeWeatherBot/3.0'}
            url = "https://nominatim.openstreetmap.org/search"
            params = {'q': city_name, 'format': 'json', 'limit': 1}
            res = requests.get(url, params=params, headers=headers, timeout=5)
            if res.status_code == 200 and res.json():
                return float(res.json()[0]['lat']), float(res.json()[0]['lon'])
        except: pass
        return None, None

    def handle(self, *args, **kwargs):
        now_str = timezone.localtime(timezone.now()).strftime('%H:%M:%S')
        users = User.objects.filter(profile__receive_alerts=True).distinct()
        
        if not users.exists():
            return

        for user in users:
            try:
                profile = user.profile
                city = profile.alert_city
                if not city: continue

                lat, lon = self.get_coordinates(city)
                if not lat: continue

                # Gọi API Open-Meteo
                w_url = "https://api.open-meteo.com/v1/forecast"
                w_params = {
                    'latitude': lat, 'longitude': lon,
                    'current': 'temperature_2m,apparent_temperature,precipitation,wind_speed_10m,weather_code,visibility,relative_humidity_2m',
                    'daily': 'uv_index_max,precipitation_sum,sunrise,sunset',
                    'timezone': 'auto'
                }
                resp = requests.get(w_url, params=w_params, verify=False, timeout=10)
                
                if resp.status_code == 200:
                    data = resp.json()
                    curr = data['current']
                    daily = data['daily']
                    
                    # Trích xuất dữ liệu chi tiết
                    temp = curr['temperature_2m']
                    feels_like = curr['apparent_temperature']
                    wind = curr['wind_speed_10m']
                    humidity = curr['relative_humidity_2m']
                    visibility = curr['visibility'] / 1000
                    rain_24h = daily['precipitation_sum'][0]
                    uv = daily['uv_index_max'][0]
                    w_code = curr['weather_code']
                    
                    # Xử lý giờ bình minh/hoàng hôn
                    sunrise = datetime.fromisoformat(daily['sunrise'][0]).strftime('%H:%M')
                    sunset = datetime.fromisoformat(daily['sunset'][0]).strftime('%H:%M')

                    # --- BỘ LỌC CỰC ĐOAN (Chỉ gửi mail nếu có ít nhất 1 dòng ở đây) ---
                    extremes = []
                    if temp >= 38: extremes.append(f"🌡️ Nắng nóng gay gắt ({temp}°C)")
                    if temp <= 2: extremes.append(f"❄️ Cảnh báo băng giá/Rét đậm ({temp}°C)")
                    if feels_like >= 45: extremes.append(f"🔥 Nhiệt độ cảm nhận nguy hiểm ({feels_like}°C)")
                    if feels_like <= -10: extremes.append(f"🥶 Rét hại cực hạn (Cảm giác {feels_like}°C)")
                    if rain_24h >= 80: extremes.append(f"🌊 Nguy cơ ngập lụt/Mưa lớn ({rain_24h}mm)")
                    if wind >= 60: extremes.append(f"🚩 Gió mạnh nguy hiểm ({wind}km/h)")
                    if uv >= 8: extremes.append(f"☀️ Chỉ số UV độc hại mức {uv}")
                    if visibility <= 1: extremes.append(f"🌫️ Tầm nhìn cực thấp ({visibility}km)")
                    if w_code in [95, 96, 99]: extremes.append("⚡ Giông sét cực đoan")

                    # CHỈ GỬI MAIL KHI PHÁT HIỆN CỰC ĐOAN
                    if extremes:
                        subject = f"⚠️ CẢNH BÁO THỜI TIẾT KHẨN CẤP: {city.upper()}"
                        extreme_list = "\n".join([f"   !!! {e}" for e in extremes])
                        
                        msg = (
                            f"Xin chào {user.username},\n\n"
                            f"🚨 PHÁT HIỆN TÌNH TRẠNG THỜI TIẾT NGUY HIỂM TẠI {city.upper()}:\n"
                            f"----------------------------------------\n"
                            f"{extreme_list}\n"
                            f"----------------------------------------\n\n"
                            f"📊 THÔNG SỐ CHI TIẾT:\n"
                            f"   • Nhiệt độ: {temp}°C (Cảm giác: {feels_like}°C)\n"
                            f"   • Sức gió: {wind}km/h | Độ ẩm: {humidity}%\n"
                            f"   • Tầm nhìn: {visibility}km | Chỉ số UV: {uv}\n"
                            f"   • Lượng mưa 24h: {rain_24h}mm\n"
                            f"   • 🌅 Bình minh: {sunrise} | 🌇 Hoàng hôn: {sunset}\n\n"
                            f"📢 KHUYẾN CÁO: Vui lòng chú ý an toàn, hạn chế di chuyển ngoài trời nếu không cần thiết.\n\n"
                            f"Trân trọng,\nWeatherApp Monitoring System."
                        )
                        
                        send_mail(subject, msg, settings.EMAIL_HOST_USER, [user.email])
                        print(f"📧 [{now_str}] ĐÃ GỬI MAIL CẢNH BÁO tới {user.username} ({city})")
                    else:
                        # Ghi log ở terminal để bạn biết nó vẫn đang kiểm tra nhưng không gửi mail
                        print(f"🟢 [{now_str}] {city}: Thời tiết bình thường.")

                time.sleep(1) # Tránh bị chặn API
            except Exception as e:
                print(f"❌ Lỗi xử lý cho {user.username}: {e}")