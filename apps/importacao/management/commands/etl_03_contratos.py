from django.db import transaction
from ._base import BaseETLCommand
from apps.core.models import Contabilidade
from apps.pessoas.models import PessoaJuridica, PessoaFisica, Contrato
from django.contrib.contenttypes.models import ContentType
import re
from datetime import date, datetime

class Command(BaseETLCommand):
    help = 'ETL 03 - Importação de Contratos e Pessoas (Físicas/Jurídicas) - Multi-Tenant com CNPJ/CPF como chave'

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

        self.stdout.write(self.style.SUCCESS('=== ETL 03 - CONTRATOS E PESSOAS (Multi-Tenant) ==='))
        self.stdout.write('NOTA: Usa CNPJ/CPF como chave de identificação!')

        # Construir mapa histórico para validação
        self.stdout.write('\n[1] Construindo mapa histórico de contabilidades...')
        historical_map = self.build_historical_contabilidade_map_cached()

        connection = self.get_sybase_connection()
        if not connection:
            return

        # Buscar regimes tributários de todas as empresas
        self.stdout.write("\n[1.1] Buscando regimes tributários do Sybase...")
        regime_query = """
            SELECT cgce_emp, MAX(vigencia_par) as vigencia_max, MAX(rfed_par) as rfed_par
            FROM bethadba.EFPARAMETRO_VIGENCIA
            WHERE cgce_emp IS NOT NULL
            GROUP BY cgce_emp
        """
        regime_data = self.execute_query(connection, regime_query)
        # Montar dict {cnpj: regime}
        regime_map = {}
        for row in regime_data:
            cnpj = re.sub(r'\D', '', str(row.get('cgce_emp') or ''))
            if cnpj:
                regime_map[cnpj] = row.get('rfed_par')

        # Primeiro, carregar dados das empresas (geempre)
        self.stdout.write("\n[2] Extraindo dados de Empresas do Sybase...")
        empresas_query = """
            SELECT 
                nome_emp, cepe_emp, cgce_emp, ramo_emp, codi_emp, rleg_emp, stat_emp, 
                dina_emp, dcad_emp, ccae_emp, cpf_leg_emp, cnae_emp, codi_con, email_emp, 
                dtinicio_emp, duracao_emp, dttermino_emp, razao_emp, tipoi_emp, i_cnae20, 
                usa_cnae20, email_leg_emp, CERTIFICADO_DIGITAL, fantasia_emp, ende_emp,
                nume_emp, comp_emp, bair_emp, cida_emp, esta_emp, fone_emp, imun_emp,
                simples_emp
            FROM bethadba.geempre
            WHERE cgce_emp IS NOT NULL
            AND codi_emp NOT IN (9997, 9998, 9999, 10000, 10001)
        """
        empresas_data = self.execute_query(connection, empresas_query)
        self.stdout.write(f"   ✅ {len(empresas_data)} empresas extraídas")

        # Depois, carregar contratos
        self.stdout.write("\n[3] Extraindo dados de Contratos do Sybase...")
        data_corte = '2019-01-01'  # Buscar contratos a partir de 01/01/2019
        contratos_query = f"""
            SELECT 
                hc.codi_emp,
                hc.i_cliente,
                hc.data_inicio_faturamento as DATA_INICIO,
                hc.data_termino as DATA_TERMINO,
                hc.valor_contrato as VALOR_CONTRATO,
                hc.dia_vencimento,
                hc.i_contrato,
                ge.cgce_emp as documento_cliente,
                cont_ge.cgce_emp as cnpj_contabilidade
            FROM bethadba.HRCONTRATO AS hc
            INNER JOIN bethadba.HRVCLIENTE AS hvc 
                ON hc.i_cliente = hvc.i_cliente AND hc.codi_emp = hvc.codigo_escritorio
            INNER JOIN bethadba.GEEMPRE AS ge 
                ON hvc.i_cliente_fixo = ge.codi_emp
            INNER JOIN bethadba.GEEMPRE AS cont_ge 
                ON hc.codi_emp = cont_ge.codi_emp
            WHERE (hc.data_inicio_faturamento >= '{data_corte}' 
                   OR hc.data_termino >= '{data_corte}' 
                   OR hc.data_termino IS NULL)
            AND ge.codi_emp NOT IN (9997, 9998, 9999, 10000, 10001)
            ORDER BY hc.codi_emp, hc.i_contrato
        """

        if self.limit:
            contratos_query = f"SELECT TOP {self.limit} * FROM ({contratos_query}) AS contratos"

        data = self.execute_query(connection, contratos_query)
        connection.close()

        if not empresas_data:
            self.stdout.write(self.style.WARNING('Nenhuma empresa encontrada.'))
            return

        if not data:
            self.stdout.write(self.style.WARNING('Nenhum contrato encontrado.'))
            return

        self.stdout.write(f"\n[4] Processando {len(empresas_data)} empresas e {len(data)} contratos...")

        # Passar regime_map para processar_empresas
        stats = {
            'pj_criadas': 0,
            'pj_atualizadas': 0,
            'pj_puladas': 0,
            'pf_criadas': 0,
            'pf_atualizadas': 0,
            'pf_puladas': 0,
            'contratos_criados': 0,
            'contratos_atualizados': 0,
            'contratos_pulados': 0,
            'contabilidades_criadas': 0,
            'erros': 0,
            'erros_contabilidade_nao_encontrada': 0,
            'erros_cliente_nao_encontrado': 0,
            'erros_documento_invalido': 0,
            'erros_outros': 0
        }

        try:
            self.processar_empresas(empresas_data, stats, regime_map)
            self.processar_contratos(data, historical_map, stats)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Ocorreu um erro durante o carregamento: {e}'))
            import traceback
            traceback.print_exc()
        finally:
            if hasattr(self, '_sybase_connection') and self._sybase_connection:
                try:
                    self.close_sybase_connection()
                except:
                    pass  # Ignorar erro se conexão já estiver fechada

    def processar_empresas(self, data, stats, regime_map=None):
        """Processa as empresas extraídas do Sybase (geempre)"""
        self.stdout.write("\n   Processando empresas...")

        for i, item in enumerate(data, 1):
            if i % 100 == 0:
                self.stdout.write(f"   Empresa {i}/{len(data)}...")

            try:
                # Limpar documento (CNPJ ou CPF)
                documento_bruto = str(item.get('cgce_emp') or '').strip()
                documento_limpo = re.sub(r'\D', '', documento_bruto)

                if not documento_limpo or len(documento_limpo) not in [11, 14]:
                    stats['erros'] += 1
                    stats['erros_documento_invalido'] += 1
                    continue

                # Processar por tipo de documento
                if len(documento_limpo) == 14:
                    # Pessoa Jurídica
                    regime_sybase = None
                    if regime_map:
                        regime_sybase = regime_map.get(documento_limpo)
                    self._processar_pessoa_juridica(item, documento_limpo, stats, regime_sybase)
                elif len(documento_limpo) == 11:
                    # Pessoa Física
                    self._processar_pessoa_fisica(item, documento_limpo, stats)

            except Exception as e:
                self.stdout.write(self.style.ERROR(f'   Erro ao processar empresa {i}: {e}'))
                stats['erros'] += 1
                continue

        pj_puladas = stats.get('pj_puladas', 0)
        pf_puladas = stats.get('pf_puladas', 0)
        self.stdout.write(f"   ✅ Empresas processadas:")
        self.stdout.write(f"      - PJ: {stats['pj_criadas']} criadas, {stats['pj_atualizadas']} atualizadas, {pj_puladas} sem mudança")
        self.stdout.write(f"      - PF: {stats['pf_criadas']} criadas, {stats['pf_atualizadas']} atualizadas, {pf_puladas} sem mudança")

    def _processar_pessoa_juridica(self, item, cnpj, stats, regime_sybase=None):
        """Processa uma Pessoa Jurídica com idempotência"""
        # Mapeamento dos campos
        simples_emp = item.get('simples_emp')
        # Priorizar regime_tributario_sybase se disponível
        if regime_sybase is not None:
            regime_tributario = regime_sybase
        else:
            regime_tributario = None
            if simples_emp == 1:
                regime_tributario = '1'  # Simples Nacional
            elif simples_emp == 0:
                regime_tributario = '2'  # Lucro Presumido

        # Mapear regime_fiscal conforme regime_tributario Sybase
        regime_fiscal = None
        if regime_tributario == '1':
            regime_fiscal = 'simples'
        elif regime_tributario == '2':
            regime_fiscal = 'presumido'
        elif regime_tributario == '3':
            regime_fiscal = 'real'
        
        # Preparar CEP
        cep = str(item.get('cepe_emp') or '').strip()
        cep_formatado = re.sub(r'\D', '', cep)
        if len(cep_formatado) == 8:
            cep_formatado = f"{cep_formatado[:5]}-{cep_formatado[5:]}"
        else:
            cep_formatado = cep_formatado or ''

        # Preparar dados completos - TODOS os campos do Sybase
        dados = {
            'razao_social': str(item.get('razao_emp') or item.get('nome_emp') or '').strip() or 'RAZÃO SOCIAL NÃO INFORMADA',
            'nome_fantasia': str(item.get('fantasia_emp') or '').strip() or '',
            'logradouro': str(item.get('ende_emp') or '').strip() or '',
            'numero': str(item.get('nume_emp') or '').strip() or '',
            'complemento': str(item.get('comp_emp') or '').strip() or '',
            'bairro': str(item.get('bair_emp') or '').strip() or '',
            'cidade': str(item.get('cida_emp') or '').strip() or '',
            'uf': str(item.get('esta_emp') or '').strip() or '',
            'cep': cep_formatado,
            'pais': 'Brasil',
            'telefone': str(item.get('fone_emp') or '').strip() or '',
            'email': str(item.get('email_emp') or '').strip() or '',
            'inscricao_municipal': str(item.get('imun_emp') or '').strip() or '',
            'regime_tributario': regime_tributario,
            'simples_nacional': bool(simples_emp == 1),
            'responsavel_legal': str(item.get('rleg_emp') or '').strip() or '',
            'cpf_responsavel': str(item.get('cpf_leg_emp') or '').strip() or '',
            'email_resp_legal': str(item.get('email_leg_emp') or '').strip() or '',
            'cnae': str(item.get('cnae_emp') or '').strip() or '',
            'cnae_20': str(item.get('i_cnae20') or '').strip() or '',
            'usa_cnae_20': bool(item.get('usa_cnae20')),
            'situacao': str(item.get('stat_emp') or '').strip() or '',
            'data_cadastro': item.get('dcad_emp'),
            'data_inicio_atividades': item.get('dtinicio_emp'),
            'data_inatividade': item.get('dina_emp'),
            'motivo_inatividade': str(item.get('tipoi_emp') or '').strip() or '',
            'cae': str(item.get('ccae_emp') or '').strip() or '',
            'contador': str(item.get('codi_con') or '').strip() or '',
            'duracao_contrato': self._converter_duracao_contrato(item.get('duracao_emp')),
            'data_termino_contrato': item.get('dttermino_emp'),
            'certificado_digital': str(item.get('CERTIFICADO_DIGITAL') or '').strip() or '',
            'ramo_atividade': self._mapear_ramo_atividade(item.get('ramo_emp')),
            'regime_fiscal': regime_fiscal,
        }
        
        if not self.dry_run:
            # IDEMPOTÊNCIA: Verificar se já existe e se mudou
            pj_existente = PessoaJuridica.objects.filter(cnpj=cnpj).first()
            
            if pj_existente:
                # Verificar se algum campo mudou
                houve_mudanca = False
                campos_alterados = []
                
                for campo, valor_novo in dados.items():
                    valor_antigo = getattr(pj_existente, campo)
                    if valor_antigo != valor_novo:
                        houve_mudanca = True
                        campos_alterados.append(campo)
                
                if houve_mudanca:
                    # Atualizar apenas se houve mudança
                    for campo, valor in dados.items():
                        setattr(pj_existente, campo, valor)
                    pj_existente.save()
                    stats['pj_atualizadas'] += 1
                    
                    if len(campos_alterados) <= 3:
                        self.stdout.write(f"   📝 PJ {cnpj} atualizada: {', '.join(campos_alterados)}")
                    else:
                        self.stdout.write(f"   📝 PJ {cnpj} atualizada: {len(campos_alterados)} campos")
                else:
                    # Pular - já existe e não mudou (idempotência)
                    stats['pj_puladas'] = stats.get('pj_puladas', 0) + 1
            else:
                # Criar nova PJ
                PessoaJuridica.objects.create(cnpj=cnpj, **dados)
                stats['pj_criadas'] += 1
                self.stdout.write(f"   ✅ PJ {cnpj} criada: {dados['razao_social']}")
        else:
            # Modo dry-run
            if PessoaJuridica.objects.filter(cnpj=cnpj).exists():
                stats['pj_atualizadas'] += 1
            else:
                stats['pj_criadas'] += 1

    def _processar_pessoa_fisica(self, item, cpf, stats):
        """Processa uma Pessoa Física com idempotência"""
        cep = str(item.get('cepe_emp') or '').strip()
        cep_formatado = re.sub(r'\D', '', cep)
        if len(cep_formatado) == 8:
            cep_formatado = f"{cep_formatado[:5]}-{cep_formatado[5:]}"
        else:
            cep_formatado = cep_formatado or ''
        
        dados = {
            'nome_completo': str(item.get('nome_emp') or '').strip() or 'NOME NÃO INFORMADO',
            'logradouro': str(item.get('ende_emp') or '').strip() or '',
            'numero': str(item.get('nume_emp') or '').strip() or '',
            'complemento': str(item.get('comp_emp') or '').strip() or '',
            'bairro': str(item.get('bair_emp') or '').strip() or '',
            'cidade': str(item.get('cida_emp') or '').strip() or '',
            'uf': str(item.get('esta_emp') or '').strip() or '',
            'cep': cep_formatado,
            'telefone': str(item.get('fone_emp') or '').strip() or '',
            'email': str(item.get('email_emp') or '').strip() or '',
        }
        
        if not self.dry_run:
            # IDEMPOTÊNCIA: Verificar se já existe e se mudou
            pf_existente = PessoaFisica.objects.filter(cpf=cpf).first()

            if pf_existente:
                # Verificar se algum campo mudou
                houve_mudanca = False
                campos_alterados = []

                for campo, valor_novo in dados.items():
                    valor_antigo = getattr(pf_existente, campo)
                    if valor_antigo != valor_novo:
                        houve_mudanca = True
                        campos_alterados.append(campo)

                if houve_mudanca:
                    # Atualizar apenas se houve mudança
                    for campo, valor in dados.items():
                        setattr(pf_existente, campo, valor)
                    pf_existente.save()
                    stats['pf_atualizadas'] += 1
                    self.stdout.write(f"   📝 PF {cpf} atualizada: {', '.join(campos_alterados)}")
                else:
                    # Pular - já existe e não mudou (idempotência)
                    stats['pf_puladas'] = stats.get('pf_puladas', 0) + 1
            else:
                # Criar nova PF
                PessoaFisica.objects.create(cpf=cpf, **dados)
                stats['pf_criadas'] += 1
                self.stdout.write(f"   ✅ PF {cpf} criada: {dados['nome_completo']}")
        else:
            # Modo dry-run
            if PessoaFisica.objects.filter(cpf=cpf).exists():
                stats['pf_atualizadas'] += 1
            else:
                stats['pf_criadas'] += 1

    def _mapear_ramo_atividade(self, ramo_emp):
        """Mapeia o código do ramo de atividade"""
        mapeamento = {
            '1': 'comercio',
            '2': 'industria',
            '3': 'servicos',
        }
        return mapeamento.get(str(ramo_emp or ''), None)

    def _mapear_regime_fiscal(self, simples_emp):
        """Mapeia o regime fiscal"""
        if simples_emp == 1:
            return 'simples'
        elif simples_emp == 0:
            return 'presumido'
        return None

    def _converter_duracao_contrato(self, duracao_emp):
        """Converte duração do contrato do Sybase para número
        
        No Sybase, duracao_emp pode ser:
        - 'I' = Indeterminado (None)
        - 'D' = Determinado (None, pois não tem número específico)
        - Número = Meses de duração
        """
        if not duracao_emp:
            return None
        
        # Se for string com 'I' ou 'D', retornar None
        if isinstance(duracao_emp, str) and duracao_emp.strip().upper() in ['I', 'D']:
            return None
        
        # Tentar converter para inteiro
        try:
            return int(duracao_emp)
        except (ValueError, TypeError):
            return None

    def _criar_contabilidade_se_necessario(self, cnpj, codi_emp, stats):
        """Cria uma contabilidade se ela não existir, buscando dados do Sybase
        
        Args:
            cnpj: CNPJ da contabilidade
            codi_emp: Código da empresa no Sybase (id_legado)
            stats: Dicionário de estatísticas
            
        Returns:
            Contabilidade criada ou None se houver erro
        """
        if self.dry_run:
            return None
        
        try:
            # Buscar dados da contabilidade no Sybase
            connection = self.get_sybase_connection()
            if not connection:
                return None
            
            query = f"""
                SELECT 
                    codi_emp, razao_emp, nome_emp, fantasia_emp, 
                    cgce_emp, ende_emp, fone_emp, email_emp
                FROM bethadba.geempre
                WHERE codi_emp = {codi_emp}
            """
            
            resultado = self.execute_query(connection, query)
            
            if not resultado or len(resultado) == 0:
                self.stdout.write(self.style.WARNING(
                    f"   ⚠️  Contabilidade {cnpj} (codi_emp={codi_emp}) não encontrada no Sybase"
                ))
                return None
            
            dados_sybase = resultado[0]
            
            # Criar a contabilidade
            contabilidade = Contabilidade.objects.create(
                cnpj=cnpj,
                id_legado=codi_emp,
                razao_social=str(dados_sybase.get('razao_emp') or dados_sybase.get('nome_emp') or 'CONTABILIDADE').strip(),
                nome_fantasia=str(dados_sybase.get('fantasia_emp') or '').strip() or None,
                endereco=str(dados_sybase.get('ende_emp') or '').strip() or None,
                telefone=str(dados_sybase.get('fone_emp') or '').strip() or None,
                email=str(dados_sybase.get('email_emp') or '').strip() or None,
                ativo=True
            )
            
            stats['contabilidades_criadas'] += 1
            self.stdout.write(self.style.SUCCESS(
                f"   ✨ Contabilidade {cnpj} criada automaticamente: {contabilidade.razao_social}"
            ))
            
            return contabilidade
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(
                f"   ❌ Erro ao criar contabilidade {cnpj}: {e}"
            ))
            return None

    def processar_contratos(self, data, historical_map, stats):
        """Processa os contratos extraídos"""
        self.stdout.write("\n   Processando contratos...")
        
        for i, item in enumerate(data, 1):
            if i % 100 == 0:
                self.stdout.write(f"   Contrato {i}/{len(data)}...")
            
            try:
                # Limpar documentos
                documento_cliente = str(item.get('documento_cliente') or '').strip()
                documento_cliente_limpo = re.sub(r'\D', '', documento_cliente)
                
                cnpj_contabilidade = str(item.get('cnpj_contabilidade') or '').strip()
                cnpj_contabilidade_limpo = re.sub(r'\D', '', cnpj_contabilidade)
                
                # Buscar ou criar contabilidade pelo CNPJ
                contabilidade = Contabilidade.objects.filter(cnpj=cnpj_contabilidade_limpo).first()
                if not contabilidade:
                    # Buscar dados da contabilidade no Sybase (GEEMPRE) usando codi_emp
                    codi_emp_contabilidade = item.get('codi_emp')
                    contabilidade = self._criar_contabilidade_se_necessario(
                        cnpj_contabilidade_limpo, 
                        codi_emp_contabilidade,
                        stats
                    )
                    
                    if not contabilidade:
                        stats['erros'] += 1
                        stats['erros_contabilidade_nao_encontrada'] += 1
                        continue
                
                # Buscar cliente pelo CNPJ/CPF
                cliente_obj = None
                if len(documento_cliente_limpo) == 14:
                    cliente_obj = PessoaJuridica.objects.filter(cnpj=documento_cliente_limpo).first()
                elif len(documento_cliente_limpo) == 11:
                    cliente_obj = PessoaFisica.objects.filter(cpf=documento_cliente_limpo).first()
                
                if not cliente_obj:
                    stats['erros'] += 1
                    stats['erros_cliente_nao_encontrado'] += 1
                    continue
                
                # Criar chave única: CNPJ_Contabilidade + CNPJ_Cliente
                contrato_id_legado = f"{cnpj_contabilidade_limpo}-{documento_cliente_limpo}"
                content_type = ContentType.objects.get_for_model(cliente_obj)

                if not self.dry_run:
                    data_termino = item.get('DATA_TERMINO')
                    
                    # Lógica para determinar se o contrato está ativo
                    ativo = False
                    if data_termino is None:
                        ativo = True
                    else:
                        if isinstance(data_termino, str):
                            try:
                                data_termino = date.fromisoformat(data_termino.split(' ')[0])
                            except (ValueError, TypeError):
                                data_termino = None
                        
                        if data_termino and data_termino > date.today():
                            ativo = True

                    # IDEMPOTÊNCIA: Verificar se já existe e se mudou
                    contrato_existente = Contrato.objects.filter(id_legado=contrato_id_legado).first()
                    
                    dados_contrato = {
                        'contabilidade': contabilidade,
                        'content_type': content_type,
                        'object_id': cliente_obj.id,
                        'data_inicio': item.get('DATA_INICIO'),
                        'data_termino': data_termino,
                        'dia_vencimento': item.get('dia_vencimento'),
                        'valor_honorario': item.get('VALOR_CONTRATO') or 0,
                        'ativo': ativo,
                    }
                    
                    if contrato_existente:
                        # Verificar se algum campo mudou
                        houve_mudanca = False
                        campos_alterados = []
                        
                        for campo, valor_novo in dados_contrato.items():
                            valor_antigo = getattr(contrato_existente, campo)
                            if valor_antigo != valor_novo:
                                houve_mudanca = True
                                campos_alterados.append(campo)
                        
                        if houve_mudanca:
                            # Atualizar apenas se houve mudança
                            for campo, valor in dados_contrato.items():
                                setattr(contrato_existente, campo, valor)
                            contrato_existente.save()
                            stats['contratos_atualizados'] += 1
                            self.stdout.write(f"   📝 Contrato {contrato_id_legado} atualizado: {', '.join(campos_alterados)}")
                        else:
                            # Pular - já existe e não mudou (idempotência)
                            stats['contratos_pulados'] = stats.get('contratos_pulados', 0) + 1
                    else:
                        # Criar novo contrato
                        Contrato.objects.create(id_legado=contrato_id_legado, **dados_contrato)
                        stats['contratos_criados'] += 1
                        self.stdout.write(f"   ✅ Contrato {contrato_id_legado} criado para {cliente_obj}")
                else:
                    # Modo dry-run
                    if Contrato.objects.filter(id_legado=contrato_id_legado).exists():
                        stats['contratos_atualizados'] += 1
                    else:
                        stats['contratos_criados'] += 1
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'   Erro ao processar contrato {i}: {e}'))
                stats['erros'] += 1
                stats['erros_outros'] += 1
                continue

        # Relatório final - APENAS O QUE FOI IMPORTADO/MODIFICADO NESTA EXECUÇÃO
        pj_puladas = stats.get('pj_puladas', 0)
        pf_puladas = stats.get('pf_puladas', 0)
        contratos_pulados = stats.get('contratos_pulados', 0)
        
        self.stdout.write('\n' + '='*70)
        self.stdout.write(self.style.SUCCESS('📊 RELATÓRIO FINAL - ETL 03 (Importação desta Execução)'))
        self.stdout.write('='*70)
        
        self.stdout.write('\n🏢 PESSOAS JURÍDICAS:')
        self.stdout.write(f'   ✅ Criadas nesta execução: {stats["pj_criadas"]}')
        self.stdout.write(f'   📝 Atualizadas (com mudanças): {stats["pj_atualizadas"]}')
        self.stdout.write(f'   ⏭️  Puladas (sem mudanças): {pj_puladas}')
        self.stdout.write(f'   📊 Total processado: {stats["pj_criadas"] + stats["pj_atualizadas"] + pj_puladas}')
        
        self.stdout.write('\n👤 PESSOAS FÍSICAS:')
        self.stdout.write(f'   ✅ Criadas nesta execução: {stats["pf_criadas"]}')
        self.stdout.write(f'   📝 Atualizadas (com mudanças): {stats["pf_atualizadas"]}')
        self.stdout.write(f'   ⏭️  Puladas (sem mudanças): {pf_puladas}')
        self.stdout.write(f'   📊 Total processado: {stats["pf_criadas"] + stats["pf_atualizadas"] + pf_puladas}')
        
        self.stdout.write('\n📄 CONTRATOS:')
        self.stdout.write(f'   ✅ Criados nesta execução: {stats["contratos_criados"]}')
        self.stdout.write(f'   📝 Atualizados (com mudanças): {stats["contratos_atualizados"]}')
        self.stdout.write(f'   ⏭️  Pulados (sem mudanças): {contratos_pulados}')
        self.stdout.write(f'   📊 Total processado: {stats["contratos_criados"] + stats["contratos_atualizados"] + contratos_pulados}')
        
        if stats.get('contabilidades_criadas', 0) > 0:
            self.stdout.write(f'\n✨ CONTABILIDADES CRIADAS AUTOMATICAMENTE: {stats["contabilidades_criadas"]}')
        
        if stats["erros"] > 0:
            self.stdout.write(f'\n❌ ERROS: {stats["erros"]}')
            self.stdout.write(f'   • Contabilidade não encontrada: {stats["erros_contabilidade_nao_encontrada"]}')
            self.stdout.write(f'   • Cliente não encontrado: {stats["erros_cliente_nao_encontrado"]}')
            self.stdout.write(f'   • Documento inválido: {stats["erros_documento_invalido"]}')
            self.stdout.write(f'   • Outros erros: {stats["erros_outros"]}')
        
        # Resumo de impacto
        total_modificacoes = (stats["pj_criadas"] + stats["pj_atualizadas"] + 
                             stats["pf_criadas"] + stats["pf_atualizadas"] + 
                             stats["contratos_criados"] + stats["contratos_atualizados"])
        
        self.stdout.write(f'\n💡 RESUMO:')
        self.stdout.write(f'   • Total de modificações no banco: {total_modificacoes}')
        self.stdout.write(f'   • Registros processados sem mudança (idempotência): {pj_puladas + pf_puladas + contratos_pulados}')
        
        # Calcular taxa de modificação (evitar divisão por zero)
        total_registros = total_modificacoes + pj_puladas + pf_puladas + contratos_pulados
        if total_registros > 0:
            taxa = (total_modificacoes / total_registros * 100)
            self.stdout.write(f'   • Taxa de modificação: {taxa:.1f}%')
        else:
            self.stdout.write(f'   • Taxa de modificação: N/A (nenhum registro processado)')
        
        # Estatísticas de performance
        self.stdout.write('\n⏱️  PERFORMANCE:')
        self.print_stats()
        
        self.stdout.write('\n' + '='*70)
        self.stdout.write(self.style.SUCCESS('✅ ETL 03 CONCLUÍDA COM SUCESSO!'))
        self.stdout.write('='*70)

