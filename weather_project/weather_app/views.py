from prophet import Prophet
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required

# --- NHÓM AUTH & SESSION (Đã bổ sung update_session_auth_hash) ---
from django.contrib.auth import login, logout, update_session_auth_hash

# --- NHÓM FORMS (Đã bổ sung PasswordChangeForm) ---
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm, PasswordChangeForm

# --- NHÓM FORMS CỦA BẠN (Đã bổ sung ProfileUpdateForm) ---
from .forms import RegisterForm, ProfileUpdateForm 
from .forms import ProfileUpdateForm, ProfilePicForm # Import form mới

# --- NHÓM MODEL ---
from .models import SearchHistory
from .models import UserProfile # Nhớ import model mới

# --- NHÓM TIỆN ÍCH (Đã bổ sung messages) ---
from django.contrib import messages 
from django.http import JsonResponse

# --- NHÓM XỬ LÝ DỮ LIỆU & AI ---
from sklearn.metrics import mean_absolute_error
from sklearn.linear_model import LinearRegression
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import urllib3

# --- CẤU HÌNH ---
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Header giả lập trình duyệt xịn để không bị API chặn
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Referer': 'https://www.google.com/'
}

# Bảng mã thời tiết chuẩn Quốc tế (WMO) dịch sang Tiếng Việt
WMO_CODES = {
    0: "Trời quang đãng", 1: "Chủ yếu là nắng", 2: "Có mây", 3: "U ám (Nhiều mây)",
    45: "Sương mù", 48: "Sương muối",
    51: "Mưa phùn nhẹ", 53: "Mưa phùn", 55: "Mưa phùn dày",
    61: "Mưa nhỏ", 63: "Mưa vừa", 65: "Mưa to",
    80: "Mưa rào nhẹ", 81: "Mưa rào", 82: "Mưa rào rất to",
    95: "Dông bão", 96: "Dông kèm mưa đá", 99: "Dông kèm mưa đá to"
}

# =========================================================
# 1. CÁC HÀM HỖ TRỢ (CORE LOGIC) - GIỮ NGUYÊN
# =========================================================

def get_city_name_from_coords(lat, lon):
    """
    Dịch ngược tọa độ ra Tên (Reverse Geocoding) - CHỐNG HIỆN SỐ
    """
    # Cách 1: Nominatim (OpenStreetMap)
    try:
        url = "https://nominatim.openstreetmap.org/reverse"
        params = {'lat': lat, 'lon': lon, 'format': 'json', 'zoom': 14, 'accept-language': 'vi'}
        res = requests.get(url, params=params, headers=HEADERS, timeout=4, verify=False)
        if res.status_code == 200:
            data = res.json()
            name = data.get('display_name', '')
            if name:
                # Lấy 3 thành phần đầu cho gọn (VD: Phường, Quận, Thành phố)
                return ", ".join(name.split(', ')[:3])
    except: pass

    # Cách 2: BigDataCloud (Dự phòng cực mạnh nếu Cách 1 lỗi/chậm)
    try:
        url_bk = "https://api.bigdatacloud.net/data/reverse-geocode-client"
        params_bk = {'latitude': lat, 'longitude': lon, 'localityLanguage': 'vi'}
        res_bk = requests.get(url_bk, params=params_bk, timeout=4, verify=False).json()
        parts = []
        if res_bk.get('locality'): parts.append(res_bk['locality'])
        if res_bk.get('city'): parts.append(res_bk['city'])
        if res_bk.get('countryName'): parts.append(res_bk['countryName'])
        if parts: return ", ".join(parts)
    except: pass

    return f"Vị trí: {lat:.3f}, {lon:.3f}"

