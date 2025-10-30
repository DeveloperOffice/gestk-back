"""
Script para testar a contagem de vínculos empregatícios internos da contabilidade
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
from apps.pessoas.models import PessoaJuridica, PessoaFisica
from apps.funcionarios.models import VinculoEmpregaticio
from datetime import date
from django.db.models import Q

def testar_vinculos_internos():
    """Testa a contagem de vínculos empregatícios internos da contabilidade"""
    print("=== TESTE DE VINCULOS INTERNOS DA CONTABILIDADE ===\n")
    
    # 1. Buscar a contabilidade OFFICE
    contabilidade = Contabilidade.objects.filter(
        razao_social="ASSESSORIA CONTABIL OFFICE LTDA"
    ).first()
    
    if not contabilidade:
        print("ERRO: Contabilidade OFFICE não encontrada!")
        return
    
    print(f"OK - Contabilidade encontrada: {contabilidade.razao_social}")
    print(f"   CNPJ: {contabilidade.cnpj}")
    print(f"   ID: {contabilidade.id}")
    
    # 2. Buscar ContentType da Contabilidade
    print("\n=== VERIFICANDO VINCULOS ONDE A CONTABILIDADE É O EMPREGADOR ===")
    contabilidade_content_type = ContentType.objects.get_for_model(Contabilidade)
    print(f"ContentType da Contabilidade: {contabilidade_content_type}")
    
    # 3. Contar vínculos onde a contabilidade é o empregador (correto)
    vinculos_corretos = VinculoEmpregaticio.objects.filter(
        content_type=contabilidade_content_type,
        object_id=contabilidade.id,
        ativo=True
    ).count()
    
    print(f"\nOK - Vínculos onde a contabilidade é o EMPREGADOR: {vinculos_corretos}")
    print("     (Estes são os funcionários internos: auxiliares contábeis, fiscais, etc.)")
    
    # 4. Listar alguns exemplos desses vínculos
    print("\n=== EXEMPLOS DE FUNCIONÁRIOS INTERNOS ===")
    vinculos_exemplos = VinculoEmpregaticio.objects.filter(
        content_type=contabilidade_content_type,
        object_id=contabilidade.id,
        ativo=True
    ).select_related('funcionario__pessoa_fisica', 'cargo')[:10]
    
    for vinculo in vinculos_exemplos:
        print(f"\n   Funcionário: {vinculo.funcionario.pessoa_fisica.nome_razao_social}")
        print(f"   CPF: {vinculo.funcionario.pessoa_fisica.cpf}")
        print(f"   Matrícula: {vinculo.matricula}")
        print(f"   Cargo: {vinculo.cargo.nome if vinculo.cargo else 'Não informado'}")
        print(f"   Data Admissão: {vinculo.data_admissao}")
    
    # 5. Verificar vínculos usando contabilidade=contabilidade (forma antiga/errada)
    print("\n=== COMPARAÇÃO COM MÉTODO ANTIGO ===")
    vinculos_antigos = VinculoEmpregaticio.objects.filter(
        contabilidade=contabilidade,
        ativo=True
    ).count()
    
    print(f"Vínculos usando contabilidade=contabilidade: {vinculos_antigos}")
    print(f"Vínculos onde contabilidade é o empregador: {vinculos_corretos}")
    
    # 6. Teste com data específica (outubro 2025)
    print("\n=== TESTE COM DATA ESPECÍFICA (OUTUBRO 2025) ===")
    mes_data = date(2025, 10, 1)
    
    vinculos_outubro = VinculoEmpregaticio.objects.filter(
        content_type=contabilidade_content_type,
        object_id=contabilidade.id,
        data_admissao__lte=mes_data
    ).filter(
        Q(data_demissao__gte=mes_data) | Q(data_demissao__isnull=True),
        ativo=True
    ).count()
    
    print(f"Vínculos internos ativos em outubro/2025: {vinculos_outubro}")
    
    print("\n=== RESUMO FINAL ===")
    print(f"A contabilidade '{contabilidade.razao_social}' possui:")
    print(f"  - {vinculos_corretos} funcionários internos ativos")
    print(f"  - {vinculos_outubro} funcionários internos ativos em outubro/2025")
    print("\nEstes números representam apenas os funcionários da própria contabilidade")
    print("(auxiliares contábeis, fiscais, pessoal administrativo, etc.)")

if __name__ == "__main__":
    testar_vinculos_internos()

