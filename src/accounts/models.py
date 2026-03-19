from django.db import models

class ControlAcessTask(models.Model):
    name = models.CharField(max_length=100)

    class Meta:
        permissions = [
            ("can_create_tasks", "Pode Criar Chamados"),
        ]