@echo off
:: Di chuyển thư mục làm việc về đúng chỗ chứa file này
cd /d "%~dp0"

:: Kích hoạt môi trường ảo (Dựa theo đường dẫn trong lỗi bạn gửi lúc nãy)
:: Lệnh này lùi ra 1 cấp thư mục (..) rồi vào venv
call ..\venv\Scripts\activate

:: Mở cửa sổ 1: Chạy Server Web
start "WEBSITE SERVER" python manage.py runserver

:: Mở cửa sổ 2: Chạy Robot Hẹn Giờ
start "ROBOT GUI MAIL" python manage.py run_scheduler

echo Da khoi dong xong
echo Ban co the thu nho cua so nay xuong.
pause