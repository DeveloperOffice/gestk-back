"""
Script para testar a contagem de vínculos empregatícios do dashboard do escritório
"""
import os
import sys
import django

# Configurar Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gestk.settings')
django.setup()

from django.contrib.contenttypes.models import ContentType
from apps.core.models import Contabilidade
from apps.pessoas.models import PessoaJuridica, Contrato
from apps.funcionarios.models import VinculoEmpregaticio
from datetime import date
from django.db.models import Q

def testar_contagem_vinculos():
    """Testa a contagem de vínculos empregatícios"""
    print("=== TESTE DE CONTAGEM DE VÍNCULOS EMPREGATÍCIOS ===\n")
    
    # 1. Buscar uma contabilidade de exemplo
    contabilidade = Contabilidade.objects.filter(
        razao_social="ASSESSORIA CONTABIL OFFICE LTDA"
    ).first()
    
    if not contabilidade:
        print("ERRO: Contabilidade OFFICE não encontrada!")
        return
    
    print(f"OK - Contabilidade encontrada: {contabilidade.razao_social}")
    print(f"   CNPJ: {contabilidade.cnpj}")
    print(f"   ID: {contabilidade.id}")
    
    # 2. Listar vínculos DA contabilidade (errado)
    print("\n=== VÍNCULOS DA PRÓPRIA CONTABILIDADE (ERRADO) ===")
    vinculos_proprios = VinculoEmpregaticio.objects.filter(
        contabilidade=contabilidade,
        ativo=True
    ).count()
    print(f"ERRO: Total de vínculos usando contabilidade=contabilidade: {vinculos_proprios}")
    
    # 3. Listar vínculos dos CLIENTES da contabilidade (correto)
    print("\n=== VÍNCULOS DOS CLIENTES DA CONTABILIDADE (CORRETO) ===")
    
    # Buscar contratos ativos
    contratos_ativos = Contrato.objects.filter(
        contabilidade=contabilidade,
        ativo=True
    )
    print(f"OK - Total de contratos ativos: {contratos_ativos.count()}")
    
    # Obter PessoasJuridicas clientes
    pj_content_type = ContentType.objects.get_for_model(PessoaJuridica)
    empresas_clientes_ids = contratos_ativos.filter(
        content_type=pj_content_type
    ).values_list('object_id', flat=True).distinct()
    
    print(f"OK - Total de empresas (PJ) clientes: {len(list(empresas_clientes_ids))}")
    
    # Contar vínculos empregatícios dos clientes
    vinculos_clientes = VinculoEmpregaticio.objects.filter(
        content_type=pj_content_type,
        object_id__in=empresas_clientes_ids,
        ativo=True
    ).count()
    
    print(f"OK - Total de vínculos empregatícios dos clientes: {vinculos_clientes}")
    
    # 4. Mostrar alguns exemplos
    print("\n=== EXEMPLOS DE EMPRESAS CLIENTES E SEUS VÍNCULOS ===")
    empresas_exemplo = PessoaJuridica.objects.filter(
        id__in=list(empresas_clientes_ids)[:5]
    )
    
    for empresa in empresas_exemplo:
        vinculos_empresa = VinculoEmpregaticio.objects.filter(
            content_type=pj_content_type,
            object_id=empresa.id,
            ativo=True
        ).count()
        
        print(f"\n   Empresa: {empresa.razao_social}")
        print(f"   CNPJ: {empresa.cnpj}")
        print(f"   Vínculos ativos: {vinculos_empresa}")
    
    # 5. Testar com data específica (outubro 2025)
    print("\n=== TESTE COM DATA ESPECÍFICA (OUTUBRO 2025) ===")
    mes_data = date(2025, 10, 1)
    
    vinculos_outubro = VinculoEmpregaticio.objects.filter(
        content_type=pj_content_type,
        object_id__in=empresas_clientes_ids,
        data_admissao__lte=mes_data
    ).filter(
        Q(data_demissao__gte=mes_data) | Q(data_demissao__isnull=True),
        ativo=True
    ).count()
    
    print(f"OK - Vínculos ativos em outubro/2025: {vinculos_outubro}")
    
    print("\n=== RESUMO ===")
    print(f"ERRO: Contagem ERRADA (vínculos da contabilidade): {vinculos_proprios}")
    print(f"OK - Contagem CORRETA (vínculos dos clientes): {vinculos_clientes}")
    print(f"   Diferença: {vinculos_clientes - vinculos_proprios}")

if __name__ == "__main__":
    testar_contagem_vinculos()
