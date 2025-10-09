# 🔗 Integração Frontend-Backend - GESTK

## 📋 Visão Geral

Este documento detalha a integração completa entre o frontend (Next.js) e o backend (Django REST API) do GESTK, baseado no mapeamento completo das tabelas, APIs e funcionalidades.

## 🏗️ Arquitetura de Integração

### Stack Tecnológica
- **Frontend**: Next.js 15, TypeScript, Tailwind CSS, shadcn/ui
- **Backend**: Django 4.2, Django REST Framework, PostgreSQL
- **Autenticação**: JWT (JSON Web Tokens)
- **Comunicação**: Axios com interceptors automáticos
- **Multi-tenancy**: Isolamento automático por contabilidade

### Fluxo de Dados
```
Frontend (Next.js) → API Client (Axios) → Backend (Django) → Database (PostgreSQL)
                  ← Response ← Serializer ← QuerySet ← Models
```

## 🔐 Sistema de Autenticação

### Configuração do Cliente API
```typescript
// packages/shared/src/api/client.ts
export class ApiClient {
  private accessToken: string | null = null;
  private contabilidadeId: string | null = null;
  private appContext: 'admin' | 'client' | null = null;

  // Headers automáticos
  private setupInterceptors() {
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
  }
}
```

### Endpoints de Autenticação
```typescript
// Login
POST /api/auth/login/
{
  "username": "usuario@gestk.com",
  "password": "senha123"
}

// Response
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "user": {
    "id": "uuid",
    "username": "usuario@gestk.com",
    "email": "usuario@gestk.com",
    "tipo_usuario": "operacional",
    "contabilidade": {
      "id": "uuid",
      "razao_social": "Contabilidade ABC"
    }
  }
}
```

## 🏢 Aplicação Admin

### Módulos e Endpoints

#### 1. Gestão de Contratos GESTK
```typescript
// Endpoints
GET    /api/administracao/contratos-gestk/           // Listar contratos
POST   /api/administracao/contratos-gestk/           // Criar contrato
GET    /api/administracao/contratos-gestk/{id}/      // Detalhes
PUT    /api/administracao/contratos-gestk/{id}/      // Atualizar
DELETE /api/administracao/contratos-gestk/{id}/      // Excluir
POST   /api/administracao/contratos-gestk/{id}/cancelar/  // Cancelar

// Tipos TypeScript
interface ContratoGestk {
  id: string;
  numero_contrato: string;
  contabilidade: Contabilidade;
  plano_servico: string;
  valor_mensal: number;
  data_inicio: string;
  data_termino?: string;
  status: 'ativo' | 'suspenso' | 'cancelado' | 'vencido';
  modulos_inclusos: string[];
  limites: {
    usuarios: number;
    empresas: number;
    contratos: number;
  };
}
```

#### 2. Gestão de Usuários e Acessos
```typescript
// Endpoints
GET    /api/administracao/usuarios-acesso/           // Listar acessos
POST   /api/administracao/usuarios-acesso/           // Conceder acesso
GET    /api/administracao/usuarios-acesso/{id}/      // Detalhes
PUT    /api/administracao/usuarios-acesso/{id}/      // Atualizar
DELETE /api/administracao/usuarios-acesso/{id}/      // Revogar acesso

// Tipos TypeScript
interface UsuarioAcesso {
  id: string;
  usuario: User;
  contabilidade: Contabilidade;
  contrato?: ContratoGestk;
  empresa_cnpj?: string;
  role: 'superuser' | 'admin' | 'operacional' | 'etl' | 'readonly';
  modulos_acesso: string[];
  data_inicio: string;
  data_fim?: string;
  ativo: boolean;
}
```

#### 3. Sistema de Billing
```typescript
// Endpoints
GET    /api/billing/planos/                         // Listar planos
GET    /api/billing/assinaturas/                    // Listar assinaturas
GET    /api/billing/faturas/                        // Listar faturas
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



