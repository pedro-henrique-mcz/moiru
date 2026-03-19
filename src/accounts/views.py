from django.contrib.auth.views import LoginView
from django.shortcuts import redirect

class CustomLoginView(LoginView):
    template_name = 'accounts/auth.html'
    redirect_authenticated_user = True

    def form_valid(self, form):
        # Chama a lógica padrão de login do Django primeiro
        result = super().form_valid(form)

        # Verifica se o checkbox 'remember_me' foi marcado no HTML
        remember_me = self.request.POST.get('remember_me')

        if remember_me:
            # Se marcou: Define a sessão para expirar em 2 semanas (1209600 segundos)
            # Você pode alterar esse valor se quiser mais ou menos tempo
            self.request.session.set_expiry(1209600) 
        else:
            # Se NÃO marcou: Define para 0 (significa: expira ao fechar o navegador)
            self.request.session.set_expiry(0)

        return result