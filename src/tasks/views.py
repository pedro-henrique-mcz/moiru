import markdown
import os
import io
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db.models import Q
from django.utils import timezone
from django.http import JsonResponse, FileResponse, HttpResponse
from django.contrib.auth.models import User, Group
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.template.loader import get_template
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from datetime import timedelta


from xhtml2pdf import pisa
from pypdf import PdfWriter, PdfReader
from PIL import Image, ImageOps

# Imports dos Models e Forms
from .models import Ticket, Status, Unit, Environment, FollowUp, TicketAttachment, Department, Category, Occupation, Item, Action
from .forms import TicketForm, FollowUpForm

# ==============================================================================
# 1. FUNÇÕES AUXILIARES E PERMISSÕES
# ==============================================================================

def is_admin_member(user):
    """Verifica se o usuário é superusuário ou pertence ao grupo 'Administrativo'."""
    return user.is_superuser or user.groups.filter(name='Administrativo').exists()

# ==============================================================================
# 2. OPERAÇÕES DE CHAMADOS (HOME & DASHBOARD)
# ==============================================================================

@login_required
def home(request):
    """Página inicial de boas-vindas com resumo de pendências."""
    user = request.user
    agora = timezone.now()
    
    meus_chamados_abertos = Ticket.objects.filter(
        (Q(requester=user) | Q(responsibles=user)),
        status__identifier__in=['aberto', 'em-andamento'], 
        is_active=True
    ).count()

    context = {
        'usuario': user,
        'hoje': agora,
        'chamados_pendentes': meus_chamados_abertos
    }
    return render(request, 'tasks/home.html', context)

@login_required
def dashboard(request):
    """Dashboard principal com métricas, filtros unificados e paginação."""
    user = request.user
    agora = timezone.now()
    
    # 2.1 Base de Dados (Filtro por permissão e exclusão lógica)
    if is_admin_member(user):
        base_qs = Ticket.objects.filter(is_active=True)
    else:
        meus_setores = user.groups.values_list('name', flat=True)
        base_qs = Ticket.objects.filter(
            Q(department__name__in=meus_setores) |
            Q(creator=user) | Q(requester=user) | Q(responsibles=user),
            is_active=True
        ).distinct()

    # 2.2 Estatísticas e Tendências
    hoje = timezone.now()
    mes_atual_inicio = hoje - timezone.timedelta(days=30)
    mes_anterior_inicio = hoje - timezone.timedelta(days=60)

    def get_trend_pct(queryset, filters_extra=None):
        if filters_extra is None: filters_extra = {}
        qtd_atual = queryset.filter(created_at__gte=mes_atual_inicio, **filters_extra).count()
        qtd_anterior = queryset.filter(created_at__gte=mes_anterior_inicio, created_at__lt=mes_atual_inicio, **filters_extra).count()
        if qtd_anterior == 0:
            pct = 100 if qtd_atual > 0 else 0
        else:
            pct = ((qtd_atual - qtd_anterior) / qtd_anterior) * 100
        return {
            'value': round(pct, 1), 
            'abs_value': round(abs(pct), 1), 
            'positive': pct >= 0, 
            'is_zero': pct == 0
        }

    stats = {
        'total': base_qs.count(),
        'solucionados': base_qs.filter(status__name='Concluído').count(),
        'andamento': base_qs.filter(status__name='Em Andamento').count(),
        'atrasados': base_qs.filter(due_date__lt=agora, due_date__isnull=False).exclude(status__name__in=['Concluído', 'Cancelado']).count(),
        'trend_total': get_trend_pct(base_qs),
        'trend_solucionados': get_trend_pct(base_qs, {'status__name': 'Concluído'}),
        'trend_andamento': get_trend_pct(base_qs, {'status__name': 'Em Andamento'}),
        'trend_atrasados': get_trend_pct(base_qs, {'due_date__lt': agora}),
    }

    # 2.3 Filtragem
    tickets = base_qs 
    quick_filter = request.GET.get('quick_filter', 'total') 
    current_scope = request.GET.get('scope', 'all')
    query = request.GET.get('q', '')
    
    selected_statuses = [int(x) for x in request.GET.getlist('status') if x.isdigit()]
    selected_depts = [int(x) for x in request.GET.getlist('department') if x.isdigit()]

    if quick_filter == 'solucionados':
        tickets = tickets.filter(status__name='Concluído')
    elif quick_filter == 'andamento':
        tickets = tickets.filter(status__name='Em Andamento')
    elif quick_filter == 'atrasados':
        tickets = tickets.filter(due_date__lt=agora, due_date__isnull=False).exclude(status__name__in=['Concluído', 'Cancelado'])

    if selected_statuses: tickets = tickets.filter(status__id__in=selected_statuses)
    if selected_depts: tickets = tickets.filter(department__id__in=selected_depts)
    if query:
        tickets = tickets.filter(Q(id=query) | Q(title__icontains=query)) if query.isdigit() else \
                  tickets.filter(Q(title__icontains=query) | Q(description__icontains=query) | Q(requester__first_name__icontains=query) | Q(department__name__icontains=query)).distinct()
    
    if current_scope == 'me': tickets = tickets.filter(Q(requester=user) | Q(responsibles=user)).distinct()

    # 2.4 Paginação
    tickets = tickets.order_by('-created_at').select_related('status', 'department', 'requester')
    paginator = Paginator(tickets, 8)
    page_obj = paginator.get_page(request.GET.get('page'))

    params = request.GET.copy()
    if 'page' in params: del params['page']

    context = {
        'page_obj': page_obj,
        'stats': stats,
        'quick_filter': quick_filter,
        'current_scope': current_scope,
        'preserved_filters': params.urlencode(),
        'dropdown_data': {'all_statuses': Status.objects.all(), 'all_departments': Department.objects.all()},
        'active_filters': {'statuses': Status.objects.filter(id__in=selected_statuses), 'departments': Department.objects.filter(id__in=selected_depts)},
        'filters': {'q': query, 'selected_statuses': selected_statuses, 'selected_depts': selected_depts}
    }
    return render(request, 'tasks/dashboard.html', context)

