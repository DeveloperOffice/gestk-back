# Guia de Desenvolvimento - GESTK

## 🚀 Configuração do Ambiente de Desenvolvimento

### Pré-requisitos

- Python 3.11+
- PostgreSQL 13+
- Git
- IDE (VS Code, PyCharm, etc.)

### Configuração Inicial

1. **Clone e Configure**
```bash
git clone <repository-url>
cd gestk-novo
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate     # Windows
```

2. **Instale Dependências**
```bash
pip install -r requirements.txt
```

3. **Configure Variáveis de Ambiente**
```bash
cp .env.example .env
# Edite o arquivo .env com suas configurações
```

#### **Arquivo `.env` Exemplo:**
```bash
SECRET_KEY=django-insecure-seu-segredo-super-secreto-aqui
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# PostgreSQL
DB_NAME=db_gestk
DB_USER=postgres
DB_PASSWORD=admin
DB_HOST=localhost
DB_PORT=5432

# Sybase (para ETL)
ODBC_DRIVER=SQL Anywhere 17
ODBC_SERVER=dominio3
ODBC_DATABASE=contabil
ODBC_USER=EXTERNO
ODBC_PASSWORD=externo
```

#### **Configuração CORS para Frontend:**
```python
# settings.py
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",      # GESTK Admin App
    "http://127.0.0.1:3000",      # GESTK Admin App (alternativo)
    "http://localhost:3001",      # GESTK Client App
    "http://127.0.0.1:3001",      # GESTK Client App (alternativo)
]

CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_HEADERS = [
    'accept', 'accept-encoding', 'authorization', 'content-type',
    'dnt', 'origin', 'user-agent', 'x-csrftoken', 'x-requested-with',
    'x-contabilidade-id'  # Header customizado do GESTK
]
```

4. **Execute Migrações**
```bash
python manage.py migrate
python manage.py createsuperuser
```

## 📁 Estrutura do Projeto

```
gestk-novo/
├── apps/                          # Aplicações Django
│   ├── core/                     # Módulo central (Contabilidades, Usuários)
│   │   ├── models.py             # Contabilidades, Usuários
│   │   ├── admin.py              # Interface administrativa
│   │   └── management/commands/  # Comandos Django
│   ├── pessoas/                  # Pessoas e Contratos
│   │   ├── models.py             # PessoaFisica, PessoaJuridica, Contrato
│   │   ├── models_quadro_societario.py  # QuadroSocietario, CapitalSocial
│   │   └── services.py           # Serviços de pessoas
│   ├── fiscal/                   # Documentos Fiscais
│   │   └── models.py             # NotaFiscal, NotaFiscalItem
│   ├── funcionarios/             # Recursos Humanos
│   │   └── models.py             # Funcionario, VinculoEmpregaticio, etc.
│   ├── contabil/                 # Contabilidade
│   │   └── models.py             # PlanoContas, LancamentoContabil
│   ├── administracao/            # Administração e Logs
│   │   ├── models.py             # Usuario, UsuarioContabilidade
│   │   └── models_etl19_corrigido.py  # Logs de atividades
│   ├── cadastros_gerais/         # Cadastros Gerais
│   ├── contabilidade_fiscal/     # Contabilidade Fiscal
│   └── importacao/               # Sistema ETL
│       └── management/commands/  # Comandos ETL
│           ├── _base.py          # Classe base para ETLs
│           ├── etl_00_*.py       # ETLs de mapeamento
│           ├── etl_01_*.py       # ETLs base
│           ├── etl_05_*.py       # ETLs contábeis
│           ├── etl_07_*.py       # ETLs fiscais
│           ├── etl_08_*.py       # ETLs de RH
│           ├── etl_18_*.py       # ETLs de administração
│           └── etl_21_*.py       # ETLs de quadro societário
├── shared/                       # Código compartilhado
│   ├── mixins/                   # Mixins reutilizáveis
│   ├── utils/                    # Utilitários
│   └── validators/               # Validadores
├── tests/                        # Testes automatizados
├── docs/                         # Documentação técnica
│   ├── desenvolvimento/          # Guia de desenvolvimento
│   ├── etls/                     # Guia de ETLs
│   ├── arquitetura/              # Guia de arquitetura
│   ├── api/                      # Documentação da API
│   └── deploy/                   # Guia de deploy
├── gestk/                        # Configurações Django
│   ├── settings.py               # Configurações principais
│   ├── urls.py                   # URLs principais
│   ├── wsgi.py                   # WSGI
│   └── asgi.py                   # ASGI
└── requirements.txt              # Dependências
```

