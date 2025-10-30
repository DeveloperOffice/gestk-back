"""
Script para investigar como os vínculos empregatícios estão salvos
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

def investigar_vinculos():
    """Investiga como os vínculos estão salvos no banco"""
    print("=== INVESTIGANDO ESTRUTURA DOS VINCULOS ===\n")
    
    # 1. Buscar contabilidade OFFICE
    contabilidade = Contabilidade.objects.filter(
        razao_social="ASSESSORIA CONTABIL OFFICE LTDA"
    ).first()
    
    if not contabilidade:
        print("ERRO: Contabilidade não encontrada!")
        return
    
    print(f"Contabilidade: {contabilidade.razao_social}")
    print(f"ID: {contabilidade.id}\n")
    
    # 2. Pegar alguns vínculos da contabilidade
    print("=== ANALISANDO VINCULOS COM contabilidade=contabilidade ===")
    vinculos_amostra = VinculoEmpregaticio.objects.filter(
        contabilidade=contabilidade
    )[:5]
    
    for i, vinculo in enumerate(vinculos_amostra, 1):
        print(f"\nVínculo {i}:")
        print(f"  - ID: {vinculo.id}")
        print(f"  - Funcionário: {vinculo.funcionario.pessoa_fisica.nome_completo}")
        print(f"  - Contabilidade: {vinculo.contabilidade.razao_social}")
        print(f"  - Content Type: {vinculo.content_type}")
        print(f"  - Object ID: {vinculo.object_id}")
        
        # Tentar recuperar o objeto empresa
        if vinculo.content_type and vinculo.object_id:
            try:
                empresa_obj = vinculo.empresa
                if isinstance(empresa_obj, PessoaJuridica):
                    print(f"  - Empresa (GenericFK): {empresa_obj.razao_social} - CNPJ: {empresa_obj.cnpj}")
                elif isinstance(empresa_obj, Contabilidade):
                    print(f"  - Empresa (GenericFK): {empresa_obj.razao_social} (É uma Contabilidade!)")
                else:
                    print(f"  - Empresa (GenericFK): {type(empresa_obj)} - {empresa_obj}")
            except Exception as e:
                print(f"  - Erro ao recuperar empresa: {e}")
        else:
            print("  - Empresa (GenericFK): Não definida")
    
    # 3. Verificar ContentTypes disponíveis
    print("\n=== CONTENT TYPES DISPONÍVEIS ===")
    ct_pj = ContentType.objects.get_for_model(PessoaJuridica)
    ct_cont = ContentType.objects.get_for_model(Contabilidade)
    
    print(f"ContentType PessoaJuridica: {ct_pj}")
    print(f"ContentType Contabilidade: {ct_cont}")
    
    # 4. Contar vínculos por ContentType
    print("\n=== CONTAGEM POR CONTENT TYPE ===")
    vinculos_pj = VinculoEmpregaticio.objects.filter(
        contabilidade=contabilidade,
        content_type=ct_pj
    ).count()
    
    vinculos_cont = VinculoEmpregaticio.objects.filter(
        contabilidade=contabilidade,
        content_type=ct_cont
    ).count()
    
    vinculos_null = VinculoEmpregaticio.objects.filter(
        contabilidade=contabilidade,
        content_type__isnull=True
    ).count()
    
    print(f"Vínculos com PessoaJuridica como empregador: {vinculos_pj}")
    print(f"Vínculos com Contabilidade como empregador: {vinculos_cont}")
    print(f"Vínculos sem empregador definido (null): {vinculos_null}")
    
    # 5. Verificar se a própria contabilidade tem PessoaJuridica
    print("\n=== VERIFICANDO SE A CONTABILIDADE TEM PJ ASSOCIADA ===")
    pj_contabilidade = PessoaJuridica.objects.filter(cnpj=contabilidade.cnpj).first()
    if pj_contabilidade:
        print(f"PJ encontrada: {pj_contabilidade.razao_social}")
        print(f"ID da PJ: {pj_contabilidade.id}")
        
        # Verificar vínculos dessa PJ
        vinculos_pj_contabilidade = VinculoEmpregaticio.objects.filter(
            content_type=ct_pj,
            object_id=pj_contabilidade.id
        ).count()
        print(f"Vínculos onde esta PJ é empregador: {vinculos_pj_contabilidade}")

if __name__ == "__main__":
    investigar_vinculos()
