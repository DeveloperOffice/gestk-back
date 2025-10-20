# 📊 ANÁLISE COMPLETA DA ETL 07 - NOTAS FISCAIS

## 🎯 **VISÃO GERAL**

A ETL 07 é responsável por importar **Notas Fiscais** do sistema Sybase para o PostgreSQL, incluindo:
- **Notas de Entrada** (produtos comprados)
- **Notas de Saída** (produtos vendidos) 
- **Notas de Serviço** (serviços prestados)

---

## 🏗️ **ARQUITETURA E FLUXO DE DADOS**

### **1. CONFIGURAÇÃO INICIAL**
```python
# Configurações de Performance ULTRA OTIMIZADAS v2
CPU_CORES = multiprocessing.cpu_count()
BATCH_SIZE_OPTIMIZED = 1000  # Batch size para processamento
MEMORY_CHUNK_SIZE = 10000    # 10k registros por chunk
PARALLEL_WORKERS = min(CPU_CORES, 2)  # Workers paralelos (limitado a 2)
CPU_USAGE_LIMIT = 0.5  # 50% CPU
```

**Análise**: Configuração conservadora para evitar travamentos, mas pode ser otimizada.

### **2. MAPEAMENTO DE CONTABILIDADES (REGRA DE OURO)**
```python
def build_historical_contabilidade_map(self):
    # Mapeia CNPJ/CPF -> Contrato -> Contabilidade
    # Baseado em datas de início/fim dos contratos
```

**Lógica**: 
- Busca contratos ativos na data da nota fiscal
- Se não encontrar, busca ex-clientes válidos (< 5 anos)
- Ordena por data de término (mais recente primeiro)

---

## 🔍 **ANÁLISE DETALHADA DA QUERY SQL**

### **QUERY PRINCIPAL (Linhas 356-461)**

A query é um **UNION ALL** de 3 consultas:

#### **1. NOTAS DE ENTRADA (Linhas 358-389)**
```sql
SELECT
    1 as TIPO_DOC,
    EFMVEPRO.CODI_EMP as CODIGO_EMPRESA,
    EFENTRADAS.NUME_ENT as NUM_DOCUMENTO,
    -- ... outros campos ...
    GEEMPRE.CGCE_EMP AS CNPJ_EMPRESA
FROM BETHADBA.EFMVEPRO
INNER JOIN BETHADBA.EFENTRADAS ON EFMVEPRO.CODI_ENT = EFENTRADAS.CODI_ENT
INNER JOIN BETHADBA.EFFORNECE ON EFENTRADAS.CODI_FOR = EFFORNECE.CODI_FOR
INNER JOIN BETHADBA.EFPRODUTOS ON EFMVEPRO.CODI_PDI = EFPRODUTOS.CODI_PDI
LEFT JOIN BETHADBA.GEEMPRE ON EFMVEPRO.CODI_EMP = GEEMPRE.CODI_EMP
WHERE EFENTRADAS.DENT_ENT >= '2019-01-01'
AND EFENTRADAS.CHAVE_NFE_ENT IS NOT NULL
AND EFENTRADAS.CHAVE_NFE_ENT <> ''
```

#### **2. NOTAS DE SAÍDA (Linhas 394-425)**
```sql
SELECT
    2 as TIPO_DOC,
    EFMVSPRO.CODI_EMP as CODIGO_EMPRESA,
    EFSAIDAS.NUME_SAI as NUM_DOCUMENTO,
    -- ... outros campos ...
    GEEMPRE.CGCE_EMP AS CNPJ_EMPRESA
FROM BETHADBA.EFMVSPRO
INNER JOIN BETHADBA.EFSAIDAS ON EFMVSPRO.CODI_SAI = EFSAIDAS.CODI_SAI
INNER JOIN BETHADBA.EFCLIENTES ON EFSAIDAS.CODI_CLI = EFCLIENTES.CODI_CLI
INNER JOIN BETHADBA.EFPRODUTOS ON EFMVSPRO.CODI_PDI = EFPRODUTOS.CODI_PDI
LEFT JOIN BETHADBA.GEEMPRE ON EFMVSPRO.CODI_EMP = GEEMPRE.CODI_EMP
WHERE EFSAIDAS.DSAI_SAI >= '2019-01-01'
AND EFSAIDAS.CHAVE_NFE_SAI IS NOT NULL
AND EFSAIDAS.CHAVE_NFE_SAI <> ''
```

#### **3. NOTAS DE SERVIÇO (Linhas 430-460)**
```sql
SELECT
    3 as TIPO_DOC,
    EFSERVICOS.CODI_EMP as CODIGO_EMPRESA,
    EFSERVICOS.NUME_SER as NUM_DOCUMENTO,
    -- ... outros campos ...
    GEEMPRE.CGCE_EMP AS CNPJ_EMPRESA
FROM BETHADBA.EFSERVICOS
INNER JOIN BETHADBA.EFCLIENTES ON EFSERVICOS.CODI_CLI = EFCLIENTES.CODI_CLI
LEFT JOIN BETHADBA.GEEMPRE ON EFSERVICOS.CODI_EMP = GEEMPRE.CODI_EMP
WHERE EFSERVICOS.DSER_SER >= '2019-01-01'
AND EFSERVICOS.CHAVE_ELETRONICA IS NOT NULL
AND EFSERVICOS.CHAVE_ELETRONICA <> ''
```

---

## ⚠️ **PROBLEMAS IDENTIFICADOS**

### **1. PROBLEMA CRÍTICO: NOMES DE CAMPOS INCORRETOS**

