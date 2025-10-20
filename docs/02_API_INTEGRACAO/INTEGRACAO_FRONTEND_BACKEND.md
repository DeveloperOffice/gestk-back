# 🔗 Integração Frontend-Backend - GESTK

**Última Atualização**: 20/10/2025 18:00  
**Status**: ✅ **69 ENDPOINTS IMPLEMENTADOS E FUNCIONANDO**

---

## 📋 Visão Geral

Este documento detalha a integração completa entre o frontend (Next.js) e o backend (Django REST API) do GESTK, incluindo **TODOS os 69 endpoints de CRUDs de Administração e Billing**.

## 🎯 Endpoints Disponíveis

| Módulo | ViewSets | Endpoints | Status |
|--------|----------|-----------|--------|
| **Billing** | 5 | 43 | ✅ 100% |
| **Administração** | 3 | 26 | ✅ 100% |
| **Gestão** | 10+ | 50+ | ✅ 100% |
| **Dashboards** | 5 | 15+ | ✅ 100% |
| **TOTAL** | **23+** | **130+** | ✅ **PRONTO** |

---

## 🏗️ Arquitetura de Integração

### Stack Tecnológica
- **Frontend**: Next.js 15, TypeScript, Tailwind CSS, shadcn/ui, React Query
- **Backend**: Django 5.2.5, Django REST Framework, PostgreSQL
- **Autenticação**: JWT (Simple JWT) - 8h access, 7d refresh
- **Comunicação**: Axios com interceptors automáticos
- **Multi-tenancy**: Isolamento automático por contabilidade (REGRA DE OURO)
- **Base URL**: `http://localhost:8000/api/`

### Fluxo de Dados
```
Frontend (Next.js) → API Client (Axios) → Backend (Django) → Database (PostgreSQL)
                  ← Response ← Serializer ← QuerySet ← Models
                  
Middleware: CSRF Exempt para APIs JWT
Permissões: IsAuthenticated + IsAdminOrContabilidadeOwner
Multitenancy: X-Contabilidade-ID header
```

## 🔐 Sistema de Autenticação

### Base URL
```
http://localhost:8000/api/
```

### Configuração do Cliente API
```typescript
// packages/shared/src/api/client.ts
import axios, { AxiosInstance } from 'axios';

export class ApiClient {
  private client: AxiosInstance;
  private accessToken: string | null = null;
  private refreshToken: string | null = null;
  private contabilidadeId: string | null = null;
  private appContext: 'admin' | 'client' | null = null;

  constructor() {
    this.client = axios.create({
      baseURL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api',
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    this.setupInterceptors();
  }

  // Headers automáticos
  private setupInterceptors() {
    // Request interceptor
    this.client.interceptors.request.use((config) => {
      if (this.accessToken) {
        config.headers.Authorization = `Bearer ${this.accessToken}`;
      }
      if (this.contabilidadeId) {
        config.headers['X-Contabilidade-ID'] = this.contabilidadeId;
      }
      if (this.appContext) {
        config.headers['X-App-Context'] = this.appContext;
      }
      return config;
    });

    // Response interceptor (refresh token automático)
    this.client.interceptors.response.use(
      (response) => response,
      async (error) => {
        const originalRequest = error.config;

        // Se 401 e não é retry, tenta refresh
        if (error.response?.status === 401 && !originalRequest._retry) {
          originalRequest._retry = true;

          try {
            const { data } = await axios.post(
              `${this.client.defaults.baseURL}/auth/token/refresh/`,
              { refresh: this.refreshToken }
            );

            this.setTokens(data.access, this.refreshToken!);
            originalRequest.headers.Authorization = `Bearer ${data.access}`;

            return this.client(originalRequest);
          } catch (refreshError) {
            // Refresh falhou, desloga usuário
            this.clearTokens();
            window.location.href = '/login';
            return Promise.reject(refreshError);
          }
        }

        return Promise.reject(error);
      }
    );
  }

  setTokens(access: string, refresh: string) {
    this.accessToken = access;
    this.refreshToken = refresh;
    localStorage.setItem('access_token', access);
    localStorage.setItem('refresh_token', refresh);
  }

  setContabilidade(id: string) {
    this.contabilidadeId = id;
    localStorage.setItem('contabilidade_id', id);
  }

  clearTokens() {
    this.accessToken = null;
    this.refreshToken = null;
    this.contabilidadeId = null;
    localStorage.clear();
  }
}

export const apiClient = new ApiClient();
```

### Endpoints de Autenticação

#### 1. Login
```typescript
POST /api/auth/login/
Content-Type: application/json



Response 200:
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "user": {
    "id": "uuid",
    "username": "wando",
    "email": "juridico@office-ce.com.br",
    "first_name": "Wando",
    "last_name": "Oliveira",
    "tipo_usuario": "superuser",
    "is_superuser": true,
    "contabilidades": [
      {
        "id": "uuid",
        "razao_social": "GESTK CONTABILIDADE",
        "cnpj": "12.345.678/0001-90"
      }
    ]
  }
}

Response 401:
{
  "detail": "No active account found with the given credentials"
}
```

#### 2. Refresh Token
```typescript
POST /api/auth/token/refresh/
Content-Type: application/json

Request:
{
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}

Response 200:
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "access_token_expiration": "2025-10-21T02:00:00Z"
}
```

#### 3. Obter Dados do Usuário Logado
```typescript
GET /api/auth/me/
Authorization: Bearer {access_token}

Response 200:
{
  "id": "uuid",
  "username": "wando",
  "email": "juridico@office-ce.com.br",
  "tipo_usuario": "superuser",
  "contabilidades": [...],
  "permissions": [...]
}
```

#### 4. Logout
```typescript
POST /api/auth/logout/
Authorization: Bearer {access_token}

Response 200:
{
  "message": "Logout realizado com sucesso"
}
```

#### 5. CSRF Token (Opcional)
```typescript
GET /api/auth/csrf/

Response 200:
{
  "csrfToken": "token-value"
}
```

---

---

## 💰 MÓDULO BILLING (43 endpoints)

### 1️⃣ Planos - 8 endpoints

**Base URL**: `/api/billing/planos/`

#### Tipos TypeScript
```typescript
interface Plano {
  id: string;
  codigo: string;              // Ex: "BASIC", "PRO", "ENTERPRISE"
  nome: string;                // Ex: "Plano Básico"
  descricao: string;
  preco_mensal: string;        // Decimal como string
  preco_anual: string;         // Decimal como string
  desconto_anual: number;      // Percentual
  preco_anual_calculado: string; // Read-only
  modulos_inclusos: string[];  // ["fiscal", "contabil", "folha"]
  limites: {
    usuarios?: number;
    empresas?: number;
    contratos?: number;
  };
  ativo: boolean;
  ordem_exibicao: number;
  created_at: string;
  updated_at: string;
}

interface PlanoListResponse {
  count: number;
  next: string | null;
  previous: string | null;
  results: Plano[];
}
```

#### Endpoints

**1.1 Listar Planos**
```typescript
GET /api/billing/planos/
Authorization: Bearer {token}

Query Params:
- page: number
- page_size: number (default: 20)
- codigo: string (filtro)
- nome: string (filtro)
- ativo: boolean
- preco_min: number
- preco_max: number
- tem_desconto_anual: boolean
- search: string (busca em código/nome/descrição)
- ordering: string (nome, preco_mensal, -nome, etc)

Response 200: PlanoListResponse
```

**1.2 Detalhar Plano**
```typescript
GET /api/billing/planos/{id}/
Authorization: Bearer {token}

Response 200: Plano
Response 404: { "detail": "Not found." }
```

**1.3 Criar Plano**
```typescript
POST /api/billing/planos/
Authorization: Bearer {token}
Content-Type: application/json

Request:
{
  "codigo": "ENTERPRISE",
  "nome": "Plano Enterprise",
  "descricao": "Plano completo para grandes empresas",
  "preco_mensal": "499.00",
  "preco_anual": "4990.00",
  "desconto_anual": 16.67,
  "modulos_inclusos": ["fiscal", "contabil", "folha", "gestao"],
  "limites": {
    "usuarios": 50,
    "empresas": 100,
    "contratos": 500
  },
  "ativo": true,
  "ordem_exibicao": 3
}

Response 201: Plano
Response 400: { "codigo": ["Já existe um plano com este código."] }
```

