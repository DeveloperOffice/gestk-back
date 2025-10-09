# 🚀 Guia de Implementação Frontend - GESTK

## 📋 Visão Geral

Este guia prático detalha como implementar a integração do frontend com o backend GESTK, baseado no mapeamento completo das APIs e dados.

## 🎯 Objetivos

1. **Configurar** a conexão com o backend
2. **Implementar** serviços de API
3. **Atualizar** tipos TypeScript
4. **Criar** hooks personalizados
5. **Testar** a integração completa

## 🔧 Configuração Inicial

### 1. Variáveis de Ambiente

#### Admin App (`apps/admin/.env.local`)
```bash
# API Configuration
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_API_VERSION=v1

# Authentication
NEXTAUTH_SECRET=your-secret-key-here
NEXTAUTH_URL=http://localhost:3000

# App Context
NEXT_PUBLIC_APP_CONTEXT=admin
```

#### Client App (`apps/client/.env.local`)
```bash
# API Configuration
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_API_VERSION=v1

# Authentication
NEXTAUTH_SECRET=your-secret-key-here
NEXTAUTH_URL=http://localhost:3001

# App Context
NEXT_PUBLIC_APP_CONTEXT=client
```

### 2. Atualizar Tipos TypeScript

#### Admin Types (`apps/admin/src/types/index.ts`)
```typescript
// Manter tipos existentes e adicionar novos campos baseados no backend

export interface Contabilidade {
  id: string
  razao_social: string
  nome_fantasia: string
  cnpj: string
  ativo: boolean
  // Campos de billing (já existem)
  responsavel_financeiro_nome: string
  responsavel_financeiro_email: string
  suspensa_por_inadimplencia: boolean
  saldo_creditos: number
  // Novos campos do backend
  created_at: string
  updated_at: string
}

export interface ContratoGestk {
  id: string
  numero_contrato: string
  contabilidade: Contabilidade
  plano_servico: string
  valor_mensal: number
  data_inicio: string
  data_termino?: string
  status: 'ativo' | 'suspenso' | 'cancelado' | 'vencido'
  modulos_inclusos: string[]
  limites: {
    usuarios: number
    empresas: number
    contratos: number
  }
  created_at: string
  updated_at: string
}

// Adicionar tipos para billing
export interface Plano {
  id: string
  codigo: string
  nome: string
  preco_mensal: number
  preco_anual: number
  modulos_inclusos: string[]
  limites: {
    usuarios: number
    empresas: number
    contratos: number
  }
  ativo: boolean
}

export interface Assinatura {
  id: string
  contabilidade: Contabilidade
  plano: Plano
  data_inicio: string
  data_fim?: string
  status: 'ativa' | 'suspensa' | 'cancelada' | 'vencida'
  valor_mensal: number
  ciclo_cobranca: 'mensal' | 'anual'
}

export interface Fatura {
  id: string
  assinatura: Assinatura
  numero_fatura: string
  competencia: string
  valor_original: number
  valor_final: number
  data_emissao: string
  data_vencimento: string
  status: 'pendente' | 'paga' | 'vencida' | 'cancelada'
}

export interface Pagamento {
  id: string
  fatura: Fatura
  valor: number
  metodo: 'pix' | 'cartao' | 'boleto' | 'transferencia'
  transacao_id: string
  status: 'pendente' | 'processando' | 'aprovado' | 'rejeitado' | 'estornado'
  data_pagamento?: string
}
```

