# Arquitetura Multi-Tenant do GESTK

## 📋 Visão Geral

O GESTK implementa uma arquitetura multi-tenant robusta que permite que múltiplos escritórios de contabilidade utilizem o mesmo sistema de forma isolada e segura. Cada contabilidade é um "tenant" com seus próprios dados, usuários e configurações.

## 🏗️ Princípios Arquiteturais

### 1. Isolamento de Dados
- **Chave Estrangeira Obrigatória**: Todos os modelos principais possuem uma `ForeignKey` para `Contabilidade`
- **Validação no Banco**: Constraints de integridade referencial garantem isolamento
- **Middleware de Contexto**: Define automaticamente o tenant ativo para cada requisição

### 2. Segurança por Design
- **Regra de Ouro**: Validação automática de acesso baseada no contexto de tenant
- **Permissões Granulares**: Controle de acesso por escopo (contrato/empresa)
- **Auditoria Completa**: Log de todas as operações e mudanças de contexto

### 3. Escalabilidade
- **UUIDs**: Chaves primárias UUID evitam conflitos e facilitam replicação
- **Índices Otimizados**: Índices específicos para consultas multi-tenant
- **Cache Inteligente**: Cache por tenant para melhor performance

## 🔧 Componentes da Arquitetura

### Core Models

#### Contabilidade (Tenant Root)
```python
class Contabilidade(models.Model):
    """
    Representa um tenant (escritório de contabilidade)
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    razao_social = models.CharField(max_length=200)
    nome_fantasia = models.CharField(max_length=200)
    cnpj = models.CharField(max_length=20, unique=True)
    ativo = models.BooleanField(default=True)
    
    # Campos de billing
    responsavel_financeiro_nome = models.CharField(max_length=100)
    responsavel_financeiro_email = models.EmailField()
    suspensa_por_inadimplencia = models.BooleanField(default=False)
    saldo_creditos = models.DecimalField(max_digits=10, decimal_places=2)
```

#### Usuario (Multi-Tenant User)
```python
class Usuario(AbstractUser):
    """
    Usuário que pode acessar múltiplas contabilidades
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    tipo_usuario = models.CharField(max_length=20, choices=TIPO_USUARIO_CHOICES)
    contabilidade = models.ForeignKey(Contabilidade, on_delete=models.CASCADE, null=True)
    ultima_contabilidade = models.ForeignKey(Contabilidade, on_delete=models.SET_NULL, null=True)
    modulos_acessiveis = models.JSONField(default=list)
```

#### UsuarioAcesso (Access Control)
```python
class UsuarioAcesso(models.Model):
    """
    Define o acesso de um usuário a uma contabilidade específica
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    contabilidade = models.ForeignKey(Contabilidade, on_delete=models.CASCADE)
    contrato = models.ForeignKey('pessoas.Contrato', on_delete=models.CASCADE, null=True)
    empresa_cnpj = models.CharField(max_length=20, null=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    modulos_acesso = models.JSONField(default=list)
    data_inicio = models.DateField()
    data_fim = models.DateField(null=True)
    ativo = models.BooleanField(default=True)
```

### Middleware Multi-Tenant

#### MultiTenantContextMiddleware
```python
class MultiTenantContextMiddleware:
    """
    Define o contexto da contabilidade (tenant) para a requisição
    """
    def __call__(self, request):
        if request.user.is_authenticated:
            contabilidade_id = None
            
            # 1. Header X-Contabilidade-ID
            if 'HTTP_X_CONTABILIDADE_ID' in request.META:
                contabilidade_id = request.META['HTTP_X_CONTABILIDADE_ID']
            
            # 2. Query parameter
            if not contabilidade_id and 'contabilidade_id' in request.query_params:
                contabilidade_id = request.query_params['contabilidade_id']
            
            # 3. Contabilidade padrão do usuário
            if not contabilidade_id and hasattr(request.user, 'contabilidade'):
                contabilidade_id = str(request.user.contabilidade.id)
            
            # 4. Última contabilidade acessada
            if not contabilidade_id and hasattr(request.user, 'ultima_contabilidade'):
                contabilidade_id = str(request.user.ultima_contabilidade.id)
            
            # Validar acesso e definir contexto
            if contabilidade_id:
                contabilidade = Contabilidade.objects.get(id=contabilidade_id)
                has_access = UsuarioAcesso.objects.filter(
                    usuario=request.user,
                    contabilidade=contabilidade,
                    ativo=True
                ).exists()
                
                if has_access:
                    request.contabilidade = contabilidade
                    # Atualizar última contabilidade acessada
                    request.user.ultima_contabilidade = contabilidade
                    request.user.save(update_fields=['ultima_contabilidade'])
```

