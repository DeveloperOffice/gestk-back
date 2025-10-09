from django.core.management.base import BaseCommand
from django.db import transaction
from apps.core.models import Contabilidade
from apps.cadastros_gerais.models import CNAE
from apps.pessoas.models import Contrato, PessoaJuridica, PessoaFisica
from apps.contabil.models import PlanoContas, LancamentoContabil
from apps.fiscal.models import NotaFiscal, NotaFiscalItem
from apps.funcionarios.models import Funcionario, VinculoEmpregaticio, Rescisao
from apps.administracao.models import ContratoGestk, Usuario, UsuarioContabilidade, UsuarioModulo, LogAcesso, LancamentoUsuario, AuditoriaSistema
from apps.billing.models import Plano, Assinatura, Fatura, Pagamento

class Command(BaseCommand):
    help = 'Limpa todos os dados de teste criados para simular as ETLs'

    def add_arguments(self, parser):
        parser.add_argument(
            '--confirmar',
            action='store_true',
            help='Confirma a exclusão de todos os dados',
        )

    def handle(self, *args, **options):
        if not options['confirmar']:
            self.stdout.write(self.style.WARNING('ATENÇÃO: Este comando irá deletar TODOS os dados do banco!'))
            self.stdout.write('Use --confirmar para executar a limpeza.')
            return

        self.stdout.write(self.style.WARNING('Iniciando limpeza dos dados de teste...'))
        
        with transaction.atomic():
            # Deletar em ordem reversa para respeitar as foreign keys
            self.stdout.write('Deletando Pagamentos...')
            Pagamento.objects.all().delete()
            
            self.stdout.write('Deletando Faturas...')
            Fatura.objects.all().delete()
            
            self.stdout.write('Deletando Assinaturas...')
            Assinatura.objects.all().delete()
            
            self.stdout.write('Deletando Planos...')
            Plano.objects.all().delete()
            
            self.stdout.write('Deletando Auditorias do Sistema...')
            AuditoriaSistema.objects.all().delete()
            
            self.stdout.write('Deletando Lançamentos dos Usuários...')
            LancamentoUsuario.objects.all().delete()
            
            self.stdout.write('Deletando Logs de Acesso...')
            LogAcesso.objects.all().delete()
            
            self.stdout.write('Deletando Módulos dos Usuários...')
            UsuarioModulo.objects.all().delete()
            
            self.stdout.write('Deletando Vínculos Usuário-Contabilidade...')
            UsuarioContabilidade.objects.all().delete()
            
            self.stdout.write('Deletando Usuários...')
            Usuario.objects.all().delete()
            
            self.stdout.write('Deletando Contratos GestK...')
            ContratoGestk.objects.all().delete()
            
            self.stdout.write('Deletando Rescisões...')
            Rescisao.objects.all().delete()
            
            self.stdout.write('Deletando Vínculos Empregatícios...')
            VinculoEmpregaticio.objects.all().delete()
            
            self.stdout.write('Deletando Funcionários...')
            Funcionario.objects.all().delete()
            
            self.stdout.write('Deletando Itens de Nota Fiscal...')
            NotaFiscalItem.objects.all().delete()
            
            self.stdout.write('Deletando Notas Fiscais...')
            NotaFiscal.objects.all().delete()
            
            self.stdout.write('Deletando Lançamentos Contábeis...')
            LancamentoContabil.objects.all().delete()
            
            self.stdout.write('Deletando Plano de Contas...')
            PlanoContas.objects.all().delete()
            
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
