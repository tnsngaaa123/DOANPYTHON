import logging
from django.conf import settings
from django.core.management.base import BaseCommand
from django.core.management import call_command
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from django_apscheduler.jobstores import DjangoJobStore
from django.utils import timezone

logger = logging.getLogger(__name__)

def send_weather_job():
    """Hàm này thực hiện kiểm tra thời tiết"""
    # Dòng "nhịp đập" để bạn biết robot vẫn đang sống trong file .bat
    now = timezone.localtime(timezone.now()).strftime('%H:%M:%S')
    print(f"💓 [{now}] Robot đang kiểm tra dữ liệu thời tiết cực đoan...")
    
    # Gọi lệnh gửi cảnh báo
    call_command('send_alerts')

class Command(BaseCommand):
    help = "Chạy lịch trình giám sát thời tiết cực đoan"

    def handle(self, *args, **options):
        scheduler = BlockingScheduler(timezone=settings.TIME_ZONE)
        scheduler.add_jobstore(DjangoJobStore(), "default")

        # --- QUAN TRỌNG: Xóa sạch các job cũ bị kẹt trong Database ---
        scheduler.remove_all_jobs()

        # Thiết lập chạy mỗi 10 phút (vào các phút :00, :10, :20,...)
        scheduler.add_job(
            send_weather_job,
            trigger=CronTrigger(minute="*/1"), 
            id="UNIQUE_EXTREME_WEATHER_JOB",
            max_instances=1,
            replace_existing=True,
        )

        print("🚀 [HỆ THỐNG ĐÃ SẴN SÀNG]")
        print("📌 Chế độ: Chỉ gửi cảnh báo khi phát hiện dấu hiệu nguy hiểm.")
        print("📌 Tình trạng: Đang chạy ngầm (Sẽ hiện log nhịp đập mỗi 10 phút).")

        try:
            scheduler.start()
        except (KeyboardInterrupt, SystemExit):
            scheduler.shutdown()
            print("\n🛑 Đã dừng Robot.")