# ==============================================================================
# 3. GESTÃO DE TICKET (CRUD, FOLLOWUP, OS)
# ==============================================================================

@login_required
def create_ticket(request):
    """Criação de novos chamados."""
    if not (is_admin_member(request.user) or request.user.has_perm('tasks.add_ticket')):
        messages.error(request, "Permissão negada.")
        return redirect('dashboard')

    if request.method == 'POST':
        form = TicketForm(request.POST, request.FILES) 
        if form.is_valid():
            ticket = form.save(commit=False)
            ticket.creator = request.user 
            ticket.status = Status.objects.filter(identifier='aberto').first() or Status.objects.create(name='Aberto', identifier='aberto', color='#0d6efd')
            ticket.save()
            form.save_m2m() 
            for f in request.FILES.getlist('attachments'):
                TicketAttachment.objects.create(ticket=ticket, file=f)
            messages.success(request, "Chamado criado com sucesso!")
            return redirect('dashboard')
        else:
            messages.error(request, "O Django bloqueou o salvamento. Verifique os erros abaixo.")
            print("ERROS DE VALIDAÇÃO DO FORMULÁRIO:", form.errors)
    else:
        form = TicketForm(initial={'requester': request.user})
    return render(request, 'tasks/create_ticket.html', {'form': form})

@login_required
def ticket_detail(request, ticket_id):
    """Visualização detalhada do chamado."""
    ticket = get_object_or_404(Ticket, pk=ticket_id)
    
    all_status = Status.objects.all()
    all_users = User.objects.filter(is_active=True).order_by('first_name')
    
    ticket.description_html = markdown.markdown(ticket.description, extensions=['nl2br', 'fenced_code']) if ticket.description else ""
    
    form = FollowUpForm(initial={'new_status': ticket.status})
    e_admin = is_admin_member(request.user)
    
    if not e_admin:
        form.fields['new_status'].queryset = Status.objects.exclude(name__in=['Concluído', 'Cancelado'])

    is_closed = ticket.status.name in ['Concluído', 'Cancelado']
    
    context = {
        'ticket': ticket, 
        'form': form, 
        'is_closed': is_closed,
        'can_reopen': is_closed and e_admin,
        'can_conclude': e_admin and not is_closed,
        'can_comment': not is_closed and (e_admin or ticket.requester == request.user or request.user in ticket.responsibles.all()),
        'all_status': all_status,
        'all_users': all_users,
        'is_admin': e_admin
    }
    return render(request, 'tasks/ticket_detail.html', context)

