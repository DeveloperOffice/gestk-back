# API de Administração GESTK

## 📋 Visão Geral

A API de Administração do GESTK é um sistema completo de gestão multi-tenant que permite o controle de acessos, contratos e billing para escritórios de contabilidade. O sistema foi projetado para ser seguro, escalável e fácil de usar.

## 🏗️ Arquitetura

### Multi-Tenancy
- **Isolamento de Dados**: Cada contabilidade é um tenant isolado
- **Contexto Dinâmico**: Middleware define automaticamente o contexto de tenant
- **Permissões Granulares**: Controle de acesso por escopo (contrato/empresa)

### Componentes Principais
1. **Core**: Modelos base (Contabilidade, Usuario, UsuarioAcesso)
2. **Administração**: Gestão de contratos e acessos
3. **Billing**: Sistema de faturamento e pagamentos
4. **API**: Endpoints REST com autenticação JWT

## 🔐 Sistema de Permissões

### Roles Disponíveis
- **superuser**: Acesso total ao sistema
- **admin**: Administrador da contabilidade
- **operacional**: Usuário operacional
- **etl**: Acesso para importação de dados
- **readonly**: Somente leitura

### Escopo de Acesso
- **Total**: Acesso a todos os dados da contabilidade
- **Por Contrato**: Acesso restrito a um contrato específico
- **Por Empresa**: Acesso restrito a uma empresa (CNPJ)

## 📊 Modelos de Dados

### Core Models

#### Contabilidade
```python
class Contabilidade(models.Model):
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

#### Usuario
```python
class Usuario(AbstractUser):
    tipo_usuario = models.CharField(max_length=20, choices=TIPO_USUARIO_CHOICES)
    contabilidade = models.ForeignKey(Contabilidade, on_delete=models.CASCADE)
    ultima_contabilidade = models.ForeignKey(Contabilidade, on_delete=models.SET_NULL)
    modulos_acessiveis = models.JSONField(default=list)
```

#### UsuarioAcesso
```python
class UsuarioAcesso(models.Model):
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

### Administração Models

#### ContratoGestk
```python
class ContratoGestk(models.Model):
    contabilidade = models.OneToOneField(Contabilidade, on_delete=models.CASCADE)
    numero_contrato = models.CharField(max_length=50, unique=True)
    data_inicio = models.DateField()
    data_termino = models.DateField(null=True)
    plano_servico = models.CharField(max_length=50)
    modulos_inclusos = models.JSONField(default=list)
    limites_usuarios = models.IntegerField(default=5)
    limites_empresas = models.IntegerField(default=10)
    valor_mensal = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
```

### Billing Models

#### Plano
```python
class Plano(models.Model):
    codigo = models.CharField(max_length=50, unique=True)
    nome = models.CharField(max_length=100)
    preco_mensal = models.DecimalField(max_digits=10, decimal_places=2)
    preco_anual = models.DecimalField(max_digits=10, decimal_places=2)
    modulos_inclusos = models.JSONField(default=list)
    limites = models.JSONField(default=dict)
    ativo = models.BooleanField(default=True)
```

#### Assinatura
```python
class Assinatura(models.Model):
    contabilidade = models.ForeignKey(Contabilidade, on_delete=models.CASCADE)
    plano = models.ForeignKey(Plano, on_delete=models.PROTECT)
    data_inicio = models.DateField()
    data_fim = models.DateField(null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    valor_mensal = models.DecimalField(max_digits=10, decimal_places=2)
    ciclo_cobranca = models.CharField(max_length=20, choices=CICLO_CHOICES)
```

#### Fatura
```python
class Fatura(models.Model):
    assinatura = models.ForeignKey(Assinatura, on_delete=models.CASCADE)
    numero_fatura = models.CharField(max_length=50, unique=True)
    competencia = models.CharField(max_length=7)
    valor_original = models.DecimalField(max_digits=12, decimal_places=2)
    valor_final = models.DecimalField(max_digits=12, decimal_places=2)
    data_emissao = models.DateField()
    data_vencimento = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
```

