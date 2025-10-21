# 📊 Status de Implementação da Lógica Superuser

## ✅ **IMPLEMENTADO** (3 endpoints)

### Módulo: Gestão > Carteira
- ✅ `GET /api/gestao/carteira/clientes/` - Lista de clientes
- ✅ `GET /api/gestao/carteira/categorias/` - Categorias por regime fiscal
- ✅ `GET /api/gestao/carteira/evolucao/` - Evolução mensal

**Resultado**: Superuser vê **TODOS os 2.186 contratos** do banco de dados

---

## ⏳ **PENDENTE** (41+ endpoints)

### 🔐 Módulo: Auth (2 endpoints)
**Arquivo**: `apps/api/auth/views.py`
- ⏳ Linha 43-44: Lista de usuários
- ⏳ Linha 76-77: Lista de usuários (duplicado?)

### 📊 Módulo: Dashboards (14+ endpoints)
**Arquivo**: `apps/api/dashboards/views.py`
- ⏳ Linha 40: Dashboard Demográfico - Indicadores
- ⏳ Linha 107: Dashboard Demográfico - Evolução mensal
- ⏳ Linha 163: Dashboard Demográfico - Distribuição etária
- ⏳ Linha 227: Dashboard Demográfico - Distribuição por gênero
- ⏳ Linha 270: Dashboard Demográfico - Distribuição por escolaridade
- ⏳ Linha 345: Dashboard Demográfico - Distribuição por cargo
- ⏳ Linha 432: Dashboard Demográfico - Colaboradores
- ⏳ Linha 489: Dashboard Organizacional - Cargos
- ⏳ Linha 521: Dashboard Organizacional - Departamentos
- ⏳ Linha 613: Dashboard Organizacional - Hierarquia
- ⏳ Linha 680: Dashboard Pessoal - Indicadores
- ⏳ Linha 747: Dashboard Contábil - Indicadores
- ⏳ Linha 811: Dashboard Fiscal - Indicadores
- ⏳ Linha 840: Dashboard Fiscal - Resumo por tipo
- ⏳ Linha 867: Dashboard Fiscal - Top clientes
- ⏳ Linha 898: Dashboard Fiscal - Produtos mais vendidos
- ⏳ Linha 932: Dashboard Fiscal - Distribuição por UF

### 👥 Módulo: Gestão (6+ endpoints)
**Arquivo**: `apps/api/gestao/views.py`
- ⏳ Linha 285: Lista de clientes
- ⏳ Linha 394: Detalhes do cliente
- ⏳ Linha 485: Sócios majoritários
- ⏳ Linha 558: Lista de usuários
- ⏳ Linha 584: Atividades por usuário
- ⏳ Linha 668: Produtividade por usuário

### 🔧 Módulo: Shared (Infraestrutura)
**Arquivo**: `apps/api/shared/viewsets.py`
- ⏳ Linha 52-53: ViewSet base com filtro por contabilidade
- ⏳ Linha 125: Método de criação
- ⏳ Linha 132: Método de atualização
- ⏳ Linha 186: Método de deleção

**Arquivo**: `apps/api/shared/permissions.py`
- ⏳ Linha 29: Permissão ContabilidadePermission
- ⏳ Linha 46: Verificação de objeto
- ⏳ Linha 62: Permissão IsOwnerOrContabilidade
- ⏳ Linha 83: Verificação de objeto
- ⏳ Linha 103: Permissão PodeAcessarModulo
- ⏳ Linha 124: Verificação de objeto
- ⏳ Linha 140: Permissão ContabilidadeAtivaPermission
- ⏳ Linha 160: Permissão MultiTenantPermission

---

## 🎯 **ESTRATÉGIA DE IMPLEMENTAÇÃO**

### **Fase 1: Módulos Prioritários** ✅ CONCLUÍDA
- ✅ Gestão > Carteira (3 endpoints) - **FEITO**

### **Fase 2: Dashboards** 🔄 PRÓXIMO
**Prioridade**: ALTA
**Motivo**: Frontend usa muito os dashboards
**Estimativa**: 14 endpoints

Todos os dashboards devem seguir o mesmo padrão:
```python
if usuario.is_superuser:
    logger.info(f"[DASHBOARD] ✅ Superuser '{usuario.username}' acessando TODOS os dados")
    dados = Modelo.objects.all()
else:
    if not hasattr(usuario, 'contabilidade') or not usuario.contabilidade:
        logger.error(f"[DASHBOARD] ❌ Usuário {usuario.username} não possui contabilidade")
        return Response({"error": "Usuário não possui contabilidade associada"}, status=400)
    
    contabilidade = usuario.contabilidade
    logger.info(f"[DASHBOARD] ✅ Usuário COMUM '{usuario.username}' - Contabilidade: '{contabilidade.razao_social}'")
    dados = Modelo.objects.filter(contabilidade=contabilidade)
```

