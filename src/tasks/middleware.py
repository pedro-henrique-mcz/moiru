# tasks/middleware.py
from threading import local

_thread_locals = local()

def get_current_user():
    """Retorna o usuário da requisição atual para ser usado nos signals."""
    return getattr(_thread_locals, 'user', None)

class RequestUserMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Armazena o usuário logado na thread atual
        _thread_locals.user = request.user
        response = self.get_response(request)
        return response