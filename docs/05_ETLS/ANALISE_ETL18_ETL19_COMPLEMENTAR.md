# ANÁLISE COMPARATIVA: ETL 18 e ETL 19 - Sistema de Usuários

## 📋 VISÃO GERAL

As ETLs 18 e 19 trabalham de forma **COMPLEMENTAR** para importar dados completos sobre usuários do sistema legado:

- **ETL 18**: Importa dados **GENÉRICOS** (cadastro básico de usuários)
- **ETL 19**: Importa dados **DETALHADOS** (logs de atividades e estatísticas)

---

## 🔄 ETL 18 - USUÁRIOS (Dados Genéricos)

### Objetivo
Importar o **cadastro básico** de usuários e seus vínculos com empresas/contabilidades.

### Tabelas de Origem (Sybase)
1. **USCONFUSUARIO** - Cadastro de usuários
2. **USCONFEMPRESAS** - Vínculos usuário-empresa
3. **ROWGENERATOR** - Módulos acessíveis
4. **GEEMPRE** - Dados das empresas (CNPJ)

### Modelos de Destino (Django)
1. **Usuario** - Tabela GLOBAL (sem contabilidade)
   ```python
   - id_legado (ÚNICO GLOBAL)
   - nome_usuario
   - tipo_usuario (GERENTE, EXTERNO, NORMAL, etc.)
   - ativo
   - data_ultimo_acesso
   ```

2. **UsuarioContabilidade** - Vínculos multitenant
   ```python
   - contabilidade (FK)
   - usuario (FK)
   - empresa_cnpj (identificação)
   - empresa_nome
   - data_inicio
   - data_fim
   - modulos_acesso (JSONField)
   ```

3. **UsuarioModulo** - Módulos por contabilidade
   ```python
   - contabilidade (FK)
   - usuario (FK)
   - modulo_id
   - modulo_nome
   - ativo
   ```

### Estratégia de Mapeamento
✅ **Usa REGRA DE OURO**
- Busca CNPJ da empresa (cgce_emp)
- Mapeia via `build_historical_contabilidade_map()`
- Cria usuário para CADA contabilidade relacionada à empresa

### Dados Importados
- ✅ Nome do usuário
- ✅ Tipo de usuário
- ✅ Status (ativo/inativo)
- ✅ Vínculos com empresas (CNPJ)
- ✅ Módulos acessíveis
- ✅ Data de último acesso (gerada aleatoriamente)

### Características
- **Genérico**: Cadastro básico para autenticação
- **Estrutural**: Define estrutura de acesso
- **Estático**: Dados de configuração

---

## 📊 ETL 19 - LOGS UNIFICADOS (Dados Detalhados)

### Objetivo
Importar **logs de uso** e gerar **estatísticas detalhadas** sobre:
- Tempo de uso por usuário/empresa
- Importações realizadas
- Lançamentos contábeis
- Análise de produtividade

### Tabelas de Origem (Sybase)
1. **GELOGUSER** - Logs de atividades (sessões)
2. **EFSAIDAS** - Importações de saídas fiscais
3. **EFENTRADAS** - Importações de entradas fiscais
4. **EFSERVICOS** - Importações de serviços
5. **CTLANCTO** - Lançamentos contábeis

### Modelos de Destino (Django)
1. **LogAtividade** - Sessões de uso
   ```python
   - contabilidade (FK)
   - usuario (FK - Usuario da ETL 18)
   - empresa (FK - PessoaJuridica)
   - data_atividade
   - hora_inicial
   - hora_final
   - tempo_sessao_minutos (CALCULADO)
   - sistema_modulo
   ```

2. **LogImportacao** - Importações realizadas
   ```python
   - contabilidade (FK)
   - usuario (FK)
   - empresa (FK)
   - tipo_importacao (SAIDA/ENTRADA/SERVICO)
   - data_importacao
   - quantidade_registros
   - valor_total
   ```

3. **LogLancamento** - Lançamentos contábeis
   ```python
   - contabilidade (FK)
   - usuario (FK)
   - empresa (FK)
   - data_lancamento
   - origem_registro (0=automático, !=0=manual)
   - tipo_operacao
   - valor
   - conta_debito
   - conta_credito
   - historico
   ```

