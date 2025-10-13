# 🔌 Integração Frontend Next.js → Backend Django

## ✅ Backend Configurado

O backend Django já está 100% configurado e testado para aceitar requisições do frontend Next.js.

---

## 📝 Instruções para o Frontend

### 1. Criar um Usuário no Django (Backend)

Primeiro, crie um usuário para testar:

```bash
# No terminal do backend
cd c:\GitHub\gestk-back
python manage.py createsuperuser
```

Siga as instruções e crie:
- Username: `admin` (ou o que preferir)
- Email: `admin@gestk.com`
- Password: `sua_senha_segura`

---

### 2. Configuração do Next.js

#### A) Service de Autenticação (`lib/auth.ts`)

```typescript
// lib/auth.ts
const API_URL = 'http://localhost:8000';

export interface LoginCredentials {
  username: string;
  password: string;
}

export interface LoginResponse {
  access: string;
  refresh: string;
  user: {
    id: number;
    username: string;
    email: string;
    first_name: string;
    last_name: string;
    tipo_usuario: string;
    contabilidade_id: string;
    contabilidade_razao_social: string;
  };
}

export interface User {
  id: number;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  tipo_usuario: string;
  contabilidade_id: string;
  contabilidade_razao_social: string;
}

/**
 * Faz login no sistema
 */
export async function login(credentials: LoginCredentials): Promise<LoginResponse> {
  const response = await fetch(`${API_URL}/api/auth/login/`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(credentials),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.non_field_errors?.[0] || 'Erro ao fazer login');
  }

  const data = await response.json();
  
  // Armazenar tokens
  localStorage.setItem('access_token', data.access);
  localStorage.setItem('refresh_token', data.refresh);
  localStorage.setItem('user', JSON.stringify(data.user));

  return data;
}

/**
 * Faz logout do sistema
 */
export async function logout(): Promise<void> {
  const refreshToken = localStorage.getItem('refresh_token');
  const accessToken = localStorage.getItem('access_token');

  if (refreshToken && accessToken) {
    try {
      await fetch(`${API_URL}/api/auth/logout/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${accessToken}`,
        },
        body: JSON.stringify({
          refresh: refreshToken,
        }),
      });
    } catch (error) {
      console.error('Erro ao fazer logout:', error);
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
export async function getCurrentUser(): Promise<User> {
  const accessToken = localStorage.getItem('access_token');

  if (!accessToken) {
    throw new Error('Usuário não autenticado');
  }

  const response = await fetch(`${API_URL}/api/auth/me/`, {
    method: 'GET',
    headers: {
      'Authorization': `Bearer ${accessToken}`,
    },
  });

  if (!response.ok) {
    if (response.status === 401) {
      // Token expirado, tentar refresh
      await refreshAccessToken();
      // Tentar novamente
      return getCurrentUser();
    }
    throw new Error('Erro ao obter dados do usuário');
  }

  return response.json();
}

/**
 * Renova o access token usando o refresh token
 */
export async function refreshAccessToken(): Promise<string> {
  const refreshToken = localStorage.getItem('refresh_token');

  if (!refreshToken) {
    throw new Error('Refresh token não encontrado');
  }

  const response = await fetch(`${API_URL}/api/auth/token/refresh/`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      refresh: refreshToken,
    }),
  });

  if (!response.ok) {
    // Refresh token inválido, fazer logout
    await logout();
    throw new Error('Sessão expirada. Faça login novamente.');
  }

  const data = await response.json();
  localStorage.setItem('access_token', data.access);

  return data.access;
}

/**
 * Verifica se o usuário está autenticado
 */
export function isAuthenticated(): boolean {
  return !!localStorage.getItem('access_token');
}

/**
 * Obtém o usuário armazenado no localStorage
 */
export function getStoredUser(): User | null {
  const userStr = localStorage.getItem('user');
  return userStr ? JSON.parse(userStr) : null;
}
```

---

#### B) Componente de Login (`components/LoginForm.tsx`)

```tsx
// components/LoginForm.tsx
'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { login } from '@/lib/auth';

export default function LoginForm() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const response = await login({ username, password });
      console.log('Login bem-sucedido:', response);
      
      // Redirecionar para o dashboard
      router.push('/dashboard');
    } catch (err: any) {
      setError(err.message || 'Erro ao fazer login');
      console.error('Erro no login:', err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="max-w-md w-full space-y-8 p-8 bg-white rounded-lg shadow-md">
        <div>
          <h2 className="text-center text-3xl font-extrabold text-gray-900">
            GESTK
          </h2>
          <p className="mt-2 text-center text-sm text-gray-600">
            Faça login para continuar
          </p>
        </div>

        <form className="mt-8 space-y-6" onSubmit={handleSubmit}>
          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
              {error}
            </div>
          )}

          <div className="space-y-4">
            <div>
              <label htmlFor="username" className="block text-sm font-medium text-gray-700">
                Usuário
              </label>
              <input
                id="username"
                name="username"
                type="text"
                required
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                placeholder="Digite seu usuário"
              />
            </div>

            <div>
              <label htmlFor="password" className="block text-sm font-medium text-gray-700">
                Senha
              </label>
              <input
                id="password"
                name="password"
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                placeholder="Digite sua senha"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? 'Entrando...' : 'Entrar'}
          </button>
        </form>
      </div>
    </div>
  );
}
```

