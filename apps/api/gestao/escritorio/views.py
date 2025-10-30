"""
Views para Dashboard do Escritório
Endpoint unificado que retorna dados completos do dashboard em uma única requisição
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Count, Sum, Q, F, Avg
from django.utils import timezone
from datetime import datetime, timedelta, date
from calendar import month_abbr
import logging

from apps.core.models import Contabilidade, Usuario
from apps.pessoas.models import PessoaJuridica, PessoaFisica, Contrato
from apps.contabil.models import LancamentoContabil
from apps.fiscal.models import NotaFiscal
from apps.funcionarios.models import VinculoEmpregaticio
from apps.administracao.models import Usuario as UsuarioLegado, UsuarioContabilidade, LogAcesso

logger = logging.getLogger(__name__)


class EscritorioViewSet(viewsets.ViewSet):
    """
    ViewSet para Dashboard do Escritório
    
    Endpoints:
    - GET /api/gestao/escritorio/dashboard/ - Dashboard completo unificado
    """
    
    permission_classes = [IsAuthenticated]
    
    def _get_contratos_queryset(self, request):
        """
        Aplica Regra de Ouro para obter contratos baseado no tipo de usuário
        """
        usuario = request.user
        
        if usuario.is_superuser:
            logger.info(f"[ESCRITORIO/DASHBOARD] ✅ Superuser '{usuario.username}' acessando TODOS os dados")
            return Contrato.objects.all()
        else:
            if not hasattr(usuario, 'contabilidade') or not usuario.contabilidade:
                logger.error(f"[ESCRITORIO/DASHBOARD] ❌ Usuário {usuario.username} não possui contabilidade")
                return None
            
            contabilidade = usuario.contabilidade
            logger.info(f"[ESCRITORIO/DASHBOARD] ✅ Usuário COMUM '{usuario.username}' - Contabilidade: '{contabilidade.razao_social}'")
            return Contrato.objects.filter(contabilidade=contabilidade)
    
    def _get_dados_gerais(self, contabilidade):
        """
        Bloco 1: Dados gerais do escritório
        """
        try:
            # Fallback: tentar obter informações da PessoaJuridica vinculada
            # ATENÇÃO: PessoaJuridica não possui FK direta para Contabilidade aqui no modelo,
            # então buscamos pela correspondência de CNPJ (mesma abordagem usada em outras partes do arquivo)
            pj = PessoaJuridica.objects.filter(cnpj=contabilidade.cnpj).first()

            # Montar endereço a partir da Contabilidade, com fallback da PessoaJuridica
            if contabilidade.endereco:
                endereco_value = contabilidade.endereco
            else:
                if pj:
                    partes_endereco = [
                        pj.logradouro or '',
                        pj.numero or '',
                        pj.complemento or '',
                        pj.bairro or '',
                        pj.cidade or '',
                        pj.uf or '',
                        pj.cep or '',
                    ]
                    # Remover vazios e unir com vírgula/ espaço
                    endereco_value = ', '.join([p for p in partes_endereco if p]) or 'Endereço não informado'
                else:
                    endereco_value = 'Endereço não informado'

            telefone_value = contabilidade.telefone or (pj.telefone if pj and pj.telefone else 'Telefone não informado')
            # Email: preferir da contabilidade; fallback email da PJ; por fim email do resp. legal
            email_value = (
                contabilidade.email
                or (pj.email if pj and pj.email else None)
                or (getattr(pj, 'email_resp_legal', None) if pj else None)
                or 'Email não informado'
            )
            # Responsável: preferir responsável financeiro; fallback responsável legal da PJ
            responsavel_value = (
                contabilidade.responsavel_financeiro_nome
                or (getattr(pj, 'responsavel_legal', None) if pj else None)
                or 'Responsável não informado'
            )

            # Buscar dados consolidados
            dados_contabilidade = {
                'id': str(contabilidade.id),
                'razao_social': contabilidade.razao_social,
                'nome_fantasia': contabilidade.nome_fantasia or contabilidade.razao_social,
                'cnpj': contabilidade.cnpj,
                'endereco': endereco_value,
                'telefone': telefone_value,
                'email': email_value,
                'responsavel': responsavel_value,
                'data_fundacao': contabilidade.created_at.strftime('%Y-%m-%d'),
            }
            
            # Contar total de clientes (contratos únicos)
            total_clientes = Contrato.objects.filter(contabilidade=contabilidade).values('object_id').distinct().count()
            
            # Contar total de usuários ativos
            total_usuarios = UsuarioContabilidade.objects.filter(
                contabilidade=contabilidade,
                ativo=True
            ).values('usuario').distinct().count()
            
            # Identificar módulos ativos (mais comuns nos vínculos)
            modulos_acesso = UsuarioContabilidade.objects.filter(
                contabilidade=contabilidade,
                ativo=True
            ).values_list('modulos_acesso', flat=True)
            
            # Flatten e contar módulos
            modulos_flat = []
            for modulos in modulos_acesso:
                if modulos:
                    modulos_flat.extend(modulos)
            
            # Contar frequência dos módulos
            from collections import Counter
            modulos_count = Counter(modulos_flat)
            modulos_ativos = [modulo for modulo, count in modulos_count.most_common(4)]
            
            # Mapear códigos para nomes legíveis
            modulo_names = {
                'fiscal': 'fiscal',
                'contabil': 'contabil', 
                'rh': 'rh',
                'gestao': 'gestao',
                'administracao': 'administracao'
            }
            
            modulos_ativos_nomes = [modulo_names.get(mod, mod) for mod in modulos_ativos if mod in modulo_names]
            
            dados_gerais = {
                **dados_contabilidade,
                'total_clientes': total_clientes,
                'total_usuarios': total_usuarios,
                'modulos_ativos': modulos_ativos_nomes
            }
            
            return dados_gerais
            
        except Exception as e:
            logger.error(f"[ESCRITORIO/DADOS_GERAIS] Erro ao buscar dados gerais: {e}")
            return {
                'id': str(contabilidade.id),
                'razao_social': contabilidade.razao_social,
                'nome_fantasia': contabilidade.nome_fantasia or contabilidade.razao_social,
                'cnpj': contabilidade.cnpj,
                'endereco': 'Erro ao carregar',
                'telefone': 'Erro ao carregar',
                'email': 'Erro ao carregar',
                'responsavel': 'Erro ao carregar',
                'data_fundacao': contabilidade.created_at.strftime('%Y-%m-%d'),
                'total_clientes': 0,
                'total_usuarios': 0,
                'modulos_ativos': []
            }
    
    def _calcular_analise_mensal(self, contabilidade, meses=12):
        """
        Bloco 2: Análise mensal com todas as métricas
        """
        try:
            hoje = timezone.now().date()
            analise_mensal = []
            
            for i in range(meses):
                # Calcular data do mês (i meses atrás)
                if i == 0:
                    mes_data = hoje.replace(day=1)
                else:
                    mes_anterior = hoje.replace(day=1) - timedelta(days=1)
                    mes_data = mes_anterior.replace(day=1)
                    hoje = mes_anterior
                
                # Nome do mês para display
                mes_display = f"{month_abbr[mes_data.month].lower()}. de {str(mes_data.year)[-2:]}"
                
                # 1. Clientes
                contratos_mes = Contrato.objects.filter(
                    contabilidade=contabilidade,
                    data_inicio__lte=mes_data
                ).filter(
                    Q(data_termino__gte=mes_data) | Q(data_termino__isnull=True)
                )
                
                clientes_ativos = contratos_mes.filter(ativo=True).values('object_id').distinct().count()
                clientes_inativos = contratos_mes.filter(ativo=False).values('object_id').distinct().count()
                quantidade_clientes = clientes_ativos + clientes_inativos
                
                # Novos clientes no mês
                novos_clientes = Contrato.objects.filter(
                    contabilidade=contabilidade,
                    data_inicio__year=mes_data.year,
                    data_inicio__month=mes_data.month
                ).count()
                
                # Cancelados no mês (contratos que terminaram)
                cancelados_clientes = Contrato.objects.filter(
                    contabilidade=contabilidade,
                    data_termino__year=mes_data.year,
                    data_termino__month=mes_data.month
                ).count()
                
                # 2. Faturamento (mock por enquanto - usar billing.Fatura quando disponível)
                faturamento_escritorio = 5000.00 + (i * 1000)  # Mock crescente
                variacao_faturamento = 0.00 if i == 0 else 100.00  # Mock
                
                # 3. Tempo ativo sistema (de LogAcesso)
                tempo_ativo = LogAcesso.objects.filter(
                    contabilidade=contabilidade,
                    data_acesso__year=mes_data.year,
                    data_acesso__month=mes_data.month
                ).aggregate(
                    total_tempo=Sum('tempo_sessao')
                )['total_tempo'] or timedelta(0)
                
                # Converter para horas
                tempo_ativo_horas = tempo_ativo.total_seconds() / 3600
                tempo_ativo_display = f"{int(tempo_ativo_horas)}:{int((tempo_ativo_horas % 1) * 60):02d}:00"
                
                # 4. Lançamentos contábeis
                lancamentos_total = LancamentoContabil.objects.filter(
                    contabilidade=contabilidade,
                    data_lancamento__year=mes_data.year,
                    data_lancamento__month=mes_data.month
                ).count()
                
                # Estimar manual vs automático (90% automático, 10% manual)
                lancamentos_automaticos = int(lancamentos_total * 0.9)
                lancamentos_manuais = lancamentos_total - lancamentos_automaticos
                percentual_lancamentos_manuais = (lancamentos_manuais / lancamentos_total * 100) if lancamentos_total > 0 else 0
                
                # 5. Vínculos de folha ativos (funcionários internos da contabilidade)
                # Buscar a PessoaJuridica associada à contabilidade
                from django.contrib.contenttypes.models import ContentType
                pj_contabilidade = PessoaJuridica.objects.filter(
                    cnpj=contabilidade.cnpj
                ).first()
                
                if pj_contabilidade:
                    # Buscar ContentType de PessoaJuridica
                    pj_content_type = ContentType.objects.get_for_model(PessoaJuridica)
                    
                    # Contar vínculos onde a PJ da contabilidade é o empregador
                    vinculos_folhas_ativos = VinculoEmpregaticio.objects.filter(
                        content_type=pj_content_type,
                        object_id=pj_contabilidade.id,
                        data_admissao__lte=mes_data
                    ).filter(
                        Q(data_demissao__gte=mes_data) | Q(data_demissao__isnull=True),
                        ativo=True
                    ).count()
                else:
                    # Se não encontrar a PJ, retorna 0
                    vinculos_folhas_ativos = 0
                
                # 6. Notas fiscais
                notas_fiscais = NotaFiscal.objects.filter(
                    contabilidade=contabilidade,
                    data_emissao__year=mes_data.year,
                    data_emissao__month=mes_data.month
                )
                
                notas_emitidas = notas_fiscais.count()
                notas_entrada = notas_fiscais.filter(tipo_nota='ENTRADA').count()
                notas_saida = notas_fiscais.filter(tipo_nota='SAIDA').count()
                notas_servicos = notas_fiscais.filter(tipo_nota='SERVICO').count()
                total_notas_fiscais_movimentadas = notas_emitidas
                
                # 7. Custos operacionais (mock baseado em médias)
                custo_operacional = 63677.95  # Mock fixo
                rentabilidade_operacional = faturamento_escritorio - custo_operacional
                margem_operacional = (rentabilidade_operacional / faturamento_escritorio * 100) if faturamento_escritorio > 0 else 0
                
                mes_analise = {
                    'mes': mes_data.strftime('%Y-%m'),
                    'mes_display': mes_display,
                    'quantidade_clientes': quantidade_clientes,
                    'clientes_ativos': clientes_ativos,
                    'clientes_inativos': clientes_inativos,
                    'novos_clientes': novos_clientes,
                    'cancelados_clientes': cancelados_clientes,
                    'faturamento_escritorio': float(faturamento_escritorio),
                    'variacao_faturamento': variacao_faturamento,
                    'tempo_ativo_sistema': tempo_ativo_display,
                    'tempo_ativo_horas': round(tempo_ativo_horas, 2),
                    'lancamentos_total': lancamentos_total,
                    'lancamentos_automaticos': lancamentos_automaticos,
                    'lancamentos_manuais': lancamentos_manuais,
                    'percentual_lancamentos_manuais': round(percentual_lancamentos_manuais, 2),
                    'vinculos_folhas_ativos': vinculos_folhas_ativos,
                    'notas_fiscais_emitidas': notas_emitidas,
                    'notas_fiscais_entrada': notas_entrada,
                    'notas_fiscais_saida': notas_saida,
                    'notas_fiscais_servicos': notas_servicos,
                    'total_notas_fiscais_movimentadas': total_notas_fiscais_movimentadas,
                    'custo_operacional': custo_operacional,
                    'rentabilidade_operacional': round(rentabilidade_operacional, 2),
                    'margem_operacional': round(margem_operacional, 2)
                }
                
                analise_mensal.append(mes_analise)
            
            return analise_mensal
            
        except Exception as e:
            logger.error(f"[ESCRITORIO/ANALISE_MENSAL] Erro ao calcular análise mensal: {e}")
            return []
    
    def _calcular_kpis(self, contabilidade, analise_mensal):
        """
        Bloco 3: KPIs consolidados
        """
        try:
            if not analise_mensal:
                return {}
            
            # Dados do primeiro e último mês
            primeiro_mes = analise_mensal[-1]  # Mais antigo
            ultimo_mes = analise_mensal[0]     # Mais recente
            
            # 1. Total de clientes
            total_clientes_atual = ultimo_mes['quantidade_clientes']
            total_clientes_anterior = primeiro_mes['quantidade_clientes']
            variacao_clientes = total_clientes_atual - total_clientes_anterior
            variacao_percentual_clientes = (variacao_clientes / total_clientes_anterior * 100) if total_clientes_anterior > 0 else 0
            
            # 2. Faturamento anual
            faturamento_anual = sum(mes['faturamento_escritorio'] for mes in analise_mensal)
            faturamento_anterior = sum(mes['faturamento_escritorio'] for mes in analise_mensal[1:]) if len(analise_mensal) > 1 else faturamento_anual
            variacao_faturamento = faturamento_anual - faturamento_anterior
            variacao_percentual_faturamento = (variacao_faturamento / faturamento_anterior * 100) if faturamento_anterior > 0 else 0
            
            # Encontrar mês de maior e menor faturamento
            mes_maior = max(analise_mensal, key=lambda x: x['faturamento_escritorio'])
            mes_menor = min(analise_mensal, key=lambda x: x['faturamento_escritorio'])
            
            # 3. Rentabilidade média
            rentabilidades = [mes['rentabilidade_operacional'] for mes in analise_mensal]
            rentabilidade_media = sum(rentabilidades) / len(rentabilidades)
            melhor_mes = max(analise_mensal, key=lambda x: x['rentabilidade_operacional'])
            
            # 4. Custo por cliente
            custo_por_cliente = ultimo_mes['custo_operacional'] / ultimo_mes['quantidade_clientes'] if ultimo_mes['quantidade_clientes'] > 0 else 0
            custo_anterior = primeiro_mes['custo_operacional'] / primeiro_mes['quantidade_clientes'] if primeiro_mes['quantidade_clientes'] > 0 else 0
            variacao_custo = custo_por_cliente - custo_anterior
            variacao_percentual_custo = (variacao_custo / custo_anterior * 100) if custo_anterior > 0 else 0
            
            # 5. Tempo ativo total
            tempo_ativo_total = sum(mes['tempo_ativo_horas'] for mes in analise_mensal)
            tempo_ativo_display = f"{int(tempo_ativo_total)}:{int((tempo_ativo_total % 1) * 60):02d}:00"
            media_mensal_horas = tempo_ativo_total / len(analise_mensal)
            
            # 6. Notas fiscais ano
            total_notas = sum(mes['total_notas_fiscais_movimentadas'] for mes in analise_mensal)
            notas_emitidas = sum(mes['notas_fiscais_emitidas'] for mes in analise_mensal)
            notas_entrada = sum(mes['notas_fiscais_entrada'] for mes in analise_mensal)
            notas_saida = sum(mes['notas_fiscais_saida'] for mes in analise_mensal)
            notas_servicos = sum(mes['notas_fiscais_servicos'] for mes in analise_mensal)
            media_mensal_notas = total_notas / len(analise_mensal)
            
            # 7. Lançamentos contábeis
            total_lancamentos = sum(mes['lancamentos_total'] for mes in analise_mensal)
            media_mensal_lancamentos = total_lancamentos / len(analise_mensal)
            percentual_automaticos = sum(mes['lancamentos_automaticos'] for mes in analise_mensal) / total_lancamentos * 100 if total_lancamentos > 0 else 0
            percentual_manuais = 100 - percentual_automaticos
            
            # 8. Produtividade equipe
            usuarios_ativos = UsuarioContabilidade.objects.filter(
                contabilidade=contabilidade,
                ativo=True
            ).count()
            
            lancamentos_por_hora = total_lancamentos / tempo_ativo_total if tempo_ativo_total > 0 else 0
            tempo_medio_por_lancamento = (tempo_ativo_total * 60) / total_lancamentos if total_lancamentos > 0 else 0  # em minutos
            eficiencia_media = 85.5  # Mock baseado em padrões
            
            kpis = {
                'total_clientes': {
                    'valor': total_clientes_atual,
                    'variacao': round(variacao_clientes, 1),
                    'variacao_percentual': round(variacao_percentual_clientes, 2),
                    'tendencia': 'crescente' if variacao_clientes > 0 else 'decrescente' if variacao_clientes < 0 else 'estavel',
                    'comparacao_mes_anterior': variacao_clientes,
                    'comparacao_ano_anterior': variacao_clientes
                },
                'faturamento_anual': {
                    'valor': round(faturamento_anual, 2),
                    'variacao': round(variacao_faturamento, 2),
                    'variacao_percentual': round(variacao_percentual_faturamento, 2),
                    'tendencia': 'crescente' if variacao_faturamento > 0 else 'decrescente' if variacao_faturamento < 0 else 'estavel',
                    'mes_maior_faturamento': mes_maior['mes'],
                    'valor_maior_faturamento': round(mes_maior['faturamento_escritorio'], 2),
                    'mes_menor_faturamento': mes_menor['mes'],
                    'valor_menor_faturamento': round(mes_menor['faturamento_escritorio'], 2)
                },
                'rentabilidade_media': {
                    'valor': round(rentabilidade_media, 2),
                    'variacao': round(rentabilidade_media - primeiro_mes['rentabilidade_operacional'], 1),
                    'variacao_percentual': round((rentabilidade_media - primeiro_mes['rentabilidade_operacional']) / abs(primeiro_mes['rentabilidade_operacional']) * 100, 1) if primeiro_mes['rentabilidade_operacional'] != 0 else 0,
                    'tendencia': 'crescente' if rentabilidade_media > primeiro_mes['rentabilidade_operacional'] else 'decrescente',
                    'melhor_mes': melhor_mes['mes'],
                    'melhor_valor': round(melhor_mes['rentabilidade_operacional'], 2)
                },
                'custo_por_cliente': {
                    'valor': round(custo_por_cliente, 2),
                    'variacao': round(variacao_custo, 1),
                    'variacao_percentual': round(variacao_percentual_custo, 2),
                    'tendencia': 'estavel' if abs(variacao_percentual_custo) < 5 else 'crescente' if variacao_percentual_custo > 0 else 'decrescente',
                    'media_anual': round(custo_por_cliente, 2)
                },
                'tempo_ativo_total': {
                    'valor_horas': round(tempo_ativo_total, 2),
                    'valor_display': tempo_ativo_display,
                    'media_mensal_horas': round(media_mensal_horas, 2),
                    'variacao': 0,
                    'tendencia': 'estavel'
                },
                'notas_fiscais_ano': {
                    'total': total_notas,
                    'emitidas': notas_emitidas,
                    'entrada': notas_entrada,
                    'saida': notas_saida,
                    'servicos': notas_servicos,
                    'media_mensal': round(media_mensal_notas, 2),
                    'variacao': 8.5,  # Mock
                    'tendencia': 'crescente'
                },
                'lancamentos_contabeis': {
                    'total_ano': total_lancamentos,
                    'media_mensal': round(media_mensal_lancamentos, 0),
                    'percentual_automaticos': round(percentual_automaticos, 2),
                    'percentual_manuais': round(percentual_manuais, 2),
                    'variacao': 5.2,  # Mock
                    'tendencia': 'crescente'
                },
                'produtividade_equipe': {
                    'lancamentos_por_hora': round(lancamentos_por_hora, 2),
                    'tempo_medio_por_lancamento': round(tempo_medio_por_lancamento, 2),
                    'eficiencia_media': eficiencia_media,
                    'usuarios_ativos': usuarios_ativos,
                    'variacao': 3.2,  # Mock
                    'tendencia': 'crescente'
                }
            }
            
            return kpis
            
        except Exception as e:
            logger.error(f"[ESCRITORIO/KPIS] Erro ao calcular KPIs: {e}")
            return {}
    
    def _calcular_rentabilidade(self, analise_mensal):
        """
        Bloco 4: Rentabilidade detalhada por mês
        """
        try:
            rentabilidade = []
            
            for mes in analise_mensal:
                receita = mes['faturamento_escritorio']
                custos_operacionais = mes['custo_operacional']
                
                # Distribuição de custos (mock baseado em médias)
                custos_pessoal = custos_operacionais * 0.70
                custos_infraestrutura = custos_operacionais * 0.19
                custos_outros = custos_operacionais * 0.11
                
                lucro_bruto = receita - custos_operacionais
                margem_bruta = (lucro_bruto / receita * 100) if receita > 0 else 0
                roi = (lucro_bruto / custos_operacionais * 100) if custos_operacionais > 0 else 0
                
                mes_rentabilidade = {
                    'mes': mes['mes'],
                    'mes_display': mes['mes_display'],
                    'receita': round(receita, 2),
                    'custos_operacionais': round(custos_operacionais, 2),
                    'custos_pessoal': round(custos_pessoal, 2),
                    'custos_infraestrutura': round(custos_infraestrutura, 2),
                    'custos_outros': round(custos_outros, 2),
                    'lucro_bruto': round(lucro_bruto, 2),
                    'margem_bruta': round(margem_bruta, 2),
                    'roi': round(roi, 2)
                }
                
                rentabilidade.append(mes_rentabilidade)
            
            return rentabilidade
            
        except Exception as e:
            logger.error(f"[ESCRITORIO/RENTABILIDADE] Erro ao calcular rentabilidade: {e}")
            return []
    
    def _calcular_tendencias(self, analise_mensal, kpis):
        """
        Bloco 5: Tendências e projeções
        """
        try:
            if not analise_mensal or not kpis:
                return {}
            
            # Análise de crescimento de clientes
            primeiro_mes = analise_mensal[-1]
            ultimo_mes = analise_mensal[0]
            crescimento_clientes = kpis['total_clientes']['variacao_percentual']
            
            # Análise de faturamento
            faturamentos = [mes['faturamento_escritorio'] for mes in analise_mensal]
            variacao_faturamento = kpis['faturamento_anual']['variacao_percentual']
            
            # Calcular volatilidade (desvio padrão simples)
            media_faturamento = sum(faturamentos) / len(faturamentos)
            variancia = sum((f - media_faturamento) ** 2 for f in faturamentos) / len(faturamentos)
            volatilidade = (variancia ** 0.5) / media_faturamento * 100 if media_faturamento > 0 else 0
            
            # Análise de rentabilidade
            rentabilidades = [mes['rentabilidade_operacional'] for mes in analise_mensal]
            melhor_mes_rent = max(analise_mensal, key=lambda x: x['rentabilidade_operacional'])
            pior_mes_rent = min(analise_mensal, key=lambda x: x['rentabilidade_operacional'])
            
            # Análise de produtividade
            produtividade_media = kpis['produtividade_equipe']['eficiencia_media']
            variacao_produtividade = kpis['produtividade_equipe']['variacao']
            
            tendencias = {
                'crescimento_clientes': {
                    'periodo': '12_meses',
                    'taxa_crescimento': round(crescimento_clientes, 1),
                    'tendencia': 'crescimento_consistente' if crescimento_clientes > 10 else 'crescimento_leve' if crescimento_clientes > 0 else 'estavel',
                    'previsao_proximo_mes': ultimo_mes['quantidade_clientes'] + int(crescimento_clientes / 12),
                    'previsao_trimestre': ultimo_mes['quantidade_clientes'] + int(crescimento_clientes / 4)
                },
                'faturamento': {
                    'periodo': '12_meses',
                    'variacao_percentual': round(variacao_faturamento, 2),
                    'tendencia': 'crescimento_irregular' if volatilidade > 20 else 'crescimento_consistente' if variacao_faturamento > 0 else 'estavel',
                    'pico_mes': melhor_mes_rent['mes'],
                    'pico_valor': round(melhor_mes_rent['faturamento_escritorio'], 2),
                    'vale_mes': pior_mes_rent['mes'],
                    'vale_valor': round(pior_mes_rent['faturamento_escritorio'], 2),
                    'volatilidade': round(volatilidade, 1),
                    'previsao_proximo_mes': round(ultimo_mes['faturamento_escritorio'] * (1 + variacao_faturamento / 100 / 12), 2)
                },
                'rentabilidade': {
                    'periodo': '12_meses',
                    'tendencia': 'prejuizo_constante' if all(r < 0 for r in rentabilidades) else 'lucro_irregular' if any(r > 0 for r in rentabilidades) else 'estavel',
                    'melhor_mes': melhor_mes_rent['mes'],
                    'melhor_valor': round(melhor_mes_rent['rentabilidade_operacional'], 2),
                    'pior_mes': pior_mes_rent['mes'],
                    'pior_valor': round(pior_mes_rent['rentabilidade_operacional'], 2),
                    'ponto_equilibrio_estimado': 'não_alcançado' if all(r < 0 for r in rentabilidades) else 'alcançado',
                    'acoes_recomendadas': [
                        'aumentar_faturamento' if any(r < 0 for r in rentabilidades) else 'manter_estrategia',
                        'reduzir_custos_operacionais' if any(r < 0 for r in rentabilidades) else 'otimizar_produtividade',
                        'otimizar_produtividade'
                    ]
                },
                'produtividade': {
                    'periodo': '12_meses',
                    'tendencia': 'crescimento_leve' if variacao_produtividade > 0 else 'estavel',
                    'eficiencia_media': produtividade_media,
                    'variacao': variacao_produtividade,
                    'areas_melhoria': [
                        'automacao_lancamentos' if kpis['lancamentos_contabeis']['percentual_manuais'] > 15 else 'manter_automacao',
                        'reducao_tempo_processamento' if kpis['produtividade_equipe']['tempo_medio_por_lancamento'] > 20 else 'otimizar_processos'
                    ]
                }
            }
            
            return tendencias
            
        except Exception as e:
            logger.error(f"[ESCRITORIO/TENDENCIAS] Erro ao calcular tendências: {e}")
            return {}
    
    def _gerar_insights(self, kpis, tendencias, analise_mensal):
        """
        Bloco 6: Insights automáticos
        """
        try:
            insights = []
            
            # Insight 1: Rentabilidade
            if kpis.get('rentabilidade_media', {}).get('valor', 0) < 0:
                insights.append({
                    'tipo': 'alerta',
                    'categoria': 'rentabilidade',
                    'prioridade': 'alta',
                    'titulo': 'Rentabilidade Negativa Consistente',
                    'descricao': 'O escritório apresenta rentabilidade negativa em todos os meses do período analisado',
                    'impacto': f"Prejuízo médio mensal de R$ {abs(kpis.get('rentabilidade_media', {}).get('valor', 0)):,.2f}",
                    'recomendacoes': [
                        'Aumentar faturamento médio por cliente',
                        'Revisar estrutura de custos operacionais',
                        'Avaliar produtividade da equipe'
                    ]
                })
            
            # Insight 2: Crescimento
            crescimento = tendencias.get('crescimento_clientes', {}).get('taxa_crescimento', 0)
            if crescimento > 10:
                insights.append({
                    'tipo': 'oportunidade',
                    'categoria': 'crescimento',
                    'prioridade': 'media',
                    'titulo': 'Crescimento Consistente de Clientes',
                    'descricao': f'Base de clientes cresceu {crescimento:.1f}% no período',
                    'impacto': f"{kpis.get('total_clientes', {}).get('comparacao_ano_anterior', 0)} novos clientes no ano",
                    'recomendacoes': [
                        'Manter estratégias de captação atuais',
                        'Investir em retenção de clientes'
                    ]
                })
            
            # Insight 3: Automação
            percentual_manuais = kpis.get('lancamentos_contabeis', {}).get('percentual_manuais', 0)
            if percentual_manuais > 15:
                insights.append({
                    'tipo': 'otimizacao',
                    'categoria': 'automacao',
                    'prioridade': 'media',
                    'titulo': 'Oportunidade de Automação',
                    'descricao': f'{percentual_manuais:.1f}% dos lançamentos ainda são manuais',
                    'impacto': 'Potencial redução de 15% no tempo de processamento',
                    'recomendacoes': [
                        'Implementar mais regras de automação',
                        'Treinar equipe em ferramentas automatizadas'
                    ]
                })
            
            return insights
            
        except Exception as e:
            logger.error(f"[ESCRITORIO/INSIGHTS] Erro ao gerar insights: {e}")
            return []
    
    def _calcular_custos(self, analise_mensal):
        """
        Bloco 7: Análise de custos
        """
        try:
            if not analise_mensal:
                return {}
            
            # Custos totais do período
            custo_total_periodo = sum(mes['custo_operacional'] for mes in analise_mensal)
            custo_medio_mensal = custo_total_periodo / len(analise_mensal)
            
            # Custo por cliente (média)
            total_clientes_medio = sum(mes['quantidade_clientes'] for mes in analise_mensal) / len(analise_mensal)
            custo_por_cliente = custo_medio_mensal / total_clientes_medio if total_clientes_medio > 0 else 0
            
            # Custo por usuário (média)
            usuarios_medio = 12  # Mock - seria calculado de UsuarioContabilidade
            custo_por_usuario = custo_medio_mensal / usuarios_medio if usuarios_medio > 0 else 0
            
            # Custo por lançamento (média)
            total_lancamentos = sum(mes['lancamentos_total'] for mes in analise_mensal)
            custo_por_lancamento = custo_total_periodo / total_lancamentos if total_lancamentos > 0 else 0
            
            # Distribuição de custos (baseada em médias do setor)
            distribuicao_custos = [
                {
                    'categoria': 'pessoal',
                    'valor': round(custo_total_periodo * 0.70, 2),
                    'percentual': 70.67
                },
                {
                    'categoria': 'infraestrutura',
                    'valor': round(custo_total_periodo * 0.19, 2),
                    'percentual': 18.85
                },
                {
                    'categoria': 'software',
                    'valor': round(custo_total_periodo * 0.06, 2),
                    'percentual': 6.28
                },
                {
                    'categoria': 'outros',
                    'valor': round(custo_total_periodo * 0.05, 2),
                    'percentual': 4.20
                }
            ]
            
            # Evolução de custos
            evolucao_custos = []
            for mes in analise_mensal:
                custo_mes = mes['custo_operacional']
                clientes_mes = mes['quantidade_clientes']
                custo_por_cliente_mes = custo_mes / clientes_mes if clientes_mes > 0 else 0
                
                evolucao_custos.append({
                    'mes': mes['mes'],
                    'custo_total': round(custo_mes, 2),
                    'custo_por_cliente': round(custo_por_cliente_mes, 2)
                })
            
            custos = {
                'custo_total_periodo': round(custo_total_periodo, 2),
                'custo_medio_mensal': round(custo_medio_mensal, 2),
                'custo_por_cliente': round(custo_por_cliente, 2),
                'custo_por_usuario': round(custo_por_usuario, 2),
                'custo_por_lancamento': round(custo_por_lancamento, 2),
                'distribuicao_custos': distribuicao_custos,
                'evolucao_custos': evolucao_custos
            }
            
            return custos
            
        except Exception as e:
            logger.error(f"[ESCRITORIO/CUSTOS] Erro ao calcular custos: {e}")
            return {}
    
    def _calcular_produtividade(self, contabilidade, periodo):
        """
        Bloco 8: Métricas de produtividade
        """
        try:
            # Buscar usuários ativos da contabilidade
            usuarios_ativos = UsuarioContabilidade.objects.filter(
                contabilidade=contabilidade,
                ativo=True
            ).select_related('usuario')
            
            # Métricas globais (mock por enquanto)
            metricas_globais = {
                'produtividade_media': 85.5,
                'eficiencia_media': 82.3,
                'tempo_medio_por_lancamento_minutos': 14.35,
                'lancamentos_por_hora': 4.18,
                'taxa_automacao': 90.36
            }
            
            # Distribuição de produtividade (mock)
            distribuicao_produtividade = [
                {
                    'faixa': 'alta',
                    'faixa_display': 'Alta (>90%)',
                    'usuarios': 4,
                    'percentual': 33.33
                },
                {
                    'faixa': 'media',
                    'faixa_display': 'Média (70-90%)',
                    'usuarios': 6,
                    'percentual': 50.00
                },
                {
                    'faixa': 'baixa',
                    'faixa_display': 'Baixa (<70%)',
                    'usuarios': 2,
                    'percentual': 16.67
                }
            ]
            
            # Evolução de produtividade (mock)
            evolucao_produtividade = []
            for i, mes in enumerate(periodo):
                evolucao_produtividade.append({
                    'mes': mes['mes'],
                    'produtividade': 83.2 + (i * 0.5),
                    'eficiencia': 80.5 + (i * 0.3)
                })
            
            # Top 5 usuários (mock)
            usuarios_top_5 = []
            for i, usuario_vinculo in enumerate(usuarios_ativos[:5]):
                usuarios_top_5.append({
                    'usuario_id': str(usuario_vinculo.usuario.id),
                    'usuario_nome': usuario_vinculo.usuario.nome_usuario,
                    'produtividade': 95.5 - (i * 2),
                    'lancamentos_total': 8500 - (i * 500),
                    'tempo_ativo': f"{520 - (i * 30)}:30:00"
                })
            
            produtividade = {
                'metricas_globais': metricas_globais,
                'distribuicao_produtividade': distribuicao_produtividade,
                'evolucao_produtividade': evolucao_produtividade,
                'usuarios_top_5': usuarios_top_5
            }
            
            return produtividade
            
        except Exception as e:
            logger.error(f"[ESCRITORIO/PRODUTIVIDADE] Erro ao calcular produtividade: {e}")
            return {}
    
    def _calcular_projecoes(self, analise_mensal, tendencias):
        """
        Bloco 9: Projeções futuras
        """
        try:
            if not analise_mensal or not tendencias:
                return {}
            
            ultimo_mes = analise_mensal[0]
            
            # Projeção próximo mês
            crescimento_clientes = tendencias.get('crescimento_clientes', {}).get('taxa_crescimento', 0)
            variacao_faturamento = tendencias.get('faturamento', {}).get('variacao_percentual', 0)
            
            proximo_mes = {
                'mes': '2025-02',  # Mock
                'previsao_clientes': ultimo_mes['quantidade_clientes'] + int(crescimento_clientes / 12),
                'previsao_faturamento': ultimo_mes['faturamento_escritorio'] * (1 + variacao_faturamento / 100 / 12),
                'previsao_custos': ultimo_mes['custo_operacional'],
                'previsao_rentabilidade': ultimo_mes['faturamento_escritorio'] * (1 + variacao_faturamento / 100 / 12) - ultimo_mes['custo_operacional'],
                'confianca': 75
            }
            
            # Projeção próximo trimestre
            proximo_trimestre = {
                'periodo': '2025-Q1',
                'previsao_clientes_fim': ultimo_mes['quantidade_clientes'] + int(crescimento_clientes / 4),
                'previsao_faturamento_total': ultimo_mes['faturamento_escritorio'] * 3 * (1 + variacao_faturamento / 100 / 4),
                'previsao_custos_total': ultimo_mes['custo_operacional'] * 3,
                'previsao_rentabilidade': ultimo_mes['faturamento_escritorio'] * 3 * (1 + variacao_faturamento / 100 / 4) - ultimo_mes['custo_operacional'] * 3,
                'confianca': 65
            }
            
            # Cenários
            cenarios = [
                {
                    'nome': 'otimista',
                    'descricao': 'Aumento de 30% no faturamento com redução de 10% nos custos',
                    'faturamento_mensal': ultimo_mes['faturamento_escritorio'] * 1.3,
                    'custos_mensal': ultimo_mes['custo_operacional'] * 0.9,
                    'rentabilidade_mensal': ultimo_mes['faturamento_escritorio'] * 1.3 - ultimo_mes['custo_operacional'] * 0.9,
                    'probabilidade': 20
                },
                {
                    'nome': 'realista',
                    'descricao': 'Manutenção das tendências atuais',
                    'faturamento_mensal': proximo_mes['previsao_faturamento'],
                    'custos_mensal': proximo_mes['previsao_custos'],
                    'rentabilidade_mensal': proximo_mes['previsao_rentabilidade'],
                    'probabilidade': 60
                },
                {
                    'nome': 'pessimista',
                    'descricao': 'Redução de 20% no faturamento com custos estáveis',
                    'faturamento_mensal': ultimo_mes['faturamento_escritorio'] * 0.8,
                    'custos_mensal': ultimo_mes['custo_operacional'],
                    'rentabilidade_mensal': ultimo_mes['faturamento_escritorio'] * 0.8 - ultimo_mes['custo_operacional'],
                    'probabilidade': 20
                }
            ]
            
            projecoes = {
                'proximo_mes': proximo_mes,
                'proximo_trimestre': proximo_trimestre,
                'cenarios': cenarios
            }
            
            return projecoes
            
        except Exception as e:
            logger.error(f"[ESCRITORIO/PROJECOES] Erro ao calcular projeções: {e}")
            return {}
    
    @action(detail=False, methods=['get'], url_path='dashboard')
    def dashboard(self, request):
        """
        GET /api/gestao/escritorio/dashboard/
        
        Endpoint unificado que retorna dashboard completo do escritório
        """
        try:
            # 1. Aplicar Regra de Ouro
            contratos_queryset = self._get_contratos_queryset(request)
            if contratos_queryset is None:
                return Response(
                    {"error": "Usuário não possui contabilidade associada"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Determinar contabilidade
            if request.user.is_superuser:
                # Superuser: usar primeira contabilidade como exemplo
                contabilidade = Contabilidade.objects.first()
                if not contabilidade:
                    return Response(
                        {"error": "Nenhuma contabilidade encontrada no sistema"}, 
                        status=status.HTTP_404_NOT_FOUND
                    )
            else:
                contabilidade = request.user.contabilidade
            
            logger.info(f"[ESCRITORIO/DASHBOARD] Processando dashboard para contabilidade: {contabilidade.razao_social}")
            
            # 2. Chamar todas as funções auxiliares
            dados_gerais = self._get_dados_gerais(contabilidade)
            analise_mensal = self._calcular_analise_mensal(contabilidade, meses=12)
            kpis = self._calcular_kpis(contabilidade, analise_mensal)
            rentabilidade = self._calcular_rentabilidade(analise_mensal)
            tendencias = self._calcular_tendencias(analise_mensal, kpis)
            insights = self._gerar_insights(kpis, tendencias, analise_mensal)
            custos = self._calcular_custos(analise_mensal)
            produtividade = self._calcular_produtividade(contabilidade, analise_mensal)
            projecoes = self._calcular_projecoes(analise_mensal, tendencias)
            
            # 3. Montar resposta completa
            response_data = {
                'dados_gerais': dados_gerais,
                'analise_mensal': analise_mensal,
                'kpis': kpis,
                'rentabilidade': rentabilidade,
                'tendencias': tendencias,
                'custos': custos,
                'produtividade': produtividade,
                'insights': insights,
                'projecoes': projecoes,
                'metadata': {
                    'periodo_analisado': {
                        'data_inicio': analise_mensal[-1]['mes'] if analise_mensal else '2024-01-01',
                        'data_fim': analise_mensal[0]['mes'] if analise_mensal else '2024-12-31',
                        'total_meses': len(analise_mensal)
                    },
                    'data_geracao': timezone.now().isoformat(),
                    'versao_api': '1.0',
                    'tempo_processamento_ms': 450  # Mock
                }
            }
            
            logger.info(f"[ESCRITORIO/DASHBOARD] Dashboard gerado com sucesso para {contabilidade.razao_social}")
            
            # 4. Retornar Response
            return Response(response_data)
            
        except Exception as e:
            logger.exception(f"[ESCRITORIO/DASHBOARD] Erro crítico ao gerar dashboard")
            return Response(
                {"error": f"Erro interno ao gerar dashboard: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )