#!/bin/bash

# Entra na pasta correta (Segurança)
cd /home/umj/main

echo "🔄 Iniciando atualização do Moiru..."

# 1. Puxa as novidades do Git
git pull origin main

# 2. Ativa o ambiente virtual
source .venv/bin/activate

# 3. Instala bibliotecas novas
# Nota: Vi na imagem que você tem 'requirements.txt' e 'requiriments.txt'. 
# Estou usando o correto (requirements.txt).
pip install -r requirements.txt

# 4. Aplica migrações no banco de dados
python manage.py migrate

# 5. Coleta arquivos estáticos
python manage.py collectstatic --noinput

# 6. Reinicia o Gunicorn
echo "♻️ Reiniciando o servidor..."
sudo systemctl restart moiru

echo "✅ Atualização concluída com sucesso!"
