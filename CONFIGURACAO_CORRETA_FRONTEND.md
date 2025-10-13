# 🔧 Configuração Correta do Frontend Next.js

## ✅ Backend Funcionando

O teste confirma que o backend está OK:
```
✅ Status Code: 400 (esperado para credenciais vazias)
✅ CORS: access-control-allow-origin: http://localhost:3000
✅ Endpoint: http://localhost:8000/api/auth/login/
```

---

## 🛠️ Configuração do Frontend (SEM PROXY)

### 1. Criar/Atualizar `apiClient.ts`

```typescript
// src/lib/api/apiClient.ts
import axios, { AxiosError } from 'axios';

// URL base do Django (SEM proxy do Next.js)
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// Criar instância do Axios
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true, // Importante para CORS
  timeout: 10000, // 10 segundos
});

// Interceptor para adicionar token nas requisições
apiClient.interceptors.request.use(
  (config) => {
    if (typeof window !== 'undefined') {
      const token = localStorage.getItem('access_token');
      if (token && config.headers) {
        config.headers.Authorization = `Bearer ${token}`;
      }
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Interceptor para tratar erros e refresh token
apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config;

    // Se erro 401 e não é a rota de refresh
    if (error.response?.status === 401 && originalRequest && !originalRequest.url?.includes('/auth/token/refresh/')) {
      try {
        // Tentar renovar o token
        const refreshToken = localStorage.getItem('refresh_token');
        if (refreshToken) {
          const response = await axios.post(
            `${API_BASE_URL}/api/auth/token/refresh/`,
            { refresh: refreshToken }
          );

          const { access } = response.data;
          localStorage.setItem('access_token', access);

          // Retentar requisição original
          if (originalRequest.headers) {
            originalRequest.headers.Authorization = `Bearer ${access}`;
          }
          return apiClient(originalRequest);
        }
      } catch (refreshError) {
        // Refresh token inválido, fazer logout
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        localStorage.removeItem('user');
        window.location.href = '/login';
      }
    }

    return Promise.reject(error);
  }
);

export default apiClient;
```

---

### 2. Atualizar `auth.service.ts`

```typescript
// src/lib/api/services/auth.service.ts
import apiClient from '../apiClient';

export interface LoginData {
  username: string;
  password: string;
}

export interface User {
  id: number;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  tipo_usuario: string;
  contabilidade_id?: string;
  contabilidade_razao_social?: string;
}

export interface LoginResponse {
  access: string;
  refresh: string;
  user: User;
}

export class AuthService {
  /**
   * Faz login no sistema
   */
  static async login(credentials: LoginData): Promise<LoginResponse> {
    console.log('🔵 Tentando login:', { username: credentials.username });
    console.log('🔵 URL:', apiClient.defaults.baseURL + '/api/auth/login/');
    
    try {
      const response = await apiClient.post<LoginResponse>(
        '/api/auth/login/',
        credentials
      );

      console.log('✅ Login bem-sucedido:', response.status);

      // Salvar tokens no localStorage
      if (typeof window !== 'undefined') {
        localStorage.setItem('access_token', response.data.access);
        localStorage.setItem('refresh_token', response.data.refresh);
        localStorage.setItem('user', JSON.stringify(response.data.user));
      }

      return response.data;
    } catch (error: any) {
      console.error('❌ Erro no login:');
      console.error('❌ Status:', error.response?.status);
      console.error('❌ URL:', error.config?.url);
      console.error('❌ Data:', error.response?.data);
      
      // Lançar erro com mensagem amigável
      const message = error.response?.data?.non_field_errors?.[0] 
        || error.response?.data?.detail
        || 'Erro ao fazer login';
      
      throw new Error(message);
    }
  }

  /**
   * Faz logout do sistema
   */
  static async logout(): Promise<void> {
    const refreshToken = localStorage.getItem('refresh_token');
    
    if (refreshToken) {
      try {
        await apiClient.post('/api/auth/logout/', {
          refresh: refreshToken,
        });
      } catch (error) {
        console.error('Erro ao fazer logout no backend:', error);
      }
    }

    // Limpar storage
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('user');
  }

  /**
   * Obtém informações do usuário atual
   */
  static async getCurrentUser(): Promise<User> {
    const response = await apiClient.get<User>('/api/auth/me/');
    return response.data;
  }

  /**
   * Verifica se está autenticado
   */
  static isAuthenticated(): boolean {
    if (typeof window === 'undefined') return false;
    return !!localStorage.getItem('access_token');
  }

  /**
   * Obtém usuário do storage
   */
  static getStoredUser(): User | null {
    if (typeof window === 'undefined') return null;
    const userStr = localStorage.getItem('user');
    return userStr ? JSON.parse(userStr) : null;
  }
}
```