#### TenantAuditMiddleware
```python
class TenantAuditMiddleware:
    """
    Audita mudanças de contexto de tenant
    """
    def __call__(self, request):
        previous_contabilidade_id = None
        if request.user.is_authenticated and hasattr(request.user, 'ultima_contabilidade'):
            previous_contabilidade_id = str(request.user.ultima_contabilidade.id)
        
        response = self.get_response(request)
        
        if request.user.is_authenticated and hasattr(request, 'contabilidade'):
            current_contabilidade_id = str(request.contabilidade.id)
            
            if previous_contabilidade_id != current_contabilidade_id:
                # Registrar auditoria
                AuditoriaSistema.objects.create(
                    contabilidade=request.contabilidade,
                    usuario=request.user,
                    acao='TROCA_TENANT',
                    dados_anteriores={'contabilidade_id': previous_contabilidade_id},
                    dados_novos={'contabilidade_id': current_contabilidade_id}
                )
        
        return response
```

### Sistema de Permissões

#### RegraOuroPermission
```python
class RegraOuroPermission(BasePermission):
    """
    Permissão baseada na Regra de Ouro do GESTK
    """
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        # Superusuários têm acesso total
        if request.user.is_superuser:
            return True
        
        # Verificar acesso à contabilidade
        contabilidade = getattr(request, 'contabilidade', None)
        if not contabilidade:
            return False
        
        return self.verificar_acesso_contabilidade(request.user, contabilidade)
    
    def verificar_acesso_contabilidade(self, usuario, contabilidade):
        """
        Verifica se o usuário tem acesso à contabilidade
        """
        return UsuarioAcesso.objects.filter(
            usuario=usuario,
            contabilidade=contabilidade,
            ativo=True,
            data_inicio__lte=timezone.now().date(),
            data_fim__isnull=True
        ).exists() or UsuarioAcesso.objects.filter(
            usuario=usuario,
            contabilidade=contabilidade,
            ativo=True,
            data_inicio__lte=timezone.now().date(),
            data_fim__gte=timezone.now().date()
        ).exists()
```

#### IsContabilidadeAccessible
```python
class IsContabilidadeAccessible(BasePermission):
    """
    Verifica se o usuário tem acesso à contabilidade do contexto
    """
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        contabilidade = getattr(request, 'contabilidade', None)
        if not contabilidade:
            return False
        
        return UsuarioAcesso.objects.filter(
            usuario=request.user,
            contabilidade=contabilidade,
            ativo=True
        ).exists()
```

#### IsScopeAccessible
```python
class IsScopeAccessible(BasePermission):
    """
    Verifica se o usuário tem acesso ao escopo específico
    """
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        contabilidade = getattr(request, 'contabilidade', None)
        if not contabilidade:
            return False
        
        # Verificar acesso total
        has_total_access = UsuarioAcesso.objects.filter(
            usuario=request.user,
            contabilidade=contabilidade,
            ativo=True,
            contrato__isnull=True,
            empresa_cnpj__isnull=True
        ).exists()
        
        if has_total_access:
            return True
        
        # Verificar acesso por escopo específico
        contrato_id = request.data.get('contrato') or request.query_params.get('contrato')
        empresa_cnpj = request.data.get('empresa_cnpj') or request.query_params.get('empresa_cnpj')
        
        if contrato_id:
            return UsuarioAcesso.objects.filter(
                usuario=request.user,
                contabilidade=contabilidade,
                ativo=True,
                contrato_id=contrato_id
            ).exists()
        
        if empresa_cnpj:
            return UsuarioAcesso.objects.filter(
                usuario=request.user,
                contabilidade=contabilidade,
                ativo=True,
                empresa_cnpj=empresa_cnpj
            ).exists()
        
        return False
```