#### **Notas de Entrada:**
- ❌ `EFENTRADAS.NUME_ENT` → Deveria ser `EFENTRADAS.CODI_ENT`
- ❌ `EFENTRADAS.DATA_ENTRADA` → Deveria ser `EFENTRADAS.DATA_ENTRADA` (OK)

#### **Notas de Saída:**
- ❌ `EFSAIDAS.NUME_SAI` → Deveria ser `EFSAIDAS.NUME_SAI` (OK)
- ❌ `EFSAIDAS.DATA_SAIDA` → Deveria ser `EFSAIDAS.DATA_SAIDA` (OK)

#### **Notas de Serviço:**
- ❌ `EFSERVICOS.NUME_SER` → Deveria ser `EFSERVICOS.NUME_SER` (OK)
- ❌ `EFSERVICOS.DATA_SERVICO` → Deveria ser `EFSERVICOS.DDOC_SER`

### **2. PROBLEMA DE PERFORMANCE: QUERY FALLBACK**
```python
# Linha 481-496: Query de fallback com TOP 100000
query_fallback = """
SELECT TOP 100000
    1 as TIPO_DOC, EFMVEPRO.CODI_EMP, EFENTRADAS.NUME_ENT, ...
"""
```
**Problema**: Limita a importação a apenas 100k registros quando deveria importar 700k+.

### **3. PROBLEMA DE IDEMPOTÊNCIA**
A ETL não implementa idempotência correta:
- Não verifica se a nota já existe antes de criar
- Sempre tenta criar/atualizar, causando erros de chave duplicada

### **4. PROBLEMA DE MAPEAMENTO DE CAMPOS**
```python
# Linha 203: Usa CNPJ_EMPRESA da query (posição 22)
cnpj_empresa = self.limpar_documento(str(row[22] or ''))
```
**Problema**: A posição 22 pode estar incorreta dependendo da query.

---

## 🔧 **PROCESSAMENTO DE DADOS**

### **1. PROCESSAMENTO EM CHUNKS (Linha 164-336)**
```python
def processar_chunk_ultra_otimizado(self, chunk_data, historical_map):
    # 1. Preparar dados e chaves para busca em massa
    # 2. Processar Pessoas (Parceiros) em Massa
    # 3. Buscar Notas Fiscais existentes em UMA ÚNICA QUERY
    # 4. Iterar em memória, separando notas para criar e atualizar
    # 5. Executar Bulk Create para NOVAS notas
    # 6. Executar Bulk Update para notas EXISTENTES
    # 7. Criar ITENS em massa para TODAS as notas
```

### **2. PROCESSAMENTO DE PESSOAS (Linha 114-162)**
```python
def processar_pessoas_em_massa(self, pessoas_para_processar):
    # Busca Pessoas Jurídicas e Físicas existentes
    # Cria/atualiza em massa usando bulk_create/bulk_update
    # Repopula cache em massa
```

---

## 📊 **ESTATÍSTICAS E MONITORAMENTO**

### **Métricas Coletadas:**
- `notas_criadas`: Notas fiscais criadas
- `notas_atualizadas`: Notas fiscais atualizadas  
- `itens_criados`: Itens de nota fiscal criados
- `sem_mapeamento`: Registros sem contabilidade mapeada

### **Monitoramento de Recursos:**
- CPU usage
- RAM usage
- Tempo de processamento
- Velocidade (registros/segundo)

---

## 🚨 **PROBLEMAS CRÍTICOS IDENTIFICADOS**

### **1. LIMITAÇÃO DE REGISTROS**
- Query fallback limita a 100k registros
- Deveria processar 700k+ registros

### **2. CAMPOS INCORRETOS**
- Nomes de campos podem estar incorretos
- Posições de array podem estar erradas

### **3. FALTA DE IDEMPOTÊNCIA**
- Não verifica duplicatas corretamente
- Causa erros de chave duplicada

### **4. MAPEAMENTO DE CONTABILIDADE**
- Usa `build_historical_contabilidade_map()` (correto)
- Mas pode ter problemas na lógica de busca

---

## 🎯 **RECOMENDAÇÕES PARA CORREÇÃO**

### **1. CORRIGIR QUERY PRINCIPAL**
- Verificar nomes corretos dos campos no Sybase
- Remover limitação de 100k registros
- Testar query individualmente

### **2. IMPLEMENTAR IDEMPOTÊNCIA**
- Verificar se nota já existe antes de criar
- Só atualizar se dados mudaram
- Pular registros já processados

### **3. CORRIGIR MAPEAMENTO DE CAMPOS**
- Verificar posições corretas dos campos
- Adicionar validação de dados

### **4. OTIMIZAR PERFORMANCE**
- Aumentar chunk size se memória permitir
- Melhorar paralelismo
- Implementar cache mais eficiente

---

## 📈 **PRÓXIMOS PASSOS**

1. **Verificar estrutura real das tabelas Sybase**
2. **Corrigir query principal**
3. **Implementar idempotência correta**
4. **Testar com pequeno volume primeiro**
5. **Executar importação completa**

---

## 🔍 **CONCLUSÃO**

A ETL 07 v2 tem uma arquitetura sólida com otimizações avançadas, mas possui **problemas críticos** que impedem o funcionamento correto:

1. **Query com campos incorretos**
2. **Limitação artificial de registros**
3. **Falta de idempotência**
4. **Possível mapeamento incorreto de campos**

**Recomendação**: Corrigir esses problemas antes de executar a importação completa.
