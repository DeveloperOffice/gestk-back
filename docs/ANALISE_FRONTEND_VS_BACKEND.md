# 🔄 Análise: Frontend vs Backend - Endpoints da Carteira

**Data**: 21/10/2025  
**Análise**: Comparação entre endpoints esperados pelo frontend e implementados no backend

---

## 📊 RESUMO EXECUTIVO

| Status | Quantidade | Descrição |
|--------|-----------|-----------|
| ✅ **Implementado** | 3 | Endpoints funcionando parcialmente |
| ⚠️ **Precisa Ajuste** | 3 | Estrutura diferente do esperado |
| ❌ **Faltando** | 5 | Endpoints não existem |
| **TOTAL** | **11** | Endpoints necessários |

---

## 1️⃣ GET `/api/gestao/carteira/clientes/` - Lista de Clientes

### ✅ STATUS: IMPLEMENTADO (mas estrutura diferente)

### 📥 Frontend Espera:
```json
{
  "count": 2186,
  "next": "http://127.0.0.1:8000/api/gestao/carteira/clientes/?page=2",
  "previous": null,
  "results": [
    {
      "id": "uuid-1",
      "razao_social": "Empresa A LTDA",
      "cnpj": "12.345.678/0001-90",
      "status": "ATIVO",
      "regime_fiscal": "SIMPLES_NACIONAL",
      "data_inicio": "2020-01-15",
      "inadimplente": false
    }
  ],
  "summary": {
    "total_clientes": 2186,
    "clientes_ativos": 1550,
    "clientes_inativos": 636,
    "clientes_novos": 6,
    "clientes_sem_movimentacao": 0,
    "percentual_ativo": 70.91
  }
}
```

### 📤 Backend Retorna:
```json
{
  "summary": {
    "total_clientes": 2186,
    "clientes_ativos": 1550,
    "clientes_inativos": 636,
    "clientes_novos": 0,
    "clientes_sem_movimentacao": 0,
    "percentual_ativo": 70.91
  },
  "results": []  ← VAZIO!
}
```

### ⚠️ PROBLEMAS:
1. ❌ **Falta paginação** (count, next, previous)
2. ❌ **results está vazio** - não retorna lista de clientes
3. ❌ **Faltam dados dos clientes** (razao_social, cnpj, status, etc.)
4. ❌ **Não suporta filtros** (page, page_size, status, regime_fiscal, search)

### 🔧 CORREÇÃO NECESSÁRIA:
```python
# Adicionar ao método clientes():
# 1. Buscar clientes com detalhes
# 2. Implementar paginação
# 3. Implementar filtros
# 4. Retornar lista completa em results
```

---

## 2️⃣ GET `/api/gestao/carteira/resumo/` - Resumo/Estatísticas

### ❌ STATUS: NÃO EXISTE

### 📥 Frontend Espera:
```json
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
```

### 📤 Backend Retorna:
```
404 Not Found
```