**1.4 Atualizar Plano (Completo)**
```typescript
PUT /api/billing/planos/{id}/
Authorization: Bearer {token}

Request: (todos os campos obrigatórios)
Response 200: Plano
```

**1.5 Atualizar Plano (Parcial)**
```typescript
PATCH /api/billing/planos/{id}/
Authorization: Bearer {token}

Request: (campos opcionais)
{
  "preco_mensal": "599.00",
  "ativo": false
}

Response 200: Plano
```

**1.6 Deletar Plano**
```typescript
DELETE /api/billing/planos/{id}/
Authorization: Bearer {token}

Response 204: No Content
Response 404: Not found
```

**1.7 Listar Planos Ativos**
```typescript
GET /api/billing/planos/ativos/
Authorization: Bearer {token}

Response 200: Plano[]
```

**1.8 Resumo de Planos**
```typescript
GET /api/billing/planos/resumo/
Authorization: Bearer {token}

Response 200:
{
  "total": 5,
  "ativos": 4,
  "inativos": 1,
  "preco_medio_mensal": "299.00",
  "preco_medio_anual": "2990.00"
}
```

---

### 2️⃣ Assinaturas - 11 endpoints

**Base URL**: `/api/billing/assinaturas/`

#### Tipos TypeScript
```typescript
interface Assinatura {
  id: string;
  contabilidade: string;       // UUID
  contabilidade_razao_social: string; // Read-only
  contabilidade_cnpj: string;  // Read-only
  plano: string;               // UUID
  plano_nome: string;          // Read-only
  plano_codigo: string;        // Read-only
  data_inicio: string;         // YYYY-MM-DD
  data_fim: string | null;     // YYYY-MM-DD
  data_renovacao: string | null;
  status: 'ativa' | 'suspensa' | 'cancelada' | 'expirada' | 'trial';
  ciclo_cobranca: 'mensal' | 'anual' | 'trimestral' | 'semestral';
  trial_ate: string | null;    // YYYY-MM-DD
  valor_mensal: string;
  valor_anual: string | null;
  dia_vencimento: number;      // 1-28
  desconto_percentual: number;
  motivo_suspensao: string | null;
  data_suspensao: string | null;
  motivo_cancelamento: string | null;
  data_cancelamento: string | null;
  metadados: Record<string, any>;
  created_at: string;
  updated_at: string;
  created_by: string | null;
  esta_ativa: boolean;         // Read-only
  esta_em_trial: boolean;      // Read-only
  dias_para_vencimento: number | null; // Read-only
}
```

#### Endpoints

**2.1 Listar Assinaturas**
```typescript
GET /api/billing/assinaturas/
Authorization: Bearer {token}

Query Params:
- contabilidade: uuid
- plano: uuid
- plano_codigo: string
- status: 'ativa' | 'suspensa' | 'cancelada' | 'expirada' | 'trial'
- ciclo_cobranca: 'mensal' | 'anual' | 'trimestral' | 'semestral'
- data_inicio_apos: YYYY-MM-DD
- data_inicio_antes: YYYY-MM-DD
- data_fim_apos: YYYY-MM-DD
- data_fim_antes: YYYY-MM-DD
- valor_min: number
- valor_max: number
- ativa: boolean (filtra apenas ativas vigentes)
- em_trial: boolean
- vencida: boolean
- vence_em_dias: number (ex: 30 = vence nos próximos 30 dias)
- search: string
- ordering: string

Response 200: AssinaturaListResponse
```

**2.2 Detalhar Assinatura**
```typescript
GET /api/billing/assinaturas/{id}/
Authorization: Bearer {token}

Response 200: Assinatura
```

**2.3 Criar Assinatura**
```typescript
POST /api/billing/assinaturas/
Authorization: Bearer {token}

Request:
{
  "contabilidade": "uuid",
  "plano": "uuid",
  "data_inicio": "2025-10-20",
  "data_fim": "2026-10-20",
  "ciclo_cobranca": "mensal",
  "valor_mensal": "99.00",
  "dia_vencimento": 10,
  "trial_ate": "2025-11-20"
}

Response 201: Assinatura
Response 400: Validation errors
```

**2.4 Atualizar Assinatura**
```typescript
PUT /api/billing/assinaturas/{id}/
PATCH /api/billing/assinaturas/{id}/
Authorization: Bearer {token}

Response 200: Assinatura
```

**2.5 Deletar Assinatura**
```typescript
DELETE /api/billing/assinaturas/{id}/
Authorization: Bearer {token}

Response 204: No Content
```

**2.6 Suspender Assinatura**
```typescript
POST /api/billing/assinaturas/{id}/suspender/
Authorization: Bearer {token}

Request:
{
  "motivo": "Inadimplência - Fatura vencida há 30 dias"
}

Response 200:
{
  "message": "Assinatura suspensa com sucesso",
  "status": "suspensa",
  "motivo": "Inadimplência - Fatura vencida há 30 dias",
  "data_suspensao": "2025-10-20"
}
```

**2.7 Cancelar Assinatura**
```typescript
POST /api/billing/assinaturas/{id}/cancelar/
Authorization: Bearer {token}

Request:
{
  "motivo": "Cliente solicitou cancelamento"
}

Response 200:
{
  "message": "Assinatura cancelada com sucesso",
  "status": "cancelada",
  "motivo": "Cliente solicitou cancelamento",
  "data_cancelamento": "2025-10-20"
}
```

**2.8 Ativar Assinatura**
```typescript
POST /api/billing/assinaturas/{id}/ativar/
Authorization: Bearer {token}

Response 200:
{
  "message": "Assinatura ativada com sucesso",
  "status": "ativa"
}
```

**2.9 Criar Assinatura (Alternativo)**
```typescript
POST /api/billing/assinaturas/criar-assinatura/
Authorization: Bearer {token}

Request: (mesmo formato do POST padrão)
Response 201: Assinatura
```

**2.10 Resumo de Assinaturas**
```typescript
GET /api/billing/assinaturas/resumo/
Authorization: Bearer {token}

Response 200:
{
  "total": 150,
  "por_status": {
    "ativa": 120,
    "suspensa": 15,
    "cancelada": 10,
    "expirada": 3,
    "trial": 2
  },
  "por_plano": {
    "Plano Básico": 80,
    "Plano Pro": 50,
    "Plano Enterprise": 20
  },
  "ativas": 120,
  "suspensas": 15,
  "canceladas": 10,
  "em_trial": 2,
  "receita_mensal": "14850.00",
  "receita_anual": "148500.00"
}
```

---

### 3️⃣ Faturas - 10 endpoints

**Base URL**: `/api/billing/faturas/`

#### Tipos TypeScript
```typescript
interface Fatura {
  id: string;
  assinatura: string;          // UUID
  assinatura_contabilidade: string; // Read-only
  assinatura_plano: string;    // Read-only
  numero_fatura: string;       // Ex: "FAT-2025-10-00123"
  competencia: string;         // YYYY-MM
  valor_original: string;
  desconto: string;
  valor_final: string;
  data_emissao: string;        // YYYY-MM-DD
  data_vencimento: string;     // YYYY-MM-DD
  data_pagamento: string | null;
  status: 'aberta' | 'paga' | 'vencida' | 'cancelada' | 'estornada';
  link_boleto: string | null;
  linha_digitavel: string | null;
  codigo_barras: string | null;
  metadados: Record<string, any>;
  created_at: string;
  updated_at: string;
  esta_vencida: boolean;       // Read-only
  dias_para_vencimento: number; // Read-only
}
```

#### Endpoints

