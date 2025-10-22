# 📋 Regra de Negócio: 1 Empresa = 1 Contrato Ativo por Contabilidade

## 🎯 Resumo

**Regra:** Cada empresa (Pessoa Jurídica) pode ter **apenas 1 contrato ativo** por contabilidade a qualquer momento.

## 📊 Cenários Permitidos

### ✅ Cenário 1: Empresa com 1 contrato ativo
```
Empresa A (CNPJ: 12345678000190)
└── Contabilidade XYZ
    └── Contrato #1 (ATIVO, 2020-01-01 até hoje)
```

### ✅ Cenário 2: Empresa com contratos históricos
```
Empresa B (CNPJ: 98765432000100)
└── Contabilidade ABC
    ├── Contrato #1 (INATIVO, 2018-01-01 até 2020-12-31)
    └── Contrato #2 (ATIVO, 2021-01-01 até hoje)
```

### ✅ Cenário 3: Empresa em múltiplas contabilidades
```
Empresa C (CNPJ: 11122233000144)
├── Contabilidade XYZ
│   └── Contrato #1 (ATIVO, 2019-01-01 até hoje)
└── Contabilidade ABC  
    └── Contrato #2 (ATIVO, 2020-01-01 até hoje)
```

### ❌ Cenário NÃO PERMITIDO: Múltiplos contratos ativos na mesma contabilidade
```
Empresa D (CNPJ: 55566677000188)
└── Contabilidade XYZ
    ├── Contrato #1 (ATIVO, 2018-01-01) ❌
    └── Contrato #2 (ATIVO, 2020-01-01) ❌
```

## 🐛 Problema Detectado

### Situação Atual no Banco de Dados

**Análise realizada em:** 21/10/2025

```
Total de contratos ativos: 1.550
Total de contratos ativos (PJ): 1.478
Empresas com múltiplos contratos ativos: 282 ❌
```

### Exemplos de Violação

| Empresa | CNPJ | Contabilidade | Contratos Ativos |
|---------|------|---------------|------------------|
| RCB CONSTRUTORA E INCORPORADORA LTDA | 16745090000180 | 38412169... | **4** ❌ |
| ANTONIO TELES FROTA JUNIOR & CIA LTDA | 01707986000105 | 38412169... | **5** ❌ |
| MARILIPE COMERCIO DE CONFECCOES LTDA | 05468044000164 | 7d12fd60... | **2** ❌ |

## 🔧 Correções Implementadas

### 1. Endpoint `/api/gestao/carteira/clientes/`

**ANTES:** Contava **contratos** (1.550)
**DEPOIS:** Conta **empresas únicas** (~1.196)

```python
# Antes (ERRADO)
total_clientes = todos_os_contratos.count()  # Conta contratos

# Depois (CORRETO)
empresas_unicas = todos_os_contratos.values('object_id').distinct().count()
```

### 2. Eliminação de Duplicatas na Lista

```python
# Controlar duplicatas ao montar lista
empresas_processadas = set()

for contrato in queryset.order_by('-ativo', '-data_inicio'):
    cliente = contrato.cliente
    
    if isinstance(cliente, PessoaJuridica) and cliente.id not in empresas_processadas:
        empresas_processadas.add(cliente.id)
        results.append({...})
```

**Lógica:**
- Ordena contratos por: **1º** Ativos primeiro, **2º** Mais recente
- Para cada empresa, pega apenas o **primeiro contrato** (mais relevante)
- Evita duplicatas na listagem

## 📊 Impacto nos Números

### Antes da Correção
```json
{
  "total_clientes": 2186,      // Contando CONTRATOS
  "clientes_ativos": 1550,     // Contando CONTRATOS ativos
  "clientes_inativos": 636
}
```

### Depois da Correção (esperado)
```json
{
  "total_clientes": 1904,      // Empresas ÚNICAS (2186 - 282 duplicatas)
  "clientes_ativos": 1196,     // Empresas com pelo menos 1 contrato ativo
  "clientes_inativos": 708     // Empresas sem contrato ativo
}
```

