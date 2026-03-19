# tasks/urls.py
from django.urls import path
from . import views

urlpatterns = [
    # --- DASHBOARD E LISTAGEM ---
    path('', views.dashboard, name='dashboard'),
    path('lista/', views.dashboard), 

    # --- CHAMADOS (OPERAÇÃO) ---
    path('novo/', views.create_ticket, name='create_ticket'),
    path('ticket/<int:ticket_id>/', views.ticket_detail, name='ticket_detail'),
    path('ticket/<int:ticket_id>/editar/', views.edit_ticket, name='edit_ticket'),
    path('ticket/<int:ticket_id>/excluir/', views.delete_ticket, name='delete_ticket'),
    path('ticket/<int:ticket_id>/comentar/', views.add_followup, name='add_followup'),
    path('ticket/<int:ticket_id>/reopen/', views.reopen_ticket, name='reopen_ticket'),
    path('ticket/<int:ticket_id>/os/', views.generate_os, name='generate_os'),

    # --- AJAX E CARREGAMENTO DINÂMICO ---
    path('ajax/load-users/', views.load_users_by_dept, name='ajax_load_users'),
    path('ajax/load-envs/', views.load_envs_by_unit, name='ajax_load_envs'),

    # --- ÁREA ADMINISTRATIVA (GESTÃO CENTRALIZADA) ---
    path('painel-admin/', views.admin_panel, name='admin_panel'),

    # Gestão de Unidades
    path('gestao/unidades/', views.admin_unit_list, name='admin_unit_list'),
    path('gestao/unidades/novo/', views.admin_add_unit, name='admin_add_unit'),
    path('gestao/unidades/<int:unit_id>/', views.admin_unit_manage, name='admin_unit_manage'),
    path('gestao/unidades/<int:unit_id>/editar/', views.admin_edit_unit, name='admin_edit_unit'),

    # Gestão de Ambientes
    path('gestao/unidades/<int:unit_id>/ambientes/novo/', views.admin_add_environment, name='admin_add_environment'),
    path('gestao/ambientes/<int:env_id>/toggle/', views.admin_toggle_environment_active, name='admin_toggle_environment_active'),
    path('gestao/ambientes/<int:env_id>/editar/', views.admin_edit_environment, name='admin_edit_environment'),

    # Gestão de Departamentos / Setores
    path('admin-panel/departamentos/', views.admin_department_list, name='admin_department_list'),
    path('admin-panel/departamentos/<int:dept_id>/editar/', views.admin_edit_department, name='admin_edit_department'),
    
    # Gestão de Pessoas
    path('admin-panel/pessoas/', views.admin_user_list, name='admin_user_list'),
    path('admin-panel/pessoas/<int:user_id>/editar/', views.admin_edit_user, name='admin_edit_user'),

    # ==========================================
    # NOVAS ROTAS ADICIONADAS (ITENS E AÇÕES)
    # ==========================================
    path('admin-panel/itens/', views.admin_item_list, name='admin_item_list'),
    path('admin-panel/itens/editar/<int:item_id>/', views.admin_edit_item, name='admin_edit_item'),
    
    path('admin-panel/acoes/', views.admin_action_list, name='admin_action_list'),
    path('admin-panel/acoes/editar/<int:action_id>/', views.admin_edit_action, name='admin_edit_action'),
    path('relatorios/', views.reports_view, name='reports'),
    path('relatorios/tecnico/<int:tec_id>/', views.technician_report_view, name='technician_report'), # <--- NOVA
]