**3.1 Listar Faturas**
```typescript
GET /api/billing/faturas/
Authorization: Bearer {token}

Query Params:
- assinatura: uuid
- contabilidade: uuid
- plano: uuid
- numero_fatura: string
- competencia: string (YYYY-MM)
- status: 'aberta' | 'paga' | 'vencida' | 'cancelada'
- data_emissao_apos: YYYY-MM-DD
- data_emissao_antes: YYYY-MM-DD
- data_vencimento_apos: YYYY-MM-DD
- data_vencimento_antes: YYYY-MM-DD
- data_pagamento_apos: YYYY-MM-DD
- data_pagamento_antes: YYYY-MM-DD
- valor_min: number
- valor_max: number
- vencida: boolean
- vence_em_dias: number
- search: string

Response 200: FaturaListResponse
```

**3.2-3.6 CRUD Básico**
```typescript
GET    /api/billing/faturas/{id}/
POST   /api/billing/faturas/
PUT    /api/billing/faturas/{id}/
PATCH  /api/billing/faturas/{id}/
DELETE /api/billing/faturas/{id}/
```

**3.7 Marcar Fatura como Paga**
```typescript
POST /api/billing/faturas/{id}/marcar-como-paga/
Authorization: Bearer {token}

Request:
{
  "data_pagamento": "2025-10-20"  // Opcional, default = hoje
}

Response 200:
{
  "message": "Fatura marcada como paga",
  "status": "paga",
  "data_pagamento": "2025-10-20"
}
```

**3.8 Cancelar Fatura**
```typescript
POST /api/billing/faturas/{id}/cancelar/
Authorization: Bearer {token}

Response 200:
{
  "message": "Fatura cancelada com sucesso",
  "status": "cancelada"
}
```

**3.9 Gerar Faturas em Lote**
```typescript
POST /api/billing/faturas/gerar-faturas/
Authorization: Bearer {token}

Request:
{
  "competencia": "2025-11"  // YYYY-MM
}

Response 200:
{
  "message": "Faturas geradas para competência 2025-11",
  "competencia": "2025-11",
  "faturas_geradas": 150
}
```

**3.10 Resumo de Faturas**
```typescript
GET /api/billing/faturas/resumo/
Authorization: Bearer {token}

Response 200:
{
  "total": 500,
  "por_status": {
    "aberta": 120,
    "paga": 350,
    "vencida": 25,
    "cancelada": 5
  },
  "abertas": 120,
  "pagas": 350,
  "vencidas": 25,
  "canceladas": 5,
  "valor_total_aberto": "12000.00",
  "valor_total_pago": "35000.00",
  "receita_por_mes": {
    "2025-08": "11500.00",
    "2025-09": "11800.00",
    "2025-10": "11700.00"
  }
}
```

---

### 4️⃣ Pagamentos - 9 endpoints

**Base URL**: `/api/billing/pagamentos/`

#### Tipos TypeScript
```typescript
interface Pagamento {
  id: string;
  fatura: string;              // UUID
  fatura_numero: string;       // Read-only
  fatura_contabilidade: string; // Read-only
  fatura_valor: string;        // Read-only
  valor: string;
  metodo: 'boleto' | 'pix' | 'cartao_credito' | 'cartao_debito' | 'transferencia' | 'dinheiro';
  transacao_id: string | null;
  referencia: string | null;
  status: 'pendente' | 'processando' | 'confirmado' | 'estornado' | 'falhou';
  data_pagamento: string | null;
  data_confirmacao: string | null;
  metadados: Record<string, any>;
  created_at: string;
  updated_at: string;
}
```

#### Endpoints

**4.1 Listar Pagamentos**
```typescript
GET /api/billing/pagamentos/
Authorization: Bearer {token}

Query Params:
- fatura: uuid
- assinatura: uuid
- contabilidade: uuid
- transacao_id: string
- referencia: string
- metodo: 'boleto' | 'pix' | 'cartao_credito' | etc
- status: 'pendente' | 'confirmado' | etc
- data_pagamento_apos: YYYY-MM-DD HH:MM:SS
- data_pagamento_antes: YYYY-MM-DD HH:MM:SS
- data_confirmacao_apos: YYYY-MM-DD HH:MM:SS
- data_confirmacao_antes: YYYY-MM-DD HH:MM:SS
- valor_min: number
- valor_max: number
- confirmado: boolean
- pendente: boolean
- falhou: boolean

Response 200: PagamentoListResponse
```

**4.2-4.6 CRUD Básico**
```typescript
GET    /api/billing/pagamentos/{id}/
POST   /api/billing/pagamentos/
PUT    /api/billing/pagamentos/{id}/
PATCH  /api/billing/pagamentos/{id}/
DELETE /api/billing/pagamentos/{id}/
```

**4.7 Confirmar Pagamento**
```typescript
POST /api/billing/pagamentos/{id}/confirmar/
Authorization: Bearer {token}

Request:
{
  "data_confirmacao": "2025-10-20 14:30:00"  // Opcional
}

Response 200:
{
  "message": "Pagamento confirmado com sucesso",
  "status": "confirmado",
  "data_confirmacao": "2025-10-20T14:30:00Z"
}

// IMPORTANTE: Também atualiza a fatura para "paga"
```

**4.8 Estornar Pagamento**
```typescript
POST /api/billing/pagamentos/{id}/estornar/
Authorization: Bearer {token}

Response 200:
{
  "message": "Pagamento estornado com sucesso",
  "status": "estornado"
}

// IMPORTANTE: Também reverte a fatura para "aberta"
```

**4.9 Resumo de Pagamentos**
```typescript
GET /api/billing/pagamentos/resumo/
Authorization: Bearer {token}

Response 200:
{
  "total": 400,
  "por_status": {
    "pendente": 50,
    "confirmado": 330,
    "estornado": 15,
    "falhou": 5
  },
  "por_metodo": {
    "pix": 200,
    "boleto": 150,
    "cartao_credito": 40,
    "cartao_debito": 10
  },
  "pendentes": 50,
  "confirmados": 330,
  "estornados": 15,
  "valor_total_confirmado": "39600.00",
  "valor_total_pendente": "4800.00"
}
```

---

### 5️⃣ Contabilidades Billing - 5 endpoints

**Base URL**: `/api/billing/contabilidades/`

#### Endpoints

**5.1 Listar Contabilidades**
```typescript
GET /api/billing/contabilidades/
Authorization: Bearer {token}

Response 200:
{
  "count": 50,
  "results": [
    {
      "id": "uuid",
      "razao_social": "GESTK CONTABILIDADE LTDA",
      "nome_fantasia": "GESTK",
      "cnpj": "12.345.678/0001-90",
      "ativo": true,
      "responsavel_financeiro_nome": "João Silva",
      "responsavel_financeiro_email": "financeiro@gestk.com",
      "suspensa_por_inadimplencia": false,
      "saldo_creditos": "0.00",
      "assinatura_atual": {
        "id": "uuid",
        "plano_nome": "Plano Enterprise",
        "status": "ativa",
        "valor_mensal": "499.00"
      },
      "total_faturas": 12,
      "faturas_pendentes": 1,
      "receita_total": "5988.00"
    }
  ]
}
```

**5.2 Detalhar Contabilidade**
```typescript
GET /api/billing/contabilidades/{id}/
Authorization: Bearer {token}

Response 200: (mesmo formato acima)
```

**5.3 Suspender por Inadimplência**
```typescript
POST /api/billing/contabilidades/{id}/suspender-por-inadimplencia/
Authorization: Bearer {token}

Response 200:
{
  "message": "Contabilidade suspensa por inadimplência",
  "suspensa_por_inadimplencia": true
}
```

**5.4 Reativar Contabilidade**
```typescript
POST /api/billing/contabilidades/{id}/reativar/
Authorization: Bearer {token}

Response 200:
{
  "message": "Contabilidade reativada",
  "suspensa_por_inadimplencia": false
}
```

**5.5 Resumo de Contabilidades**
```typescript
GET /api/billing/contabilidades/resumo/
Authorization: Bearer {token}

Response 200:
{
  "total": 50,
  "com_assinatura": 45,
  "sem_assinatura": 5,
  "suspensas": 3,
  "receita_total": "267450.00",
  "faturas_pendentes": "15300.00"
}
```

---

## 🏢 MÓDULO ADMINISTRAÇÃO (26 endpoints)

### 6️⃣ Contratos GESTK - 10 endpoints

