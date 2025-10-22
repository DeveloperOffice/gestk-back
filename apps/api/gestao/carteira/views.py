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
            # 1. Aplicar Regra de Ouro baseada no tipo de usuário
            todos_os_contratos = self._get_contratos_queryset(request)
            if todos_os_contratos is None and not request.user.is_superuser:
                return Response({"error": "Usuário não possui contabilidade associada"}, status=status.HTTP_400_BAD_REQUEST)

            usuario = request.user
            pj_content_type = ContentType.objects.get_for_model(PessoaJuridica)
            pf_content_type = ContentType.objects.get_for_model(PessoaFisica)
            
            # Aplicar Regra de Ouro apenas para usuários não-superuser
            if usuario.is_superuser:
                # Superuser vê TODOS os contratos
                contratos_validos = todos_os_contratos
                pj_ids_validos = PessoaJuridica.objects.all().values_list('id', flat=True)
                pf_ids_validos = PessoaFisica.objects.all().values_list('id', flat=True)
                logger.info(f"[CARTEIRA/DASHBOARD] ✅ Superuser '{usuario.username}' - Acesso TOTAL: {contratos_validos.count()} contratos")
            else:
                # Usuário normal: aplicar Regra de Ouro
                historical_map = self._build_historical_map()
                cnpjs_validos = set(historical_map.keys())
                pj_ids_validos = PessoaJuridica.objects.filter(cnpj__in=cnpjs_validos).values_list('id', flat=True)
                pf_ids_validos = PessoaFisica.objects.filter(cpf__in=cnpjs_validos).values_list('id', flat=True)
                contratos_validos = todos_os_contratos.filter(
                    Q(content_type=pj_content_type, object_id__in=pj_ids_validos) |
                    Q(content_type=pf_content_type, object_id__in=pf_ids_validos)
                )
                logger.info(f"[CARTEIRA/DASHBOARD] ✅ Usuário '{usuario.username}' - Regra de Ouro aplicada: {len(cnpjs_validos)} empresas mapeadas")

            # --- Bloco 1: Summary ---
            summary = self._calcular_resumo(contratos_validos)

            # --- Bloco 2: Categorias ---
            ativos_count = contratos_validos.filter(ativo=True).values('object_id').distinct().count()
            inativos_count = contratos_validos.values('object_id').distinct().count() - ativos_count
            categorias = [
                {'id': 'cat-ativos', 'nome': 'Ativos', 'status': 'ativo', 'quantidade': ativos_count},
                {'id': 'cat-inativos', 'nome': 'Inativos', 'status': 'inativo', 'quantidade': inativos_count}
            ]

            # --- Bloco 3: Regime Tributário ---
            regime_tributario = self._calcular_distribuicao_regime(contratos_validos, pj_ids_validos, pj_content_type)

            # --- Bloco 4: CNAE Principal (Classificação por CNAE) ---
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
                    categoria = self._categoria_por_cnae(cnae_codigo)
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
            contratos_pj = contratos_validos.filter(content_type=pj_content_type)
            total_pj = contratos_pj.values('object_id').distinct().count()
            
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
            ramo_atividade = self._calcular_distribuicao_ramo(pj_ids_validos)

            # --- Bloco 7: Evolução (últimos 6 meses) ---
            evolucao_data = self._calcular_evolucao(contratos_validos, meses=6)

            # --- Bloco 8: Aniversários de Parceria (próximos 12 meses) ---
            aniversarios = self._calcular_aniversarios(contratos_validos)

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

    @action(detail=False, methods=['get'], url_path='clientes/dashboard')
    def clientes_dashboard(self, request):
        """
        GET /api/gestao/carteira/clientes/dashboard/
        
        Query params:
        - data_inicio (YYYY-MM-DD, opcional, default: 12 meses atrás)
        - data_fim (YYYY-MM-DD, opcional, default: hoje)
        - status (string, opcional: ativo, inativo, bloqueado, baixado)
        - search (string, opcional)
        - page (int, default=1)
        - page_size (int, default=50, max=100)
        """
        try:
            # REUTILIZAR toda a lógica do dashboard() existente
            # 1. Aplicar Regra de Ouro (copiar do dashboard)
            todos_os_contratos = self._get_contratos_queryset(request)
            if todos_os_contratos is None and not request.user.is_superuser:
                return Response({"error": "Usuário não possui contabilidade associada"}, status=status.HTTP_400_BAD_REQUEST)
            
            usuario = request.user
            pj_content_type = ContentType.objects.get_for_model(PessoaJuridica)
            pf_content_type = ContentType.objects.get_for_model(PessoaFisica)
            
            # Aplicar Regra de Ouro apenas para usuários não-superuser
            if usuario.is_superuser:
                # Superuser vê TODOS os contratos
                contratos_validos = todos_os_contratos
                pj_ids_validos = PessoaJuridica.objects.all().values_list('id', flat=True)
                pf_ids_validos = PessoaFisica.objects.all().values_list('id', flat=True)
                logger.info(f"[CARTEIRA/CLIENTES-DASHBOARD] ✅ Superuser '{usuario.username}' - Acesso TOTAL: {contratos_validos.count()} contratos")
            else:
                # Usuário normal: aplicar Regra de Ouro
                historical_map = self._build_historical_map()
                cnpjs_validos = set(historical_map.keys())
                pj_ids_validos = PessoaJuridica.objects.filter(cnpj__in=cnpjs_validos).values_list('id', flat=True)
                pf_ids_validos = PessoaFisica.objects.filter(cpf__in=cnpjs_validos).values_list('id', flat=True)
                contratos_validos = todos_os_contratos.filter(
                    Q(content_type=pj_content_type, object_id__in=pj_ids_validos) |
                    Q(content_type=pf_content_type, object_id__in=pf_ids_validos)
                )
                logger.info(f"[CARTEIRA/CLIENTES-DASHBOARD] ✅ Usuário '{usuario.username}' - Regra de Ouro aplicada: {len(cnpjs_validos)} empresas mapeadas")
            
            # 2. Aplicar NOVOS filtros (data_inicio, data_fim, status, search)
            contratos_filtrados = self._aplicar_filtros_clientes(contratos_validos, request.GET)
            
            # 3. Construir lista de clientes com status
            clientes_data = self._construir_lista_clientes(contratos_filtrados, pj_ids_validos, pf_ids_validos, request)
            
            # 4. Paginar
            paginator = ClientesPagination()
            paginated_clientes = paginator.paginate_queryset(clientes_data, request)
            
            # 5. REUTILIZAR cálculo de resumo (usar contratos_validos como no dashboard)
            resumo = self._calcular_resumo(contratos_validos)
            
            # 6. REUTILIZAR distribuições (usar contratos_validos como no dashboard)
            distribuicao_regime = self._calcular_distribuicao_regime(contratos_validos, pj_ids_validos, pj_content_type)
            distribuicao_ramo = self._calcular_distribuicao_ramo(pj_ids_validos)
            
            # 7. REUTILIZAR evolução (usar contratos_validos para mostrar evolução completa)
            evolucao = self._calcular_evolucao(contratos_validos, meses=12)
            
            # 8. REUTILIZAR aniversários (copiar do dashboard)
            aniversarios = self._calcular_aniversarios(contratos_filtrados)
            
            return Response({
                'resumo': resumo,
                'lista_clientes': paginated_clientes,
                'paginacao': {
                    'pagina_atual': paginator.page.number,
                    'total_paginas': paginator.page.paginator.num_pages,
                    'total_registros': len(clientes_data),
                    'page_size': paginator.page_size
                },
                'distribuicao_regime_tributario': distribuicao_regime,
                'distribuicao_ramo_atividade': distribuicao_ramo,
                'evolucao_carteira': evolucao,
                'aniversarios': aniversarios
            })
            
        except Exception as e:
            logger.exception("[CARTEIRA/CLIENTES-DASHBOARD] Erro ao montar dashboard de clientes")
            return Response({"error": f"Erro ao montar dashboard de clientes: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

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

    # ===== MÉTODOS HELPER REUTILIZÁVEIS =====
    
    def _categoria_por_cnae(self, cnae):
        """Classifica CNAE por categoria baseada nos primeiros 2 dígitos"""
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

    def _calcular_resumo(self, contratos_validos):
        """Calcula resumo estatístico dos clientes"""
        empresas_unicas = contratos_validos.values('object_id').distinct().count()
        clientes_ativos_qs = contratos_validos.filter(ativo=True)
        empresas_ativas = clientes_ativos_qs.values('object_id').distinct().count()
        empresas_inativas = empresas_unicas - empresas_ativas
        data_limite_novos = timezone.now().date() - timedelta(days=30)
        empresas_novas = clientes_ativos_qs.filter(data_inicio__gte=data_limite_novos).values('object_id').distinct().count()
        percentual_ativo = (empresas_ativas / empresas_unicas * 100) if empresas_unicas > 0 else 0
        
        # Calcular clientes bloqueados e baixados
        clientes_bloqueados = 0
        clientes_baixados = 0
        
        for contrato in contratos_validos.select_related('contabilidade', 'content_type'):
            cliente = contrato.cliente
            status = self._calcular_status_cliente(contrato, cliente)
            if status == 'BLOQUEADO':
                clientes_bloqueados += 1
            elif status == 'BAIXADO':
                clientes_baixados += 1
        
        return {
            'total_clientes': empresas_unicas,
            'clientes_ativos': empresas_ativas,
            'clientes_inativos': empresas_inativas,
            'clientes_novos': empresas_novas,
            'clientes_bloqueados': clientes_bloqueados,
            'clientes_baixados': clientes_baixados,
            'clientes_sem_movimentacao': 0,  # TODO: implementar lógica
            'percentual_ativo': round(percentual_ativo, 2)
        }

    def _calcular_distribuicao_regime(self, contratos_validos, pj_ids_validos, pj_content_type):
        """Calcula distribuição por regime tributário"""
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
        return regime_tributario

    def _calcular_distribuicao_ramo(self, pj_ids_validos):
        """Calcula distribuição por ramo de atividade baseado no CNAE"""
        ramo_atividade = []
        categorias_cnae = {}
        
        # Buscar todas as empresas com CNAE
        empresas_com_cnae = PessoaJuridica.objects.filter(
            cnae_codigo__isnull=False, 
            cnae_codigo__gt='',
            id__in=pj_ids_validos
        )
        
        for pj in empresas_com_cnae:
            categoria = self._categoria_por_cnae(pj.cnae_codigo)
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
        return ramo_atividade

    def _calcular_evolucao(self, contratos_validos, meses=6):
        """Calcula evolução da carteira nos últimos X meses"""
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
        return evolucao_data

    def _calcular_aniversarios(self, contratos_validos):
        """Calcula aniversários de parceria dos próximos 12 meses"""
        meses_aniversario = 12
        hoje = timezone.now().date()
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
        return aniversarios

    def _mapear_regime_tributario(self, codigo):
        """Mapeia código do regime para nome legível"""
        mapeamento = {
            '1': 'Simples Nacional',
            '2': 'Lucro Presumido',
            '3': 'Lucro Real',
            '4': 'MEI',
        }
        return mapeamento.get(codigo, 'N/D')

    def _calcular_status_cliente(self, contrato, pessoa):
        """Calcula status baseado em contrato e pessoa"""
        hoje = timezone.now().date()
        
        # BLOQUEADO
        if hasattr(contrato, 'status_cobranca') and contrato.status_cobranca in ['suspenso', 'inadimplente']:
            return 'BLOQUEADO'
        
        # BAIXADO
        if hasattr(pessoa, 'motivo_inatividade') and pessoa.motivo_inatividade:
            motivo_lower = pessoa.motivo_inatividade.lower()
            if 'baix' in motivo_lower or 'transfer' in motivo_lower:
                return 'BAIXADO'
        
        # ATIVO/INATIVO
        if contrato.ativo and (not contrato.data_termino or contrato.data_termino > hoje):
            return 'ATIVO'
        else:
            return 'INATIVO'

    def _aplicar_filtros_clientes(self, contratos, params):
        """Aplica filtros específicos do endpoint de clientes"""
        # Filtro de data (default: últimos 12 meses)
        data_inicio = params.get('data_inicio')
        data_fim = params.get('data_fim')
        if not data_inicio:
            data_inicio = (timezone.now().date() - timedelta(days=365)).isoformat()
        if not data_fim:
            data_fim = timezone.now().date().isoformat()
        
        contratos = contratos.filter(
            Q(data_inicio__gte=data_inicio) | Q(data_inicio__isnull=True),
            Q(data_inicio__lte=data_fim) | Q(data_inicio__isnull=True)
        )
        
        return contratos

    def _construir_lista_clientes(self, contratos, pj_ids_validos, pf_ids_validos, request):
        """Constrói lista de clientes com todos os campos"""
        clientes_list = []
        search = request.GET.get('search', '').strip()
        status_filter = request.GET.get('status', '').upper()
        
        for contrato in contratos.select_related('contabilidade', 'content_type'):
            cliente = contrato.cliente
            
            # Calcular status
            status = self._calcular_status_cliente(contrato, cliente)
            
            # Aplicar filtro de status
            if status_filter and status != status_filter:
                continue
            
            # Dados básicos
            if isinstance(cliente, PessoaJuridica):
                razao_social = cliente.razao_social
                nome_fantasia = cliente.nome_fantasia
                cnpj = cliente.cnpj
                regime_fiscal = self._mapear_regime_tributario(cliente.regime_tributario)
                ramo_atividade = self._categoria_por_cnae(cliente.cnae_codigo)
                responsavel = {
                    'nome': cliente.responsavel_legal,
                    'email': cliente.email_resp_legal,
                    'telefone': cliente.telefone,
                    'cpf': cliente.cpf_responsavel
                }
            else:  # PessoaFisica
                razao_social = cliente.nome_completo
                nome_fantasia = None
                cnpj = cliente.cpf
                regime_fiscal = None
                ramo_atividade = None
                responsavel = None
            
            # Aplicar filtro de search
            if search:
                if search.lower() not in razao_social.lower() and \
                   (not nome_fantasia or search.lower() not in nome_fantasia.lower()) and \
                   search not in cnpj:
                    continue
            
            clientes_list.append({
                'id': str(cliente.id),
                'razao_social': razao_social,
                'nome_fantasia': nome_fantasia,
                'cnpj': cnpj,
                'status': status,
                'regime_fiscal': regime_fiscal,
                'ramo_atividade': ramo_atividade,
                'data_inicio': contrato.data_inicio,
                'data_fim': contrato.data_termino,
                'valor_mensal': contrato.valor_honorario,
                'responsavel': responsavel
            })
        
        return clientes_list

    @action(detail=False, methods=['get'], url_path='usuarios/dashboard')
    def usuarios_dashboard(self, request):
        """
        GET /api/gestao/carteira/usuarios/dashboard/
        
        Query params:
        - data_inicio (YYYY-MM-DD, default: 12 meses atrás)
        - data_fim (YYYY-MM-DD, default: hoje)
        - search (string)
        - page, page_size
        """
        try:
            from apps.administracao.models import Usuario as UsuarioLegado
            from apps.administracao.models import EstatisticaUsuario
            
            # 1. Multi-Tenancy
            usuario = request.user
            
            if usuario.is_superuser:
                # Superuser vê todos
                usuarios_validos = UsuarioLegado.objects.all()
                estatisticas_queryset = EstatisticaUsuario.objects.all()
            else:
                if not hasattr(usuario, 'contabilidade') or not usuario.contabilidade:
                    return Response({"error": "Usuário não possui contabilidade associada"}, status=400)
                
                # Filtrar por contabilidade nas estatísticas
                estatisticas_queryset = EstatisticaUsuario.objects.filter(
                    contabilidade=usuario.contabilidade
                )
                # Pegar IDs únicos de usuários das estatísticas
                usuario_ids = estatisticas_queryset.values_list('usuario_id', flat=True).distinct()
                usuarios_validos = UsuarioLegado.objects.filter(id__in=usuario_ids)
            
            # 2. Aplicar filtros
            usuarios_filtrados = self._aplicar_filtros_usuarios_legado(usuarios_validos, request.GET)
            
            # 3. Construir lista
            usuarios_data = self._construir_lista_usuarios_legado(usuarios_filtrados, request)
            
            # 4. Paginar manualmente (simular paginação)
            page = int(request.GET.get('page', 1))
            page_size = int(request.GET.get('page_size', 50))
            start = (page - 1) * page_size
            end = start + page_size
            paginated_usuarios = usuarios_data[start:end]
            
            total_pages = (len(usuarios_data) + page_size - 1) // page_size
            
            # 5. Resumo
            resumo = self._calcular_resumo_usuarios_legado(usuarios_validos)
            
            # 6. Produtividade Mensal (dados reais)
            produtividade_mensal = self._calcular_produtividade_mensal_real(
                estatisticas_queryset, request.GET
            )
            
            # 7. Ranking de Produtividade (dados reais)
            ranking = self._calcular_ranking_produtividade_real(
                estatisticas_queryset, request.GET
            )
            
            # 8. Produtividade por Empresa (dados reais)
            produtividade_empresa = self._calcular_produtividade_por_empresa(
                estatisticas_queryset, request.GET
            )
            
            return Response({
                'resumo': resumo,
                'lista_usuarios': paginated_usuarios,
                'paginacao': {
                    'pagina_atual': page,
                    'total_paginas': total_pages,
                    'total_registros': len(usuarios_data),
                    'page_size': page_size
                },
                'produtividade_mensal': produtividade_mensal,
                'ranking_produtividade': ranking,
                'produtividade_por_empresa': produtividade_empresa
            })
            
        except Exception as e:
            logger.exception("[USUARIOS-DASHBOARD] Erro")
            return Response({"error": str(e)}, status=500)

    @action(detail=False, methods=['get'], url_path='escritorio/dashboard')
    def escritorio_dashboard(self, request):
        """
        GET /api/gestao/escritorio/dashboard/
        
        Query params:
        - data_inicio (YYYY-MM-DD, default: primeiro dia do ano)
        - data_fim (YYYY-MM-DD, default: hoje)
        - contabilidade_id (obrigatório para superuser)
        """
        try:
            from apps.fiscal.models import NotaFiscal
            from apps.funcionarios.models import VinculoEmpregaticio
            from apps.contabil.models import LancamentoContabil
            from apps.administracao.models import EstatisticaUsuario
            from apps.core.models import Contabilidade
            from django.utils import timezone
            from datetime import datetime, date
            
            # 1. Multi-Tenancy
            usuario = request.user
            
            if usuario.is_superuser:
                # Superuser: escolher contabilidade via query param
                contabilidade_id = request.GET.get('contabilidade_id')
                if contabilidade_id:
                    contabilidade = Contabilidade.objects.get(id=contabilidade_id)
                else:
                    return Response({"error": "Superuser deve especificar contabilidade_id"}, status=400)
            else:
                if not hasattr(usuario, 'contabilidade') or not usuario.contabilidade:
                    return Response({"error": "Usuário não possui contabilidade associada"}, status=400)
                contabilidade = usuario.contabilidade
            
            # 2. Período de análise
            data_fim = request.GET.get('data_fim')
            if not data_fim:
                data_fim = timezone.now().date()
            else:
                data_fim = datetime.strptime(data_fim, '%Y-%m-%d').date()
            
            data_inicio = request.GET.get('data_inicio')
            if not data_inicio:
                # Default: início do ano atual
                data_inicio = date(data_fim.year, 1, 1)
            else:
                data_inicio = datetime.strptime(data_inicio, '%Y-%m-%d').date()
            
            # 3. Calcular blocos
            resumo_financeiro = self._calcular_resumo_financeiro_escritorio(
                contabilidade, data_inicio, data_fim
            )
            
            faturamento = self._calcular_faturamento_escritorio(
                contabilidade, data_inicio, data_fim
            )
            
            custos = self._calcular_custos_escritorio(
                contabilidade, data_inicio, data_fim
            )
            
            indicadores = self._calcular_indicadores_operacionais_escritorio(
                contabilidade, data_inicio, data_fim
            )
            
            dre = self._calcular_dre_escritorio(
                contabilidade, data_inicio, data_fim
            )
            
            return Response({
                'periodo': {
                    'data_inicio': data_inicio.isoformat(),
                    'data_fim': data_fim.isoformat()
                },
                'contabilidade': {
                    'id': str(contabilidade.id),
                    'razao_social': contabilidade.razao_social,
                    'cnpj': contabilidade.cnpj
                },
                'resumo_financeiro': resumo_financeiro,
                'faturamento': faturamento,
                'custos_operacionais': custos,
                'indicadores_operacionais': indicadores,
                'dre': dre
            })
            
        except Exception as e:
            logger.exception("[ESCRITORIO-DASHBOARD] Erro")
            return Response({"error": str(e)}, status=500)

    def _calcular_resumo_financeiro_escritorio(self, contabilidade, data_inicio, data_fim):
        """Calcula resumo financeiro geral do escritório"""
        from django.db.models import Sum
        from decimal import Decimal
        from apps.fiscal.models import NotaFiscal
        from apps.funcionarios.models import VinculoEmpregaticio
        
        # FATURAMENTO: Apenas da PRÓPRIA CONTABILIDADE (não dos clientes)
        from apps.gestao_models.models import FaturamentoEmpresa
        from django.db import models
        from django.contrib.contenttypes.models import ContentType
        
        # Buscar faturamento da própria contabilidade
        contabilidade_content_type = ContentType.objects.get_for_model(contabilidade.__class__)
        
        faturamento_escritorio = FaturamentoEmpresa.objects.filter(
            contabilidade=contabilidade,
            content_type=contabilidade_content_type,
            object_id=contabilidade.id,
            ano__gte=data_inicio.year,
            ano__lte=data_fim.year
        ).filter(
            # Filtrar por mês dentro do período
            models.Q(ano=data_inicio.year, mes__gte=data_inicio.month) |
            models.Q(ano__gt=data_inicio.year, ano__lt=data_fim.year) |
            models.Q(ano=data_fim.year, mes__lte=data_fim.month)
        )
        
        faturamento_total = faturamento_escritorio.aggregate(
            total=Sum('total_saidas') + Sum('total_servicos')
        )['total'] or 0
        
        # Faturamento mensal médio
        meses = (data_fim.year - data_inicio.year) * 12 + (data_fim.month - data_inicio.month) + 1
        faturamento_mensal = faturamento_total / max(meses, 1)
        
        # Custos (folha de pagamento DO ESCRITÓRIO)
        # NOTA: Funcionários do escritório são aqueles cujo empregador é a própria contabilidade
        # Verificar se o content_type e object_id apontam para a contabilidade
        from django.contrib.contenttypes.models import ContentType
        
        # Buscar ContentType da Contabilidade
        contabilidade_content_type = ContentType.objects.get_for_model(contabilidade.__class__)
        
        funcionarios = VinculoEmpregaticio.objects.filter(
            contabilidade=contabilidade,
            ativo=True,
            content_type=contabilidade_content_type,
            object_id=contabilidade.id
        )
        custo_folha = funcionarios.aggregate(Sum('salario_base'))['salario_base__sum'] or 0
        custo_operacional_mensal = custo_folha
        custo_operacional_total = custo_folha * meses
        
        # Margens
        lucro_bruto = faturamento_total - custo_operacional_total
        margem_bruta = (lucro_bruto / faturamento_total * 100) if faturamento_total > 0 else 0
        
        # Impostos (estimativa 15% do faturamento)
        impostos = faturamento_total * Decimal('0.15')
        lucro_liquido = lucro_bruto - impostos
        margem_liquida = (lucro_liquido / faturamento_total * 100) if faturamento_total > 0 else 0
        
        return {
            'faturamento_total': float(faturamento_total),
            'faturamento_mensal': float(faturamento_mensal),
            'custo_operacional_total': float(custo_operacional_total),
            'custo_operacional_mensal': float(custo_operacional_mensal),
            'lucro_bruto': float(lucro_bruto),
            'margem_bruta_percentual': round(margem_bruta, 2),
            'lucro_liquido': float(lucro_liquido),
            'margem_liquida_percentual': round(margem_liquida, 2)
        }

    def _calcular_faturamento_escritorio(self, contabilidade, data_inicio, data_fim):
        """Calcula faturamento detalhado do escritório - APENAS da própria contabilidade"""
        from django.db.models import Sum, Count
        from apps.gestao_models.models import FaturamentoEmpresa
        from django.db import models
        from django.contrib.contenttypes.models import ContentType
        
        # FATURAMENTO: Apenas da PRÓPRIA CONTABILIDADE (não dos clientes)
        contabilidade_content_type = ContentType.objects.get_for_model(contabilidade.__class__)
        
        faturamento_escritorio = FaturamentoEmpresa.objects.filter(
            contabilidade=contabilidade,
            content_type=contabilidade_content_type,
            object_id=contabilidade.id,
            ano__gte=data_inicio.year,
            ano__lte=data_fim.year
        ).filter(
            # Filtrar por mês dentro do período
            models.Q(ano=data_inicio.year, mes__gte=data_inicio.month) |
            models.Q(ano__gt=data_inicio.year, ano__lt=data_fim.year) |
            models.Q(ano=data_fim.year, mes__lte=data_fim.month)
        )
        
        # Por tipo (Saídas vs Serviços)
        por_tipo = [
            {
                'tipo': 'SAIDAS',
                'valor': float(faturamento_escritorio.aggregate(total=Sum('total_saidas'))['total'] or 0),
                'quantidade': faturamento_escritorio.filter(total_saidas__gt=0).count()
            },
            {
                'tipo': 'SERVICOS', 
                'valor': float(faturamento_escritorio.aggregate(total=Sum('total_servicos'))['total'] or 0),
                'quantidade': faturamento_escritorio.filter(total_servicos__gt=0).count()
            }
        ]
        
        # Evolução mensal
        evolucao = []
        for ano in range(data_inicio.year, data_fim.year + 1):
            for mes in range(1, 13):
                if ano == data_inicio.year and mes < data_inicio.month:
                    continue
                if ano == data_fim.year and mes > data_fim.month:
                    continue
                
                faturamento_mes = faturamento_escritorio.filter(ano=ano, mes=mes).aggregate(
                    total=Sum('total_saidas') + Sum('total_servicos')
                )['total'] or 0
                
                if faturamento_mes > 0:
                    evolucao.append({
                        'mes': f"{ano}-{mes:02d}-01",
                        'valor': float(faturamento_mes),
                        'notas': faturamento_escritorio.filter(ano=ano, mes=mes).count()
                    })
        
        # Top clientes não se aplica - estamos mostrando apenas dados da própria contabilidade
        top_clientes = []
        
        return {
            'por_tipo_nota': por_tipo,
            'evolucao_mensal': evolucao,
            'top_clientes': top_clientes
        }

    def _calcular_custos_escritorio(self, contabilidade, data_inicio, data_fim):
        """Calcula custos operacionais do escritório"""
        from django.db.models import Sum, Count
        from apps.funcionarios.models import VinculoEmpregaticio
        from apps.contabil.models import LancamentoContabil
        
        # Folha de pagamento
        funcionarios = VinculoEmpregaticio.objects.filter(
            contabilidade=contabilidade,
            ativo=True
        )
        
        total_folha = funcionarios.aggregate(Sum('salario_base'))['salario_base__sum'] or 0
        total_funcionarios = funcionarios.count()
        custo_medio = total_folha / max(total_funcionarios, 1)
        
        # Lançamentos contábeis
        lancamentos = LancamentoContabil.objects.filter(
            contabilidade=contabilidade,
            data_lancamento__gte=data_inicio,
            data_lancamento__lte=data_fim
        )
        
        total_lancamentos = lancamentos.count()
        valor_lancamentos = lancamentos.aggregate(Sum('valor_total'))['valor_total__sum'] or 0
        
        return {
            'folha_pagamento': {
                'total_mensal': float(total_folha),
                'total_funcionarios': total_funcionarios,
                'custo_medio_funcionario': float(custo_medio)
            },
            'despesas_contabeis': {
                'total_lancamentos': total_lancamentos,
                'valor_total': float(valor_lancamentos)
            }
        }

    def _calcular_indicadores_operacionais_escritorio(self, contabilidade, data_inicio, data_fim):
        """Calcula indicadores operacionais do escritório"""
        from django.db.models import Sum
        from apps.pessoas.models import Contrato
        from apps.administracao.models import EstatisticaUsuario
        
        # Clientes e contratos ativos
        contratos = Contrato.objects.filter(
            contabilidade=contabilidade,
            ativo=True
        )
        
        clientes_ativos = contratos.values('object_id').distinct().count()
        contratos_ativos = contratos.count()
        
        # Ticket médio
        valor_total = contratos.aggregate(Sum('valor_honorario'))['valor_honorario__sum'] or 0
        ticket_medio = valor_total / max(clientes_ativos, 1)
        
        # Produtividade dos usuários
        estatisticas = EstatisticaUsuario.objects.filter(
            contabilidade=contabilidade,
            periodo_referencia__gte=data_inicio,
            periodo_referencia__lte=data_fim
        ).values('usuario__nome_usuario').annotate(
            lancamentos=Sum('total_lancamentos'),
            horas=Sum('tempo_total_minutos') / 60.0
        ).order_by('-lancamentos')[:10]
        
        return {
            'clientes_ativos': clientes_ativos,
            'contratos_ativos': contratos_ativos,
            'ticket_medio': float(ticket_medio),
            'produtividade_usuarios': [
                {
                    'usuario': item['usuario__nome_usuario'],
                    'lancamentos': item['lancamentos'],
                    'horas': float(item['horas'])
                }
                for item in estatisticas
            ]
        }

    def _calcular_dre_escritorio(self, contabilidade, data_inicio, data_fim):
        """Calcula DRE completo do escritório"""
        from decimal import Decimal
        
        resumo = self._calcular_resumo_financeiro_escritorio(contabilidade, data_inicio, data_fim)
        
        receita_bruta = Decimal(str(resumo['faturamento_total']))
        impostos = receita_bruta * Decimal('0.15')  # Estimativa
        receita_liquida = receita_bruta - impostos
        custos_variaveis = Decimal('0.00')  # Serviços contábeis não têm CMV
        lucro_bruto = receita_liquida - custos_variaveis
        despesas_operacionais = Decimal(str(resumo['custo_operacional_total']))
        lucro_operacional = lucro_bruto - despesas_operacionais
        lucro_liquido = lucro_operacional
        
        return {
            'receita_bruta': receita_bruta,
            'impostos': impostos,
            'receita_liquida': receita_liquida,
            'custos_variaveis': custos_variaveis,
            'lucro_bruto': lucro_bruto,
            'despesas_operacionais': despesas_operacionais,
            'lucro_operacional': lucro_operacional,
            'lucro_liquido': lucro_liquido
        }

    def _aplicar_filtros_usuarios_legado(self, usuarios, params):
        """Aplica filtros aos usuários legados"""
        data_inicio = params.get('data_inicio')
        data_fim = params.get('data_fim')
        
        if data_inicio:
            usuarios = usuarios.filter(data_criacao__gte=data_inicio)
        if data_fim:
            usuarios = usuarios.filter(data_criacao__lte=data_fim)
        
        return usuarios

    def _construir_lista_usuarios_legado(self, usuarios, request):
        """Constrói lista simplificada"""
        usuarios_list = []
        search = request.GET.get('search', '').strip()
        
        for user in usuarios:
            if search and search.lower() not in user.nome_usuario.lower():
                continue
            
            usuarios_list.append({
                'id': str(user.id),
                'nome': user.nome_usuario,
                'status': 'ATIVO' if user.ativo else 'INATIVO'
            })
        
        return usuarios_list

    def _calcular_resumo_usuarios_legado(self, usuarios_validos):
        """Resumo básico"""
        total = usuarios_validos.count()
        ativos = usuarios_validos.filter(ativo=True).count()
        
        return {
            'total_usuarios': total,
            'usuarios_ativos': ativos,
            'usuarios_inativos': total - ativos
        }

    def _calcular_produtividade_mensal_real(self, estatisticas_queryset, params):
        """Produtividade mensal com dados REAIS"""
        from django.db.models import Sum
        
        # Filtro de período (default: 12 meses)
        data_inicio = params.get('data_inicio')
        data_fim = params.get('data_fim')
        
        if not data_inicio:
            data_inicio = (timezone.now().date() - timedelta(days=365))
        if not data_fim:
            data_fim = timezone.now().date()
        
        # Agrupar por período_referencia
        produtividade = estatisticas_queryset.filter(
            periodo_referencia__gte=data_inicio,
            periodo_referencia__lte=data_fim
        ).values('periodo_referencia').annotate(
            tempo_total_horas=Sum('tempo_total_minutos') / 60.0,
            total_importacoes=Sum('total_importacoes'),
            total_lancamentos=Sum('total_lancamentos'),
            lancamentos_manuais=Sum('lancamentos_manuais'),
            lancamentos_automaticos=Sum('lancamentos_automaticos'),
            total_atividades=Sum('total_atividades')
        ).order_by('periodo_referencia')
        
        return [
            {
                'mes': item['periodo_referencia'].strftime('%Y-%m'),
                'tempo_total_horas': float(item['tempo_total_horas'] or 0),
                'total_importacoes': item['total_importacoes'] or 0,
                'total_lancamentos': item['total_lancamentos'] or 0,
                'lancamentos_manuais': item['lancamentos_manuais'] or 0,
                'lancamentos_automaticos': item['lancamentos_automaticos'] or 0,
                'total_atividades': item['total_atividades'] or 0
            }
            for item in produtividade
        ]

    def _calcular_ranking_produtividade_real(self, estatisticas_queryset, params):
        """Ranking com dados REAIS (top 10)"""
        from django.db.models import Sum, F, ExpressionWrapper, FloatField, Case, When
        
        # Período (default: último mês)
        data_inicio = params.get('data_inicio')
        data_fim = params.get('data_fim')
        
        if not data_inicio:
            data_inicio = (timezone.now().date() - timedelta(days=30))
        if not data_fim:
            data_fim = timezone.now().date()
        
        # Agrupar por usuário
        ranking = estatisticas_queryset.filter(
            periodo_referencia__gte=data_inicio,
            periodo_referencia__lte=data_fim
        ).values('usuario__id', 'usuario__nome_usuario').annotate(
            tempo_sistema_horas=Sum('tempo_total_minutos') / 60.0,
            total_lancamentos=Sum('total_lancamentos'),
            lancamentos_manuais=Sum('lancamentos_manuais'),
            total_importacoes=Sum('total_importacoes')
        ).annotate(
            # Eficiência: lançamentos automáticos / total (quanto maior, mais eficiente)
            # Evitar divisão por zero usando CASE WHEN
            eficiencia=ExpressionWrapper(
                Case(
                    When(total_lancamentos__gt=0, then=1.0 - (F('lancamentos_manuais') * 1.0 / F('total_lancamentos'))),
                    default=0.0,
                    output_field=FloatField()
                ),
                output_field=FloatField()
            )
        ).order_by('-total_lancamentos')[:10]
        
        return [
            {
                'usuario_id': str(item['usuario__id']),
                'nome': item['usuario__nome_usuario'],
                'tempo_sistema_horas': float(item['tempo_sistema_horas'] or 0),
                'total_lancamentos': item['total_lancamentos'] or 0,
                'lancamentos_manuais': item['lancamentos_manuais'] or 0,
                'total_importacoes': item['total_importacoes'] or 0,
                'eficiencia': float(item['eficiencia'] or 0)
            }
            for item in ranking
        ]

    def _calcular_produtividade_por_empresa(self, estatisticas_queryset, params):
        """Produtividade por empresa com dados REAIS"""
        from django.db.models import Sum
        
        # Período
        data_inicio = params.get('data_inicio')
        data_fim = params.get('data_fim')
        
        if not data_inicio:
            data_inicio = (timezone.now().date() - timedelta(days=30))
        if not data_fim:
            data_fim = timezone.now().date()
        
        # Agrupar por empresa (top 20)
        produtividade = estatisticas_queryset.filter(
            periodo_referencia__gte=data_inicio,
            periodo_referencia__lte=data_fim,
            empresa__isnull=False
        ).values(
            'empresa__cnpj',
            'empresa__razao_social'
        ).annotate(
            tempo_horas=Sum('tempo_total_minutos') / 60.0,
            total_lancamentos=Sum('total_lancamentos'),
            lancamentos_manuais=Sum('lancamentos_manuais'),
            lancamentos_automaticos=Sum('lancamentos_automaticos'),
            total_importacoes=Sum('total_importacoes'),
            total_atividades=Sum('total_atividades')
        ).order_by('-total_lancamentos')[:20]
        
        return [
            {
                'empresa_cnpj': item['empresa__cnpj'],
                'empresa_nome': item['empresa__razao_social'],
                'tempo_horas': float(item['tempo_horas'] or 0),
                'total_lancamentos': item['total_lancamentos'] or 0,
                'lancamentos_manuais': item['lancamentos_manuais'] or 0,
                'lancamentos_automaticos': item['lancamentos_automaticos'] or 0,
                'total_importacoes': item['total_importacoes'] or 0,
                'total_atividades': item['total_atividades'] or 0
            }
            for item in produtividade
        ]