### **Fase 3: Gestão Geral** ⏳
**Prioridade**: MÉDIA
**Estimativa**: 6 endpoints
- Lista de clientes
- Detalhes do cliente
- Sócios
- Usuários
- Atividades
- Produtividade

### **Fase 4: Auth** ⏳
**Prioridade**: BAIXA
**Estimativa**: 2 endpoints
- Lista de usuários (pode precisar de lógica diferente)

### **Fase 5: Infraestrutura (Shared)** ⏳
**Prioridade**: CRÍTICA (mas complexa)
**Estimativa**: Refatoração completa
**Motivo**: Afeta TODOS os outros módulos

Opções:
1. **Criar BaseViewSet com lógica de superuser embutida**
2. **Criar Middleware que adiciona lógica automaticamente**
3. **Criar decorador @check_superuser**

---

## 📝 **TEMPLATE DE IMPLEMENTAÇÃO**

### Para Views (ViewSet methods):
```python
def metodo(self, request):
    """
    Regra de Ouro Multi-Tenant:
    - Superuser: Vê TODOS os dados
    - Client: Vê apenas dados da sua contabilidade
    """
    try:
        usuario = request.user
        logger.info(f"[MODULO] Requisição recebida de usuário: {usuario.username}")
        
        if not usuario.is_authenticated:
            logger.error("[MODULO] Usuário não autenticado.")
            return Response({"error": "Authentication credentials were not provided."}, status=401)

        # Verificar se é superuser
        if usuario.is_superuser:
            logger.info(f"[MODULO] ✅ Superuser '{usuario.username}' acessando TODOS os dados")
            queryset = Modelo.objects.all()
        else:
            if not hasattr(usuario, 'contabilidade') or not usuario.contabilidade:
                logger.error(f"[MODULO] ❌ Usuário {usuario.username} não possui contabilidade")
                return Response({"error": "Usuário não possui contabilidade associada"}, status=400)
            
            contabilidade = usuario.contabilidade
            logger.info(f"[MODULO] ✅ Usuário COMUM '{usuario.username}' - Contabilidade: '{contabilidade.razao_social}'")
            queryset = Modelo.objects.filter(contabilidade=contabilidade)
        
        # Continuar com a lógica específica...
        
    except Exception as e:
        logger.exception(f"[MODULO] Erro crítico")
        return Response({"error": str(e)}, status=500)
```

---

## 🚀 **PRÓXIMOS PASSOS**

### 1. **TESTAR O ENDPOINT ATUAL** ✅
- Reiniciar servidor Django
- Testar no Postman com superuser `wando`
- Verificar se retorna 2.186 contratos

### 2. **IMPLEMENTAR DASHBOARDS** ⏳
Começar pelos mais usados:
1. Dashboard Demográfico - Indicadores
2. Dashboard Fiscal - Indicadores
3. Dashboard Contábil - Indicadores

### 3. **CRIAR HELPER/DECORATOR** ⏳
Para evitar repetição de código:
```python
# apps/api/shared/utils.py
def get_queryset_for_user(usuario, modelo, contabilidade_field='contabilidade'):
    """
    Retorna queryset baseado no tipo de usuário
    - Superuser: todos os dados
    - Client: apenas da sua contabilidade
    """
    if usuario.is_superuser:
        return modelo.objects.all()
    
    if not hasattr(usuario, 'contabilidade') or not usuario.contabilidade:
        raise ValueError("Usuário não possui contabilidade associada")
    
    filter_kwargs = {contabilidade_field: usuario.contabilidade}
    return modelo.objects.filter(**filter_kwargs)
```

### 4. **DOCUMENTAR** ⏳
- Atualizar `MAPEAMENTO_TABELAS_APIS_FRONTEND.md`
- Criar exemplos de uso para cada endpoint
- Documentar comportamento de superuser vs client

---

## 📊 **PROGRESSO GERAL**

```
Total de Endpoints: ~44
Implementados: 3 (7%)
Pendentes: 41 (93%)

Módulos:
├─ Gestão > Carteira: ✅ 3/3 (100%)
├─ Dashboards: ⏳ 0/14 (0%)
├─ Gestão: ⏳ 0/6 (0%)
├─ Auth: ⏳ 0/2 (0%)
└─ Shared: ⏳ 0/19 (0%)
```

---

## 🎯 **IMPACTO**

### ✅ **Com a implementação completa:**
- Superusers podem administrar TODO o sistema
- Relatórios consolidados de todas as contabilidades
- Auditoria completa do sistema
- Suporte técnico facilitado
- Análises globais possíveis

### ⚠️ **Risco de não implementar:**
- Superusers presos a uma única contabilidade
- Impossível fazer análises globais
- Dificuldade em suporte técnico
- Dados inconsistentes entre módulos

---

**Status**: Documentado em 21/10/2025  
**Última atualização**: Implementados 3 endpoints do módulo Carteira  
**Próxima ação**: Testar endpoint atual e implementar Dashboards
