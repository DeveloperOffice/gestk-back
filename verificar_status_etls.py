import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gestk.settings')
django.setup()

from apps.core.models import Contabilidade, Usuario
from apps.pessoas.models import PessoaJuridica, PessoaFisica, Contrato
from apps.cadastros_gerais.models import CNAE
from apps.contabil.models import PlanoContas, LancamentoContabil, Partida
from apps.fiscal.models import NotaFiscal
from apps.funcionarios.models import Cargo, Departamento, Funcionario, VinculoEmpregaticio

print('\n' + '='*70)
print('          ANÁLISE DE STATUS - ETLs GESTK')
print('='*70 + '\n')

# Contadores
contab = Contabilidade.objects.count()
cnaes = CNAE.objects.count()
contratos = Contrato.objects.count()
pj = PessoaJuridica.objects.count()
pf = PessoaFisica.objects.count()
plano = PlanoContas.objects.count()
lanc = LancamentoContabil.objects.count()
part = Partida.objects.count()
nf = NotaFiscal.objects.count()
cargos = Cargo.objects.count()
dept = Departamento.objects.count()
func = Funcionario.objects.count()
vinc = VinculoEmpregaticio.objects.count()
users = Usuario.objects.count()

print('📊 MÓDULO: BASE E CADASTROS')
status_01 = '✅' if contab > 0 else '❌'
status_02 = '✅' if cnaes > 0 else '❌'
status_03 = '✅' if contratos > 0 else '❌'
print(f'  ETL 01 - Contabilidades:      {contab:>8,} registros  {status_01}')
print(f'  ETL 02 - CNAEs:               {cnaes:>8,} registros  {status_02}')
print(f'  ETL 03 - Contratos:           {contratos:>8,} registros  {status_03}')
print(f'           ├─ Pessoas Jurídicas: {pj:>8,} registros')
print(f'           └─ Pessoas Físicas:   {pf:>8,} registros')

print(f'\n💰 MÓDULO: CONTÁBIL')
status_05 = '✅' if plano > 0 else '❌'
status_06 = '✅' if lanc > 0 else '❌'
print(f'  ETL 05 - Plano de Contas:     {plano:>8,} registros  {status_05}')
print(f'  ETL 06 - Lançamentos:         {lanc:>8,} registros  {status_06}')
print(f'           └─ Partidas:          {part:>8,} registros')

print(f'\n📋 MÓDULO: FISCAL')
status_07 = '✅' if nf > 0 else '❌'
print(f'  ETL 07 - Notas Fiscais:       {nf:>8,} registros  {status_07}')

print(f'\n👥 MÓDULO: RECURSOS HUMANOS')
status_08 = '✅' if cargos > 0 else '⏳'
status_09 = '✅' if dept > 0 else '⏳'
status_11 = '✅' if func > 0 else '⏳'
print(f'  ETL 08 - Cargos:              {cargos:>8,} registros  {status_08}')
print(f'  ETL 09 - Departamentos:       {dept:>8,} registros  {status_09}')
print(f'  ETL 11 - Funcionários:        {func:>8,} registros  {status_11}')
print(f'           └─ Vínculos:          {vinc:>8,} registros')

print(f'\n👤 MÓDULO: ADMINISTRAÇÃO')
status_18 = '✅' if users > 0 else '⏳'
print(f'  ETL 18 - Usuários:            {users:>8,} registros  {status_18}')

print('\n' + '='*70)
print('\n📈 RESUMO:')
etls_completos = sum([
    contab > 0, cnaes > 0, contratos > 0,
    plano > 0, lanc > 0, nf > 0
])
print(f'  ✅ ETLs Base/Contábil/Fiscal: {etls_completos}/6 principais')

if func == 0:
    print(f'  ⏳ ETLs RH: PENDENTES (necessário executar ETL 08-11)')
elif func > 0:
    print(f'  ✅ ETLs RH: EM ANDAMENTO ({func:,} funcionários importados)')

print('\n✨ PRÓXIMOS PASSOS:')
if func == 0:
    print('  1️⃣  Executar ETL 08 (Cargos)')
    print('  2️⃣  Executar ETL 09 (Departamentos)')
    print('  3️⃣  Executar ETL 10 (Centros de Custo)')
    print('  4️⃣  Executar ETL 11 (Funcionários e Vínculos)')
else:
    print('  ✅ ETLs principais já executados!')
    print('  📝 Considerar ETLs complementares: 12-16 (Históricos, Férias, etc)')

print('\n')
