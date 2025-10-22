#!/usr/bin/env python
"""
Script para analisar os 873 erros do ETL 03
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

def analisar_erros_etl03():
    """Analisa os possíveis erros do ETL 03"""
    
    print("="*70)
    print("ANALISE DOS ERROS ETL 03")
    print("="*70)
    
    # 1. Verificar documentos inválidos
    print("\n1. ANALISE DE DOCUMENTOS INVALIDOS:")
    print("-" * 40)
    
    # Buscar registros com CNPJ/CPF inválidos
    pj_invalidas = PessoaJuridica.objects.filter(
        cnpj__isnull=True
    ).exclude(cnpj='')
    
    pf_invalidas = PessoaFisica.objects.filter(
        cpf__isnull=True
    ).exclude(cpf='')
    
    print(f"   Pessoas Jurídicas sem CNPJ: {pj_invalidas.count()}")
    print(f"   Pessoas Físicas sem CPF: {pf_invalidas.count()}")
    
    # 2. Verificar contabilidades não encontradas
    print("\n2. ANALISE DE CONTABILIDADES NAO ENCONTRADAS:")
    print("-" * 40)
    
    # Buscar contratos sem contabilidade
    contratos_sem_contabilidade = Contrato.objects.filter(
        contabilidade__isnull=True
    )
    
    print(f"   Contratos sem contabilidade: {contratos_sem_contabilidade.count()}")
    
    # 3. Verificar clientes não encontrados
    print("\n3. ANALISE DE CLIENTES NAO ENCONTRADOS:")
    print("-" * 40)
    
    # Buscar contratos sem cliente
    contratos_sem_cliente = Contrato.objects.filter(
        content_type__isnull=True
    )
    
    print(f"   Contratos sem cliente: {contratos_sem_cliente.count()}")
    
    # 4. Verificar dados duplicados
    print("\n4. ANALISE DE DADOS DUPLICADOS:")
    print("-" * 40)
    
    # CNPJs duplicados
    from django.db.models import Count
    cnpjs_duplicados = PessoaJuridica.objects.values('cnpj').annotate(
        count=Count('cnpj')
    ).filter(count__gt=1)
    
    # CPFs duplicados
    cpfs_duplicados = PessoaFisica.objects.values('cpf').annotate(
        count=Count('cpf')
    ).filter(count__gt=1)
    
    print(f"   CNPJs duplicados: {cnpjs_duplicados.count()}")
    print(f"   CPFs duplicados: {cpfs_duplicados.count()}")
    
    # 5. Verificar campos obrigatórios
    print("\n5. ANALISE DE CAMPOS OBRIGATORIOS:")
    print("-" * 40)
    
    # Pessoas Jurídicas sem razão social
    pj_sem_razao = PessoaJuridica.objects.filter(
        razao_social__isnull=True
    ).exclude(razao_social='')
    
    # Pessoas Físicas sem nome
    pf_sem_nome = PessoaFisica.objects.filter(
        nome_completo__isnull=True
    ).exclude(nome_completo='')
    
    print(f"   Pessoas Jurídicas sem razão social: {pj_sem_razao.count()}")
    print(f"   Pessoas Físicas sem nome: {pf_sem_nome.count()}")
    
    # 6. Verificar integridade referencial
    print("\n6. ANALISE DE INTEGRIDADE REFERENCIAL:")
    print("-" * 40)
    
    # Contratos com content_type inválido
    contratos_content_type_invalido = Contrato.objects.filter(
        content_type__isnull=False
    ).exclude(
        content_type__in=ContentType.objects.filter(
            model__in=['pessoajuridica', 'pessoafisica']
        )
    )
    
    print(f"   Contratos com content_type inválido: {contratos_content_type_invalido.count()}")
    
    # 7. Verificar dados de regime tributário
    print("\n7. ANALISE DE REGIME TRIBUTARIO:")
    print("-" * 40)
    
    # Pessoas Jurídicas sem regime tributário
    pj_sem_regime = PessoaJuridica.objects.filter(
        regime_tributario__isnull=True
    ).exclude(regime_tributario='')
    
    print(f"   Pessoas Jurídicas sem regime tributário: {pj_sem_regime.count()}")
    
    # 8. Verificar CNAEs
    print("\n8. ANALISE DE CNAEs:")
    print("-" * 40)
    
    # Pessoas Jurídicas sem CNAE principal
    pj_sem_cnae = PessoaJuridica.objects.filter(
        cnae_principal__isnull=True
    )
    
    print(f"   Pessoas Jurídicas sem CNAE principal: {pj_sem_cnae.count()}")
    
    # 9. Resumo geral
    print("\n9. RESUMO GERAL:")
    print("-" * 40)
    
    total_pj = PessoaJuridica.objects.count()
    total_pf = PessoaFisica.objects.count()
    total_contratos = Contrato.objects.count()
    total_contabilidades = Contabilidade.objects.count()
    
    print(f"   Total de Pessoas Jurídicas: {total_pj}")
    print(f"   Total de Pessoas Físicas: {total_pf}")
    print(f"   Total de Contratos: {total_contratos}")
    print(f"   Total de Contabilidades: {total_contabilidades}")
    
    # 10. Sugestões de correção
    print("\n10. SUGESTOES DE CORRECAO:")
    print("-" * 40)
    
    print("   - Verificar se os CNPJs/CPFs estão sendo validados corretamente")
    print("   - Verificar se as contabilidades estão sendo criadas antes dos contratos")
    print("   - Verificar se os clientes estão sendo criados antes dos contratos")
    print("   - Verificar se os campos obrigatórios estão sendo preenchidos")
    print("   - Verificar se há problemas de encoding nos dados do Sybase")
    print("   - Verificar se há problemas de conexão com o banco Sybase")
    
    print("\n" + "="*70)
    print("ANALISE CONCLUIDA")
    print("="*70)

if __name__ == "__main__":
    analisar_erros_etl03()
