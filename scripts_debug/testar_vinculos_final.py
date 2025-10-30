"""
Script final para testar vínculos da contabilidade
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
from apps.pessoas.models import PessoaJuridica
from apps.funcionarios.models import VinculoEmpregaticio
from datetime import date
from django.db.models import Q

def testar_vinculos_final():
    """Teste final dos vínculos"""
    print("=== TESTE FINAL - VÍNCULOS DA CONTABILIDADE ===\n")
    
    # 1. Buscar contabilidade
    contabilidade = Contabilidade.objects.filter(
        razao_social="ASSESSORIA CONTABIL OFFICE LTDA"
    ).first()
    
    if not contabilidade:
        print("ERRO: Contabilidade não encontrada!")
        return
    
    print(f"Contabilidade: {contabilidade.razao_social}")
    print(f"CNPJ: {contabilidade.cnpj}\n")
    
    # 2. Buscar PJ da contabilidade
    pj_contabilidade = PessoaJuridica.objects.filter(
        cnpj=contabilidade.cnpj
    ).first()
    
    if pj_contabilidade:
        print(f"PessoaJuridica da contabilidade encontrada:")
        print(f"  - Razão Social: {pj_contabilidade.razao_social}")
        print(f"  - ID: {pj_contabilidade.id}")
        
        # 3. Contar vínculos onde a PJ é empregador
        pj_content_type = ContentType.objects.get_for_model(PessoaJuridica)
        
        vinculos_total = VinculoEmpregaticio.objects.filter(
            content_type=pj_content_type,
            object_id=pj_contabilidade.id,
            ativo=True
        ).count()
        
        print(f"\nTotal de funcionários internos ativos: {vinculos_total}")
        
        # 4. Teste com data específica (outubro 2025)
        mes_data = date(2025, 10, 1)
        vinculos_outubro = VinculoEmpregaticio.objects.filter(
            content_type=pj_content_type,
            object_id=pj_contabilidade.id,
            data_admissao__lte=mes_data
        ).filter(
            Q(data_demissao__gte=mes_data) | Q(data_demissao__isnull=True),
            ativo=True
        ).count()
        
        print(f"Funcionários internos ativos em outubro/2025: {vinculos_outubro}")
        
        # 5. Listar alguns exemplos
        if vinculos_total > 0:
            print("\n=== EXEMPLOS DE FUNCIONÁRIOS INTERNOS ===")
            exemplos = VinculoEmpregaticio.objects.filter(
                content_type=pj_content_type,
                object_id=pj_contabilidade.id,
                ativo=True
            ).select_related('funcionario__pessoa_fisica', 'cargo')[:5]
            
            for vinculo in exemplos:
                print(f"\n  Funcionário: {vinculo.funcionario.pessoa_fisica.nome_completo}")
                print(f"  Cargo: {vinculo.cargo.nome if vinculo.cargo else 'Não informado'}")
                print(f"  Data Admissão: {vinculo.data_admissao}")
        else:
            print("\nNenhum funcionário interno encontrado para esta contabilidade.")
            print("Isso pode indicar que:")
            print("1. Os funcionários não foram cadastrados ainda")
            print("2. Estão cadastrados em outra empresa do grupo")
            print("3. A contabilidade usa outra forma de registro")
    else:
        print("AVISO: Não foi encontrada uma PessoaJuridica para esta contabilidade!")
        print("Isso explica porque não há vínculos internos.")
        
    print("\n=== RESUMO ===")
    print(f"O valor correto de 'vinculos_folhas_ativos' para o dashboard é: {vinculos_outubro if pj_contabilidade else 0}")

if __name__ == "__main__":
    testar_vinculos_final()

