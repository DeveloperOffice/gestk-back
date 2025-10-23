from django.core.management.base import BaseCommand
from django.db.models import Sum
from apps.gestao_models.models import FaturamentoEmpresa
from apps.core.models import Contabilidade

class Command(BaseCommand):
    help = 'Gera um relatório de faturamento mensal consolidado por contabilidade e mês.'

    def add_arguments(self, parser):
        parser.add_argument('--ano', type=int, help='Ano para o relatório (opcional)')
        parser.add_argument('--contabilidade-id', type=str, help='UUID da contabilidade (opcional)')

    def handle(self, *args, **options):
        ano = options.get('ano')
        contabilidade_id = options.get('contabilidade_id')
        qs = FaturamentoEmpresa.objects.all()
        if ano:
            qs = qs.filter(ano=ano)
        if contabilidade_id:
            qs = qs.filter(contabilidade_id=contabilidade_id)
        qs = qs.values('ano', 'mes', 'contabilidade__razao_social').annotate(
            total_saidas=Sum('total_saidas'),
            total_servicos=Sum('total_servicos'),
            total_geral=Sum('total_geral')
        ).order_by('ano', 'mes', 'contabilidade__razao_social')
        if not qs:
            self.stdout.write(self.style.WARNING('Nenhum dado encontrado para os filtros informados.'))
            return
        self.stdout.write('ANO | MÊS | CONTABILIDADE | SAÍDAS | SERVIÇOS | TOTAL')
        self.stdout.write('-'*80)
        for row in qs:
            self.stdout.write(f"{row['ano']} | {row['mes']:02d} | {row['contabilidade__razao_social']} | R$ {row['total_saidas']:,.2f} | R$ {row['total_servicos']:,.2f} | R$ {row['total_geral']:,.2f}")