@login_required
def reopen_ticket(request, ticket_id):
    """Reabre chamados concluídos ou cancelados (Admin only)."""
    if not is_admin_member(request.user): return redirect('ticket_detail', ticket_id=ticket_id)
    ticket = get_object_or_404(Ticket, pk=ticket_id)
    novo_status = Status.objects.filter(name='Em Andamento').first() or Status.objects.filter(name='Aberto').first()
    if novo_status:
        ticket.status = novo_status
        ticket.save()
        FollowUp.objects.create(ticket=ticket, user=request.user, message="Chamado reaberto.", new_status=novo_status)
    return redirect('ticket_detail', ticket_id=ticket.id)

@login_required
def add_followup(request, ticket_id):
    """Adiciona interações e altera status dos chamados."""
    ticket = get_object_or_404(Ticket, pk=ticket_id)
    
    if request.method == 'POST':
        form = FollowUpForm(request.POST, request.FILES)
        if form.is_valid():
            fup = form.save(commit=False)
            fup.ticket, fup.user = ticket, request.user
            
            novo_status = form.cleaned_data.get('new_status')
            if novo_status and ticket.status != novo_status:
                ticket.status = novo_status
                ticket.save()
                
            fup.save()
            
            if 'technicians' in form.cleaned_data:
                ticket.responsibles.set(form.cleaned_data['technicians'])
                
            messages.success(request, "Interação adicionada com sucesso.")
        else:
            messages.error(request, "Falha ao atualizar o chamado. Verifique os campos.")
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
                    
    return redirect('ticket_detail', ticket_id=ticket.id)

@login_required
def generate_os(request, ticket_id):
    """Gera versão de impressão da O.S., mesclando anexos em um único PDF."""
    ticket = get_object_or_404(Ticket, id=ticket_id)
    ticket.description_html = markdown.markdown(ticket.description, extensions=['nl2br', 'fenced_code']) if ticket.description else ""
    
    template = get_template('tasks/print_os.html')
    html = template.render({'ticket': ticket, 'generated_at': timezone.now()})
    
    os_pdf_stream = io.BytesIO()
    pisa_status = pisa.CreatePDF(io.BytesIO(html.encode('UTF-8')), dest=os_pdf_stream, encoding='UTF-8')
    
    if pisa_status.err:
        return HttpResponse('Erro ao renderizar o documento PDF da O.S.', status=500)
        
    merger = PdfWriter()
    os_pdf_stream.seek(0)
    merger.append(PdfReader(os_pdf_stream))
    
    # 1. Caçador de Anexos: Pega do Legado, dos Anexos Principais e das Interações
    all_files = []
    if ticket.attachment:
        all_files.append(ticket.attachment)
    for att in ticket.attachments.all():
        if att.file:
            all_files.append(att.file)
    for fup in ticket.follow_ups.all():
        if fup.attachment:
            all_files.append(fup.attachment)
    
    # 2. Processamento e Mesclagem Inteligente
    for file_field in all_files:
        try:
            # Trava de Segurança: Se o arquivo físico não estiver mais no servidor, pula.
            if not os.path.exists(file_field.path):
                continue
                
            ext = os.path.splitext(file_field.name)[1].lower()
            
            if ext == '.pdf':
                merger.append(PdfReader(file_field.path))
            else:
                # Se não for PDF, a biblioteca tenta "adivinhar" que é uma imagem, 
                # mesmo que falte a extensão ou seja um formato diferente (webp, jfif, etc).
                img = Image.open(file_field.path)
                
                # Vacina: Corrige a rotação de fotos de celular (Senão saem deitadas)
                img = ImageOps.exif_transpose(img)
                
                if img.mode in ("RGBA", "P"): 
                    img = img.convert("RGB")
                    
                img_pdf_stream = io.BytesIO()
                img.save(img_pdf_stream, format='PDF', resolution=100.0)
                img_pdf_stream.seek(0)
                merger.append(PdfReader(img_pdf_stream))
                
        except Exception as e:
            # Se cair aqui, é porque a Chirley anexou um Word (.docx), Excel, etc.
            # O Python não consegue "colar" um Excel dentro de um PDF de forma simples, então ele ignora para não dar pau.
            print(f"Ignorando anexo na O.S. (Formato não suportado para mesclagem): {str(e)}")
            continue
            
    final_pdf = io.BytesIO()
    merger.write(final_pdf)
    merger.close()
    final_pdf.seek(0)
    
    return FileResponse(final_pdf, as_attachment=False, filename=f"OS_{ticket.id}.pdf", content_type='application/pdf')
