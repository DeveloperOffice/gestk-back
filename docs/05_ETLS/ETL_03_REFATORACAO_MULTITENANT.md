# ETL 03 - Refatoração Multi-Tenant (CNPJ/CPF como Chave)

## 📋 Resumo das Mudanças

### 1. **Modelo PessoaJuridica - Novos Campos do Sybase**

Foram adicionados **13 novos campos** baseados no mapeamento da tabela `geempre` do Sybase:

| Campo                    | Tipo           | Origem Sybase        | Descrição                          |
|--------------------------|----------------|----------------------|------------------------------------|
| `cnae`                   | CharField(20)  | `cnae_emp`           | CNAE principal da empresa          |
| `cnae_20`                | CharField(20)  | `i_cnae20`           | CNAE 2.0                           |
| `usa_cnae_20`            | BooleanField   | `usa_cnae20`         | Se usa CNAE 2.0                    |
| `situacao`               | CharField(20)  | `stat_emp`           | Situação cadastral                 |
| `data_cadastro`          | DateField      | `dcad_emp`           | Data de cadastro no sistema        |
| `data_inatividade`       | DateField      | `dina_emp`           | Data de inativação                 |
| `motivo_inatividade`     | CharField(100) | `tipoi_emp`          | Motivo da inatividade              |
| `cae`                    | CharField(20)  | `ccae_emp`           | CAE (código de atividade)          |
| `contador`               | CharField(50)  | `codi_con`           | Código do contador responsável     |
| `email_resp_legal`       | EmailField     | `email_leg_emp`      | Email do responsável legal         |
| `duracao_contrato`       | IntegerField   | `duracao_emp`        | Duração do contrato (meses)        |
| `data_termino_contrato`  | DateField      | `dttermino_emp`      | Data de término do contrato        |
| `certificado_digital`    | CharField(255) | `CERTIFICADO_DIGITAL`| Informações do certificado digital |

### 2. **Chave de Identificação: CNPJ/CPF ao invés de ID Legado**

#### ❌ **Antes (ID Legado)**
```python
# Chave baseada em IDs internos do Sybase
contrato_id_legado = f"{id_contabilidade}-{id_contrato}"
# Exemplo: "591-45"
```

#### ✅ **Agora (CNPJ/CPF)**
```python
# Chave baseada em documentos (multi-tenant)
contrato_id_legado = f"{cnpj_contabilidade}-{cnpj_cliente}"
# Exemplo: "04550060000152-08300713000182"
```

**Benefícios:**
- ✅ **Multi-tenant**: Cada contabilidade tem seus próprios clientes identificados por CNPJ/CPF
- ✅ **Portabilidade**: Mesma empresa pode estar em múltiplas contabilidades
- ✅ **Unicidade global**: CNPJ/CPF é único no sistema
- ✅ **Rastreabilidade**: Fácil identificar clientes sem depender de IDs internos

### 3. **Separação de Processamento: Empresas e Contratos**

#### ❌ **Antes (Tudo junto)**
```sql
-- Query única buscando empresas e contratos em uma JOIN complexa
SELECT hc.*, ge.*, ...
FROM HRCONTRATO hc
JOIN GEEMPRE ge ...
```

#### ✅ **Agora (Duas fases)**
```sql
-- FASE 1: Buscar TODAS as empresas
SELECT nome_emp, cgce_emp, ramo_emp, ... FROM geempre

-- FASE 2: Buscar contratos ATIVOS
SELECT codi_emp, i_cliente, data_inicio, ...
FROM HRCONTRATO
WHERE data_termino > HOJE OR data_termino IS NULL
```

**Benefícios:**
- ✅ **Cobertura completa**: Todas as empresas são importadas, mesmo sem contrato
- ✅ **Performance**: Menos JOINs complexos
- ✅ **Manutenção**: Fácil atualizar dados de empresas sem reprocessar contratos

### 4. **Novos Métodos na ETL 03**