## 🎯 Padrões de Desenvolvimento

### 1. Estrutura de Modelos

```python
class MeuModelo(models.Model):
    """Docstring descritiva do modelo."""
    
    # Campos obrigatórios
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    contabilidade = models.ForeignKey('core.Contabilidade', on_delete=models.PROTECT)
    
    # Campos de negócio
    nome = models.CharField(max_length=255)
    ativo = models.BooleanField(default=True)
    
    # Auditoria
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()
    
    class Meta:
        verbose_name = 'Meu Modelo'
        verbose_name_plural = 'Meus Modelos'
        db_table = 'app_meu_modelo'
        unique_together = ('contabilidade', 'nome')
        indexes = [
            models.Index(fields=['contabilidade', 'ativo']),
        ]
    
    def __str__(self):
        return f"{self.nome} ({self.contabilidade.razao_social})"
```

### 2. ETLs (Extract, Transform, Load)

```python
from ._base import BaseETLCommand

class Command(BaseETLCommand):
    help = 'Descrição do ETL'
    
    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('--- Iniciando ETL ---'))
        
        # 1. Construir mapas de referência
        historical_map = self.build_historical_contabilidade_map()
        
        # 2. Extrair dados do Sybase
        connection = self.get_sybase_connection()
        data = self.extract_data(connection)
        
        # 3. Processar e carregar
        stats = self.processar_dados(data, historical_map)
        
        # 4. Relatório final
        self.print_stats(stats)
```

### 3. APIs REST

```python
from rest_framework import viewsets, permissions
from rest_framework.decorators import action

class MeuModeloViewSet(viewsets.ModelViewSet):
    """ViewSet para MeuModelo."""
    
    serializer_class = MeuModeloSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Filtra por contabilidade do usuário."""
        return MeuModelo.objects.filter(
            contabilidade=self.request.user.contabilidade
        )
    
    @action(detail=True, methods=['post'])
    def acao_customizada(self, request, pk=None):
        """Ação customizada do endpoint."""
        # Implementação da ação
        pass
```

## 🔒 Regras de Multi-Tenancy

### 1. Isolamento Obrigatório

**✅ CORRETO:**
```python
# Sempre filtrar por contabilidade
queryset = MeuModelo.objects.filter(contabilidade=user.contabilidade)

# Em ETLs, usar get_contabilidade_for_date
contabilidade = self.get_contabilidade_for_date(historical_map, codi_emp, data)
```

**❌ INCORRETO:**
```python
# NUNCA fazer isso
queryset = MeuModelo.objects.all()  # Vaza dados de outras contabilidades
```

### 2. Validação de Permissões

```python
def clean(self):
    """Validação de isolamento multitenant."""
    if not self.contabilidade:
        raise ValidationError("Contabilidade é obrigatória")
    
    # Verificar se o usuário tem acesso à contabilidade
    if hasattr(self, 'user') and self.user.contabilidade != self.contabilidade:
        raise ValidationError("Acesso negado à contabilidade")
```

## 🧪 Testes

### 1. Testes Unitários

```python
from django.test import TestCase
from django.contrib.auth import get_user_model
from core.models import Contabilidade

class MeuModeloTestCase(TestCase):
    def setUp(self):
        self.contabilidade = Contabilidade.objects.create(
            razao_social="Teste Contabilidade",
            cnpj="12345678000199"
        )
        self.user = get_user_model().objects.create_user(
            username="teste",
            contabilidade=self.contabilidade
        )
    
    def test_criacao_modelo(self):
        """Testa criação de modelo."""
        modelo = MeuModelo.objects.create(
            contabilidade=self.contabilidade,
            nome="Teste"
        )
        self.assertEqual(modelo.nome, "Teste")
        self.assertEqual(modelo.contabilidade, self.contabilidade)
```

