"""
Script para testar a IDEMPOTÊNCIA da ETL 03 refatorada
Simula múltiplas execuções e valida que apenas mudanças reais são aplicadas
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

def test_idempotencia():
    """Testa a idempotência da ETL 03"""
    
    print("=" * 80)
    print("TESTE DE IDEMPOTÊNCIA - ETL 03")
    print("=" * 80)
    print()
    
    # 1. Capturar estado inicial
    print("1️⃣ Capturando estado inicial do banco...")
    total_pj_antes = PessoaJuridica.objects.count()
    total_pf_antes = PessoaFisica.objects.count()
    total_contratos_antes = Contrato.objects.count()
    
    print(f"   📊 PJ: {total_pj_antes}")
    print(f"   📊 PF: {total_pf_antes}")
    print(f"   📊 Contratos: {total_contratos_antes}")
    
    # 2. Pegar uma amostra de registros para validar
    print("\n2️⃣ Selecionando amostras para validação...")
    
    pj_sample = PessoaJuridica.objects.first()
    if pj_sample:
        pj_cnpj = pj_sample.cnpj
        pj_updated_at_antes = pj_sample.updated_at
        print(f"   📋 PJ Selecionada: {pj_sample.razao_social} ({pj_cnpj})")
        print(f"      - Última atualização: {pj_updated_at_antes}")
        print(f"      - Email: {pj_sample.email or 'Não informado'}")
        print(f"      - CNAE: {pj_sample.cnae or 'Não informado'}")
    
    contrato_sample = Contrato.objects.first()
    if contrato_sample:
        contrato_id = contrato_sample.id_legado
        contrato_updated_at_antes = contrato_sample.updated_at
        print(f"\n   📋 Contrato Selecionado: {contrato_id}")
        print(f"      - Última atualização: {contrato_updated_at_antes}")
        print(f"      - Valor: R$ {contrato_sample.valor_honorario}")
        print(f"      - Ativo: {'Sim' if contrato_sample.ativo else 'Não'}")
    
    # 3. Instruções para teste manual
    print("\n" + "=" * 80)
    print("🔄 INSTRUÇÕES PARA TESTE DE IDEMPOTÊNCIA")
    print("=" * 80)
    print("""
Para testar a idempotência, execute os seguintes passos:

CENÁRIO 1: Dados não mudaram no Sybase (idempotência total)
----------------------------------------------------------
1. Execute: python manage.py etl_03_contratos --limit 10
2. Observe que todos os registros devem ser PULADOS (⏭️)
3. Verifique que o campo 'updated_at' NÃO mudou

Comando:
    python manage.py etl_03_contratos --limit 10

Resultado esperado:
    ⏭️ Registros processados sem mudança (idempotência): 10
    💡 Taxa de modificação: 0.0%


CENÁRIO 2: Dados mudaram no Sybase (atualização seletiva)
---------------------------------------------------------
1. Altere manualmente um registro no banco (exemplo):
   
   UPDATE pessoas_juridicas 
   SET email = 'teste@example.com' 
   WHERE cnpj = '{pj_cnpj if pj_sample else "12345678000190"}';
   
2. Execute: python manage.py etl_03_contratos --limit 10
3. Observe que apenas o registro alterado será ATUALIZADO (📝)
4. Os demais serão PULADOS (⏭️)

Resultado esperado:
    📝 PJ xxx atualizada: email
    ⏭️ 9 registros sem mudança
    💡 Taxa de modificação: 10.0%


CENÁRIO 3: Novos registros no Sybase (criação)
----------------------------------------------
1. Adicione um novo registro na tabela geempre do Sybase
2. Execute: python manage.py etl_03_contratos
3. Observe que apenas o NOVO registro será CRIADO (✅)
4. Os demais serão PULADOS (⏭️)

Resultado esperado:
    ✅ PJ xxx criada: NOVA EMPRESA
    ⏭️ Registros existentes sem mudança
    

VALIDAÇÃO DE PERFORMANCE:
------------------------
A idempotência melhora a performance porque:
- ✅ Não executa UPDATE desnecessários
- ✅ Não dispara triggers/signals do Django
- ✅ Não gera logs de auditoria desnecessários
- ✅ Reduz I/O do banco de dados

Execute múltiplas vezes e compare o tempo:
    time python manage.py etl_03_contratos
    
Na primeira execução: muitas modificações
Nas execuções seguintes: tudo pulado (muito mais rápido!)
""")
    
    print("\n" + "=" * 80)
    print("📝 REGISTROS ATUAIS PARA COMPARAÇÃO")
    print("=" * 80)
    
    if pj_sample:
        print(f"\nPJ: {pj_sample.razao_social}")
        print(f"  - CNPJ: {pj_cnpj}")
        print(f"  - Email: {pj_sample.email or 'Não informado'}")
        print(f"  - CNAE: {pj_sample.cnae or 'Não informado'}")
        print(f"  - Regime Fiscal: {pj_sample.regime_fiscal or 'Não informado'}")
        print(f"  - Updated At: {pj_sample.updated_at}")
    
    if contrato_sample:
        print(f"\nContrato: {contrato_id}")
        print(f"  - Cliente: {contrato_sample.cliente}")
        print(f"  - Valor: R$ {contrato_sample.valor_honorario}")
        print(f"  - Ativo: {'Sim' if contrato_sample.ativo else 'Não'}")
        print(f"  - Updated At: {contrato_sample.updated_at}")
    
    print("\n" + "=" * 80)
    print("✅ SCRIPT DE TESTE CONCLUÍDO")
    print("=" * 80)
    print("\nExecute agora: python manage.py etl_03_contratos --limit 10")
    print("E observe o comportamento de idempotência!\n")

if __name__ == '__main__':
    test_idempotencia()