@login_required
def edit_ticket(request, ticket_id):
    """View para edição de um chamado existente."""
    ticket = get_object_or_404(Ticket, pk=ticket_id)
    
    if not (is_admin_member(request.user) or request.user == ticket.creator):
        messages.error(request, "Acesso negado: Você não tem permissão para editar este chamado.")
        return redirect('ticket_detail', ticket_id=ticket.id)

    if ticket.status.name in ['Concluído', 'Cancelado'] and not is_admin_member(request.user):
        messages.warning(request, "Chamados encerrados não podem ser editados.")
        return redirect('ticket_detail', ticket_id=ticket.id)

    if request.method == 'POST':
        form = TicketForm(request.POST, request.FILES, instance=ticket)
        if form.is_valid():
            form.save()
            messages.success(request, "Chamado atualizado com sucesso.")
            return redirect('ticket_detail', ticket_id=ticket.id)
        else:
            messages.error(request, "Erro ao salvar edição. Verifique os campos obrigatórios.")
    else:
        form = TicketForm(instance=ticket)

    context = {
        'form': form,
        'ticket': ticket
    }
    return render(request, 'tasks/edit_ticket.html', context)

@login_required
def delete_ticket(request, ticket_id):
    """Realiza o Soft Delete do chamado."""
    ticket = get_object_or_404(Ticket, pk=ticket_id)
    
    if not is_admin_member(request.user) and request.user != ticket.creator:
        messages.error(request, "Permissão negada para excluir este chamado.")
        return redirect('ticket_detail', ticket_id=ticket.id)
        
    ticket.is_active = False
    ticket.save()
    
    messages.success(request, f"Chamado #{ticket.id} excluído com sucesso.")
    return redirect('dashboard')

# ==============================================================================
# 4. ÁREA ADMINISTRATIVA 
# ==============================================================================

@login_required
@user_passes_test(is_admin_member, login_url='dashboard')
def admin_panel(request):
    """Hub central administrativo."""
    return render(request, 'tasks/admin_panel.html')

# --- GESTÃO DE UNIDADES E AMBIENTES ---

@login_required
@user_passes_test(is_admin_member, login_url='dashboard')
def admin_unit_list(request):
    """Lista unidades com design de linhas clicáveis."""
    units = Unit.objects.all().order_by('name')
    return render(request, 'tasks/admin_unit_list.html', {'units': units})

@login_required
@user_passes_test(is_admin_member, login_url='dashboard')
def admin_add_unit(request):
    """Cria uma nova unidade."""
    if request.method == 'POST':
        Unit.objects.create(
            name=request.POST.get('name'),
            identifier=request.POST.get('identifier'),
            cep=request.POST.get('cep'),
            address=request.POST.get('address'),
            number=request.POST.get('number'),
            neighborhood=request.POST.get('neighborhood'),
            city=request.POST.get('city'),
            color=request.POST.get('color', '#6c757d'),
            description=request.POST.get('description')
        )
        messages.success(request, "Unidade criada com sucesso!")
    return redirect('admin_unit_list')

@login_required
@user_passes_test(is_admin_member, login_url='dashboard')
def admin_unit_manage(request, unit_id):
    """Página central da unidade: exibe detalhes e carrega opções para o formulário."""
    unit = get_object_or_404(Unit, pk=unit_id)
    environments = Environment.objects.filter(unit=unit).order_by('block', 'identifier')
    categories = Category.objects.all().order_by('name')
    occupations = Occupation.objects.all().order_by('name')
    
    return render(request, 'tasks/admin_unit_manage.html', {
        'unit': unit,
        'environments': environments,
        'categories': categories,
        'occupations': occupations
    })

@login_required
@user_passes_test(is_admin_member, login_url='dashboard')
def admin_edit_unit(request, unit_id):
    """Atualização de dados da unidade existente."""
    unit = get_object_or_404(Unit, pk=unit_id)
    if request.method == 'POST':
        unit.name = request.POST.get('name')
        unit.identifier = request.POST.get('identifier')
        unit.cep = request.POST.get('cep')
        unit.address = request.POST.get('address')
        unit.number = request.POST.get('number')
        unit.neighborhood = request.POST.get('neighborhood')
        unit.city = request.POST.get('city')
        unit.color = request.POST.get('color')
        unit.description = request.POST.get('description')
        unit.save()
        messages.success(request, "Unidade atualizada!")
    return redirect('admin_unit_manage', unit_id=unit.id)