#### Client Types (`apps/client/src/types/index.ts`)
```typescript
// Tipos para dados de gestão
export interface CarteiraCliente {
  id: string
  razao_social: string
  cnpj: string
  regime_fiscal: 'simples' | 'presumido' | 'real' | 'mei'
  ramo_atividade: 'comercio' | 'industria' | 'servicos' | 'tecnologia'
  status_cliente: 'ativo' | 'inativo' | 'novo' | 'sem_movimentacao'
  data_abertura: string
  data_inicio_contrato: string
  tempo_contrato_meses: number
  ultima_movimentacao: string
  uf: string
  cidade: string
}

export interface ClienteDetalhado extends CarteiraCliente {
  nome_fantasia: string
  ativo: boolean
  data_inicio_atividades: string
  contratos: ContratoCliente[]
  faturamento_total: number
  faturamento_mes_atual: number
  notas_fiscais_mes: number
}

export interface ContratoCliente {
  id: string
  data_inicio: string
  data_termino?: string
  valor_honorario: number
  plano_servico: string
  modulos_contratados: string[]
  status_cobranca: 'em_dia' | 'atrasado' | 'suspenso'
}

// Tipos para dashboards
export interface DemograficoIndicadores {
  total_colaboradores: number
  colaboradores_ativos: number
  colaboradores_inativos: number
  turnover_mensal: number
  turnover_anual: number
  media_idade: number
  percentual_masculino: number
  percentual_feminino: number
  distribuicao_escolaridade: {
    fundamental: number
    medio: number
    superior: number
    pos: number
  }
}

export interface FiscalFaturamento {
  total_faturamento: number
  total_impostos: number
  percentual_impostos: number
  total_notas_fiscais: number
  media_valor_nota: number
  faturamento_mes_anterior: number
  crescimento_percentual: number
}

export interface ContabilIndicadores {
  total_ativo: number
  total_passivo: number
  patrimonio_liquido: number
  receita_total: number
  despesas_total: number
  lucro_liquido: number
  margem_lucro: number
}

// Tipos para export
export interface ExportResponse {
  arquivo_url: string
  nome_arquivo: string
  tamanho_bytes: number
  data_geracao: string
}

export interface CarteiraFiltros {
  search?: string
  regime_fiscal?: string
  ramo_atividade?: string
  status_cliente?: string
  page?: number
  page_size?: number
}
```

## 🔌 Implementação dos Serviços

### 1. Serviço de Autenticação

#### Admin (`apps/admin/src/lib/services/authService.ts`)
```typescript
import { apiClient } from '@gestk/shared';
import type { LoginData, LoginResponse, User } from '../types';

export class AuthService {
  static async login(credentials: LoginData): Promise<LoginResponse> {
    const response = await apiClient.post<LoginResponse>('/api/auth/login/', credentials);
    
    // Configurar tokens
    apiClient.setAccessToken(response.access);
    apiClient.setRefreshToken(response.refresh);
    
    // Configurar contexto admin
    apiClient.setAppContext('admin');
    
    return response;
  }

  static async logout(): Promise<void> {
    try {
      await apiClient.post('/api/auth/logout/');
    } finally {
      apiClient.clearAuth();
    }
  }

  static async getCurrentUser(): Promise<User> {
    return apiClient.get<User>('/api/auth/user/');
  }

  static async refreshToken(): Promise<string> {
    const refreshToken = apiClient.getRefreshToken();
    if (!refreshToken) throw new Error('No refresh token available');
    
    const response = await apiClient.post<{ access: string }>('/api/auth/token/refresh/', {
      refresh: refreshToken
    });
    
    apiClient.setAccessToken(response.access);
    return response.access;
  }
}
```

#### Client (`apps/client/src/lib/services/authService.ts`)
```typescript
import { apiClient } from '@gestk/shared';
import type { LoginData, LoginResponse, User } from '../types';

export class AuthService {
  static async login(credentials: LoginData): Promise<LoginResponse> {
    const response = await apiClient.post<LoginResponse>('/api/auth/login/', credentials);
    
    // Configurar tokens
    apiClient.setAccessToken(response.access);
    apiClient.setRefreshToken(response.refresh);
    
    // Configurar contexto client
    apiClient.setAppContext('client');
    
    // Configurar contabilidade do usuário
    if (response.user.contabilidade) {
      apiClient.setContabilidadeId(response.user.contabilidade.id);
    }
    
    return response;
  }

  static async logout(): Promise<void> {
    try {
      await apiClient.post('/api/auth/logout/');
    } finally {
      apiClient.clearAuth();
    }
  }

  static async getCurrentUser(): Promise<User> {
    return apiClient.get<User>('/api/auth/user/');
  }

  static async switchContabilidade(contabilidadeId: string): Promise<void> {
    // Verificar se usuário tem acesso à contabilidade
    const hasAccess = await apiClient.get<boolean>(
      `/api/administracao/usuarios-acesso/verificar-acesso/?contabilidade=${contabilidadeId}`
    );
    
    if (hasAccess) {
      apiClient.setContabilidadeId(contabilidadeId);
    } else {
      throw new Error('Usuário não tem acesso a esta contabilidade');
    }
  }
}
```

### 2. Serviço de Carteira (Client)

