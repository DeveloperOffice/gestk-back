# 📊 RESUMO EXECUTIVO - CRUDs ADMIN

## ✅ SITUAÇÃO ATUAL

### Modelos Verificados (Todos existem!)
| Modelo | Localização | Status | Campos |
|--------|-------------|--------|--------|
| **ContratoGestk** | `administracao.models` | ✅ Completo | 20+ campos, status workflow |
| **Plano** | `billing.models` | ✅ Completo | Preços, ciclos, módulos, limites |
| **Assinatura** | `billing.models` | ✅ Completo | Status workflow, trial, valores |
| **Fatura** | `billing.models` | ✅ Completo | Valores, datas, boleto, status |
| **Pagamento** | `billing.models` | ✅ Completo | Métodos, transação, confirmação |
| **UsuarioAcesso** | ❌ Não existe | ⚠️ Precisa criar | - |
| **Contabilidade** | `core.models` | ✅ Existe | Adaptar views admin |

### API Atual
```
✅ /api/auth/                          # Autenticação completa
✅ /api/gestao/                        # Gestão operacional
✅ /api/dashboards/                    # Dashboards
⚠️ /api/administracao/                 # Parcialmente implementado
❌ /api/billing/                       # NÃO EXISTE (precisa criar)
```

### Infraestrutura Existente