---

### 3. Verificar `.env.local`

```bash
# .env.local (raiz do projeto Next.js)
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

### 4. Remover Rewrites do `next.config.js`

```javascript
// next.config.js
/** @type {import('next').NextConfig} */
const nextConfig = {
  // NÃO usar rewrites para API
  // Deixar o Next.js chamar diretamente http://localhost:8000
}

module.exports = nextConfig
```

---

### 5. Atualizar Página de Login

```typescript
// src/app/(auth)/login/page.tsx
'use client';

import { useState, FormEvent } from 'react';
import { useRouter } from 'next/navigation';
import { AuthService } from '@/lib/api/services/auth.service';
import { toast } from 'sonner'; // ou seu sistema de toast

export default function LoginPage() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setLoading(true);

    try {
      console.log('🔵 Iniciando processo de login...');
      
      const response = await AuthService.login({ username, password });
      
      console.log('✅ Login realizado com sucesso!');
      console.log('✅ User:', response.user);
      
      toast.success('Login realizado com sucesso!');
      
      // Redirecionar para dashboard
      router.push('/dashboard');
    } catch (error: any) {
      console.error('❌ Falha no login:', error);
      toast.error(error.message || 'Falha na autenticação');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center">
      <form onSubmit={onSubmit} className="w-full max-w-md space-y-4 p-8 bg-white rounded-lg shadow">
        <h1 className="text-2xl font-bold text-center">Login</h1>
        
        <div>
          <label className="block text-sm font-medium mb-1">
            Usuário
          </label>
          <input
            type="text"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            className="w-full px-3 py-2 border rounded"
            required
          />
        </div>

        <div>
          <label className="block text-sm font-medium mb-1">
            Senha
          </label>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full px-3 py-2 border rounded"
            required
          />
        </div>

        <button
          type="submit"
          disabled={loading}
          className="w-full py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
        >
          {loading ? 'Entrando...' : 'Entrar'}
        </button>
      </form>
    </div>
  );
}
```

---

## 🧪 Passos para Testar

### 1. Parar e limpar tudo

```bash
# No terminal do Next.js
# Ctrl+C para parar

# Limpar cache
rm -rf .next

# Limpar node_modules (opcional, se problema persistir)
# rm -rf node_modules
# npm install
```

### 2. Verificar arquivo `.env.local`

```bash
# Criar/editar .env.local
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### 3. Reiniciar Next.js

```bash
npm run dev
```

### 4. Limpar cache do navegador

- Abrir DevTools (F12)
- Application → Clear Storage → Clear site data
- Ou usar modo anônimo (Ctrl+Shift+N)

### 5. Testar login

- Acessar: `http://localhost:3000/login`
- Abrir DevTools → Network tab
- Fazer login
- Verificar:
  - ✅ URL chamada: `http://localhost:8000/api/auth/login/`
  - ✅ Status: 200 (sucesso) ou 400 (credenciais inválidas)
  - ❌ Se 403: ainda há problema

---

## 🔍 Debug Adicional

Se ainda retornar 403, adicione logs no console:

```typescript
// Antes de chamar login
console.log('🔵 Config do apiClient:', {
  baseURL: apiClient.defaults.baseURL,
  headers: apiClient.defaults.headers,
  withCredentials: apiClient.defaults.withCredentials,
});
```

E verifique no Network tab do DevTools:
- Request URL
- Request Method
- Request Headers (deve ter Origin)
- Response Headers (deve ter access-control-allow-origin)

---

**✅ Com essas configurações, o erro 403 deve ser resolvido!**

O problema estava na configuração do proxy/rewrites do Next.js. Chamando diretamente o Django resolve.