@login_required
@user_passes_test(is_admin_member, login_url='dashboard')
def admin_add_environment(request, unit_id):
    unit = get_object_or_404(Unit, pk=unit_id)
    if request.method == 'POST':
        identifier = request.POST.get('identifier')
        if identifier:
            Environment.objects.create(
                unit=unit,
                identifier=identifier,
                block=request.POST.get('block'),
                floor=request.POST.get('floor'),
                description=request.POST.get('description'),
                occupation=request.POST.get('occupation'), 
                category_id=request.POST.get('category') or None
            )
            messages.success(request, "Ambiente adicionado!")
    return redirect('admin_unit_manage', unit_id=unit.id)

@login_required
@user_passes_test(is_admin_member, login_url='dashboard')
def admin_edit_environment(request, env_id):
    """Edita um ambiente existente."""
    env = get_object_or_404(Environment, pk=env_id)
    if request.method == 'POST':
        env.identifier = request.POST.get('identifier')
        env.block = request.POST.get('block')
        env.floor = request.POST.get('floor')
        env.occupation = request.POST.get('occupation')
        env.description = request.POST.get('description')
        env.category_id = request.POST.get('category') or None
        env.save()
        messages.success(request, f"Ambiente {env.identifier} atualizado!")
    return redirect('admin_unit_manage', unit_id=env.unit.id)

@login_required
@user_passes_test(is_admin_member, login_url='dashboard')
def admin_toggle_environment_active(request, env_id):
    """Ativa/Desativa ambiente (Soft Delete)."""
    env = get_object_or_404(Environment, pk=env_id)
    env.is_active = not env.is_active
    env.save()
    messages.success(request, f"Ambiente {'ativado' if env.is_active else 'desativado'}.")
    return redirect('admin_unit_manage', unit_id=env.unit.id)

# --- GESTÃO DE DEPARTAMENTOS (SETORES) ---

@login_required
@user_passes_test(is_admin_member, login_url='dashboard')
def admin_department_list(request):
    """Lista todos os departamentos e sincroniza a criação com Grupos do Django."""
    
    departamentos_existentes = Department.objects.all()
    for dept in departamentos_existentes:
        Group.objects.get_or_create(name=dept.name)

    if request.method == 'POST':
        novo_nome = request.POST.get('name')
        
        Department.objects.create(
            name=novo_nome,
            identifier=request.POST.get('identifier'),
            email=request.POST.get('email'),
            phone=request.POST.get('phone'),
            color=request.POST.get('color', '#6c757d'),
            is_active=request.POST.get('is_active') == 'on'
        )
        
        Group.objects.get_or_create(name=novo_nome)
        
        messages.success(request, "Setor e Grupo de acesso criados com sucesso!")
        return redirect('admin_department_list')
        
    departments = Department.objects.all().order_by('name')
    return render(request, 'tasks/admin_department_list.html', {'departments': departments})

@login_required
@user_passes_test(is_admin_member, login_url='dashboard')
def admin_edit_department(request, dept_id):
    """Atualiza o departamento e sincroniza renomeações com o Grupo correspondente."""
    dept = get_object_or_404(Department, pk=dept_id)
    
    if request.method == 'POST':
        nome_antigo = dept.name
        novo_nome = request.POST.get('name')
        
        dept.name = novo_nome
        dept.identifier = request.POST.get('identifier')
        dept.email = request.POST.get('email')
        dept.phone = request.POST.get('phone')
        dept.color = request.POST.get('color')
        dept.is_active = request.POST.get('is_active') == 'on'
        dept.save()
        
        if nome_antigo != novo_nome:
            try:
                grupo = Group.objects.get(name=nome_antigo)
                grupo.name = novo_nome
                grupo.save()
            except Group.DoesNotExist:
                Group.objects.get_or_create(name=novo_nome)
                
        messages.success(request, "Setor atualizado e permissões sincronizadas!")
        
    return redirect('admin_department_list')

# --- GESTÃO DE PESSOAS (USUÁRIOS) ---