4. **EstatisticaUsuario** - Estatísticas consolidadas
   ```python
   - contabilidade (FK)
   - usuario (FK)
   - empresa (FK)
   - periodo_referencia (YYYY-MM-01)
   
   # Atividades
   - total_atividades
   - tempo_total_minutos
   - modulos_acessados
   
   # Importações
   - total_importacoes
   - importacoes_saidas
   - importacoes_entradas
   - importacoes_servicos
   - valor_total_importacoes
   
   # Lançamentos
   - total_lancamentos
   - lancamentos_manuais
   - lancamentos_automaticos
   - valor_total_lancamentos
   ```

### Estratégia de Mapeamento
✅ **Usa REGRA DE OURO + Validação de Vínculos**

1. Busca usuário (ETL 18)
2. Busca empresa por CNPJ
3. **VALIDA vínculo UsuarioContabilidade**
   - Verifica se usuário tem acesso à empresa
   - Verifica se vínculo está ativo na data do evento
4. Usa contabilidade do vínculo válido

### Dados Importados
- ✅ **Tempo logado por empresa** (minutos de sessão)
- ✅ **Importações por usuário/empresa** (quantidade e valor)
- ✅ **Lançamentos por usuário/empresa** (manuais vs automáticos)
- ✅ **Estatísticas consolidadas mensais**
- ✅ **Módulos mais acessados**
- ✅ **Produtividade por período**

### Características
- **Detalhado**: Logs granulares de uso
- **Analítico**: Estatísticas e métricas
- **Dinâmico**: Dados de comportamento

---

## 🔗 RELAÇÃO ENTRE ETL 18 E ETL 19

### Dependências
```
ETL 18 (Usuários Genéricos)
    ↓
    ├─ Cria: Usuario (tabela global)
    ├─ Cria: UsuarioContabilidade (vínculos)
    └─ Cria: UsuarioModulo (permissões)
    
ETL 19 (Logs Detalhados)
    ↓
    ├─ DEPENDE: Usuario (ETL 18)
    ├─ DEPENDE: UsuarioContabilidade (ETL 18)
    ├─ DEPENDE: PessoaJuridica (ETL 02)
    ↓
    ├─ Cria: LogAtividade (sessões)
    ├─ Cria: LogImportacao (importações)
    ├─ Cria: LogLancamento (lançamentos)
    └─ Gera: EstatisticaUsuario (consolidado)
```

### Ordem de Execução
```bash
1. ETL 02 - Pessoas Jurídicas (CNPJ das empresas)
2. ETL 18 - Usuários (cadastro básico)
3. ETL 19 - Logs (dados de uso detalhados)
```

---

## 📊 ANÁLISE COMPLEMENTAR

### ETL 18 responde:
- ❓ **Quem são** os usuários?
- ❓ **Onde** podem acessar? (empresas/contabilidades)
- ❓ **O que** podem fazer? (módulos)
- ❓ **Quando** foi o último acesso? (data_ultimo_acesso)

### ETL 19 responde:
- ❓ **Quanto tempo** cada usuário passou no sistema?
- ❓ **Quantas importações** realizou por empresa?
- ❓ **Quantos lançamentos** fez (manuais vs automáticos)?
- ❓ **Qual a produtividade** por período?
- ❓ **Quais módulos** mais utilizou?
- ❓ **Quanto valor** movimentou em importações/lançamentos?

---

## 🎯 CASOS DE USO

### Dashboard de Usuários
**ETL 18 fornece:**
- Lista de usuários ativos
- Empresas vinculadas
- Último acesso

**ETL 19 complementa:**
- Tempo total de uso
- Atividades recentes
- Gráfico de produtividade

### Relatório de Produtividade
**ETL 18 fornece:**
- Usuários da contabilidade
- Permissões/módulos

**ETL 19 complementa:**
- Importações por usuário
- Lançamentos realizados
- Tempo efetivo trabalhado
- Comparativo mensal

