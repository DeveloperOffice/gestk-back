# Guia de Desenvolvimento - API de Administração

## 📋 Visão Geral

Este guia fornece instruções detalhadas para desenvolvedores que trabalham com a API de Administração do GESTK. Inclui padrões de código, convenções, exemplos práticos e melhores práticas.

## 🏗️ Estrutura do Projeto

### Organização de Arquivos
```
apps/
├── core/                           # Modelos base e multi-tenancy
│   ├── models.py                   # Contabilidade, Usuario, UsuarioAcesso
│   ├── admin.py                    # Interface administrativa
│   └── migrations/                 # Migrations do core
├── administracao/                  # Gestão de contratos e acessos
│   ├── models.py                   # ContratoGestk
│   ├── admin.py                    # Interface administrativa
│   └── migrations/                 # Migrations de administração
├── billing/                        # Sistema de faturamento
│   ├── models.py                   # Plano, Assinatura, Fatura, Pagamento
│   ├── admin.py                    # Interface administrativa
│   └── migrations/                 # Migrations de billing
└── api/
    ├── shared/                     # Componentes compartilhados
    │   ├── viewsets.py             # BaseViewSet, ReadOnlyViewSet
    │   ├── permissions.py          # Sistema de permissões
    │   ├── middleware.py           # Middleware multi-tenant
    │   └── serializers.py          # Serializers base
    ├── administracao/              # API de administração
    │   ├── views.py                # ViewSets de administração
    │   ├── serializers.py          # Serializers específicos
    │   ├── filters.py              # Filtros de busca
    │   ├── urls.py                 # URLs da API
    │   └── tests.py                # Testes da API
    └── billing/                    # API de billing
        ├── views.py                # ViewSets de billing
        ├── serializers.py          # Serializers específicos
        ├── filters.py              # Filtros de busca
        ├── urls.py                 # URLs da API
        └── tests.py                # Testes da API
```

## 🔧 Padrões de Desenvolvimento

### 1. Modelos (Models)

#### Estrutura Padrão
```python
class MeuModelo(models.Model):
    """
    Descrição clara do modelo
    """
    # Campos obrigatórios
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    contabilidade = models.ForeignKey(
        Contabilidade,
        on_delete=models.CASCADE,
        related_name='meus_modelos',
        help_text="Contabilidade proprietária"
    )
    
    # Campos de dados
    nome = models.CharField(
        _('Nome'),
        max_length=100,
        help_text="Nome do item"
    )
    
    # Campos de controle
    ativo = models.BooleanField(
        _('Ativo'),
        default=True,
        db_index=True,
        help_text="Se o item está ativo"
    )
    
    # Campos de auditoria
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        'core.Usuario',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='meus_modelos_criados'
    )
    
    # Histórico
    history = HistoricalRecords()
    
    class Meta:
        verbose_name = _('Meu Modelo')
        verbose_name_plural = _('Meus Modelos')
        db_table = 'app_meus_modelos'
        indexes = [
            models.Index(fields=['contabilidade', 'ativo']),
            models.Index(fields=['nome']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.nome} - {self.contabilidade.razao_social}"
    
    @property
    def esta_ativo(self):
        """Verifica se o item está ativo"""
        return self.ativo
    
    def ativar(self):
        """Ativa o item"""
        self.ativo = True
        self.save()
    
    def desativar(self):
        """Desativa o item"""
        self.ativo = False
        self.save()
```

#### Convenções de Campos
- **ID**: Sempre UUID como chave primária
- **Contabilidade**: Sempre ForeignKey para isolamento multi-tenant
- **Nomes**: Usar `CharField` com `max_length` apropriado
- **Textos Longos**: Usar `TextField` para descrições
- **Valores Monetários**: Usar `DecimalField` com `max_digits` e `decimal_places`
- **Datas**: Usar `DateField` para datas, `DateTimeField` para timestamps
- **Booleanos**: Usar `BooleanField` com `default` explícito
- **JSON**: Usar `JSONField` para dados estruturados
- **Auditoria**: Sempre incluir `created_at`, `updated_at`, `created_by`

