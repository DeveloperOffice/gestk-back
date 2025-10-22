from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from django.db.models import Count, Q, F
from django.utils import timezone
from datetime import timedelta, datetime
from django.contrib.contenttypes.models import ContentType
from calendar import month_abbr

from apps.core.models import Contabilidade, Usuario
from apps.pessoas.models import PessoaJuridica, PessoaFisica, Contrato
from apps.contabil.models import LancamentoContabil
from apps.fiscal.models import NotaFiscal
from ..serializers import (
    CarteiraClientesSerializer, CarteiraCategoriasSerializer, CarteiraEvolucaoSerializer
)
from apps.importacao.management.commands._base import BaseETLCommand

import logging
logger = logging.getLogger(__name__)


class ClientesPagination(PageNumberPagination):
    """Paginação customizada para lista de clientes"""
    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 100


class CarteiraViewSet(viewsets.ViewSet):
    @action(detail=False, methods=['get'], url_path='dashboard')
    def dashboard(self, request):
        """
        GET /api/gestao/carteira/dashboard/
        Endpoint consolidado: retorna todos os blocos do dashboard em uma única resposta.
        """
        try:
            # 1. Aplicar Regra de Ouro para TODOS os usuários (incluindo superuser)
            # A Regra de Ouro mapeia todas as contabilidades e seus clientes
            historical_map = self._build_historical_map()
            todos_os_contratos = self._get_contratos_queryset(request)
            if todos_os_contratos is None:
                return Response({"error": "Usuário não possui contabilidade associada"}, status=status.HTTP_400_BAD_REQUEST)

            usuario = request.user
            pj_content_type = ContentType.objects.get_for_model(PessoaJuridica)
            pf_content_type = ContentType.objects.get_for_model(PessoaFisica)
            
            # Aplicar Regra de Ouro para todos os usuários
            cnpjs_validos = set(historical_map.keys())
            pj_ids_validos = PessoaJuridica.objects.filter(cnpj__in=cnpjs_validos).values_list('id', flat=True)
            pf_ids_validos = PessoaFisica.objects.filter(cpf__in=cnpjs_validos).values_list('id', flat=True)
            contratos_validos = todos_os_contratos.filter(
                Q(content_type=pj_content_type, object_id__in=pj_ids_validos) |
                Q(content_type=pf_content_type, object_id__in=pf_ids_validos)
            )
            
            logger.info(f"[CARTEIRA/DASHBOARD] ✅ Usuário '{usuario.username}' - Regra de Ouro aplicada: {len(cnpjs_validos)} empresas mapeadas")

            # --- Bloco 1: Summary ---
            empresas_unicas = contratos_validos.values('object_id').distinct().count()
            clientes_ativos_qs = contratos_validos.filter(ativo=True)
            empresas_ativas = clientes_ativos_qs.values('object_id').distinct().count()
            empresas_inativas = empresas_unicas - empresas_ativas
            data_limite_novos = timezone.now().date() - timedelta(days=30)
            empresas_novas = clientes_ativos_qs.filter(data_inicio__gte=data_limite_novos).values('object_id').distinct().count()
            percentual_ativo = (empresas_ativas / empresas_unicas * 100) if empresas_unicas > 0 else 0
            summary = {
                'total_clientes': empresas_unicas,
                'clientes_ativos': empresas_ativas,
                'clientes_inativos': empresas_inativas,
                'clientes_novos': empresas_novas,
                'clientes_sem_movimentacao': 0,  # TODO: implementar lógica
                'percentual_ativo': round(percentual_ativo, 2)
            }

            # --- Bloco 2: Categorias ---
            ativos_count = contratos_validos.filter(ativo=True).values('object_id').distinct().count()
            inativos_count = contratos_validos.values('object_id').distinct().count() - ativos_count
            categorias = [
                {'id': 'cat-ativos', 'nome': 'Ativos', 'status': 'ativo', 'quantidade': ativos_count},
                {'id': 'cat-inativos', 'nome': 'Inativos', 'status': 'inativo', 'quantidade': inativos_count}
            ]

            # --- Bloco 3: Regime Tributário ---
            contratos_pj = contratos_validos.filter(content_type=pj_content_type)
            total_pj = contratos_pj.values('object_id').distinct().count()
            regimes_map = {
                '1': 'Simples Nacional',
                '2': 'Lucro Presumido',
                '3': 'Lucro Real',
                '4': 'MEI - Microempreendedor Individual'
            }
            regime_tributario = []
            for regime_key, regime_nome in regimes_map.items():
                pj_ids = PessoaJuridica.objects.filter(regime_tributario=regime_key, id__in=pj_ids_validos).values_list('id', flat=True)
                quantidade = contratos_pj.filter(object_id__in=pj_ids).values('object_id').distinct().count()
                percentual = (quantidade / total_pj * 100) if total_pj > 0 else 0
                regime_tributario.append({
                    'regime': regime_key,
                    'nome': regime_nome,
                    'quantidade': quantidade,
                    'percentual': round(percentual, 2)
                })

            # --- Bloco 4: CNAE Principal (Classificação por CNAE) ---
            def categoria_por_cnae(cnae):
                if not cnae:
                    return "Desconhecido"
                try:
                    prefixo = int(str(cnae).replace("-", "").replace("/", "")[:2])
                    if prefixo in range(1, 10):
                        return "Agropecuária"
                    elif prefixo in range(10, 34):
                        return "Indústria"
                    elif prefixo == 35:
                        return "Energia"
                    elif prefixo in range(36, 40):
                        return "Saneamento e Resíduos"
                    elif prefixo in range(41, 44):
                        return "Construção"
                    elif prefixo in range(45, 48):
                        return "Comércio"
                    elif prefixo in range(49, 54):
                        return "Transporte e Logística"
                    elif prefixo in range(55, 57):
                        return "Hospedagem e Alimentação"
                    elif prefixo in range(58, 64):
                        return "Informação e Comunicação"
                    elif prefixo in range(65, 67):
                        return "Financeiro e Seguros"
                    elif prefixo in range(68, 75):
                        return "Serviços Profissionais"
                    elif prefixo in range(77, 84):
                        return "Administração Pública e Serviços Diversos"
                    elif prefixo in range(85, 89):
                        return "Educação e Saúde"
                    elif prefixo in range(90, 94):
                        return "Cultura, Esporte e Lazer"
                    elif prefixo in range(95, 100):
                        return "Serviços Domésticos"
                    else:
                        return "Outros"
                except:
                    return "Desconhecido"
            
            cnae_principal_stats = []
            cnaes_principais = PessoaJuridica.objects.filter(
                cnae_codigo__isnull=False, 
                cnae_codigo__gt='',
                id__in=pj_ids_validos
            )
            
            cnae_grupos = {}
            for pj in cnaes_principais:
                cnae_codigo = pj.cnae_codigo
                if cnae_codigo:
                    categoria = categoria_por_cnae(cnae_codigo)
                    if categoria not in cnae_grupos:
                        cnae_grupos[categoria] = {
                            'categoria': categoria,
                            'quantidade': 0
                        }
                    cnae_grupos[categoria]['quantidade'] += 1
            
            total_empresas_com_cnae = sum(grupo['quantidade'] for grupo in cnae_grupos.values())
            for categoria, dados in cnae_grupos.items():
                percentual = (dados['quantidade'] / total_empresas_com_cnae * 100) if total_empresas_com_cnae > 0 else 0
                cnae_principal_stats.append({
                    'categoria': categoria,
                    'nome': categoria,
                    'quantidade': dados['quantidade'],
                    'percentual': round(percentual, 2)
                })
            cnae_principal_stats.sort(key=lambda x: x['quantidade'], reverse=True)

            # --- Bloco 5: Regime Tributário Secundário ---
            regime_secundario_stats = []
            # Cooperativas
            cooperativas = PessoaJuridica.objects.filter(cooperativa=True, id__in=pj_ids_validos).count()
            if cooperativas > 0:
                percentual = (cooperativas / total_pj * 100) if total_pj > 0 else 0
                regime_secundario_stats.append({
                    'tipo': 'cooperativa',
                    'nome': 'Cooperativas',
                    'quantidade': cooperativas,
                    'percentual': round(percentual, 2)
                })
            
            # Construtoras
            construtoras = PessoaJuridica.objects.filter(construtora=True, id__in=pj_ids_validos).count()
            if construtoras > 0:
                percentual = (construtoras / total_pj * 100) if total_pj > 0 else 0
                regime_secundario_stats.append({
                    'tipo': 'construtora',
                    'nome': 'Construtoras',
                    'quantidade': construtoras,
                    'percentual': round(percentual, 2)
                })
            
            # Produtores Rurais
            produtores_rurais = PessoaJuridica.objects.filter(produtor_rural=True, id__in=pj_ids_validos).count()
            if produtores_rurais > 0:
                percentual = (produtores_rurais / total_pj * 100) if total_pj > 0 else 0
                regime_secundario_stats.append({
                    'tipo': 'produtor_rural',
                    'nome': 'Produtores Rurais',
                    'quantidade': produtores_rurais,
                    'percentual': round(percentual, 2)
                })

            # --- Bloco 6: Ramo de Atividade (Classificação por CNAE) ---
            def categoria_por_cnae(cnae):
                if not cnae:
                    return "Desconhecido"
                try:
                    prefixo = int(str(cnae).replace("-", "").replace("/", "")[:2])
                    if prefixo in range(1, 10):
                        return "Agropecuária"
                    elif prefixo in range(10, 34):
                        return "Indústria"
                    elif prefixo == 35:
                        return "Energia"
                    elif prefixo in range(36, 40):
                        return "Saneamento e Resíduos"
                    elif prefixo in range(41, 44):
                        return "Construção"
                    elif prefixo in range(45, 48):
                        return "Comércio"
                    elif prefixo in range(49, 54):
                        return "Transporte e Logística"
                    elif prefixo in range(55, 57):
                        return "Hospedagem e Alimentação"
                    elif prefixo in range(58, 64):
                        return "Informação e Comunicação"
                    elif prefixo in range(65, 67):
                        return "Financeiro e Seguros"
                    elif prefixo in range(68, 75):
                        return "Serviços Profissionais"
                    elif prefixo in range(77, 84):
                        return "Administração Pública e Serviços Diversos"
                    elif prefixo in range(85, 89):
                        return "Educação e Saúde"
                    elif prefixo in range(90, 94):
                        return "Cultura, Esporte e Lazer"
                    elif prefixo in range(95, 100):
                        return "Serviços Domésticos"
                    else:
                        return "Outros"
                except:
                    return "Desconhecido"
            
            # Classificar empresas por CNAE
            ramo_atividade = []
            categorias_cnae = {}
            
            # Buscar todas as empresas com CNAE
            empresas_com_cnae = PessoaJuridica.objects.filter(
                cnae_codigo__isnull=False, 
                cnae_codigo__gt='',
                id__in=pj_ids_validos
            )
            
            for pj in empresas_com_cnae:
                categoria = categoria_por_cnae(pj.cnae_codigo)
                if categoria not in categorias_cnae:
                    categorias_cnae[categoria] = 0
                categorias_cnae[categoria] += 1
            
            # Converter para lista ordenada por quantidade
            total_empresas_com_cnae = sum(categorias_cnae.values())
            for categoria, quantidade in categorias_cnae.items():
                percentual = (quantidade / total_empresas_com_cnae * 100) if total_empresas_com_cnae > 0 else 0
                ramo_atividade.append({
                    'ramo': categoria.lower().replace(' ', '_').replace('ç', 'c').replace('ã', 'a'),
                    'nome': categoria,
                    'quantidade': quantidade,
                    'percentual': round(percentual, 2)
                })
            
            # Ordenar por quantidade (decrescente)
            ramo_atividade.sort(key=lambda x: x['quantidade'], reverse=True)

            # --- Bloco 7: Evolução (últimos 6 meses) ---
            meses = 6
            evolucao_data = []
            hoje = timezone.now().date()
            for i in range(meses):
                month_date = hoje - timedelta(days=30 * i)
                mes_inicio = month_date.replace(day=1)
                if month_date.month == 12:
                    mes_fim = month_date.replace(year=month_date.year + 1, month=1, day=1)
                else:
                    mes_fim = month_date.replace(month=month_date.month + 1, day=1)
                total_clientes = contratos_validos.filter(data_inicio__lte=mes_fim, ativo=True).values('object_id').distinct().count()
                novos_clientes = contratos_validos.filter(data_inicio__gte=mes_inicio, data_inicio__lt=mes_fim).values('object_id').distinct().count()
                clientes_inativos = contratos_validos.filter(data_termino__gte=mes_inicio, data_termino__lt=mes_fim, ativo=False).values('object_id').distinct().count()
                mes_abrev = {1: 'jan.', 2: 'fev.', 3: 'mar.', 4: 'abr.', 5: 'mai.', 6: 'jun.', 7: 'jul.', 8: 'ago.', 9: 'set.', 10: 'out.', 11: 'nov.', 12: 'dez.'}
                mes_formatado = f"{mes_abrev[month_date.month]} de {str(month_date.year)[2:]}"
                evolucao_data.append({
                    'mes': mes_formatado,
                    'mês': month_date.strftime('%Y-%m'),
                    'total_clientes': total_clientes,
                    'total_clientes_mes': total_clientes,
                    'novos_clientes': novos_clientes,
                    'novos_clientes_mes': novos_clientes,
                    'clientes_inativos': clientes_inativos,
                    'clientes_inativos_mes': clientes_inativos
                })
            evolucao_data.reverse()

            # --- Bloco 8: Aniversários de Parceria (próximos 12 meses) ---
            meses_aniversario = 12
            data_limite = hoje + timedelta(days=30 * meses_aniversario)
            aniversarios = []
            empresas_processadas = set()
            for contrato in contratos_validos.filter(ativo=True, data_inicio__isnull=False).order_by('-data_inicio'):
                cliente = contrato.cliente
                if not isinstance(cliente, PessoaJuridica) or cliente.id in empresas_processadas:
                    continue
                empresas_processadas.add(cliente.id)
                data_inicio = contrato.data_inicio
                anos_parceria = hoje.year - data_inicio.year
                if hoje.month < data_inicio.month or (hoje.month == data_inicio.month and hoje.day < data_inicio.day):
                    anos_parceria -= 1
                proximo_aniversario = data_inicio.replace(year=data_inicio.year + anos_parceria + 1)
                if hoje <= proximo_aniversario <= data_limite:
                    dias_faltando = (proximo_aniversario - hoje).days
                    meses_nomes = ['janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho', 'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro']
                    aniversarios.append({
                        'id': str(contrato.id),
                        'razao_social': cliente.razao_social,
                        'cnpj': cliente.cnpj,
                        'data_aniversario': proximo_aniversario.strftime('%Y-%m-%d'),
                        'dias_faltando': dias_faltando,
                        'mes_aniversario': meses_nomes[proximo_aniversario.month - 1]
                    })
            aniversarios.sort(key=lambda x: x['dias_faltando'])

            # --- Montar resposta final ---
            return Response({
                'summary': summary,
                'categorias': categorias,
                'regime_tributario': regime_tributario,
                'cnae_principal': cnae_principal_stats,
                'regime_secundario': regime_secundario_stats,
                'ramo_atividade': ramo_atividade,
                'evolucao': evolucao_data,
                'aniversarios_parceria': aniversarios
            })
        except Exception as e:
            logger.exception("[CARTEIRA/DASHBOARD] Erro ao montar dashboard consolidado")
            return Response({"error": f"Erro ao montar dashboard: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    """ViewSet para análise de carteira - Todos os endpoints com suporte Multi-Tenant"""
    permission_classes = [IsAuthenticated]
    pagination_class = ClientesPagination
    
    def _build_historical_map(self):
        """
        Constrói o mapa histórico usando a Regra de Ouro.
        Retorna apenas empresas/pessoas que possuem contratos válidos.
        """
        etl_command = BaseETLCommand()
        return etl_command.build_historical_contabilidade_map()

    def _get_contratos_queryset(self, request):
        """
        Helper para aplicar a Regra de Ouro Multi-Tenant
        - Superuser: Vê TODOS os contratos
        - Client: Vê apenas contratos da sua contabilidade
        """
        usuario = request.user
        
        if usuario.is_superuser:
            logger.info(f"[CARTEIRA] ✅ Superuser '{usuario.username}' - Acesso TOTAL")
            return Contrato.objects.all()
        else:
            if not hasattr(usuario, 'contabilidade') or not usuario.contabilidade:
                return None
            
            contabilidade = usuario.contabilidade
            logger.info(f"[CARTEIRA] ✅ User '{usuario.username}' - Contabilidade: {contabilidade.razao_social}")
            return Contrato.objects.filter(contabilidade=contabilidade)

    @action(detail=False, methods=['get'])
    def clientes(self, request):
        """
        GET /api/gestao/carteira/clientes/
        
        Lista completa de clientes (empresas únicas) com paginação, filtros e summary.
        
        IMPORTANTE: Conta empresas ÚNICAS, não contratos.
        Uma empresa pode ter múltiplos contratos (históricos ou em diferentes contabilidades),
        mas é contada apenas uma vez.
        
        Query params:
        - page: número da página
        - page_size: itens por página (padrão 50)
        - status: filtrar por 'ativo' ou 'inativo'
        - regime_fiscal: filtrar por regime (simples, presumido, real)
        - search: busca por razão social ou CNPJ
        
        Response:
        {
            "count": 1196,
            "next": "url_proxima_pagina",
            "previous": null,
            "results": [
                {
                    "id": "uuid",
                    "razao_social": "Empresa A",
                    "cnpj": "12345678000190",
                    "status": "ATIVO",
                    "regime_fiscal": "SIMPLES_NACIONAL",
                    "data_inicio": "2020-01-15",
                    "inadimplente": false
                }
            ],
            "summary": {
                "total_clientes": 1196,
                "clientes_ativos": 1150,
                "clientes_inativos": 46,
                "clientes_novos": 6,
                "clientes_sem_movimentacao": 0,
                "percentual_ativo": 96.15
            }
        }
        """
        try:
            # 1. Construir mapa histórico (REGRA DE OURO)
            logger.info("[CARTEIRA/CLIENTES] Construindo mapa histórico...")
            historical_map = self._build_historical_map()
            logger.info(f"[CARTEIRA/CLIENTES] Mapa construído: {len(historical_map)} clientes únicos")
            
            # 2. Obter contratos baseado no usuário
            todos_os_contratos = self._get_contratos_queryset(request)
            if todos_os_contratos is None:
                return Response(
                    {"error": "Usuário não possui contabilidade associada"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # 3. Filtrar apenas clientes que existem no mapa histórico (têm contratos válidos)
            # Buscar todos os CNPJs/CPFs dos clientes no mapa histórico
            cnpjs_validos = set(historical_map.keys())
            logger.info(f"[CARTEIRA/CLIENTES] {len(cnpjs_validos)} documentos válidos no mapa")
            
            # Filtrar PJs com CNPJ válido
            pj_ids_validos = PessoaJuridica.objects.filter(
                cnpj__in=cnpjs_validos
            ).values_list('id', flat=True)
            
            # Filtrar PFs com CPF válido
            pf_ids_validos = PessoaFisica.objects.filter(
                cpf__in=cnpjs_validos
            ).values_list('id', flat=True)
            
            # Aplicar filtro nos contratos
            pj_content_type = ContentType.objects.get_for_model(PessoaJuridica)
            pf_content_type = ContentType.objects.get_for_model(PessoaFisica)
            
            contratos_validos = todos_os_contratos.filter(
                Q(content_type=pj_content_type, object_id__in=pj_ids_validos) |
                Q(content_type=pf_content_type, object_id__in=pf_ids_validos)
            )
            
            logger.info(f"[CARTEIRA/CLIENTES] Contratos válidos filtrados: {contratos_validos.count()}")
            
            # 4. Calcular summary (contar CLIENTES ÚNICOS do mapa histórico)
            empresas_unicas = contratos_validos.values('object_id').distinct().count()
            
            # Empresas com pelo menos 1 contrato ativo
            clientes_ativos_qs = contratos_validos.filter(ativo=True)
            empresas_ativas = clientes_ativos_qs.values('object_id').distinct().count()
            
            # Empresas sem nenhum contrato ativo
            empresas_inativas = empresas_unicas - empresas_ativas
            
            # Empresas novas (com contrato iniciado nos últimos 30 dias)
            data_limite_novos = timezone.now().date() - timedelta(days=30)
            empresas_novas = clientes_ativos_qs.filter(
                data_inicio__gte=data_limite_novos
            ).values('object_id').distinct().count()
            
            percentual_ativo = (empresas_ativas / empresas_unicas * 100) if empresas_unicas > 0 else 0

            summary = {
                'total_clientes': empresas_unicas,
                'clientes_ativos': empresas_ativas,
                'clientes_inativos': empresas_inativas,
                'clientes_novos': empresas_novas,
                'clientes_sem_movimentacao': 0,  # TODO: implementar lógica
                'percentual_ativo': round(percentual_ativo, 2)
            }
            
            # 5. Aplicar filtros adicionais
            queryset = contratos_validos
            
            # Filtro por status
            status_filter = request.GET.get('status', None)
            if status_filter == 'ativo':
                queryset = queryset.filter(ativo=True)
            elif status_filter == 'inativo':
                queryset = queryset.filter(ativo=False)
            
            # Filtro por regime fiscal
            regime_filter = request.GET.get('regime_fiscal', None)
            if regime_filter:
                pj_content_type = ContentType.objects.get_for_model(PessoaJuridica)
                pj_ids = PessoaJuridica.objects.filter(regime_fiscal=regime_filter).values_list('id', flat=True)
                queryset = queryset.filter(content_type=pj_content_type, object_id__in=pj_ids)
            
            # Busca textual
            search = request.GET.get('search', None)
            if search:
                pj_content_type = ContentType.objects.get_for_model(PessoaJuridica)
                pj_ids = PessoaJuridica.objects.filter(
                    Q(razao_social__icontains=search) | Q(cnpj__icontains=search)
                ).values_list('id', flat=True)
                queryset = queryset.filter(content_type=pj_content_type, object_id__in=pj_ids)
            
            # 4. Montar lista de clientes ÚNICOS (eliminar duplicatas por object_id)
            results = []
            empresas_processadas = set()  # Controlar duplicatas
            
            for contrato in queryset.select_related('content_type').order_by('-ativo', '-data_inicio'):
                cliente = contrato.cliente
                
                # Apenas PJ e evitar duplicatas
                if isinstance(cliente, PessoaJuridica) and cliente.id not in empresas_processadas:
                    empresas_processadas.add(cliente.id)
                    
                    results.append({
                        'id': str(cliente.id),  # ID da empresa, não do contrato
                        'razao_social': cliente.razao_social,
                        'cnpj': cliente.cnpj,
                        'status': 'ATIVO' if contrato.ativo else 'INATIVO',
                        'regime_fiscal': cliente.regime_fiscal or 'NAO_INFORMADO',
                        'data_inicio': contrato.data_inicio.strftime('%Y-%m-%d') if contrato.data_inicio else None,
                        'inadimplente': contrato.status_cobranca == 'inadimplente' if hasattr(contrato, 'status_cobranca') else False
                    })
            
            # 5. Aplicar paginação
            paginator = ClientesPagination()
            paginator.page_size = int(request.GET.get('page_size', 50))
            paginated_results = paginator.paginate_queryset(results, request)
            
            # 6. Montar resposta com paginação
            return Response({
                'count': len(results),
                'next': paginator.get_next_link(),
                'previous': paginator.get_previous_link(),
                'results': paginated_results,
                'summary': summary
            })

        except Exception as e:
            logger.exception("[CARTEIRA/CLIENTES] Erro ao buscar clientes")
            return Response(
                {"error": f"Erro ao buscar clientes: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def resumo(self, request):
        """
        GET /api/gestao/carteira/resumo/
        
        Retorna apenas o summary (estatísticas gerais) sem a lista de clientes.
        Ideal para painéis que só precisam dos totalizadores.
        
        Response:
        {
            "summary": {
                "total_clientes": 2186,
                "clientes_ativos": 1550,
                "clientes_inativos": 636,
                "clientes_novos": 6,
                "clientes_sem_movimentacao": 0,
                "percentual_ativo": 70.91
            }
        }
        """
        try:
            # Construir mapa histórico (REGRA DE OURO)
            logger.info("[CARTEIRA/RESUMO] Construindo mapa histórico...")
            historical_map = self._build_historical_map()
            
            todos_os_contratos = self._get_contratos_queryset(request)
            if todos_os_contratos is None:
                return Response(
                    {"error": "Usuário não possui contabilidade associada"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Filtrar apenas clientes que existem no mapa histórico
            cnpjs_validos = set(historical_map.keys())
            
            pj_ids_validos = PessoaJuridica.objects.filter(cnpj__in=cnpjs_validos).values_list('id', flat=True)
            pf_ids_validos = PessoaFisica.objects.filter(cpf__in=cnpjs_validos).values_list('id', flat=True)
            
            pj_content_type = ContentType.objects.get_for_model(PessoaJuridica)
            pf_content_type = ContentType.objects.get_for_model(PessoaFisica)
            
            contratos_validos = todos_os_contratos.filter(
                Q(content_type=pj_content_type, object_id__in=pj_ids_validos) |
                Q(content_type=pf_content_type, object_id__in=pf_ids_validos)
            )
            
            # Contar CLIENTES ÚNICOS do mapa histórico
            empresas_unicas = contratos_validos.values('object_id').distinct().count()
            
            clientes_ativos_qs = contratos_validos.filter(ativo=True)
            empresas_ativas = clientes_ativos_qs.values('object_id').distinct().count()
            empresas_inativas = empresas_unicas - empresas_ativas
            
            data_limite_novos = timezone.now().date() - timedelta(days=30)
            empresas_novas = clientes_ativos_qs.filter(
                data_inicio__gte=data_limite_novos
            ).values('object_id').distinct().count()
            
            percentual_ativo = (empresas_ativas / empresas_unicas * 100) if empresas_unicas > 0 else 0

            return Response({
                'summary': {
                    'total_clientes': empresas_unicas,
                    'clientes_ativos': empresas_ativas,
                    'clientes_inativos': empresas_inativas,
                    'clientes_novos': empresas_novas,
                    'clientes_sem_movimentacao': 0,
                    'percentual_ativo': round(percentual_ativo, 2)
                }
            })

        except Exception as e:
            logger.exception("[CARTEIRA/RESUMO] Erro ao buscar resumo")
            return Response(
                {"error": f"Erro ao buscar resumo: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def categorias(self, request):
        """
        GET /api/gestao/carteira/categorias/
        
        Retorna categorias de clientes por STATUS (Ativos/Inativos).
        Diferente de regime-tributario que agrupa por regime fiscal.
        
        Response:
        [
            {
                "id": "uuid-1",
                "nome": "Ativos",
                "status": "ativo",
                "quantidade": 1550
            },
            {
                "id": "uuid-2",
                "nome": "Inativos",
                "status": "inativo",
                "quantidade": 636
            }
        ]
        """
        try:
            # Construir mapa histórico (REGRA DE OURO)
            logger.info("[CARTEIRA/CATEGORIAS] Construindo mapa histórico...")
            historical_map = self._build_historical_map()
            
            todos_os_contratos = self._get_contratos_queryset(request)
            if todos_os_contratos is None:
                return Response(
                    {"error": "Usuário não possui contabilidade associada"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Filtrar apenas clientes que existem no mapa histórico
            cnpjs_validos = set(historical_map.keys())
            
            pj_ids_validos = PessoaJuridica.objects.filter(cnpj__in=cnpjs_validos).values_list('id', flat=True)
            pf_ids_validos = PessoaFisica.objects.filter(cpf__in=cnpjs_validos).values_list('id', flat=True)
            
            pj_content_type = ContentType.objects.get_for_model(PessoaJuridica)
            pf_content_type = ContentType.objects.get_for_model(PessoaFisica)
            
            contratos_validos = todos_os_contratos.filter(
                Q(content_type=pj_content_type, object_id__in=pj_ids_validos) |
                Q(content_type=pf_content_type, object_id__in=pf_ids_validos)
            )
            
            # Contar empresas únicas por status
            ativos_count = contratos_validos.filter(ativo=True).values('object_id').distinct().count()
            inativos_count = contratos_validos.values('object_id').distinct().count() - ativos_count
            
            return Response([
                {
                    'id': 'cat-ativos',
                    'nome': 'Ativos',
                    'status': 'ativo',
                    'quantidade': ativos_count
                },
                {
                    'id': 'cat-inativos',
                    'nome': 'Inativos',
                    'status': 'inativo',
                    'quantidade': inativos_count
                }
            ])

        except Exception as e:
            logger.exception("[CARTEIRA/CATEGORIAS] Erro ao buscar categorias")
            return Response(
                {"error": f"Erro ao buscar categorias: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'], url_path='regime-tributario')
    def regime_tributario(self, request):
        """
        GET /api/gestao/carteira/regime-tributario/
        
        Distribuição de clientes por regime tributário com percentuais.
        
        Response:
        [
            {
                "regime": "simples",
                "nome": "Simples Nacional",
                "quantidade": 1100,
                "percentual": 50.32
            },
            {
                "regime": "presumido",
                "nome": "Lucro Presumido",
                "quantidade": 700,
                "percentual": 32.05
            },
            {
                "regime": "real",
                "nome": "Lucro Real",
                "quantidade": 386,
                "percentual": 17.66
            }
        ]
        """
        try:
            # Construir mapa histórico (REGRA DE OURO)
            logger.info("[CARTEIRA/REGIME-TRIBUTARIO] Construindo mapa histórico...")
            historical_map = self._build_historical_map()
            
            todos_os_contratos = self._get_contratos_queryset(request)
            if todos_os_contratos is None:
                return Response(
                    {"error": "Usuário não possui contabilidade associada"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Filtrar apenas clientes que existem no mapa histórico
            cnpjs_validos = set(historical_map.keys())
            
            pj_ids_validos = PessoaJuridica.objects.filter(cnpj__in=cnpjs_validos).values_list('id', flat=True)
            pf_ids_validos = PessoaFisica.objects.filter(cpf__in=cnpjs_validos).values_list('id', flat=True)
            
            # Apenas contratos de PJ válidos
            pj_content_type = ContentType.objects.get_for_model(PessoaJuridica)
            pf_content_type = ContentType.objects.get_for_model(PessoaFisica)
            
            contratos_validos = todos_os_contratos.filter(
                Q(content_type=pj_content_type, object_id__in=pj_ids_validos) |
                Q(content_type=pf_content_type, object_id__in=pf_ids_validos)
            )
            
            contratos_pj = contratos_validos.filter(content_type=pj_content_type)
            # Contar empresas únicas, não contratos
            total_pj = contratos_pj.values('object_id').distinct().count()
            
            if total_pj == 0:
                return Response([])
            
            # Contar por regime fiscal
            regimes_map = {
                'simples': 'Simples Nacional',
                'presumido': 'Lucro Presumido',
                'real': 'Lucro Real'
            }
            
            result = []
            for regime_key, regime_nome in regimes_map.items():
                # Buscar PJs com esse regime (apenas PJs válidas do mapa)
                pj_ids = PessoaJuridica.objects.filter(
                    regime_fiscal=regime_key,
                    id__in=pj_ids_validos
                ).values_list('id', flat=True)
                
                # Contar empresas únicas com esse regime
                quantidade = contratos_pj.filter(object_id__in=pj_ids).values('object_id').distinct().count()
                percentual = (quantidade / total_pj * 100) if total_pj > 0 else 0
                
                result.append({
                    'regime': regime_key,
                    'nome': regime_nome,
                    'quantidade': quantidade,
                    'percentual': round(percentual, 2)
                })
            
            return Response(result)

        except Exception as e:
            logger.exception("[CARTEIRA/REGIME-TRIBUTARIO] Erro ao buscar regime tributário")
            return Response(
                {"error": f"Erro ao buscar regime tributário: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'], url_path='ramo-atividade')
    def ramo_atividade(self, request):
        """
        GET /api/gestao/carteira/ramo-atividade/
        
        Distribuição de clientes por ramo de atividade com percentuais.
        
        Response:
        [
            {
                "ramo": "comercio",
                "nome": "Comércio",
                "quantidade": 850,
                "percentual": 38.89
            },
            {
                "ramo": "servicos",
                "nome": "Serviços",
                "quantidade": 700,
                "percentual": 32.02
            },
            {
                "ramo": "industria",
                "nome": "Indústria",
                "quantidade": 636,
                "percentual": 29.10
            }
        ]
        """
        try:
            # Construir mapa histórico (REGRA DE OURO)
            logger.info("[CARTEIRA/RAMO-ATIVIDADE] Construindo mapa histórico...")
            historical_map = self._build_historical_map()
            
            todos_os_contratos = self._get_contratos_queryset(request)
            if todos_os_contratos is None:
                return Response(
                    {"error": "Usuário não possui contabilidade associada"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Filtrar apenas clientes que existem no mapa histórico
            cnpjs_validos = set(historical_map.keys())
            
            pj_ids_validos = PessoaJuridica.objects.filter(cnpj__in=cnpjs_validos).values_list('id', flat=True)
            pf_ids_validos = PessoaFisica.objects.filter(cpf__in=cnpjs_validos).values_list('id', flat=True)
            
            # Apenas contratos de PJ válidos
            pj_content_type = ContentType.objects.get_for_model(PessoaJuridica)
            pf_content_type = ContentType.objects.get_for_model(PessoaFisica)
            
            contratos_validos = todos_os_contratos.filter(
                Q(content_type=pj_content_type, object_id__in=pj_ids_validos) |
                Q(content_type=pf_content_type, object_id__in=pf_ids_validos)
            )
            
            contratos_pj = contratos_validos.filter(content_type=pj_content_type)
            # Contar empresas únicas, não contratos
            total_pj = contratos_pj.values('object_id').distinct().count()
            
            if total_pj == 0:
                return Response([])
            
            # Contar por ramo de atividade
            ramos_map = {
                'comercio': 'Comércio',
                'servicos': 'Serviços',
                'industria': 'Indústria'
            }
            
            result = []
            for ramo_key, ramo_nome in ramos_map.items():
                # Buscar PJs com esse ramo
                pj_ids = PessoaJuridica.objects.filter(
                    ramo_atividade=ramo_key,
                    id__in=pj_ids_validos  # Apenas PJs válidas do mapa
                ).values_list('id', flat=True)
                
                # Contar empresas únicas com esse ramo
                quantidade = contratos_pj.filter(object_id__in=pj_ids).values('object_id').distinct().count()
                percentual = (quantidade / total_pj * 100) if total_pj > 0 else 0
                
                result.append({
                    'ramo': ramo_key,
                    'nome': ramo_nome,
                    'quantidade': quantidade,
                    'percentual': round(percentual, 2)
                })
            
            return Response(result)

        except Exception as e:
            logger.exception("[CARTEIRA/RAMO-ATIVIDADE] Erro ao buscar ramo de atividade")
            return Response(
                {"error": f"Erro ao buscar ramo de atividade: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def evolucao(self, request):
        """
        GET /api/gestao/carteira/evolucao/?meses=12
        
        Evolução mensal de clientes (total, novos, inativos) nos últimos X meses.
        
        Query params:
        - meses: quantidade de meses (padrão 6, máximo 24)
        
        Response:
        [
            {
                "mes": "jan. de 24",
                "mês": "2024-01",
                "total_clientes": 100,
                "total_clientes_mes": 100,
                "novos_clientes": 5,
                "novos_clientes_mes": 5,
                "clientes_inativos": 2,
                "clientes_inativos_mes": 2
            }
        ]
        """
        try:
            # Construir mapa histórico (REGRA DE OURO)
            logger.info("[CARTEIRA/EVOLUCAO] Construindo mapa histórico...")
            historical_map = self._build_historical_map()
            
            todos_os_contratos = self._get_contratos_queryset(request)
            if todos_os_contratos is None:
                return Response(
                    {"error": "Usuário não possui contabilidade associada"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Filtrar apenas clientes que existem no mapa histórico
            cnpjs_validos = set(historical_map.keys())
            
            pj_ids_validos = PessoaJuridica.objects.filter(cnpj__in=cnpjs_validos).values_list('id', flat=True)
            pf_ids_validos = PessoaFisica.objects.filter(cpf__in=cnpjs_validos).values_list('id', flat=True)
            
            pj_content_type = ContentType.objects.get_for_model(PessoaJuridica)
            pf_content_type = ContentType.objects.get_for_model(PessoaFisica)
            
            contratos_validos = todos_os_contratos.filter(
                Q(content_type=pj_content_type, object_id__in=pj_ids_validos) |
                Q(content_type=pf_content_type, object_id__in=pf_ids_validos)
            )
            
            # Parâmetro de quantos meses
            meses = min(int(request.GET.get('meses', 6)), 24)
            
            evolucao_data = []
            hoje = timezone.now().date()
            
            for i in range(meses):
                # Data do mês
                month_date = hoje - timedelta(days=30 * i)
                mes_inicio = month_date.replace(day=1)
                
                # Calcular próximo mês
                if month_date.month == 12:
                    mes_fim = month_date.replace(year=month_date.year + 1, month=1, day=1)
                else:
                    mes_fim = month_date.replace(month=month_date.month + 1, day=1)
                
                # Total de clientes únicos ativos até o final desse mês
                total_clientes = contratos_validos.filter(
                    data_inicio__lte=mes_fim,
                    ativo=True
                ).values('object_id').distinct().count()
                
                # Novos clientes únicos iniciados nesse mês
                novos_clientes = contratos_validos.filter(
                    data_inicio__gte=mes_inicio,
                    data_inicio__lt=mes_fim
                ).values('object_id').distinct().count()
                
                # Clientes únicos que ficaram inativos nesse mês
                clientes_inativos = contratos_validos.filter(
                    data_termino__gte=mes_inicio,
                    data_termino__lt=mes_fim,
                    ativo=False
                ).values('object_id').distinct().count()
                
                # Formatação do mês
                mes_abrev = {
                    1: 'jan.', 2: 'fev.', 3: 'mar.', 4: 'abr.',
                    5: 'mai.', 6: 'jun.', 7: 'jul.', 8: 'ago.',
                    9: 'set.', 10: 'out.', 11: 'nov.', 12: 'dez.'
                }
                mes_formatado = f"{mes_abrev[month_date.month]} de {str(month_date.year)[2:]}"
                
                evolucao_data.append({
                    'mes': mes_formatado,
                    'mês': month_date.strftime('%Y-%m'),
                    'total_clientes': total_clientes,
                    'total_clientes_mes': total_clientes,
                    'novos_clientes': novos_clientes,
                    'novos_clientes_mes': novos_clientes,
                    'clientes_inativos': clientes_inativos,
                    'clientes_inativos_mes': clientes_inativos
                })
            
            # Inverter para ordem cronológica crescente
            evolucao_data.reverse()
            
            return Response(evolucao_data)

        except Exception as e:
            logger.exception("[CARTEIRA/EVOLUCAO] Erro ao buscar evolução")
            return Response(
                {"error": f"Erro ao buscar evolução: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'], url_path='aniversarios-parceria')
    def aniversarios_parceria(self, request):
        """
        GET /api/gestao/carteira/aniversarios-parceria/?meses=12
        
        Clientes que completam aniversário de parceria nos próximos X meses.
        
        Query params:
        - meses: quantidade de meses a frente (padrão 12)
        
        Response:
        [
            {
                "id": "uuid",
                "razao_social": "Empresa A LTDA",
                "cnpj": "12345678000190",
                "data_aniversario": "2025-01-15",
                "dias_faltando": 86,
                "mes_aniversario": "janeiro"
            }
        ]
        """
        try:
            # Construir mapa histórico (REGRA DE OURO)
            logger.info("[CARTEIRA/ANIVERSARIOS-PARCERIA] Construindo mapa histórico...")
            historical_map = self._build_historical_map()
            
            todos_os_contratos = self._get_contratos_queryset(request)
            if todos_os_contratos is None:
                return Response(
                    {"error": "Usuário não possui contabilidade associada"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Filtrar apenas clientes que existem no mapa histórico
            cnpjs_validos = set(historical_map.keys())
            
            pj_ids_validos = PessoaJuridica.objects.filter(cnpj__in=cnpjs_validos).values_list('id', flat=True)
            pf_ids_validos = PessoaFisica.objects.filter(cpf__in=cnpjs_validos).values_list('id', flat=True)
            
            pj_content_type = ContentType.objects.get_for_model(PessoaJuridica)
            pf_content_type = ContentType.objects.get_for_model(PessoaFisica)
            
            contratos_validos = todos_os_contratos.filter(
                Q(content_type=pj_content_type, object_id__in=pj_ids_validos) |
                Q(content_type=pf_content_type, object_id__in=pf_ids_validos)
            )
            
            meses = int(request.GET.get('meses', 12))
            hoje = timezone.now().date()
            data_limite = hoje + timedelta(days=30 * meses)
            
            aniversarios = []
            empresas_processadas = set()  # Evitar duplicatas
            
            # Buscar contratos ativos válidos com data_inicio
            for contrato in contratos_validos.filter(ativo=True, data_inicio__isnull=False).order_by('-data_inicio'):
                cliente = contrato.cliente
                
                # Apenas PJ e evitar duplicatas
                if not isinstance(cliente, PessoaJuridica) or cliente.id in empresas_processadas:
                    continue
                
                empresas_processadas.add(cliente.id)
                data_inicio = contrato.data_inicio
                
                # Calcular próximo aniversário
                anos_parceria = hoje.year - data_inicio.year
                if hoje.month < data_inicio.month or (hoje.month == data_inicio.month and hoje.day < data_inicio.day):
                    anos_parceria -= 1
                
                proximo_aniversario = data_inicio.replace(year=data_inicio.year + anos_parceria + 1)
                
                # Se o aniversário está no período
                if hoje <= proximo_aniversario <= data_limite:
                    dias_faltando = (proximo_aniversario - hoje).days
                    
                    cliente = contrato.cliente
                    if isinstance(cliente, PessoaJuridica):
                        meses_nomes = [
                            'janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho',
                            'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro'
                        ]
                        
                        aniversarios.append({
                            'id': str(contrato.id),
                            'razao_social': cliente.razao_social,
                            'cnpj': cliente.cnpj,
                            'data_aniversario': proximo_aniversario.strftime('%Y-%m-%d'),
                            'dias_faltando': dias_faltando,
                            'mes_aniversario': meses_nomes[proximo_aniversario.month - 1]
                        })
            
            # Ordenar por data mais próxima
            aniversarios.sort(key=lambda x: x['dias_faltando'])
            
            return Response(aniversarios)

        except Exception as e:
            logger.exception("[CARTEIRA/ANIVERSARIOS-PARCERIA] Erro ao buscar aniversários")
            return Response(
                {"error": f"Erro ao buscar aniversários de parceria: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'], url_path='socios-aniversariantes')
    def socios_aniversariantes(self, request):
        """
        GET /api/gestao/carteira/socios-aniversariantes/?meses=12
        
        Sócios que fazem aniversário nos próximos X meses.
        
        Query params:
        - meses: quantidade de meses a frente (padrão 12)
        
        Response:
        [
            {
                "id": "uuid",
                "nome_socio": "João Silva",
                "empresa_razao_social": "Empresa A LTDA",
                "empresa_cnpj": "12345678000190",
                "data_nascimento": "1980-03-15",
                "dias_faltando": 45,
                "mes_aniversario": "março"
            }
        ]
        
        NOTA: Este endpoint requer um modelo de Sócio vinculado a PessoaJuridica.
              Se não existir, retorna lista vazia.
        """
        try:
            # TODO: Implementar quando houver modelo de Sócio
            # Por enquanto, retorna lista vazia
            logger.warning("[CARTEIRA/SOCIOS-ANIVERSARIANTES] Modelo de Sócio ainda não implementado")
            return Response([])

        except Exception as e:
            logger.exception("[CARTEIRA/SOCIOS-ANIVERSARIANTES] Erro ao buscar sócios aniversariantes")
            return Response(
                {"error": f"Erro ao buscar sócios aniversariantes: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