### ⚠️ PROBLEMAS:
1. ❌ **Endpoint não existe**
2. ⚠️ **Dados estão em /clientes/ mas frontend espera em /resumo/**

### 🔧 CORREÇÃO NECESSÁRIA:
```python
@action(detail=False, methods=['get'])
def resumo(self, request):
    """
    Endpoint: /api/gestao/carteira/resumo/
    Retorna apenas o summary sem a lista de clientes
    """
    # Copiar lógica de clientes() mas retornar só summary
    return Response({"summary": {...}})
```

### 💡 SOLUÇÃO ALTERNATIVA:
- Frontend pode usar `/clientes/` e pegar só o `summary`
- Mas melhor criar `/resumo/` separado para performance

---

## 3️⃣ GET `/api/gestao/carteira/categorias/` - Categorias

### ⚠️ STATUS: IMPLEMENTADO (mas estrutura diferente)

### 📥 Frontend Espera:
```json
[
  {
    "id": "uuid-1",
    "nome": "Ativos",
    "status": "ativo",
    "quantidade": 1550
  },
  {
    "id": "uuid-2",
    "nome": "Inativos",
    "status": "inativo",
    "quantidade": 636
  }
]
```

### 📤 Backend Retorna:
```json
[
  {
    "contabilidade": {
      "id": "uuid",
      "cnpj": "12345678000190",
      "razao_social": "Contabilidade ABC"
    },
    "categoria": "Simples Nacional",
    "total_clientes": 1100
  }
]
```

### ⚠️ PROBLEMAS:
1. ❌ **Estrutura diferente** (contabilidade vs id/nome)
2. ❌ **Categoriza por regime fiscal** (frontend espera por status: ativo/inativo)
3. ⚠️ **Campo "contabilidade" desnecessário** para frontend

### 🔧 CORREÇÃO NECESSÁRIA:
- Frontend espera categorias de **STATUS** (Ativos/Inativos)
- Backend retorna categorias de **REGIME FISCAL** (Simples/Presumido)
- **São coisas diferentes!**

---

## 4️⃣ GET `/api/gestao/carteira/evolucao/` - Evolução Mensal

### ✅ STATUS: IMPLEMENTADO (mas precisa ajustes)

### 📥 Frontend Espera:
```json
[
  {
    "mes": "jan. de 24",
    "mês": "2024-01",
    "total_clientes": 100,
    "total_clientes_mes": 100,
    "novos_clientes": 5,
    "novos_clientes_mes": 5,
    "clientes_inativos": 2,
    "clientes_inativos_mes": 2
  }
]
```

### 📤 Backend Retorna:
```json
[
  {
    "mes_ano": "2024-10",
    "total_clientes": 1550
  }
]
```

### ⚠️ PROBLEMAS:
1. ❌ **Faltam campos** (mes, novos_clientes, clientes_inativos)
2. ❌ **Formato do mês diferente** ("2024-10" vs "out. de 24")
3. ❌ **Não suporta parâmetro ?meses=12** (fixo em 6)

### 🔧 CORREÇÃO NECESSÁRIA:
```python
# Adicionar:
# - mes (formatado: "jan. de 24")
# - novos_clientes_mes
# - clientes_inativos_mes
# - Suporte a parâmetro ?meses=
```

---

## 5️⃣ GET `/api/gestao/carteira/aniversarios-parceria/` - Aniversários

### ❌ STATUS: NÃO EXISTE

### 📥 Frontend Espera:
```json
[
  {
    "id": "uuid-1",
    "razao_social": "Empresa A LTDA",
    "cnpj": "12.345.678/0001-90",
    "data_aniversario": "2025-01-15",
    "dias_faltando": 86,
    "mes_aniversario": "janeiro"
  }
]
```

### 📤 Backend Retorna:
```
404 Not Found
```

### 🔧 CORREÇÃO NECESSÁRIA:
```python
@action(detail=False, methods=['get'])
def aniversarios_parceria(self, request):
    """
    Retorna clientes que completam aniversário de parceria
    nos próximos X meses (padrão: 12)
    """
    meses = int(request.GET.get('meses', 12))
    # Buscar contratos e calcular aniversário
    # Ordenar por data mais próxima
    return Response([...])
```

---

## 6️⃣ GET `/api/gestao/carteira/socios-aniversariantes/` - Sócios

### ❌ STATUS: NÃO EXISTE

### 📥 Frontend Espera:
```json
[
  {
    "id": "uuid-1",
    "nome_socio": "João Silva",
    "empresa_razao_social": "Empresa A LTDA",
    "empresa_cnpj": "12.345.678/0001-90",
    "data_nascimento": "1980-03-15",
    "dias_faltando": 45,
    "mes_aniversario": "março"
  }
]
```

### 📤 Backend Retorna:
```
404 Not Found
```

### 🔧 CORREÇÃO NECESSÁRIA:
```python
@action(detail=False, methods=['get'])
def socios_aniversariantes(self, request):
    """
    Retorna sócios que fazem aniversário
    nos próximos X meses (padrão: 12)
    """
    meses = int(request.GET.get('meses', 12))
    # Buscar sócios das empresas da carteira
    # Calcular dias até aniversário
    return Response([...])
```

---

## 7️⃣ GET `/api/gestao/carteira/regime-tributario/` - Distribuição por Regime

### ❌ STATUS: NÃO EXISTE

### 📥 Frontend Espera:
```json
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

### 📤 Backend Retorna:
```
404 Not Found
```

### ⚠️ NOTA:
O endpoint `/categorias/` retorna dados similares, mas com estrutura diferente!

### 🔧 CORREÇÃO NECESSÁRIA:
```python
@action(detail=False, methods=['get'], url_path='regime-tributario')
def regime_tributario(self, request):
    """
    Distribuição de clientes por regime tributário
    com percentuais
    """
    # Agrupar por regime_tributario
    # Calcular quantidade e percentual
    return Response([...])
```

---

## 8️⃣ GET `/api/gestao/carteira/ramo-atividade/` - Distribuição por Ramo

### ❌ STATUS: NÃO EXISTE

### 📥 Frontend Espera:
```json
[
  {
    "ramo": "Consultoria",
    "nome": "Consultoria",
    "quantidade": 450,
    "percentual": 20.59
  },
  {
    "ramo": "Tecnologia",
    "nome": "Tecnologia",
    "quantidade": 600,
    "percentual": 27.46
  }
]
```

### 📤 Backend Retorna:
```
404 Not Found
```

### 🔧 CORREÇÃO NECESSÁRIA:
```python
@action(detail=False, methods=['get'], url_path='ramo-atividade')
def ramo_atividade(self, request):
    """
    Distribuição de clientes por ramo de atividade
    com percentuais
    """
    # Agrupar por ramo_atividade
    # Calcular quantidade e percentual
    return Response([...])
```

---

## 📋 TABELA RESUMO: O QUE FALTA IMPLEMENTAR

| # | Endpoint | Status | Prioridade | Estimativa |
|---|----------|--------|------------|------------|
| 1 | `/clientes/` | ⚠️ Ajustar | 🔴 CRÍTICA | 4h |
| 2 | `/resumo/` | ❌ Criar | 🔴 CRÍTICA | 1h |
| 3 | `/categorias/` | ⚠️ Ajustar | 🟡 MÉDIA | 2h |
| 4 | `/evolucao/` | ⚠️ Ajustar | 🔴 ALTA | 2h |
| 5 | `/aniversarios-parceria/` | ❌ Criar | 🟡 MÉDIA | 3h |
| 6 | `/socios-aniversariantes/` | ❌ Criar | 🟡 MÉDIA | 3h |
| 7 | `/regime-tributario/` | ❌ Criar | 🔴 ALTA | 2h |
| 8 | `/ramo-atividade/` | ❌ Criar | 🔴 ALTA | 2h |

**Total Estimado**: ~19 horas de desenvolvimento

---

## 🎯 PLANO DE AÇÃO RECOMENDADO

### **FASE 1: CORREÇÕES CRÍTICAS** (2h)
1. ✅ **Criar `/resumo/`** - Retorna só o summary (PRONTO se copiar de /clientes/)
2. ⚠️ **Ajustar `/clientes/`** - Adicionar paginação e lista de clientes

### **FASE 2: GRÁFICOS PRINCIPAIS** (6h)
3. ✅ **Criar `/regime-tributario/`** - Distribuição por regime
4. ✅ **Criar `/ramo-atividade/`** - Distribuição por ramo
5. ⚠️ **Ajustar `/evolucao/`** - Adicionar campos faltantes

### **FASE 3: FEATURES EXTRAS** (6h)
6. ✅ **Criar `/aniversarios-parceria/`** - Aniversários de contratos
7. ✅ **Criar `/socios-aniversariantes/`** - Aniversários de sócios

### **FASE 4: AJUSTES FINAIS** (2h)
8. ⚠️ **Ajustar `/categorias/`** - Decidir se mantém ou remove
9. ✅ **Adicionar lógica de superuser** em TODOS os novos endpoints
10. ✅ **Testes completos** no Postman

---

## 💾 PRÓXIMOS PASSOS IMEDIATOS

### 1️⃣ **TESTE O ENDPOINT ATUAL** (5 min)
```bash
# Reinicie o servidor
Ctrl + C
python manage.py runserver

# Teste no Postman
GET http://127.0.0.1:8000/api/gestao/carteira/clientes/
Authorization: Bearer SEU_TOKEN
```

### 2️⃣ **CRIE O ENDPOINT /resumo/** (10 min)
É só duplicar a lógica de `/clientes/` mas retornar só o summary

### 3️⃣ **IMPLEMENTE OS GRÁFICOS** (4h)
- `/regime-tributario/`
- `/ramo-atividade/`

Esses são os **mais importantes** para o frontend funcionar!

---

## 🔍 CAMPOS DO MODELO QUE PRECISAMOS

### Modelo `PessoaJuridica`:
- ✅ `razao_social` - Existe
- ✅ `cnpj` - Existe
- ❓ `regime_tributario` - Verificar se existe
- ❓ `ramo_atividade` - Verificar se existe

### Modelo `Contrato`:
- ✅ `contabilidade` - Existe
- ✅ `ativo` - Existe
- ✅ `data_inicio` - Existe
- ❓ `status_cobranca` - Para "inadimplente"

### Modelo `Socio` (se existir):
- ❓ `nome` - Para aniversariantes
- ❓ `data_nascimento` - Para calcular aniversário
- ❓ Relacionamento com PessoaJuridica

---

## 📊 ANÁLISE DO BANCO DE DADOS NECESSÁRIA

Execute este script para verificar os campos disponíveis:
```python
from apps.pessoas.models import PessoaJuridica, Contrato
from django.db import connection

# Verificar campos de PessoaJuridica
print("Campos de PessoaJuridica:")
for field in PessoaJuridica._meta.get_fields():
    print(f"  - {field.name}")

# Verificar campos de Contrato
print("\nCampos de Contrato:")
for field in Contrato._meta.get_fields():
    print(f"  - {field.name}")
```

---

**Conclusão**: O backend tem a estrutura básica, mas precisa de **5 novos endpoints** e **ajustes em 3 existentes** para atender completamente o frontend.

**Prioridade Máxima**:
1. ✅ Criar `/resumo/` 
2. ✅ Criar `/regime-tributario/`
3. ✅ Criar `/ramo-atividade/`

Estes 3 resolverão 80% do problema visual! 🎯