| Método                          | Descrição                                               |
|---------------------------------|---------------------------------------------------------|
| `processar_empresas()`          | Processa todas as empresas do Sybase (geempre)          |
| `_processar_pessoa_juridica()`  | Cria ou atualiza uma PJ com TODOS os campos do Sybase  |
| `_processar_pessoa_fisica()`    | Cria ou atualiza uma PF                                 |
| `_mapear_ramo_atividade()`      | Mapeia código do ramo para string ('comercio', etc.)    |
| `_mapear_regime_fiscal()`       | Mapeia simples_emp para regime ('simples', 'presumido') |
| `processar_contratos()`         | Processa contratos usando CNPJ/CPF como chave           |

### 5. **Queries do Sybase Implementadas**

#### **Query 1: Contratos Ativos**
```sql
SELECT 
    hc.codi_emp,
    hc.i_cliente,
    hc.data_inicio_faturamento as DATA_INICIO,
    hc.data_termino as DATA_TERMINO,
    hc.valor_contrato as VALOR_CONTRATO,
    hc.dia_vencimento,
    hc.i_contrato,
    ge.cgce_emp as documento_cliente,
    cont_ge.cgce_emp as cnpj_contabilidade
FROM bethadba.HRCONTRATO AS hc
INNER JOIN bethadba.HRVCLIENTE AS hvc 
    ON hc.i_cliente = hvc.i_cliente AND hc.codi_emp = hvc.codigo_escritorio
INNER JOIN bethadba.GEEMPRE AS ge 
    ON hvc.i_cliente_fixo = ge.codi_emp
INNER JOIN bethadba.GEEMPRE AS cont_ge 
    ON hc.codi_emp = cont_ge.codi_emp
WHERE (hc.data_termino > HOJE OR hc.data_termino IS NULL)
AND ge.codi_emp NOT IN (9997, 9998, 9999, 10000, 10001)
```

#### **Query 2: Empresas Completas**
```sql
SELECT 
    nome_emp, cepe_emp, cgce_emp, ramo_emp, codi_emp, rleg_emp, stat_emp, 
    dina_emp, dcad_emp, ccae_emp, cpf_leg_emp, cnae_emp, codi_con, email_emp, 
    dtinicio_emp, duracao_emp, dttermino_emp, razao_emp, tipoi_emp, i_cnae20, 
    usa_cnae20, email_leg_emp, CERTIFICADO_DIGITAL, fantasia_emp, ende_emp,
    nume_emp, comp_emp, bair_emp, cida_emp, esta_emp, fone_emp, imun_emp,
    simples_emp
FROM bethadba.geempre
WHERE cgce_emp IS NOT NULL
AND codi_emp NOT IN (9997, 9998, 9999, 10000, 10001)
```

### 6. **Mapeamento Completo de Campos**

| Campo Sybase         | Campo Django                 | Transformação                |
|----------------------|------------------------------|------------------------------|
| `razao_emp`          | `razao_social`               | -                            |
| `nome_emp`           | `razao_social` (fallback)    | -                            |
| `fantasia_emp`       | `nome_fantasia`              | -                            |
| `cgce_emp`           | `cnpj`                       | Limpar não-numéricos         |
| `cepe_emp`           | `cep`                        | Formatar 12345-678           |
| `ende_emp`           | `logradouro`                 | -                            |
| `nume_emp`           | `numero`                     | -                            |
| `comp_emp`           | `complemento`                | -                            |
| `bair_emp`           | `bairro`                     | -                            |
| `cida_emp`           | `cidade`                     | -                            |
| `esta_emp`           | `uf`                         | -                            |
| `fone_emp`           | `telefone`                   | -                            |
| `email_emp`          | `email`                      | -                            |
| `imun_emp`           | `inscricao_municipal`        | -                            |
| `rleg_emp`           | `responsavel_legal`          | -                            |
| `cpf_leg_emp`        | `cpf_responsavel`            | -                            |
| `email_leg_emp`      | `email_resp_legal`           | -                            |
| `cnae_emp`           | `cnae`                       | -                            |
| `i_cnae20`           | `cnae_20`                    | -                            |
| `usa_cnae20`         | `usa_cnae_20`                | Boolean                      |
| `stat_emp`           | `situacao`                   | -                            |
| `dcad_emp`           | `data_cadastro`              | DateField                    |
| `dtinicio_emp`       | `data_inicio_atividades`     | DateField                    |
| `dina_emp`           | `data_inatividade`           | DateField                    |
| `tipoi_emp`          | `motivo_inatividade`         | -                            |
| `ccae_emp`           | `cae`                        | -                            |
| `codi_con`           | `contador`                   | -                            |
| `duracao_emp`        | `duracao_contrato`           | IntegerField                 |
| `dttermino_emp`      | `data_termino_contrato`      | DateField                    |
| `CERTIFICADO_DIGITAL`| `certificado_digital`        | -                            |
| `simples_emp`        | `regime_fiscal`              | 1='simples', 0='presumido'   |
| `simples_emp`        | `simples_nacional`           | Boolean (1=True)             |
| `ramo_emp`           | `ramo_atividade`             | 1='comercio', 2='industria', 3='servicos' |

