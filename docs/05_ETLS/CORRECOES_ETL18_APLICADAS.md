# ✅ CORREÇÕES APLICADAS NA ETL 18 - USUÁRIOS

## 🔧 Problema Identificado

A ETL 18 estava tentando criar o modelo **Usuario** com campos que não existem:
- ❌ `contabilidade` (Usuario é global, sem FK para Contabilidade)
- ❌ `cnpj_empresa` (campo não existe no modelo)

## ✅ Correções Implementadas

### 1. Criação Correta do Usuario (GLOBAL)

**ANTES (❌ ERRADO):**
```python
Usuario.objects.update_or_create(
    contabilidade=contabilidade,  # ← Campo não existe!
    cnpj_empresa=cnpj_limpo,      # ← Campo não existe!
    id_legado=nome_usuario,
    defaults={...}
)
```

**DEPOIS (✅ CORRETO):**
```python
Usuario.objects.get_or_create(
    id_legado=nome_usuario,  # ← ÚNICO identificador global
    defaults={
        'nome_usuario': nome_usuario,
        'tipo_usuario': tipo_usuario,
        'ativo': True,
        'data_ultimo_acesso': self.gerar_data_ultimo_acesso(),
    }
)
```

### 2. Criação Correta de UsuarioContabilidade (MULTITENANT)

**ANTES (❌ INCOMPLETO):**
```python
UsuarioContabilidade.objects.update_or_create(
    contabilidade=contabilidade,
    usuario=usuario_obj,
    data_inicio=datetime(2023, 1, 1),  # ← datetime object
    defaults={
        'ativo': True,
        'modulos_acesso': [vinculo['CP_MODULO']],
    }
)
```

**DEPOIS (✅ COMPLETO):**
```python
UsuarioContabilidade.objects.update_or_create(
    contabilidade=contabilidade,
    usuario=usuario_obj,
    empresa_cnpj=cnpj_limpo,  # ← CNPJ da empresa
    defaults={
        'empresa_nome': empresa_nome,
        'data_inicio': datetime(2023, 1, 1).date(),  # ← date object
        'data_fim': None,
        'ativo': True,
        'modulos_acesso': [vinculo['CP_MODULO']],
    }
)
```

### 3. Correção na busca de contabilidades

**ANTES (❌ ERRO):**
```python
for data_inicio, data_termino, contabilidade in contratos:
    # ← Faltava desempacotar 'contrato' (4 elementos)
```

**DEPOIS (✅ CORRETO):**
```python
for data_inicio, data_termino, contabilidade, contrato in contratos:
    # ← Desempacota corretamente os 4 elementos
```

## 📊 Fluxo Corrigido

```
1. Busca CNPJ da empresa (cgce_emp)
   ↓
2. Limpa documento (limpar_documento)
   ↓
3. Busca contabilidades via REGRA DE OURO (historical_map)
   ↓
4. Cria Usuario GLOBAL (único por id_legado)
   ↓
5. Para cada contabilidade:
   ├─ Busca PessoaJuridica por CNPJ
   ├─ Cria UsuarioContabilidade (vínculo)
   └─ Cria UsuarioModulo (permissões)
```

## 🎯 Resultado Esperado

Agora a ETL 18 deve funcionar corretamente:

- ✅ 1 Usuario GLOBAL por id_legado
- ✅ N UsuarioContabilidade (1 por contabilidade)
- ✅ N UsuarioModulo (1 por módulo/contabilidade)
- ✅ Identificação por CNPJ (regra de ouro)
- ✅ Compatível com ETL 19 (logs)

## 🧪 Próximos Passos

1. **Testar ETL 18:**
   ```bash
   python manage.py etl_18_usuarios --limit 100
   ```

2. **Verificar dados criados:**
   ```python
   # Total de usuários globais
   Usuario.objects.count()
   
   # Vínculos por contabilidade
   UsuarioContabilidade.objects.values('contabilidade').annotate(total=Count('id'))
   
   # Módulos por usuário
   UsuarioModulo.objects.values('usuario').annotate(total=Count('id'))
   ```

3. **Executar ETL 19:**
   ```bash
   python manage.py etl_19_logs_unificado_corrigido --tipo todos --data-inicio 2019-01-01
   ```