---

#### C) Página de Login (`app/login/page.tsx`)

```tsx
// app/login/page.tsx
import LoginForm from '@/components/LoginForm';

export default function LoginPage() {
  return <LoginForm />;
}
```

---

#### D) Middleware de Autenticação (`middleware.ts`)

```typescript
// middleware.ts
import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

export function middleware(request: NextRequest) {
  const token = request.cookies.get('access_token')?.value;

  // Rotas públicas
  const publicPaths = ['/login', '/'];
  const isPublicPath = publicPaths.includes(request.nextUrl.pathname);

  // Se não está autenticado e tenta acessar rota protegida
  if (!token && !isPublicPath) {
    return NextResponse.redirect(new URL('/login', request.url));
  }

  // Se está autenticado e tenta acessar login
  if (token && request.nextUrl.pathname === '/login') {
    return NextResponse.redirect(new URL('/dashboard', request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: ['/((?!api|_next/static|_next/image|favicon.ico).*)'],
};
```

---

#### E) Hook de Autenticação (`hooks/useAuth.ts`)

```typescript
// hooks/useAuth.ts
'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { getCurrentUser, logout, isAuthenticated, getStoredUser } from '@/lib/auth';
import type { User } from '@/lib/auth';

export function useAuth() {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  useEffect(() => {
    checkAuth();
  }, []);

  const checkAuth = async () => {
    try {
      if (isAuthenticated()) {
        // Primeiro, pegar do storage (mais rápido)
        const storedUser = getStoredUser();
        if (storedUser) {
          setUser(storedUser);
        }

        // Depois, validar com o backend
        const userData = await getCurrentUser();
        setUser(userData);
      }
    } catch (error) {
      console.error('Erro ao verificar autenticação:', error);
      setUser(null);
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = async () => {
    await logout();
    setUser(null);
    router.push('/login');
  };

  return {
    user,
    loading,
    isAuthenticated: !!user,
    logout: handleLogout,
    refetch: checkAuth,
  };
}
```

---

#### F) Componente Protegido (`components/ProtectedRoute.tsx`)

```tsx
// components/ProtectedRoute.tsx
'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/hooks/useAuth';

export default function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !isAuthenticated) {
      router.push('/login');
    }
  }, [isAuthenticated, loading, router]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return null;
  }

  return <>{children}</>;
}
```

---

### 3. Exemplo de Uso

#### Dashboard Protegido (`app/dashboard/page.tsx`)

```tsx
// app/dashboard/page.tsx
'use client';

import ProtectedRoute from '@/components/ProtectedRoute';
import { useAuth } from '@/hooks/useAuth';

export default function DashboardPage() {
  const { user, logout } = useAuth();

  return (
    <ProtectedRoute>
      <div className="min-h-screen bg-gray-100">
        <nav className="bg-white shadow">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex justify-between h-16">
              <div className="flex items-center">
                <h1 className="text-xl font-bold">GESTK Dashboard</h1>
              </div>
              <div className="flex items-center space-x-4">
                <span className="text-gray-700">
                  Olá, {user?.first_name || user?.username}!
                </span>
                <button
                  onClick={logout}
                  className="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700"
                >
                  Sair
                </button>
              </div>
            </div>
          </div>
        </nav>

        <main className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
          <div className="px-4 py-6 sm:px-0">
            <div className="bg-white shadow rounded-lg p-6">
              <h2 className="text-2xl font-bold mb-4">
                Bem-vindo ao GESTK!
              </h2>
              <div className="space-y-2">
                <p><strong>Usuário:</strong> {user?.username}</p>
                <p><strong>Email:</strong> {user?.email}</p>
                <p><strong>Tipo:</strong> {user?.tipo_usuario}</p>
                <p><strong>Contabilidade:</strong> {user?.contabilidade_razao_social}</p>
              </div>
            </div>
          </div>
        </main>
      </div>
    </ProtectedRoute>
  );
}
```

---

## ✅ Teste Completo

1. **Backend Django rodando:**
   ```bash
   cd c:\GitHub\gestk-back
   python manage.py runserver
   ```

2. **Frontend Next.js rodando:**
   ```bash
   cd c:\GitHub\gestk-front  # (ou nome do seu projeto frontend)
   npm run dev
   ```

3. **Acessar:**
   - Frontend: `http://localhost:3000`
   - Fazer login com as credenciais criadas
   - Verificar que não há mais erro 403! ✅

---

## 🎉 Resultado Esperado

- ✅ Login sem erro 403
- ✅ Tokens armazenados no localStorage
- ✅ Redirecionamento para dashboard
- ✅ Requisições autenticadas funcionando
- ✅ Logout funcionando
- ✅ Refresh token automático

---

**Está tudo pronto! Pode testar no frontend!** 🚀
