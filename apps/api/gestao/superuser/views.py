"""
Views para gestão de Contabilidades (SUPERUSER)
"""

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from django.db.models import Count, Sum, Q, Prefetch
from django.utils import timezone
from datetime import datetime, timedelta

from apps.api.shared.permissions import IsSuperUserOrContabilidadeOwner

from apps.core.models import Contabilidade
from .serializers import (
    ContabilidadeListSerializer,
    ContabilidadeDetailSerializer,
    ContabilidadeCreateSerializer,
    ContabilidadeUpdateSerializer,
)
from .filters import ContabilidadeFilter
from .services import ContabilidadeService


class StandardPagination(PageNumberPagination):
    """Paginação padrão"""
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class ContabilidadeViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gerenciamento de Contabilidades (SUPERUSER)
    
    Permissões:
    - SUPERUSER: Acesso total
    
    Endpoints:
    - GET /api/gestao/superuser/contabilidades/ - Listar todas
    - POST /api/gestao/superuser/contabilidades/ - Criar nova
    - GET /api/gestao/superuser/contabilidades/{id}/ - Detalhes
    - PUT/PATCH /api/gestao/superuser/contabilidades/{id}/ - Atualizar
    - DELETE /api/gestao/superuser/contabilidades/{id}/ - Deletar (soft)
    - GET /api/gestao/superuser/contabilidades/{id}/estatisticas/ - Estatísticas
    - POST /api/gestao/superuser/contabilidades/{id}/ativar/ - Ativar
    - POST /api/gestao/superuser/contabilidades/{id}/desativar/ - Desativar
    - POST /api/gestao/superuser/contabilidades/{id}/suspender/ - Suspender
    - POST /api/gestao/superuser/contabilidades/{id}/liberar/ - Liberar
    - GET /api/gestao/superuser/contabilidades/resumo/ - Resumo geral
    
    Filtros disponíveis:
    - ativo: true/false
    - suspensa_por_inadimplencia: true/false
    - data_inicio: YYYY-MM-DD
    - data_fim: YYYY-MM-DD
    - saldo_creditos_min: valor
    - saldo_creditos_max: valor
    - busca: texto (busca em razão social, nome fantasia, CNPJ, email)
    """
    
    queryset = Contabilidade.objects.all()
    serializer_class = ContabilidadeListSerializer
    permission_classes = [IsAuthenticated, IsSuperUserOrContabilidadeOwner]
    pagination_class = StandardPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = ContabilidadeFilter
    search_fields = ['razao_social', 'nome_fantasia', 'cnpj', 'email']
    ordering_fields = ['created_at', 'razao_social', 'saldo_creditos']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        """Retorna serializer apropriado para cada action"""
        if self.action == 'list':
            return ContabilidadeListSerializer
        elif self.action == 'retrieve':
            return ContabilidadeDetailSerializer
        elif self.action == 'create':
            return ContabilidadeCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return ContabilidadeUpdateSerializer
        return super().get_serializer_class()
    
    def get_queryset(self):
        """
        Filtra queryset baseado no tipo de usuário
        - SUPERUSER: Vê todas as contabilidades
        - Outros: Erro de permissão
        """
        queryset = super().get_queryset()
        user = self.request.user
        
        # Apenas superusuários têm acesso
        if user.tipo_usuario == 'superuser' or user.is_superuser:
            return queryset
        
        # Outros usuários não têm acesso a este endpoint
        return queryset.none()
    
    def create(self, request, *args, **kwargs):
        """
        Criar nova contabilidade
        POST /api/gestao/superuser/contabilidades/
        
        Request Body:
        {
            "razao_social": "Contabilidade ABC Ltda",
            "nome_fantasia": "ABC Contábil",
            "cnpj": "12345678000190",
            "email": "contato@abc.com.br",
            "telefone": "11999999999",
            "endereco": "Rua ABC, 123",
            "responsavel_financeiro_nome": "João Silva",
            "responsavel_financeiro_email": "financeiro@abc.com.br",
            "responsavel_financeiro_telefone": "11888888888"
        }
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Usar service para lógica de negócio
        contabilidade = ContabilidadeService.criar(
            dados=serializer.validated_data,
            usuario=request.user
        )
        
        response_serializer = ContabilidadeDetailSerializer(contabilidade)
        return Response(
            response_serializer.data,
            status=status.HTTP_201_CREATED
        )
    
    def update(self, request, *args, **kwargs):
        """
        Atualizar contabilidade
        PUT /api/gestao/superuser/contabilidades/{id}/
        PATCH /api/gestao/superuser/contabilidades/{id}/
        """
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(
            instance,
            data=request.data,
            partial=partial
        )
        serializer.is_valid(raise_exception=True)
        
        # Usar service para lógica de negócio
        contabilidade = ContabilidadeService.atualizar(
            instance=instance,
            dados=serializer.validated_data,
            usuario=request.user
        )
        
        response_serializer = ContabilidadeDetailSerializer(contabilidade)
        return Response(response_serializer.data)
    
    def destroy(self, request, *args, **kwargs):
        """
        Deletar contabilidade (soft delete)
        DELETE /api/gestao/superuser/contabilidades/{id}/
        """
        instance = self.get_object()
        
        # Usar service para soft delete
        ContabilidadeService.deletar(instance, usuario=request.user)
        
        return Response(
            {'message': 'Contabilidade desativada com sucesso'},
            status=status.HTTP_204_NO_CONTENT
        )
    
    @action(detail=True, methods=['get'])
    def estatisticas(self, request, pk=None):
        """
        Estatísticas da contabilidade
        GET /api/gestao/superuser/contabilidades/{id}/estatisticas/
        
        Query Parameters:
        - data_inicio: YYYY-MM-DD (padrão: 30 dias atrás)
        - data_fim: YYYY-MM-DD (padrão: hoje)
        
        Response:
        {
            "periodo": {
                "data_inicio": "2024-01-01",
                "data_fim": "2024-01-31"
            },
            "usuarios": {
                "total": 10,
                "ativos": 8,
                "inativos": 2,
                "por_tipo": {...}
            },
            "contratos": {...},
            "financeiro": {...}
        }
        """
        instance = self.get_object()
        
        data_inicio = request.query_params.get('data_inicio')
        data_fim = request.query_params.get('data_fim')
        
        # Converter strings para date se fornecido
        if data_inicio:
            data_inicio = datetime.strptime(data_inicio, '%Y-%m-%d').date()
        if data_fim:
            data_fim = datetime.strptime(data_fim, '%Y-%m-%d').date()
        
        estatisticas = ContabilidadeService.calcular_estatisticas(
            instance=instance,
            data_inicio=data_inicio,
            data_fim=data_fim
        )
        
        return Response(estatisticas)
    
    @action(detail=True, methods=['post'])
    def ativar(self, request, pk=None):
        """
        Ativar contabilidade
        POST /api/gestao/superuser/contabilidades/{id}/ativar/
        """
        instance = self.get_object()
        
        ContabilidadeService.ativar(instance, usuario=request.user)
        
        return Response({
            'message': 'Contabilidade ativada com sucesso',
            'contabilidade': ContabilidadeDetailSerializer(instance).data
        })
    
    @action(detail=True, methods=['post'])
    def desativar(self, request, pk=None):
        """
        Desativar contabilidade
        POST /api/gestao/superuser/contabilidades/{id}/desativar/
        """
        instance = self.get_object()
        
        ContabilidadeService.desativar(instance, usuario=request.user)
        
        return Response({
            'message': 'Contabilidade desativada com sucesso',
            'contabilidade': ContabilidadeDetailSerializer(instance).data
        })
    
    @action(detail=True, methods=['post'])
    def suspender(self, request, pk=None):
        """
        Suspender contabilidade por inadimplência
        POST /api/gestao/superuser/contabilidades/{id}/suspender/
        """
        instance = self.get_object()
        
        ContabilidadeService.suspender_por_inadimplencia(
            instance, 
            usuario=request.user
        )
        
        return Response({
            'message': 'Contabilidade suspensa por inadimplência',
            'contabilidade': ContabilidadeDetailSerializer(instance).data
        })
    
    @action(detail=True, methods=['post'])
    def liberar(self, request, pk=None):
        """
        Liberar contabilidade da inadimplência
        POST /api/gestao/superuser/contabilidades/{id}/liberar/
        """
        instance = self.get_object()
        
        ContabilidadeService.liberar_inadimplencia(
            instance, 
            usuario=request.user
        )
        
        return Response({
            'message': 'Contabilidade liberada da inadimplência',
            'contabilidade': ContabilidadeDetailSerializer(instance).data
        })
    
    @action(detail=False, methods=['get'])
    def resumo(self, request):
        """
        Resumo geral de todas as contabilidades
        GET /api/gestao/superuser/contabilidades/resumo/
        
        Response:
        {
            "total": 50,
            "ativas": 45,
            "inativas": 5,
            "suspensas_inadimplencia": 3,
            "percentual_ativas": 90.0,
            "saldo_creditos_total": 15000.00
        }
        """
        queryset = self.filter_queryset(self.get_queryset())
        
        resumo = ContabilidadeService.calcular_resumo(queryset)
        
        return Response(resumo)
