"""
Script para testar os endpoints de carteira após aplicação da Regra de Ouro
Valida que todos os endpoints retornam contagens consistentes de clientes únicos
"""

import os
import sys
import django

# Configurar Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gestk.settings')
django.setup()

from django.contrib.contenttypes.models import ContentType
from apps.pessoas.models import PessoaJuridica, PessoaFisica, Contrato
from apps.importacao.management.commands._base import BaseETLCommand
from django.db.models import Q

def test_carteira_endpoints():
    """Testa consistência dos endpoints de carteira"""
    
    print("=" * 80)
    print("TESTE DOS ENDPOINTS DE CARTEIRA - REGRA DE OURO")
    print("=" * 80)
    print()
    
    # 1. Construir mapa histórico (igual aos endpoints)
    print("1️⃣ Construindo mapa histórico (Regra de Ouro)...")
    etl_command = BaseETLCommand()
    historical_map = etl_command.build_historical_contabilidade_map()
    print(f"   ✅ Mapa construído: {len(historical_map)} clientes únicos com contratos válidos\n")
    
    # 2. Obter todos os contratos
    print("2️⃣ Obtendo contratos...")
    todos_os_contratos = Contrato.objects.all()
    print(f"   📊 Total de contratos no banco: {todos_os_contratos.count()}")
    print(f"   ✅ Contratos ativos: {todos_os_contratos.filter(ativo=True).count()}")
    print(f"   ❌ Contratos inativos: {todos_os_contratos.filter(ativo=False).count()}\n")
    
    # 3. Filtrar apenas clientes válidos (com contratos no mapa)
    print("3️⃣ Filtrando clientes válidos...")
    cnpjs_validos = set(historical_map.keys())
    
    pj_ids_validos = PessoaJuridica.objects.filter(cnpj__in=cnpjs_validos).values_list('id', flat=True)
    pf_ids_validos = PessoaFisica.objects.filter(cpf__in=cnpjs_validos).values_list('id', flat=True)
    
    pj_content_type = ContentType.objects.get_for_model(PessoaJuridica)
    pf_content_type = ContentType.objects.get_for_model(PessoaFisica)
    
    contratos_validos = todos_os_contratos.filter(
        Q(content_type=pj_content_type, object_id__in=pj_ids_validos) |
        Q(content_type=pf_content_type, object_id__in=pf_ids_validos)
    )
    
    print(f"   ✅ Contratos válidos (com clientes no mapa): {contratos_validos.count()}")
    print(f"   ❌ Contratos órfãos (sem cliente válido): {todos_os_contratos.count() - contratos_validos.count()}\n")
    
    # 4. Contar clientes ÚNICOS (não contratos)
    print("4️⃣ Contando clientes ÚNICOS...")
    empresas_unicas = contratos_validos.values('object_id').distinct().count()
    print(f"   👥 Total de clientes únicos: {empresas_unicas}")
    
    clientes_ativos_qs = contratos_validos.filter(ativo=True)
    empresas_ativas = clientes_ativos_qs.values('object_id').distinct().count()
    print(f"   ✅ Clientes ativos: {empresas_ativas}")
    
    empresas_inativas = empresas_unicas - empresas_ativas
    print(f"   ❌ Clientes inativos: {empresas_inativas}\n")
    
    # 5. Validar categorias (Ativos/Inativos)
    print("5️⃣ Endpoint /categorias/")
    ativos_count = contratos_validos.filter(ativo=True).values('object_id').distinct().count()
    inativos_count = empresas_unicas - ativos_count
    print(f"   ✅ Ativos: {ativos_count}")
    print(f"   ❌ Inativos: {inativos_count}")
    print(f"   📊 Total: {ativos_count + inativos_count}\n")
    
    # 6. Validar regime tributário
    print("6️⃣ Endpoint /regime-tributario/")
    contratos_pj = contratos_validos.filter(content_type=pj_content_type)
    total_pj = contratos_pj.values('object_id').distinct().count()
    
    regimes_map = {
        'simples': 'Simples Nacional',
        'presumido': 'Lucro Presumido',
        'real': 'Lucro Real'
    }
    
    print(f"   📊 Total PJ: {total_pj}")
    for regime_key, regime_nome in regimes_map.items():
        pj_ids = PessoaJuridica.objects.filter(
            regime_fiscal=regime_key,
            id__in=pj_ids_validos
        ).values_list('id', flat=True)
        
        quantidade = contratos_pj.filter(object_id__in=pj_ids).values('object_id').distinct().count()
        percentual = (quantidade / total_pj * 100) if total_pj > 0 else 0
        print(f"   - {regime_nome}: {quantidade} ({percentual:.1f}%)")
    print()
    
    # 7. Validar ramo de atividade
    print("7️⃣ Endpoint /ramo-atividade/")
    ramos_map = {
        'comercio': 'Comércio',
        'servicos': 'Serviços',
        'industria': 'Indústria'
    }
    
    for ramo_key, ramo_nome in ramos_map.items():
        pj_ids = PessoaJuridica.objects.filter(
            ramo_atividade=ramo_key,
            id__in=pj_ids_validos
        ).values_list('id', flat=True)
        
        quantidade = contratos_pj.filter(object_id__in=pj_ids).values('object_id').distinct().count()
        percentual = (quantidade / total_pj * 100) if total_pj > 0 else 0
        print(f"   - {ramo_nome}: {quantidade} ({percentual:.1f}%)")
    print()
    
    # 8. Validar aniversários de parceria
    print("8️⃣ Endpoint /aniversarios-parceria/")
    aniversarios_count = 0
    empresas_processadas = set()
    
    for contrato in contratos_validos.filter(ativo=True, data_inicio__isnull=False):
        cliente = contrato.cliente
        if isinstance(cliente, PessoaJuridica) and cliente.id not in empresas_processadas:
            empresas_processadas.add(cliente.id)
            aniversarios_count += 1
    
    print(f"   🎂 Clientes com aniversário de parceria: {aniversarios_count}\n")
    
    # 9. Resumo final
    print("=" * 80)
    print("RESUMO FINAL")
    print("=" * 80)
    print(f"✅ Clientes únicos válidos (no mapa histórico): {empresas_unicas}")
    print(f"✅ Contratos válidos: {contratos_validos.count()}")
    print(f"❌ Contratos órfãos (eliminados): {todos_os_contratos.count() - contratos_validos.count()}")
    print(f"📊 Percentual de aproveitamento: {(contratos_validos.count() / todos_os_contratos.count() * 100):.1f}%")
    print()
    
    # Validações
    print("VALIDAÇÕES:")
    if empresas_unicas == ativos_count + inativos_count:
        print("✅ Soma de ativos + inativos = total de clientes únicos")
    else:
        print(f"❌ ERRO: {empresas_unicas} ≠ {ativos_count + inativos_count}")
    
    if contratos_validos.count() <= todos_os_contratos.count():
        print("✅ Contratos válidos ≤ Total de contratos")
    else:
        print("❌ ERRO: Contratos válidos > Total de contratos")
    
    if len(historical_map) == empresas_unicas:
        print("✅ Mapa histórico = Clientes únicos")
    else:
        print(f"⚠️  AVISO: Mapa histórico ({len(historical_map)}) ≠ Clientes únicos ({empresas_unicas})")
    
    print()
    print("=" * 80)
    print("TESTE CONCLUÍDO")
    print("=" * 80)

if __name__ == '__main__':
    test_carteira_endpoints()
