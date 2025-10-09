# 🔧 Configuração CORS para Frontend - GESTK

## ✅ **Configurações Implementadas**

### **1. Configurações CORS no Django (settings.py)**

```python
# =============================================================================
# CONFIGURAÇÕES CORS E SEGURANÇA
# =============================================================================

# CORS - Configuração para desenvolvimento
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",      # GESTK Admin App
    "http://127.0.0.1:3000",      # GESTK Admin App (alternativo)
    "http://localhost:3001",      # GESTK Client App
    "http://127.0.0.1:3001",      # GESTK Client App (alternativo)
    "http://localhost:3002",      # GESTK Extra App (se houver)
    "http://127.0.0.1:3002",      # GESTK Extra App (alternativo)
]

# Headers personalizados do GESTK
CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
    'x-contabilidade-id',  # Para multi-tenancy
    'x-app-context',       # Para contexto da aplicação
]

# Métodos permitidos
CORS_ALLOW_METHODS = [
    'DELETE',
    'GET',
    'OPTIONS',
    'PATCH',
    'POST',
    'PUT',
]

# Permitir cookies (se necessário)
CORS_ALLOW_CREDENTIALS = True

# CSRF - Configuração
CSRF_TRUSTED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3001",
    "http://localhost:3002",
    "http://127.0.0.1:3002",
]

# Configuração de sessão
SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_HTTPONLY = True
```

### **2. Configurações de Hosts Permitidos**

```python
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1,0.0.0.0', cast=lambda v: [s.strip() for s in v.split(',')])
```

### **3. Middleware CORS Configurado**

```python
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',  # ✅ Posição correta
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'apps.api.shared.middleware.MultiTenantContextMiddleware',
    'apps.api.shared.middleware.TenantAuditMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'simple_history.middleware.HistoryRequestMiddleware',
]
```

## 🚀 **Como Testar a Configuração**

### **1. Reiniciar o Servidor Django**

```bash
# Parar o servidor atual (Ctrl+C)
# Reiniciar o servidor
python manage.py runserver
```

### **2. Testar CORS com cURL**

```bash
# Teste de CORS preflight
curl -X OPTIONS \
  -H "Origin: http://localhost:3000" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: authorization,content-type" \
  http://localhost:8000/api/auth/login/

# Teste de requisição real
curl -X POST \
  -H "Origin: http://localhost:3000" \
  -H "Content-Type: application/json" \
  -d '{"username":"test@example.com","password":"password123"}' \
  http://localhost:8000/api/auth/login/
```

### **3. Testar no Navegador**

```javascript
// Teste no console do navegador (F12)
fetch('http://localhost:8000/api/auth/login/', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    username: 'test@example.com',
    password: 'password123'
  })
})
.then(response => response.json())
.then(data => console.log('Success:', data))
.catch(error => console.error('Error:', error));
```

## 🔧 **Configuração do Frontend**

### **1. Variáveis de Ambiente (.env.local)**

```bash
# Frontend Admin App
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_APP_CONTEXT=admin
NEXTAUTH_SECRET=admin-secret-key
NEXTAUTH_URL=http://localhost:3000

# Frontend Client App
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_APP_CONTEXT=client
NEXTAUTH_SECRET=client-secret-key
NEXTAUTH_URL=http://localhost:3001
```

### **2. Cliente API (Axios)**

```typescript
// lib/api-client.ts
import axios from 'axios';

const apiClient = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true, // Para enviar cookies se necessário
});

// Interceptor para adicionar headers customizados
apiClient.interceptors.request.use((config) => {
  // Adicionar token JWT
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  
  // Adicionar headers customizados do GESTK
  const contabilidadeId = localStorage.getItem('contabilidade_id');
  if (contabilidadeId) {
    config.headers['X-Contabilidade-ID'] = contabilidadeId;
  }
  
  const appContext = process.env.NEXT_PUBLIC_APP_CONTEXT;
  if (appContext) {
    config.headers['X-App-Context'] = appContext;
  }
  
  return config;
});

export default apiClient;
```

## 🚨 **Solução de Problemas**

### **1. Erro: "Forbidden origin checking failed"**

**Causa**: A origem do frontend não está na lista `CORS_ALLOWED_ORIGINS`

**Solução**: Adicionar a URL do frontend:
```python
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",  # ✅ Adicionar se não estiver
    "http://localhost:3001",  # ✅ Adicionar se não estiver
]
```

### **2. Erro: "Request header field x-contabilidade-id is not allowed"**

**Causa**: Header customizado não está permitido

**Solução**: Adicionar ao `CORS_ALLOW_HEADERS`:
```python
CORS_ALLOW_HEADERS = [
    # ... outros headers ...
    'x-contabilidade-id',  # ✅ Adicionar
    'x-app-context',       # ✅ Adicionar
]
```

### **3. Erro: "DisallowedHost at /api/..."**

**Causa**: Host não está em `ALLOWED_HOSTS`

**Solução**: Adicionar o host:
```python
ALLOWED_HOSTS = [
    'localhost',
    '127.0.0.1',
    '0.0.0.0',  # ✅ Adicionar se necessário
]
```

### **4. Erro: "CSRF verification failed"**

**Causa**: CSRF não configurado para APIs JWT

**Solução**: Adicionar ao `CSRF_TRUSTED_ORIGINS`:
```python
CSRF_TRUSTED_ORIGINS = [
    "http://localhost:3000",  # ✅ Adicionar
    "http://localhost:3001",  # ✅ Adicionar
]
```

## 📋 **Checklist de Verificação**

- [ ] ✅ `corsheaders` instalado (`pip install django-cors-headers`)
- [ ] ✅ `corsheaders` em `INSTALLED_APPS`
- [ ] ✅ `CorsMiddleware` em `MIDDLEWARE` (posição correta)
- [ ] ✅ `CORS_ALLOWED_ORIGINS` configurado com URLs do frontend
- [ ] ✅ `CORS_ALLOW_HEADERS` inclui headers customizados
- [ ] ✅ `CORS_ALLOW_METHODS` inclui métodos necessários
- [ ] ✅ `CORS_ALLOW_CREDENTIALS = True` (se necessário)
- [ ] ✅ `CSRF_TRUSTED_ORIGINS` configurado
- [ ] ✅ `ALLOWED_HOSTS` inclui hosts necessários
- [ ] ✅ Servidor Django reiniciado
- [ ] ✅ Frontend configurado com URL correta da API

## 🎯 **Resultado Esperado**

Após aplicar essas configurações:

- ✅ **Sem erros de CORS** no console do navegador
- ✅ **Requisições funcionando** entre frontend e backend
- ✅ **Headers customizados** sendo aceitos
- ✅ **Autenticação JWT** funcionando
- ✅ **Multi-tenancy** funcionando com headers customizados

## 🔄 **Próximos Passos**

1. **Reiniciar o servidor Django** com as novas configurações
2. **Testar uma requisição simples** do frontend
3. **Verificar o console** do navegador para erros
4. **Implementar autenticação** se necessário
5. **Testar todos os endpoints** da API

---

**Status**: ✅ Configurações implementadas  
**Última atualização**: Janeiro 2025  
**Versão**: 1.0
