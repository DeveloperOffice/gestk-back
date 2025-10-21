# 👥 Divisão de Trabalho - Time Backend GESTK

Este documento organiza a divisão de tarefas entre os desenvolvedores do time backend.

**Última atualização:** 21/10/2025

---

## 📊 Status Geral do Projeto

### **Progresso de Implementação:**

| Módulo | Total Endpoints | Implementados | Pendentes | % Completo |
|--------|-----------------|---------------|-----------|------------|
| **Carteira** | 8 | 3 | 5 | 37% |
| **Dashboards** | 20+ | 0 | 20+ | 0% |
| **Gestão** | 10 | 3 | 7 | 30% |
| **Auth** | 5 | 5 | 0 | 100% ✅ |
| **TOTAL** | **43+** | **11** | **32+** | **26%** |

---

## 👤 DEV 1 - Dashboards Demográfico e Organizacional

### **Branch:** `feature/dashboard-demografico-organizacional`

### **Responsabilidades:**

#### **1. Dashboard Demográfico** (Prioridade: 🔴 ALTA)

**Endpoints a Implementar:**

```python
# apps/api/dashboards/views.py

@action(detail=False, methods=['get'])
def demografico_kpis(self, request):
    """
    GET /api/dashboards/demografico/kpis/
    
    Retorna KPIs principais do dashboard demográfico.
    """
    pass

@action(detail=False, methods=['get'])
def demografico_turnover(self, request):
    """
    GET /api/dashboards/demografico/turnover/
    
    Retorna evolução mensal do turnover.
    """
    pass

@action(detail=False, methods=['get'])
def demografico_distribuicao_etaria(self, request):
    """
    GET /api/dashboards/demografico/distribuicao-etaria/
    
    Retorna distribuição de funcionários por faixa etária.
    """
    pass

@action(detail=False, methods=['get'])
def demografico_distribuicao_genero(self, request):
    """
    GET /api/dashboards/demografico/distribuicao-genero/
    
    Retorna distribuição de funcionários por gênero.
    """
    pass

@action(detail=False, methods=['get'])
def demografico_distribuicao_escolaridade(self, request):
    """
    GET /api/dashboards/demografico/distribuicao-escolaridade/
    
    Retorna distribuição de funcionários por escolaridade.
    """
    pass
```

#### **2. Dashboard Organizacional** (Prioridade: 🟡 MÉDIA)

```python
@action(detail=False, methods=['get'])
def organizacional_hierarquia(self, request):
    """
    GET /api/dashboards/organizacional/hierarquia/
    
    Retorna estrutura hierárquica da empresa.
    """
    pass

@action(detail=False, methods=['get'])
def organizacional_departamentos(self, request):
    """
    GET /api/dashboards/organizacional/departamentos/
    
    Retorna lista de departamentos com estatísticas.
    """
    pass

@action(detail=False, methods=['get'])
def organizacional_cargos(self, request):
    """
    GET /api/dashboards/organizacional/cargos/
    
    Retorna distribuição de funcionários por cargo.
    """
    pass
```

### **Modelos Necessários:**

```python
# apps/funcionarios/models.py
- Funcionario
- Cargo
- Departamento
- Movimentacao (admissões/demissões)
```

### **Estrutura de Response Esperada:**

```json
// GET /api/dashboards/demografico/kpis/
{
  "total_funcionarios": 1250,
  "total_ativos": 1180,
  "total_inativos": 70,
  "taxa_turnover": 5.2,
  "admissoes_mes": 15,
  "demissoes_mes": 8,
  "media_idade": 32.5,
  "percentual_masculino": 62.3,
  "percentual_feminino": 37.7
}
```

### **Estimativa:** 16-20 horas

---

## 👤 DEV 2 - Dashboards Fiscal e Contábil

### **Branch:** `feature/dashboard-fiscal-contabil`

### **Responsabilidades:**

#### **1. Dashboard Fiscal** (Prioridade: 🔴 ALTA)

**Endpoints a Implementar:**

```python
# apps/api/dashboards/views.py

@action(detail=False, methods=['get'])
def fiscal_kpis(self, request):
    """
    GET /api/dashboards/fiscal/kpis/
    
    Retorna KPIs principais do dashboard fiscal.
    """
    pass

@action(detail=False, methods=['get'])
def fiscal_resumo_tipo(self, request):
    """
    GET /api/dashboards/fiscal/resumo-tipo/
    
    Retorna resumo de notas fiscais por tipo.
    """
    pass

@action(detail=False, methods=['get'])
def fiscal_top_clientes(self, request):
    """
    GET /api/dashboards/fiscal/top-clientes/
    
    Retorna top clientes por faturamento.
    """
    pass

@action(detail=False, methods=['get'])
def fiscal_produtos(self, request):
    """
    GET /api/dashboards/fiscal/produtos/
    
    Retorna produtos mais vendidos.
    """
    pass

@action(detail=False, methods=['get'])
def fiscal_distribuicao_uf(self, request):
    """
    GET /api/dashboards/fiscal/distribuicao-uf/
    
    Retorna distribuição de notas por UF.
    """
    pass
```

