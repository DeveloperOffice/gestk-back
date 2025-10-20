# 📝 TEMPLATES DE CÓDIGO - Implementação Rápida

## 🎯 Objetivo

Este documento fornece templates prontos para acelerar a implementação dos endpoints seguindo as melhores práticas do Django Rest Framework.

---

## 📋 Template 1: ViewSet Completo

```python
"""
Views para [MÓDULO]
"""

from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Count, Sum, Q, Prefetch
from django.utils import timezone
from datetime import datetime, timedelta

from apps.api.shared.viewsets import BaseViewSet
from apps.api.shared.permissions import IsSuperUser, IsAdminUser
from apps.api.shared.pagination import StandardPagination
from apps.api.shared.filters import StandardFilterBackend

from .models import [MODEL]
from .serializers import (
    [MODEL]ListSerializer,
    [MODEL]DetailSerializer,
    [MODEL]CreateSerializer,
    [MODEL]UpdateSerializer,
)
from .filters import [MODEL]Filter
from .services import [MODEL]Service


class [MODEL]ViewSet(BaseViewSet):
    """
    ViewSet para gerenciamento de [MÓDULO]
    
    Permissões:
    - SUPERUSER: Acesso total
    - ADMIN: Acesso aos da própria contabilidade
    - USUARIO: Apenas leitura (se permitido)
    
    Filtros disponíveis:
    - status: ativo/inativo
    - data_inicio: YYYY-MM-DD
    - data_fim: YYYY-MM-DD
    - search: busca por nome/identificador
    """
    
    queryset = [MODEL].objects.all()
    serializer_class = [MODEL]ListSerializer
    permission_classes = [IsSuperUser]  # Ajustar conforme necessário
    pagination_class = StandardPagination
    filter_backends = [StandardFilterBackend]
    filterset_class = [MODEL]Filter
    search_fields = ['nome', 'identificador']
    ordering_fields = ['data_criacao', 'nome']
    ordering = ['-data_criacao']
    
    def get_serializer_class(self):
        """Retorna serializer apropriado para cada action"""
        if self.action == 'list':
            return [MODEL]ListSerializer
        elif self.action == 'retrieve':
            return [MODEL]DetailSerializer
        elif self.action == 'create':
            return [MODEL]CreateSerializer
        elif self.action in ['update', 'partial_update']:
            return [MODEL]UpdateSerializer
        return super().get_serializer_class()
    
    def get_queryset(self):
        """
        Filtra queryset baseado no tipo de usuário
        - SUPERUSER: Vê tudo
        - ADMIN: Vê apenas da própria contabilidade
        - USUARIO: Vê apenas se tem permissão
        """
        queryset = super().get_queryset()
        user = self.request.user
        
        if user.tipo_usuario == 'SUPERUSER':
            return queryset
        
        if user.tipo_usuario in ['ADMIN', 'USUARIO']:
            if user.contabilidade:
                return queryset.filter(contabilidade=user.contabilidade)
            return queryset.none()
        
        return queryset.none()
    
    def create(self, request, *args, **kwargs):
        """
        Criar novo registro
        POST /api/[modulo]/[recurso]/
        
        Request Body:
        {
            "campo1": "valor1",
            "campo2": "valor2"
        }
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Usar service para lógica de negócio complexa
        instance = [MODEL]Service.criar(
            dados=serializer.validated_data,
            usuario=request.user
        )
        
        response_serializer = [MODEL]DetailSerializer(instance)
        return Response(
            response_serializer.data,
            status=status.HTTP_201_CREATED
        )
    
    def update(self, request, *args, **kwargs):
        """
        Atualizar registro
        PUT /api/[modulo]/[recurso]/{id}/
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
        instance = [MODEL]Service.atualizar(
            instance=instance,
            dados=serializer.validated_data,
            usuario=request.user
        )
        
        response_serializer = [MODEL]DetailSerializer(instance)
        return Response(response_serializer.data)
    
    def destroy(self, request, *args, **kwargs):
        """
        Deletar registro (soft delete)
        DELETE /api/[modulo]/[recurso]/{id}/
        """
        instance = self.get_object()
        
        # Usar service para soft delete
        [MODEL]Service.deletar(instance, usuario=request.user)
        
        return Response(
            {'message': f'{[MODEL].__name__} deletado com sucesso'},
            status=status.HTTP_204_NO_CONTENT
        )
    
    @action(detail=True, methods=['get'])
    def estatisticas(self, request, pk=None):
        """
        Estatísticas do registro
        GET /api/[modulo]/[recurso]/{id}/estatisticas/
        
        Query Parameters:
        - data_inicio: YYYY-MM-DD
        - data_fim: YYYY-MM-DD
        """
        instance = self.get_object()
        
        data_inicio = request.query_params.get('data_inicio')
        data_fim = request.query_params.get('data_fim')
        
        estatisticas = [MODEL]Service.calcular_estatisticas(
            instance=instance,
            data_inicio=data_inicio,
            data_fim=data_fim
        )
        
        return Response(estatisticas)
    
    @action(detail=True, methods=['post'])
    def ativar(self, request, pk=None):
        """
        Ativar registro
        POST /api/[modulo]/[recurso]/{id}/ativar/
        """
        instance = self.get_object()
        
        [MODEL]Service.ativar(instance, usuario=request.user)
        
        return Response({
            'message': f'{[MODEL].__name__} ativado com sucesso'
        })
    
    @action(detail=True, methods=['post'])
    def desativar(self, request, pk=None):
        """
        Desativar registro
        POST /api/[modulo]/[recurso]/{id}/desativar/
        """
        instance = self.get_object()
        
        [MODEL]Service.desativar(instance, usuario=request.user)
        
        return Response({
            'message': f'{[MODEL].__name__} desativado com sucesso'
        })
    
    @action(detail=False, methods=['get'])
    def resumo(self, request):
        """
        Resumo geral
        GET /api/[modulo]/[recurso]/resumo/
        """
        queryset = self.filter_queryset(self.get_queryset())
        
        resumo = [MODEL]Service.calcular_resumo(queryset)
        
        return Response(resumo)
```