### Auditoria de Acesso
**ETL 18 fornece:**
- Vínculos ativos
- Histórico de permissões

**ETL 19 complementa:**
- Logs de sessão detalhados
- Histórico de operações
- Rastreamento de lançamentos

---

## ⚠️ PONTOS DE ATENÇÃO

### ETL 18
```python
# ❌ PROBLEMA IDENTIFICADO: Dados duplicados
# Linha 293: Cria usuário para CADA contabilidade
usuario_obj, created = Usuario.objects.update_or_create(
    contabilidade=contabilidade,  # ← Usuario não deveria ter contabilidade!
    cnpj_empresa=cnpj_limpo,      # ← Usuario não tem esse campo!
    id_legado=nome_usuario,
    defaults={...}
)
```

**CORREÇÃO NECESSÁRIA:**
```python
# ✅ Usuario é GLOBAL (único por id_legado)
usuario_obj, created = Usuario.objects.get_or_create(
    id_legado=nome_usuario,  # ← Apenas id_legado
    defaults={
        'nome_usuario': nome_usuario,
        'tipo_usuario': tipo_usuario,
        'ativo': True,
    }
)

# ✅ Vínculo é MULTITENANT (múltiplos por contabilidade)
UsuarioContabilidade.objects.update_or_create(
    contabilidade=contabilidade,
    usuario=usuario_obj,
    empresa_cnpj=cnpj_limpo,
    defaults={...}
)
```

### ETL 19
```python
# ✅ CORRETO: Busca usuario global
usuario = Usuario.objects.get(nome_usuario=usuario_nome)

# ✅ CORRETO: Valida vínculo na data do evento
vinculos = UsuarioContabilidade.objects.filter(
    usuario=usuario,
    empresa_cnpj=cnpj_empresa,
    data_inicio__lte=data_evento,
    data_fim__gte=data_evento
)
```

---

## 🔧 CORREÇÕES NECESSÁRIAS NA ETL 18

### Problema 1: Usuario com contabilidade
❌ **Atual:** Usuario tem FK para Contabilidade
✅ **Correto:** Usuario é global, sem FK

### Problema 2: Usuario com cnpj_empresa
❌ **Atual:** Usuario tem campo cnpj_empresa
✅ **Correto:** CNPJ está em UsuarioContabilidade

### Problema 3: Criação duplicada
❌ **Atual:** Cria 1 Usuario por contabilidade
✅ **Correto:** Cria 1 Usuario global + N UsuarioContabilidade

---

## 📝 RESUMO EXECUTIVO

| Aspecto | ETL 18 | ETL 19 |
|---------|--------|--------|
| **Tipo de Dados** | Genéricos (cadastro) | Detalhados (logs) |
| **Origem** | USCONFUSUARIO, USCONFEMPRESAS | GELOGUSER, EFSAIDAS, CTLANCTO |
| **Destino** | Usuario, UsuarioContabilidade | LogAtividade, LogImportacao, LogLancamento |
| **REGRA DE OURO** | ✅ Sim | ✅ Sim (com validação de vínculos) |
| **Granularidade** | Usuário/Empresa | Usuário/Empresa/Data |
| **Atualização** | Estática (config) | Dinâmica (eventos) |
| **Depende de** | ETL 02 (Pessoas) | ETL 02 + ETL 18 |
| **Usa histórico?** | Não (data fixa) | Sim (valida data do evento) |
| **Status** | ⚠️ Precisa correção | ✅ Correto |

---

## ✅ PRÓXIMOS PASSOS

1. **Corrigir ETL 18:**
   - Remover contabilidade_id de Usuario
   - Remover cnpj_empresa de Usuario
   - Implementar criação correta (1 Usuario global)

2. **Testar ETL 18:**
   - Verificar unicidade global de id_legado
   - Validar vínculos multitenant

3. **Executar ETL 19:**
   - Depende da correção da ETL 18
   - Validar cálculo de tempo de sessão
   - Verificar estatísticas consolidadas

4. **Gerar relatórios:**
   - Dashboard de produtividade
   - Análise de uso por módulo
   - Auditoria de acessos
