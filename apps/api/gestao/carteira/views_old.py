from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Count, Sum
from django.utils import timezone
from datetime import timedelta
from django.contrib.contenttypes.models import ContentType

from apps.core.models import Contabilidade, Usuario
from apps.pessoas.models import PessoaJuridica, PessoaFisica, Contrato
from apps.contabil.models import LancamentoContabil
from apps.fiscal.models import NotaFiscal
from ..serializers import (
    CarteiraClientesSerializer, CarteiraCategoriasSerializer, CarteiraEvolucaoSerializer
)

import logging
logger = logging.getLogger(__name__)

class CarteiraViewSet(viewsets.ViewSet):
    """ViewSet para análise de carteira"""
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'])
    def clientes(self, request):
        """
        Endpoint: /api/gestao/carteira/clientes/
        Lista clientes por status (Ativos, Inativos, Novos, Sem movimentação)
        
        Regra de Ouro Multi-Tenant:
        - Superuser: Vê TODOS os contratos do banco de dados
        - Client: Vê apenas contratos da sua contabilidade
        """
        try:
            # 1. Obter o usuário autenticado
            usuario = request.user
            logger.info(f"[CARTEIRA] Requisição recebida de usuário: {usuario.username if usuario.is_authenticated else 'ANÔNIMO'}")
            
            if not usuario.is_authenticated:
                logger.error("[CARTEIRA] Usuário não autenticado.")
                return Response({"error": "Authentication credentials were not provided."}, status=status.HTTP_401_UNAUTHORIZED)

            # 2. Verificar se é superuser
            if usuario.is_superuser:
                logger.info(f"[CARTEIRA] ✅ Superuser '{usuario.username}' acessando TODOS os contratos do banco de dados")
                todos_os_contratos = Contrato.objects.all()
            else:
                # Usuário comum precisa ter contabilidade associada
                if not hasattr(usuario, 'contabilidade') or not usuario.contabilidade:
                    logger.error(f"[CARTEIRA] ❌ Usuário {usuario.username} não possui contabilidade associada.")
                    return Response(
                        {"error": "Usuário não possui contabilidade associada"}, 
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                contabilidade = usuario.contabilidade
                logger.info(f"[CARTEIRA] ✅ Usuário COMUM '{usuario.username}' - Contabilidade: '{contabilidade.razao_social}' (ID: {contabilidade.id})")
                todos_os_contratos = Contrato.objects.filter(contabilidade=contabilidade)
            
            # 3. Contar contratos
            total_clientes = todos_os_contratos.count()
            logger.info(f"[CARTEIRA] 📊 Total de contratos encontrados: {total_clientes}")

            # 4. Calcular status dos clientes
            clientes_ativos_qs = todos_os_contratos.filter(ativo=True)
            clientes_ativos = clientes_ativos_qs.count()
            clientes_inativos = total_clientes - clientes_ativos
            
            # 5. Calcular clientes novos (ativos nos últimos 30 dias)
            data_limite_novos = timezone.now().date() - timedelta(days=30)
            clientes_novos = clientes_ativos_qs.filter(
                data_inicio__gte=data_limite_novos
            ).count()
            
            logger.info(f"[CARTEIRA] 📈 Cálculos: Total={total_clientes}, Ativos={clientes_ativos}, Inativos={clientes_inativos}, Novos={clientes_novos}")

            # 6. Simular clientes sem movimentação
            contratos_sem_movimentacao = 0
            
            # 7. Calcular percentual
            percentual_ativo = (clientes_ativos / total_clientes * 100) if total_clientes > 0 else 0

            # 8. Montar a resposta
            data = {
                'summary': {
                    'total_clientes': total_clientes,
                    'clientes_ativos': clientes_ativos,
                    'clientes_inativos': clientes_inativos,
                    'clientes_novos': clientes_novos,
                    'clientes_sem_movimentacao': contratos_sem_movimentacao,
                    'percentual_ativo': round(percentual_ativo, 2)
                },
                'results': [] 
            }

            logger.info(f"[CARTEIRA] ✅ Resposta montada com sucesso: {data['summary']}")
            return Response(data)

        except Exception as e:
            logger.exception("[CARTEIRA] Erro crítico ao buscar dados da carteira.")
            return Response(
                {"error": f"Erro ao buscar dados da carteira: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def categorias(self, request):
        """
        Endpoint para agregações de clientes por categoria (regime fiscal, ramo de atividade).
        
        Regra de Ouro Multi-Tenant:
        - Superuser: Vê categorias de TODOS os contratos do banco de dados
        - Client: Vê apenas categorias da sua contabilidade
        """
        try:
            usuario = request.user
            logger.info(f"[CARTEIRA/CATEGORIAS] Requisição recebida de usuário: {usuario.username}")
            
            if not usuario.is_authenticated:
                logger.error("[CARTEIRA/CATEGORIAS] Usuário não autenticado.")
                return Response({"error": "Authentication credentials were not provided."}, status=status.HTTP_401_UNAUTHORIZED)

            # Verificar se é superuser
            if usuario.is_superuser:
                logger.info(f"[CARTEIRA/CATEGORIAS] ✅ Superuser '{usuario.username}' acessando TODAS as categorias")
                contratos_ativos = Contrato.objects.filter(ativo=True)
            else:
                if not hasattr(usuario, 'contabilidade') or not usuario.contabilidade:
                    logger.error(f"[CARTEIRA/CATEGORIAS] ❌ Usuário {usuario.username} não possui contabilidade associada.")
                    return Response(
                        {"error": "Usuário não possui contabilidade associada"},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                contabilidade = usuario.contabilidade
                logger.info(f"[CARTEIRA/CATEGORIAS] ✅ Usuário COMUM '{usuario.username}' - Contabilidade: '{contabilidade.razao_social}'")
                contratos_ativos = Contrato.objects.filter(
                    contabilidade=contabilidade,
                    ativo=True
                )

            # Agrupar por regime fiscal
            regime_fiscal_data = []
            
            # Buscar pessoas jurídicas com contratos ativos
            pj_content_type = ContentType.objects.get_for_model(PessoaJuridica)
            contratos_pj = contratos_ativos.filter(content_type=pj_content_type)
            
            # Agrupar por regime tributário
            regimes = ['1', '2', '3', '4']  # Simples Nacional, Lucro Presumido, Lucro Real, MEI
            regime_labels = {
                '1': 'Simples Nacional',
                '2': 'Lucro Presumido', 
                '3': 'Lucro Real',
                '4': 'MEI - Microempreendedor Individual'
            }
            
            for regime in regimes:
                # Contar contratos por regime
                count = 0
                for contrato in contratos_pj:
                    cliente = contrato.cliente
                    if isinstance(cliente, PessoaJuridica) and cliente.regime_tributario == regime:
                        count += 1
                
                regime_fiscal_data.append({
                    'contabilidade': {
                        'id': str(contabilidade.id),
                        'cnpj': contabilidade.cnpj,
                        'razao_social': contabilidade.razao_social
                    },
                    'categoria': regime_labels.get(regime, 'Outros'),
                    'total_clientes': count
                })

            return Response(regime_fiscal_data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": f"Erro ao buscar categorias da carteira: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'])
    def evolucao(self, request):
        """
        Endpoint para gráficos de evolução mensal de clientes.
        
        Regra de Ouro Multi-Tenant:
        - Superuser: Vê evolução de TODOS os contratos do banco de dados
        - Client: Vê apenas evolução da sua contabilidade
        """
        try:
            usuario = request.user
            logger.info(f"[CARTEIRA/EVOLUCAO] Requisição recebida de usuário: {usuario.username}")
            
            if not usuario.is_authenticated:
                logger.error("[CARTEIRA/EVOLUCAO] Usuário não autenticado.")
                return Response({"error": "Authentication credentials were not provided."}, status=status.HTTP_401_UNAUTHORIZED)

            # Simular dados de evolução mensal
            evolucao_data = []
            for i in range(6):  # Últimos 6 meses
                month = timezone.now().date() - timedelta(days=30 * i)
                
                # Verificar se é superuser
                if usuario.is_superuser:
                    logger.info(f"[CARTEIRA/EVOLUCAO] ✅ Superuser '{usuario.username}' acessando evolução de TODOS os contratos")
                    total_clientes_mes = Contrato.objects.filter(
                        data_inicio__lte=month,
                        ativo=True
                    ).count()
                else:
                    if not hasattr(usuario, 'contabilidade') or not usuario.contabilidade:
                        logger.error(f"[CARTEIRA/EVOLUCAO] ❌ Usuário {usuario.username} não possui contabilidade associada.")
                        return Response(
                            {"error": "Usuário não possui contabilidade associada"},
                            status=status.HTTP_400_BAD_REQUEST
                        )
                    
                    contabilidade = usuario.contabilidade
                    logger.info(f"[CARTEIRA/EVOLUCAO] ✅ Usuário COMUM '{usuario.username}' - Contabilidade: '{contabilidade.razao_social}'")
                    total_clientes_mes = Contrato.objects.filter(
                        contabilidade=contabilidade,
                        data_inicio__lte=month,
                        ativo=True
                    ).count()
                evolucao_data.append({
                    'mes_ano': month.strftime('%Y-%m'),
                    'total_clientes': total_clientes_mes
                })
            
            # Inverter para ordem cronológica crescente
            evolucao_data.reverse()

            return Response(evolucao_data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": f"Erro ao buscar evolução da carteira: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
