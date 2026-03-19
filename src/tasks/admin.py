from django.contrib import admin
from .models import (
    Department, Unit, Category, Occupation, Environment,
    Action, Item, Status, Ticket, 
    TicketAttachment, FollowUp, AuditLog
)

# Inlines (Sem Item)
class TicketAttachmentInline(admin.TabularInline):
    model = TicketAttachment
    extra = 1

class FollowUpInline(admin.StackedInline):
    model = FollowUp
    extra = 0
    readonly_fields = ('created_at',)

@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    # REMOVI O 'item' DA LISTA ABAIXO:
    list_display = ('id', 'title', 'status', 'created_at')
    list_filter = ('status', 'department', 'unit')
    search_fields = ('title', 'description', 'id')
    
    inlines = [TicketAttachmentInline, FollowUpInline]
    
    fieldsets = (
        ('Dados Básicos', {
            'fields': ('title', 'description', 'status', 'department')
        }),
        ('Solicitante & Responsáveis', {
            'fields': ('creator', 'requester', 'responsibles')
        }),
        ('Localização', {
            # REMOVI O 'item' DAQUI TAMBÉM:
            'fields': ('unit', 'environment', 'item')
        }),
        ('Classificação Técnica', {
            'fields': ('action', 'due_date', 'start_date', 'finish_date')
        }),
    )

# Registros Padrão
admin.site.register(Item)
admin.site.register(Department)
admin.site.register(Unit)
admin.site.register(Environment)
admin.site.register(Category)
admin.site.register(Occupation)
admin.site.register(Action)
admin.site.register(Status)
admin.site.register(AuditLog)