---

## 📋 Template 2: Serializers

```python
"""
Serializers para [MÓDULO]
"""

from rest_framework import serializers
from django.db import transaction

from .models import [MODEL]


class [MODEL]ListSerializer(serializers.ModelSerializer):
    """
    Serializer para listagem (campos mínimos)
    """
    
    # Campos adicionais computados
    total_relacionados = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = [MODEL]
        fields = [
            'id',
            'nome',
            'identificador',
            'status',
            'status_display',
            'data_criacao',
            'data_modificacao',
            'total_relacionados',
        ]
        read_only_fields = ['id', 'data_criacao', 'data_modificacao']
    
    def get_total_relacionados(self, obj):
        """Retorna total de registros relacionados"""
        return obj.relacionados.filter(ativo=True).count()


class [MODEL]DetailSerializer(serializers.ModelSerializer):
    """
    Serializer para detalhes (todos os campos)
    """
    
    # Relacionamentos
    contabilidade_nome = serializers.CharField(
        source='contabilidade.razao_social',
        read_only=True
    )
    criado_por_nome = serializers.CharField(
        source='criado_por.get_full_name',
        read_only=True
    )
    
    # Campos computados
    total_relacionados = serializers.SerializerMethodField()
    estatisticas = serializers.SerializerMethodField()
    
    class Meta:
        model = [MODEL]
        fields = '__all__'
        read_only_fields = [
            'id',
            'data_criacao',
            'data_modificacao',
            'criado_por',
            'modificado_por',
        ]
    
    def get_total_relacionados(self, obj):
        return obj.relacionados.count()
    
    def get_estatisticas(self, obj):
        """Retorna estatísticas do registro"""
        return {
            'total_ativo': obj.relacionados.filter(ativo=True).count(),
            'total_inativo': obj.relacionados.filter(ativo=False).count(),
        }


class [MODEL]CreateSerializer(serializers.ModelSerializer):
    """
    Serializer para criação
    """
    
    class Meta:
        model = [MODEL]
        fields = [
            'nome',
            'identificador',
            'campo1',
            'campo2',
            'contabilidade',
        ]
    
    def validate_identificador(self, value):
        """Validar identificador único"""
        if [MODEL].objects.filter(identificador=value).exists():
            raise serializers.ValidationError(
                'Já existe um registro com este identificador'
            )
        return value
    
    def validate(self, attrs):
        """Validações customizadas"""
        # Exemplo: validar datas
        if 'data_inicio' in attrs and 'data_fim' in attrs:
            if attrs['data_fim'] < attrs['data_inicio']:
                raise serializers.ValidationError({
                    'data_fim': 'Data fim deve ser maior que data início'
                })
        
        return attrs
    
    @transaction.atomic
    def create(self, validated_data):
        """
        Criar registro com transação
        """
        # Extrair dados relacionados se necessário
        relacionados_data = validated_data.pop('relacionados', [])
        
        # Criar registro principal
        instance = [MODEL].objects.create(**validated_data)
        
        # Criar relacionados
        for relacionado_data in relacionados_data:
            instance.relacionados.create(**relacionado_data)
        
        return instance


class [MODEL]UpdateSerializer(serializers.ModelSerializer):
    """
    Serializer para atualização
    """
    
    class Meta:
        model = [MODEL]
        fields = [
            'nome',
            'campo1',
            'campo2',
            'status',
        ]
    
    def validate(self, attrs):
        """Validações de atualização"""
        instance = self.instance
        
        # Exemplo: não permitir alterar status se tiver pendências
        if 'status' in attrs and instance.tem_pendencias():
            raise serializers.ValidationError({
                'status': 'Não é possível alterar status com pendências'
            })
        
        return attrs
    
    @transaction.atomic
    def update(self, instance, validated_data):
        """
        Atualizar com transação
        """
        # Atualizar campos
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        instance.save()
        return instance
```