#### (`apps/client/src/lib/services/carteiraService.ts`)
```typescript
import { apiClient } from '@gestk/shared';
import type { 
  CarteiraCliente, 
  ClienteDetalhado, 
  CarteiraFiltros, 
  ApiResponse,
  ExportResponse 
} from '../types';

export class CarteiraService {
  static async getCarteira(filtros?: CarteiraFiltros): Promise<ApiResponse<CarteiraCliente>> {
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

  static async getClienteDetalhado(id: string): Promise<ClienteDetalhado> {
    return apiClient.get<ClienteDetalhado>(`/api/gestao/clientes/${id}/`);
  }

  static async getCategorias(): Promise<CategoriaCliente[]> {
    return apiClient.get<CategoriaCliente[]>('/api/gestao/carteira/categorias/');
  }

  static async getEvolucaoMensal(): Promise<EvolucaoMensal[]> {
    return apiClient.get<EvolucaoMensal[]>('/api/gestao/carteira/evolucao-mensal/');
  }

  static async exportarCarteira(formato: 'pdf' | 'excel', filtros?: CarteiraFiltros): Promise<ExportResponse> {
    return apiClient.post<ExportResponse>(`/api/export/carteira/${formato}/`, {
      filtros,
      formato,
      incluir_graficos: true
    });
  }
}
```

### 3. Serviço de Dashboards (Client)

#### (`apps/client/src/lib/services/dashboardService.ts`)
```typescript
import { apiClient } from '@gestk/shared';
import type { 
  DemograficoIndicadores,
  FiscalFaturamento,
  ContabilIndicadores,
  OrganizacionalEstrutura,
  PessoalFolhaPagamento
} from '../types';

export class DashboardService {
  // Dashboard Demográfico
  static async getDemograficoIndicadores(): Promise<DemograficoIndicadores> {
    return apiClient.get<DemograficoIndicadores>('/api/dashboards/demografico/indicadores/');
  }

  static async getDemograficoColaboradores(): Promise<EvolucaoMensal[]> {
    return apiClient.get<EvolucaoMensal[]>('/api/dashboards/demografico/colaboradores/');
  }

  static async getDemograficoDistribuicoes(): Promise<DistribuicoesDemograficas> {
    return apiClient.get<DistribuicoesDemograficas>('/api/dashboards/demografico/distribuicoes/');
  }

  // Dashboard Fiscal
  static async getFiscalFaturamento(): Promise<FiscalFaturamento> {
    return apiClient.get<FiscalFaturamento>('/api/dashboards/fiscal/faturamento/');
  }

  static async getFiscalProdutos(): Promise<ProdutoFiscal[]> {
    return apiClient.get<ProdutoFiscal[]>('/api/dashboards/fiscal/produtos/');
  }

  static async getFiscalClientes(): Promise<ClienteFiscal[]> {
    return apiClient.get<ClienteFiscal[]>('/api/dashboards/fiscal/clientes/');
  }

  static async getFiscalGeolocalizacao(): Promise<GeolocalizacaoFiscal[]> {
    return apiClient.get<GeolocalizacaoFiscal[]>('/api/dashboards/fiscal/geolocalizacao/');
  }

  // Dashboard Contábil
  static async getContabilIndicadores(): Promise<ContabilIndicadores> {
    return apiClient.get<ContabilIndicadores>('/api/dashboards/contabil/indicadores/');
  }

  static async getContabilEvolucao(): Promise<EvolucaoContabil[]> {
    return apiClient.get<EvolucaoContabil[]>('/api/dashboards/contabil/evolucao/');
  }

  static async getContabilGrupos(): Promise<GrupoContabil[]> {
    return apiClient.get<GrupoContabil[]>('/api/dashboards/contabil/grupos/');
  }

  static async getContabilTopContas(): Promise<TopConta[]> {
    return apiClient.get<TopConta[]>('/api/dashboards/contabil/top-contas/');
  }

  // Dashboard Organizacional
  static async getOrganizacionalEstrutura(): Promise<OrganizacionalEstrutura> {
    return apiClient.get<OrganizacionalEstrutura>('/api/dashboards/organizacional/estrutura/');
  }

  static async getOrganizacionalDistribuicaoDepartamentos(): Promise<DistribuicaoDepartamento[]> {
    return apiClient.get<DistribuicaoDepartamento[]>('/api/dashboards/organizacional/distribuicao-departamentos/');
  }

  static async getOrganizacionalHierarquia(): Promise<HierarquiaOrganizacional[]> {
    return apiClient.get<HierarquiaOrganizacional[]>('/api/dashboards/organizacional/hierarquia/');
  }

  static async getOrganizacionalCustoDepartamento(): Promise<CustoDepartamento[]> {
    return apiClient.get<CustoDepartamento[]>('/api/dashboards/organizacional/custo-departamento/');
  }

  // Dashboard Pessoal
  static async getPessoalFolhaPagamento(): Promise<PessoalFolhaPagamento> {
    return apiClient.get<PessoalFolhaPagamento>('/api/dashboards/pessoal/folha-pagamento/');
  }

  static async getPessoalBeneficios(): Promise<BeneficioPessoal[]> {
    return apiClient.get<BeneficioPessoal[]>('/api/dashboards/pessoal/beneficios/');
  }

  static async getPessoalCustosTrabalhistas(): Promise<CustoTrabalhista[]> {
    return apiClient.get<CustoTrabalhista[]>('/api/dashboards/pessoal/custos-trabalhistas/');
  }

  static async getPessoalEvolucaoFolha(): Promise<EvolucaoFolha[]> {
    return apiClient.get<EvolucaoFolha[]>('/api/dashboards/pessoal/evolucao-folha/');
  }
}
```

