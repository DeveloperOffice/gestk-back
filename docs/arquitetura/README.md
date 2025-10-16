# Guia de Arquitetura - GESTK

## 🏗️ Visão Geral da Arquitetura

O GESTK é um sistema de gestão contábil SaaS (Software as a Service) construído com Django, PostgreSQL e arquitetura multitenant rigorosa. O sistema migra dados de um legado Sybase SQL Anywhere para uma arquitetura moderna, garantindo isolamento total entre contabilidades (tenants).

## 🎯 Princípios Arquiteturais

### 1. **Multi-Tenancy Estrito**
- **Isolamento Total**: Cada contabilidade é completamente isolada
- **Segurança por Design**: Impossível vazamento de dados entre tenants
- **Escalabilidade**: Suporte a milhares de contabilidades

### 2. **Normalização de Dados (3NF)**
- **Eliminação de Redundância**: Dados existem em um único lugar
- **Integridade Referencial**: Relacionamentos explícitos e consistentes
- **Performance**: Consultas otimizadas e índices eficientes

### 3. **Idempotência e Confiabilidade**
- **ETLs Idempotentes**: Execução múltipla sem duplicação
- **Transações Atômicas**: Rollback automático em caso de erro
- **Auditoria Completa**: Rastreamento de todas as alterações

### 4. **Performance e Escalabilidade**
- **Processamento em Lotes**: Eficiência em grandes volumes
- **Cache Inteligente**: TTL de 5 minutos para mapas
- **Índices Otimizados**: Consultas multitenant eficientes

## 🔒 Segurança e Arquitetura

### **Implementações de Segurança**

#### **1. Multi-Tenancy Estrito**
- **Isolamento por Contabilidade**: ForeignKey obrigatória em todas as tabelas
- **Middleware Automático**: Contexto de tenant definido automaticamente
- **Validação de Acesso**: Verificação de permissões por contabilidade
- **Auditoria Completa**: Log de todas as operações com contexto

#### **2. Autenticação e Autorização**
- **JWT Authentication**: Tokens seguros com refresh automático
- **Roles Granulares**: Superusuário, Admin, Operacional, ETL, Somente Leitura
- **MFA Support**: Autenticação de dois fatores para staff
- **IP Restrictions**: Controle de acesso por faixas de IP

#### **3. Validações de Segurança**
- **CNPJ/CPF como Identificador Universal**: Validação rigorosa
- **Regra de Ouro**: Resolução de contabilidade por data do evento
- **Validação de Permissões**: Verificação em cada operação
- **Auditoria de Acessos**: Rastreamento completo de alterações

### **Plano de Implementação de Segurança**

#### **Status Atual (14/10/2025)**
| Implementação | Status | Prioridade | Descrição |
|---------------|--------|------------|-----------|
| **Custom User (AbstractUser)** | ✅ Concluído | Alta | Evita migração dolorosa futura |
| **Roles por contabilidade** | 🔄 Em andamento | Alta | Melhor isolamento multitenant |
| **RLS no PostgreSQL** | ⏳ Pendente | Alta | Segurança adicional crítica |
| **JWT RS256 + Claims** | 🔄 Em andamento | Média | Segurança enterprise |
| **ETL Assíncrono (Celery)** | ⏳ Pendente | Alta | Performance e confiabilidade |
| **Logging estruturado JSON** | ⏳ Pendente | Média | Observabilidade |
| **MFA para staff** | ⏳ Pendente | Média | Segurança adicional |

#### **Próximas Implementações**
1. **RLS (Row Level Security)** no PostgreSQL
2. **JWT RS256** com claims customizados
3. **ETL Assíncrono** com Celery
4. **Logging estruturado** em JSON
5. **MFA** para usuários administrativos

## 🏛️ Arquitetura do Sistema

### **Diagrama de Alto Nível**

```
┌─────────────────────────────────────────────────────────────┐
│                    GESTK - ARQUITETURA                     │
├─────────────────────────────────────────────────────────────┤
│  Frontend (React/Vue)  │  API REST (Django)  │  Admin      │
├─────────────────────────────────────────────────────────────┤
│  PostgreSQL (Multi-tenant)  │  Redis (Cache)  │  Files     │
├─────────────────────────────────────────────────────────────┤
│  ETL System (Sybase → PostgreSQL)  │  Monitoring & Logs   │
└─────────────────────────────────────────────────────────────┘
```

