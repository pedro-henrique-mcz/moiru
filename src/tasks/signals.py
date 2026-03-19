# tasks/signals.py
from django.db.models.signals import pre_save, post_save, post_delete
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import (
    Ticket, Environment, Unit, Item, Category, 
    Occupation, Action, Department, Status, 
    FollowUp, TicketAttachment, AuditLog
)
from .middleware import get_current_user

# Monitora todas as tabelas importantes do sistema
MODELS_TO_WATCH = [
    Ticket, Environment, Unit, Item, Category, 
    Occupation, Action, Department, Status, 
    FollowUp, TicketAttachment, User
]

@receiver(pre_save)
def capture_changes(sender, instance, **kwargs):
    if sender in MODELS_TO_WATCH and instance.pk:
        try:
            old_obj = sender.objects.get(pk=instance.pk)
            changes = {}
            for field in instance._meta.fields:
                field_name = field.name
                # Pula campos sensíveis ou automáticos
                if field_name in ['password', 'last_login']: continue
                
                old_val = getattr(old_obj, field_name)
                new_val = getattr(instance, field_name)
                
                if old_val != new_val:
                    # Ajustado para "antes" e "depois" conforme seu admin.py
                    changes[field_name] = {"antes": str(old_val), "depois": str(new_val)}
            instance._audit_changes = changes
        except Exception: pass

@receiver(post_save)
def log_save(sender, instance, created, **kwargs):
    if sender in MODELS_TO_WATCH:
        user = get_current_user()
        
        # DEBUG NO TERMINAL: Verifique se isso aparece quando você salva algo!
        print(f"\n[SINAL] {sender.__name__} {'CRIADO' if created else 'EDITADO'} | Usuário: {user}")

        # Se não houver usuário logado (ex: via terminal ou script), registra como 'Sistema'
        history_data = getattr(instance, '_audit_changes', None) if not created else None
        
        AuditLog.objects.create(
            user=user if user and user.is_authenticated else None,
            action='C' if created else 'U',
            model_name=sender._meta.verbose_name.title(),
            object_id=instance.id,
            object_repr=str(instance)[:255],
            history=history_data
        )