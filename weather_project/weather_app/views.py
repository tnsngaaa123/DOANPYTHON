from prophet import Prophet
from urllib.parse import quote
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required

# --- NHÓM AUTH & SESSION ---
from django.contrib.auth import login, logout, update_session_auth_hash

# --- NHÓM FORMS ---
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm, PasswordChangeForm

# --- NHÓM FORMS CỦA BẠN ---
from .forms import RegisterForm, ProfileUpdateForm, ProfilePicForm

# --- NHÓM MODEL ---
from .models import SearchHistory
from .models import UserProfile

# --- NHÓM TIỆN ÍCH ---
from django.contrib import messages 
from django.http import JsonResponse

# --- NHÓM XỬ LÝ DỮ LIỆU & AI ---
from sklearn.metrics import mean_absolute_error
from sklearn.linear_model import LinearRegression
import requests
import pandas as pd
import numpy as np
from datetime import datetime, date, timedelta # Đã thêm timedelta
import json
import urllib3

# --- CẤU HÌNH ---
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Header giả lập trình duyệt xịn để không bị API chặn
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Referer': 'https://www.google.com/'
}

# --- HÀM TRỢ GIÚP: CHỌN ICON ĐỘNG (Cho Detail View) ---
def get_icon_name(code, is_day):
    """
    Trả về tên icon dựa trên mã thời tiết và trạng thái ngày/đêm.
    is_day: 1 (Ngày), 0 (Đêm)
    """
    suffix = "-day" if is_day == 1 else "-night"
    
    # 0: Clear (Quang đãng)
    if code == 0: return f"clear{suffix}"
    
    # 1: Partly Cloud (Ít mây)
    if code == 1: return f"partly-cloudy{suffix}"
    
    # 2: Cloudy (Có mây) -> Basmilius thường dùng chung icon cloudy, hoặc cloudy-day/night
    if code == 2: return f"partly-cloudy{suffix}" # Hoặc "cloudy" nếu muốn icon mây to hơn
    
    # 3: Overcast (U ám)
    if code == 3: return "overcast" # U ám thì ngày đêm giống nhau (mây đen)
    
    # Sương mù
    if code in [45, 48]: return f"fog{suffix}"
    
    # Mưa phùn
    if code in [51, 53, 55, 56, 57]: return f"drizzle"
    
    # Mưa
    if code in [61, 63, 65, 80, 81, 82]: return f"rain"
    
    # Tuyết
    if code in [71, 73, 75, 77, 85, 86]: return f"snow"
    
    # Dông
    if code in [95, 96, 99]: return f"thunderstorms{suffix}"
    
    return f"partly-cloudy{suffix}"

# Bảng mã thời tiết chuẩn Quốc tế (WMO) dịch sang Tiếng Việt
WMO_CODES = {
    0: "Trời quang đãng", 1: "Chủ yếu là nắng", 2: "Có mây", 3: "U ám (Nhiều mây)",
    45: "Sương mù", 48: "Sương muối",
    51: "Mưa phùn nhẹ", 53: "Mưa phùn", 55: "Mưa phùn dày",
    56: "Mưa phùn lạnh", 57: "Mưa phùn đông kết",
    61: "Mưa nhỏ", 63: "Mưa vừa", 65: "Mưa to",
    66: "Mưa đá nhẹ", 67: "Mưa đá nặng",
    71: "Tuyết nhẹ", 73: "Tuyết vừa", 75: "Tuyết dày",
    77: "Hạt tuyết",
    80: "Mưa rào nhẹ", 81: "Mưa rào", 82: "Mưa rào rất to",
    85: "Tuyết rào nhẹ", 86: "Tuyết rào nặng",
    95: "Dông bão", 96: "Dông kèm mưa đá", 99: "Dông kèm mưa đá to"
}

# =========================================================
# 1. CÁC HÀM HỖ TRỢ (CORE LOGIC)
# =========================================================

def get_city_name_from_coords(lat, lon):
    """ Dịch ngược tọa độ ra Tên (Reverse Geocoding) """
    try:
        url = "https://nominatim.openstreetmap.org/reverse"
        params = {'lat': lat, 'lon': lon, 'format': 'json', 'zoom': 14, 'accept-language': 'vi'}
        res = requests.get(url, params=params, headers=HEADERS, timeout=4, verify=False)
        if res.status_code == 200:
            data = res.json()
            name = data.get('display_name', '')
            if name:
                return ", ".join(name.split(', ')[:3])
    except: pass

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
# 2. VIEW CHÍNH (HOME)
# =========================================================