**Base URL**: `/api/administracao/contratos-gestk/`

#### Tipos TypeScript
```typescript
interface ContratoGestk {
  id: string;
  contabilidade: string;       // UUID
  contabilidade_razao_social: string; // Read-only
  contabilidade_cnpj: string;  // Read-only
  numero_contrato: string;     // Ex: "CTRT-2025-00123"
  plano_servico: string;       // Ex: "BASIC", "PRO", "ENTERPRISE"
  modulos_inclusos: string[];  // ["fiscal", "contabil", "folha"]
  limites_usuarios: number;
  limites_empresas: number;
  limites_contratos_internos: number;
  valor_mensal: string;
  valor_anual: string | null;
  desconto_percentual: number;
  dia_vencimento: number;      // 1-28
  data_inicio: string;         // YYYY-MM-DD
  data_termino: string | null; // YYYY-MM-DD
  trial_ate: string | null;    // YYYY-MM-DD
  status: 'trial' | 'ativo' | 'suspenso' | 'cancelado' | 'vencido';
  motivo_suspensao: string | null;
  data_suspensao: string | null;
  motivo_cancelamento: string | null;
  data_cancelamento: string | null;
  observacoes: string;
  metadados: Record<string, any>;
  created_at: string;
  updated_at: string;
  created_by: string | null;
}
```

#### Endpoints

**6.1 Listar Contratos**
```typescript
GET /api/administracao/contratos-gestk/
Authorization: Bearer {token}

Query Params:
- contabilidade: uuid
- numero_contrato: string
- plano_servico: string
- status: 'trial' | 'ativo' | 'suspenso' | 'cancelado' | 'vencido'
- data_inicio_apos: YYYY-MM-DD
- data_inicio_antes: YYYY-MM-DD
- search: string (busca em número, razão social)
- ordering: string

Response 200:
{
  "count": 50,
  "results": [ContratoGestk]
}
```

**6.2-6.6 CRUD Básico**
```typescript
GET    /api/administracao/contratos-gestk/{id}/
POST   /api/administracao/contratos-gestk/
PUT    /api/administracao/contratos-gestk/{id}/
PATCH  /api/administracao/contratos-gestk/{id}/
DELETE /api/administracao/contratos-gestk/{id}/
```

**6.7 Suspender Contrato**
```typescript
POST /api/administracao/contratos-gestk/{id}/suspender/
Authorization: Bearer {token}

Request:
{
  "motivo": "Inadimplência - Fatura vencida há 60 dias"
}

Response 200:
{
  "message": "Contrato suspenso com sucesso",
  "status": "suspenso",
  "motivo": "Inadimplência - Fatura vencida há 60 dias",
  "data_suspensao": "2025-10-20"
}
```

**6.8 Cancelar Contrato**
```typescript
POST /api/administracao/contratos-gestk/{id}/cancelar/
Authorization: Bearer {token}

Request:
{
  "motivo": "Cliente solicitou rescisão"
}

Response 200:
{
  "message": "Contrato cancelado com sucesso",
  "status": "cancelado",
  "motivo": "Cliente solicitou rescisão",
  "data_cancelamento": "2025-10-20"
}
```

**6.9 Ativar Contrato**
```typescript
POST /api/administracao/contratos-gestk/{id}/ativar/
Authorization: Bearer {token}

Response 200:
{
  "message": "Contrato ativado com sucesso",
  "status": "ativo"
}
```

**6.10 Resumo de Contratos**
```typescript
GET /api/administracao/contratos-gestk/resumo/
Authorization: Bearer {token}

Response 200:
{
  "total": 50,
  "por_status": {
    "ativo": 40,
    "suspenso": 5,
    "cancelado": 3,
    "vencido": 1,
    "trial": 1
  },
  "por_plano": {
    "BASIC": 20,
    "PRO": 25,
    "ENTERPRISE": 5
  },
  "ativos": 40,
  "suspensos": 5,
  "cancelados": 3,
  "em_trial": 1,
  "receita_mensal": "24950.00",
  "receita_anual": "249500.00"
}
```

---

### 7️⃣ Usuários de Acesso - 10 endpoints

**Base URL**: `/api/administracao/usuarios-acesso/`

#### Tipos TypeScript
```typescript
interface UsuarioAcesso {
  id: string;
  usuario: string;             // UUID
  usuario_username: string;    // Read-only
  usuario_email: string;       // Read-only
  contabilidade: string;       // UUID
  contabilidade_razao_social: string; // Read-only
  contrato: string | null;     // UUID (se acesso restrito a contrato)
  empresa_cnpj: string | null; // Se acesso restrito a empresa
  role: 'superuser' | 'admin' | 'operacional' | 'etl' | 'readonly';
  modulos_acesso: string[];    // ["fiscal", "contabil", "folha"]
  permissoes: string[];        // ["create", "read", "update", "delete"]
  data_inicio: string;         // YYYY-MM-DD
  data_fim: string | null;     // YYYY-MM-DD
  ativo: boolean;
  observacoes: string;
  created_at: string;
  updated_at: string;
  created_by: string | null;
}
```

#### Endpoints

**7.1 Listar Acessos**
```typescript
GET /api/administracao/usuarios-acesso/
Authorization: Bearer {token}

Query Params:
- usuario: uuid
- contabilidade: uuid
- role: 'superuser' | 'admin' | 'operacional' | 'etl' | 'readonly'
- ativo: boolean
- data_inicio_apos: YYYY-MM-DD
- data_inicio_antes: YYYY-MM-DD
- data_fim_apos: YYYY-MM-DD
- data_fim_antes: YYYY-MM-DD
- search: string (busca em username, email, razão social)
- ordering: string

Response 200:
{
  "count": 200,
  "results": [UsuarioAcesso]
}
```

**7.2-7.6 CRUD Básico**
```typescript
GET    /api/administracao/usuarios-acesso/{id}/
POST   /api/administracao/usuarios-acesso/
PUT    /api/administracao/usuarios-acesso/{id}/
PATCH  /api/administracao/usuarios-acesso/{id}/
DELETE /api/administracao/usuarios-acesso/{id}/
```

**7.7 Ativar Acesso**
```typescript
POST /api/administracao/usuarios-acesso/{id}/ativar/
Authorization: Bearer {token}

Response 200:
{
  "message": "Acesso ativado com sucesso",
  "ativo": true
}
```

**7.8 Desativar Acesso**
```typescript
POST /api/administracao/usuarios-acesso/{id}/desativar/
Authorization: Bearer {token}

Response 200:
{
  "message": "Acesso desativado com sucesso",
  "ativo": false
}
```

**7.9 Estender Vigência**
```typescript
POST /api/administracao/usuarios-acesso/{id}/estender-vigencia/
Authorization: Bearer {token}

Request:
{
  "data_fim": "2026-12-31"  // YYYY-MM-DD
}

Response 200:
{
  "message": "Vigência estendida com sucesso",
  "data_fim": "2026-12-31"
}

Response 400:
{
  "error": "Data de fim é obrigatória"
}
```

**7.10 Resumo de Acessos**
```typescript
GET /api/administracao/usuarios-acesso/resumo/
Authorization: Bearer {token}

Response 200:
{
  "total": 200,
  "por_role": {
    "superuser": 5,
    "admin": 20,
    "operacional": 150,
    "etl": 10,
    "readonly": 15
  },
  "por_status": {
    "true": 180,    // ativos
    "false": 20     // inativos
  },
  "ativos": 180,
  "inativos": 20,
  "vencidos": 15,
  "em_trial": 5
}
```

---

### 8️⃣ Contabilidades Admin - 6 endpoints

**Base URL**: `/api/administracao/contabilidades-admin/`

#### Tipos TypeScript
```typescript
interface ContabilidadeAdmin {
  id: string;
  razao_social: string;
  nome_fantasia: string;
  cnpj: string;
  inscricao_estadual: string | null;
  inscricao_municipal: string | null;
  telefone: string | null;
  email: string | null;
  ativo: boolean;
  responsavel_financeiro_nome: string | null;
  responsavel_financeiro_email: string | null;
  responsavel_financeiro_telefone: string | null;
  suspensa_por_inadimplencia: boolean;
  saldo_creditos: string;
  observacoes: string;
  metadados: Record<string, any>;
  created_at: string;
  updated_at: string;
  // Dados agregados
  contrato_gestk: ContratoGestk | null;
  total_usuarios: number;
  total_empresas: number;
  total_contratos: number;
}
```