#### Pagamento
```python
class Pagamento(models.Model):
    fatura = models.ForeignKey(Fatura, on_delete=models.CASCADE)
    valor = models.DecimalField(max_digits=12, decimal_places=2)
    metodo = models.CharField(max_length=20, choices=METODO_CHOICES)
    transacao_id = models.CharField(max_length=100)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    data_pagamento = models.DateTimeField(null=True)
```

## 🔗 Endpoints da API

### Administração

#### Contratos GESTK
```
GET    /api/administracao/contratos-gestk/           # Listar contratos
POST   /api/administracao/contratos-gestk/           # Criar contrato
GET    /api/administracao/contratos-gestk/{id}/      # Obter contrato
PUT    /api/administracao/contratos-gestk/{id}/      # Atualizar contrato
DELETE /api/administracao/contratos-gestk/{id}/      # Excluir contrato
POST   /api/administracao/contratos-gestk/{id}/suspender/    # Suspender contrato
POST   /api/administracao/contratos-gestk/{id}/cancelar/     # Cancelar contrato
POST   /api/administracao/contratos-gestk/{id}/ativar/       # Ativar contrato
GET    /api/administracao/contratos-gestk/resumo/    # Resumo dos contratos
```

#### Acessos de Usuário
```
GET    /api/administracao/usuarios-acesso/           # Listar acessos
POST   /api/administracao/usuarios-acesso/           # Criar acesso
GET    /api/administracao/usuarios-acesso/{id}/      # Obter acesso
PUT    /api/administracao/usuarios-acesso/{id}/      # Atualizar acesso
DELETE /api/administracao/usuarios-acesso/{id}/      # Excluir acesso
POST   /api/administracao/usuarios-acesso/{id}/ativar/       # Ativar acesso
POST   /api/administracao/usuarios-acesso/{id}/desativar/    # Desativar acesso
POST   /api/administracao/usuarios-acesso/{id}/estender-vigencia/  # Estender vigência
GET    /api/administracao/usuarios-acesso/resumo/    # Resumo dos acessos
```

#### Contabilidades Admin
```
GET    /api/administracao/contabilidades-admin/      # Listar contabilidades
GET    /api/administracao/contabilidades-admin/{id}/ # Obter contabilidade
PUT    /api/administracao/contabilidades-admin/{id}/ # Atualizar contabilidade
POST   /api/administracao/contabilidades-admin/{id}/suspender-por-inadimplencia/  # Suspender por inadimplência
POST   /api/administracao/contabilidades-admin/{id}/reativar/  # Reativar
GET    /api/administracao/contabilidades-admin/resumo/  # Resumo das contabilidades
```

### Billing

#### Planos
```
GET    /api/billing/planos/                          # Listar planos
POST   /api/billing/planos/                          # Criar plano
GET    /api/billing/planos/{id}/                     # Obter plano
PUT    /api/billing/planos/{id}/                     # Atualizar plano
DELETE /api/billing/planos/{id}/                     # Excluir plano
GET    /api/billing/planos/ativos/                   # Listar planos ativos
GET    /api/billing/planos/resumo/                   # Resumo dos planos
```

#### Assinaturas
```
GET    /api/billing/assinaturas/                     # Listar assinaturas
POST   /api/billing/assinaturas/criar-assinatura/    # Criar assinatura
GET    /api/billing/assinaturas/{id}/                # Obter assinatura
PUT    /api/billing/assinaturas/{id}/                # Atualizar assinatura
DELETE /api/billing/assinaturas/{id}/                # Excluir assinatura
POST   /api/billing/assinaturas/{id}/suspender/      # Suspender assinatura
POST   /api/billing/assinaturas/{id}/cancelar/       # Cancelar assinatura
POST   /api/billing/assinaturas/{id}/ativar/         # Ativar assinatura
GET    /api/billing/assinaturas/resumo/              # Resumo das assinaturas
```

#### Faturas
```
GET    /api/billing/faturas/                         # Listar faturas
POST   /api/billing/faturas/                         # Criar fatura
GET    /api/billing/faturas/{id}/                    # Obter fatura
PUT    /api/billing/faturas/{id}/                    # Atualizar fatura
DELETE /api/billing/faturas/{id}/                    # Excluir fatura
POST   /api/billing/faturas/{id}/marcar-como-paga/   # Marcar como paga
POST   /api/billing/faturas/{id}/cancelar/           # Cancelar fatura
POST   /api/billing/faturas/gerar-faturas/           # Gerar faturas
GET    /api/billing/faturas/resumo/                  # Resumo das faturas
```