@login_required
@user_passes_test(is_admin_member, login_url='dashboard')
def admin_user_list(request):
    """Lista todos os usuários e lida com a criação de novos."""
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        first_name = request.POST.get('first_name')
        password = request.POST.get('password')
        matricula = request.POST.get('matricula')
        department_id = request.POST.get('department')
        
        if User.objects.filter(username=username).exists():
            messages.error(request, "Erro: Este Nome de Usuário (Login) já está em uso.")
        else:
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                is_active=request.POST.get('is_active') == 'on'
            )
            
            user.info.matricula = matricula
            user.info.save()
            
            if department_id:
                try:
                    dept = Department.objects.get(id=department_id)
                    grupo, _ = Group.objects.get_or_create(name=dept.name)
                    user.groups.add(grupo)
                except Department.DoesNotExist:
                    pass
                    
            messages.success(request, "Usuário criado com sucesso!")
        return redirect('admin_user_list')
        
    users = User.objects.all().select_related('info').order_by('first_name', 'username')
    departments = Department.objects.filter(is_active=True).order_by('name')
    
    return render(request, 'tasks/admin_user_list.html', {
        'users': users, 
        'departments': departments
    })

@login_required
@user_passes_test(is_admin_member, login_url='dashboard')
def admin_edit_user(request, user_id):
    """Atualiza os dados de um usuário existente."""
    edit_user = get_object_or_404(User, pk=user_id)
    if request.method == 'POST':
        edit_user.first_name = request.POST.get('first_name')
        edit_user.email = request.POST.get('email')
        edit_user.is_active = request.POST.get('is_active') == 'on'
        
        new_password = request.POST.get('password')
        if new_password:
            edit_user.set_password(new_password)
            
        edit_user.save()
        
        matricula = request.POST.get('matricula')
        if matricula:
            edit_user.info.matricula = matricula
            edit_user.info.save()
            
        department_id = request.POST.get('department')
        if department_id:
            try:
                dept = Department.objects.get(id=department_id)
                grupo, _ = Group.objects.get_or_create(name=dept.name)
                
                dept_names = Department.objects.values_list('name', flat=True)
                grupos_antigos = edit_user.groups.filter(name__in=dept_names)
                edit_user.groups.remove(*grupos_antigos)
                
                edit_user.groups.add(grupo)
            except Department.DoesNotExist:
                pass
                
        messages.success(request, "Usuário atualizado com sucesso!")
    return redirect('admin_user_list')


# --- GESTÃO DE ITENS ---
@login_required
@user_passes_test(is_admin_member, login_url='dashboard')
def admin_item_list(request):
    """Lista e cria novos Itens (Equipamentos/Hardware/Software)."""
    if request.method == 'POST':
        Item.objects.create(
            name=request.POST.get('name'),
            identifier=request.POST.get('identifier')
        )
        messages.success(request, "Item criado com sucesso!")
        return redirect('admin_item_list')
    
    items = Item.objects.all().order_by('name')
    return render(request, 'tasks/admin_item_list.html', {'items': items})

@login_required
@user_passes_test(is_admin_member, login_url='dashboard')
def admin_edit_item(request, item_id):
    """Edita um Item existente."""
    item = get_object_or_404(Item, pk=item_id)
    if request.method == 'POST':
        item.name = request.POST.get('name')
        item.identifier = request.POST.get('identifier')
        item.save()
        messages.success(request, "Item atualizado com sucesso!")
    return redirect('admin_item_list')

# --- GESTÃO DE AÇÕES ---
@login_required
@user_passes_test(is_admin_member, login_url='dashboard')
def admin_action_list(request):
    """Lista e cria novas Ações (Ex: Formatação, Conserto, Instalação)."""
    if request.method == 'POST':
        Action.objects.create(
            name=request.POST.get('name'),
            identifier=request.POST.get('identifier')
        )
        messages.success(request, "Ação criada com sucesso!")
        return redirect('admin_action_list')
    
    actions = Action.objects.all().order_by('name')
    return render(request, 'tasks/admin_action_list.html', {'actions': actions})

@login_required
@user_passes_test(is_admin_member, login_url='dashboard')
def admin_edit_action(request, action_id):
    """Edita uma Ação existente."""
    action = get_object_or_404(Action, pk=action_id)
    if request.method == 'POST':
        action.name = request.POST.get('name')
        action.identifier = request.POST.get('identifier')
        action.save()
        messages.success(request, "Ação atualizada com sucesso!")
    return redirect('admin_action_list')