#### Endpoints

**8.1 Listar Contabilidades Admin**
```typescript
GET /api/administracao/contabilidades-admin/
Authorization: Bearer {token}

Query Params:
- razao_social: string
- cnpj: string
- ativo: boolean
- suspensa_por_inadimplencia: boolean
- search: string
- ordering: string

Response 200:
{
  "count": 50,
  "results": [ContabilidadeAdmin]
}
```

**8.2 Detalhar Contabilidade Admin**
```typescript
GET /api/administracao/contabilidades-admin/{id}/
Authorization: Bearer {token}

Response 200: ContabilidadeAdmin
```

**8.3 Suspender por Inadimplência**
```typescript
POST /api/administracao/contabilidades-admin/{id}/suspender-por-inadimplencia/
Authorization: Bearer {token}

Response 200:
{
  "message": "Contabilidade suspensa por inadimplência",
  "suspensa_por_inadimplencia": true
}

// IMPORTANTE: Também suspende todos os usuários dessa contabilidade
```

**8.4 Reativar Contabilidade**
```typescript
POST /api/administracao/contabilidades-admin/{id}/reativar/
Authorization: Bearer {token}

Response 200:
{
  "message": "Contabilidade reativada",
  "suspensa_por_inadimplencia": false
}
```

**8.5 Resumo de Contabilidades**
```typescript
GET /api/administracao/contabilidades-admin/resumo/
Authorization: Bearer {token}

Response 200:
{
  "total": 50,
  "com_contrato": 45,
  "sem_contrato": 5,
  "suspensas": 3,
  "total_usuarios": 500,
  "receita_total": "24950.00"
}
```

**8.6 Histórico da Contabilidade**
```typescript
GET /api/administracao/contabilidades-admin/{id}/historico/
Authorization: Bearer {token}

Response 200:
{
  "contabilidade": ContabilidadeAdmin,
  "historico_contratos": ContratoGestk[],
  "historico_assinaturas": Assinatura[],
  "historico_faturas": Fatura[],
  "historico_pagamentos": Pagamento[],
  "eventos": [
    {
      "data": "2025-10-20",
      "tipo": "suspensao",
      "descricao": "Contabilidade suspensa por inadimplência",
      "usuario": "admin"
    }
  ]
}
```

---

## 📊 QUADRO RESUMO COMPLETO - TODOS OS 69 ENDPOINTS

### Billing (43 endpoints)
| Recurso | List | Detail | Create | Update | Delete | Actions | Total |
|---------|------|--------|--------|--------|--------|---------|-------|
| Planos | ✅ | ✅ | ✅ | ✅ | ✅ | ativos, resumo | 8 |
| Assinaturas | ✅ | ✅ | ✅ | ✅ | ✅ | suspender, cancelar, ativar, criar-assinatura, resumo | 11 |
| Faturas | ✅ | ✅ | ✅ | ✅ | ✅ | marcar-paga, cancelar, gerar-faturas, resumo | 10 |
| Pagamentos | ✅ | ✅ | ✅ | ✅ | ✅ | confirmar, estornar, resumo | 9 |
| Contabilidades | ✅ | ✅ | - | - | - | suspender, reativar, resumo | 5 |
| **TOTAL BILLING** | | | | | | | **43** |

### Administração (26 endpoints)
| Recurso | List | Detail | Create | Update | Delete | Actions | Total |
|---------|------|--------|--------|--------|--------|---------|-------|
| Contratos GESTK | ✅ | ✅ | ✅ | ✅ | ✅ | suspender, cancelar, ativar, resumo | 10 |
| Usuários Acesso | ✅ | ✅ | ✅ | ✅ | ✅ | ativar, desativar, estender-vigencia, resumo | 10 |
| Contabilidades Admin | ✅ | ✅ | - | - | - | suspender, reativar, resumo, historico | 6 |
| **TOTAL ADMINISTRAÇÃO** | | | | | | | **26** |

### **TOTAL GERAL: 69 ENDPOINTS** ✅

---

## 🔧 HOOKS REACT QUERY RECOMENDADOS

### Exemplo Completo: Planos
```typescript
// hooks/usePlanos.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api';
import type { Plano, PlanoCreate, PlanoQueryParams, PlanoListResponse, PlanoResumo } from '@/types/billing';

export const usePlanos = (params?: PlanoQueryParams) => {
  return useQuery({
    queryKey: ['planos', params],
    queryFn: () => apiClient.get<PlanoListResponse>('/billing/planos/', { params }),
  });
};

export const usePlano = (id: string) => {
  return useQuery({
    queryKey: ['plano', id],
    queryFn: () => apiClient.get<Plano>(`/billing/planos/${id}/`),
    enabled: !!id,
  });
};

export const useCreatePlano = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (data: PlanoCreate) => 
      apiClient.post<Plano>('/billing/planos/', data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['planos'] });
    },
  });
};

export const useUpdatePlano = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<Plano> }) =>
      apiClient.patch<Plano>(`/billing/planos/${id}/`, data),
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: ['plano', id] });
      queryClient.invalidateQueries({ queryKey: ['planos'] });
    },
  });
};

export const useDeletePlano = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (id: string) => apiClient.delete(`/billing/planos/${id}/`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['planos'] });
    },
  });
};

export const usePlanosAtivos = () => {
  return useQuery({
    queryKey: ['planos', 'ativos'],
    queryFn: () => apiClient.get<Plano[]>('/billing/planos/ativos/'),
  });
};

export const usePlanosResumo = () => {
  return useQuery({
    queryKey: ['planos', 'resumo'],
    queryFn: () => apiClient.get<PlanoResumo>('/billing/planos/resumo/'),
  });
};
```

### Exemplo: Assinaturas com Actions
```typescript
// hooks/useAssinaturas.ts
export const useSuspenderAssinatura = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: ({ id, motivo }: { id: string; motivo: string }) =>
      apiClient.post(`/billing/assinaturas/${id}/suspender/`, { motivo }),
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: ['assinatura', id] });
      queryClient.invalidateQueries({ queryKey: ['assinaturas'] });
      queryClient.invalidateQueries({ queryKey: ['assinaturas', 'resumo'] });
    },
  });
};

export const useCancelarAssinatura = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: ({ id, motivo }: { id: string; motivo: string }) =>
      apiClient.post(`/billing/assinaturas/${id}/cancelar/`, { motivo }),
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: ['assinatura', id] });
      queryClient.invalidateQueries({ queryKey: ['assinaturas'] });
    },
  });
};

export const useAtivarAssinatura = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (id: string) =>
      apiClient.post(`/billing/assinaturas/${id}/ativar/`),
    onSuccess: (_, id) => {
      queryClient.invalidateQueries({ queryKey: ['assinatura', id] });
      queryClient.invalidateQueries({ queryKey: ['assinaturas'] });
    },
  });
};
```

### Exemplo: Contratos GESTK
```typescript
// hooks/useContratosGestk.ts
export const useSuspenderContrato = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: ({ id, motivo }: { id: string; motivo: string }) =>
      apiClient.post(`/administracao/contratos-gestk/${id}/suspender/`, { motivo }),
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: ['contrato-gestk', id] });
      queryClient.invalidateQueries({ queryKey: ['contratos-gestk'] });
    },
  });
};

export const useEstenderVigenciaAcesso = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: ({ id, data_fim }: { id: string; data_fim: string }) =>
      apiClient.post(`/administracao/usuarios-acesso/${id}/estender-vigencia/`, { data_fim }),
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: ['usuario-acesso', id] });
      queryClient.invalidateQueries({ queryKey: ['usuarios-acesso'] });
    },
  });
};
```

---

## 🎨 COMPONENTES DE UI RECOMENDADOS