### **Camadas da Aplicação**

```
┌─────────────────────────────────────────────────────────────┐
│                    CAMADA DE APRESENTAÇÃO                   │
│  React/Vue Frontend  │  Django Admin  │  API REST         │
├─────────────────────────────────────────────────────────────┤
│                    CAMADA DE APLICAÇÃO                      │
│  Views/ViewSets  │  Serializers  │  Services  │  ETLs     │
├─────────────────────────────────────────────────────────────┤
│                    CAMADA DE DOMÍNIO                        │
│  Models  │  Business Logic  │  Validators  │  Rules      │
├─────────────────────────────────────────────────────────────┤
│                    CAMADA DE INFRAESTRUTURA                 │
│  PostgreSQL  │  Redis  │  File Storage  │  Sybase ODBC   │
└─────────────────────────────────────────────────────────────┘
```

## 🗄️ Arquitetura de Dados

### **Modelo de Dados Principal**

```mermaid
erDiagram
    Contabilidade ||--o{ PessoaJuridica : "possui"
    Contabilidade ||--o{ PessoaFisica : "possui"
    Contabilidade ||--o{ Usuario : "possui"
    Contabilidade ||--o{ NotaFiscal : "possui"
    Contabilidade ||--o{ LancamentoContabil : "possui"
    
    PessoaJuridica ||--o{ Contrato : "tem"
    PessoaFisica ||--o{ Contrato : "tem"
    PessoaJuridica ||--o{ QuadroSocietario : "tem"
    
    Usuario ||--o{ UsuarioContabilidade : "vinculado"
    UsuarioContabilidade }o--|| Contabilidade : "pertence"
    UsuarioContabilidade }o--|| PessoaJuridica : "acessa"
    
    NotaFiscal ||--o{ NotaFiscalItem : "contém"
    LancamentoContabil ||--o{ LancamentoContabilItem : "contém"
```

### **Estrutura Multitenant**

#### **Tabela Central: Contabilidade**
```python
class Contabilidade(models.Model):
    """Representa cada tenant (contabilidade) no sistema."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    razao_social = models.CharField(max_length=255)
    nome_fantasia = models.CharField(max_length=255)
    cnpj = models.CharField(max_length=14, unique=True)
    ativo = models.BooleanField(default=True)
    # ... outros campos
```

#### **Isolamento por ForeignKey**
```python
class PessoaJuridica(models.Model):
    """Pessoa jurídica isolada por contabilidade."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    contabilidade = models.ForeignKey(
        'core.Contabilidade', 
        on_delete=models.CASCADE,  # OBRIGATÓRIO
        db_index=True
    )
    cnpj = models.CharField(max_length=14)
    razao_social = models.CharField(max_length=255)
    # ... outros campos
    
    class Meta:
        unique_together = ('contabilidade', 'cnpj')  # Isolamento garantido
```

### **Regra de Ouro (Golden Rule)**

O sistema utiliza um mapeamento histórico robusto para resolver a contabilidade correta:

```python
def get_contabilidade_for_date_optimized(self, historical_map, codi_emp, event_date):
    """
    Resolve contabilidade para empresa em data específica.
    
    Fluxo:
    1. codi_emp (Sybase) → cgce_emp (CNPJ/CPF) via bethadba.geempre
    2. CNPJ/CPF → Contratos ativos na data do evento
    3. Contrato → Contabilidade
    """
    # Implementação com cache e validação
    pass
```

## 🔄 Arquitetura ETL

### **Sistema de ETL em Camadas**

