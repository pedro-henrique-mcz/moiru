from django.shortcuts import redirect
from django.urls import reverse

class ForcePasswordChangeMiddleware:
    """
    Intercepta todas as requisições. Se o usuário estiver logado e a flag 
    force_password_change for True, ele é bloqueado em qualquer tela.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated and not request.user.is_superuser:
            if hasattr(request.user, 'info') and request.user.info.force_password_change:
                
                # Lista de rotas que ele TEM permissão de acessar enquanto está bloqueado
                allowed_paths = [reverse('force_password_change'), reverse('logout')] # Substitua 'logout' pelo name da sua url de logout se for diferente
                
                if request.path not in allowed_paths and not request.path.startswith('/static/'):
                    # Bloqueia e redireciona
                    return redirect('force_password_change')
        
        return self.get_response(request)