### Exemplo: Lista de Planos com Actions
```typescript
// components/billing/PlanosList.tsx
'use client';

import { usePlanos, useDeletePlano } from '@/hooks/usePlanos';
import { DataTable } from '@/components/ui/data-table';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import Link from 'next/link';

export function PlanosList() {
  const { data, isLoading } = usePlanos();
  const deletePlano = useDeletePlano();

  const columns = [
    {
      accessorKey: 'codigo',
      header: 'Código',
    },
    {
      accessorKey: 'nome',
      header: 'Nome',
    },
    {
      accessorKey: 'preco_mensal',
      header: 'Preço Mensal',
      cell: ({ row }) => `R$ ${row.original.preco_mensal}`,
    },
    {
      accessorKey: 'ativo',
      header: 'Status',
      cell: ({ row }) => (
        <Badge variant={row.original.ativo ? 'success' : 'destructive'}>
          {row.original.ativo ? 'Ativo' : 'Inativo'}
        </Badge>
      ),
    },
    {
      id: 'actions',
      cell: ({ row }) => (
        <div className="flex gap-2">
          <Button size="sm" variant="outline" asChild>
            <Link href={`/admin/planos/${row.original.id}`}>
              Editar
            </Link>
          </Button>
          <Button
            size="sm"
            variant="destructive"
            onClick={() => deletePlano.mutate(row.original.id)}
          >
            Excluir
          </Button>
        </div>
      ),
    },
  ];

  if (isLoading) return <div>Carregando...</div>;

  return (
    <DataTable
      columns={columns}
      data={data?.results || []}
      pagination={{
        pageCount: Math.ceil((data?.count || 0) / 20),
      }}
    />
  );
}
```

### Exemplo: Assinatura com Actions
```typescript
// components/billing/AssinaturaActions.tsx
'use client';

import { useSuspenderAssinatura, useCancelarAssinatura, useAtivarAssinatura } from '@/hooks/useAssinaturas';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Textarea } from '@/components/ui/textarea';
import { useState } from 'react';

export function AssinaturaActions({ assinatura }: { assinatura: Assinatura }) {
  const [motivo, setMotivo] = useState('');
  const suspender = useSuspenderAssinatura();
  const cancelar = useCancelarAssinatura();
  const ativar = useAtivarAssinatura();

  if (assinatura.status === 'suspensa') {
    return (
      <Button
        onClick={() => ativar.mutate(assinatura.id)}
        disabled={ativar.isPending}
      >
        Ativar Assinatura
      </Button>
    );
  }

  return (
    <div className="flex gap-2">
      <Dialog>
        <DialogTrigger asChild>
          <Button variant="outline">Suspender</Button>
        </DialogTrigger>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Suspender Assinatura</DialogTitle>
          </DialogHeader>
          <Textarea
            placeholder="Motivo da suspensão..."
            value={motivo}
            onChange={(e) => setMotivo(e.target.value)}
          />
          <Button
            onClick={() => suspender.mutate({ id: assinatura.id, motivo })}
            disabled={!motivo || suspender.isPending}
          >
            Confirmar Suspensão
          </Button>
        </DialogContent>
      </Dialog>

      <Dialog>
        <DialogTrigger asChild>
          <Button variant="destructive">Cancelar</Button>
        </DialogTrigger>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Cancelar Assinatura</DialogTitle>
          </DialogHeader>
          <Textarea
            placeholder="Motivo do cancelamento..."
            value={motivo}
            onChange={(e) => setMotivo(e.target.value)}
          />
          <Button
            onClick={() => cancelar.mutate({ id: assinatura.id, motivo })}
            disabled={!motivo || cancelar.isPending}
            variant="destructive"
          >
            Confirmar Cancelamento
          </Button>
        </DialogContent>
      </Dialog>
    </div>
  );
}
```

---

## 🚨 TRATAMENTO DE ERROS

```typescript
// lib/api/error-handler.ts
import { toast } from '@/components/ui/use-toast';

export class ApiError extends Error {
  constructor(
    public status: number,
    public data: any,
    message?: string
  ) {
    super(message || 'API Error');
  }
}

export const handleApiError = (error: any) => {
  if (error.response) {
    // Erros do servidor (4xx, 5xx)
    const status = error.response.status;
    const data = error.response.data;

    if (status === 401) {
      // Token expirado ou inválido
      toast({
        title: 'Sessão expirada',
        description: 'Por favor, faça login novamente.',
        variant: 'destructive',
      });
      window.location.href = '/login';
      return;
    }

    if (status === 403) {
      // Sem permissão
      toast({
        title: 'Acesso negado',
        description: 'Você não tem permissão para realizar esta ação.',
        variant: 'destructive',
      });
      return;
    }

    if (status === 404) {
      toast({
        title: 'Não encontrado',
        description: 'O recurso solicitado não foi encontrado.',
        variant: 'destructive',
      });
      return;
    }

    if (status === 400) {
      // Erros de validação
      const errors = Object.entries(data).map(([field, messages]) => 
        `${field}: ${(messages as string[]).join(', ')}`
      ).join('\n');
      
      toast({
        title: 'Erros de validação',
        description: errors,
        variant: 'destructive',
      });
      return;
    }

    if (status >= 500) {
      toast({
        title: 'Erro no servidor',
        description: 'Ocorreu um erro no servidor. Tente novamente mais tarde.',
        variant: 'destructive',
      });
      return;
    }
  }

  // Erro de rede
  toast({
    title: 'Erro de conexão',
    description: 'Verifique sua conexão com a internet.',
    variant: 'destructive',
  });
};
```

---

## 📦 PAGINAÇÃO E FILTROS

### Exemplo: Componente de Paginação
```typescript
// components/ui/pagination.tsx
import { Button } from '@/components/ui/button';

interface PaginationProps {
  currentPage: number;
  totalPages: number;
  onPageChange: (page: number) => void;
}

export function Pagination({ currentPage, totalPages, onPageChange }: PaginationProps) {
  return (
    <div className="flex items-center justify-between px-2">
      <div className="flex-1 text-sm text-muted-foreground">
        Página {currentPage} de {totalPages}
      </div>
      <div className="flex items-center space-x-2">
        <Button
          variant="outline"
          size="sm"
          onClick={() => onPageChange(currentPage - 1)}
          disabled={currentPage === 1}
        >
          Anterior
        </Button>
        <Button
          variant="outline"
          size="sm"
          onClick={() => onPageChange(currentPage + 1)}
          disabled={currentPage === totalPages}
        >
          Próxima
        </Button>
      </div>
    </div>
  );
}
```

### Exemplo: Filtros de Assinatura
```typescript
// components/billing/AssinaturaFilters.tsx
'use client';

import { Input } from '@/components/ui/input';
import { Select } from '@/components/ui/select';
import { Button } from '@/components/ui/button';
import { useState } from 'react';

export function AssinaturaFilters({ onFilter }: { onFilter: (filters: any) => void }) {
  const [filters, setFilters] = useState({
    search: '',
    status: '',
    plano: '',
    ativa: '',
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onFilter(filters);
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <Input
        placeholder="Buscar por razão social, CNPJ..."
        value={filters.search}
        onChange={(e) => setFilters({ ...filters, search: e.target.value })}
      />
      
      <Select
        value={filters.status}
        onValueChange={(value) => setFilters({ ...filters, status: value })}
      >
        <option value="">Todos os status</option>
        <option value="ativa">Ativa</option>
        <option value="suspensa">Suspensa</option>
        <option value="cancelada">Cancelada</option>
        <option value="vencida">Vencida</option>
      </Select>

      <Select
        value={filters.ativa}
        onValueChange={(value) => setFilters({ ...filters, ativa: value })}
      >
        <option value="">Todas</option>
        <option value="true">Somente Ativas</option>
        <option value="false">Somente Inativas</option>
      </Select>

      <div className="flex gap-2">
        <Button type="submit">Filtrar</Button>
        <Button
          type="button"
          variant="outline"
          onClick={() => {
            setFilters({ search: '', status: '', plano: '', ativa: '' });
            onFilter({});
          }}
        >
          Limpar
        </Button>
      </div>
    </form>
  );
}
```

---

## 📝 TIPOS TYPESCRIPT EXPORTADOS

