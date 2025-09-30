from django.core.management.base import BaseCommand
from apps.core.models import Contabilidade
from apps.pessoas.models import Contrato, PessoaJuridica, PessoaFisica

class Command(BaseCommand):
    help = 'Verifica o mapeamento entre Contabilidades e Clientes através dos Contratos.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('--- Iniciando verificação de mapeamento Contabilidade -> Cliente ---'))

        contabilidades = Contabilidade.objects.all()
        if not contabilidades.exists():
            self.stdout.write(self.style.WARNING('Nenhuma contabilidade encontrada no banco de dados.'))
            return

        total_contratos_verificados = 0
        contabilidades_com_contratos = 0

        for contabilidade in contabilidades:
            contratos = Contrato.objects.filter(contabilidade=contabilidade, ativo=True)
            
            if contratos.exists():
                contabilidades_com_contratos += 1
                self.stdout.write('\n' + '-'*80)
                self.stdout.write(self.style.SUCCESS(
                    f'Contabilidade: {contabilidade.razao_social} (CNPJ: {contabilidade.cnpj})'
                ))
                self.stdout.write('-'*80)
                
                for contrato in contratos:
                    total_contratos_verificados += 1
                    cliente = contrato.cliente
                    
                    if cliente:
                        if isinstance(cliente, PessoaJuridica):
                            tipo_cliente = 'PJ'
                            documento_cliente = cliente.cnpj
                            nome_cliente = cliente.razao_social
                        elif isinstance(cliente, PessoaFisica):
                            tipo_cliente = 'PF'
                            documento_cliente = cliente.cpf
                            nome_cliente = cliente.nome_completo
                        else:
                            tipo_cliente = 'Desconhecido'
                            documento_cliente = 'N/A'
                            nome_cliente = 'N/A'

                        self.stdout.write(
                            f'  -> Cliente [{tipo_cliente}]: {nome_cliente} (Doc: {documento_cliente})'
                        )
                    else:
                        self.stdout.write(self.style.WARNING(
                            f'  -> Contrato ID {contrato.id_legado} não possui cliente associado.'
                        ))
            
        self.stdout.write('\n' + '='*80)
        self.stdout.write(self.style.SUCCESS('--- Resumo da Verificação ---'))
        self.stdout.write(f'Total de Contabilidades verificadas: {contabilidades.count()}')
        self.stdout.write(f'Contabilidades com contratos ativos: {contabilidades_com_contratos}')
        self.stdout.write(f'Total de Contratos verificados: {total_contratos_verificados}')
        self.stdout.write('='*80)