## 🔍 Scripts de Validação

### Script: `validar_regra_1_contrato_ativo.py`

```bash
python scripts_debug/validar_regra_1_contrato_ativo.py
```

**O que faz:**
- ✅ Conta total de contratos ativos
- ✅ Identifica empresas com múltiplos contratos ativos
- ✅ Lista os 10 primeiros casos
- ✅ Mostra detalhes de cada contrato

## 🛠️ Ações Recomendadas

### 1. Identificar a Causa Raiz

Possíveis causas para os 282 casos:
- ❓ Erro na importação da ETL
- ❓ Contratos não foram encerrados corretamente
- ❓ Renovações criaram novo contrato sem desativar o antigo
- ❓ Filiais foram cadastradas como contratos separados

### 2. Decidir Estratégia de Limpeza

**Opção A: Manter apenas o contrato mais recente**
```sql
-- Para cada empresa com duplicatas:
-- Desativar contratos antigos, manter apenas o mais recente
```

**Opção B: Consolidar contratos**
```sql
-- Mesclar informações dos contratos duplicados
-- em um único contrato "correto"
```

**Opção C: Análise manual**
```sql
-- Revisar caso a caso com equipe de negócio
-- Algumas duplicatas podem ser legítimas (ex: filiais)
```

### 3. Implementar Validação na Aplicação

**No modelo `Contrato`:**
```python
class Contrato(models.Model):
    # ... campos ...
    
    class Meta:
        # Garantir unicidade: 1 empresa ativa por contabilidade
        constraints = [
            models.UniqueConstraint(
                fields=['content_type', 'object_id', 'contabilidade'],
                condition=Q(ativo=True),
                name='unique_active_contract_per_company_accounting'
            )
        ]
    
    def save(self, *args, **kwargs):
        if self.ativo:
            # Desativar outros contratos ativos da mesma empresa/contabilidade
            Contrato.objects.filter(
                content_type=self.content_type,
                object_id=self.object_id,
                contabilidade=self.contabilidade,
                ativo=True
            ).exclude(id=self.id).update(ativo=False)
        
        super().save(*args, **kwargs)
```

## 📝 Documentação da API

### Endpoint Atualizado

**GET** `/api/gestao/carteira/clientes/`

**Mudanças:**
- ✅ Agora conta **empresas únicas** ao invés de contratos
- ✅ Elimina duplicatas na listagem
- ✅ Prioriza contratos ativos e mais recentes
- ✅ Retorna `id` da empresa, não do contrato

**Response:**
```json
{
  "count": 1196,
  "results": [
    {
      "id": "uuid-da-empresa",  // ⚠️ Mudou: antes era ID do contrato
      "razao_social": "EMPRESA A LTDA",
      "cnpj": "12345678000190",
      "status": "ATIVO",
      "regime_fiscal": "simples",
      "data_inicio": "2020-01-15",
      "inadimplente": false
    }
  ],
  "summary": {
    "total_clientes": 1196,      // ⚠️ Agora conta empresas únicas
    "clientes_ativos": 1150,
    "clientes_inativos": 46,
    "clientes_novos": 6,
    "percentual_ativo": 96.15
  }
}
```

## 🎯 Próximos Passos

1. ✅ **Correção implementada na API** - Contar empresas únicas
2. 🔲 **Análise de dados** - Entender por que existem duplicatas
3. 🔲 **Limpeza de dados** - Decidir estratégia e executar
4. 🔲 **Constraint no banco** - Prevenir novas duplicatas
5. 🔲 **Validação na ETL** - Garantir importação correta
6. 🔲 **Testes** - Validar cenários de renovação de contrato

## 📚 Referências

- **Modelo:** `apps/pessoas/models.py` → `Contrato`
- **API:** `apps/api/gestao/carteira/views.py` → `CarteiraViewSet.clientes()`
- **Validação:** `scripts_debug/validar_regra_1_contrato_ativo.py`

---

**Última atualização:** 21/10/2025  
**Status:** Correção implementada na API, aguardando limpeza de dados
