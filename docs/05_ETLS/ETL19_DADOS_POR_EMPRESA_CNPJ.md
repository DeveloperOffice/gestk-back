# ✅ CONFIRMAÇÃO: ETL 19 - Dados por Empresa (CNPJ) para APIs

## 🎯 RESPOSTA DIRETA

**SIM! A ETL 19 importa TODOS os dados por empresa (CNPJ) que você mencionou:**

✅ **Tempo por empresa (minutos de sessão)**
✅ **Importações (manuais e automáticas por tipo)**
✅ **Lançamentos (manuais vs automáticos)**
✅ **Estatísticas consolidadas por período**

Esses dados ficam prontos no banco para serem consumidos pelas **APIs/endpoints**.

---

## 📊 ESTRUTURA DE DADOS IMPORTADOS

### 1. **LogAtividade** - Tempo por Empresa

```python
class LogAtividade(BaseModeloMultitenant):
    contabilidade = FK(Contabilidade)     # Isolamento multitenant
    usuario = FK(Usuario)                 # Qual usuário
    empresa = FK(PessoaJuridica)          # ✅ EMPRESA (CNPJ)
    data_atividade = DateField            # Quando
    hora_inicial = TimeField              # Início da sessão
    hora_final = TimeField                # Fim da sessão
    tempo_sessao_minutos = IntegerField   # ✅ TEMPO CALCULADO (minutos)
    sistema_modulo = IntegerField         # Qual módulo acessou
```

**Queries possíveis para API:**
```python
# Tempo total por empresa
LogAtividade.objects.filter(
    empresa__cnpj='12345678000199'
).aggregate(Sum('tempo_sessao_minutos'))

# Tempo por usuário em empresa específica
LogAtividade.objects.filter(
    empresa__cnpj='12345678000199',
    usuario=usuario_obj
).aggregate(Sum('tempo_sessao_minutos'))

# Tempo por módulo
LogAtividade.objects.filter(
    empresa__cnpj='12345678000199'
).values('sistema_modulo').annotate(
    tempo_total=Sum('tempo_sessao_minutos')
)
```

---

### 2. **LogImportacao** - Importações por Empresa

```python
class LogImportacao(BaseModeloMultitenant):
    contabilidade = FK(Contabilidade)
    usuario = FK(Usuario)
    empresa = FK(PessoaJuridica)          # ✅ EMPRESA (CNPJ)
    tipo_importacao = CharField           # ✅ SAIDA/ENTRADA/SERVICO
    data_importacao = DateField
    quantidade_registros = IntegerField   # Quantos registros
    valor_total = DecimalField            # Valor movimentado
```

**Queries possíveis para API:**
```python
# Total de importações por tipo
LogImportacao.objects.filter(
    empresa__cnpj='12345678000199'
).values('tipo_importacao').annotate(
    total=Count('id'),
    valor=Sum('valor_total')
)

# Importações por usuário
LogImportacao.objects.filter(
    empresa__cnpj='12345678000199'
).values('usuario__nome_usuario').annotate(
    total=Count('id')
)

# Importações por período
LogImportacao.objects.filter(
    empresa__cnpj='12345678000199',
    data_importacao__range=['2024-01-01', '2024-12-31']
).aggregate(
    total_saidas=Count('id', filter=Q(tipo_importacao='SAIDA')),
    total_entradas=Count('id', filter=Q(tipo_importacao='ENTRADA')),
    total_servicos=Count('id', filter=Q(tipo_importacao='SERVICO'))
)
```

---

### 3. **LogLancamento** - Lançamentos por Empresa

```python
class LogLancamento(BaseModeloMultitenant):
    contabilidade = FK(Contabilidade)
    usuario = FK(Usuario)
    empresa = FK(PessoaJuridica)          # ✅ EMPRESA (CNPJ)
    data_lancamento = DateField
    origem_registro = IntegerField        # ✅ 0=AUTOMÁTICO, !=0=MANUAL
    tipo_operacao = CharField             # MANUAL/AUTOMATICO
    valor = DecimalField
    conta_debito = CharField
    conta_credito = CharField
    historico = CharField
```

