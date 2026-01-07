from django.urls import path
from . import views
from django.contrib.auth import views as auth_views 

urlpatterns = [
    path('', views.home_view, name='home'),             
    path('history/', views.history_view, name='history'), 
    path('prediction/', views.prediction_view, name='prediction'), 
    path('profile/', views.profile_view, name='profile'),
    
    path('login/', views.login_view, name='login'),
    path('register/', views.register, name='register'),
    path('logout/', views.logout_view, name='logout'),
    
    path('suggest/', views.city_suggest, name='city_suggest'),

    path('password_reset/', 
         auth_views.PasswordResetView.as_view(template_name='registration/password_reset_form.html'), 
         name='password_reset'),

    path('password_reset/done/', 
         auth_views.PasswordResetDoneView.as_view(template_name='registration/password_reset_done.html'), 
         name='password_reset_done'),

    path('reset/<uidb64>/<token>/', 
         auth_views.PasswordResetConfirmView.as_view(template_name='registration/password_reset_confirm.html'), 
         name='password_reset_confirm'),

    path('reset/done/', 
         auth_views.PasswordResetCompleteView.as_view(template_name='registration/password_reset_complete.html'), 
         name='password_reset_complete'),
     path('profile/edit/', views.edit_profile_view, name='edit_profile'),
     path('profile/password/', views.change_password_view, name='change_password'),
     path('detail/', views.detail_view, name='detail'),
]