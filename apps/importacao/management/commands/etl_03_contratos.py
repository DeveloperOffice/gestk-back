from django.db import transaction
from ._base import BaseETLCommand
from apps.core.models import Contabilidade
from apps.pessoas.models import PessoaJuridica, PessoaFisica, Contrato
from django.contrib.contenttypes.models import ContentType
import re
from datetime import date

class Command(BaseETLCommand):
    help = 'ETL 03 - Importação de Contratos e Pessoas (Físicas/Jurídicas) com dados específicos'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Executar em modo de teste (não salva no banco)',
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=None,
            help='Limitar número de contratos para processar (para testes)',
        )
        parser.add_argument(
            '--update-only',
            action='store_true',
            help='Apenas atualizar contratos existentes (não criar novos)',
        )

    def handle(self, *args, **options):
        self.dry_run = options['dry_run']
        self.limit = options['limit']
        self.update_only = options['update_only']
        
        if self.dry_run:
            self.stdout.write(self.style.WARNING('MODO DRY-RUN: Nenhum dado será salvo no banco'))
        
        self.stdout.write(self.style.SUCCESS('=== ETL 04 - CONTRATOS E PESSOAS ==='))
        self.stdout.write('NOTA: Execute ETL 00 primeiro para garantir cobertura completa!')
        
        # Construir mapa histórico para validação
        self.stdout.write('\n[1] Construindo mapa histórico de contabilidades...')
        historical_map = self.build_historical_contabilidade_map_cached()

        connection = self.get_sybase_connection()
        if not connection:
            return

        # Query para buscar todos os contratos com dados dos clientes e CNPJ da contabilidade
        query = """
        SELECT
            hc.codi_emp as id_legado_contabilidade,
            cont_ge.cgce_emp as cnpj_contabilidade,
            hc.i_contrato as id_legado_contrato,
            hc.data_inicio_faturamento,
            hc.data_termino,
            hc.dia_vencimento,
            hc.valor_contrato,
            ge.codi_emp as id_legado_cliente,
            ge.cgce_emp as documento,
            ge.nome_emp as nome_razao_social,
            ge.fantasia_emp,
            ge.simples_emp,
            ge.cnae_emp,
            ge.ramo_emp,
            ge.rleg_emp,
            ge.cpf_leg_emp as cpf_responsavel,
            ge.ende_emp as logradouro,
            ge.nume_emp as numero,
            ge.comp_emp as complemento,
            ge.bair_emp as bairro,
            ge.cida_emp as cidade,
            ge.esta_emp as uf,
            ge.cepe_emp as cep,
            ge.email_emp as email,
            ge.fone_emp as telefone
        FROM 
            BETHADBA.HRCONTRATO AS hc
        INNER JOIN
            BETHADBA.HRVCLIENTE AS hvc ON hc.i_cliente = hvc.i_cliente AND hc.codi_emp = hvc.codigo_escritorio
        INNER JOIN
            BETHADBA.GEEMPRE AS ge ON hvc.i_cliente_fixo = ge.codi_emp
        INNER JOIN
            BETHADBA.GEEMPRE AS cont_ge ON hc.codi_emp = cont_ge.codi_emp
        WHERE hc.data_inicio_faturamento >= '2019-01-01'
        AND ge.codi_emp NOT IN (9997, 9998, 9999, 10000, 10001)  -- Excluir empresas modelo
        ORDER BY hc.codi_emp, hc.i_contrato
        """
        
        if self.limit:
            query = f"SELECT TOP {self.limit} * FROM ({query}) AS contratos"

        self.stdout.write("\n[2] Extraindo dados de Contratos do Sybase...")
        data = self.execute_query(connection, query)
        connection.close()

        if not data:
            self.stdout.write(self.style.WARNING('Nenhum contrato encontrado.'))
            return

        self.stdout.write(f"{len(data)} contratos extraídos. Iniciando o carregamento...")
        
        total_contratos_criados = 0
        total_contratos_atualizados = 0
        total_pj_criadas = 0
        total_pf_criadas = 0
        total_erros = 0

        try:
            if not self.dry_run:
                with transaction.atomic():
                    self.processar_contratos(data, historical_map, total_contratos_criados, total_contratos_atualizados, total_pj_criadas, total_pf_criadas, total_erros)
            else:
                self.processar_contratos(data, historical_map, total_contratos_criados, total_contratos_atualizados, total_pj_criadas, total_pf_criadas, total_erros)
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Ocorreu um erro durante o carregamento: {e}'))
            raise
        finally:
            if hasattr(self, '_sybase_connection') and self._sybase_connection:
                try:
                    self.close_sybase_connection()
                except:
                    pass  # Ignorar erro se conexão já estiver fechada

    def processar_contratos(self, data, historical_map, total_contratos_criados, total_contratos_atualizados, total_pj_criadas, total_pf_criadas, total_erros):
        """Processa os contratos extraídos"""
        for i, item in enumerate(data, 1):
            if i % 100 == 0:
                self.stdout.write(f"Processando contrato {i}/{len(data)}...")
            
            try:
                documento_bruto = str(item.get('documento') or '').strip()
                documento_limpo = re.sub(r'\D', '', documento_bruto)
                
                # Buscar contabilidade pelo CNPJ
                cnpj_contabilidade = str(item.get('cnpj_contabilidade') or '').strip()
                cnpj_contabilidade_limpo = re.sub(r'\D', '', cnpj_contabilidade)
                
                contabilidade = Contabilidade.objects.filter(cnpj=cnpj_contabilidade_limpo).first()
                if not contabilidade:
                    self.stdout.write(self.style.WARNING(f"Contabilidade com CNPJ {cnpj_contabilidade_limpo} não encontrada. Pulando contrato."))
                    total_erros += 1
                    continue
                
                # Buscar ou criar pessoa
                cliente_obj = self.buscar_ou_criar_pessoa(item, documento_limpo)
                if not cliente_obj:
                    total_erros += 1
                    continue
                
                # Verificar se pessoa foi criada
                if hasattr(cliente_obj, 'cnpj'):
                    if not PessoaJuridica.objects.filter(cnpj=documento_limpo).exists():
                        total_pj_criadas += 1
                    else:
                        # Atualizar campos da PJ existente
                        pj_existente = PessoaJuridica.objects.get(cnpj=documento_limpo)
                        simples_emp = item.get('simples_emp')
                        regime_tributario = None
                        if simples_emp == 1:
                            regime_tributario = '1'  # Simples Nacional
                        elif simples_emp == 0:
                            regime_tributario = '2'  # Lucro Presumido
                        
                        pj_existente.regime_tributario = regime_tributario
                        pj_existente.simples_nacional = bool(simples_emp == 1)
                        if item.get('rleg_emp'):
                            pj_existente.responsavel_legal = str(item.get('rleg_emp')).strip()
                        if item.get('cpf_responsavel'):
                            pj_existente.cpf_responsavel = str(item.get('cpf_responsavel')).strip()
                        pj_existente.save()
                elif hasattr(cliente_obj, 'cpf'):
                    if not PessoaFisica.objects.filter(cpf=documento_limpo).exists():
                        total_pf_criadas += 1
                
                # Criar ou atualizar contrato
                contrato_id_legado = f"{item.get('id_legado_contabilidade')}-{item.get('id_legado_contrato')}"
                content_type = ContentType.objects.get_for_model(cliente_obj)

                if not self.dry_run:
                    data_termino = item.get('data_termino')
                    
                    # Lógica para determinar se o contrato está ativo
                    # Um contrato é ativo se a data de término for nula (indeterminado)
                    # ou se a data de término for no futuro.
                    ativo = False
                    if data_termino is None:
                        ativo = True
                    else:
                        # Converte para objeto date se não for
                        if isinstance(data_termino, str):
                            try:
                                data_termino = date.fromisoformat(data_termino.split(' ')[0])
                            except (ValueError, TypeError):
                                data_termino = None # Tratar datas inválidas
                        
                        if data_termino and data_termino > date.today():
                            ativo = True

                    contrato, created = Contrato.objects.update_or_create(
                        id_legado=contrato_id_legado,
                        defaults={
                            'contabilidade': contabilidade,
                            'content_type': content_type,
                            'object_id': cliente_obj.id,
                            'data_inicio': item.get('data_inicio_faturamento'),
                            'data_termino': data_termino,
                            'dia_vencimento': item.get('dia_vencimento'),
                            'valor_honorario': item.get('valor_contrato') or 0,
                            'ativo': ativo,
                        }
                    )
                    
                    if created:
                        total_contratos_criados += 1
                    else:
                        total_contratos_atualizados += 1
                else:
                    # Modo dry-run
                    if Contrato.objects.filter(id_legado=contrato_id_legado).exists():
                        total_contratos_atualizados += 1
                    else:
                        total_contratos_criados += 1
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Erro ao processar contrato {i}: {e}'))
                total_erros += 1
                continue

        # Relatório final
        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.SUCCESS('RELATÓRIO FINAL - ETL 04'))
        self.stdout.write('='*60)
        self.stdout.write(f'Pessoas Jurídicas criadas: {total_pj_criadas}')
        self.stdout.write(f'Pessoas Físicas criadas: {total_pf_criadas}')
        self.stdout.write(f'Contratos criados: {total_contratos_criados}')
        self.stdout.write(f'Contratos atualizados: {total_contratos_atualizados}')
        self.stdout.write(f'Erros: {total_erros}')
        
        # Estatísticas de performance
        self.print_stats()
        
        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.SUCCESS('ETL 04 CONCLUÍDO COM SUCESSO!'))
        self.stdout.write('='*60)

    def buscar_ou_criar_pessoa(self, item, documento_limpo):
        """Busca ou cria pessoa baseada no documento"""
        if len(documento_limpo) == 14:
            # Pessoa Jurídica
            # Determinar regime tributário baseado no simples_emp
            simples_emp = item.get('simples_emp')
            regime_tributario = None
            if simples_emp == 1:
                regime_tributario = '1'  # Simples Nacional
            elif simples_emp == 0:
                regime_tributario = '2'  # Lucro Presumido (assumindo)
            
            pj, created = PessoaJuridica.objects.get_or_create(
                cnpj=documento_limpo,
                defaults={
                    'id_legado': item.get('id_legado_cliente'),
                    'razao_social': str(item.get('nome_razao_social') or '').strip(),
                    'nome_fantasia': str(item.get('fantasia_emp') or '').strip(),
                    'logradouro': str(item.get('logradouro') or '').strip(),
                    'numero': str(item.get('numero') or '').strip(),
                    'complemento': str(item.get('complemento') or '').strip(),
                    'bairro': str(item.get('bairro') or '').strip(),
                    'cidade': str(item.get('cidade') or '').strip(),
                    'uf': str(item.get('uf') or '').strip(),
                    'cep': str(item.get('cep') or '').strip(),
                    'email': str(item.get('email') or '').strip(),
                    'telefone': str(item.get('telefone') or '').strip(),
                }
            )
            
            # Sempre atualizar os campos
            pj.regime_tributario = regime_tributario
            pj.simples_nacional = bool(simples_emp == 1)
            if item.get('rleg_emp'):
                pj.responsavel_legal = str(item.get('rleg_emp')).strip()
            
            # Atualizar campos de endereço e contato
            pj.logradouro = str(item.get('logradouro') or '').strip() or pj.logradouro
            pj.numero = str(item.get('numero') or '').strip() or pj.numero
            pj.complemento = str(item.get('complemento') or '').strip() or pj.complemento
            pj.bairro = str(item.get('bairro') or '').strip() or pj.bairro
            pj.cidade = str(item.get('cidade') or '').strip() or pj.cidade
            pj.uf = str(item.get('uf') or '').strip() or pj.uf
            pj.cep = str(item.get('cep') or '').strip() or pj.cep
            pj.email = str(item.get('email') or '').strip() or pj.email
            pj.telefone = str(item.get('telefone') or '').strip() or pj.telefone
            pj.save()
            
            return pj
        
        elif len(documento_limpo) == 11:
            # Pessoa Física
            pf, created = PessoaFisica.objects.get_or_create(
                cpf=documento_limpo,
                defaults={
                    'id_legado': item.get('id_legado_cliente'),
                    'nome_completo': str(item.get('nome_razao_social') or '').strip(),
                    'logradouro': str(item.get('logradouro') or '').strip(),
                    'numero': str(item.get('numero') or '').strip(),
                    'complemento': str(item.get('complemento') or '').strip(),
                    'bairro': str(item.get('bairro') or '').strip(),
                    'cidade': str(item.get('cidade') or '').strip(),
                    'uf': str(item.get('uf') or '').strip(),
                    'cep': str(item.get('cep') or '').strip(),
                    'email': str(item.get('email') or '').strip(),
                    'telefone': str(item.get('telefone') or '').strip(),
                }
            )
            
            # Atualizar campos de endereço e contato
            pf.logradouro = str(item.get('logradouro') or '').strip() or pf.logradouro
            pf.numero = str(item.get('numero') or '').strip() or pf.numero
            pf.complemento = str(item.get('complemento') or '').strip() or pf.complemento
            pf.bairro = str(item.get('bairro') or '').strip() or pf.bairro
            pf.cidade = str(item.get('cidade') or '').strip() or pf.cidade
            pf.uf = str(item.get('uf') or '').strip() or pf.uf
            pf.cep = str(item.get('cep') or '').strip() or pf.cep
            pf.email = str(item.get('email') or '').strip() or pf.email
            pf.telefone = str(item.get('telefone') or '').strip() or pf.telefone
            pf.save()
            
            return pf
        
        else:
            self.stdout.write(self.style.WARNING(f"Documento inválido '{documento_limpo}' para o cliente {item.get('id_legado_cliente')}. Pulando contrato."))
            return None