### 2. Serializers

#### Estrutura Padrão
```python
class MeuModeloSerializer(serializers.ModelSerializer):
    """
    Serializer para MeuModelo
    """
    # Campos calculados
    contabilidade_razao_social = serializers.CharField(
        source='contabilidade.razao_social', 
        read_only=True
    )
    created_by_username = serializers.CharField(
        source='created_by.username', 
        read_only=True
    )
    esta_ativo = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = MeuModelo
        fields = [
            'id', 'contabilidade', 'contabilidade_razao_social',
            'nome', 'ativo', 'created_at', 'updated_at',
            'created_by', 'created_by_username', 'esta_ativo'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'created_by']
    
    def validate_nome(self, value):
        """
        Validação específica do campo nome
        """
        if len(value) < 3:
            raise serializers.ValidationError("Nome deve ter pelo menos 3 caracteres.")
        return value
    
    def validate(self, data):
        """
        Validação geral do serializer
        """
        # Validações que envolvem múltiplos campos
        return data
```

#### Convenções de Serializers
- **Campos Relacionados**: Sempre incluir campos de leitura para relacionamentos
- **Validações**: Implementar validações específicas e gerais
- **Campos Calculados**: Usar `@property` nos modelos e `read_only=True`
- **Nested Serializers**: Usar com moderação para evitar N+1 queries
- **Campos de Auditoria**: Sempre `read_only=True`

### 3. ViewSets

#### Estrutura Padrão
```python
class MeuModeloViewSet(BaseViewSet):
    """
    ViewSet para gestão de MeuModelo
    """
    queryset = MeuModelo.objects.all()
    serializer_class = MeuModeloSerializer
    permission_classes = [IsAuthenticated, IsContabilidadeAccessible]
    filterset_class = MeuModeloFilter
    search_fields = ['nome', 'contabilidade__razao_social']
    ordering_fields = ['nome', 'created_at', 'ativo']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """
        Filtra queryset por contabilidade do contexto
        """
        queryset = MeuModelo.objects.select_related(
            'contabilidade', 'created_by'
        ).all()
        
        # Aplicar filtro de contabilidade se não for superusuário
        if not self.request.user.is_superuser:
            contabilidade = getattr(self.request, 'contabilidade', None)
            if contabilidade:
                queryset = queryset.filter(contabilidade=contabilidade)
        
        return queryset
    
    @action(detail=True, methods=['post'])
    def ativar(self, request, pk=None):
        """
        Ativa um item
        """
        item = self.get_object()
        item.ativar()
        
        return Response({
            'message': 'Item ativado com sucesso',
            'ativo': item.ativo
        })
    
    @action(detail=True, methods=['post'])
    def desativar(self, request, pk=None):
        """
        Desativa um item
        """
        item = self.get_object()
        item.desativar()
        
        return Response({
            'message': 'Item desativado com sucesso',
            'ativo': item.ativo
        })
    
    @action(detail=False, methods=['get'])
    def resumo(self, request):
        """
        Resumo dos itens
        """
        queryset = self.get_queryset()
        
        resumo = {
            'total': queryset.count(),
            'ativos': queryset.filter(ativo=True).count(),
            'inativos': queryset.filter(ativo=False).count(),
        }
        
        return Response(resumo)
```

#### Convenções de ViewSets
- **Herança**: Sempre herdar de `BaseViewSet`
- **Permissões**: Usar `IsContabilidadeAccessible` para multi-tenancy
- **Filtros**: Implementar `filterset_class` para busca avançada
- **Busca**: Definir `search_fields` para busca por texto
- **Ordenação**: Definir `ordering_fields` e `ordering` padrão
- **Ações Customizadas**: Usar `@action` para operações específicas
- **Resumos**: Implementar endpoint `/resumo/` para estatísticas