### 4. Serviço de Administração (Admin)

#### (`apps/admin/src/lib/services/administracaoService.ts`)
```typescript
import { apiClient } from '@gestk/shared';
import type { 
  ContratoGestk, 
  UsuarioAcesso, 
  Contabilidade,
  ApiResponse 
} from '../types';

export class AdministracaoService {
  // Contratos GESTK
  static async getContratosGestk(): Promise<ApiResponse<ContratoGestk>> {
    return apiClient.get<ApiResponse<ContratoGestk>>('/api/administracao/contratos-gestk/');
  }

  static async getContratoGestk(id: string): Promise<ContratoGestk> {
    return apiClient.get<ContratoGestk>(`/api/administracao/contratos-gestk/${id}/`);
  }

  static async createContratoGestk(data: Partial<ContratoGestk>): Promise<ContratoGestk> {
    return apiClient.post<ContratoGestk>('/api/administracao/contratos-gestk/', data);
  }

  static async updateContratoGestk(id: string, data: Partial<ContratoGestk>): Promise<ContratoGestk> {
    return apiClient.put<ContratoGestk>(`/api/administracao/contratos-gestk/${id}/`, data);
  }

  static async deleteContratoGestk(id: string): Promise<void> {
    return apiClient.delete<void>(`/api/administracao/contratos-gestk/${id}/`);
  }

  static async cancelarContratoGestk(id: string): Promise<ContratoGestk> {
    return apiClient.post<ContratoGestk>(`/api/administracao/contratos-gestk/${id}/cancelar/`);
  }

  // Usuários e Acessos
  static async getUsuariosAcesso(): Promise<ApiResponse<UsuarioAcesso>> {
    return apiClient.get<ApiResponse<UsuarioAcesso>>('/api/administracao/usuarios-acesso/');
  }

  static async getUsuarioAcesso(id: string): Promise<UsuarioAcesso> {
    return apiClient.get<UsuarioAcesso>(`/api/administracao/usuarios-acesso/${id}/`);
  }

  static async createUsuarioAcesso(data: Partial<UsuarioAcesso>): Promise<UsuarioAcesso> {
    return apiClient.post<UsuarioAcesso>('/api/administracao/usuarios-acesso/', data);
  }

  static async updateUsuarioAcesso(id: string, data: Partial<UsuarioAcesso>): Promise<UsuarioAcesso> {
    return apiClient.put<UsuarioAcesso>(`/api/administracao/usuarios-acesso/${id}/`, data);
  }

  static async deleteUsuarioAcesso(id: string): Promise<void> {
    return apiClient.delete<void>(`/api/administracao/usuarios-acesso/${id}/`);
  }

  // Contabilidades
  static async getContabilidades(): Promise<ApiResponse<Contabilidade>> {
    return apiClient.get<ApiResponse<Contabilidade>>('/api/administracao/contabilidades/');
  }

  static async getContabilidade(id: string): Promise<Contabilidade> {
    return apiClient.get<Contabilidade>(`/api/administracao/contabilidades/${id}/`);
  }

  static async updateContabilidade(id: string, data: Partial<Contabilidade>): Promise<Contabilidade> {
    return apiClient.put<Contabilidade>(`/api/administracao/contabilidades/${id}/`, data);
  }
}
```