@login_required(login_url='login')
def home_view(request):
    weather_data = None
    error_msg = None
    
    final_lat, final_lon = 21.0285, 105.8542
    display_name = "Hà Nội, Việt Nam"
    
    city_req = request.POST.get('city') or request.GET.get('city')
    lat_req = request.GET.get('lat')
    lon_req = request.GET.get('lon')
    date_req = request.POST.get('date') or request.GET.get('date')
    
    is_historical = False
    display_date = datetime.now()

    if date_req:
        try:
            req_date_obj = datetime.strptime(date_req, '%Y-%m-%d').date()
            display_date = req_date_obj
            if req_date_obj < datetime.now().date():
                is_historical = True
        except: pass

    should_save = False 

    # --- LOGIC SESSION & TỌA ĐỘ ---
    if lat_req and lon_req:
        request.session['home_city_coords'] = f"{lat_req},{lon_req}"
        if 'home_city_name' in request.session: del request.session['home_city_name']
    elif city_req:
        request.session['home_city_name'] = city_req
        if 'home_city_coords' in request.session: del request.session['home_city_coords']
    else:
        if request.session.get('home_city_coords'):
            lat_req, lon_req = request.session['home_city_coords'].split(',')
        elif request.session.get('home_city_name'):
            city_req = request.session['home_city_name']
        else:
            if request.user.is_authenticated:
                last = SearchHistory.objects.filter(user=request.user).last()
                if last:
                    city_req = last.city
                    request.session['home_city_name'] = city_req

    if lat_req and lon_req:
        try:
            final_lat, final_lon = float(lat_req), float(lon_req)
            has_valid_name = city_req and len(city_req) > 2 and not any(c.isdigit() for c in city_req[:4])
            display_name = city_req if has_valid_name else get_city_name_from_coords(final_lat, final_lon)
            should_save = True
        except: error_msg = "Tọa độ lỗi"
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
            current_hour_idx = datetime.now().hour

            if is_historical:
                # --- API LỊCH SỬ ---
                url = (f"https://archive-api.open-meteo.com/v1/archive?latitude={final_lat}&longitude={final_lon}"
                       f"&start_date={date_req}&end_date={date_req}"
                       f"&hourly=temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,weather_code,cloud_cover,wind_speed_10m,pressure_msl"
                       f"&daily=temperature_2m_max,temperature_2m_min&timezone=auto")
                
                res = requests.get(url, timeout=8, verify=False).json()
                
                if 'hourly' in res:
                    hourly = res['hourly']
                    daily = res.get('daily', {})
                    idx = 12 
                    
                    precip_list = hourly.get('precipitation', [])
                    total_rain_so_far = sum(p for p in precip_list if p is not None)

                    weather_data = {
                        'temp': round(hourly['temperature_2m'][idx]),
                        'humidity': hourly['relative_humidity_2m'][idx],
                        'wind_speed': hourly['wind_speed_10m'][idx],
                        'feels_like': round(hourly['apparent_temperature'][idx]),
                        'rain_display': round(total_rain_so_far, 1), 
                        'pressure': hourly['pressure_msl'][idx],
                        'description': WMO_CODES.get(hourly['weather_code'][idx], "Không có dữ liệu"),
                        'cloud_cover': hourly['cloud_cover'][idx],
                        'uv_index': 0,
                        'min_temp': round(daily['temperature_2m_min'][0]) if 'temperature_2m_min' in daily else 0,
                        'max_temp': round(daily['temperature_2m_max'][0]) if 'temperature_2m_max' in daily else 0,
                    }

            else:
                # --- API HIỆN TẠI (FORECAST) ---
                url = "https://api.open-meteo.com/v1/forecast"
                params = {
                    'latitude': final_lat,
                    'longitude': final_lon,
                    'daily': 'weather_code,temperature_2m_max,temperature_2m_min,uv_index_max',
                    'hourly': 'visibility,precipitation', 
                    'current': 'temperature_2m,relative_humidity_2m,apparent_temperature,is_day,precipitation,rain,showers,weather_code,cloud_cover,pressure_msl,wind_speed_10m',
                    'minutely_15': 'visibility',
                    'timezone': 'auto'
                }
                
                res = requests.get(url, params=params, timeout=8, verify=False).json()
                
                if 'current' in res:
                    curr = res['current']
                    daily = res.get('daily', {})
                    hourly = res.get('hourly', {})

                    total_rain_so_far = 0.0
                    if 'precipitation' in hourly:
                        precip_so_far = hourly['precipitation'][:current_hour_idx + 1]
                        total_rain_so_far = sum(p for p in precip_so_far if p is not None)

                    vis_val = 10000 
                    if 'visibility' in hourly and len(hourly['visibility']) > 0:
                         vis_val = hourly['visibility'][0] 
                    elif 'visibility' in res.get('minutely_15', {}):
                         vis_val = res['minutely_15']['visibility'][0]

                    uv_val = daily['uv_index_max'][0] if 'uv_index_max' in daily and len(daily['uv_index_max']) > 0 else 0

                    weather_data = {
                        'temp': round(curr['temperature_2m']),
                        'humidity': curr['relative_humidity_2m'],
                        'wind_speed': curr['wind_speed_10m'],
                        'feels_like': round(curr['apparent_temperature']),
                        'rain_display': round(total_rain_so_far, 1),
                        'pressure': curr.get('pressure_msl', 1013),
                        'visibility': round(vis_val / 1000, 1) if vis_val is not None else 10.0,
                        'description': WMO_CODES.get(curr.get('weather_code', 0), "Có mây"),
                        'cloud_cover': curr.get('cloud_cover', 0),
                        'uv_index': uv_val,
                        'min_temp': round(daily['temperature_2m_min'][0]) if 'temperature_2m_min' in daily else 0,
                        'max_temp': round(daily['temperature_2m_max'][0]) if 'temperature_2m_max' in daily else 0,
                    }

            if should_save and not is_historical and weather_data:
                if request.user.is_authenticated:
                    SearchHistory.objects.filter(user=request.user, city=display_name).delete()
                    SearchHistory.objects.create(
                        user=request.user, city=display_name,
                        temp=weather_data['temp'], humidity=weather_data['humidity'],
                        wind_speed=weather_data['wind_speed'], pressure=weather_data['pressure'],
                        feels_like=weather_data['feels_like'], description=weather_data['description'],
                        visibility=weather_data['visibility'], uv_index=weather_data['uv_index']
                    )
        except Exception as e:
            print(f"API Error: {e}")
            if should_save: error_msg = "Không thể kết nối máy chủ thời tiết."

    short_city_name = display_name.split(',')[0] if display_name else ""

    context = {
        'current': weather_data,
        'city_name': short_city_name,
        'full_city_name': display_name,
        'city': display_name,
        'map_lat': final_lat,
        'map_lon': final_lon,
        'error': error_msg,
        'today': display_date
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
# 4. VIEW DỰ BÁO (PREDICTION) - ĐÃ CÓ TIMEDELTA
# =========================================================

@login_required(login_url='login')
def prediction_view(request):
    if request.method == 'POST':
        city_input = request.POST.get('city', '').strip()
    else:
        city_input = request.GET.get('city', '').strip()

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
            # Dùng timedelta để lấy dữ liệu 3 năm trước
            end_date_hist = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
            start_date_hist = (datetime.now() - timedelta(days=1095)).strftime('%Y-%m-%d')
            
            url_hist = (f"https://archive-api.open-meteo.com/v1/archive?latitude={lat}&longitude={lon}"
                        f"&start_date={start_date_hist}&end_date={end_date_hist}"
                        f"&daily=temperature_2m_max,rain_sum,wind_speed_10m_max,shortwave_radiation_sum"
                        f"&timezone=auto")
            res_hist = requests.get(url_hist, timeout=8, verify=False).json()
            
            url_future = (f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
                          f"&current=temperature_2m"  
                          f"&daily=temperature_2m_max,temperature_2m_min,rain_sum,wind_speed_10m_max,shortwave_radiation_sum"
                          f"&forecast_days=8&timezone=auto")
            res_future = requests.get(url_future, timeout=8, verify=False).json()

            if 'daily' in res_hist and 'daily' in res_future:
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
                
                current_real_temp = res_future.get('current', {}).get('temperature_2m')
                today_str = datetime.now().strftime('%Y-%m-%d')
                ai_today_row = forecast[forecast['ds'].astype(str) == today_str]
                
                bias_correction = 0
                if not ai_today_row.empty and current_real_temp is not None:
                    ai_today_val = ai_today_row.iloc[0]['yhat']
                    bias_correction = (current_real_temp - ai_today_val) * 0.8
                
                display_forecast = forecast.tail(8).iloc[1:] 
                fut_min_temps = res_future['daily'].get('temperature_2m_min', [])[1:] 

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

# =========================================================
# 5. VIEW CHI TIẾT (DETAIL) - GIAO DIỆN PRO MỚI
# =========================================================
@login_required(login_url='login')
def detail_view(request):
    raw_lat = request.GET.get('lat')
    raw_lon = request.GET.get('lon')
    city = request.GET.get('city', 'Địa điểm')
    date_str = request.GET.get('date') 

    if not raw_lat or not raw_lon:
        return redirect('home')

    lat = raw_lat.replace(',', '.')
    lon = raw_lon.replace(',', '.')

    # 1. Xử lý ngày & Logic chọn API
    if not date_str:
        target_date = date.today()
        date_str = target_date.strftime('%Y-%m-%d')
        is_history = False
    else:
        try:
            target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            
            # --- [SỬA QUAN TRỌNG] ---
            # Chỉ dùng Archive API nếu ngày đó cũ hơn 10 ngày so với hôm nay.
            # Các ngày gần đây (VD: hôm qua, tuần trước) vẫn dùng Forecast API để có đủ UV/Đất.
            cutoff_date = date.today() - timedelta(days=10)
            is_history = target_date < cutoff_date
            
        except ValueError:
            target_date = date.today()
            date_str = target_date.strftime('%Y-%m-%d')
            is_history = False

    # 2. Cấu hình biến API
    hourly_vars_list = [
        "temperature_2m", "relative_humidity_2m", "apparent_temperature",
        "precipitation", "weather_code", "pressure_msl", "cloud_cover", 
        "wind_speed_10m", "uv_index", "soil_moisture_0_to_1cm", "is_day" 
    ]
    hourly_vars_str = ",".join(hourly_vars_list)
    
    base_url = "https://archive-api.open-meteo.com/v1/archive" if is_history else "https://api.open-meteo.com/v1/forecast"
    
    url = (f"{base_url}?latitude={lat}&longitude={lon}"
           f"&start_date={date_str}&end_date={date_str}"
           f"&hourly={hourly_vars_str}&timezone=auto")

    hourly_data = []
    
    try:
        res = requests.get(url, timeout=10, verify=False).json()
        
        if 'hourly' in res:
            h = res['hourly']
            for i in range(len(h['time'])):
                time_val = h['time'][i]
                
                code = h['weather_code'][i]
                is_day = h['is_day'][i] if 'is_day' in h else 1
                if code is None: code = 0

                # Xử lý mô tả: Nếu là ban đêm, đổi "Nắng" thành "Quang đãng"
                desc = WMO_CODES.get(code, "Có mây")
                if is_day == 0: 
                    if code == 0: desc = "Quang đãng (Đêm)"
                    elif code == 1: desc = "Ít mây (Đêm)"
                    else: desc = desc.replace("nắng", "quang đãng").replace("Nắng", "Quang đãng")

                hour_info = {
                    'time': time_val.split('T')[1] if 'T' in time_val else time_val,
                    'temp': h['temperature_2m'][i],
                    'humidity': h['relative_humidity_2m'][i],
                    'feels_like': h['apparent_temperature'][i],
                    'rain': h['precipitation'][i],
                    'wind': h['wind_speed_10m'][i],
                    'cloud': h.get('cloud_cover', [0]*24)[i],
                    
                    # Fix lỗi None data
                    'uv': h.get('uv_index', [0]*24)[i],
                    'soil_moisture': h.get('soil_moisture_0_to_1cm', [0]*24)[i],
                    
                    'description': desc,
                    'code': code,
                    'icon_name': get_icon_name(code, is_day) 
                }
                
                if hour_info['uv'] is None: hour_info['uv'] = 0
                if hour_info['soil_moisture'] is None: hour_info['soil_moisture'] = 0.0

                hourly_data.append(hour_info)
    except Exception as e:
        print(f"Detail API Error: {e}")

    context = {
        'city': city,
        'date': target_date,
        'hourly_data': hourly_data,
        'lat': lat,
        'lon': lon
    }
    
    return render(request, 'detail.html', context)

@login_required
def history_view(request):
    return render(request, 'history.html', {'history': SearchHistory.objects.filter(user=request.user).order_by('-search_time')})

@login_required
def profile_view(request):
    h = SearchHistory.objects.filter(user=request.user)
    last_city = h.last().city.split(',')[0] if h.exists() else "Chưa có"
    user_email = request.user.email if request.user.email else "Chưa cập nhật email"
    
    if request.user.date_joined:
        join_date_str = request.user.date_joined.strftime("%d/%m/%Y")
    else:
        join_date_str = "N/A"

    return render(request, 'profile.html', {
        'total_searches': h.count(), 
        'last_city': last_city,
        'user_email': user_email,
        'user_join_date': join_date_str
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
    profile, created = UserProfile.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        u_form = ProfileUpdateForm(request.POST, instance=request.user)
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

@login_required
def change_password_view(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user) 
            messages.success(request, 'Đổi mật khẩu thành công!')
            return redirect('profile')
        else:
            messages.error(request, 'Vui lòng kiểm tra lại thông tin.')
    else:
        form = PasswordChangeForm(request.user)
        
    return render(request, 'change_password.html', {'form': form})