---

## 📋 Template 3: Services (Lógica de Negócio)

```python
"""
Services para [MÓDULO]
Contém toda a lógica de negócio
"""

from django.db import transaction
from django.utils import timezone
from datetime import datetime, timedelta

from .models import [MODEL]


class [MODEL]Service:
    """
    Service para lógica de negócio de [MODEL]
    """
    
    @staticmethod
    @transaction.atomic
    def criar(dados, usuario):
        """
        Criar novo registro com lógica de negócio
        
        Args:
            dados: dict com dados validados
            usuario: usuário que está criando
            
        Returns:
            instance: Instância criada
        """
        # Adicionar informações de auditoria
        dados['criado_por'] = usuario
        dados['contabilidade'] = usuario.contabilidade
        
        # Criar instância
        instance = [MODEL].objects.create(**dados)
        
        # Executar ações pós-criação
        [MODEL]Service._processar_pos_criacao(instance)
        
        return instance
    
    @staticmethod
    @transaction.atomic
    def atualizar(instance, dados, usuario):
        """
        Atualizar registro com lógica de negócio
        
        Args:
            instance: instância a ser atualizada
            dados: dict com dados validados
            usuario: usuário que está atualizando
            
        Returns:
            instance: Instância atualizada
        """
        # Guardar estado anterior
        estado_anterior = {
            'status': instance.status,
            'campo_importante': instance.campo_importante,
        }
        
        # Atualizar campos
        for campo, valor in dados.items():
            setattr(instance, campo, valor)
        
        instance.modificado_por = usuario
        instance.save()
        
        # Executar ações baseadas em mudanças
        [MODEL]Service._processar_mudancas(
            instance,
            estado_anterior,
            usuario
        )
        
        return instance
    
    @staticmethod
    @transaction.atomic
    def deletar(instance, usuario):
        """
        Deletar registro (soft delete)
        
        Args:
            instance: instância a ser deletada
            usuario: usuário que está deletando
        """
        # Validar se pode deletar
        if instance.tem_dependencias():
            from rest_framework.exceptions import ValidationError
            raise ValidationError(
                'Não é possível deletar. Existem dependências.'
            )
        
        # Soft delete
        instance.ativo = False
        instance.data_exclusao = timezone.now()
        instance.excluido_por = usuario
        instance.save()
        
        # Executar ações pós-exclusão
        [MODEL]Service._processar_pos_exclusao(instance)
    
    @staticmethod
    def ativar(instance, usuario):
        """Ativar registro"""
        instance.ativo = True
        instance.data_ativacao = timezone.now()
        instance.ativado_por = usuario
        instance.save()
    
    @staticmethod
    def desativar(instance, usuario):
        """Desativar registro"""
        instance.ativo = False
        instance.data_desativacao = timezone.now()
        instance.desativado_por = usuario
        instance.save()
    
    @staticmethod
    def calcular_estatisticas(instance, data_inicio=None, data_fim=None):
        """
        Calcular estatísticas do registro
        
        Args:
            instance: instância
            data_inicio: data inicial (opcional)
            data_fim: data final (opcional)
            
        Returns:
            dict com estatísticas
        """
        # Definir período
        if not data_inicio:
            data_inicio = timezone.now().date() - timedelta(days=30)
        if not data_fim:
            data_fim = timezone.now().date()
        
        # Calcular estatísticas
        relacionados = instance.relacionados.filter(
            data__gte=data_inicio,
            data__lte=data_fim
        )
        
        return {
            'periodo': {
                'data_inicio': data_inicio,
                'data_fim': data_fim,
            },
            'total': relacionados.count(),
            'total_ativo': relacionados.filter(ativo=True).count(),
            'total_inativo': relacionados.filter(ativo=False).count(),
        }
    
    @staticmethod
    def calcular_resumo(queryset):
        """
        Calcular resumo geral
        
        Args:
            queryset: QuerySet filtrado
            
        Returns:
            dict com resumo
        """
        from django.db.models import Count, Sum, Avg
        
        return {
            'total': queryset.count(),
            'total_ativo': queryset.filter(ativo=True).count(),
            'total_inativo': queryset.filter(ativo=False).count(),
            'agregacoes': queryset.aggregate(
                total_valor=Sum('valor'),
                media_valor=Avg('valor'),
            ),
        }
    
    # Métodos privados (helper methods)
    
    @staticmethod
    def _processar_pos_criacao(instance):
        """Processar ações após criação"""
        # Exemplo: enviar notificação, criar registros relacionados, etc.
        pass
    
    @staticmethod
    def _processar_mudancas(instance, estado_anterior, usuario):
        """Processar mudanças importantes"""
        # Exemplo: se mudou status, fazer algo
        if estado_anterior['status'] != instance.status:
            # Lógica específica de mudança de status
            pass
    
    @staticmethod
    def _processar_pos_exclusao(instance):
        """Processar ações após exclusão"""
        # Exemplo: limpar relacionamentos, notificar, etc.
        pass
```

