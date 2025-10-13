"""
Views para gerenciamento de Contratos (Clientes) por ADMIN
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter, SearchFilter

from apps.pessoas.models import Contrato
from .contrato_serializers import (
    ContratoListSerializer,
    ContratoDetailSerializer,
    ContratoUpdateSerializer
)
from .contrato_services import ContratoService
from .contrato_filters import ContratoFilter
from .usuario_views import IsAdminUser

import logging

logger = logging.getLogger(__name__)


class ContratoViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gerenciamento de Contratos (Clientes) por ADMIN
    
    Endpoints:
    - list: Lista contratos da contabilidade do ADMIN
    - retrieve: Detalha um contrato
    - update/partial_update: Atualiza contrato
    - destroy: Deleta contrato (soft delete)
    - ativar: Ativa um contrato
    - desativar: Desativa um contrato
    - suspender: Suspende um contrato
    - renovar: Renova um contrato
    - atualizar_modulos: Atualiza módulos contratados
    - atualizar_limites: Atualiza limites do contrato
    - estatisticas: Estatísticas de contratos
    """
    
    queryset = Contrato.objects.all()
    permission_classes = [IsAuthenticated, IsAdminUser]
    filter_backends = [DjangoFilterBackend, OrderingFilter, SearchFilter]
    filterset_class = ContratoFilter
    search_fields = ['id_legado', 'plano_servico']
    ordering_fields = [
        'data_inicio', 'data_termino', 'valor_honorario',
        'ativo', 'status_cobranca'
    ]
    ordering = ['-data_inicio']
    
    def get_serializer_class(self):
        """Retorna o serializer adequado para cada ação"""
        if self.action == 'list':
            return ContratoListSerializer
        elif self.action in ['update', 'partial_update']:
            return ContratoUpdateSerializer
        else:
            return ContratoDetailSerializer
    
    def get_queryset(self):
        """
        Filtra contratos baseado no tipo do usuário autenticado
        - SUPERUSER: vê todos os contratos
        - ADMIN: vê contratos da sua contabilidade
        """
        queryset = Contrato.objects.select_related(
            'contabilidade',
            'content_type'
        ).all()
        
        user = self.request.user
        
        # SUPERUSER vê todos
        if user.is_superuser or user.tipo_usuario == 'superuser':
            return queryset
        
        # ADMIN vê apenas da sua contabilidade
        if user.tipo_usuario == 'admin' and user.contabilidade:
            return queryset.filter(contabilidade=user.contabilidade)
        
        # Outros usuários não têm acesso
        return queryset.none()
    
    def update(self, request, *args, **kwargs):
        """Atualiza um contrato"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        
        serializer = self.get_serializer(
            instance,
            data=request.data,
            partial=partial
        )
        serializer.is_valid(raise_exception=True)
        
        try:
            # Atualizar contrato usando o service
            contrato = ContratoService.atualizar_contrato(
                instance,
                serializer.validated_data,
                request.user
            )
            
            # Retornar resposta
            output_serializer = ContratoDetailSerializer(contrato)
            return Response(output_serializer.data)
            
        except ValueError as e:
            return Response(
                {'detail': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Erro ao atualizar contrato: {str(e)}")
            return Response(
                {'detail': 'Erro ao atualizar contrato'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def destroy(self, request, *args, **kwargs):
        """Deleta um contrato (soft delete)"""
        instance = self.get_object()
        
        try:
            ContratoService.deletar_contrato(instance, request.user)
            return Response(status=status.HTTP_204_NO_CONTENT)
            
        except Exception as e:
            logger.error(f"Erro ao deletar contrato: {str(e)}")
            return Response(
                {'detail': 'Erro ao deletar contrato'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def ativar(self, request, pk=None):
        """Ativa um contrato"""
        contrato = self.get_object()
        
        try:
            contrato = ContratoService.ativar_contrato(contrato, request.user)
            serializer = ContratoDetailSerializer(contrato)
            return Response(serializer.data)
            
        except Exception as e:
            logger.error(f"Erro ao ativar contrato: {str(e)}")
            return Response(
                {'detail': 'Erro ao ativar contrato'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def desativar(self, request, pk=None):
        """Desativa um contrato"""
        contrato = self.get_object()
        
        try:
            contrato = ContratoService.desativar_contrato(contrato, request.user)
            serializer = ContratoDetailSerializer(contrato)
            return Response(serializer.data)
            
        except Exception as e:
            logger.error(f"Erro ao desativar contrato: {str(e)}")
            return Response(
                {'detail': 'Erro ao desativar contrato'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def suspender(self, request, pk=None):
        """Suspende um contrato"""
        contrato = self.get_object()
        motivo = request.data.get('motivo', 'Não informado')
        
        try:
            contrato = ContratoService.suspender_contrato(
                contrato,
                motivo,
                request.user
            )
            serializer = ContratoDetailSerializer(contrato)
            return Response(serializer.data)
            
        except Exception as e:
            logger.error(f"Erro ao suspender contrato: {str(e)}")
            return Response(
                {'detail': 'Erro ao suspender contrato'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def renovar(self, request, pk=None):
        """Renova um contrato"""
        contrato = self.get_object()
        nova_data_termino = request.data.get('nova_data_termino')
        
        if not nova_data_termino:
            return Response(
                {'detail': 'Nova data de término é obrigatória'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            from datetime import datetime
            nova_data = datetime.strptime(nova_data_termino, '%Y-%m-%d').date()
            
            contrato = ContratoService.renovar_contrato(
                contrato,
                nova_data,
                request.user
            )
            serializer = ContratoDetailSerializer(contrato)
            return Response(serializer.data)
            
        except ValueError as e:
            return Response(
                {'detail': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Erro ao renovar contrato: {str(e)}")
            return Response(
                {'detail': 'Erro ao renovar contrato'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def atualizar_modulos(self, request, pk=None):
        """Atualiza os módulos contratados"""
        contrato = self.get_object()
        modulos = request.data.get('modulos', [])
        
        if not isinstance(modulos, list):
            return Response(
                {'detail': 'Módulos deve ser uma lista'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            contrato = ContratoService.atualizar_modulos(
                contrato,
                modulos,
                request.user
            )
            serializer = ContratoDetailSerializer(contrato)
            return Response(serializer.data)
            
        except ValueError as e:
            return Response(
                {'detail': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Erro ao atualizar módulos: {str(e)}")
            return Response(
                {'detail': 'Erro ao atualizar módulos'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def atualizar_limites(self, request, pk=None):
        """Atualiza os limites do contrato"""
        contrato = self.get_object()
        limite_usuarios = request.data.get('limite_usuarios')
        limite_empresas = request.data.get('limite_empresas')
        
        if not limite_usuarios or not limite_empresas:
            return Response(
                {'detail': 'Limite de usuários e empresas são obrigatórios'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            contrato = ContratoService.atualizar_limites(
                contrato,
                int(limite_usuarios),
                int(limite_empresas),
                request.user
            )
            serializer = ContratoDetailSerializer(contrato)
            return Response(serializer.data)
            
        except ValueError as e:
            return Response(
                {'detail': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Erro ao atualizar limites: {str(e)}")
            return Response(
                {'detail': 'Erro ao atualizar limites'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def estatisticas(self, request):
        """Retorna estatísticas de contratos"""
        try:
            # Filtrar por contabilidade se não for superuser
            contabilidade = None
            if request.user.tipo_usuario != 'superuser' and request.user.contabilidade:
                contabilidade = request.user.contabilidade
            
            estatisticas = ContratoService.calcular_estatisticas(contabilidade)
            return Response(estatisticas)
            
        except Exception as e:
            logger.error(f"Erro ao calcular estatísticas: {str(e)}")
            return Response(
                {'detail': 'Erro ao calcular estatísticas'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