def get_location_data(query):
    """ Tìm kiếm địa điểm (Global) """
    results = []
    
    # 1. Nominatim
    try:
        url_nom = "https://nominatim.openstreetmap.org/search"
        params_nom = {'q': query, 'format': 'json', 'addressdetails': 1, 'limit': 5, 'accept-language': 'vi'}
        res = requests.get(url_nom, params=params_nom, headers=HEADERS, timeout=4, verify=False)
        if res.status_code == 200:
            for item in res.json():
                results.append({
                    'name': item.get('display_name'),
                    'display_name': item.get('display_name'),
                    'lat': float(item['lat']),
                    'lon': float(item['lon'])
                })
    except: pass

    # 2. Open-Meteo (Dự phòng)
    if not results:
        try:
            url_om = "https://geocoding-api.open-meteo.com/v1/search"
            res = requests.get(url_om, params={'name': query, 'count': 5, 'language': 'vi', 'format': 'json'}, timeout=4, verify=False)
            data = res.json()
            if 'results' in data:
                for item in data['results']:
                    full = f"{item['name']}, {item.get('country', '')}"
                    results.append({
                        'name': full, 'display_name': full,
                        'lat': item['latitude'], 'lon': item['longitude']
                    })
        except: pass

    return results

# =========================================================
# 2. VIEW CHÍNH (HOME) - ĐÃ SỬA LỖI VARIABLE DOES NOT EXIST VÀ SESSION
# =========================================================

@login_required(login_url='login')
def home_view(request):
    weather_data = None
    error_msg = None
    
    # Mặc định: Hà Nội
    final_lat, final_lon = 21.0285, 105.8542
    display_name = "Hà Nội, Việt Nam"
    
    # Lấy request
    city_req = request.POST.get('city') or request.GET.get('city')
    lat_req = request.GET.get('lat')
    lon_req = request.GET.get('lon')
    should_save = False

    # --- LOGIC SESSION (MỚI THÊM) ---
    # Ưu tiên 1: GPS
    if lat_req and lon_req:
        request.session['home_city_coords'] = f"{lat_req},{lon_req}"
        # Xóa tên cũ trong session để ưu tiên tọa độ
        if 'home_city_name' in request.session: del request.session['home_city_name']
    
    # Ưu tiên 2: Tìm kiếm mới
    elif city_req:
        request.session['home_city_name'] = city_req
        if 'home_city_coords' in request.session: del request.session['home_city_coords']

    # Ưu tiên 3: Lấy từ Session (Nếu không thao tác gì)
    else:
        if request.session.get('home_city_coords'):
            lat_req, lon_req = request.session['home_city_coords'].split(',')
        elif request.session.get('home_city_name'):
            city_req = request.session['home_city_name']
        else:
            # Ưu tiên 4: Lấy từ DB (Chỉ khi session trống - Lần đầu login)
            if request.user.is_authenticated:
                last = SearchHistory.objects.filter(user=request.user).last()
                if last:
                    city_req = last.city
                    request.session['home_city_name'] = city_req # Lưu lại luôn

    # --- XỬ LÝ VỊ TRÍ (CODE CŨ) ---
    
    # TH1: Có tọa độ
    if lat_req and lon_req:
        try:
            final_lat, final_lon = float(lat_req), float(lon_req)
            # Kiểm tra tên
            has_valid_name = city_req and len(city_req) > 2 and not any(c.isdigit() for c in city_req[:4])
            if has_valid_name:
                display_name = city_req
            else:
                display_name = get_city_name_from_coords(final_lat, final_lon)
            should_save = True
        except: error_msg = "Tọa độ lỗi"

    # TH2: Có tên
    elif city_req:
        locs = get_location_data(city_req)
        if locs:
            final_lat, final_lon = locs[0]['lat'], locs[0]['lon']
            display_name = locs[0]['name']
            should_save = True
        else:
            error_msg = f"Không tìm thấy: {city_req}"
            display_name = city_req

    # --- GỌI API THỜI TIẾT ---
    if not error_msg:
        try:
            url = f"https://api.open-meteo.com/v1/forecast?latitude={final_lat}&longitude={final_lon}&current=temperature_2m,relative_humidity_2m,apparent_temperature,is_day,precipitation,rain,weather_code,cloud_cover,wind_speed_10m,pressure_msl,visibility&daily=uv_index_max,temperature_2m_max,temperature_2m_min&timezone=auto"
            
            res = requests.get(url, timeout=8, verify=False).json()
            
            if 'current' in res:
                curr = res['current']
                daily = res.get('daily', {})
                
                w_code = curr.get('weather_code', 0)
                desc = WMO_CODES.get(w_code, "Có mây")
                
                vis_val = curr.get('visibility')
                vis_km = round(vis_val / 1000, 1) if vis_val is not None else 10.0
                
                uv_val = 0
                if 'uv_index_max' in daily and len(daily['uv_index_max']) > 0:
                    uv_val = daily['uv_index_max'][0]

                weather_data = {
                    'temp': round(curr['temperature_2m']),
                    'humidity': curr['relative_humidity_2m'],
                    'wind_speed': curr['wind_speed_10m'],
                    'feels_like': round(curr['apparent_temperature']),
                    'rain': curr.get('rain', 0.0),
                    'pressure': curr.get('pressure_msl', 1013),
                    'visibility': vis_km,
                    'description': desc,
                    'cloud_cover': curr.get('cloud_cover', 0),
                    'uv_index': uv_val,
                    # Thêm 2 dòng này để tránh lỗi hiển thị nếu home.html cần
                    'min_temp': round(daily['temperature_2m_min'][0]) if 'temperature_2m_min' in daily else 0,
                    'max_temp': round(daily['temperature_2m_max'][0]) if 'temperature_2m_max' in daily else 0,
                }

                # Chỉ lưu lịch sử khi người dùng CHỦ ĐỘNG tìm kiếm (có request thực)
                if request.GET.get('city') or request.GET.get('lat'):
                    if request.user.is_authenticated:
                        # Xóa cũ lưu mới
                        SearchHistory.objects.filter(user=request.user, city=display_name).delete()
                        SearchHistory.objects.create(
                            user=request.user, city=display_name,
                            temp=weather_data['temp'], humidity=weather_data['humidity'],
                            wind_speed=weather_data['wind_speed'], pressure=weather_data['pressure'],
                            feels_like=weather_data['feels_like'], description=desc,
                            visibility=vis_km, uv_index=uv_val
                        )
        except Exception as e:
            print(f"API Error: {e}")
            if should_save: error_msg = "Không thể kết nối máy chủ thời tiết."

    short_city_name = display_name.split(',')[0] if display_name else ""

    context = {
        'current': weather_data,
        'city_name': short_city_name,  # <--- KHẮC PHỤC LỖI VariableDoesNotExist
        'full_city_name': display_name,
        'city': display_name,          # Dự phòng
        'map_lat': final_lat,
        'map_lon': final_lon,
        'error': error_msg,
        'today': datetime.now()
    }
    return render(request, 'home.html', context)