#### Pagamentos
```
GET    /api/billing/pagamentos/                      # Listar pagamentos
POST   /api/billing/pagamentos/                      # Criar pagamento
GET    /api/billing/pagamentos/{id}/                 # Obter pagamento
PUT    /api/billing/pagamentos/{id}/                 # Atualizar pagamento
DELETE /api/billing/pagamentos/{id}/                 # Excluir pagamento
POST   /api/billing/pagamentos/{id}/confirmar/       # Confirmar pagamento
POST   /api/billing/pagamentos/{id}/estornar/        # Estornar pagamento
GET    /api/billing/pagamentos/resumo/               # Resumo dos pagamentos
```

## 🔧 Filtros e Busca

### Filtros Disponíveis

#### Contratos GESTK
- `contabilidade`: ID da contabilidade
- `numero_contrato`: Número do contrato (contém)
- `plano_servico`: Código do plano (contém)
- `status`: Status do contrato
- `data_inicio_apos`: Data de início após
- `data_inicio_antes`: Data de início antes
- `valor_min`: Valor mínimo
- `valor_max`: Valor máximo
- `ativo`: Contratos ativos
- `vencido`: Contratos vencidos
- `em_trial`: Contratos em trial

#### Acessos de Usuário
- `usuario`: ID do usuário
- `contabilidade`: ID da contabilidade
- `contrato`: ID do contrato
- `role`: Papel do usuário
- `ativo`: Acessos ativos
- `vencido`: Acessos vencidos
- `mfa_required`: MFA obrigatório

#### Faturas
- `assinatura`: ID da assinatura
- `contabilidade`: ID da contabilidade
- `numero_fatura`: Número da fatura (contém)
- `status`: Status da fatura
- `data_vencimento_apos`: Data de vencimento após
- `data_vencimento_antes`: Data de vencimento antes
- `valor_min`: Valor mínimo
- `valor_max`: Valor máximo
- `vencida`: Faturas vencidas
- `vence_em_dias`: Vence em X dias

### Busca
Todos os endpoints suportam busca por texto nos campos relevantes:
- **Contratos**: `numero_contrato`, `contabilidade__razao_social`
- **Acessos**: `usuario__username`, `usuario__email`, `contabilidade__razao_social`
- **Faturas**: `numero_fatura`, `assinatura__contabilidade__razao_social`

### Ordenação
Todos os endpoints suportam ordenação pelos campos relevantes:
- **Contratos**: `numero_contrato`, `data_inicio`, `data_termino`, `status`, `created_at`
- **Acessos**: `data_inicio`, `data_fim`, `role`, `ativo`, `created_at`
- **Faturas**: `numero_fatura`, `data_emissao`, `data_vencimento`, `status`, `valor_final`

## 🔐 Autenticação e Autorização

### JWT Authentication
```bash
# Login
POST /api/auth/login/
{
    "username": "usuario",
    "password": "senha"
}

# Response
{
    "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

### Headers de Autenticação
```bash
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...
```

### Contexto de Contabilidade
```bash
# Header para definir contexto de tenant
X-Contabilidade-ID: 123e4567-e89b-12d3-a456-426614174000

# Ou via query parameter
?contabilidade_id=123e4567-e89b-12d3-a456-426614174000
```

## 📊 Exemplos de Uso

### Criar Contrato GESTK
```bash
curl -X POST /api/administracao/contratos-gestk/ \
  -H "Authorization: Bearer TOKEN" \
  -H "X-Contabilidade-ID: CONTABILIDADE_ID" \
  -H "Content-Type: application/json" \
  -d '{
    "contabilidade": "CONTABILIDADE_ID",
    "numero_contrato": "GESTK-2024-001",
    "data_inicio": "2024-01-01",
    "plano_servico": "basic",
    "modulos_inclusos": ["contabil", "fiscal"],
    "limites_usuarios": 5,
    "limites_empresas": 10,
    "valor_mensal": 299.90,
    "status": "ativo"
  }'
