import os
from django.db import models
from django.contrib.auth.models import User

# ==============================================================================
# TABELAS DE SUPORTE (MANTIDAS IGUAIS)
# ==============================================================================

class Department(models.Model):
    name = models.CharField(max_length=100, verbose_name="Nome do Setor")
    identifier = models.CharField(max_length=50, unique=True, verbose_name="Identificador (Sigla)")
    email = models.EmailField(blank=True, null=True, verbose_name="E-mail do Setor")
    phone = models.CharField(max_length=20, blank=True, null=True, verbose_name="Telefone / Ramal")
    color = models.CharField(max_length=7, default='#6c757d', help_text="Código Hexadecimal (ex: #FF0000)")
    is_active = models.BooleanField(default=True, verbose_name="Ativo")

    class Meta:
        verbose_name = "Setor / Departamento"
        verbose_name_plural = "Setores / Departamentos"
        ordering = ['name'] # Facilita, pois os dropdowns já virão em ordem alfabética

    def __str__(self):
        return f"{self.identifier} - {self.name}"
    
class Unit(models.Model):
    name = models.CharField(max_length=100, verbose_name="Nome da Unidade")
    identifier = models.SlugField(max_length=50, unique=True, verbose_name="Sigla")
    color = models.CharField(max_length=7, default='#6c757d')
    cep = models.CharField(max_length=10, blank=True, null=True)
    address = models.CharField(max_length=255, blank=True, null=True, verbose_name="Rua")
    number = models.CharField(max_length=10, blank=True, null=True, verbose_name="Número")
    neighborhood = models.CharField(max_length=100, blank=True, null=True, verbose_name="Bairro")
    city = models.CharField(max_length=100, blank=True, null=True, verbose_name="Cidade")
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    def __str__(self): return self.name

class Category(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="Nome da Categoria")
    description = models.TextField(blank=True, null=True, verbose_name="Descrição")
    class Meta:
        verbose_name = "Categoria de Ambiente"
        verbose_name_plural = "Categorias de Ambiente"
    def __str__(self): return self.name

class Occupation(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="Tipo de Ocupação")
    description = models.TextField(blank=True, null=True, verbose_name="Descrição")
    class Meta:
        verbose_name = "Tipo de Ocupação"
        verbose_name_plural = "Tipos de Ocupação"
    def __str__(self): return self.name

class Environment(models.Model):
    identifier = models.CharField(max_length=50, unique=True, verbose_name="Identificador (Sala)")
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE, related_name='environments', verbose_name="Unidade (Sede)")
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='environments', verbose_name="Categoria Macro")
    occupation = models.CharField(max_length=100, blank=True, null=True, verbose_name="Tipo de Ocupação")
    block = models.CharField(max_length=20, blank=True, null=True, verbose_name="Bloco")
    floor = models.CharField(max_length=20, blank=True, null=True, verbose_name="Andar")
    description = models.TextField(blank=True, null=True, verbose_name="Ponto de Referência")
    is_active = models.BooleanField(default=True, verbose_name="Ativo")
    class Meta:
        verbose_name = "Ambiente"
        verbose_name_plural = "Ambientes"
        ordering = ['unit', 'block', 'identifier']
    def __str__(self):
        loc_parts = []
        if self.block: loc_parts.append(f"Bl {self.block}")
        if self.floor: loc_parts.append(self.floor)
        details = f" ({' - '.join(loc_parts)})" if loc_parts else ""
        return f"{self.identifier}{details}"

class Action(models.Model):
    name = models.CharField(max_length=100, verbose_name="Nome da Ação")
    identifier = models.CharField(max_length=50, unique=True, verbose_name="Identificador")
    
    def __str__(self): return self.name

class Item(models.Model):
    name = models.CharField(max_length=100, verbose_name="Nome do Item")
    identifier = models.CharField(max_length=50, unique=True, verbose_name="Identificador")
    
    def __str__(self): return self.name

class Status(models.Model):
    name = models.CharField(max_length=50, verbose_name="Nome do Status")
    identifier = models.CharField(max_length=50, unique=True, verbose_name="Identificador")
    color = models.CharField(max_length=7, help_text="Cor representativa (CSS Hex)")
    class Meta: verbose_name_plural = "Status"
    def __str__(self): return self.name

# ==============================================================================
# TICKET (COM O CAMPO 'item' COMENTADO AGORA)
# ==============================================================================
from django.db.models.signals import post_save
from django.dispatch import receiver

# ==============================================================================
# EXTENSÃO DO USUÁRIO (USER INFO)
# ==============================================================================