---

## 📋 Template 4: Filters

```python
"""
Filters para [MÓDULO]
"""

import django_filters
from django.db.models import Q

from .models import [MODEL]


class [MODEL]Filter(django_filters.FilterSet):
    """
    Filtros customizados para [MODEL]
    
    Uso:
    GET /api/[modulo]/[recurso]/?status=ativo&data_inicio=2024-01-01
    """
    
    # Filtros básicos
    status = django_filters.ChoiceFilter(
        field_name='status',
        choices=[MODEL].STATUS_CHOICES
    )
    
    ativo = django_filters.BooleanFilter(
        field_name='ativo'
    )
    
    # Filtros de data
    data_inicio = django_filters.DateFilter(
        field_name='data_criacao',
        lookup_expr='gte',
        label='Data Início (maior ou igual)'
    )
    
    data_fim = django_filters.DateFilter(
        field_name='data_criacao',
        lookup_expr='lte',
        label='Data Fim (menor ou igual)'
    )
    
    # Filtros de range
    valor_min = django_filters.NumberFilter(
        field_name='valor',
        lookup_expr='gte'
    )
    
    valor_max = django_filters.NumberFilter(
        field_name='valor',
        lookup_expr='lte'
    )
    
    # Busca textual
    busca = django_filters.CharFilter(
        method='filter_busca',
        label='Busca geral'
    )
    
    # Filtros de relacionamento
    contabilidade = django_filters.UUIDFilter(
        field_name='contabilidade__id'
    )
    
    contabilidade_nome = django_filters.CharFilter(
        field_name='contabilidade__razao_social',
        lookup_expr='icontains'
    )
    
    class Meta:
        model = [MODEL]
        fields = {
            'nome': ['exact', 'icontains', 'istartswith'],
            'identificador': ['exact', 'icontains'],
            'data_criacao': ['exact', 'gte', 'lte', 'year', 'month'],
        }
    
    def filter_busca(self, queryset, name, value):
        """
        Busca em múltiplos campos
        
        Busca por: nome, identificador, campos relacionados
        """
        return queryset.filter(
            Q(nome__icontains=value) |
            Q(identificador__icontains=value) |
            Q(contabilidade__razao_social__icontains=value)
        )
```

---

## 📋 Template 5: URLs

```python
"""
URLs para [MÓDULO]
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import [MODEL]ViewSet

# Router
router = DefaultRouter()
router.register(r'[recurso]', [MODEL]ViewSet, basename='[recurso]')

urlpatterns = [
    path('', include(router.urls)),
]
```

---

## 📋 Template 6: Tests