# ==============================================================================
# 5. UTILITÁRIOS E AJAX
# ==============================================================================

def load_users_by_dept(request):
    """Carrega usuários por departamento via AJAX."""
    department_id = request.GET.get('department_id')
    users = User.objects.filter(groups__id=department_id).order_by('first_name') if department_id else User.objects.none()
    return JsonResponse(list(users.values('id', 'first_name', 'username')), safe=False)

def load_envs_by_unit(request):
    """Carrega ambientes ativos de uma unidade via AJAX."""
    unit_id = request.GET.get('unit_id')
    envs = Environment.objects.filter(unit_id=unit_id, is_active=True).order_by('block', 'identifier') if unit_id else []
    return JsonResponse([{'id': e.id, 'name': str(e)} for e in envs], safe=False)

@login_required
def force_password_change(request):
    """Tela obrigatória de troca de senha no primeiro acesso."""
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user) 
            user.info.force_password_change = False
            user.info.save()
            messages.success(request, 'Senha atualizada com sucesso! Bem-vindo ao Moiru.')
            return redirect('dashboard')
    else:
        form = PasswordChangeForm(request.user)
    return render(request, 'tasks/force_password_change.html', {'form': form})

# ==============================================================================
# 6. RELATÓRIOS
# ==============================================================================

@login_required
def reports_view(request):
    """Visão geral de produtividade por técnico."""
    is_admin = request.user.is_superuser or request.user.groups.filter(name='Administrativo').exists()
    if not is_admin:
        messages.error(request, "Acesso negado.")
        return redirect('dashboard')

    hoje = timezone.now().date()
    data_inicio = request.GET.get('data_inicio', (hoje - timedelta(days=30)).strftime('%Y-%m-%d'))
    data_fim = request.GET.get('data_fim', hoje.strftime('%Y-%m-%d'))
    q_nome = request.GET.get('q_nome', '').strip()

    tecnicos = User.objects.filter(Q(groups__name='Administrativo') | Q(is_superuser=True)).distinct()

    if q_nome:
        tecnicos = tecnicos.filter(Q(first_name__icontains=q_nome) | Q(username__icontains=q_nome))

    dados_relatorio = []
    for tec in tecnicos:
        tickets_do_tec = Ticket.objects.filter(responsibles=tec, created_at__date__gte=data_inicio, created_at__date__lte=data_fim)
        total = tickets_do_tec.count()
        concluidos = tickets_do_tec.filter(status__name__icontains='Concluído').count()
        
        if total > 0: 
            dados_relatorio.append({
                'id': tec.id,
                'nome': tec.get_full_name() or tec.username,
                'total': total,
                'concluidos': concluidos,
                'pendentes': total - concluidos,
            })

    dados_relatorio = sorted(dados_relatorio, key=lambda x: x['concluidos'], reverse=True)
    todos_tecnicos = User.objects.filter(Q(groups__name='Administrativo') | Q(is_superuser=True)).distinct()

    return render(request, 'tasks/reports.html', {
        'dados_relatorio': dados_relatorio, 'data_inicio': data_inicio, 
        'data_fim': data_fim, 'q_nome': q_nome, 'todos_tecnicos': todos_tecnicos
    })

@login_required
def technician_report_view(request, tec_id):
    """Relatório detalhado (OS) de um técnico específico."""
    is_admin = request.user.is_superuser or request.user.groups.filter(name='Administrativo').exists()
    if not is_admin: return redirect('dashboard')

    tecnico = get_object_or_404(User, id=tec_id)
    data_inicio = request.GET.get('data_inicio')
    data_fim = request.GET.get('data_fim')

    tickets = Ticket.objects.filter(responsibles=tecnico)
    if data_inicio and data_fim:
        tickets = tickets.filter(created_at__date__gte=data_inicio, created_at__date__lte=data_fim)
    
    tickets = tickets.order_by('-created_at')

    stats = {
        'total': tickets.count(),
        'concluidos': tickets.filter(status__name__icontains='Concluído').count(),
        'andamento': tickets.exclude(status__name__icontains='Concluído').count(),
    }

    return render(request, 'tasks/technician_report.html', {
        'tecnico': tecnico, 'tickets': tickets, 'stats': stats,
        'data_inicio': data_inicio, 'data_fim': data_fim
    })