```typescript
// types/billing.ts
export interface Plano {
  id: string;
  codigo: string;
  nome: string;
  descricao: string;
  preco_mensal: string;
  preco_anual: string | null;
  desconto_percentual_anual: number;
  periodo_trial_dias: number;
  ativo: boolean;
  destaque: boolean;
  modulos_inclusos: string[];
  limite_usuarios: number;
  limite_empresas: number;
  limite_contratos: number;
  recursos_inclusos: Record<string, any>;
  created_at: string;
  updated_at: string;
  preco_anual_calculado: string;
}

export interface Assinatura {
  id: string;
  contabilidade: string;
  contabilidade_razao_social: string;
  contabilidade_cnpj: string;
  plano: string;
  plano_nome: string;
  plano_codigo: string;
  data_inicio: string;
  data_fim: string | null;
  data_proxima_renovacao: string;
  status: 'ativa' | 'suspensa' | 'cancelada' | 'vencida';
  motivo_suspensao: string | null;
  data_suspensao: string | null;
  motivo_cancelamento: string | null;
  data_cancelamento: string | null;
  trial_ate: string | null;
  valor_mensal: string;
  desconto_percentual: number;
  dia_vencimento: number;
  observacoes: string;
  metadados: Record<string, any>;
  created_at: string;
  updated_at: string;
  esta_ativa: boolean;
}

// ... more types
```

---

## 📚 DOCUMENTAÇÃO DE REFERÊNCIA RÁPIDA

### URLs Base dos Módulos
- **Auth**: `/api/auth/`
- **Billing**: `/api/billing/`
- **Administração**: `/api/administracao/`
- **Gestão**: `/api/gestao/`
- **Dashboards**: `/api/dashboards/`

### Headers Obrigatórios
```typescript
{
  'Authorization': 'Bearer {access_token}',
  'X-Contabilidade-ID': '{contabilidade_uuid}', // Exceto para superusers
  'Content-Type': 'application/json'
}
```

### Códigos de Status HTTP
- **200**: Sucesso
- **201**: Criado com sucesso
- **204**: Sucesso sem conteúdo (geralmente DELETE)
- **400**: Erro de validação
- **401**: Não autenticado
- **403**: Sem permissão
- **404**: Não encontrado
- **500**: Erro no servidor

---

**Última Atualização**: 20/10/2025 19:00  
**Total de Endpoints Documentados**: 69 (43 Billing + 26 Administração)  
**Status**: ✅ Documentação completa para implementação frontend
GET    /api/billing/pagamentos/                     // Listar pagamentos
POST   /api/billing/faturas/{id}/pagar/             // Processar pagamento

// Tipos TypeScript
interface Plano {
  id: string;
  codigo: string;
  nome: string;
  preco_mensal: number;
  preco_anual: number;
  modulos_inclusos: string[];
  limites: {
    usuarios: number;
    empresas: number;
    contratos: number;
  };
  ativo: boolean;
}
```

## 👥 Aplicação Client

### Módulos e Endpoints

#### 1. Módulo Gestão

##### Carteira de Clientes
```typescript
// Endpoint
GET /api/gestao/carteira/

// Parâmetros de Query
{
  "search": "Empresa ABC",           // Busca por razão social
  "regime_fiscal": "simples",        // Filtro por regime
  "ramo_atividade": "servicos",      // Filtro por ramo
  "status_cliente": "ativo",         // Filtro por status
  "page": 1,                         // Paginação
  "page_size": 20                    // Tamanho da página
}

// Response
{
  "count": 89,
  "next": "http://localhost:8000/api/gestao/carteira/?page=2",
  "previous": null,
  "results": [
    {
      "id": "uuid",
      "razao_social": "Empresa ABC Ltda",
      "cnpj": "12.345.678/0001-90",
      "regime_fiscal": "simples",
      "ramo_atividade": "servicos",
      "status_cliente": "ativo",
      "data_inicio_contrato": "2023-02-01",
      "tempo_contrato_meses": 24,
      "ultima_movimentacao": "2024-12-15"
    }
  ]
}
```

##### Detalhes do Cliente
```typescript
// Endpoint
GET /api/gestao/clientes/{id}/

// Response
{
  "id": "uuid",
  "razao_social": "Empresa ABC Ltda",
  "cnpj": "12.345.678/0001-90",
  "nome_fantasia": "ABC Ltda",
  "regime_fiscal": "simples",
  "ramo_atividade": "servicos",
  "uf": "SP",
  "cidade": "São Paulo",
  "ativo": true,
  "data_inicio_atividades": "2020-01-15",
  "contratos": [
    {
      "id": "uuid",
      "data_inicio": "2023-02-01",
      "data_termino": "2024-01-31",
      "valor_honorario": 500.00,
      "plano_servico": "premium",
      "modulos_contratados": ["contabil", "fiscal", "rh"],
      "status_cobranca": "em_dia"
    }
  ],
  "faturamento_total": 15000.00,
  "faturamento_mes_atual": 1250.00,
  "notas_fiscais_mes": 15
}
```

#### 2. Módulo Dashboards

##### Dashboard Demográfico
```typescript
// Endpoints
GET /api/dashboards/demografico/indicadores/         // Indicadores gerais
GET /api/dashboards/demografico/colaboradores/       // Evolução mensal
GET /api/dashboards/demografico/distribuicoes/       // Distribuições

// Exemplo - Indicadores
{
  "total_colaboradores": 45,
  "colaboradores_ativos": 42,
  "colaboradores_inativos": 3,
  "turnover_mensal": 2.5,
  "turnover_anual": 15.2,
  "media_idade": 35.5,
  "percentual_masculino": 60.0,
  "percentual_feminino": 40.0,
  "distribuicao_escolaridade": {
    "fundamental": 5,
    "medio": 20,
    "superior": 15,
    "pos": 5
  }
}
```

##### Dashboard Fiscal
```typescript
// Endpoints
GET /api/dashboards/fiscal/faturamento/              // Visão geral
GET /api/dashboards/fiscal/produtos/                 // Top produtos
GET /api/dashboards/fiscal/clientes/                 // Top clientes
GET /api/dashboards/fiscal/geolocalizacao/           // Por UF
GET /api/dashboards/fiscal/impostos/                 // Impostos devidos

// Exemplo - Faturamento
{
  "total_faturamento": 125000.00,
  "total_impostos": 18750.00,
  "percentual_impostos": 15.0,
  "total_notas_fiscais": 150,
  "media_valor_nota": 833.33,
  "faturamento_mes_anterior": 118000.00,
  "crescimento_percentual": 5.9
}
```

##### Dashboard Contábil
```typescript
// Endpoints
GET /api/dashboards/contabil/indicadores/            // Indicadores
GET /api/dashboards/contabil/evolucao/               // Evolução mensal
GET /api/dashboards/contabil/grupos/                 // Por grupos
GET /api/dashboards/contabil/top-contas/             // Top contas

// Exemplo - Indicadores
{
  "total_ativo": 2500000.00,
  "total_passivo": 1800000.00,
  "patrimonio_liquido": 700000.00,
  "receita_total": 1500000.00,
  "despesas_total": 1200000.00,
  "lucro_liquido": 300000.00,
  "margem_lucro": 20.0
}
```

#### 3. Módulo Export
```typescript
// Endpoints
POST /api/export/carteira/pdf/                       // Carteira em PDF
POST /api/export/carteira/excel/                     // Carteira em Excel
POST /api/export/clientes/pdf/                       // Clientes em PDF
POST /api/export/clientes/excel/                     // Clientes em Excel
POST /api/export/relatorio-geral/pdf/                // Relatório geral

// Request
{
  "filtros": {
    "regime_fiscal": "simples",
    "ramo_atividade": "servicos",
    "data_inicio": "2024-01-01",
    "data_fim": "2024-12-31"
  },
  "formato": "pdf",
  "incluir_graficos": true
}

