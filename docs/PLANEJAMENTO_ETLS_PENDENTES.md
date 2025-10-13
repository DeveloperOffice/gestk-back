# 📋 PLANEJAMENTO DE EXECUÇÃO DE ETLs - GESTK

**Data da Análise**: 13/10/2025  
**Status Geral**: 5 de 6 ETLs principais completos (83%)

---

## 📊 SITUAÇÃO ATUAL

### ✅ ETLs JÁ EXECUTADOS COM SUCESSO

| ETL | Descrição | Registros | Status |
|-----|-----------|-----------|--------|
| **ETL 01** | Contabilidades | 11 | ✅ COMPLETO |
| **ETL 02** | CNAEs | 2,071 | ✅ COMPLETO |
| **ETL 03** | Contratos + Pessoas | 2,186 contratos<br>918 PJ<br>13,693 PF | ✅ COMPLETO |
| **ETL 05** | Plano de Contas | 68,415 | ✅ COMPLETO |
| **ETL 07** | Notas Fiscais | 10,279 | ✅ COMPLETO |
| **ETL 08** | Cargos (RH) | 1,442 | ✅ COMPLETO |
| **ETL 09** | Departamentos (RH) | 128 | ✅ COMPLETO |
| **ETL 11** | Funcionários + Vínculos | 6,247 func<br>5,891 vínculos | ✅ COMPLETO |
| **ETL 18** | Usuários | 7 | ✅ COMPLETO |

**Total Importado**: 105,688 registros em 9 ETLs principais

---

## ⚠️ ETLs PENDENTES/CRÍTICOS

### 🔴 PRIORIDADE CRÍTICA

#### **ETL 06 - Lançamentos Contábeis** ❌ PENDENTE
- **Status**: 0 registros (NÃO EXECUTADO)
- **Impacto**: ALTO - Bloqueia dashboards contábeis
- **Dependências**: ETL 05 (Plano de Contas) ✅ OK
- **Estimativa**: ~500.000+ lançamentos esperados
- **Tempo de Execução**: 2-4 horas (grande volume)
- **Comando**:
  ```bash
  python manage.py etl_06_lancamentos
  ```
- **⚠️ ATENÇÃO**: Este é o ETL mais crítico pendente!

---

## 📋 PLANEJAMENTO DE EXECUÇÃO

### **FASE 1: ETL CRÍTICO (Executar IMEDIATAMENTE)** 🔴

#### Passo 1: ETL 06 - Lançamentos Contábeis
```bash
# Teste primeiro com limite
python manage.py etl_06_lancamentos --limit 1000 --dry-run

# Se OK, executar completo
python manage.py etl_06_lancamentos
```

**Por quê executar primeiro?**
- ✅ Desbloqueia Dashboard Contábil (Fase 3)
- ✅ Permite análise de balancetes
- ✅ Fundamental para relatórios financeiros
- ✅ Dados já preparados (ETL 05 completo)

---

### **FASE 2: ETLs COMPLEMENTARES DE RH** 🟡

Executar na ordem após ETL 06:

#### Passo 2: ETL 10 - Centros de Custo
```bash
python manage.py etl_10_rh_centros_custo
```
- **Dependências**: ETL 03 ✅
- **Estimativa**: ~100-500 registros
- **Tempo**: 5-10 minutos

#### Passo 3: ETL 12 - Históricos Funcionais
```bash
python manage.py etl_12_rh_historicos
```
- **Dependências**: ETL 11 ✅
- **Estimativa**: ~10.000-20.000 registros
- **Tempo**: 30-60 minutos
- **Descrição**: Mudanças de cargo, departamento, salário

#### Passo 4: ETL 13 - Períodos Aquisitivos de Férias
```bash
python manage.py etl_13_rh_periodos_aquisitivos
```
- **Dependências**: ETL 11 ✅
- **Estimativa**: ~5.000-10.000 períodos
- **Tempo**: 20-40 minutos

#### Passo 5: ETL 14 - Gozo de Férias
```bash
python manage.py etl_14_rh_gozo_ferias
```
- **Dependências**: ETL 13 ✅
- **Estimativa**: ~8.000-15.000 registros
- **Tempo**: 30-50 minutos

#### Passo 6: ETL 15 - Afastamentos
```bash
python manage.py etl_15_rh_afastamentos
```
- **Dependências**: ETL 11 ✅
- **Estimativa**: ~1.000-3.000 afastamentos
- **Tempo**: 15-30 minutos

#### Passo 7: ETL 16 - Rescisões
```bash
python manage.py etl_16_rh_rescisoes

# Depois executar rubricas
python manage.py etl_16_rh_rescisoes_rubricas
```
- **Dependências**: ETL 11 ✅
- **Estimativa**: ~2.000-4.000 rescisões
- **Tempo**: 20-40 minutos cada

---

### **FASE 3: ETLs OPCIONAIS/COMPLEMENTARES** 🟢

#### Passo 8: ETL 04 - Quadro Societário
```bash
python manage.py etl_04_quadro_societario
```
- **Dependências**: ETL 03 ✅
- **Estimativa**: ~2.000-5.000 registros
- **Tempo**: 15-30 minutos
- **Descrição**: Sócios das empresas

#### Passo 9: ETL 17 - Cupons Fiscais
```bash
python manage.py etl_17_cupons_fiscais
```
- **Dependências**: ETL 03 ✅
- **Estimativa**: ~50.000-100.000 cupons
- **Tempo**: 1-2 horas
- **Descrição**: Cupons fiscais eletrônicos (varejo)

#### Passo 10: ETL 19 - Logs de Sistema
```bash
python manage.py etl_19_logs_unificado_corrigido
```
- **Dependências**: ETL 18 ✅
- **Estimativa**: ~100.000+ logs
- **Tempo**: 2-3 horas
- **Descrição**: Logs de acesso e auditoria