### 4. Filtros

#### Estrutura Padrão
```python
class MeuModeloFilter(django_filters.FilterSet):
    """
    Filtros para MeuModelo
    """
    contabilidade = django_filters.UUIDFilter(field_name='contabilidade__id')
    nome = django_filters.CharFilter(lookup_expr='icontains')
    ativo = django_filters.BooleanFilter()
    
    # Filtros de data
    created_apos = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    created_antes = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')
    
    # Filtros especiais
    ativo = django_filters.BooleanFilter(method='filter_ativo')
    
    class Meta:
        model = MeuModelo
        fields = ['contabilidade', 'nome', 'ativo', 'created_apos', 'created_antes']
    
    def filter_ativo(self, queryset, name, value):
        """
        Filtra itens ativos
        """
        if value:
            return queryset.filter(ativo=True)
        return queryset.exclude(ativo=True)
```

#### Convenções de Filtros
- **Campos Relacionados**: Usar `field_name='relacionamento__campo'`
- **Lookups**: Usar `lookup_expr` para operadores (icontains, gte, lte, etc.)
- **Filtros Especiais**: Implementar métodos customizados para lógica complexa
- **Datas**: Sempre incluir filtros de data de criação e atualização
- **Booleanos**: Implementar filtros para campos booleanos

### 5. URLs

#### Estrutura Padrão
```python
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import MeuModeloViewSet

router = DefaultRouter()
router.register(r'meus-modelos', MeuModeloViewSet, basename='meumodelo')

urlpatterns = [
    path('', include(router.urls)),
]
```

#### Convenções de URLs
- **Nomes**: Usar kebab-case para URLs
- **Basename**: Usar snake_case para basename
- **Router**: Usar `DefaultRouter` para ViewSets
- **Organização**: Agrupar por funcionalidade

## 🔐 Sistema de Permissões

### Hierarquia de Permissões
```python
# 1. IsAuthenticated - Usuário deve estar autenticado
# 2. IsContabilidadeAccessible - Usuário deve ter acesso à contabilidade
# 3. IsScopeAccessible - Usuário deve ter acesso ao escopo específico
# 4. IsAdminOrContabilidadeOwner - Apenas admins ou donos da contabilidade
```

### Implementação de Permissões Customizadas
```python
class MinhaPermissaoCustomizada(BasePermission):
    """
    Permissão customizada para operação específica
    """
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        # Lógica de permissão específica
        return self.verificar_permissao_especifica(request.user, request)
    
    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated:
            return False
        
        # Lógica de permissão para objeto específico
        return self.verificar_permissao_objeto(request.user, obj)
    
    def verificar_permissao_especifica(self, usuario, request):
        # Implementar lógica específica
        pass
    
    def verificar_permissao_objeto(self, usuario, obj):
        # Implementar lógica específica
        pass
```

## 🧪 Testes

### Estrutura de Testes
```python
class MeuModeloAPITestCase(APITestCase):
    """
    Testes para API de MeuModelo
    """
    
    def setUp(self):
        """
        Configuração inicial para os testes
        """
        # Criar usuário
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            tipo_usuario='admin'
        )
        
        # Criar contabilidade
        self.contabilidade = Contabilidade.objects.create(
            razao_social='Contabilidade Teste',
            cnpj='12345678000195',
            ativo=True
        )
        
        # Criar acesso
        self.acesso = UsuarioAcesso.objects.create(
            usuario=self.user,
            contabilidade=self.contabilidade,
            role='admin',
            data_inicio='2024-01-01',
            ativo=True
        )
        
        # Token de autenticação
        refresh = RefreshToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    
    def test_criar_item(self):
        """
        Testa criação de item
        """
        url = reverse('meumodelo-list')
        data = {
            'contabilidade': str(self.contabilidade.id),
            'nome': 'Item Teste',
            'ativo': True
        }
        
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(MeuModelo.objects.count(), 1)
    
    def test_listar_itens(self):
        """
        Testa listagem de itens
        """
        # Criar item
        MeuModelo.objects.create(
            contabilidade=self.contabilidade,
            nome='Item Teste',
            ativo=True
        )
        
        url = reverse('meumodelo-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
    
    def test_ativar_item(self):
        """
        Testa ativação de item
        """
        item = MeuModelo.objects.create(
            contabilidade=self.contabilidade,
            nome='Item Teste',
            ativo=False
        )
        
        url = reverse('meumodelo-ativar', kwargs={'pk': item.id})
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        item.refresh_from_db()
        self.assertTrue(item.ativo)
```

