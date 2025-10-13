# 📋 ANÁLISE DETALHADA - ETL 06 - LANÇAMENTOS CONTÁBEIS

**Data da Análise:** 13/10/2025  
**Analista:** GitHub Copilot  
**Status:** ⚠️ PROBLEMAS IDENTIFICADOS - CORREÇÕES NECESSÁRIAS

---

## 🎯 OBJETIVO DO ETL

Importar lançamentos contábeis do Sybase (BETHADBA.CTLANCTO) para o PostgreSQL, respeitando:
- ✅ Período: Lançamentos a partir de 01/01/2019
- ✅ Regra dos 5 anos: Manter dados de ex-clientes por 5 anos (obrigação legal)
- ✅ Regra de Ouro: Vincular lançamento à contabilidade correta via histórico de contratos

---

## 🔍 ANÁLISE DA LÓGICA ATUAL

### ✅ **PONTOS POSITIVOS**

1. **Query SQL do Sybase está correta:**
   ```sql
   WHERE l.data_lan >= '2019-01-01'
   ```
   - Importa lançamentos de 01/01/2019 até hoje ✓

2. **Mapa Histórico funcional:**
   - `build_historical_contabilidade_map()` cria um dicionário:
     ```python
     {
       'cnpj_limpo': [
         (data_inicio, data_termino, contabilidade, contrato),
         ...
       ]
     }
     ```
   - Suporta múltiplos contratos por empresa ✓

3. **Validação de período:**
   ```python
   if data_lancamento < date(2019, 1, 1) or data_lancamento > date.today():
       continue  # Ignora lançamentos fora do período
   ```

---

## ❌ **PROBLEMAS CRÍTICOS IDENTIFICADOS**

### 🔴 **PROBLEMA 1: Lógica de "5 Anos" está INCORRETA**

**Código Atual:**
```python
data_limite_5_anos = date(2019, 1, 1)  # ❌ FIXO em 2019!

contrato_nos_ultimos_5_anos = (
    (data_inicio and data_inicio >= data_limite_5_anos) or
    (data_termino and data_termino >= data_limite_5_anos) or
    (data_inicio and data_termino and data_inicio <= data_limite_5_anos <= data_termino)
)
```

**Problema:** 
- A data limite está **FIXA em 2019**, não calculada dinamicamente!
- Em 2025, os "últimos 5 anos" deveriam ser de **01/10/2020 até 13/10/2025**
- Está aceitando contratos de 2019 como se ainda estivessem nos "últimos 5 anos"

**Impacto:**
- ✅ Para lançamentos de 2019-2025: Funciona (está importando tudo)
- ❌ Para lançamentos futuros: A lógica estará errada
- ❌ Conceito: A "obrigação de 5 anos" não está sendo calculada corretamente

**Correção Necessária:**
```python
# Calcular dinamicamente os últimos 5 anos a partir de HOJE
from datetime import date, timedelta
data_atual = date.today()
data_limite_5_anos = data_atual - timedelta(days=5*365)  # ~5 anos atrás

# OU: Se quer desde 2019 fixo (período de importação)
data_limite_importacao = date(2019, 1, 1)
```

---

### 🟡 **PROBLEMA 2: Lógica de seleção de contabilidade é AMBÍGUA**

**Código Atual:**
```python
# Passo 1: Tenta encontrar contrato EXATO para a data do lançamento
if data_inicio <= data_lancamento <= data_termino:
    contabilidade = contab
    break

# Passo 2: Se não encontrou, usa o contrato mais RECENTE dos últimos 5 anos
if not contabilidade and contrato_valido:
    contratos_validos.sort(key=lambda x: x[0] or date.min, reverse=True)
    contabilidade = contratos_validos[0]
```

**Cenário Problemático:**

Empresa X tem 2 contratos:
- **Contrato A** com Contabilidade A: 01/01/2019 a 31/12/2021
- **Contrato B** com Contabilidade B: 01/01/2022 a 31/12/2024

Lançamento de **15/06/2020** (dentro do Contrato A):
- ✅ **Passo 1:** Encontra Contrato A → **CORRETO!**

Lançamento de **15/06/2025** (FORA de qualquer contrato):
- ❌ **Passo 2:** Pega o contrato mais recente (Contrato B) → **ERRADO!**
- 🤔 **Problema:** Lançamento de 2025 não deveria ser importado para nenhum contrato encerrado

**Correção Necessária:**
```python
# Só importar se o lançamento estiver DENTRO do período de um contrato
# OU se for de um ex-cliente dentro dos 5 anos de obrigação legal

# Lógica correta:
# 1. Lançamento dentro do contrato ativo? → Importar no contrato
# 2. Lançamento de ex-cliente (até 5 anos após término)? → Importar no último contrato
# 3. Lançamento sem contrato válido? → NÃO importar
```

---

### 🟡 **PROBLEMA 3: Regra dos "5 Anos" não está clara**

**Interpretação 1:** Importar lançamentos dos últimos 5 anos (2020-2025)
- ❌ Código atual: Está importando desde 2019

**Interpretação 2:** Manter dados de ex-clientes por 5 anos após término do contrato
- ❌ Código atual: Não verifica o término do contrato para aplicar essa regra

**Interpretação 3:** Importar histórico desde 2019 (período fixo de importação)
- ✅ Código atual: Está fazendo isso!

