# 🎯 RESUMO DAS MELHORIAS - ETL 03_1

## ✅ O que foi implementado

### 1. 📊 Captura de Regime Tributário

**Query SQL implementada:**
```sql
-- Busca o regime federal mais recente de cada empresa
regime_federal = IsNull((SELECT efpv.RFED_PAR
                         FROM bethadba.EFPARAMETRO_VIGENCIA AS efpv
                         WHERE efpv.CODI_EMP = ge.codi_emp
                         AND efpv.VIGENCIA_PAR = (SELECT MAX(v.VIGENCIA_PAR)
                                                  FROM bethadba.EFPARAMETRO_VIGENCIA AS v
                                                  WHERE v.CODI_EMP = ge.codi_emp)), 0)
```

**Mapeamento implementado:**
- `RFED_PAR = 1` → Simples Nacional
- `RFED_PAR = 2` → Lucro Presumido
- `RFED_PAR = 3` → Lucro Real
- Fallback: `simples_emp` (campo antigo da GEEMPRE)

**Campos populados no PostgreSQL:**
- ✅ `regime_tributario` (CharField: '1', '2', '3')
- ✅ `simples_nacional` (BooleanField)
- ✅ `regime_fiscal` (CharField: 'simples', 'presumido', 'real') - Para dashboards

---

### 2. 🏢 Captura de CNAE

**Campo importado:** `cnae_emp` da tabela `GEEMPRE`

**Relacionamento criado:**
```python
cnae_principal = CNAE.objects.filter(codigo=cnae_codigo).first()
empresa_data['cnae_principal'] = cnae_principal
```

**Validação:**
- Verifica se o CNAE existe na tabela `cadastros_gerais.CNAE`
- Contabiliza CNAEs não encontrados nas estatísticas
- Mantém o relacionamento FK correto

---

### 3. 🔐 Implementação da Regra de Ouro

**Mapeamento de Contabilidade:**
```python
# Construir mapa histórico de contabilidades
historical_map = self.build_historical_contabilidade_map_cached()

# Validar se empresa possui contabilidade mapeada
if cnpj_limpo not in historical_map:
    stats['sem_contabilidade'] += 1
    continue  # Pular empresa sem contrato válido
```

**O que isso garante:**
- ✅ Apenas empresas com contratos válidos são importadas
- ✅ Relacionamento correto entre empresa e contabilidade
- ✅ Validação temporal dos contratos
- ✅ Multi-tenant seguro

---

## 📁 Arquivos Modificados

### 1. ETL Principal
📄 `apps/importacao/management/commands/etl_03_1_pessoas_juridicas.py`

**Alterações:**
- ✅ Query SQL atualizada com `RFED_PAR` da `EFPARAMETRO_VIGENCIA`
- ✅ Lógica de mapeamento de regime tributário aprimorada
- ✅ Integração com `build_historical_contabilidade_map()`
- ✅ Validação de contabilidade antes de importar
- ✅ Estatísticas ampliadas (adicionado `sem_contabilidade`)
- ✅ Comentários detalhados sobre mapeamento

---

### 2. Documentação Criada
📄 `docs/05_ETLS/ETL_03_1_REGIME_TRIBUTARIO_CNAE.md`

**Conteúdo:**
- 📋 Visão geral da atualização
- 📊 Query SQL completa
- 🗃️ Mapeamento de campos detalhado
- 🔐 Explicação da Regra de Ouro
- 📝 Exemplos de dados
- 🚀 Comandos de execução
- 📊 Interpretação de estatísticas
- 🔍 Validações implementadas
- 🎨 Uso nos dashboards
- 🐛 Troubleshooting
- ✅ Checklist de validação

---

### 3. Script de Validação
📄 `scripts_debug/validar_etl03_regime_cnae.py`

**Funcionalidades:**
- ✅ Valida regime tributário importado
- ✅ Verifica distribuição por regime
- ✅ Valida consistência entre campos
- ✅ Verifica CNAEs importados
- ✅ Lista top 10 CNAEs mais usados
- ✅ Valida ramo de atividade
- ✅ Verifica Regra de Ouro (contabilidade)
- ✅ Mostra amostras de dados

**Execução:**
```bash
python scripts_debug/validar_etl03_regime_cnae.py
```

---

### 4. README Atualizado
📄 `scripts_debug/README.md`

Adicionado novo script na seção de ETL.

---

## 🗃️ Modelo de Dados

### Campos no PostgreSQL (PessoaJuridica)