**Queries possíveis para API:**
```python
# Lançamentos manuais vs automáticos
LogLancamento.objects.filter(
    empresa__cnpj='12345678000199'
).aggregate(
    manuais=Count('id', filter=Q(origem_registro__gt=0)),
    automaticos=Count('id', filter=Q(origem_registro=0))
)

# Valor total lançado
LogLancamento.objects.filter(
    empresa__cnpj='12345678000199'
).aggregate(
    valor_total=Sum('valor')
)

# Lançamentos por usuário
LogLancamento.objects.filter(
    empresa__cnpj='12345678000199'
).values('usuario__nome_usuario').annotate(
    total_lancamentos=Count('id'),
    valor_total=Sum('valor')
)
```

---

### 4. **EstatisticaUsuario** - Consolidado Mensal

```python
class EstatisticaUsuario(BaseModeloMultitenant):
    contabilidade = FK(Contabilidade)
    usuario = FK(Usuario)
    empresa = FK(PessoaJuridica)          # ✅ EMPRESA (CNPJ)
    periodo_referencia = DateField        # YYYY-MM-01
    
    # ✅ ATIVIDADES
    total_atividades = IntegerField
    tempo_total_minutos = IntegerField    # ✅ TEMPO TOTAL
    modulos_acessados = JSONField
    
    # ✅ IMPORTAÇÕES
    total_importacoes = IntegerField
    importacoes_saidas = IntegerField     # ✅ POR TIPO
    importacoes_entradas = IntegerField   # ✅ POR TIPO
    importacoes_servicos = IntegerField   # ✅ POR TIPO
    valor_total_importacoes = DecimalField
    
    # ✅ LANÇAMENTOS
    total_lancamentos = IntegerField
    lancamentos_manuais = IntegerField    # ✅ MANUAIS
    lancamentos_automaticos = IntegerField # ✅ AUTOMÁTICOS
    valor_total_lancamentos = DecimalField
```

**Queries possíveis para API:**
```python
# Estatísticas consolidadas de uma empresa
EstatisticaUsuario.objects.filter(
    empresa__cnpj='12345678000199',
    periodo_referencia='2024-10-01'
).aggregate(
    tempo_total=Sum('tempo_total_minutos'),
    total_importacoes=Sum('total_importacoes'),
    total_lancamentos=Sum('total_lancamentos')
)

# Ranking de usuários por produtividade
EstatisticaUsuario.objects.filter(
    empresa__cnpj='12345678000199'
).values('usuario__nome_usuario').annotate(
    tempo=Sum('tempo_total_minutos'),
    lancamentos=Sum('total_lancamentos')
).order_by('-lancamentos')
```

---

## 🔗 RELAÇÃO CNPJ → DADOS

```
CNPJ (PessoaJuridica)
    ↓
    ├─ LogAtividade (tempo de sessão por empresa)
    │   └─ tempo_sessao_minutos ✅
    │
    ├─ LogImportacao (importações por empresa)
    │   ├─ tipo_importacao (SAIDA/ENTRADA/SERVICO) ✅
    │   ├─ quantidade_registros ✅
    │   └─ valor_total ✅
    │
    ├─ LogLancamento (lançamentos por empresa)
    │   ├─ origem_registro (0=automático, !=0=manual) ✅
    │   ├─ tipo_operacao (MANUAL/AUTOMATICO) ✅
    │   └─ valor ✅
    │
    └─ EstatisticaUsuario (consolidado mensal)
        ├─ tempo_total_minutos ✅
        ├─ importacoes_saidas/entradas/servicos ✅
        ├─ lancamentos_manuais/automaticos ✅
        └─ valores_totais ✅
```

---

## 🎯 ENDPOINTS SUGERIDOS PARA API

### 1. **Dashboard de Empresa**
```python
GET /api/admin/empresas/{cnpj}/dashboard/
Response:
{
    "empresa": {
        "cnpj": "12345678000199",
        "nome": "Empresa XYZ"
    },
    "periodo": "2024-10",
    "tempo_uso": {
        "total_minutos": 15420,
        "total_horas": 257,
        "por_usuario": [...]
    },
    "importacoes": {
        "total": 1250,
        "saidas": 450,
        "entradas": 600,
        "servicos": 200,
        "valor_total": 1500000.00
    },
    "lancamentos": {
        "total": 3200,
        "manuais": 800,
        "automaticos": 2400,
        "valor_total": 5000000.00
    }
}
```