#### **2. Dashboard Contábil** (Prioridade: 🟡 MÉDIA)

```python
@action(detail=False, methods=['get'])
def contabil_kpis(self, request):
    """
    GET /api/dashboards/contabil/kpis/
    
    Retorna KPIs principais do dashboard contábil.
    """
    pass

@action(detail=False, methods=['get'])
def contabil_balancete(self, request):
    """
    GET /api/dashboards/contabil/balancete/
    
    Retorna balancete resumido.
    """
    pass

@action(detail=False, methods=['get'])
def contabil_fluxo_caixa(self, request):
    """
    GET /api/dashboards/contabil/fluxo-caixa/
    
    Retorna evolução do fluxo de caixa.
    """
    pass
```

### **Modelos Necessários:**

```python
# apps/fiscal/models.py
- NotaFiscal
- ItemNotaFiscal
- Produto

# apps/contabil/models.py
- LancamentoContabil
- ContaContabil
- PlanoDeContas
```

### **Estrutura de Response Esperada:**

```json
// GET /api/dashboards/fiscal/kpis/
{
  "total_notas": 5420,
  "valor_total": 12500000.00,
  "ticket_medio": 2305.17,
  "total_nfe": 4200,
  "total_nfse": 1220,
  "crescimento_mes": 8.5
}
```

### **Estimativa:** 16-20 horas

---

## 👤 DEV 3 - Endpoints de Carteira (CRÍTICO)

### **Branch:** `feature/endpoints-carteira`

### **Responsabilidades:**

#### **Endpoints Críticos para o Frontend** (Prioridade: 🔴 CRÍTICA)

```python
# apps/api/gestao/carteira/views.py

@action(detail=False, methods=['get'])
def resumo(self, request):
    """
    GET /api/gestao/carteira/resumo/
    
    NOVO - Retorna apenas resumo/estatísticas.
    """
    pass

@action(detail=False, methods=['get'], url_path='regime-tributario')
def regime_tributario(self, request):
    """
    GET /api/gestao/carteira/regime-tributario/
    
    NOVO - Distribuição por regime tributário.
    """
    pass

@action(detail=False, methods=['get'], url_path='ramo-atividade')
def ramo_atividade(self, request):
    """
    GET /api/gestao/carteira/ramo-atividade/
    
    NOVO - Distribuição por ramo de atividade.
    """
    pass

@action(detail=False, methods=['get'], url_path='aniversarios-parceria')
def aniversarios_parceria(self, request):
    """
    GET /api/gestao/carteira/aniversarios-parceria/
    
    NOVO - Aniversários de contratos próximos.
    """
    pass

@action(detail=False, methods=['get'], url_path='socios-aniversariantes')
def socios_aniversariantes(self, request):
    """
    GET /api/gestao/carteira/socios-aniversariantes/
    
    NOVO - Aniversários de sócios próximos.
    """
    pass
```

#### **Ajustes em Endpoints Existentes:**

```python
# AJUSTAR: clientes() - Adicionar paginação e lista completa
# AJUSTAR: evolucao() - Adicionar campos faltantes (novos_clientes, inativos)
# AJUSTAR: categorias() - Revisar estrutura conforme frontend
```

### **Modelos Necessários:**

```python
# apps/pessoas/models.py
- PessoaJuridica (verificar campos: regime_tributario, ramo_atividade)
- Contrato
- Socio
```

### **Estrutura de Response Esperada:**

```json
// GET /api/gestao/carteira/resumo/
{
  "summary": {
    "total_clientes": 2186,
    "clientes_ativos": 1550,
    "clientes_inativos": 636,
    "clientes_novos": 6,
    "clientes_sem_movimentacao": 0,
    "percentual_ativo": 70.91
  }
}

// GET /api/gestao/carteira/regime-tributario/
[
  {
    "regime": "SIMPLES_NACIONAL",
    "nome": "Simples Nacional",
    "quantidade": 1100,
    "percentual": 50.32
  },
  {
    "regime": "LUCRO_PRESUMIDO",
    "nome": "Lucro Presumido",
    "quantidade": 700,
    "percentual": 32.05
  }
]
```

### **Estimativa:** 12-16 horas

---

## 👤 TECH LEAD (Wando) - Code Review & Arquitetura

### **Responsabilidades:**

1. **Code Review:**
   - Revisar todos os Pull Requests
   - Garantir padrões de código
   - Verificar implementação de lógica de superuser
   - Validar estruturas de response