```python
class PessoaJuridica(models.Model):
    # ... outros campos ...
    
    # Regime Tributário
    REGIME_TRIBUTARIO_CHOICES = [
        ('1', 'Simples Nacional'),
        ('2', 'Lucro Presumido'),
        ('3', 'Lucro Real'),
        ('4', 'MEI'),
    ]
    regime_tributario = models.CharField(
        max_length=1, 
        choices=REGIME_TRIBUTARIO_CHOICES,
        blank=True, null=True
    )
    simples_nacional = models.BooleanField(default=False)
    
    # Para dashboards
    regime_fiscal = models.CharField(
        max_length=20,
        choices=[
            ('simples', 'Simples Nacional'),
            ('presumido', 'Lucro Presumido'),
            ('real', 'Lucro Real'),
        ],
        blank=True, null=True
    )
    
    ramo_atividade = models.CharField(
        max_length=20,
        choices=[
            ('comercio', 'Comércio'),
            ('industria', 'Indústria'),
            ('servicos', 'Serviços'),
        ],
        blank=True, null=True
    )
    
    # CNAE
    cnae_principal = models.ForeignKey(
        'cadastros_gerais.CNAE',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='empresas_cnae_principal'
    )
```

---

## 🚀 Como Testar

### 1. Executar a ETL

```bash
# Modo teste (não salva)
python manage.py etl_03_1_pessoas_juridicas --dry-run

# Execução real
python manage.py etl_03_1_pessoas_juridicas

# Com limite (para testes rápidos)
python manage.py etl_03_1_pessoas_juridicas --limit 100
```

### 2. Validar Resultados

```bash
python scripts_debug/validar_etl03_regime_cnae.py
```

### 3. Testar na API

```bash
# Obter token
POST http://localhost:8000/api/auth/login/
{
  "username": "seu_usuario",
  "password": "sua_senha"
}

# Testar endpoint de categorias (usa regime_fiscal)
GET http://localhost:8000/api/gestao/carteira/categorias/
Authorization: Bearer {seu_token}
```

---

## 📊 Estatísticas Esperadas

Após executar a ETL, você verá:

```
=== RELATÓRIO FINAL - ETL 03_1 ===
Total de empresas processadas: 1500
Pessoas Jurídicas criadas: 200
Pessoas Jurídicas atualizadas: 1250
CNPJs inválidos: 10
CNAEs não encontrados: 15
Sem contabilidade mapeada: 25    ← NOVO!
Erros: 0
```

---

## ✅ Checklist de Validação

Use este checklist após executar a ETL:

- [ ] ETL executou sem erros críticos
- [ ] Campo `regime_tributario` preenchido (> 90% das empresas)
- [ ] Campo `regime_fiscal` preenchido para dashboards
- [ ] `simples_nacional` = True apenas para regime '1'
- [ ] Campo `cnae_principal` vinculado (> 80% das empresas)
- [ ] Apenas empresas com contratos foram importadas
- [ ] Estatística "Sem contabilidade mapeada" faz sentido
- [ ] Script de validação executou sem erros
- [ ] API `/api/gestao/carteira/categorias/` retorna dados
- [ ] Dashboard mostra distribuição por regime fiscal

---

## 🎨 Integração com Dashboard

### Endpoint Afetado

`/api/gestao/carteira/categorias/`

**Antes:** Dados simulados
**Agora:** Dados reais do banco

```python
# Agregar por regime fiscal
regime_fiscal_data = []
contratos_ativos = Contrato.objects.filter(
    contabilidade=contabilidade,
    ativo=True
)

for regime in ['simples', 'presumido', 'real']:
    # Buscar empresas com este regime
    empresas = PessoaJuridica.objects.filter(
        id__in=contratos_ativos.values_list('object_id'),
        regime_fiscal=regime
    ).count()
    
    regime_fiscal_data.append({
        'regime_fiscal': regime,
        'total_clientes': empresas,
        'percentual': (empresas / total * 100) if total > 0 else 0
    })
```

---

## 🔄 Próximos Passos

1. ✅ **Executar a ETL 03_1** com as novas alterações
2. ✅ **Validar os dados** usando o script de validação
3. ✅ **Testar a API** `/api/gestao/carteira/categorias/`
4. 🔲 **Atualizar o frontend** para exibir os dados reais
5. 🔲 **Criar filtros** por regime tributário nos dashboards
6. 🔲 **Adicionar visualizações** por CNAE (se necessário)

---

## 📞 Suporte

Se encontrar problemas:

1. ✅ Verificar logs da ETL
2. ✅ Executar script de validação
3. ✅ Consultar documentação: `docs/05_ETLS/ETL_03_1_REGIME_TRIBUTARIO_CNAE.md`
4. ✅ Revisar query SQL no Sybase manualmente
5. ✅ Validar prerequisitos (ETL de CNAEs e Contratos executados)

---

## 🎉 Conclusão

A ETL 03_1 agora:
- ✅ Captura regime tributário correto da fonte oficial (`EFPARAMETRO_VIGENCIA`)
- ✅ Importa CNAE com relacionamento FK correto
- ✅ Aplica Regra de Ouro com validação de contabilidade
- ✅ Está totalmente documentada
- ✅ Possui script de validação automatizado
- ✅ Está pronta para dashboards com dados reais

**Status: IMPLEMENTAÇÃO CONCLUÍDA ✅**