## 📊 Estatísticas Atuais

- **Total de PJ**: 14.252
- **Total de PF**: 34.740
- **Total de Contratos**: 2.186
- **Contratos Ativos**: 1.550
- **Contratos Inativos**: 636

## 🔄 Como Usar a Nova ETL

```bash
# Executar a ETL completa
python manage.py etl_03_contratos

# Executar em modo dry-run (teste)
python manage.py etl_03_contratos --dry-run

# Limitar quantidade de registros (para testes)
python manage.py etl_03_contratos --limit 100

# Apenas atualizar contratos existentes
python manage.py etl_03_contratos --update-only
```

## ✅ Validações Implementadas

1. ✅ **Integridade de Dados**: Todos os contratos têm contabilidade associada
2. ✅ **Documentos Únicos**: CNPJ/CPF são únicos no sistema
3. ✅ **Mapeamento Completo**: Todos os campos do Sybase são importados
4. ✅ **Multi-Tenant**: Chave baseada em CNPJ/CPF permite múltiplas contabilidades
5. ✅ **Contratos Ativos**: Apenas contratos válidos são importados
6. ✅ **Idempotência**: Registros sem mudança são pulados automaticamente

## 🔄 Idempotência

A ETL implementa **idempotência inteligente**:

- ✅ **Compara campo por campo** antes de atualizar
- ✅ **Pula registros sem mudança** (não gera UPDATE desnecessário)
- ✅ **Registra apenas modificações reais** no relatório final
- ✅ **Performance otimizada**: Menos writes no banco de dados

### Exemplo de Idempotência:

```bash
# 1ª Execução
✅ PJ 12345678000190 criada: EMPRESA ABC LTDA
✅ Contrato 04550060000152-12345678000190 criado

# 2ª Execução (dados não mudaram no Sybase)
⏭️  PJ 12345678000190 pulada (sem mudança)
⏭️  Contrato 04550060000152-12345678000190 pulado (sem mudança)

# 3ª Execução (email mudou no Sybase)
📝 PJ 12345678000190 atualizada: email
⏭️  Contrato 04550060000152-12345678000190 pulado (sem mudança)
```

## 🎯 Próximos Passos

1. ⏭️ Executar a ETL refatorada para popular os novos campos
2. ⏭️ Validar que os novos campos estão sendo preenchidos corretamente
3. ⏭️ Atualizar documentação da API de carteira com os novos campos disponíveis
4. ⏭️ Implementar filtros adicionais nos endpoints usando os novos campos

## 📝 Notas Importantes

- A chave `id_legado` do contrato agora segue o padrão: `{CNPJ_Contabilidade}-{CNPJ_Cliente}`
- Empresas sem contrato também são importadas (antes eram ignoradas)
- Todos os campos do Sybase estão disponíveis no Django, mesmo que vazios
- A ETL agora é **idempotente**: pode ser executada múltiplas vezes sem duplicar dados
