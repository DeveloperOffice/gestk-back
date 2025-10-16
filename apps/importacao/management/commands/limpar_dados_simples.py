from django.core.management.base import BaseCommand
from django.db import transaction
from apps.core.models import Contabilidade
from apps.cadastros_gerais.models import CNAE
from apps.pessoas.models import Contrato, PessoaJuridica, PessoaFisica

class Command(BaseCommand):
    help = 'Limpa apenas os dados principais criados para simular as ETLs'

    def add_arguments(self, parser):
        parser.add_argument(
            '--confirmar',
            action='store_true',
            help='Confirma a exclusão dos dados',
        )

    def handle(self, *args, **options):
        if not options['confirmar']:
            self.stdout.write(self.style.WARNING('ATENÇÃO: Este comando irá deletar os dados principais!'))
            self.stdout.write('Use --confirmar para executar a limpeza.')
            return

        self.stdout.write(self.style.WARNING('Iniciando limpeza dos dados principais...'))
        
        with transaction.atomic():
            # Deletar apenas os dados principais
            self.stdout.write('Deletando Contratos...')
            Contrato.objects.all().delete()
            
            self.stdout.write('Deletando Pessoas Físicas...')
            PessoaFisica.objects.all().delete()
            
            self.stdout.write('Deletando Pessoas Jurídicas...')
            PessoaJuridica.objects.all().delete()
            
            self.stdout.write('Deletando CNAEs...')
            CNAE.objects.all().delete()
            
            self.stdout.write('Deletando Contabilidades...')
            Contabilidade.objects.all().delete()

        self.stdout.write(self.style.SUCCESS('Limpeza concluída com sucesso!'))
        self.stdout.write('Agora você pode executar as ETLs reais com o banco Sybase disponível.')