// Response
{
  "arquivo_url": "http://localhost:8000/media/exports/carteira_20241215.pdf",
  "nome_arquivo": "carteira_20241215.pdf",
  "tamanho_bytes": 1024000,
  "data_geracao": "2024-12-15T10:30:00Z"
}
```

## 🔄 Implementação dos Serviços

### 1. Serviço de Carteira
```typescript
// apps/client/src/lib/services/carteiraService.ts
import { apiClient } from '@gestk/shared';

export class CarteiraService {
  static async getCarteira(filtros?: CarteiraFiltros) {
    const params = new URLSearchParams();
    
    if (filtros?.search) params.append('search', filtros.search);
    if (filtros?.regime_fiscal) params.append('regime_fiscal', filtros.regime_fiscal);
    if (filtros?.ramo_atividade) params.append('ramo_atividade', filtros.ramo_atividade);
    if (filtros?.status_cliente) params.append('status_cliente', filtros.status_cliente);
    if (filtros?.page) params.append('page', filtros.page.toString());
    if (filtros?.page_size) params.append('page_size', filtros.page_size.toString());

    return apiClient.get<ApiResponse<CarteiraCliente>>(
      `/api/gestao/carteira/?${params.toString()}`
    );
  }

  static async getClienteDetalhado(id: string) {
    return apiClient.get<ClienteDetalhado>(`/api/gestao/clientes/${id}/`);
  }

  static async exportarCarteira(formato: 'pdf' | 'excel', filtros: CarteiraFiltros) {
    return apiClient.post<ExportResponse>(`/api/export/carteira/${formato}/`, {
      filtros,
      formato,
      incluir_graficos: true
    });
  }
}
```

### 2. Serviço de Dashboards
```typescript
// apps/client/src/lib/services/dashboardService.ts
import { apiClient } from '@gestk/shared';

export class DashboardService {
  static async getDemograficoIndicadores() {
    return apiClient.get<DemograficoIndicadores>('/api/dashboards/demografico/indicadores/');
  }

  static async getFiscalFaturamento() {
    return apiClient.get<FiscalFaturamento>('/api/dashboards/fiscal/faturamento/');
  }

  static async getContabilIndicadores() {
    return apiClient.get<ContabilIndicadores>('/api/dashboards/contabil/indicadores/');
  }

  static async getOrganizacionalEstrutura() {
    return apiClient.get<OrganizacionalEstrutura>('/api/dashboards/organizacional/estrutura/');
  }

  static async getPessoalFolhaPagamento() {
    return apiClient.get<PessoalFolhaPagamento>('/api/dashboards/pessoal/folha-pagamento/');
  }
}
```

### 3. Hook de API
```typescript
// packages/shared/src/hooks/useApi.ts
import { useState, useEffect } from 'react';
import { apiClient } from '../api/client';

export function useApi<T>(
  endpoint: string,
  options?: {
    immediate?: boolean;
    params?: Record<string, any>;
  }
) {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const fetchData = async () => {
    try {
      setLoading(true);
      setError(null);
      const result = await apiClient.get<T>(endpoint, { params: options?.params });
      setData(result);
    } catch (err) {
      setError(err as Error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (options?.immediate !== false) {
      fetchData();
    }
  }, [endpoint, JSON.stringify(options?.params)]);

  return { data, loading, error, refetch: fetchData };
}
```

## 🎯 Configuração de Ambiente

### Variáveis de Ambiente

#### Admin App (.env.local)
```bash
# API Configuration
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_API_VERSION=v1

# Authentication
NEXTAUTH_SECRET=your-secret-key
NEXTAUTH_URL=http://localhost:3000

# App Context
NEXT_PUBLIC_APP_CONTEXT=admin
```

#### Client App (.env.local)
```bash
# API Configuration
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_API_VERSION=v1

# Authentication
NEXTAUTH_SECRET=your-secret-key
NEXTAUTH_URL=http://localhost:3001

# App Context
NEXT_PUBLIC_APP_CONTEXT=client
```

### Configuração do Cliente API
```typescript
// packages/shared/src/api/index.ts
import { ApiClient } from './client';

// Configuração base
const apiConfig = {
  baseURL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
};

// Instância singleton
export const apiClient = new ApiClient(apiConfig);

// Configurar contexto da aplicação
if (typeof window !== 'undefined') {
  const appContext = process.env.NEXT_PUBLIC_APP_CONTEXT as 'admin' | 'client';
  if (appContext) {
    apiClient.setAppContext(appContext);
  }
}
```

## 🔐 Aplicação da Regra de Ouro

### Isolamento Automático
A **Regra de Ouro** é aplicada automaticamente em todas as requisições:

1. **Middleware Backend**: Filtra automaticamente por `contabilidade`
2. **Headers Frontend**: Envia `X-Contabilidade-ID` automaticamente
3. **Contexto de Usuário**: Mantém contabilidade ativa no localStorage
4. **Validação de Acesso**: Verifica permissões antes de cada operação

### Exemplo de Implementação
```typescript
// Contexto de usuário
const useUserContext = () => {
  const [user, setUser] = useState<User | null>(null);
  const [contabilidade, setContabilidade] = useState<Contabilidade | null>(null);

  const login = async (credentials: LoginData) => {
    const response = await apiClient.post<LoginResponse>('/api/auth/login/', credentials);
    
    // Configurar tokens
    apiClient.setAccessToken(response.access);
    apiClient.setRefreshToken(response.refresh);
    
    // Configurar contexto
    setUser(response.user);
    setContabilidade(response.user.contabilidade);
    apiClient.setContabilidadeId(response.user.contabilidade.id);
    
    return response;
  };

  const switchContabilidade = async (contabilidadeId: string) => {
    // Verificar se usuário tem acesso à contabilidade
    const hasAccess = await apiClient.get<boolean>(
      `/api/administracao/usuarios-acesso/verificar-acesso/?contabilidade=${contabilidadeId}`
    );
    
    if (hasAccess) {
      setContabilidade(contabilidadeId);
      apiClient.setContabilidadeId(contabilidadeId);
    }
  };

  return { user, contabilidade, login, switchContabilidade };
};
```

## 📊 Mapeamento de Dados

### Tabelas ↔ APIs ↔ Frontend

| Tabela | Modelo | API | Frontend | Dados |
|--------|--------|-----|----------|-------|
| `core_contabilidades` | `Contabilidade` | `/api/administracao/contabilidades/` | Admin | Gestão de contabilidades |
| `core_usuarios` | `Usuario` | `/api/auth/user/` | Admin/Client | Dados do usuário |
| `pessoas_juridicas` | `PessoaJuridica` | `/api/gestao/carteira/` | Client | Carteira de clientes |
| `fiscal_notas_fiscais` | `NotaFiscal` | `/api/dashboards/fiscal/` | Client | Dashboard fiscal |
| `funcionarios_funcionarios` | `Funcionario` | `/api/dashboards/demografico/` | Client | Dashboard demográfico |
| `contabil_lancamentos_contabeis` | `LancamentoContabil` | `/api/dashboards/contabil/` | Client | Dashboard contábil |

## 🚀 Próximos Passos

### 1. Implementação Imediata
- [ ] Configurar variáveis de ambiente
- [ ] Implementar serviços de API
- [ ] Criar hooks personalizados
- [ ] Atualizar tipos TypeScript

### 2. Testes de Integração
- [ ] Testar autenticação
- [ ] Validar isolamento multi-tenant
- [ ] Testar todos os endpoints
- [ ] Verificar performance

### 3. Deploy e Produção
- [ ] Configurar URLs de produção
- [ ] Implementar monitoramento
- [ ] Configurar logs
- [ ] Testes de carga

## 📚 Documentação Relacionada

- [Mapeamento Completo](MAPEAMENTO_TABELAS_APIS_FRONTEND.md) - Tabelas ↔ APIs ↔ Frontend
- [API de Administração](api/ADMINISTRACAO_API.md) - Endpoints administrativos
- [Arquitetura Multi-Tenant](arquitetura/MULTI_TENANCY.md) - Sistema multi-tenant
- [Guia de Desenvolvimento](desenvolvimento/API_ADMINISTRACAO.md) - Padrões de desenvolvimento

---

**Status**: ✅ Documentação completa  
**Última atualização**: 08/10/2025  
**Versão**: 1.0