```
┌─────────────────────────────────────────────────────────────┐
│                    CAMADA DE APLICAÇÃO ETL                  │
│  ETL Commands  │  BaseETLCommand  │  Data Processing      │
├─────────────────────────────────────────────────────────────┤
│                    CAMADA DE TRANSFORMAÇÃO                  │
│  Data Mapping  │  Validation  │  Business Rules          │
├─────────────────────────────────────────────────────────────┤
│                    CAMADA DE EXTRAÇÃO                       │
│  Sybase ODBC  │  Query Builder  │  Data Extraction       │
├─────────────────────────────────────────────────────────────┤
│                    CAMADA DE CARREGAMENTO                   │
│  PostgreSQL  │  Transactions  │  Data Loading            │
└─────────────────────────────────────────────────────────────┘
```

### **BaseETLCommand - Classe Base**

```python
class BaseETLCommand(BaseCommand):
    """Classe base para todos os ETLs."""
    
    def get_sybase_connection(self):
        """Conexão otimizada com Sybase."""
        
    def build_historical_contabilidade_map_cached(self):
        """Mapa histórico com cache TTL de 5 minutos."""
        
    def get_contabilidade_for_date_optimized(self, historical_map, codi_emp, event_date):
        """Resolve contabilidade usando regra de ouro."""
        
    def execute_query(self, connection, query):
        """Execução otimizada de queries."""
        
    def print_stats(self, stats):
        """Relatórios detalhados de execução."""
```

### **Fluxo de Execução ETL**

```mermaid
graph TD
    A[Início ETL] --> B[Construir Mapa Histórico]
    B --> C[Conectar Sybase]
    C --> D[Extrair Dados]
    D --> E[Processar em Lotes]
    E --> F[Resolver Contabilidade]
    F --> G[Validar Dados]
    G --> H[Salvar no PostgreSQL]
    H --> I[Atualizar Estatísticas]
    I --> J[Próximo Lote?]
    J -->|Sim| E
    J -->|Não| K[Gerar Relatório]
    K --> L[Fim ETL]
```

## 🔒 Arquitetura de Segurança

### **Isolamento Multitenant**

#### **Nível de Banco de Dados**
```sql
-- Todas as consultas são automaticamente filtradas por contabilidade
SELECT * FROM pessoas_juridicas 
WHERE contabilidade_id = 'uuid-da-contabilidade';
```

#### **Nível de Aplicação**
```python
class PessoaJuridicaViewSet(viewsets.ModelViewSet):
    def get_queryset(self):
        """Filtro automático por contabilidade do usuário."""
        return PessoaJuridica.objects.filter(
            contabilidade=self.request.user.contabilidade
        )
```

#### **Nível de API**
```python
class PessoaJuridicaSerializer(serializers.ModelSerializer):
    def validate(self, data):
        """Validação de isolamento multitenant."""
        if not data.get('contabilidade'):
            raise ValidationError("Contabilidade é obrigatória")
        return data
```

### **Auditoria e Rastreabilidade**

```python
class PessoaJuridica(models.Model):
    # ... campos do modelo
    
    # Auditoria automática
    history = HistoricalRecords()
    
    # Campos de auditoria
    data_criacao = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)
    criado_por = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True)
    atualizado_por = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True)
```

## 📊 Arquitetura de Performance

### **Estratégias de Otimização**

#### **1. Processamento em Lotes**
```python
def processar_dados(self, data, historical_map, options):
    """Processamento em lotes para performance."""
    BATCH_SIZE = options.get('batch_size', 1000)
    
    for i in range(0, len(data), BATCH_SIZE):
        batch = data[i:i + BATCH_SIZE]
        
        with transaction.atomic():
            for row in batch:
                # Processar registro
                pass
```

#### **2. Cache Inteligente**
```python
@lru_cache(maxsize=128)
def get_contabilidade_for_date_optimized(self, historical_map, codi_emp, event_date):
    """Cache com TTL de 5 minutos."""
    # Implementação com cache
    pass
```

#### **3. Índices Otimizados**
```python
class PessoaJuridica(models.Model):
    # ... campos
    
    class Meta:
        indexes = [
            models.Index(fields=['contabilidade', 'cnpj']),
            models.Index(fields=['contabilidade', 'razao_social']),
            models.Index(fields=['cnpj']),  # Para busca global
        ]
```

### **Monitoramento de Performance**