## 🎣 Hooks Personalizados

### 1. Hook de API Genérico

#### (`packages/shared/src/hooks/useApi.ts`)
```typescript
import { useState, useEffect, useCallback } from 'react';
import { apiClient } from '../api/client';

interface UseApiOptions<T> {
  immediate?: boolean;
  params?: Record<string, any>;
  onSuccess?: (data: T) => void;
  onError?: (error: Error) => void;
}

export function useApi<T>(
  endpoint: string,
  options: UseApiOptions<T> = {}
) {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const result = await apiClient.get<T>(endpoint, { params: options.params });
      setData(result);
      options.onSuccess?.(result);
    } catch (err) {
      const error = err as Error;
      setError(error);
      options.onError?.(error);
    } finally {
      setLoading(false);
    }
  }, [endpoint, JSON.stringify(options.params)]);

  useEffect(() => {
    if (options.immediate !== false) {
      fetchData();
    }
  }, [fetchData, options.immediate]);

  return { 
    data, 
    loading, 
    error, 
    refetch: fetchData,
    mutate: setData
  };
}
```

### 2. Hook de Carteira (Client)

#### (`apps/client/src/hooks/useCarteira.ts`)
```typescript
import { useState, useCallback } from 'react';
import { CarteiraService } from '../lib/services/carteiraService';
import { useApi } from '@gestk/shared';
import type { CarteiraCliente, CarteiraFiltros, ApiResponse } from '../types';

export function useCarteira(filtros?: CarteiraFiltros) {
  const [filtrosAtuais, setFiltrosAtuais] = useState<CarteiraFiltros>(filtros || {});
  
  const { data, loading, error, refetch } = useApi<ApiResponse<CarteiraCliente>>(
    '/api/gestao/carteira/',
    {
      params: filtrosAtuais,
      immediate: true
    }
  );

  const aplicarFiltros = useCallback((novosFiltros: CarteiraFiltros) => {
    setFiltrosAtuais(prev => ({ ...prev, ...novosFiltros }));
  }, []);

  const limparFiltros = useCallback(() => {
    setFiltrosAtuais({});
  }, []);

  const exportarCarteira = useCallback(async (formato: 'pdf' | 'excel') => {
    try {
      const response = await CarteiraService.exportarCarteira(formato, filtrosAtuais);
      return response;
    } catch (error) {
      throw error;
    }
  }, [filtrosAtuais]);

  return {
    carteira: data,
    loading,
    error,
    refetch,
    aplicarFiltros,
    limparFiltros,
    exportarCarteira
  };
}
```

### 3. Hook de Dashboards (Client)

#### (`apps/client/src/hooks/useDashboards.ts`)
```typescript
import { useApi } from '@gestk/shared';
import { DashboardService } from '../lib/services/dashboardService';
import type { 
  DemograficoIndicadores,
  FiscalFaturamento,
  ContabilIndicadores 
} from '../types';

export function useDashboards() {
  // Dashboard Demográfico
  const demograficoIndicadores = useApi<DemograficoIndicadores>(
    '/api/dashboards/demografico/indicadores/',
    { immediate: true }
  );

  const demograficoColaboradores = useApi(
    '/api/dashboards/demografico/colaboradores/',
    { immediate: true }
  );

  const demograficoDistribuicoes = useApi(
    '/api/dashboards/demografico/distribuicoes/',
    { immediate: true }
  );

  // Dashboard Fiscal
  const fiscalFaturamento = useApi<FiscalFaturamento>(
    '/api/dashboards/fiscal/faturamento/',
    { immediate: true }
  );

  const fiscalProdutos = useApi(
    '/api/dashboards/fiscal/produtos/',
    { immediate: true }
  );

  const fiscalClientes = useApi(
    '/api/dashboards/fiscal/clientes/',
    { immediate: true }
  );

  const fiscalGeolocalizacao = useApi(
    '/api/dashboards/fiscal/geolocalizacao/',
    { immediate: true }
  );

  // Dashboard Contábil
  const contabilIndicadores = useApi<ContabilIndicadores>(
    '/api/dashboards/contabil/indicadores/',
    { immediate: true }
  );

  const contabilEvolucao = useApi(
    '/api/dashboards/contabil/evolucao/',
    { immediate: true }
  );

  const contabilGrupos = useApi(
    '/api/dashboards/contabil/grupos/',
    { immediate: true }
  );

  const contabilTopContas = useApi(
    '/api/dashboards/contabil/top-contas/',
    { immediate: true }
  );

  return {
    demografico: {
      indicadores: demograficoIndicadores,
      colaboradores: demograficoColaboradores,
      distribuicoes: demograficoDistribuicoes
    },
    fiscal: {
      faturamento: fiscalFaturamento,
      produtos: fiscalProdutos,
      clientes: fiscalClientes,
      geolocalizacao: fiscalGeolocalizacao
    },
    contabil: {
      indicadores: contabilIndicadores,
      evolucao: contabilEvolucao,
      grupos: contabilGrupos,
      topContas: contabilTopContas
    }
  };
}
```