class UserInfo(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='info', verbose_name="Usuário")
    cpf = models.CharField(max_length=14, unique=True, blank=True, null=True, verbose_name="CPF")
    matricula = models.CharField(max_length=50, unique=True, blank=True, null=True, verbose_name="Matrícula")
    contato = models.CharField(max_length=20, blank=True, null=True, verbose_name="Contato (Telefone/Celular)")
    force_password_change = models.BooleanField(default=True, verbose_name="Exige troca de senha")
    class Meta:
        verbose_name = "Informação Adicional de Usuário"
        verbose_name_plural = "Informações Adicionais de Usuários"

    def __str__(self):
        return f"Dados complementares: {self.user.username}"

# --- SIGNALS (Gatilhos Automáticos) ---
# Cria o UserInfo vazio automaticamente assim que um novo User é salvo no banco
@receiver(post_save, sender=User)
def create_user_info(sender, instance, created, **kwargs):
    if created:
        UserInfo.objects.create(user=instance)

# Salva as alterações do UserInfo sempre que o User for salvo
@receiver(post_save, sender=User)
def save_user_info(sender, instance, **kwargs):
    instance.info.save()


class Ticket(models.Model):
    title = models.CharField(max_length=200, verbose_name="Título/Assunto")
    description = models.TextField(verbose_name="Descrição", blank=True, null=True)
    status = models.ForeignKey(Status, on_delete=models.PROTECT, related_name='tickets')
    creator = models.ForeignKey(User, on_delete=models.PROTECT, related_name='created_tickets', verbose_name="Criador")
    requester = models.ForeignKey(User, on_delete=models.PROTECT, related_name='requested_tickets', verbose_name="Solicitante")
    responsibles = models.ManyToManyField(User, related_name='assigned_tickets', blank=True, verbose_name="Responsáveis")
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, verbose_name="Departamento")
    unit = models.ForeignKey(Unit, on_delete=models.SET_NULL, null=True, verbose_name="Unidade")
    environment = models.ForeignKey(Environment, on_delete=models.SET_NULL, null=True, verbose_name="Ambiente")
    action = models.ForeignKey(Action, on_delete=models.SET_NULL, verbose_name="Ação", null=True)
    is_active = models.BooleanField(default=True, verbose_name="Ativo")

    #--- COMENTEI O CAMPO ABAIXO PARA O PASSO 1 ---
    item = models.ForeignKey(
       Item, 
       on_delete=models.SET_NULL, 
       null=True, 
       blank=True, 
       verbose_name="Item / Equipamento",
       help_text="Selecione o item relacionado a este chamado"
    )
    
    attachment = models.FileField(upload_to='tickets/attachments/', null=True, blank=True, verbose_name="Anexo (Legado)")
    start_date = models.DateTimeField(null=True, blank=True, verbose_name="Data de Início")
    due_date = models.DateTimeField(null=True, blank=True, verbose_name="Data de Entrega") 
    finish_date = models.DateTimeField(null=True, blank=True, verbose_name="Data de Término")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Data de Registro")

    def save(self, *args, **kwargs):
        if self.environment and self.environment.unit:
            self.unit = self.environment.unit
        super(Ticket, self).save(*args, **kwargs)
    def __str__(self): return f"Ticket #{self.id} - {self.title}"

# ==============================================================================
# RESTANTE NORMAL
# ==============================================================================

class TicketAttachment(models.Model):
    ticket = models.ForeignKey(Ticket, related_name='attachments', on_delete=models.CASCADE)
    file = models.FileField(upload_to='tickets/attachments/', verbose_name="Arquivo")
    uploaded_at = models.DateTimeField(auto_now_add=True)
    def filename(self): return os.path.basename(self.file.name)
    def __str__(self): return f"Anexo de {self.ticket.id}"

class FollowUp(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='follow_ups', verbose_name="Chamado")
    user = models.ForeignKey(User, on_delete=models.PROTECT, verbose_name="Usuário")
    message = models.TextField(verbose_name="Mensagem")
    attachment = models.FileField(upload_to='tickets/followups/', null=True, blank=True, verbose_name="Anexo")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Data")
    old_status = models.ForeignKey(Status, on_delete=models.SET_NULL, null=True, blank=True, related_name='status_anterior')
    new_status = models.ForeignKey(Status, on_delete=models.SET_NULL, null=True, blank=True, related_name='status_novo')
    def __str__(self): return f"Interação em #{self.ticket.id} por {self.user.username}"
    
class AuditLog(models.Model):
    ACTIONS = (('C', 'Criou'), ('U', 'Editou'), ('D', 'Excluiu'))
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name="Responsável")
    action = models.CharField(max_length=1, choices=ACTIONS)
    model_name = models.CharField(max_length=100, verbose_name="Tabela")
    object_id = models.PositiveIntegerField()
    object_repr = models.CharField(max_length=255, verbose_name="Item")
    history = models.JSONField(null=True, blank=True, verbose_name="Mudanças Detalhadas")
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name="Data/Hora")
    class Meta:
        verbose_name = "Log de Auditoria"
        ordering = ['-timestamp']