**apps/api/administracao/** (Parcial):
- `views.py` - Tem `ContratoGestkViewSet` básico
- `serializers.py` - Tem `ContratoGestkSerializer` básico
- `filters.py` - Tem `ContratoGestkFilter` básico
- `urls.py` - Configurado

**apps/api/billing/** (Não existe):
- ❌ Precisa criar módulo completo
- ❌ Serializers
- ❌ Views
- ❌ Filters
- ❌ URLs

---

## 🎯 PLANO DE AÇÃO

### FASE 1: Fundação (4-6 horas)
**Objetivo**: Preparar base de dados e estrutura

#### 1.1 Criar Modelo UsuarioAcesso
- Vínculo usuário-contabilidade
- Controle de roles e permissões
- Vigência de acesso
- Migration

#### 1.2 Criar Módulo API Billing
- Estrutura de arquivos
- Apps config
- URLs
- Importações

**Entregável**: Base pronta para desenvolvimento

---

### FASE 2: Módulo Administração (6-8 horas)

#### 2.1 ContratoGestk (EXPANDIR)
**Endpoints necessários**:
```
POST   /api/administracao/contratos-gestk/                    # Criar
GET    /api/administracao/contratos-gestk/                    # Listar
GET    /api/administracao/contratos-gestk/{id}/               # Detalhar
PUT    /api/administracao/contratos-gestk/{id}/               # Atualizar completo
PATCH  /api/administracao/contratos-gestk/{id}/               # Atualizar parcial
DELETE /api/administracao/contratos-gestk/{id}/               # Deletar
POST   /api/administracao/contratos-gestk/{id}/suspender/     # Suspender
POST   /api/administracao/contratos-gestk/{id}/cancelar/      # Cancelar
POST   /api/administracao/contratos-gestk/{id}/ativar/        # Ativar
GET    /api/administracao/contratos-gestk/resumo/             # Resumo (dashboard)
```

**Serializers**:
- `ContratoGestkListSerializer` - Listagem (campos essenciais)
- `ContratoGestkDetailSerializer` - Detalhes (tudo expandido)
- `ContratoGestkCreateSerializer` - Criação (validações)
- `ContratoGestkUpdateSerializer` - Atualização (validações)

**Filtros**:
- `status` - Filtrar por status
- `contabilidade` - Filtrar por contabilidade
- `plano_servico` - Filtrar por plano
- `data_inicio_min`, `data_inicio_max` - Range de datas
- `search` - Busca em número_contrato, razão social

#### 2.2 UsuarioAcesso (CRIAR)
**Endpoints necessários**:
```
POST   /api/administracao/usuarios-acesso/                    # Criar
GET    /api/administracao/usuarios-acesso/                    # Listar
GET    /api/administracao/usuarios-acesso/{id}/               # Detalhar
PUT    /api/administracao/usuarios-acesso/{id}/               # Atualizar
PATCH  /api/administracao/usuarios-acesso/{id}/               # Atualizar parcial
DELETE /api/administracao/usuarios-acesso/{id}/               # Deletar
POST   /api/administracao/usuarios-acesso/{id}/ativar/        # Ativar
POST   /api/administracao/usuarios-acesso/{id}/desativar/     # Desativar
POST   /api/administracao/usuarios-acesso/{id}/estender-vigencia/  # Estender
GET    /api/administracao/usuarios-acesso/resumo/             # Resumo
```

**Filtros**:
- `usuario` - Filtrar por usuário
- `contabilidade` - Filtrar por contabilidade
- `role` - Filtrar por função
- `ativo` - Filtrar por status
- `search` - Busca em nome, email

#### 2.3 ContabilidadeAdmin (ADAPTAR)
**Endpoints necessários**:
```
GET    /api/administracao/contabilidades-admin/               # Listar
GET    /api/administracao/contabilidades-admin/{id}/          # Detalhar
POST   /api/administracao/contabilidades-admin/{id}/suspender-inadimplencia/  # Suspender
POST   /api/administracao/contabilidades-admin/{id}/reativar/ # Reativar
GET    /api/administracao/contabilidades-admin/resumo/        # Resumo
GET    /api/administracao/contabilidades-admin/{id}/historico/  # Histórico
```

---

### FASE 3: Módulo Billing (10-12 horas)

#### 3.1 Planos (2-3 horas)
**Endpoints necessários**:
```
POST   /api/billing/planos/              # Criar
GET    /api/billing/planos/              # Listar
GET    /api/billing/planos/{id}/         # Detalhar
PUT    /api/billing/planos/{id}/         # Atualizar
PATCH  /api/billing/planos/{id}/         # Atualizar parcial
DELETE /api/billing/planos/{id}/         # Deletar (soft delete)
GET    /api/billing/planos/ativos/       # Listar apenas ativos
GET    /api/billing/planos/resumo/       # Resumo
```

**Serializers**:
- `PlanoListSerializer`
- `PlanoDetailSerializer`
- `PlanoCreateSerializer`
- `PlanoUpdateSerializer`

**Filtros**:
- `ativo` - Filtrar por status
- `ciclo_cobranca` - Filtrar por ciclo
- `preco_min`, `preco_max` - Range de preços
- `search` - Busca em código, nome

#### 3.2 Assinaturas (3-4 horas)
**Endpoints necessários**:
```
POST   /api/billing/assinaturas/                # Criar
GET    /api/billing/assinaturas/                # Listar
GET    /api/billing/assinaturas/{id}/           # Detalhar
PUT    /api/billing/assinaturas/{id}/           # Atualizar
PATCH  /api/billing/assinaturas/{id}/           # Atualizar parcial
DELETE /api/billing/assinaturas/{id}/           # Deletar
POST   /api/billing/assinaturas/{id}/suspender/ # Suspender
POST   /api/billing/assinaturas/{id}/cancelar/  # Cancelar
POST   /api/billing/assinaturas/{id}/ativar/    # Ativar
GET    /api/billing/assinaturas/resumo/         # Resumo
```

**Serializers**:
- `AssinaturaListSerializer`
- `AssinaturaDetailSerializer` (com plano e contabilidade expandidos)
- `AssinaturaCreateSerializer`
- `AssinaturaUpdateSerializer`

**Filtros**:
- `status` - Filtrar por status
- `contabilidade` - Filtrar por contabilidade
- `plano` - Filtrar por plano
- `ciclo_cobranca` - Filtrar por ciclo
- `data_inicio_min`, `data_inicio_max` - Range
- `search` - Busca

#### 3.3 Faturas (2-3 horas)
**Endpoints necessários**:
```
POST   /api/billing/faturas/                     # Criar
GET    /api/billing/faturas/                     # Listar
GET    /api/billing/faturas/{id}/                # Detalhar
PUT    /api/billing/faturas/{id}/                # Atualizar
PATCH  /api/billing/faturas/{id}/                # Atualizar parcial
DELETE /api/billing/faturas/{id}/                # Deletar
POST   /api/billing/faturas/{id}/marcar-paga/    # Marcar como paga
POST   /api/billing/faturas/{id}/cancelar/       # Cancelar
GET    /api/billing/faturas/resumo/              # Resumo
```

**Serializers**:
- `FaturaListSerializer`
- `FaturaDetailSerializer`
- `FaturaCreateSerializer`

**Filtros**:
- `status` - Filtrar por status
- `assinatura` - Filtrar por assinatura
- `competencia` - Filtrar por competência
- `data_vencimento_min`, `data_vencimento_max` - Range
- `vencidas` - Apenas vencidas
- `search` - Busca em número

#### 3.4 Pagamentos (2-3 horas)
**Endpoints necessários**:
```
POST   /api/billing/pagamentos/                  # Criar
GET    /api/billing/pagamentos/                  # Listar
GET    /api/billing/pagamentos/{id}/             # Detalhar
PUT    /api/billing/pagamentos/{id}/             # Atualizar
PATCH  /api/billing/pagamentos/{id}/             # Atualizar parcial
DELETE /api/billing/pagamentos/{id}/             # Deletar
POST   /api/billing/pagamentos/{id}/confirmar/   # Confirmar
POST   /api/billing/pagamentos/{id}/estornar/    # Estornar
GET    /api/billing/pagamentos/resumo/           # Resumo
```

**Serializers**:
- `PagamentoListSerializer`
- `PagamentoDetailSerializer`
- `PagamentoCreateSerializer`

**Filtros**:
- `status` - Filtrar por status
- `fatura` - Filtrar por fatura
- `metodo` - Filtrar por método
- `data_pagamento_min`, `data_pagamento_max` - Range
- `search` - Busca em transação ID

---

### FASE 4: Testes e Documentação (4-6 horas)

#### 4.1 Testes
- Testes unitários de serializers
- Testes de integração de ViewSets
- Testes de permissões
- Testes de ações (suspender, cancelar, etc)

#### 4.2 Documentação
- Swagger/ReDoc
- Postman Collection
- README com exemplos

---

## 📊 CONTAGEM DE ENDPOINTS

### Módulo Administração
- **ContratoGestk**: 10 endpoints
- **UsuarioAcesso**: 10 endpoints
- **ContabilidadeAdmin**: 6 endpoints
- **Subtotal**: 26 endpoints

### Módulo Billing
- **Planos**: 8 endpoints
- **Assinaturas**: 10 endpoints
- **Faturas**: 9 endpoints
- **Pagamentos**: 9 endpoints
- **Subtotal**: 36 endpoints

### Total Geral
**62 endpoints** (incluindo resumos e ações)

---

## ⏱️ ESTIMATIVA DE TEMPO

| Fase | Descrição | Tempo Estimado |
|------|-----------|----------------|
| 1 | Fundação (UsuarioAcesso + Billing structure) | 4-6 horas |
| 2 | Módulo Administração (Contratos, Usuários, Contabilidades) | 6-8 horas |
| 3 | Módulo Billing (Planos, Assinaturas, Faturas, Pagamentos) | 10-12 horas |
| 4 | Testes e Documentação | 4-6 horas |
| **TOTAL** | | **24-32 horas** (3-4 dias úteis) |

---

## 🚀 PRIORIDADES

### P0 - Crítico (Fazer primeiro)
1. Criar modelo `UsuarioAcesso`
2. Criar módulo `apps/api/billing/`
3. CRUD ContratoGestk completo
4. CRUD Planos

### P1 - Alto (Fazer em seguida)
5. CRUD Assinaturas
6. CRUD Faturas
7. CRUD Pagamentos
8. CRUD UsuarioAcesso

### P2 - Médio (Fazer depois)
9. ContabilidadeAdmin
10. Resumos e dashboards
11. Filtros avançados

### P3 - Baixo (Refinar)
12. Testes completos
13. Documentação
14. Otimizações

---

## ✅ PRÓXIMOS PASSOS IMEDIATOS

1. **APROVAR ESTE PLANO**
2. **COMEÇAR FASE 1**: Criar modelo UsuarioAcesso
3. **GERAR MIGRATION**
4. **CRIAR ESTRUTURA DO MÓDULO BILLING**

Pronto para começar? 🚀