```python
"""
Tests para [MÓDULO]
"""

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status

from apps.core.models import Usuario, Contabilidade
from .models import [MODEL]


class [MODEL]ViewSetTest(TestCase):
    """
    Testes para [MODEL]ViewSet
    """
    
    def setUp(self):
        """Configurar dados de teste"""
        self.client = APIClient()
        
        # Criar contabilidade
        self.contabilidade = Contabilidade.objects.create(
            cnpj='12345678000190',
            razao_social='Test Contabilidade',
        )
        
        # Criar usuários
        self.superuser = Usuario.objects.create_user(
            username='superuser',
            password='testpass123',
            tipo_usuario='SUPERUSER',
            contabilidade=self.contabilidade
        )
        
        self.admin = Usuario.objects.create_user(
            username='admin',
            password='testpass123',
            tipo_usuario='ADMIN',
            contabilidade=self.contabilidade
        )
        
        self.usuario = Usuario.objects.create_user(
            username='usuario',
            password='testpass123',
            tipo_usuario='USUARIO',
            contabilidade=self.contabilidade
        )
        
        # Criar registros de teste
        self.[recurso] = [MODEL].objects.create(
            nome='Test [MODEL]',
            identificador='TEST001',
            contabilidade=self.contabilidade,
            criado_por=self.admin
        )
    
    def test_list_[recurso]_superuser(self):
        """SUPERUSER pode listar todos os registros"""
        self.client.force_authenticate(user=self.superuser)
        url = reverse('[recurso]-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data['results']), 1)
    
    def test_list_[recurso]_admin(self):
        """ADMIN pode listar registros da própria contabilidade"""
        self.client.force_authenticate(user=self.admin)
        url = reverse('[recurso]-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data['results']), 1)
    
    def test_list_[recurso]_unauthorized(self):
        """Usuário não autenticado não pode listar"""
        url = reverse('[recurso]-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_create_[recurso]_superuser(self):
        """SUPERUSER pode criar registro"""
        self.client.force_authenticate(user=self.superuser)
        url = reverse('[recurso]-list')
        data = {
            'nome': 'Novo [MODEL]',
            'identificador': 'NEW001',
            'contabilidade': str(self.contabilidade.id),
        }
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['nome'], data['nome'])
    
    def test_update_[recurso]_superuser(self):
        """SUPERUSER pode atualizar registro"""
        self.client.force_authenticate(user=self.superuser)
        url = reverse('[recurso]-detail', args=[self.[recurso].id])
        data = {
            'nome': 'Nome Atualizado',
        }
        response = self.client.patch(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['nome'], data['nome'])
    
    def test_delete_[recurso]_superuser(self):
        """SUPERUSER pode deletar registro"""
        self.client.force_authenticate(user=self.superuser)
        url = reverse('[recurso]-detail', args=[self.[recurso].id])
        response = self.client.delete(url)
        
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        
        # Verificar soft delete
        self.[recurso].refresh_from_db()
        self.assertFalse(self.[recurso].ativo)
    
    def test_estatisticas_[recurso](self):
        """Teste de estatísticas"""
        self.client.force_authenticate(user=self.superuser)
        url = reverse('[recurso]-estatisticas', args=[self.[recurso].id])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('total', response.data)
    
    def test_filtro_status(self):
        """Teste de filtro por status"""
        self.client.force_authenticate(user=self.superuser)
        url = reverse('[recurso]-list')
        response = self.client.get(url, {'status': 'ativo'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_busca(self):
        """Teste de busca"""
        self.client.force_authenticate(user=self.superuser)
        url = reverse('[recurso]-list')
        response = self.client.get(url, {'busca': 'Test'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data['results']), 1)
```

---

## 🚀 Como Usar os Templates

### **1. Substituir Placeholders**

```python
[MÓDULO] → contabilidades
[MODEL] → Contabilidade
[recurso] → contabilidades
```

### **2. Ajustar Permissões**

```python
# Para SUPERUSER apenas
permission_classes = [IsSuperUser]

# Para ADMIN e SUPERUSER
permission_classes = [IsAdminUser]

# Para todos autenticados
permission_classes = [IsAuthenticated]
```

### **3. Adicionar Validações Específicas**

```python
def validate_cnpj(self, value):
    """Validar CNPJ"""
    if not validar_cnpj(value):
        raise serializers.ValidationError('CNPJ inválido')
    return value
```

### **4. Adicionar Actions Customizadas**

```python
@action(detail=True, methods=['post'])
def acao_customizada(self, request, pk=None):
    instance = self.get_object()
    # Lógica...
    return Response({'message': 'Sucesso'})
```

---

## ✅ Checklist de Implementação

Para cada novo endpoint, seguir esta ordem:

1. [ ] Copiar template do ViewSet
2. [ ] Substituir placeholders
3. [ ] Ajustar permissões
4. [ ] Copiar template de Serializers
5. [ ] Adicionar validações específicas
6. [ ] Copiar template de Service
7. [ ] Implementar lógica de negócio
8. [ ] Copiar template de Filter
9. [ ] Adicionar filtros específicos
10. [ ] Copiar template de URLs
11. [ ] Registrar router
12. [ ] Copiar template de Tests
13. [ ] Executar testes
14. [ ] Documentar endpoint

---

**Próximo**: Começar implementação com Sprint 1!
