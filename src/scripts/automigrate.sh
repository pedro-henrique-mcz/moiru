#!/bin/bash

echo "Iniciando migração..." 

python3 manage.py makemigrations && python3 manage.py migrate 

echo "Migração encerrada"