**Necessário:** Definir claramente qual é a regra de negócio:
- **Opção A:** Importar desde 2019 fixo (período de implantação do sistema)
- **Opção B:** Importar lançamentos dentro do período de contratos + 5 anos após término
- **Opção C:** Importar apenas dos últimos 5 anos dinâmicos

---

### 🟢 **PROBLEMA 4: Erro de variável CORRIGIDO**

**Código Anterior:**
```python
'cnpj': cnpj_limpo,  # ❌ Variável inexistente
```

**Correção Aplicada:**
```python
'cnpj': documento_limpo,  # ✅ Variável correta
```

✅ **Status:** CORRIGIDO

---

## 🎯 LÓGICA PROPOSTA (CORRETA)

### **Cenário 1: Lançamento dentro do contrato ativo**
```
Empresa X: Contrato 01/2022 a 12/2024 com Contabilidade A
Lançamento: 15/06/2023

✅ Importar: SIM
📁 Contabilidade: A
📄 Contrato: Contrato de 01/2022
```

### **Cenário 2: Lançamento de ex-cliente (dentro dos 5 anos)**
```
Empresa Y: Contrato 01/2019 a 12/2020 com Contabilidade B
Lançamento: 15/06/2019
Data Atual: 13/10/2025
Tempo desde término: 4 anos e 10 meses

✅ Importar: SIM (dentro dos 5 anos de obrigação)
📁 Contabilidade: B
📄 Contrato: Contrato de 01/2019
```

### **Cenário 3: Lançamento de ex-cliente (após 5 anos)**
```
Empresa Z: Contrato 01/2015 a 12/2017 com Contabilidade C
Lançamento: 15/06/2016
Data Atual: 13/10/2025
Tempo desde término: 7 anos e 10 meses

❌ Importar: NÃO (passou dos 5 anos de obrigação)
```

### **Cenário 4: Empresa com múltiplos contratos**
```
Empresa W:
  - Contrato A: 01/2019 a 12/2021 com Contabilidade X
  - Contrato B: 01/2022 a 12/2024 com Contabilidade Y

Lançamento: 15/06/2020

✅ Importar: SIM
📁 Contabilidade: X (contrato vigente na data do lançamento)
📄 Contrato: Contrato A
```

---

## ✅ RECOMENDAÇÕES DE CORREÇÃO

### **1. Clarificar Regra de Negócio**
Escolher UMA das opções:

**Opção A - Período Fixo (RECOMENDADO para implantação):**
```python
# Importar desde 2019 (data de implantação do novo sistema)
data_limite_importacao = date(2019, 1, 1)
# Importar TODOS os lançamentos desde 2019, respeitando contratos
```

**Opção B - 5 Anos Dinâmicos:**
```python
# Importar apenas últimos 5 anos
data_limite_5_anos = date.today() - timedelta(days=5*365)
# Importar lançamentos dos últimos 5 anos, respeitando contratos
```

### **2. Corrigir Lógica de Seleção de Contabilidade**
```python
# Para cada lançamento:
# 1. Buscar contrato ATIVO na data do lançamento
# 2. Se não houver, buscar ÚLTIMO contrato SE:
#    - O término do contrato foi há menos de 5 anos
#    - O lançamento está entre (data_inicio) e (data_termino + 5 anos)
# 3. Se não atender critérios acima, NÃO importar
```

### **3. Adicionar Logs Detalhados**
```python
# Log para debug:
- Quantos lançamentos têm contrato ativo na data?
- Quantos são de ex-clientes (dentro dos 5 anos)?
- Quantos são rejeitados (sem contrato válido)?
- Quantos têm múltiplos contratos na mesma data?
```

---

## 📊 ESTATÍSTICAS ESPERADAS

Com a lógica atual (importando desde 2019):

**Total de Lançamentos no Sybase:** 7.538.155

**Estimativa de Resultados:**
- ✅ **Com mapeamento correto:** ~70-80% (5.2M - 6M lançamentos)
  - Empresas com contrato ativo na data do lançamento
  - Ex-clientes dentro do período de obrigação legal

- ⚠️ **Sem mapeamento:** ~20-30% (1.5M - 2.3M lançamentos)
  - Empresas sem contrato cadastrado
  - Lançamentos antes do primeiro contrato
  - Lançamentos após término + 5 anos

---

## 🚀 PRÓXIMOS PASSOS

1. **DECISÃO:** Definir qual regra de negócio aplicar (Opção A ou B)
2. **CORREÇÃO:** Ajustar código conforme decisão
3. **TESTE:** Executar com amostra pequena (TOP 10000) para validar
4. **EXECUÇÃO:** Rodar importação completa
5. **VALIDAÇÃO:** Verificar estatísticas e consistência dos dados

---

## ❓ PERGUNTAS PARA O USUÁRIO

1. **Qual regra aplicar?**
   - [ ] Opção A: Importar desde 01/01/2019 (fixo)
   - [ ] Opção B: Importar apenas últimos 5 anos dinâmicos

2. **Lançamentos de ex-clientes:**
   - [ ] Importar se dentro de 5 anos após término do contrato
   - [ ] Importar se tiver qualquer contrato em 2019+
   - [ ] Não importar lançamentos fora do período de contrato

3. **Empresa com múltiplos contratos na mesma data:**
   - [ ] Usar o mais recente (data_inicio)
   - [ ] Usar o primeiro (data_inicio)
   - [ ] Gerar erro/aviso

---

**Aguardando decisão para aplicar correções! 🛠️**
