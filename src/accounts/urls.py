# accounts/urls.py
from django.urls import path
from django.contrib.auth import views as auth_views
from .views import CustomLoginView # Importando sua view customizada

urlpatterns = [
    # URL: /login/
    path('login/', CustomLoginView.as_view(), name='login'),
    
    # URL: /logout/
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),

    # Recuperação de Senha
    path('reset_password/', auth_views.PasswordResetView.as_view(
        template_name='accounts/password_reset.html'
    ), name='reset_password'),

    path('reset_password_sent/', auth_views.PasswordResetDoneView.as_view(
        template_name='accounts/password_reset_done.html'
    ), name='password_reset_done'),

    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='accounts/password_reset_confirm.html'
    ), name='password_reset_confirm'),

    path('reset_password_complete/', auth_views.PasswordResetCompleteView.as_view(
        template_name='accounts/password_reset_complete.html'
    ), name='password_reset_complete'),
]