### 2. Testes de Integração

```python
class ETLTestCase(TestCase):
    def test_etl_multitenant(self):
        """Testa isolamento em ETL."""
        # Criar duas contabilidades
        cont1 = Contabilidade.objects.create(...)
        cont2 = Contabilidade.objects.create(...)
        
        # Executar ETL
        call_command('etl_teste')
        
        # Verificar isolamento
        self.assertEqual(MeuModelo.objects.filter(contabilidade=cont1).count(), 1)
        self.assertEqual(MeuModelo.objects.filter(contabilidade=cont2).count(), 1)
```

## 📝 Convenções de Código

### 1. Nomenclatura

- **Classes**: PascalCase (`MeuModelo`)
- **Funções/Métodos**: snake_case (`meu_metodo`)
- **Variáveis**: snake_case (`minha_variavel`)
- **Constantes**: UPPER_CASE (`MINHA_CONSTANTE`)

### 2. Docstrings

```python
def meu_metodo(self, parametro1, parametro2=None):
    """
    Descrição breve do método.
    
    Args:
        parametro1 (str): Descrição do parâmetro
        parametro2 (int, optional): Descrição opcional
        
    Returns:
        bool: Descrição do retorno
        
    Raises:
        ValidationError: Quando o parâmetro é inválido
    """
    pass
```

### 3. Imports

```python
# Imports padrão do Python
import os
import sys
from datetime import date, datetime

# Imports de terceiros
from django.db import models
from rest_framework import serializers

# Imports locais
from core.models import Contabilidade
from .base import BaseETLCommand
```

## 🔄 Git Workflow

### 1. Branches

- **main**: Produção
- **develop**: Desenvolvimento
- **feature/nome**: Novas funcionalidades
- **hotfix/nome**: Correções urgentes

### 2. Commits

```bash
# Formato: tipo(escopo): descrição
git commit -m "feat(etl): adiciona ETL de funcionários"
git commit -m "fix(api): corrige validação de multitenancy"
git commit -m "docs(readme): atualiza documentação"
```

### 3. Pull Requests

- Título descritivo
- Descrição detalhada das mudanças
- Referência a issues
- Checklist de validação

## 🐛 Debugging

### 1. Logs

```python
import logging

logger = logging.getLogger(__name__)

def meu_metodo(self):
    logger.info("Iniciando processamento")
    try:
        # Código
        logger.debug(f"Processando item: {item}")
    except Exception as e:
        logger.error(f"Erro no processamento: {e}")
        raise
```

### 2. Debugging Django

```python
# settings.py
DEBUG = True
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'DEBUG',
        },
    },
}
```

## 📊 Performance

### 1. Queries Otimizadas

```python
# ❌ N+1 queries
for item in MeuModelo.objects.all():
    print(item.contabilidade.razao_social)

# ✅ Query otimizada
for item in MeuModelo.objects.select_related('contabilidade'):
    print(item.contabilidade.razao_social)
```

### 2. Cache

```python
from django.core.cache import cache

def get_dados_cacheados(self):
    cache_key = f"dados_{self.contabilidade.id}"
    dados = cache.get(cache_key)
    
    if not dados:
        dados = self.calcular_dados()
        cache.set(cache_key, dados, 300)  # 5 minutos
    
    return dados
```

## 🚀 Deploy

### 1. Variáveis de Produção

```bash
DEBUG=False
SECRET_KEY=chave-super-secreta
ALLOWED_HOSTS=gestk.com.br,www.gestk.com.br
DB_HOST=postgres-prod
REDIS_URL=redis://redis-prod:6379
```

### 2. Migrações

```bash
python manage.py migrate --noinput
python manage.py collectstatic --noinput
```

## 📚 Recursos Adicionais

- [Django Documentation](https://docs.djangoproject.com/)
- [Django REST Framework](https://www.django-rest-framework.org/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [Python Style Guide](https://pep8.org/)
