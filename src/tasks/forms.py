from django import forms
from django.contrib.auth.models import User
from django.utils import timezone 
from .models import Ticket, FollowUp, Status

class UserModelChoiceField(forms.ModelMultipleChoiceField):
    def label_from_instance(self, obj):
        return obj.get_full_name() if obj.get_full_name() else obj.username

class TicketForm(forms.ModelForm):
    # O CAMPO ATTACHMENTS FOI TOTALMENTE REMOVIDO DAQUI
    # O formulário vai focar apenas em validar os textos, e a View cuida de salvar os anexos.
    
    responsibles = forms.ModelMultipleChoiceField(
        queryset=User.objects.all(),
        widget=forms.SelectMultiple(attrs={'class': 'form-select', 'size': '3'}),
        required=False,
        label="Atribuído a (Opcional)"
    )

    class Meta:
        model = Ticket
        fields = [
            'title', 
            'description', 
            'requester', 
            'responsibles',
            'department', 
            'environment', 
            'unit', 
            'action',
            'due_date',
        ]
        
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Descreva detalhadamente o problema...'}),
            'title': forms.TextInput(attrs={'placeholder': 'Ex: Ar condicionado pingando'}),
            
            # Widget da Data de Entrega 
            'due_date': forms.DateInput(attrs={
                'class': 'form-control', 
                'type': 'text',
                'placeholder': 'Sem Prazo',
                'onfocus': "(this.type='date')",
                'onblur': "if(!this.value)this.type='text'"
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.fields['requester'].label_from_instance = lambda obj: obj.get_full_name() or obj.username

        # Placeholders
        self.fields['department'].empty_label = "Selecione o Departamento"
        self.fields['unit'].empty_label = "Selecione a Unidade"
        self.fields['environment'].empty_label = "Selecione o Ambiente"
        self.fields['action'].empty_label = "Selecione o Tipo de Ação"
        
        # CORREÇÃO: Forçando o Django a entender que esses campos não são obrigatórios
        # Isso impede que a edição falhe silenciosamente caso um deles esteja vazio.
        self.fields['due_date'].required = False
        self.fields['responsibles'].required = False
        self.fields['department'].required = False
        self.fields['unit'].required = False
        self.fields['environment'].required = False
        self.fields['action'].required = False

    def clean_due_date(self):
        due_date = self.cleaned_data.get('due_date')
        if not due_date:
            return None
        return due_date
    
class FollowUpForm(forms.ModelForm):
    new_status = forms.ModelChoiceField(
        queryset=Status.objects.all(),
        required=False, 
        label="Atualizar Status",
        widget=forms.Select(attrs={'class': 'form-select'}),
        help_text="Defina o novo status do chamado após este acompanhamento."
    )

    technicians = forms.ModelMultipleChoiceField(
        queryset=User.objects.all(),
        required=False, 
        label="Adicionar Técnicos",
        widget=forms.SelectMultiple(attrs={'class': 'form-select', 'size': '3'}),
        help_text="Segure Ctrl para selecionar vários."
    )

    class Meta:
        model = FollowUp
        fields = ['message', 'attachment'] 
        widgets = {
            'message': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 5,
                'placeholder': 'Descreva detalhadamente o andamento...'
            }),
            'attachment': forms.FileInput(attrs={'class': 'form-control'})
        }