### Convenções de Testes
- **Setup**: Configurar dados de teste no `setUp`
- **Nomes**: Usar nomes descritivos para os testes
- **Cobertura**: Testar casos de sucesso e erro
- **Isolamento**: Cada teste deve ser independente
- **Dados**: Usar dados realistas mas simples

## 📊 Middleware Multi-Tenant

### Implementação de Middleware Customizado
```python
class MeuMiddlewareCustomizado:
    """
    Middleware customizado para funcionalidade específica
    """
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Lógica antes da requisição
        self.process_request(request)
        
        response = self.get_response(request)
        
        # Lógica após a requisição
        self.process_response(request, response)
        
        return response
    
    def process_request(self, request):
        """
        Processa a requisição antes da view
        """
        # Implementar lógica específica
        pass
    
    def process_response(self, request, response):
        """
        Processa a resposta após a view
        """
        # Implementar lógica específica
        pass
```

### Registro de Middleware
```python
# settings.py
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'apps.api.shared.middleware.MultiTenantContextMiddleware',
    'apps.api.shared.middleware.TenantAuditMiddleware',
    'apps.api.shared.middleware.MeuMiddlewareCustomizado',  # Customizado
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]
```

## 🔄 Migrations

### Estrutura de Migrations
```python
# 0001_initial.py
class Migration(migrations.Migration):
    initial = True
    
    dependencies = [
        ('core', '0001_initial'),
    ]
    
    operations = [
        migrations.CreateModel(
            name='MeuModelo',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('nome', models.CharField(max_length=100)),
                ('ativo', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('contabilidade', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='core.contabilidade')),
                ('created_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='core.usuario')),
            ],
            options={
                'verbose_name': 'Meu Modelo',
                'verbose_name_plural': 'Meus Modelos',
                'db_table': 'app_meus_modelos',
            },
        ),
        migrations.AddIndex(
            model_name='meumodelo',
            index=models.Index(fields=['contabilidade', 'ativo'], name='app_meus_mo_contabi_123456_idx'),
        ),
    ]
```

### Convenções de Migrations
- **Nomes**: Usar números sequenciais e nomes descritivos
- **Dependencies**: Sempre declarar dependências corretas
- **Operations**: Usar operações atômicas
- **Índices**: Criar índices para campos de busca frequente
- **Constraints**: Adicionar constraints de integridade

## 📈 Performance

### Otimizações de Query
```python
# 1. Select Related - Para ForeignKey
queryset = MeuModelo.objects.select_related('contabilidade', 'created_by')

# 2. Prefetch Related - Para ManyToMany e Reverse ForeignKey
queryset = Contabilidade.objects.prefetch_related('meus_modelos')

# 3. Only - Para campos específicos
queryset = MeuModelo.objects.only('id', 'nome', 'ativo')

# 4. Defer - Para excluir campos pesados
queryset = MeuModelo.objects.defer('dados_grandes')

# 5. Annotations - Para campos calculados
queryset = MeuModelo.objects.annotate(
    total_itens=Count('itens_relacionados')
)
```