# =========================================================
# 3. CÁC VIEW KHÁC
# =========================================================

def city_suggest(request):
    q = request.GET.get('q', '').strip()
    if len(q) < 2: return JsonResponse([], safe=False)
    return JsonResponse(get_location_data(q), safe=False)

# =========================================================
# 4. VIEW DỰ BÁO (PREDICTION) - PHIÊN BẢN V6 + BIAS + TOMORROW
# =========================================================

@login_required(login_url='login')
def prediction_view(request):
    """
    PHIÊN BẢN 6.0 FIX: 
    - Độc lập với trang chủ.
    - Dự báo từ ngày mai.
    - Bias Correction (Hiệu chỉnh sai số).
    """
    
    if request.method == 'POST':
        city_input = request.POST.get('city', '').strip()
    else:
        city_input = request.GET.get('city', '').strip()

    # Nếu không nhập gì -> Trả về trang trắng (Không tự lấy lịch sử)
    if not city_input:
        return render(request, 'prediction.html')
    
    locations = get_location_data(city_input)
    display_city_name = city_input.split(',')[0]
    context = {'city_name': display_city_name}
    
    if locations:
        best = locations[0]
        context['city_name'] = best['name'].split(',')[0]
        lat, lon = best['lat'], best['lon']
        
        try:
            # 1. LẤY DỮ LIỆU LỊCH SỬ (3 NĂM)
            end_date_hist = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
            start_date_hist = (datetime.now() - timedelta(days=1095)).strftime('%Y-%m-%d')
            
            url_hist = (f"https://archive-api.open-meteo.com/v1/archive?latitude={lat}&longitude={lon}"
                        f"&start_date={start_date_hist}&end_date={end_date_hist}"
                        f"&daily=temperature_2m_max,rain_sum,wind_speed_10m_max,shortwave_radiation_sum"
                        f"&timezone=auto")
            res_hist = requests.get(url_hist, timeout=8, verify=False).json()
            
            # 2. LẤY DỮ LIỆU TƯƠNG LAI (Lấy 8 ngày)
            url_future = (f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
                          f"&current=temperature_2m"  
                          f"&daily=temperature_2m_max,temperature_2m_min,rain_sum,wind_speed_10m_max,shortwave_radiation_sum"
                          f"&forecast_days=8&timezone=auto")
            res_future = requests.get(url_future, timeout=8, verify=False).json()

            if 'daily' in res_hist and 'daily' in res_future:
                
                # --- A. TRAIN ---
                hist_data = res_hist['daily']
                df = pd.DataFrame({
                    'ds': hist_data['time'],
                    'y': hist_data['temperature_2m_max'],
                    'rain': hist_data['rain_sum'],
                    'wind': hist_data['wind_speed_10m_max'],
                    'sun': hist_data['shortwave_radiation_sum']
                })
                df.fillna(0, inplace=True)

                m = Prophet(
                    daily_seasonality=False,
                    weekly_seasonality=True,
                    yearly_seasonality=True,
                    changepoint_prior_scale=0.1, 
                    seasonality_prior_scale=10.0
                )
                m.add_regressor('rain')
                m.add_regressor('wind')
                m.add_regressor('sun')
                m.fit(df)
                
                # --- B. DỰ BÁO (8 NGÀY) ---
                future = m.make_future_dataframe(periods=8)
                
                def get_regressor(key, hist_s):
                    fut_v = res_future['daily'].get(key, [])
                    avg = sum(hist_s)/len(hist_s) if len(hist_s) > 0 else 0
                    clean = [v if v is not None else avg for v in fut_v]
                    clean = clean[:8] 
                    return hist_s.tolist() + clean

                future['rain'] = get_regressor('rain_sum', df['rain'])[:len(future)]
                future['wind'] = get_regressor('wind_speed_10m_max', df['wind'])[:len(future)]
                future['sun'] = get_regressor('shortwave_radiation_sum', df['sun'])[:len(future)]
                
                forecast = m.predict(future)
                
                # --- C. TÍNH BIAS ---
                current_real_temp = res_future.get('current', {}).get('temperature_2m')
                today_str = datetime.now().strftime('%Y-%m-%d')
                ai_today_row = forecast[forecast['ds'].astype(str) == today_str]
                
                bias_correction = 0
                if not ai_today_row.empty and current_real_temp is not None:
                    ai_today_val = ai_today_row.iloc[0]['yhat']
                    bias_correction = (current_real_temp - ai_today_val) * 0.8
                
                # --- D. LỌC KẾT QUẢ (BỎ HÔM NAY) ---
                display_forecast = forecast.tail(8).iloc[1:] 
                fut_min_temps = res_future['daily'].get('temperature_2m_min', [])[1:] 

                # Tính accuracy
                forecast_hist = m.predict(df)
                mae = mean_absolute_error(df['y'], forecast_hist['yhat'])
                avg_val = df['y'].mean()
                accuracy = round(max(0, min(100, 100 * (1 - mae/abs(avg_val)))), 1)

                preds = []
                lbls, mins, maxs, avgs = [], [], [], []
                
                i = 0
                for index, row in display_forecast.iterrows():
                    d_str = row['ds'].strftime('%d/%m')
                    
                    val_calibrated = row['yhat'] + bias_correction
                    if val_calibrated > 36: val_calibrated = 35
                    val_final = round(val_calibrated, 1)
                    
                    ai_high = row['yhat_upper'] + bias_correction
                    real_min = fut_min_temps[i] if i < len(fut_min_temps) else (row['yhat_lower'] + bias_correction)
                    
                    preds.append({
                        'date': d_str,
                        'range_msg': f"{round(real_min)}°C - {round(ai_high)}°C",
                        'temp': val_final
                    })
                    
                    lbls.append(d_str)
                    mins.append(round(real_min, 1))
                    maxs.append(round(ai_high, 1))
                    avgs.append(val_final)
                    i += 1
                
                context.update({
                    'predictions': preds,
                    'accuracy': accuracy,
                    'mae': round(mae, 2),
                    'chart_data': json.dumps({'labels': lbls, 'min': mins, 'max': maxs, 'avg': avgs}),
                })
                
                if preds:
                    SearchHistory.objects.create(
                        user=request.user, city=best['name'],
                        temp=preds[0]['temp'], humidity=0, wind_speed=0, pressure=0, visibility=0, feels_like=0,
                        description=f"AI Forecast (Bias:{round(bias_correction,1)})"
                    )

        except Exception as e:
            print(f"Error V6: {e}")
            context['error'] = "Đang cập nhật dữ liệu..."
            
    return render(request, 'prediction.html', context)

