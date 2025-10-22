# ETL 03_1 - Regime Tributário e CNAE

## 📋 Visão Geral

Documentação das melhorias implementadas na ETL 03_1 para captura correta do **Regime Tributário** e **CNAE** das empresas, seguindo a **Regra de Ouro Multi-Tenant**.

---

## 🎯 Objetivos da Atualização

1. ✅ Capturar o **regime tributário** correto da tabela `EFPARAMETRO_VIGENCIA`
2. ✅ Importar o **CNAE principal** da tabela `GEEMPRE`
3. ✅ Aplicar a **Regra de Ouro** com `build_historical_contabilidade_map()`
4. ✅ Validar que apenas empresas com contratos válidos sejam importadas

---

## 📊 Query SQL - Regime Tributário

### Fonte dos Dados: EFPARAMETRO_VIGENCIA

```sql
SELECT 
    bethadba.geempre.codi_emp, 
    bethadba.geempre.nome_emp,       
    bethadba.EFPARAMETRO_VIGENCIA.RFED_PAR
FROM 
    bethadba.geempre,
    bethadba.EFPARAMETRO_VIGENCIA
WHERE 
    bethadba.EFPARAMETRO_VIGENCIA.CODI_EMP = bethadba.geempre.codi_emp 
    AND bethadba.EFPARAMETRO_VIGENCIA.VIGENCIA_PAR = (
        SELECT MAX(v.VIGENCIA_PAR) 
        FROM bethadba.EFPARAMETRO_VIGENCIA AS v 
        WHERE v.CODI_EMP = bethadba.geempre.codi_emp
    )
```

### Mapeamento do Campo RFED_PAR

| RFED_PAR | Descrição | regime_tributario | simples_nacional | regime_fiscal |
|----------|-----------|-------------------|------------------|---------------|
| 1 | Simples Nacional | '1' | True | 'simples' |
| 2 | Lucro Presumido | '2' | False | 'presumido' |
| 3 | Lucro Real | '3' | False | 'real' |

---

## 🗃️ Mapeamento de Campos Completo

### GEEMPRE (Sybase) → PessoaJuridica (PostgreSQL)

| Campo Sybase | Campo PostgreSQL | Tipo | Observações |
|--------------|------------------|------|-------------|
| `codi_emp` | `id_legado` | CharField(50) | ID original do Sybase |
| `cgce_emp` | `cnpj` | CharField(14) | Limpo, apenas números |
| `nome_emp` | `razao_social` | CharField(255) | Nome oficial da empresa |
| `fantasia_emp` | `nome_fantasia` | CharField(255) | Nome de fantasia |
| `ende_emp` | `logradouro` | CharField(255) | Endereço |
| `nume_emp` | `numero` | CharField(20) | Número do endereço |
| `comp_emp` | `complemento` | CharField(100) | Complemento |
| `bair_emp` | `bairro` | CharField(100) | Bairro |
| `cida_emp` / `codigo_municipio` | `cidade` | CharField(100) | Nome da cidade |
| `esta_emp` | `uf` | CharField(2) | Sigla do estado |
| `cepe_emp` | `cep` | CharField(9) | Formato: XXXXX-XXX |
| `fone_emp` | `telefone` | CharField(20) | Telefone |
| `email_emp` | `email` | EmailField | E-mail |
| `imun_emp` | `inscricao_municipal` | CharField(20) | Inscrição Municipal |
| **`RFED_PAR`** | `regime_tributario` | CharField(1) | **1=Simples, 2=Presumido, 3=Real** |
| `simples_emp` | `simples_nacional` | BooleanField | Fallback se RFED_PAR não disponível |
| - | `regime_fiscal` | CharField(20) | Para dashboards: simples/presumido/real |
| **`cnae_emp`** | `cnae_principal` | ForeignKey | **FK para cadastros_gerais.CNAE** |
| `ramo_emp` | `ramo_atividade` | CharField(20) | comercio, industria, servicos |
| `rleg_emp` | `responsavel_legal` | CharField(255) | Nome do responsável |
| `cpf_leg_emp` | `cpf_responsavel` | CharField(14) | CPF do responsável |

---

## 🔐 Regra de Ouro Multi-Tenant

### Validação com `build_historical_contabilidade_map()`

```python
# 1. Construir mapa histórico de contabilidades
historical_map = self.build_historical_contabilidade_map_cached()

# 2. Validar se empresa possui contabilidade mapeada
if cnpj_limpo not in historical_map:
    stats['sem_contabilidade'] += 1
    continue  # Pular empresa sem contrato válido
```

### O que o Mapa Histórico Garante

✅ **Apenas empresas com contratos válidos** são importadas  
✅ **Relacionamento correto** entre empresa e contabilidade  
✅ **Validação temporal** dos contratos  
✅ **Multi-tenant** seguro

---

## 📝 Exemplo de Dados Importados

### Entrada (Sybase)

```
codi_emp: 12345
nome_emp: EMPRESA EXEMPLO LTDA
cgce_emp: 12.345.678/0001-90
cnae_emp: 4711-3/02
simples_emp: 0
RFED_PAR: 2
```

### Saída (PostgreSQL)

