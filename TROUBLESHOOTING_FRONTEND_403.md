# 🔧 TROUBLESHOOTING - Erro 403 no Frontend Next.js

## ✅ Backend Funcionando

O backend Django está funcionando perfeitamente:
- ✅ Status: 200/400 (não 403)
- ✅ CORS configurado
- ✅ Middlewares corrigidos
- ✅ Endpoint `/api/auth/login/` acessível

---

## ❌ Problema: Frontend ainda retorna 403

### Possíveis Causas

#### 1. **Cache do Navegador/Next.js**

O navegador ou Next.js pode estar usando respostas antigas em cache.

**Solução:**

```bash
# No frontend Next.js
# Limpar cache e reiniciar
rm -rf .next
npm run dev
```

Ou no navegador:
- Abrir DevTools (F12)
- Aba Network
- Marcar "Disable cache"
- Fazer Ctrl+Shift+R (hard refresh)

---

#### 2. **Configuração de Proxy/Rewrites Incorreta**

Se o Next.js está usando proxy reverso, pode estar redirecionando errado.

**Verificar `next.config.js`:**

```javascript
// ❌ INCORRETO - Pode causar problemas
module.exports = {
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: 'http://localhost:8000/api/:path*',
      },
    ]
  },
}

// ✅ MELHOR - Chamar diretamente
// Remover rewrites e usar URL completa no código
```

**Solução Recomendada:**

No seu `auth.service.ts`, use a URL completa:

```typescript
// src/lib/api/apiClient.ts ou similar
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true, // Para CORS com credenciais
});
```

---

#### 3. **apiClient sem configuração de CORS**

Seu `apiClient` pode não estar enviando os headers corretos.

**Verificar configuração do Axios:**

```typescript
// src/lib/api/apiClient.ts
import axios from 'axios';

const apiClient = axios.create({
  baseURL: 'http://localhost:8000', // URL direta, SEM proxy
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true, // ✅ IMPORTANTE para CORS
});

// Interceptor para adicionar token (depois do login)
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export default apiClient;
```

---

#### 4. **Endpoint incorreto no frontend**

Verificar se o endpoint está correto:

```typescript
// ❌ INCORRETO (com proxy)
const response = await apiClient.post('/api/auth/login/', credentials);

// ✅ CORRETO (sem proxy, com baseURL)
const response = await apiClient.post('/api/auth/login/', credentials);
// Com baseURL configurado como 'http://localhost:8000'
```

---

#### 5. **Variáveis de Ambiente**

Verificar se as variáveis de ambiente estão corretas:

**`.env.local` (Next.js):**

```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## 🧪 Teste Manual com cURL

Para confirmar que o backend está funcionando, teste com cURL:

```bash
# Teste OPTIONS (CORS preflight)
curl -X OPTIONS http://localhost:8000/api/auth/login/ \
  -H "Origin: http://localhost:3000" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: content-type" \
  -v

# Teste POST (login vazio, deve retornar 400)
curl -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -H "Origin: http://localhost:3000" \
  -d '{"username":"","password":""}' \
  -v
```

**Resultado esperado:**
- OPTIONS: Status 200
- POST: Status 400 (validação de campos)

---

## 🔍 Debug no Frontend

### 1. Adicionar logs no auth.service.ts

```typescript
static async login(credentials: LoginData): Promise<LoginResponse> {
  console.log('🔵 Iniciando login...');
  console.log('🔵 URL:', apiClient.defaults.baseURL);
  console.log('🔵 Credentials:', { username: credentials.username });
  
  try {
    const response = await apiClient.post<LoginResponse>(
      '/api/auth/login/', 
      credentials
    );
    
    console.log('✅ Login bem-sucedido:', response.status);
    console.log('✅ Response:', response.data);
    
    return response.data;
  } catch (error) {
    console.error('❌ Erro no login:');
    console.error('❌ Status:', error.response?.status);
    console.error('❌ Data:', error.response?.data);
    console.error('❌ Headers:', error.response?.headers);
    throw error;
  }
}
```

### 2. Verificar Network Tab (DevTools)

Abrir DevTools → Network → Fazer login:

**Verificar:**
- [ ] URL chamada: `http://localhost:8000/api/auth/login/` (não deve ter proxy)
- [ ] Method: POST
- [ ] Status Code: 403 ou 400?
- [ ] Request Headers: Tem `Origin: http://localhost:3000`?
- [ ] Response Headers: Tem `access-control-allow-origin`?

---

## 🚀 Solução Completa (Sem Proxy)

### 1. **Remover Rewrites do Next.js**

```javascript
// next.config.js
/** @type {import('next').NextConfig} */
const nextConfig = {
  // Remover rewrites/proxies
}

module.exports = nextConfig
```

### 2. **Configurar apiClient corretamente**

```typescript
// src/lib/api/apiClient.ts
import axios from 'axios';

const apiClient = axios.create({
  baseURL: 'http://localhost:8000', // URL direta do Django
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true, // Para enviar/receber cookies
});

export default apiClient;
```

### 3. **auth.service.ts**

```typescript
// src/lib/api/services/auth.service.ts
import apiClient from '../apiClient';

export class AuthService {
  static async login(credentials: LoginData): Promise<LoginResponse> {
    const response = await apiClient.post<LoginResponse>(
      '/api/auth/login/', // Relativo ao baseURL
      credentials
    );
    
    // Salvar tokens
    if (typeof window !== 'undefined') {
      localStorage.setItem('access_token', response.data.access);
      localStorage.setItem('refresh_token', response.data.refresh);
    }
    
    return response.data;
  }
}
```

### 4. **Reiniciar Next.js**

```bash
# Parar servidor (Ctrl+C)
# Limpar cache
rm -rf .next
# Reiniciar
npm run dev
```

### 5. **Limpar cache do navegador**

- F12 → Application → Clear storage
- Ou usar modo anônimo

---

## ✅ Checklist de Verificação

- [ ] Backend Django rodando: `http://localhost:8000`
- [ ] Teste direto funciona: `python test_login_direct.py` retorna 400
- [ ] Next.js sem rewrites/proxies
- [ ] `apiClient` com `baseURL: 'http://localhost:8000'`
- [ ] `apiClient` com `withCredentials: true`
- [ ] Cache do Next.js limpo (`.next` removido)
- [ ] Cache do navegador limpo
- [ ] Network tab mostra URL correta
- [ ] Network tab mostra headers CORS

---

## 🆘 Se ainda não funcionar

1. **Capture a requisição completa:**
   - DevTools → Network → Clique na requisição
   - Copie: URL, Headers, Response

2. **Teste com Postman/Insomnia:**
   ```
   POST http://localhost:8000/api/auth/login/
   Headers:
     Content-Type: application/json
     Origin: http://localhost:3000
   Body:
     {
       "username": "admin",
       "password": "senha"
     }
   ```

3. **Verifique logs do Django:**
   - Janela onde o Django está rodando
   - Deve mostrar: `POST /api/auth/login/` HTTP/1.1" 200 ou 400

---

**✅ O backend está funcionando! O problema está na configuração do frontend Next.js.**

**Próximo passo:** Verificar/corrigir a configuração do `apiClient` no frontend.