### 2. **Tempo de Uso por Empresa**
```python
GET /api/admin/empresas/{cnpj}/tempo-uso/
Query params: ?data_inicio=2024-01-01&data_fim=2024-12-31
Response:
{
    "tempo_total_minutos": 15420,
    "tempo_total_horas": 257,
    "por_modulo": [
        {"modulo": "Contábil", "minutos": 8000},
        {"modulo": "Fiscal", "minutos": 5420},
        {"modulo": "RH", "minutos": 2000}
    ],
    "por_usuario": [
        {"usuario": "JOAO", "minutos": 6500},
        {"usuario": "MARIA", "minutos": 8920}
    ],
    "evolucao_mensal": [
        {"mes": "2024-01", "minutos": 1200},
        {"mes": "2024-02", "minutos": 1450},
        ...
    ]
}
```

### 3. **Importações por Empresa**
```python
GET /api/admin/empresas/{cnpj}/importacoes/
Query params: ?tipo=SAIDA&data_inicio=2024-01-01
Response:
{
    "total_importacoes": 450,
    "valor_total": 850000.00,
    "por_tipo": {
        "saidas": {"quantidade": 450, "valor": 850000.00},
        "entradas": {"quantidade": 600, "valor": 450000.00},
        "servicos": {"quantidade": 200, "valor": 200000.00}
    },
    "por_usuario": [
        {"usuario": "JOAO", "total": 250, "valor": 500000.00},
        {"usuario": "MARIA", "total": 200, "valor": 350000.00}
    ],
    "evolucao_mensal": [...]
}
```

### 4. **Lançamentos por Empresa**
```python
GET /api/admin/empresas/{cnpj}/lancamentos/
Response:
{
    "total_lancamentos": 3200,
    "valor_total": 5000000.00,
    "por_tipo": {
        "manuais": {"quantidade": 800, "valor": 1200000.00},
        "automaticos": {"quantidade": 2400, "valor": 3800000.00}
    },
    "por_usuario": [...],
    "por_conta": [
        {"conta": "1.01.001", "debitos": 150, "creditos": 200},
        ...
    ]
}
```

### 5. **Estatísticas Consolidadas**
```python
GET /api/admin/empresas/{cnpj}/estatisticas/
Query params: ?periodo=2024-10
Response:
{
    "periodo": "2024-10-01",
    "usuarios_ativos": 15,
    "atividades": {
        "total": 450,
        "tempo_total_minutos": 15420,
        "modulos": [...]
    },
    "importacoes": {...},
    "lancamentos": {...},
    "produtividade": {
        "lancamentos_por_hora": 20.7,
        "importacoes_por_dia": 42,
        "tempo_medio_sessao": 34
    }
}
```

### 6. **Ranking de Usuários**
```python
GET /api/admin/empresas/{cnpj}/ranking-usuarios/
Response:
{
    "periodo": "2024-10",
    "por_tempo_uso": [
        {"usuario": "MARIA", "minutos": 8920, "posicao": 1},
        {"usuario": "JOAO", "minutos": 6500, "posicao": 2}
    ],
    "por_lancamentos": [...],
    "por_importacoes": [...]
}
```

---

## ✅ RESUMO FINAL

### Dados Importados pela ETL 19 (prontos para APIs):

| Dado | Por Empresa (CNPJ) | Detalhamento |
|------|-------------------|--------------|
| **Tempo de uso** | ✅ SIM | Minutos de sessão por empresa/usuário/módulo |
| **Importações** | ✅ SIM | Por tipo (SAIDA/ENTRADA/SERVICO) + valor |
| **Lançamentos** | ✅ SIM | Manuais vs Automáticos + valor + contas |
| **Estatísticas** | ✅ SIM | Consolidado mensal por empresa/usuário |
| **Histórico** | ✅ SIM | Logs granulares de todas as operações |
| **Módulos usados** | ✅ SIM | Quais módulos cada usuário acessou |
| **Produtividade** | ✅ SIM | Métricas calculadas (lançamentos/hora, etc) |

### Fluxo Completo:

```
1. ETL 19 importa dados do Sybase
   ↓
2. Armazena no Django (PostgreSQL)
   ↓
3. APIs/Endpoints consomem os dados
   ↓
4. Frontend exibe dashboards/relatórios
```

**Tudo está pronto para ser consumido pelas APIs! 🎉**

Os dados já estão:
- ✅ Organizados por empresa (CNPJ)
- ✅ Relacionados com usuários
- ✅ Calculados (tempo, totais, etc)
- ✅ Indexados para performance
- ✅ Multitenant (isolados por contabilidade)
- ✅ Prontos para queries rápidas