### ViewSets Multi-Tenant

#### BaseViewSet
```python
class BaseViewSet(viewsets.ModelViewSet):
    """
    ViewSet base com suporte a multi-tenancy
    """
    permission_classes = [IsAuthenticated, IsContabilidadeAccessible]
    
    def get_queryset(self):
        """
        Filtra queryset por contabilidade do contexto
        """
        queryset = super().get_queryset()
        
        # Superusuários veem tudo
        if self.request.user.is_superuser:
            return queryset
        
        # Filtrar por contabilidade do contexto
        contabilidade = getattr(self.request, 'contabilidade', None)
        if contabilidade and hasattr(queryset.model, 'contabilidade'):
            queryset = queryset.filter(contabilidade=contabilidade)
        
        # Aplicar filtros de escopo
        return self.aplicar_filtros_escopo(queryset)
    
    def aplicar_filtros_escopo(self, queryset):
        """
        Aplica filtros de escopo baseados no UsuarioAcesso
        """
        contabilidade = getattr(self.request, 'contabilidade', None)
        if not contabilidade:
            return queryset
        
        acessos = UsuarioAcesso.objects.filter(
            usuario=self.request.user,
            contabilidade=contabilidade,
            ativo=True
        )
        
        # Verificar acesso total
        tem_acesso_total = any(not acesso.contrato and not acesso.empresa_cnpj for acesso in acessos)
        if tem_acesso_total:
            return queryset
        
        # Aplicar filtros de escopo
        filtros_escopo = Q()
        for acesso in acessos:
            if acesso.contrato and hasattr(queryset.model, 'contrato'):
                filtros_escopo |= Q(contrato=acesso.contrato)
            if acesso.empresa_cnpj and hasattr(queryset.model, 'empresa_cnpj'):
                filtros_escopo |= Q(empresa_cnpj=acesso.empresa_cnpj)
        
        return queryset.filter(filtros_escopo) if filtros_escopo else queryset.none()
```

## 🔄 Fluxo de Requisição Multi-Tenant

### 1. Autenticação
```python
# Login do usuário
POST /api/auth/login/
{
    "username": "usuario",
    "password": "senha"
}

# Response com JWT token
{
    "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

### 2. Definição de Contexto
```python
# Header para definir tenant
X-Contabilidade-ID: 123e4567-e89b-12d3-a456-426614174000

