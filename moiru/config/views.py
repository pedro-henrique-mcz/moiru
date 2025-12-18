from django.http import HttpResponse

# Toda view PRECISA receber pelo menos um argumento (request)
def home(request):
    # Aqui a gente processaria dados, banco de dados, etc.
    
    # Por fim, retornamos a resposta
    return HttpResponse("Olá, Pedro! Minha primeira view funcionou.")