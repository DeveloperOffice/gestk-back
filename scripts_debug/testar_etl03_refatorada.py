"""
Script para testar a ETL 03 refatorada (multi-tenant com CNPJ/CPF como chave)
Valida que a importação está correta e que os dados do Sybase foram mapeados adequadamente
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

def test_etl03_refatorada():
    """Testa a ETL 03 refatorada"""
    
    print("=" * 80)
    print("TESTE DA ETL 03 REFATORADA - Multi-Tenant com CNPJ/CPF")
    print("=" * 80)
    print()
    
    # 1. Verificar Pessoas Jurídicas
    print("1️⃣ Verificando Pessoas Jurídicas...")
    total_pj = PessoaJuridica.objects.count()
    print(f"   📊 Total de PJ: {total_pj}")
    
    # Verificar novos campos do Sybase
    pj_sample = PessoaJuridica.objects.first()
    if pj_sample:
        print(f"\n   Exemplo de PJ: {pj_sample.razao_social}")
        print(f"   - CNPJ: {pj_sample.cnpj}")
        print(f"   - CNAE: {pj_sample.cnae or 'Não informado'}")
        print(f"   - CNAE 2.0: {pj_sample.cnae_20 or 'Não informado'}")
        print(f"   - Usa CNAE 2.0: {'Sim' if pj_sample.usa_cnae_20 else 'Não'}")
        print(f"   - Situação: {pj_sample.situacao or 'Não informado'}")
        print(f"   - Data Cadastro: {pj_sample.data_cadastro or 'Não informado'}")
        print(f"   - Data Inatividade: {pj_sample.data_inatividade or 'Não informado'}")
        print(f"   - CAE: {pj_sample.cae or 'Não informado'}")
        print(f"   - Contador: {pj_sample.contador or 'Não informado'}")
        print(f"   - Email Resp. Legal: {pj_sample.email_resp_legal or 'Não informado'}")
        print(f"   - Certificado Digital: {pj_sample.certificado_digital or 'Não informado'}")
        print(f"   - Regime Fiscal: {pj_sample.regime_fiscal or 'Não informado'}")
        print(f"   - Ramo Atividade: {pj_sample.ramo_atividade or 'Não informado'}")
    
    # 2. Verificar Pessoas Físicas
    print("\n2️⃣ Verificando Pessoas Físicas...")
    total_pf = PessoaFisica.objects.count()
    print(f"   📊 Total de PF: {total_pf}")
    
    # 3. Verificar Contratos
    print("\n3️⃣ Verificando Contratos...")
    total_contratos = Contrato.objects.count()
    contratos_ativos = Contrato.objects.filter(ativo=True).count()
    contratos_inativos = Contrato.objects.filter(ativo=False).count()
    
    print(f"   📊 Total de contratos: {total_contratos}")
    print(f"   ✅ Contratos ativos: {contratos_ativos}")
    print(f"   ❌ Contratos inativos: {contratos_inativos}")
    
    # Verificar formato do id_legado (deve ser CNPJ_Contabilidade-CNPJ_Cliente)
    contrato_sample = Contrato.objects.first()
    if contrato_sample:
        print(f"\n   Exemplo de Contrato:")
        print(f"   - ID Legado: {contrato_sample.id_legado}")
        print(f"   - Contabilidade: {contrato_sample.contabilidade.razao_social}")
        print(f"   - Cliente: {contrato_sample.cliente}")
        print(f"   - Ativo: {'Sim' if contrato_sample.ativo else 'Não'}")
        print(f"   - Data Início: {contrato_sample.data_inicio}")
        print(f"   - Data Término: {contrato_sample.data_termino or 'Indeterminado'}")
    
    # 4. Verificar integridade dos dados
    print("\n4️⃣ Verificando integridade dos dados...")
    
    # Todos os contratos devem ter cliente válido
    pj_content_type = ContentType.objects.get_for_model(PessoaJuridica)
    pf_content_type = ContentType.objects.get_for_model(PessoaFisica)
    
    contratos_pj = Contrato.objects.filter(content_type=pj_content_type).count()
    contratos_pf = Contrato.objects.filter(content_type=pf_content_type).count()
    
    print(f"   📊 Contratos de PJ: {contratos_pj}")
    print(f"   📊 Contratos de PF: {contratos_pf}")
    
    # Verificar se todos os contratos têm contabilidade
    contratos_sem_contabilidade = Contrato.objects.filter(contabilidade__isnull=True).count()
    print(f"   {'✅' if contratos_sem_contabilidade == 0 else '❌'} Contratos sem contabilidade: {contratos_sem_contabilidade}")
    
    # 5. Estatísticas por regime fiscal
    print("\n5️⃣ Estatísticas por Regime Fiscal...")
    simples = PessoaJuridica.objects.filter(regime_fiscal='simples').count()
    presumido = PessoaJuridica.objects.filter(regime_fiscal='presumido').count()
    real = PessoaJuridica.objects.filter(regime_fiscal='real').count()
    nao_informado = PessoaJuridica.objects.filter(regime_fiscal__isnull=True).count()
    
    print(f"   - Simples Nacional: {simples}")
    print(f"   - Lucro Presumido: {presumido}")
    print(f"   - Lucro Real: {real}")
    print(f"   - Não Informado: {nao_informado}")
    
    # 6. Estatísticas por ramo de atividade
    print("\n6️⃣ Estatísticas por Ramo de Atividade...")
    comercio = PessoaJuridica.objects.filter(ramo_atividade='comercio').count()
    industria = PessoaJuridica.objects.filter(ramo_atividade='industria').count()
    servicos = PessoaJuridica.objects.filter(ramo_atividade='servicos').count()
    nao_informado_ramo = PessoaJuridica.objects.filter(ramo_atividade__isnull=True).count()
    
    print(f"   - Comércio: {comercio}")
    print(f"   - Indústria: {industria}")
    print(f"   - Serviços: {servicos}")
    print(f"   - Não Informado: {nao_informado_ramo}")
    
    # 7. Resumo final
    print("\n" + "=" * 80)
    print("RESUMO FINAL")
    print("=" * 80)
    print(f"✅ Total de Pessoas Jurídicas: {total_pj}")
    print(f"✅ Total de Pessoas Físicas: {total_pf}")
    print(f"✅ Total de Contratos: {total_contratos}")
    print(f"✅ Contratos Ativos: {contratos_ativos}")
    print(f"✅ Integridade dos dados: {'OK' if contratos_sem_contabilidade == 0 else 'ERRO'}")
    print()
    print("=" * 80)
    print("TESTE CONCLUÍDO")
    print("=" * 80)

if __name__ == '__main__':
    test_etl03_refatorada()