```python
PessoaJuridica {
    id: UUID("..."),
    id_legado: "12345",
    cnpj: "12345678000190",
    razao_social: "EMPRESA EXEMPLO LTDA",
    cnae_principal: CNAE(codigo="4711-3/02"),
    regime_tributario: "2",  # Lucro Presumido
    simples_nacional: False,
    regime_fiscal: "presumido",
    ativo: True
}
```

---

## 🚀 Execução da ETL

### Comando Básico

```bash
python manage.py etl_03_1_pessoas_juridicas
```

### Opções Disponíveis

```bash
# Modo teste (não salva no banco)
python manage.py etl_03_1_pessoas_juridicas --dry-run

# Limitar número de empresas
python manage.py etl_03_1_pessoas_juridicas --limit 100

# Apenas atualizar existentes
python manage.py etl_03_1_pessoas_juridicas --update-only

# Filtrar por data de início de contratos
python manage.py etl_03_1_pessoas_juridicas --data-inicio 2020-01-01
```

---

## 📊 Estatísticas de Execução

A ETL reporta as seguintes métricas:

```
=== RELATÓRIO FINAL - ETL 03_1 ===
Total de empresas processadas: 1500
Pessoas Jurídicas criadas: 200
Pessoas Jurídicas atualizadas: 1250
CNPJs inválidos: 10
CNAEs não encontrados: 15
Sem contabilidade mapeada: 25
Erros: 0
```

### Interpretação

- **Total processadas**: Todas as empresas encontradas no Sybase
- **PJ criadas**: Novas empresas inseridas no PostgreSQL
- **PJ atualizadas**: Empresas existentes com dados atualizados
- **CNPJs inválidos**: CNPJs com formato incorreto (≠14 dígitos)
- **CNAEs não encontrados**: Códigos CNAE não cadastrados na tabela `cadastros_gerais.CNAE`
- **Sem contabilidade mapeada**: Empresas sem contrato válido (ignoradas pela Regra de Ouro)
- **Erros**: Exceções durante processamento

---

## 🔍 Validações Implementadas

### 1. Validação de CNPJ

```python
cnpj_limpo = re.sub(r'\D', '', cnpj_bruto)
if len(cnpj_limpo) != 14:
    stats['cnpj_invalidos'] += 1
    continue
```

### 2. Validação de Contabilidade (Regra de Ouro)

```python
if cnpj_limpo not in historical_map:
    stats['sem_contabilidade'] += 1
    continue
```

### 3. Validação de CNAE

```python
cnae_principal = CNAE.objects.filter(codigo=cnae_codigo).first()
if not cnae_principal:
    stats['cnae_nao_encontrados'] += 1
```

### 4. Exclusão de Empresas Modelo

```sql
AND ge.codi_emp NOT IN (9997, 9998, 9999, 10000, 10001)
```

---

## 🎨 Uso nos Dashboards

### Endpoint: `/api/gestao/carteira/categorias/`

```python
# Agregar por regime fiscal
regime_fiscal_data = PessoaJuridica.objects.filter(
    contratos__contabilidade=contabilidade,
    contratos__ativo=True
).values('regime_fiscal').annotate(
    total=Count('id')
)

# Resultado:
# [
#   {'regime_fiscal': 'simples', 'total': 45},
#   {'regime_fiscal': 'presumido', 'total': 30},
#   {'regime_fiscal': 'real', 'total': 10}
# ]
```

### Endpoint: `/api/gestao/carteira/clientes/`

```python
# Filtrar clientes ativos por regime
clientes_simples = PessoaJuridica.objects.filter(
    regime_fiscal='simples',
    ativo=True
)
```

---

## 🐛 Troubleshooting

### Problema: CNAEs não encontrados

**Solução**: Execute a ETL de CNAEs primeiro

```bash
python manage.py etl_cnaes  # Se existir
```

### Problema: Empresas sem contabilidade mapeada

**Solução**: Execute a ETL de contratos antes

```bash
python manage.py etl_03_contratos
```

### Problema: Regime tributário NULL

**Verificar**:
1. Campo `RFED_PAR` está sendo retornado na query?
2. Empresa possui registro em `EFPARAMETRO_VIGENCIA`?
3. Fallback para `simples_emp` está funcionando?

---

## 📚 Referências

- **Modelo**: `apps/pessoas/models.py` → `PessoaJuridica`
- **ETL Base**: `apps/importacao/management/commands/_base.py`
- **ETL Contratos**: `apps/importacao/management/commands/etl_03_contratos.py`
- **API Carteira**: `apps/api/gestao/views.py` → `CarteiraViewSet`

---

## ✅ Checklist de Validação

Após executar a ETL, validar:

- [ ] Empresas possuem `regime_tributario` preenchido
- [ ] Campo `regime_fiscal` está correto para dashboards
- [ ] `simples_nacional` está True apenas para Simples Nacional
- [ ] `cnae_principal` está vinculado corretamente
- [ ] Apenas empresas com contratos válidos foram importadas
- [ ] Estatísticas finais fazem sentido
- [ ] Logs não mostram erros críticos

---

## 📞 Suporte

Em caso de dúvidas ou problemas:

1. Verificar logs da ETL
2. Consultar este documento
3. Revisar código em `etl_03_1_pessoas_juridicas.py`
4. Validar query SQL no Sybase manualmente