@login_required
def history_view(request):
    return render(request, 'history.html', {'history': SearchHistory.objects.filter(user=request.user).order_by('-search_time')})

@login_required
def profile_view(request):
    h = SearchHistory.objects.filter(user=request.user)
    last_city = h.last().city.split(',')[0] if h.exists() else "Chưa có"
    
    # --- XỬ LÝ DỮ LIỆU HIỂN THỊ (Fix lỗi không hiện) ---
    # 1. Xử lý Email: Nếu rỗng thì hiện thông báo
    user_email = request.user.email if request.user.email else "Chưa cập nhật email"
    
    # 2. Xử lý Ngày tham gia: Format sang ngày/tháng/năm ngay tại đây
    if request.user.date_joined:
        join_date_str = request.user.date_joined.strftime("%d/%m/%Y")
    else:
        join_date_str = "N/A"

    return render(request, 'profile.html', {
        'total_searches': h.count(), 
        'last_city': last_city,
        'user_email': user_email,       # Biến mới: Đã xử lý
        'user_join_date': join_date_str # Biến mới: Đã xử lý
    })

def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(data=request.POST)
        if form.is_valid(): 
            login(request, form.get_user())
            return redirect('home')
    else: form = AuthenticationForm()
    return render(request, 'login.html', {'form': form})