# Ou via query parameter
GET /api/endpoint/?contabilidade_id=123e4567-e89b-12d3-a456-426614174000
```

### 3. Validação de Acesso
```python
# Middleware verifica:
# 1. Usuário autenticado
# 2. Contabilidade existe
# 3. UsuarioAcesso ativo
# 4. Data de início/fim válida
```

### 4. Filtragem de Dados
```python
# ViewSet aplica filtros:
# 1. Por contabilidade (tenant)
# 2. Por escopo (contrato/empresa)
# 3. Por permissões do usuário
```

### 5. Auditoria
```python
# Middleware registra:
# 1. Mudanças de contexto
# 2. Operações realizadas
# 3. Dados acessados
```

## 📊 Padrões de Dados

### Estrutura de Tabelas
```sql
-- Tabela de tenant (raiz)
CREATE TABLE core_contabilidades (
    id UUID PRIMARY KEY,
    razao_social VARCHAR(200) NOT NULL,
    nome_fantasia VARCHAR(200),
    cnpj VARCHAR(20) UNIQUE NOT NULL,
    ativo BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Tabela de usuários multi-tenant
CREATE TABLE core_usuarios (
    id UUID PRIMARY KEY,
    username VARCHAR(150) UNIQUE NOT NULL,
    email VARCHAR(254),
    tipo_usuario VARCHAR(20) NOT NULL,
    contabilidade_id UUID REFERENCES core_contabilidades(id),
    ultima_contabilidade_id UUID REFERENCES core_contabilidades(id),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Tabela de controle de acesso
CREATE TABLE core_usuario_acessos (
    id UUID PRIMARY KEY,
    usuario_id UUID NOT NULL REFERENCES core_usuarios(id),
    contabilidade_id UUID NOT NULL REFERENCES core_contabilidades(id),
    contrato_id UUID REFERENCES pessoas_contratos(id),
    empresa_cnpj VARCHAR(20),
    role VARCHAR(20) NOT NULL,
    modulos_acesso JSONB DEFAULT '[]',
    data_inicio DATE NOT NULL,
    data_fim DATE,
    ativo BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(usuario_id, contabilidade_id, contrato_id),
    UNIQUE(usuario_id, contabilidade_id, empresa_cnpj)
);

-- Tabela de dados do tenant (exemplo)
CREATE TABLE pessoas_pessoas_juridicas (
    id UUID PRIMARY KEY,
    contabilidade_id UUID NOT NULL REFERENCES core_contabilidades(id),
    razao_social VARCHAR(200) NOT NULL,
    nome_fantasia VARCHAR(200),
    cnpj VARCHAR(20) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### Índices Otimizados
```sql
-- Índices para multi-tenancy
CREATE INDEX idx_pessoas_juridicas_contabilidade ON pessoas_pessoas_juridicas(contabilidade_id);
CREATE INDEX idx_usuario_acessos_usuario_contabilidade ON core_usuario_acessos(usuario_id, contabilidade_id);
CREATE INDEX idx_usuario_acessos_contabilidade_ativo ON core_usuario_acessos(contabilidade_id, ativo);
CREATE INDEX idx_usuario_acessos_data_vigencia ON core_usuario_acessos(data_inicio, data_fim);

-- Índices compostos para performance
CREATE INDEX idx_pessoas_juridicas_contabilidade_cnpj ON pessoas_pessoas_juridicas(contabilidade_id, cnpj);
CREATE INDEX idx_usuario_acessos_escopo ON core_usuario_acessos(usuario_id, contabilidade_id, contrato_id, empresa_cnpj);
```

## 🔒 Segurança Multi-Tenant

### Princípios de Segurança
1. **Isolamento Rigoroso**: Dados de diferentes tenants nunca se misturam
2. **Validação Dupla**: Banco de dados + aplicação
3. **Auditoria Completa**: Todas as operações são registradas
4. **Princípio do Menor Privilégio**: Usuários só acessam o necessário

### Validações de Segurança
```python
# 1. Validação no modelo
class PessoaJuridica(models.Model):
    contabilidade = models.ForeignKey(Contabilidade, on_delete=models.CASCADE)
    # Campo obrigatório garante isolamento no banco

# 2. Validação no ViewSet
def get_queryset(self):
    contabilidade = getattr(self.request, 'contabilidade', None)
    if contabilidade:
        return queryset.filter(contabilidade=contabilidade)
    return queryset.none()

# 3. Validação na permissão
def has_permission(self, request, view):
    contabilidade = getattr(request, 'contabilidade', None)
    return UsuarioAcesso.objects.filter(
        usuario=request.user,
        contabilidade=contabilidade,
        ativo=True
    ).exists()
```

### Prevenção de Vazamento de Dados
```python
# 1. Filtros automáticos
def get_queryset(self):
    return super().get_queryset().filter(contabilidade=self.request.contabilidade)

# 2. Validação de escopo
def aplicar_filtros_escopo(self, queryset):
    # Aplicar filtros baseados no UsuarioAcesso
    pass

# 3. Auditoria de acesso
def perform_create(self, serializer):
    serializer.save(contabilidade=self.request.contabilidade)
    # Registrar auditoria
```

## 📈 Performance e Escalabilidade

### Otimizações Implementadas
1. **Índices Específicos**: Índices otimizados para consultas multi-tenant
2. **Cache por Tenant**: Cache específico para cada contabilidade
3. **Lazy Loading**: Carregamento sob demanda de relacionamentos
4. **Paginação**: Paginação automática para grandes volumes

### Métricas de Performance
```python
# Query otimizada com select_related
queryset = PessoaJuridica.objects.select_related('contabilidade').filter(
    contabilidade=contabilidade
)

# Query com prefetch_related para relacionamentos
queryset = Contabilidade.objects.prefetch_related(
    'usuarios', 'pessoas_juridicas'
).filter(ativo=True)

# Query com índices específicos
queryset = UsuarioAcesso.objects.filter(
    usuario=usuario,
    contabilidade=contabilidade,
    ativo=True
).select_related('usuario', 'contabilidade')
```

### Estratégias de Escalabilidade
1. **Sharding Horizontal**: Preparado para divisão por contabilidade
2. **Read Replicas**: Suporte a réplicas de leitura
3. **Cache Distribuído**: Cache compartilhado entre instâncias
4. **Queue System**: Processamento assíncrono de operações pesadas

## 🧪 Testes Multi-Tenant

### Testes de Isolamento
```python
def test_isolamento_entre_tenants(self):
    """
    Testa se dados de diferentes tenants estão isolados
    """
    # Criar duas contabilidades
    contabilidade1 = Contabilidade.objects.create(razao_social="Contabilidade 1")
    contabilidade2 = Contabilidade.objects.create(razao_social="Contabilidade 2")
    
    # Criar dados para cada tenant
    pessoa1 = PessoaJuridica.objects.create(
        contabilidade=contabilidade1,
        razao_social="Empresa 1"
    )
    pessoa2 = PessoaJuridica.objects.create(
        contabilidade=contabilidade2,
        razao_social="Empresa 2"
    )
    
    # Verificar isolamento
    self.assertEqual(PessoaJuridica.objects.filter(contabilidade=contabilidade1).count(), 1)
    self.assertEqual(PessoaJuridica.objects.filter(contabilidade=contabilidade2).count(), 1)
```

### Testes de Permissões
```python
def test_acesso_por_escopo(self):
    """
    Testa acesso por escopo específico
    """
    # Criar usuário com acesso restrito
    acesso = UsuarioAcesso.objects.create(
        usuario=self.user,
        contabilidade=self.contabilidade,
        contrato=self.contrato,
        role='operacional'
    )
    
    # Verificar acesso ao contrato específico
    self.assertTrue(acesso.tem_acesso_contrato(self.contrato.id))
    self.assertFalse(acesso.tem_acesso_contrato('outro-contrato-id'))
```

## 🔄 Migração e Evolução

### Estratégia de Migração
1. **Fase 1**: Implementação dos modelos base
2. **Fase 2**: Middleware e permissões
3. **Fase 3**: ViewSets e APIs
4. **Fase 4**: Testes e validação
5. **Fase 5**: Documentação e deploy

### Versionamento de Schema
```python
# Migrations com versionamento
class Migration(migrations.Migration):
    dependencies = [
        ('core', '0001_initial'),
    ]
    
    operations = [
        migrations.AddField(
            model_name='contabilidade',
            name='suspensa_por_inadimplencia',
            field=models.BooleanField(default=False),
        ),
    ]
```

### Rollback Strategy
1. **Backup Automático**: Backup antes de cada migração
2. **Rollback Scripts**: Scripts para reverter mudanças
3. **Validação Pós-Migração**: Verificação de integridade
4. **Monitoramento**: Alertas para problemas

## 📚 Referências e Padrões

### Padrões Utilizados
- **Multi-Tenant Database per Schema**: Um schema por tenant
- **Shared Database, Shared Schema**: Tabelas compartilhadas com isolamento por FK
- **Row-Level Security**: Segurança a nível de linha
- **JWT Authentication**: Autenticação stateless
- **RESTful APIs**: APIs REST padronizadas

### Bibliotecas e Ferramentas
- **Django**: Framework web
- **Django REST Framework**: APIs REST
- **django-simple-history**: Auditoria
- **PostgreSQL**: Banco de dados
- **Redis**: Cache e sessões
- **Celery**: Processamento assíncrono

### Boas Práticas
1. **Sempre validar tenant**: Nunca confiar apenas no frontend
2. **Auditar tudo**: Registrar todas as operações importantes
3. **Testar isolamento**: Testes específicos para multi-tenancy
4. **Monitorar performance**: Métricas específicas por tenant
5. **Documentar mudanças**: Manter documentação atualizada