---

## 🎯 RESUMO DO PLANEJAMENTO

### **Ordem de Execução Recomendada**

```
┌─────────────────────────────────────────────────────┐
│  FASE 1: CRÍTICO (Executar HOJE)                   │
├─────────────────────────────────────────────────────┤
│  1. ETL 06 - Lançamentos Contábeis  [2-4h]   🔴   │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│  FASE 2: COMPLEMENTARES RH (Esta semana)            │
├─────────────────────────────────────────────────────┤
│  2. ETL 10 - Centros de Custo       [10min]   🟡   │
│  3. ETL 12 - Históricos             [45min]   🟡   │
│  4. ETL 13 - Períodos Férias        [30min]   🟡   │
│  5. ETL 14 - Gozo Férias            [40min]   🟡   │
│  6. ETL 15 - Afastamentos           [25min]   🟡   │
│  7. ETL 16 - Rescisões + Rubricas   [60min]   🟡   │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│  FASE 3: OPCIONAIS (Próxima semana)                │
├─────────────────────────────────────────────────────┤
│  8. ETL 04 - Quadro Societário      [20min]   🟢   │
│  9. ETL 17 - Cupons Fiscais         [1.5h]    🟢   │
│ 10. ETL 19 - Logs Sistema           [2.5h]    🟢   │
└─────────────────────────────────────────────────────┘

TEMPO TOTAL ESTIMADO:
  - Fase 1 (Crítico):      2-4 horas
  - Fase 2 (RH):           3-4 horas
  - Fase 3 (Opcionais):    4-5 horas
  - TOTAL:                 9-13 horas
```

---

## 📝 SCRIPT DE EXECUÇÃO AUTOMÁTICA

### **Opção 1: Executar ETL 06 Isoladamente**
```bash
# Windows
python manage.py etl_06_lancamentos

# Linux/Mac
python manage.py etl_06_lancamentos &
```

### **Opção 2: Executar Sequência FASE 2 (RH)**
```bash
# Criar arquivo: executar_etls_rh.bat (Windows)
@echo off
echo Executando ETLs de RH...
python manage.py etl_10_rh_centros_custo
python manage.py etl_12_rh_historicos
python manage.py etl_13_rh_periodos_aquisitivos
python manage.py etl_14_rh_gozo_ferias
python manage.py etl_15_rh_afastamentos
python manage.py etl_16_rh_rescisoes
python manage.py etl_16_rh_rescisoes_rubricas
echo Concluido!
```

### **Opção 3: Executar TUDO (Usar com cuidado)**
```bash
# Usar o script existente
python executar_etls_sequencial.py
```

---

## ⚠️ AVISOS IMPORTANTES

### **Antes de Executar ETL 06**
1. ✅ Verificar espaço em disco (500MB+ livre recomendado)
2. ✅ Confirmar conexão Sybase estável
3. ✅ Backup do banco PostgreSQL (recomendado)
4. ✅ Executar em horário de baixo uso

### **Monitoramento Durante Execução**
```bash
# Em outro terminal, monitorar progresso
python verificar_status_etls.py

# Ou verificar diretamente no banco
python manage.py shell -c "
from apps.contabil.models import LancamentoContabil
print(f'Lançamentos importados: {LancamentoContabil.objects.count():,}')
"
```

### **Em Caso de Erro**
1. ✅ Verificar logs do console
2. ✅ Confirmar se ETL 05 (Plano de Contas) está OK
3. ✅ Verificar conectividade Sybase
4. ✅ Re-executar com `--limit 100 --dry-run` para debug

---

## 📊 IMPACTO NOS DASHBOARDS

### **Após ETL 06 (Lançamentos)**
- ✅ Dashboard Contábil: 100% funcional
- ✅ Balancetes: Disponíveis
- ✅ DRE: Dados completos
- ✅ Análises financeiras: Habilitadas

### **Após ETLs RH (10-16)**
- ✅ Dashboard Demográfico: Dados históricos completos
- ✅ Análise de turnover: Habilitada
- ✅ Controle de férias: Completo
- ✅ Gestão de afastamentos: Funcional

---

## 🎯 CHECKLIST DE EXECUÇÃO

### **Hoje (13/10/2025)**
- [ ] Executar ETL 06 - Lançamentos Contábeis
- [ ] Verificar importação (deve ter ~500k+ registros)
- [ ] Testar Dashboard Contábil

### **Esta Semana**
- [ ] ETL 10 - Centros de Custo
- [ ] ETL 12 - Históricos Funcionais
- [ ] ETL 13 - Períodos Aquisitivos
- [ ] ETL 14 - Gozo Férias
- [ ] ETL 15 - Afastamentos
- [ ] ETL 16 - Rescisões

### **Próxima Semana (Opcional)**
- [ ] ETL 04 - Quadro Societário
- [ ] ETL 17 - Cupons Fiscais
- [ ] ETL 19 - Logs

---

## 📈 MÉTRICAS DE SUCESSO

**Ao completar FASE 1 (ETL 06)**:
- ✅ 100% dos ETLs críticos executados
- ✅ Todos os dashboards principais funcionais
- ✅ ~600k+ registros totais importados

**Ao completar FASE 2 (ETLs RH)**:
- ✅ Módulo RH 100% completo
- ✅ Dashboard Demográfico com dados históricos
- ✅ ~650k+ registros totais

**Ao completar FASE 3 (Opcionais)**:
- ✅ Sistema 100% importado
- ✅ Todos os módulos operacionais
- ✅ ~800k+ registros totais

---

**Última Atualização**: 13/10/2025  
**Próxima Revisão**: Após execução do ETL 06