```

### Criar Acesso de Usuário
```bash
curl -X POST /api/administracao/usuarios-acesso/ \
  -H "Authorization: Bearer TOKEN" \
  -H "X-Contabilidade-ID: CONTABILIDADE_ID" \
  -H "Content-Type: application/json" \
  -d '{
    "usuario": "USUARIO_ID",
    "contabilidade": "CONTABILIDADE_ID",
    "role": "operacional",
    "modulos_acesso": ["contabil", "fiscal"],
    "data_inicio": "2024-01-01",
    "ativo": true
  }'
```

### Criar Plano
```bash
curl -X POST /api/billing/planos/ \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "codigo": "basic",
    "nome": "Plano Básico",
    "descricao": "Plano básico para pequenas contabilidades",
    "preco_mensal": 299.90,
    "preco_anual": 2999.00,
    "desconto_anual": 10.0,
    "modulos_inclusos": ["contabil", "fiscal"],
    "limites": {
      "usuarios": 5,
      "empresas": 10,
      "contratos": 100
    },
    "ativo": true
  }'
```

### Criar Assinatura
```bash
curl -X POST /api/billing/assinaturas/criar-assinatura/ \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "contabilidade": "CONTABILIDADE_ID",
    "plano": "PLANO_ID",
    "data_inicio": "2024-01-01",
    "ciclo_cobranca": "mensal",
    "valor_mensal": 299.90,
    "dia_vencimento": 10,
    "status": "ativa"
  }'
```

## 🚨 Códigos de Erro

### HTTP Status Codes
- **200**: Sucesso
- **201**: Criado com sucesso
- **400**: Dados inválidos
- **401**: Não autenticado
- **403**: Sem permissão
- **404**: Não encontrado
- **500**: Erro interno do servidor

### Códigos de Erro Específicos
- **INVALID_TENANT**: Contabilidade inválida ou sem acesso
- **INSUFFICIENT_PERMISSIONS**: Permissões insuficientes
- **SCOPE_VIOLATION**: Violação de escopo de acesso
- **CONTRACT_EXPIRED**: Contrato expirado
- **BILLING_SUSPENDED**: Cobrança suspensa

## 🔄 Middleware Multi-Tenant

### MultiTenantContextMiddleware
Define automaticamente o contexto de contabilidade baseado em:
1. Header `X-Contabilidade-ID`
2. Query parameter `contabilidade_id`
3. Contabilidade padrão do usuário
4. Última contabilidade acessada

### TenantAuditMiddleware
Registra automaticamente as mudanças de contexto de tenant para auditoria.

## 📈 Monitoramento e Logs

### Logs de Auditoria
- Todas as operações são registradas em `AuditoriaSistema`
- Mudanças de contexto de tenant são auditadas
- Histórico completo de alterações via `django-simple-history`

### Métricas Disponíveis
- Resumos por endpoint (`/resumo/`)
- Estatísticas de uso
- Métricas financeiras
- Indicadores de performance

## 🛠️ Desenvolvimento

### Estrutura de Arquivos
```
apps/
├── core/                    # Modelos base
├── administracao/           # Gestão de contratos e acessos
├── billing/                 # Sistema de faturamento
└── api/
    ├── administracao/       # API de administração
    └── billing/             # API de billing
```

### Testes
```bash
# Executar todos os testes
python manage.py test

# Testes específicos
python manage.py test apps.api.administracao.tests_simple
python manage.py test apps.api.billing.tests
```

### Migrations
```bash
# Criar migrations
python manage.py makemigrations

# Aplicar migrations
python manage.py migrate
```

## 📚 Referências

- [Django REST Framework](https://www.django-rest-framework.org/)
- [Django Simple History](https://django-simple-history.readthedocs.io/)
- [JWT Authentication](https://django-rest-framework-simplejwt.readthedocs.io/)
- [Multi-Tenancy Patterns](https://docs.microsoft.com/en-us/azure/sql-database/saas-tenancy-app-design-patterns)
