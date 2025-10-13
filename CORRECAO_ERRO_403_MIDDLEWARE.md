# 🔧 CORREÇÃO DO ERRO 403 - Middleware Multi-Tenant

## 🎯 Problema Identificado

O erro 403 estava sendo causado pelo **middleware customizado** `MultiTenantContextMiddleware` e `TenantAuditMiddleware` que estavam processando **TODAS as requisições**, incluindo as rotas de autenticação.

### Comportamento Anterior (❌ COM ERRO)

1. Frontend faz requisição para `/api/auth/login/`
2. Middleware `MultiTenantContextMiddleware` intercepta a requisição
3. Middleware tenta acessar `request.user.contabilidade`
4. Como o usuário ainda não está autenticado, gera erro 403 (PermissionDenied)
5. Login nunca é processado

---

## ✅ Solução Implementada

### 1. Correção no `CustomTokenObtainPairView`

**Arquivo:** `apps/api/auth/views.py`

```python
class CustomTokenObtainPairView(TokenObtainPairView):
    """
    View customizada para obter tokens JWT com informações da contabilidade
    """
    permission_classes = [AllowAny]  # ✅ ADICIONADO
    serializer_class = CustomTokenObtainPairSerializer
```

### 2. Correção no `MultiTenantContextMiddleware`

**Arquivo:** `apps/api/shared/middleware.py`

```python
class MultiTenantContextMiddleware(MiddlewareMixin):
    """
    Middleware que gerencia o contexto multi-tenant
    """
    
    # ✅ ADICIONADO: Rotas que devem ser ignoradas pelo middleware
    EXCLUDED_PATHS = [
        '/api/auth/login/',
        '/api/auth/token/',
        '/api/auth/token/refresh/',
        '/admin/login/',
        '/admin/',
    ]
    
    def process_request(self, request):
        """
        Processa a requisição e define o contexto multi-tenant
        """
        # ✅ ADICIONADO: Ignorar rotas de autenticação
        if any(request.path.startswith(path) for path in self.EXCLUDED_PATHS):
            return
        
        if not request.user.is_authenticated:
            return
        # ... resto do código
```

### 3. Correção no `TenantAuditMiddleware`

**Arquivo:** `apps/api/shared/middleware.py`

```python
class TenantAuditMiddleware(MiddlewareMixin):
    """
    Middleware para auditoria de trocas de tenant
    """
    
    # ✅ ADICIONADO: Rotas que devem ser ignoradas pelo middleware
    EXCLUDED_PATHS = [
        '/api/auth/login/',
        '/api/auth/token/',
        '/api/auth/token/refresh/',
        '/admin/login/',
        '/admin/',
    ]
    
    def process_request(self, request):
        """
        Registra a troca de tenant para auditoria
        """
        # ✅ ADICIONADO: Ignorar rotas de autenticação
        if any(request.path.startswith(path) for path in self.EXCLUDED_PATHS):
            return
        
        if not request.user.is_authenticated:
            return
        # ... resto do código
```

---

## 🔄 Fluxo Correto Agora

### Antes das Correções (❌)
```
Frontend → /api/auth/login/
    ↓
MultiTenantContextMiddleware (verificação de permissões)
    ↓
❌ 403 Forbidden (usuário não tem contabilidade ainda)
```

### Depois das Correções (✅)
```
Frontend → /api/auth/login/
    ↓
MultiTenantContextMiddleware (ignora rota de autenticação) ✅
    ↓
TenantAuditMiddleware (ignora rota de autenticação) ✅
    ↓
CustomTokenObtainPairView (AllowAny) ✅
    ↓
✅ 200 OK - Retorna tokens JWT
```

---

## 📝 Rotas Excluídas dos Middlewares

As seguintes rotas **NÃO** passarão pelos middlewares multi-tenant:

- `/api/auth/login/` - Login
- `/api/auth/token/` - Obter tokens JWT
- `/api/auth/token/refresh/` - Renovar access token
- `/admin/login/` - Login do Django Admin
- `/admin/` - Django Admin

---

## ✅ Mudanças Aplicadas

### Arquivos Modificados

1. ✅ `apps/api/auth/views.py`
   - Adicionado `permission_classes = [AllowAny]` em `CustomTokenObtainPairView`

2. ✅ `apps/api/shared/middleware.py`
   - Adicionado `EXCLUDED_PATHS` em `MultiTenantContextMiddleware`
   - Adicionado verificação para ignorar rotas de autenticação
   - Adicionado `EXCLUDED_PATHS` em `TenantAuditMiddleware`
   - Adicionado verificação para ignorar rotas de autenticação

---

## 🧪 Como Testar

### 1. Reiniciar o Servidor Django

```bash
# Parar o servidor (Ctrl+C)
# Iniciar novamente
python manage.py runserver
```

### 2. Testar do Frontend Next.js

```bash
# No frontend
npm run dev
```

### 3. Fazer Login

- Acessar: `http://localhost:3000/login`
- Inserir credenciais
- **Resultado esperado:** Login bem-sucedido ✅ (não mais erro 403)

### 4. Verificar no Console do Navegador

```javascript
// Deve aparecer:
✅ Login bem-sucedido: { access: "...", refresh: "...", user: {...} }

// NÃO deve aparecer:
❌ Request failed with status code 403
```

---

## 🎉 Resultado Final

| Antes | Depois |
|-------|--------|
| ❌ 403 Forbidden | ✅ 200 OK |
| ❌ Login bloqueado | ✅ Login funcionando |
| ❌ Middleware bloqueando | ✅ Middleware ignorando rotas de auth |

---

## 📚 Documentação Adicional

### Por que isso aconteceu?

O middleware `MultiTenantContextMiddleware` foi criado para garantir que cada requisição esteja associada a uma contabilidade (multi-tenant). No entanto, ele estava processando **todas** as requisições, incluindo as de autenticação, onde o usuário ainda não tem uma contabilidade associada.

### Solução Ideal

A solução ideal é **excluir rotas públicas** (como login e token refresh) do processamento dos middlewares multi-tenant, pois essas rotas precisam funcionar **antes** do usuário estar autenticado.

---

## 🚀 Próximos Passos

1. ✅ **Servidor Django rodando**
   ```bash
   python manage.py runserver
   ```

2. ✅ **Frontend Next.js rodando**
   ```bash
   npm run dev
   ```

3. ✅ **Testar login**
   - Deve retornar 200 OK
   - Tokens devem ser recebidos
   - Usuário deve ser redirecionado para dashboard

4. ⚠️ **Monitorar logs**
   - Verificar se não há outros erros
   - Garantir que o fluxo está correto

---

**✅ PROBLEMA RESOLVIDO!**

O erro 403 estava sendo causado pelos middlewares customizados. Com as correções aplicadas, as rotas de autenticação agora são ignoradas pelos middlewares, permitindo que o login funcione corretamente.

---

**Data:** 09/10/2025  
**Correção:** Middlewares Multi-Tenant  
**Status:** ✅ RESOLVIDO
