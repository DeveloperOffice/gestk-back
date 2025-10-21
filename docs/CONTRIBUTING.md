# 🤝 Guia de Contribuição - GESTK Backend

Obrigado por contribuir com o projeto GESTK! Este documento fornece diretrizes para garantir que o código permaneça consistente e de alta qualidade.

---

## 📋 Índice

1. [Antes de Começar](#antes-de-começar)
2. [Configurando o Ambiente](#configurando-o-ambiente)
3. [Padrões de Código](#padrões-de-código)
4. [Estrutura do Projeto](#estrutura-do-projeto)
5. [Desenvolvendo uma Feature](#desenvolvendo-uma-feature)
6. [Testes](#testes)
7. [Documentação](#documentação)
8. [Code Review](#code-review)

---

## 🎯 Antes de Começar

### **Leia a Documentação:**

- ✅ [`README.md`](../README.md) - Visão geral do projeto
- ✅ [`GIT_WORKFLOW.md`](./GIT_WORKFLOW.md) - Fluxo de trabalho Git
- ✅ [`API_DOCUMENTATION.md`](./02_API_INTEGRACAO/) - Documentação da API
- ✅ [`ANALISE_FRONTEND_VS_BACKEND.md`](./ANALISE_FRONTEND_VS_BACKEND.md) - Contrato com frontend

### **Verifique Issues Abertas:**

1. Acesse [GitHub Issues](https://github.com/DeveloperOffice/gestk-back/issues)
2. Procure por issues com label `good first issue` ou `help wanted`
3. Comente na issue que você irá trabalhar nela
4. Aguarde aprovação do mantenedor

### **Comunicação:**

- 💬 Participe das discussões no Slack/Teams
- 🙋 Tire dúvidas antes de começar
- 📢 Comunique bloqueios imediatamente

---

## 🛠️ Configurando o Ambiente

### **1. Clone o Repositório:**

```bash
git clone https://github.com/DeveloperOffice/gestk-back.git
cd gestk-back
```

### **2. Configure o Ambiente Virtual:**

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
```

### **3. Instale Dependências:**

```bash
pip install -r requirements.txt
```

### **4. Configure Variáveis de Ambiente:**

Crie arquivo `.env` na raiz:

```env
# Database
DB_NAME=gestk_db
DB_USER=postgres
DB_PASSWORD=sua_senha
DB_HOST=localhost
DB_PORT=5432

# Django
SECRET_KEY=sua-chave-secreta-aqui
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# JWT
JWT_SECRET_KEY=sua-chave-jwt-aqui
```

### **5. Execute Migrations:**

```bash
python manage.py migrate
```

### **6. Crie Superuser (opcional):**

```bash
python manage.py createsuperuser
```

### **7. Inicie o Servidor:**

```bash
python manage.py runserver
```

Acesse: http://127.0.0.1:8000/admin/

---

## 📝 Padrões de Código

### **Python/Django:**

#### **PEP 8 - Style Guide**

```python
# ✅ BOM
class ClienteViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gerenciamento de clientes.
    
    Permite operações CRUD completas e filtros avançados.
    """
    queryset = Cliente.objects.all()
    serializer_class = ClienteSerializer
    permission_classes = [IsAuthenticated]
    
    def list(self, request, *args, **kwargs):
        """Lista clientes com filtros."""
        usuario = request.user
        
        if usuario.is_superuser:
            logger.info(f"[CLIENTES] Superuser '{usuario.username}' listando todos")
            queryset = Cliente.objects.all()
        else:
            logger.info(f"[CLIENTES] Usuário '{usuario.username}' listando da contabilidade")
            queryset = Cliente.objects.filter(contabilidade=usuario.contabilidade)
        
        return Response(self.serializer_class(queryset, many=True).data)


# ❌ RUIM
class ClienteViewSet(viewsets.ModelViewSet):
    queryset=Cliente.objects.all()
    serializer_class=ClienteSerializer
    def list(self,request,*args,**kwargs):
        u=request.user
        if u.is_superuser:
            q=Cliente.objects.all()
        else:
            q=Cliente.objects.filter(contabilidade=u.contabilidade)
        return Response(self.serializer_class(q,many=True).data)
```

#### **Nomenclatura:**

```python
# Classes: PascalCase
class CarteiraDeClientesViewSet(viewsets.ViewSet):
    pass

# Funções/Métodos: snake_case
def calcular_total_clientes(contabilidade):
    pass

# Constantes: UPPER_SNAKE_CASE
MAX_CLIENTES_POR_PAGINA = 100

# Variáveis: snake_case
total_clientes = 0
usuario_atual = request.user
```

#### **Imports:**

```python
# Ordem:
# 1. Bibliotecas padrão Python
import os
import sys
from datetime import datetime

# 2. Bibliotecas de terceiros
import pandas as pd
from django.db import models
from rest_framework import viewsets
from rest_framework.decorators import action

# 3. Imports locais do projeto
from apps.core.models import Usuario
from apps.pessoas.models import Cliente
from .serializers import ClienteSerializer
```

#### **Lógica de Superuser (OBRIGATÓRIO):**

```python
# ✅ PADRÃO OBRIGATÓRIO para todos os endpoints
def meu_endpoint(self, request):
    """Endpoint com suporte a superuser."""
    usuario = request.user
    
    # 1. Verificar se é superuser
    if usuario.is_superuser:
        logger.info(f"[MODULO] ✅ Superuser '{usuario.username}' acessando TODOS os dados")
        queryset = Modelo.objects.all()
    else:
        # 2. Verificar se usuário tem contabilidade
        if not hasattr(usuario, 'contabilidade') or not usuario.contabilidade:
            logger.error(f"[MODULO] ❌ Usuário '{usuario.username}' sem contabilidade")
            return Response(
                {"error": "Usuário não possui contabilidade associada"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        contabilidade = usuario.contabilidade
        logger.info(f"[MODULO] ✅ Usuário '{usuario.username}' - Contabilidade: {contabilidade.razao_social}")
        queryset = Modelo.objects.filter(contabilidade=contabilidade)
    
    # 3. Processar queryset
    # ... resto da lógica
```

#### **Logging (OBRIGATÓRIO):**

```python
import logging
logger = logging.getLogger(__name__)

# Use prefixos para facilitar debug
logger.info(f"[CARTEIRA] Endpoint /clientes/ acessado por {usuario.username}")
logger.warning(f"[CARTEIRA] ⚠️ Filtro retornou 0 resultados")
logger.error(f"[CARTEIRA] ❌ Erro ao processar dados: {str(e)}")
logger.debug(f"[CARTEIRA] Query executada: {queryset.query}")
```

---

## 📁 Estrutura do Projeto

```
gestk-back/
├── apps/
│   ├── api/                    # Endpoints da API
│   │   ├── gestao/            # Gestão (carteira, clientes)
│   │   ├── dashboards/        # Dashboards analíticos
│   │   ├── auth/              # Autenticação e autorização
│   │   └── shared/            # Componentes compartilhados
│   ├── core/                  # Modelos core (Usuario, etc)
│   ├── pessoas/               # Pessoas (física, jurídica)
│   ├── contabil/              # Módulo contábil
│   ├── fiscal/                # Módulo fiscal
│   └── funcionarios/          # RH e funcionários
├── docs/                      # Documentação
├── gestk/                     # Configurações Django
├── scripts_debug/             # Scripts auxiliares
└── tests/                     # Testes automatizados
```

### **Onde Adicionar Código:**

| O Que | Onde |
|-------|------|
| Novo endpoint de dashboard | `apps/api/dashboards/views.py` |
| Novo endpoint de carteira | `apps/api/gestao/carteira/views.py` |
| Novo modelo | `apps/[modulo]/models.py` |
| Novo serializer | `apps/api/[modulo]/serializers.py` |
| Nova URL | `apps/api/[modulo]/urls.py` |
| Testes | `tests/test_[modulo].py` |
| Script de debug | `scripts_debug/nome_script.py` |

---

## 🚀 Desenvolvendo uma Feature

### **1. Crie a Branch:**

```bash
git checkout Development
git pull origin Development
git checkout -b feature/dashboard-demografico
```

### **2. Desenvolva com Commits Frequentes:**

```bash
# Commit 1: Models
git add apps/dashboards/models.py
git commit -m "feat(dashboard): Adiciona modelo DemograficoKPI"

# Commit 2: Serializers
git add apps/api/dashboards/serializers.py
git commit -m "feat(dashboard): Adiciona serializer DemograficoKPISerializer"

# Commit 3: Views
git add apps/api/dashboards/views.py
git commit -m "feat(dashboard): Implementa endpoint /demografico/kpis/"

# Commit 4: URLs
git add apps/api/dashboards/urls.py
git commit -m "feat(dashboard): Registra rotas de dashboard demográfico"

# Commit 5: Tests
git add tests/test_dashboard_demografico.py
git commit -m "test(dashboard): Adiciona testes para endpoint de KPIs"
```

### **3. Teste Localmente:**

```bash
# Inicie o servidor
python manage.py runserver

# Teste no Postman ou curl
curl -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"username": "testuser", "password": "senha123"}'

# Use o token
curl -X GET http://localhost:8000/api/dashboards/demografico/kpis/ \
  -H "Authorization: Bearer SEU_TOKEN_AQUI"
```

### **4. Verifique Logs:**

```bash
# Terminal do servidor deve mostrar:
[DASHBOARD] Requisição recebida de usuário: testuser
[DASHBOARD] ✅ Usuário 'testuser' - Contabilidade: Contabilidade ABC
[DASHBOARD] 📊 Total de funcionários encontrados: 150
```

### **5. Push e PR:**

```bash
git push -u origin feature/dashboard-demografico
# Criar Pull Request no GitHub
```

---

## 🧪 Testes

### **Estrutura de Testes:**

```python
# tests/test_carteira.py
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from apps.core.models import Usuario, Contabilidade
from apps.pessoas.models import Contrato

class CarteiraTestCase(TestCase):
    """Testes para endpoints de carteira."""
    
    def setUp(self):
        """Configuração inicial para cada teste."""
        self.client = APIClient()
        
        # Criar contabilidade
        self.contabilidade = Contabilidade.objects.create(
            razao_social="Contabilidade Teste",
            cnpj="12345678000190"
        )
        
        # Criar usuário normal
        self.usuario = Usuario.objects.create_user(
            username="testuser",
            password="senha123",
            contabilidade=self.contabilidade
        )
        
        # Criar superuser
        self.superuser = Usuario.objects.create_superuser(
            username="admin",
            password="admin123"
        )
        
        # Criar contratos
        for i in range(10):
            Contrato.objects.create(
                contabilidade=self.contabilidade,
                ativo=True
            )
    
    def test_usuario_normal_ve_apenas_sua_contabilidade(self):
        """Usuário normal deve ver apenas contratos da sua contabilidade."""
        # Login
        self.client.force_authenticate(user=self.usuario)
        
        # Request
        response = self.client.get('/api/gestao/carteira/resumo/')
        
        # Assertions
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['summary']['total_clientes'], 10)
    
    def test_superuser_ve_todos_contratos(self):
        """Superuser deve ver todos os contratos do sistema."""
        # Criar contratos de outra contabilidade
        outra_contabilidade = Contabilidade.objects.create(
            razao_social="Outra Contabilidade",
            cnpj="98765432000100"
        )
        for i in range(5):
            Contrato.objects.create(
                contabilidade=outra_contabilidade,
                ativo=True
            )
        
        # Login como superuser
        self.client.force_authenticate(user=self.superuser)
        
        # Request
        response = self.client.get('/api/gestao/carteira/resumo/')
        
        # Assertions
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['summary']['total_clientes'], 15)  # 10 + 5
```

### **Executar Testes:**

```bash
# Todos os testes
python manage.py test

# Teste específico
python manage.py test tests.test_carteira

# Com coverage
pip install coverage
coverage run --source='.' manage.py test
coverage report
coverage html
```

---

## 📚 Documentação

### **Docstrings (OBRIGATÓRIO):**

```python
def calcular_turnover(contabilidade, mes_inicio, mes_fim):
    """
    Calcula taxa de turnover para uma contabilidade em período específico.
    
    Args:
        contabilidade (Contabilidade): Instância da contabilidade.
        mes_inicio (date): Data de início do período.
        mes_fim (date): Data de fim do período.
    
    Returns:
        dict: Dicionário contendo:
            - turnover_rate (float): Taxa de turnover em percentual.
            - admissoes (int): Total de admissões no período.
            - desligamentos (int): Total de desligamentos no período.
    
    Raises:
        ValueError: Se mes_inicio > mes_fim.
    
    Example:
        >>> turnover = calcular_turnover(contabilidade, date(2024, 1, 1), date(2024, 12, 31))
        >>> print(turnover['turnover_rate'])
        15.5
    """
    if mes_inicio > mes_fim:
        raise ValueError("Data inicial deve ser menor que data final")
    
    # ... lógica
```

### **Comentários:**

```python
# ✅ BOM: Explica o "porquê"
# Usamos select_related para evitar N+1 queries ao acessar contabilidade
contratos = Contrato.objects.select_related('contabilidade').all()

# Multiplicamos por 100 para converter para percentual
percentual_ativo = (clientes_ativos / total_clientes) * 100

# ❌ RUIM: Explica o "o quê" (óbvio)
# Soma total de clientes
total = clientes.count()
```

---

## 👀 Code Review

### **Checklist do Revisor:**

#### **Funcionalidade:**
- [ ] O código faz o que se propõe?
- [ ] Não introduz bugs?
- [ ] Trata casos extremos (edge cases)?

#### **Qualidade:**
- [ ] Código limpo e legível?
- [ ] Nomes descritivos?
- [ ] Funções pequenas e focadas?
- [ ] Sem duplicação de código?

#### **Padrões do Projeto:**
- [ ] Segue PEP 8?
- [ ] Lógica de superuser implementada?
- [ ] Logs apropriados adicionados?
- [ ] Docstrings presentes?

#### **Segurança:**
- [ ] Validação de entrada?
- [ ] Permissões corretas?
- [ ] Sem dados sensíveis expostos?

#### **Performance:**
- [ ] Queries otimizadas?
- [ ] Sem N+1 problems?
- [ ] Usa índices quando necessário?

### **Como Comentar:**

```markdown
# ✅ Aprovação
LGTM! Código está limpo e bem testado. 🚀

# 💡 Sugestão
Linha 45: Considere usar `select_related('contabilidade')` para otimizar a query.

# ⚠️ Problema Menor
Linha 78: Faltou adicionar log de erro aqui.

# 🚫 Bloqueante
Linha 120: Esta query pode causar timeout com muitos dados. 
Por favor, adicione paginação.
```

---

## 🚫 O Que NÃO Fazer

### **❌ Não Commitar:**
- Arquivos `.pyc`, `__pycache__/`
- Arquivos `.env` com credenciais
- Arquivos de IDE (`.vscode/`, `.idea/`)
- Arquivos de backup (`*.bak`, `*~`)
- Migrations desnecessárias

### **❌ Não Push Direto:**
- Nunca faça push direto em `main` ou `Development`
- Sempre use Pull Requests
- Aguarde code review

### **❌ Não Ignore Erros:**
```python
# ❌ NUNCA FAÇA ISSO
try:
    # código
except:
    pass
```

### **❌ Não Use Hardcode:**
```python
# ❌ RUIM
DATABASE_PASSWORD = "senha123"
API_KEY = "abc123xyz"

# ✅ BOM
DATABASE_PASSWORD = os.getenv('DB_PASSWORD')
API_KEY = config('API_KEY')
```

---

## ✅ Boas Práticas

### **✅ Use Type Hints:**
```python
from typing import List, Dict, Optional

def buscar_clientes(contabilidade_id: int) -> List[Dict[str, any]]:
    """Busca clientes de uma contabilidade."""
    pass
```

### **✅ Use Context Managers:**
```python
# ✅ BOM
with open('arquivo.txt', 'r') as f:
    conteudo = f.read()

# ❌ RUIM
f = open('arquivo.txt', 'r')
conteudo = f.read()
f.close()
```

### **✅ Use List Comprehensions:**
```python
# ✅ BOM
numeros_pares = [x for x in range(10) if x % 2 == 0]

# ❌ RUIM
numeros_pares = []
for x in range(10):
    if x % 2 == 0:
        numeros_pares.append(x)
```

---

## 📞 Precisa de Ajuda?

- 📖 Leia a documentação primeiro
- 💬 Pergunte no canal do Slack/Teams
- 👨‍💻 Consulte o tech lead
- 🐛 Abra uma issue no GitHub

---

**Obrigado por contribuir! 🙏**

Sua colaboração torna o GESTK melhor para todos! 🚀