2. **Arquitetura:**
   - Refatorar código compartilhado
   - Criar mixins/base classes
   - Otimizar queries complexas
   - Resolver conflitos de merge

3. **Suporte:**
   - Desbloquear desenvolvedores
   - Tirar dúvidas técnicas
   - Ajudar em problemas complexos

4. **Qualidade:**
   - Garantir testes adequados
   - Validar performance
   - Verificar segurança

---

## 📅 Timeline Sugerido

### **Sprint 1 (Semana 1-2):**

**DEV 1:**
- ✅ Dashboard Demográfico KPIs
- ✅ Dashboard Demográfico Turnover
- ✅ Dashboard Demográfico Distribuições (etária, gênero)

**DEV 2:**
- ✅ Dashboard Fiscal KPIs
- ✅ Dashboard Fiscal Resumo por Tipo
- ✅ Dashboard Fiscal Top Clientes

**DEV 3:**
- ✅ Endpoint `/resumo/` (CRÍTICO)
- ✅ Endpoint `/regime-tributario/` (CRÍTICO)
- ✅ Endpoint `/ramo-atividade/` (CRÍTICO)
- ✅ Ajuste endpoint `/clientes/` (adicionar paginação)

### **Sprint 2 (Semana 3-4):**

**DEV 1:**
- ✅ Dashboard Organizacional completo
- ✅ Dashboard Demográfico - features restantes

**DEV 2:**
- ✅ Dashboard Contábil completo
- ✅ Dashboard Fiscal - features restantes

**DEV 3:**
- ✅ Endpoints de aniversários
- ✅ Ajustes finais em carteira
- ✅ Implementar lógica de superuser em endpoints restantes

---

## 🎯 Metas de Qualidade

### **Para Todos os Desenvolvedores:**

#### **Obrigatório:**
- ✅ Implementar lógica de superuser em TODOS os endpoints
- ✅ Adicionar logs informativos (`logger.info`, `logger.error`)
- ✅ Validar entrada de dados
- ✅ Tratar erros adequadamente
- ✅ Testar com usuário normal e superuser

#### **Recomendado:**
- ✅ Adicionar docstrings
- ✅ Otimizar queries (usar `select_related`, `prefetch_related`)
- ✅ Adicionar testes automatizados
- ✅ Documentar estrutura de response

#### **Desejável:**
- ✅ Adicionar paginação (quando aplicável)
- ✅ Adicionar filtros avançados
- ✅ Cache de queries pesadas
- ✅ Métricas de performance

---

## 📞 Comunicação

### **Daily Standup (15min):**
Cada dev compartilha:
- O que fiz ontem?
- O que vou fazer hoje?
- Estou bloqueado em algo?

### **Code Review:**
- PRs devem ser revisados em até 24h
- Comentários devem ser construtivos
- Aprovação de pelo menos 1 reviewer

### **Dúvidas:**
- Slack/Teams: Dúvidas rápidas
- Pair Programming: Problemas complexos
- Tech Lead: Decisões de arquitetura

---

## 📊 Acompanhamento de Progresso

### **Atualizar Diariamente:**

```markdown
## Dev 1 - Progresso
- [x] Dashboard Demográfico KPIs
- [x] Dashboard Demográfico Turnover
- [ ] Dashboard Demográfico Distribuição Etária
- [ ] Dashboard Demográfico Distribuição Gênero
- [ ] Dashboard Organizacional Hierarquia

## Dev 2 - Progresso
- [x] Dashboard Fiscal KPIs
- [ ] Dashboard Fiscal Resumo Tipo
- [ ] Dashboard Fiscal Top Clientes
- [ ] Dashboard Contábil KPIs

## Dev 3 - Progresso
- [x] Endpoint /resumo/
- [x] Endpoint /regime-tributario/
- [ ] Endpoint /ramo-atividade/
- [ ] Endpoint /aniversarios-parceria/
```

---

## 🎓 Recursos de Aprendizado

### **Para Novos Desenvolvedores:**

1. **Leia primeiro:**
   - [`README.md`](../README.md)
   - [`GIT_WORKFLOW.md`](./GIT_WORKFLOW.md)
   - [`CONTRIBUTING.md`](./CONTRIBUTING.md)
   - [`ANALISE_FRONTEND_VS_BACKEND.md`](./ANALISE_FRONTEND_VS_BACKEND.md)

2. **Entenda o código existente:**
   - Estude `apps/api/gestao/carteira/views.py`
   - Veja como superuser foi implementado
   - Observe padrões de logging

3. **Configure ambiente local:**
   - Siga instruções do README
   - Teste endpoints existentes no Postman
   - Execute scripts de debug em `scripts_debug/`

---

**Dúvidas?** Fale com o Tech Lead! 🚀

**Boa sorte, time! Vamos fazer um ótimo trabalho! 💪**
