"""
Script para analisar os "erros" do ETL 19 e verificar mapeamento de empresas
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gestk.settings')
django.setup()

from apps.administracao.models_etl19_corrigido import LogAtividade, LogImportacao, LogLancamento
from apps.pessoas.models import PessoaJuridica
from apps.administracao.models import Usuario, UsuarioContabilidade
from django.db.models import Count

print('='*80)
print('ANÁLISE DETALHADA DOS "ERROS" DO ETL 19')
print('='*80)

# Estatísticas gerais
print('\n📊 DADOS NO SISTEMA:')
print(f'  - Usuários cadastrados: {Usuario.objects.count():,}')
print(f'  - Empresas (PessoaJuridica): {PessoaJuridica.objects.count():,}')
print(f'  - Vínculos ativos (UsuarioContabilidade): {UsuarioContabilidade.objects.filter(ativo=True).count():,}')

print('\n📊 LOGS IMPORTADOS:')
total_logs = (
    LogAtividade.objects.count() + 
    LogImportacao.objects.count() + 
    LogLancamento.objects.count()
)
print(f'  - LogAtividade: {LogAtividade.objects.count():,}')
print(f'  - LogImportacao: {LogImportacao.objects.count():,}')
print(f'  - LogLancamento: {LogLancamento.objects.count():,}')
print(f'  - TOTAL: {total_logs:,}')

# Estatísticas do relatório
print('\n📊 ANÁLISE DOS "ERROS" (do relatório):')
processados = 810_626 + 300_306 + 7_538_110  # Total processado
criados = 287_707 + 91_154 + 351_252  # Total criado
nao_criados = processados - criados

print(f'  - Registros processados: {processados:,}')
print(f'  - Registros criados: {criados:,}')
print(f'  - Registros NÃO criados: {nao_criados:,}')
print(f'  - Taxa de sucesso: {(criados/processados)*100:.1f}%')

print('\n🔍 BREAKDOWN DOS REGISTROS NÃO CRIADOS:')
sem_usuario = 14_123
sem_empresa = 99_277
sem_vinculo = 1_319_994
total_validacao = sem_usuario + sem_empresa + sem_vinculo

print(f'  - Sem usuário (nome não encontrado): {sem_usuario:,} ({(sem_usuario/processados)*100:.2f}%)')
print(f'  - Sem empresa (CNPJ não encontrado): {sem_empresa:,} ({(sem_empresa/processados)*100:.2f}%)')
print(f'  - Sem vínculo (usuário+empresa sem UsuarioContabilidade): {sem_vinculo:,} ({(sem_vinculo/processados)*100:.2f}%)')
print(f'  - Total de validações: {total_validacao:,}')

print('\n💡 INTERPRETAÇÃO:')
print('  ⚠️  "Sem vínculo" (1.3M) é o maior problema:')
print('      → Usuário existe no sistema')
print('      → Empresa existe no sistema')  
print('      → MAS não há registro em UsuarioContabilidade vinculando os dois')
print('      → Isso significa que o usuário acessou empresas sem ter vínculo formal')
print('      → Pode ser acesso de suporte, migração, testes, etc.')

print('\n  ⚠️  "Sem empresa" (99K):')
print('      → CNPJ no log não existe na tabela PessoaJuridica')
print('      → Pode ser empresa deletada, CNPJ inválido, ou empresa não migrada')

print('\n  ⚠️  "Sem usuário" (14K):')
print('      → Nome de usuário no log não existe na tabela Usuario')
print('      → Pode ser usuário deletado ou não migrado')

# Verificar amostra de empresas com mais logs
print('\n📈 TOP 10 EMPRESAS COM MAIS LOGS IMPORTADOS:')
empresas_com_logs = (
    LogAtividade.objects
    .values('empresa__cnpj', 'empresa__razao_social')
    .annotate(total=Count('id'))
    .order_by('-total')[:10]
)

for i, e in enumerate(empresas_com_logs, 1):
    cnpj = e['empresa__cnpj'] or 'N/A'
    razao = e['empresa__razao_social'] or 'Sem razão social'
    total = e['total']
    print(f'  {i:2d}. {cnpj}: {razao[:50]} ({total:,} logs)')

# Verificar se historical_map está sendo usado
print('\n🔍 VERIFICANDO PROBLEMA DE MAPEAMENTO:')
print('  O código DECLARA historical_map mas NÃO o USA na função buscar_objetos_relacionados()')
print('  Linha 490: def buscar_objetos_relacionados(..., historical_map)')
print('  Problema: o parâmetro historical_map é recebido mas NUNCA utilizado!')
print('  ')
print('  ❌ O código usa apenas os caches (usuario, empresa, vinculo)')
print('  ❌ Não usa a REGRA DE OURO (historical_map) para mapear CNPJ → Contabilidade')
print('  ')
print('  ✅ SOLUÇÃO: Integrar historical_map na busca de contabilidade')

print('\n'+'='*80)
print('CONCLUSÃO: Os "erros" são na verdade registros ESPERADOS que não têm vínculos')
print('MAS há um BUG: historical_map não está sendo usado para encontrar contabilidade!')
print('='*80)
