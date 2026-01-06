from django.contrib import admin
from django.urls import path, include
from django.conf import settings             # <--- Mới thêm: Để lấy cấu hình MEDIA
from django.conf.urls.static import static   # <--- Mới thêm: Để tạo đường dẫn file tĩnh

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('weather_app.urls')),   # Kết nối với app của bạn
]

# --- QUAN TRỌNG: CẤU HÌNH ĐỂ HIỂN THỊ ẢNH UPLOAD ---
# Chỉ chạy khi đang ở chế độ DEBUG (chạy thử trên máy cá nhân)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)