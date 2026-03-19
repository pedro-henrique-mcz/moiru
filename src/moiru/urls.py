# moiru/urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView
from tasks import views as task_views # Importe as views de tasks
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('admin/', admin.site.urls),

    # ROTA HOME (Agora fica na raiz /home/)
    path('home/', task_views.home, name='home'),

    # ROTAS DE CHAMADOS (Ficam em /chamados/...)
    path('chamados/', include('tasks.urls')),

    # CONTAS
    path('', include('accounts.urls')),

    # Redireciona a raiz pura para a home
    path('', RedirectView.as_view(pattern_name='home', permanent=False)),

    path('primeiro-acesso/', task_views.force_password_change, name='force_password_change'),

    # --- RECUPERAÇÃO DE SENHA ---
    path('recuperar-senha/', auth_views.PasswordResetView.as_view(
        template_name='tasks/password_reset.html',
        email_template_name='tasks/password_reset_email.html',
        subject_template_name='tasks/password_reset_subject.txt'
    ), name='password_reset'),
    
    path('recuperar-senha/enviado/', auth_views.PasswordResetDoneView.as_view(
        template_name='tasks/password_reset_done.html'
    ), name='password_reset_done'),
    
    path('recuperar-senha/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='tasks/password_reset_confirm.html'
    ), name='password_reset_confirm'),
    
    path('recuperar-senha/concluido/', auth_views.PasswordResetCompleteView.as_view(
        template_name='tasks/password_reset_complete.html'
    ), name='password_reset_complete'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)