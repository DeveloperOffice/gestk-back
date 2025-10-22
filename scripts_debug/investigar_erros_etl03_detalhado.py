#!/usr/bin/env python
"""
Script para investigar os 873 erros do ETL 03 de forma mais detalhada
"""

import os
import sys
import django

# Configurar Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gestk.settings')
django.setup()

from apps.pessoas.models import PessoaJuridica, PessoaFisica, Contrato
from apps.core.models import Contabilidade
from django.contrib.contenttypes.models import ContentType
from django.db import connection

def investigar_erros_etl03():
    """Investiga os 873 erros do ETL 03"""
    
    print("="*70)
    print("INVESTIGACAO DETALHADA DOS 873 ERROS ETL 03")
    print("="*70)
    
    # 1. Verificar se há problemas de encoding
    print("\n1. VERIFICACAO DE ENCODING:")
    print("-" * 40)
    
    # Buscar registros com caracteres especiais (usando LIKE)
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT COUNT(*) 
            FROM pessoas_juridicas 
            WHERE razao_social LIKE '%ã%' OR razao_social LIKE '%ç%' OR razao_social LIKE '%é%'
        """)
        pj_encoding = cursor.fetchone()[0]
        
        cursor.execute("""
            SELECT COUNT(*) 
            FROM pessoas_fisicas 
            WHERE nome_completo LIKE '%ã%' OR nome_completo LIKE '%ç%' OR nome_completo LIKE '%é%'
        """)
        pf_encoding = cursor.fetchone()[0]
    
    print(f"   Pessoas Jurídicas com caracteres especiais: {pj_encoding}")
    print(f"   Pessoas Físicas com caracteres especiais: {pf_encoding}")
    
    # 2. Verificar se há problemas de validação de CNPJ/CPF
    print("\n2. VERIFICACAO DE VALIDACAO CNPJ/CPF:")
    print("-" * 40)
    
    # CNPJs inválidos (não 14 dígitos)
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT COUNT(*) 
            FROM pessoas_juridicas 
            WHERE LENGTH(REPLACE(REPLACE(REPLACE(cnpj, '.', ''), '/', ''), '-', '')) != 14
        """)
        cnpj_invalidos = cursor.fetchone()[0]
        
        cursor.execute("""
            SELECT COUNT(*) 
            FROM pessoas_fisicas 
            WHERE LENGTH(REPLACE(REPLACE(REPLACE(cpf, '.', ''), '/', ''), '-', '')) != 11
        """)
        cpf_invalidos = cursor.fetchone()[0]
    
    print(f"   CNPJs com formato inválido: {cnpj_invalidos}")
    print(f"   CPFs com formato inválido: {cpf_invalidos}")
    
    # 3. Verificar se há problemas de dados nulos
    print("\n3. VERIFICACAO DE DADOS NULOS:")
    print("-" * 40)
    
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT COUNT(*) 
            FROM pessoas_juridicas 
            WHERE razao_social IS NULL OR razao_social = ''
        """)
        pj_razao_nula = cursor.fetchone()[0]
        
        cursor.execute("""
            SELECT COUNT(*) 
            FROM pessoas_fisicas 
            WHERE nome_completo IS NULL OR nome_completo = ''
        """)
        pf_nome_nulo = cursor.fetchone()[0]
    
    print(f"   Pessoas Jurídicas sem razão social: {pj_razao_nula}")
    print(f"   Pessoas Físicas sem nome: {pf_nome_nulo}")
    
    # 4. Verificar se há problemas de integridade referencial
    print("\n4. VERIFICACAO DE INTEGRIDADE REFERENCIAL:")
    print("-" * 40)
    
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT COUNT(*) 
            FROM pessoas_contratos 
            WHERE contabilidade_id IS NULL
        """)
        contratos_sem_contabilidade = cursor.fetchone()[0]
        
        cursor.execute("""
            SELECT COUNT(*) 
            FROM pessoas_contratos 
            WHERE content_type_id IS NULL
        """)
        contratos_sem_cliente = cursor.fetchone()[0]
    
    print(f"   Contratos sem contabilidade: {contratos_sem_contabilidade}")
    print(f"   Contratos sem cliente: {contratos_sem_cliente}")
    
    # 5. Verificar se há problemas de regime tributário
    print("\n5. VERIFICACAO DE REGIME TRIBUTARIO:")
    print("-" * 40)
    
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT COUNT(*) 
            FROM pessoas_juridicas 
            WHERE regime_tributario IS NULL OR regime_tributario = ''
        """)
        pj_sem_regime = cursor.fetchone()[0]
        
        cursor.execute("""
            SELECT regime_tributario, COUNT(*) 
            FROM pessoas_juridicas 
            WHERE regime_tributario IS NOT NULL AND regime_tributario != ''
            GROUP BY regime_tributario
            ORDER BY COUNT(*) DESC
        """)
        regimes = cursor.fetchall()
    
    print(f"   Pessoas Jurídicas sem regime tributário: {pj_sem_regime}")
    print("   Distribuição dos regimes tributários:")
    for regime, count in regimes:
        print(f"     - {regime}: {count}")
    
    # 6. Verificar se há problemas de CNAE
    print("\n6. VERIFICACAO DE CNAE:")
    print("-" * 40)
    
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT COUNT(*) 
            FROM pessoas_juridicas 
            WHERE cnae_principal_id IS NULL
        """)
        pj_sem_cnae = cursor.fetchone()[0]
        
        cursor.execute("""
            SELECT COUNT(*) 
            FROM pessoas_juridicas 
            WHERE cnae_principal_id IS NOT NULL
        """)
        pj_com_cnae = cursor.fetchone()[0]
    
    print(f"   Pessoas Jurídicas sem CNAE principal: {pj_sem_cnae}")
    print(f"   Pessoas Jurídicas com CNAE principal: {pj_com_cnae}")
    
    # 7. Verificar se há problemas de duplicação
    print("\n7. VERIFICACAO DE DUPLICACAO:")
    print("-" * 40)
    
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT cnpj, COUNT(*) 
            FROM pessoas_juridicas 
            GROUP BY cnpj 
            HAVING COUNT(*) > 1
            ORDER BY COUNT(*) DESC
            LIMIT 10
        """)
        cnpjs_duplicados = cursor.fetchall()
        
        cursor.execute("""
            SELECT cpf, COUNT(*) 
            FROM pessoas_fisicas 
            GROUP BY cpf 
            HAVING COUNT(*) > 1
            ORDER BY COUNT(*) DESC
            LIMIT 10
        """)
        cpfs_duplicados = cursor.fetchall()
    
    print(f"   CNPJs duplicados (top 10): {len(cnpjs_duplicados)}")
    for cnpj, count in cnpjs_duplicados:
        print(f"     - {cnpj}: {count} registros")
    
    print(f"   CPFs duplicados (top 10): {len(cpfs_duplicados)}")
    for cpf, count in cpfs_duplicados:
        print(f"     - {cpf}: {count} registros")
    
    # 8. Verificar se há problemas de campos obrigatórios
    print("\n8. VERIFICACAO DE CAMPOS OBRIGATORIOS:")
    print("-" * 40)
    
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT COUNT(*) 
            FROM pessoas_juridicas 
            WHERE cnpj IS NULL OR cnpj = ''
        """)
        pj_sem_cnpj = cursor.fetchone()[0]
        
        cursor.execute("""
            SELECT COUNT(*) 
            FROM pessoas_fisicas 
            WHERE cpf IS NULL OR cpf = ''
        """)
        pf_sem_cpf = cursor.fetchone()[0]
    
    print(f"   Pessoas Jurídicas sem CNPJ: {pj_sem_cnpj}")
    print(f"   Pessoas Físicas sem CPF: {pf_sem_cpf}")
    
    # 9. Resumo dos possíveis erros
    print("\n9. RESUMO DOS POSSIVEIS ERROS:")
    print("-" * 40)
    
    total_erros = (cnpj_invalidos + cpf_invalidos + pj_razao_nula + pf_nome_nulo + 
                   contratos_sem_contabilidade + contratos_sem_cliente + 
                   pj_sem_regime + pj_sem_cnae + pj_sem_cnpj + pf_sem_cpf)
    
    print(f"   Total de possíveis erros identificados: {total_erros}")
    print(f"   Erros de validação CNPJ/CPF: {cnpj_invalidos + cpf_invalidos}")
    print(f"   Erros de dados nulos: {pj_razao_nula + pf_nome_nulo}")
    print(f"   Erros de integridade referencial: {contratos_sem_contabilidade + contratos_sem_cliente}")
    print(f"   Erros de regime tributário: {pj_sem_regime}")
    print(f"   Erros de CNAE: {pj_sem_cnae}")
    print(f"   Erros de campos obrigatórios: {pj_sem_cnpj + pf_sem_cpf}")
    
    # 10. Sugestões de correção
    print("\n10. SUGESTOES DE CORRECAO:")
    print("-" * 40)
    
    if cnpj_invalidos > 0 or cpf_invalidos > 0:
        print("   - Implementar validação de CNPJ/CPF no ETL")
        print("   - Verificar se os dados do Sybase estão corretos")
    
    if pj_razao_nula > 0 or pf_nome_nulo > 0:
        print("   - Implementar valores padrão para campos obrigatórios")
        print("   - Verificar se os dados do Sybase estão completos")
    
    if contratos_sem_contabilidade > 0 or contratos_sem_cliente > 0:
        print("   - Verificar se as contabilidades estão sendo criadas antes dos contratos")
        print("   - Verificar se os clientes estão sendo criados antes dos contratos")
    
    if pj_sem_regime > 0:
        print("   - Verificar se o regime tributário está sendo mapeado corretamente")
        print("   - Implementar valor padrão para regime tributário")
    
    if pj_sem_cnae > 0:
        print("   - Verificar se os CNAEs estão sendo mapeados corretamente")
        print("   - Verificar se a tabela CNAE está populada")
    
    print("\n" + "="*70)
    print("INVESTIGACAO CONCLUIDA")
    print("="*70)

if __name__ == "__main__":
    investigar_erros_etl03()