## 🧪 Testes de Integração

### 1. Teste de Conectividade

#### (`apps/admin/src/app/test/page.tsx`)
```typescript
'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

export default function TestPage() {
  const [result, setResult] = useState<string>('');
  const [loading, setLoading] = useState(false);

  const testConnection = async () => {
    setLoading(true);
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/administracao/`);
      const data = await response.json();
      setResult(JSON.stringify(data, null, 2));
    } catch (error) {
      setResult(`Erro: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="container mx-auto p-6">
      <Card>
        <CardHeader>
          <CardTitle>Teste de Conectividade - Backend</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <Button onClick={testConnection} disabled={loading}>
            {loading ? 'Testando...' : 'Testar Conexão'}
          </Button>
          {result && (
            <pre className="bg-gray-100 p-4 rounded text-sm overflow-auto">
              {result}
            </pre>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
```

### 2. Teste de Autenticação

#### (`apps/client/src/app/test/page.tsx`)
```typescript
'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { AuthService } from '@/lib/services/authService';

export default function TestPage() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [result, setResult] = useState<string>('');
  const [loading, setLoading] = useState(false);

  const testLogin = async () => {
    setLoading(true);
    try {
      const response = await AuthService.login({ username, password });
      setResult(JSON.stringify(response, null, 2));
    } catch (error) {
      setResult(`Erro: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="container mx-auto p-6">
      <Card>
        <CardHeader>
          <CardTitle>Teste de Autenticação</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <Input
            placeholder="Username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
          />
          <Input
            type="password"
            placeholder="Password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
          <Button onClick={testLogin} disabled={loading}>
            {loading ? 'Testando...' : 'Testar Login'}
          </Button>
          {result && (
            <pre className="bg-gray-100 p-4 rounded text-sm overflow-auto">
              {result}
            </pre>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
```

## 🚀 Próximos Passos

### 1. Implementação Imediata
- [ ] Configurar variáveis de ambiente
- [ ] Implementar serviços de API
- [ ] Criar hooks personalizados
- [ ] Atualizar tipos TypeScript
- [ ] Testar conectividade

### 2. Integração com Componentes
- [ ] Atualizar componentes para usar dados reais
- [ ] Implementar loading states
- [ ] Adicionar tratamento de erros
- [ ] Implementar refresh automático

### 3. Testes e Validação
- [ ] Testes de integração completos
- [ ] Validação de isolamento multi-tenant
- [ ] Testes de performance
- [ ] Testes de segurança

### 4. Deploy e Produção
- [ ] Configurar URLs de produção
- [ ] Implementar monitoramento
- [ ] Configurar logs
- [ ] Testes de carga

## 📚 Documentação Relacionada

- [Integração Frontend-Backend](INTEGRACAO_FRONTEND_BACKEND.md) - Documentação completa
- [Mapeamento Completo](MAPEAMENTO_TABELAS_APIS_FRONTEND.md) - Tabelas ↔ APIs ↔ Frontend
- [API de Administração](api/ADMINISTRACAO_API.md) - Endpoints administrativos
- [Arquitetura Multi-Tenant](arquitetura/MULTI_TENANCY.md) - Sistema multi-tenant

---

**Status**: ✅ Guia completo  
**Última atualização**: 08/10/2025  
**Versão**: 1.0
