#!/usr/bin/env python
"""
Script para verificar as tabelas do banco
"""

import os
import sys
import django

# Configurar Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gestk.settings')
django.setup()

from django.db import connection

def verificar_tabelas():
    """Verifica as tabelas do banco"""
    
    print("="*70)
    print("VERIFICACAO DAS TABELAS DO BANCO")
    print("="*70)
    
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name LIKE '%pessoa%'
            ORDER BY table_name
        """)
        tabelas = cursor.fetchall()
    
    print("\nTabelas relacionadas a pessoas:")
    for tabela in tabelas:
        print(f"   - {tabela[0]}")
    
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name LIKE '%contrato%'
            ORDER BY table_name
        """)
        tabelas = cursor.fetchall()
    
    print("\nTabelas relacionadas a contratos:")
    for tabela in tabelas:
        print(f"   - {tabela[0]}")
    
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name LIKE '%contabilidade%'
            ORDER BY table_name
        """)
        tabelas = cursor.fetchall()
    
    print("\nTabelas relacionadas a contabilidade:")
    for tabela in tabelas:
        print(f"   - {tabela[0]}")

if __name__ == "__main__":
    verificar_tabelas()