```python
def print_stats(self, stats):
    """Estatísticas detalhadas de performance."""
    self.stdout.write(f"Cache Hits: {stats['cache_hits']}")
    self.stdout.write(f"Cache Misses: {stats['cache_misses']}")
    self.stdout.write(f"Sybase Queries: {stats['sybase_queries']}")
    self.stdout.write(f"Tempo Total: {stats['tempo_fim'] - stats['tempo_inicio']:.2f}s")
```

## 🚀 Arquitetura de Escalabilidade

### **Escalabilidade Horizontal**

#### **1. Particionamento por Contabilidade**
```python
# Cada contabilidade pode ser movida para um banco separado
class Contabilidade(models.Model):
    database_name = models.CharField(max_length=100)  # Para roteamento
```

#### **2. Cache Distribuído**
```python
# Redis para cache distribuído
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}
```

#### **3. Load Balancing**
```nginx
# Nginx para balanceamento de carga
upstream gestk_backend {
    server 127.0.0.1:8000;
    server 127.0.0.1:8001;
    server 127.0.0.1:8002;
}
```

### **Escalabilidade Vertical**

#### **1. Otimização de Queries**
```python
# select_related para evitar N+1 queries
pessoas = PessoaJuridica.objects.select_related('contabilidade')

# prefetch_related para relacionamentos many-to-many
pessoas = PessoaJuridica.objects.prefetch_related('cnaes_secundarios')
```

#### **2. Índices Compostos**
```sql
-- Índice composto para consultas multitenant
CREATE INDEX idx_pessoa_juridica_contabilidade_cnpj 
ON pessoas_juridicas (contabilidade_id, cnpj);
```

## 🔧 Arquitetura de Configuração

### **Configuração por Ambiente**

```python
# settings/base.py
class BaseSettings:
    # Configurações comuns
    
# settings/development.py
class DevelopmentSettings(BaseSettings):
    DEBUG = True
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': 'gestk_dev',
        }
    }

# settings/production.py
class ProductionSettings(BaseSettings):
    DEBUG = False
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': 'gestk_prod',
        }
    }
```

### **Variáveis de Ambiente**

```bash
# .env
DEBUG=False
SECRET_KEY=chave-super-secreta
DATABASE_URL=postgresql://user:pass@localhost/gestk
REDIS_URL=redis://localhost:6379/0
SYBASE_DRIVER=SQL Anywhere 17
SYBASE_SERVER=servidor_sybase
```

## 📈 Arquitetura de Monitoramento

### **Logs Estruturados**

```python
import logging
import structlog

logger = structlog.get_logger(__name__)

def processar_etl(self, data):
    logger.info("Iniciando ETL", etl_name="etl_18_usuarios", records=len(data))
    
    try:
        # Processamento
        logger.debug("Processando lote", batch_size=1000)
    except Exception as e:
        logger.error("Erro no ETL", error=str(e), etl_name="etl_18_usuarios")
        raise
```

### **Métricas de Performance**

```python
from django.core.cache import cache

def track_etl_metrics(self, stats):
    """Rastreia métricas de ETL."""
    cache.set(f"etl_metrics_{self.etl_name}", {
        'records_processed': stats['criados'] + stats['atualizados'],
        'errors': stats['erros'],
        'execution_time': stats['tempo_fim'] - stats['tempo_inicio'],
        'timestamp': timezone.now().isoformat(),
    }, timeout=3600)  # 1 hora
```

## 🧪 Arquitetura de Testes

### **Estrutura de Testes**

```
tests/
├── unit/                    # Testes unitários
│   ├── test_models.py      # Testes de modelos
│   ├── test_services.py    # Testes de serviços
│   └── test_utils.py       # Testes de utilitários
├── integration/             # Testes de integração
│   ├── test_etls.py        # Testes de ETLs
│   ├── test_api.py         # Testes de API
│   └── test_multitenancy.py # Testes de multitenancy
├── e2e/                     # Testes end-to-end
│   ├── test_user_flows.py  # Fluxos de usuário
│   └── test_etl_flows.py   # Fluxos de ETL
└── fixtures/                # Dados de teste
    ├── contabilidades.json
    └── usuarios.json
```

### **Testes de Multitenancy**

