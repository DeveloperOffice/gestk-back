"""
Views para gerenciamento de Usuarios por ADMIN
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter, SearchFilter

from apps.core.models import Usuario
from apps.api.shared.permissions import IsSuperUserOrContabilidadeOwner
from .usuario_serializers import (
    UsuarioListSerializer,
    UsuarioDetailSerializer,
    UsuarioCreateSerializer,
    UsuarioUpdateSerializer
)
from .usuario_services import UsuarioService
from .usuario_filters import UsuarioFilter

import logging

logger = logging.getLogger(__name__)


class IsAdminUser(IsSuperUserOrContabilidadeOwner):
    """
    Permissão para usuários ADMIN (funcionários GESTK)
    Herda de IsSuperUserOrContabilidadeOwner e adiciona verificação de tipo admin
    """
    def has_permission(self, request, view):
        # Verificar autenticação básica
        if not super().has_permission(request, view):
            return False
        
        # Superusuários sempre têm acesso
        if request.user.is_superuser or request.user.tipo_usuario == 'superuser':
            return True
        
        # Verificar se é ADMIN
        if request.user.tipo_usuario == 'admin':
            # ADMIN pode ter permissão para administrar usuários
            return request.user.pode_administrar_usuarios
        
        return False


class UsuarioViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gerenciamento de Usuarios por ADMIN
    
    Endpoints:
    - list: Lista usuários da contabilidade do ADMIN
    - create: Cria novo usuário
    - retrieve: Detalha um usuário
    - update/partial_update: Atualiza usuário
    - destroy: Deleta usuário (soft delete)
    - ativar: Ativa um usuário
    - desativar: Desativa um usuário
    - resetar_senha: Reseta senha de um usuário
    - atualizar_modulos: Atualiza módulos acessíveis
    - estatisticas: Estatísticas de usuários
    """
    
    queryset = Usuario.objects.all()
    permission_classes = [IsAuthenticated, IsAdminUser]
    filter_backends = [DjangoFilterBackend, OrderingFilter, SearchFilter]
    filterset_class = UsuarioFilter
    search_fields = ['username', 'email', 'first_name', 'last_name', 'cpf']
    ordering_fields = [
        'username', 'email', 'date_joined', 'last_login',
        'tipo_usuario', 'ativo'
    ]
    ordering = ['-date_joined']
    
    def get_serializer_class(self):
        """Retorna o serializer adequado para cada ação"""
        if self.action == 'list':
            return UsuarioListSerializer
        elif self.action == 'create':
            return UsuarioCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return UsuarioUpdateSerializer
        else:
            return UsuarioDetailSerializer
    
    def get_queryset(self):
        """
        Filtra usuários baseado no tipo do usuário autenticado
        - SUPERUSER: vê todos os usuários
        - ADMIN: vê usuários da sua contabilidade
        """
        queryset = Usuario.objects.select_related(
            'contabilidade',
            'ultima_contabilidade'
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
    
    def create(self, request, *args, **kwargs):
        """Cria um novo usuário"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            # Criar usuário usando o service
            usuario = UsuarioService.criar_usuario(
                serializer.validated_data,
                request.user
            )
            
            # Retornar resposta
            output_serializer = UsuarioDetailSerializer(usuario)
            return Response(
                output_serializer.data,
                status=status.HTTP_201_CREATED
            )
            
        except ValueError as e:
            return Response(
                {'detail': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Erro ao criar usuário: {str(e)}")
            return Response(
                {'detail': 'Erro ao criar usuário'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def update(self, request, *args, **kwargs):
        """Atualiza um usuário"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        
        serializer = self.get_serializer(
            instance,
            data=request.data,
            partial=partial
        )
        serializer.is_valid(raise_exception=True)
        
        try:
            # Atualizar usuário usando o service
            usuario = UsuarioService.atualizar_usuario(
                instance,
                serializer.validated_data,
                request.user
            )
            
            # Retornar resposta
            output_serializer = UsuarioDetailSerializer(usuario)
            return Response(output_serializer.data)
            
        except ValueError as e:
            return Response(
                {'detail': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Erro ao atualizar usuário: {str(e)}")
            return Response(
                {'detail': 'Erro ao atualizar usuário'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def destroy(self, request, *args, **kwargs):
        """Deleta um usuário (soft delete)"""
        instance = self.get_object()
        
        # Não permitir deletar a si mesmo
        if instance.id == request.user.id:
            return Response(
                {'detail': 'Não é possível deletar seu próprio usuário'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Não permitir deletar superusuários
        if instance.tipo_usuario == 'superuser' and request.user.tipo_usuario != 'superuser':
            return Response(
                {'detail': 'Não é possível deletar superusuários'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            UsuarioService.deletar_usuario(instance, request.user)
            return Response(status=status.HTTP_204_NO_CONTENT)
            
        except Exception as e:
            logger.error(f"Erro ao deletar usuário: {str(e)}")
            return Response(
                {'detail': 'Erro ao deletar usuário'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def ativar(self, request, pk=None):
        """Ativa um usuário"""
        usuario = self.get_object()
        
        try:
            usuario = UsuarioService.ativar_usuario(usuario, request.user)
            serializer = UsuarioDetailSerializer(usuario)
            return Response(serializer.data)
            
        except Exception as e:
            logger.error(f"Erro ao ativar usuário: {str(e)}")
            return Response(
                {'detail': 'Erro ao ativar usuário'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def desativar(self, request, pk=None):
        """Desativa um usuário"""
        usuario = self.get_object()
        
        # Não permitir desativar a si mesmo
        if usuario.id == request.user.id:
            return Response(
                {'detail': 'Não é possível desativar seu próprio usuário'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            usuario = UsuarioService.desativar_usuario(usuario, request.user)
            serializer = UsuarioDetailSerializer(usuario)
            return Response(serializer.data)
            
        except Exception as e:
            logger.error(f"Erro ao desativar usuário: {str(e)}")
            return Response(
                {'detail': 'Erro ao desativar usuário'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def resetar_senha(self, request, pk=None):
        """Reseta a senha de um usuário"""
        usuario = self.get_object()
        nova_senha = request.data.get('nova_senha')
        
        if not nova_senha:
            return Response(
                {'detail': 'Nova senha é obrigatória'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            usuario = UsuarioService.resetar_senha(
                usuario,
                nova_senha,
                request.user
            )
            return Response({
                'detail': 'Senha resetada com sucesso',
                'token_version': usuario.token_version
            })
            
        except Exception as e:
            logger.error(f"Erro ao resetar senha: {str(e)}")
            return Response(
                {'detail': 'Erro ao resetar senha'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def atualizar_modulos(self, request, pk=None):
        """Atualiza os módulos acessíveis do usuário"""
        usuario = self.get_object()
        modulos = request.data.get('modulos', [])
        
        if not isinstance(modulos, list):
            return Response(
                {'detail': 'Módulos deve ser uma lista'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            usuario = UsuarioService.atualizar_modulos(
                usuario,
                modulos,
                request.user
            )
            serializer = UsuarioDetailSerializer(usuario)
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
    
    @action(detail=False, methods=['get'])
    def estatisticas(self, request):
        """Retorna estatísticas de usuários"""
        try:
            # Filtrar por contabilidade se não for superuser
            contabilidade = None
            if request.user.tipo_usuario != 'superuser' and request.user.contabilidade:
                contabilidade = request.user.contabilidade
            
            estatisticas = UsuarioService.calcular_estatisticas(contabilidade)
            return Response(estatisticas)
            
        except Exception as e:
            logger.error(f"Erro ao calcular estatísticas: {str(e)}")
            return Response(
                {'detail': 'Erro ao calcular estatísticas'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
