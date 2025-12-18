from django.shortcuts import render # <--- Importe o render (geralmente já vem importado)
# from django.http import HttpResponse (pode apagar ou comentar esse)

def home(request, nome):

    context = {
        'nome':nome,
        'chamados':['aprender django', 'fazer sistema de auth', 'devolver chave'],
        'adm':True,
    }
    
    return render(request, 'index.html', context)