def register(request):
    if request.method == "POST":
        form = RegisterForm(request.POST) 
        if form.is_valid():
            form.save()
            return redirect("login")
    else:
        form = RegisterForm()
    return render(request, "register.html", {"form": form})

def logout_view(request):
    logout(request)
    return redirect('login')
@login_required
def edit_profile_view(request):
    # Đảm bảo User luôn có Profile (tránh lỗi nếu user cũ chưa có)
    profile, created = UserProfile.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        # Form sửa thông tin (Họ tên, email)
        u_form = ProfileUpdateForm(request.POST, instance=request.user)
        # Form sửa ảnh (Avatar)
        p_form = ProfilePicForm(request.POST, request.FILES, instance=profile)

        if u_form.is_valid() and p_form.is_valid():
            u_form.save()
            p_form.save()
            messages.success(request, 'Hồ sơ của bạn đã được cập nhật!')
            return redirect('profile')
    else:
        u_form = ProfileUpdateForm(instance=request.user)
        p_form = ProfilePicForm(instance=profile)
    
    context = {
        'u_form': u_form,
        'p_form': p_form
    }
    return render(request, 'edit_profile.html', context)

# 2. Hàm Đổi Mật Khẩu
@login_required
def change_password_view(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            # Quan trọng: Cập nhật session để không bị đăng xuất
            update_session_auth_hash(request, user) 
            messages.success(request, 'Đổi mật khẩu thành công!')
            return redirect('profile')
        else:
            messages.error(request, 'Vui lòng kiểm tra lại thông tin.')
    else:
        form = PasswordChangeForm(request.user)
        
    return render(request, 'change_password.html', {'form': form})