```python
class MultitenancyTestCase(TestCase):
    def setUp(self):
        self.contabilidade1 = Contabilidade.objects.create(
            razao_social="Contabilidade 1",
            cnpj="12345678000199"
        )
        self.contabilidade2 = Contabilidade.objects.create(
            razao_social="Contabilidade 2",
            cnpj="98765432000188"
        )
    
    def test_isolamento_contabilidades(self):
        """Testa isolamento entre contabilidades."""
        # Criar dados para contabilidade1
        pessoa1 = PessoaJuridica.objects.create(
            contabilidade=self.contabilidade1,
            cnpj="11111111000111",
            razao_social="Empresa 1"
        )
        
        # Verificar que contabilidade2 não vê os dados
        self.assertEqual(
            PessoaJuridica.objects.filter(contabilidade=self.contabilidade2).count(),
            0
        )
```

## 📚 Padrões de Design

### **1. Repository Pattern**

```python
class PessoaJuridicaRepository:
    """Repository para PessoaJuridica."""
    
    def __init__(self, contabilidade):
        self.contabilidade = contabilidade
    
    def get_by_cnpj(self, cnpj):
        """Busca pessoa jurídica por CNPJ."""
        return PessoaJuridica.objects.filter(
            contabilidade=self.contabilidade,
            cnpj=cnpj
        ).first()
    
    def create(self, data):
        """Cria nova pessoa jurídica."""
        data['contabilidade'] = self.contabilidade
        return PessoaJuridica.objects.create(**data)
```

### **2. Service Layer**

```python
class PessoaJuridicaService:
    """Serviço para operações de PessoaJuridica."""
    
    def __init__(self, contabilidade):
        self.repository = PessoaJuridicaRepository(contabilidade)
    
    def criar_pessoa_juridica(self, data):
        """Cria pessoa jurídica com validações."""
        # Validações de negócio
        if not self.validar_cnpj(data['cnpj']):
            raise ValidationError("CNPJ inválido")
        
        # Criar pessoa jurídica
        return self.repository.create(data)
```

### **3. Factory Pattern**

```python
class ETLFactory:
    """Factory para criação de ETLs."""
    
    @staticmethod
    def create_etl(etl_name, options):
        """Cria instância de ETL."""
        etl_class = ETL_REGISTRY.get(etl_name)
        if not etl_class:
            raise ValueError(f"ETL {etl_name} não encontrado")
        
        return etl_class(options)

ETL_REGISTRY = {
    'etl_18_usuarios': ETL18UsuariosCommand,
    'etl_19_logs': ETL19LogsCommand,
    'etl_21_quadro_societario': ETL21QuadroSocietarioCommand,
}
```

## 🔄 Arquitetura de Deploy

### **Docker e Containerização**

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8000

CMD ["gunicorn", "gestk.wsgi:application", "--bind", "0.0.0.0:8000"]
```

### **Docker Compose**

```yaml
# docker-compose.yml
version: '3.8'
services:
  web:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://postgres:password@db:5432/gestk
    depends_on:
      - db
      - redis
  
  db:
    image: postgres:13
    environment:
      POSTGRES_DB: gestk
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: password
    volumes:
      - postgres_data:/var/lib/postgresql/data
  
  redis:
    image: redis:6-alpine
    ports:
      - "6379:6379"

volumes:
  postgres_data:
```

## 📚 Referências e Recursos

### **Documentação Técnica**
- [Django Documentation](https://docs.djangoproject.com/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [Django REST Framework](https://www.django-rest-framework.org/)

### **Padrões de Design**
- [Clean Architecture](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)
- [SOLID Principles](https://en.wikipedia.org/wiki/SOLID)
- [Repository Pattern](https://martinfowler.com/eaaCatalog/repository.html)

### **Multitenancy**
- [Django Multitenancy](https://books.agiliq.com/projects/django-multi-tenant/en/latest/)
- [PostgreSQL Row Level Security](https://www.postgresql.org/docs/current/ddl-rowsecurity.html)

---

**Última atualização:** 24/09/2025  
**Versão:** 2.0  
**Status:** Arquitetura Estável