### Cache
```python
from django.core.cache import cache

def get_meus_modelos_cached(contabilidade_id):
    """
    Busca itens com cache
    """
    cache_key = f'meus_modelos_{contabilidade_id}'
    itens = cache.get(cache_key)
    
    if itens is None:
        itens = MeuModelo.objects.filter(
            contabilidade_id=contabilidade_id,
            ativo=True
        ).select_related('contabilidade')
        cache.set(cache_key, itens, 300)  # 5 minutos
    
    return itens
```

## 🚨 Tratamento de Erros

### Exceções Customizadas
```python
class MeuErroCustomizado(Exception):
    """
    Exceção customizada para erro específico
    """
    def __init__(self, message, code=None):
        self.message = message
        self.code = code
        super().__init__(self.message)

class MeuErroValidacao(ValidationError):
    """
    Erro de validação customizado
    """
    def __init__(self, message, field=None):
        self.field = field
        super().__init__(message)
```

### Tratamento de Erros em ViewSets
```python
def perform_create(self, serializer):
    """
    Criação com tratamento de erro
    """
    try:
        serializer.save(contabilidade=self.request.contabilidade)
    except MeuErroCustomizado as e:
        raise ValidationError({'error': e.message})
    except Exception as e:
        logger.error(f"Erro ao criar item: {e}")
        raise ValidationError({'error': 'Erro interno do servidor'})
```

## 📚 Boas Práticas

### 1. Código Limpo
- **Nomes Descritivos**: Usar nomes que expliquem a intenção
- **Funções Pequenas**: Uma função, uma responsabilidade
- **Comentários**: Documentar lógica complexa
- **Consistência**: Seguir padrões estabelecidos

### 2. Segurança
- **Validação**: Sempre validar dados de entrada
- **Sanitização**: Limpar dados antes de usar
- **Autorização**: Verificar permissões em cada operação
- **Auditoria**: Registrar operações importantes

### 3. Performance
- **Queries Otimizadas**: Usar select_related e prefetch_related
- **Cache**: Implementar cache para dados frequentes
- **Índices**: Criar índices para campos de busca
- **Paginação**: Usar paginação para grandes volumes

### 4. Testes
- **Cobertura**: Testar todos os cenários importantes
- **Isolamento**: Cada teste deve ser independente
- **Dados**: Usar dados de teste realistas
- **Mocks**: Usar mocks para dependências externas

### 5. Documentação
- **Docstrings**: Documentar classes e métodos
- **Comentários**: Explicar lógica complexa
- **README**: Manter documentação atualizada
- **Exemplos**: Fornecer exemplos de uso

## 🔧 Ferramentas de Desenvolvimento

### Comandos Úteis
```bash
# Executar testes
python manage.py test

# Executar testes específicos
python manage.py test apps.api.administracao.tests

# Criar migrations
python manage.py makemigrations

# Aplicar migrations
python manage.py migrate

# Shell interativo
python manage.py shell

# Verificar configuração
python manage.py check

# Coletar arquivos estáticos
python manage.py collectstatic
```

### Debugging
```python
# Logging
import logging
logger = logging.getLogger(__name__)

logger.debug("Debug message")
logger.info("Info message")
logger.warning("Warning message")
logger.error("Error message")

# Debugger
import pdb
pdb.set_trace()

# IPython debugger
import ipdb
ipdb.set_trace()
```

### Profiling
```python
# Django Debug Toolbar
INSTALLED_APPS = [
    'debug_toolbar',
]

MIDDLEWARE = [
    'debug_toolbar.middleware.DebugToolbarMiddleware',
]

# Query counting
from django.db import connection
print(len(connection.queries))
```

## 📖 Referências

- [Django Documentation](https://docs.djangoproject.com/)
- [Django REST Framework](https://www.django-rest-framework.org/)
- [Django Filter](https://django-filter.readthedocs.io/)
- [Django Simple History](https://django-simple-history.readthedocs.io/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [Multi-Tenancy Patterns](https://docs.microsoft.com/en-us/azure/sql-database/saas-tenancy-app-design-patterns)
