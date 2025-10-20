# 🗺️ MAPA DA DOCUMENTAÇÃO - GESTK

**Versão**: 1.0  
**Data**: 20/10/2025  
**Objetivo**: Guia visual para navegar em toda a documentação do projeto

---

## 🎯 COMO USAR ESTE MAPA

Este documento ajuda você a encontrar rapidamente a documentação que precisa, baseado em:
- **Seu papel no projeto** (Frontend Dev, Backend Dev, QA, Gestor)
- **Sua tarefa atual** (Implementar feature, Resolver bug, Entender arquitetura)
- **Tipo de informação** (Tutorial, Referência, Conceitual)

---

## 👥 NAVEGAÇÃO POR PAPEL

### 🎨 **DESENVOLVEDOR FRONTEND**

#### Começando
1. ⭐ **[INTEGRACAO_FRONTEND_BACKEND.md](INTEGRACAO_FRONTEND_BACKEND.md)** - SEU GUIA PRINCIPAL
   - Todos os 69 endpoints documentados
   - Interfaces TypeScript completas
   - Exemplos de React Query hooks
   - Componentes UI prontos
   - Error handling
   - **Quando usar**: Sempre que for consumir a API

2. 📊 **[MAPA_ENDPOINTS_COMPLETO.md](MAPA_ENDPOINTS_COMPLETO.md)** - REFERÊNCIA RÁPIDA
   - Tabela visual de todos os endpoints
   - Operações disponíveis (CRUD + Actions)
   - **Quando usar**: Quando precisa encontrar um endpoint específico rapidamente

#### Resolução de Problemas
3. 🛠️ **[GUIA_TROUBLESHOOTING.md](GUIA_TROUBLESHOOTING.md)**
   - Erros comuns e soluções
   - Debugging de APIs
   - **Quando usar**: Quando algo não funciona

#### Implementação Avançada
4. 📝 **[TEMPLATES_CODIGO.md](TEMPLATES_CODIGO.md)**
   - Padrões de código
   - Exemplos completos
   - **Quando usar**: Quando precisa seguir padrões do projeto

---

### 💻 **DESENVOLVEDOR BACKEND**

#### Começando
1. 👨‍💻 **[desenvolvimento/README.md](desenvolvimento/README.md)** - SEU GUIA PRINCIPAL
   - Configuração do ambiente
   - Estrutura do projeto
   - Padrões de código
   - **Quando usar**: Setup inicial e referência geral

2. 📋 **[desenvolvimento/NORMALIZACAO_E_REGULAS.md](desenvolvimento/NORMALIZACAO_E_REGULAS.md)**
   - Regras rigorosas de organização
   - Normalização de dados (3NF)
   - Padrões de ETL e API
   - **Quando usar**: Antes de criar qualquer modelo ou API

#### Implementando APIs
3. 🔌 **[desenvolvimento/API_ADMINISTRACAO.md](desenvolvimento/API_ADMINISTRACAO.md)**
   - Padrões de ViewSets
   - Sistema de permissões
   - Middleware multi-tenant
   - **Quando usar**: Ao implementar novos endpoints

4. 📝 **[TEMPLATES_CODIGO.md](TEMPLATES_CODIGO.md)**
   - Templates de ViewSets
   - Templates de Serializers
   - Templates de Filters
   - **Quando usar**: Ao criar novos componentes

#### Referência Completa
5. 📊 **[RELATORIO_FINAL_CRUDS.md](RELATORIO_FINAL_CRUDS.md)**
   - Todos os CRUDs implementados
   - Padrões seguidos
   - **Quando usar**: Para ver exemplos de implementação

6. 🔍 **[AUDITORIA_COMPLETA_CRUDS.md](AUDITORIA_COMPLETA_CRUDS.md)**
   - Auditoria técnica detalhada
   - Verificações de qualidade
   - **Quando usar**: Para revisar implementações

---

### 🔄 **DESENVOLVEDOR ETL**

#### Guia Principal
1. 🔄 **[etls/README.md](etls/README.md)** - SEU GUIA PRINCIPAL
   - Lista completa de ETLs
   - Padrões de implementação
   - Fluxo de execução
   - **Quando usar**: Sempre que trabalhar com ETLs

#### Análises Técnicas
2. 📊 **ETLs Específicos**:
   - **[ANALISE_ETL_07_COMPLETA.md](ANALISE_ETL_07_COMPLETA.md)** - ETL 07 detalhado
   - **[ANALISE_ETL18_ETL19_COMPLEMENTAR.md](ANALISE_ETL18_ETL19_COMPLEMENTAR.md)** - ETL 18 e 19
   - **[ETL19_DADOS_POR_EMPRESA_CNPJ.md](ETL19_DADOS_POR_EMPRESA_CNPJ.md)** - Dados por empresa
   - **[CORRECOES_ETL18_APLICADAS.md](CORRECOES_ETL18_APLICADAS.md)** - Correções aplicadas
   - **[RELATORIO_OTIMIZACAO_ETL19.md](RELATORIO_OTIMIZACAO_ETL19.md)** - Otimizações
   - **Quando usar**: Quando trabalhar com ETL específico

#### Problemas
3. 🛠️ **[GUIA_TROUBLESHOOTING.md](GUIA_TROUBLESHOOTING.md)**
   - Debugging de ETLs
   - Erros comuns
   - **Quando usar**: Quando ETL falhar

---

### 🏗️ **ARQUITETO / TECH LEAD**

#### Arquitetura
1. 🏗️ **[arquitetura/README.md](arquitetura/README.md)** - ARQUITETURA COMPLETA
   - Visão geral do sistema
   - Princípios arquiteturais
   - Padrões de design
   - Escalabilidade
   - **Quando usar**: Para entender ou definir arquitetura

2. 🔒 **[arquitetura/MULTI_TENANCY.md](arquitetura/MULTI_TENANCY.md)**
   - Sistema multi-tenant
   - Isolamento de dados
   - Middleware
   - **Quando usar**: Para entender isolamento de dados

#### Status e Métricas
3. 📊 **[STATUS_CONSOLIDADO_PROJETO.md](STATUS_CONSOLIDADO_PROJETO.md)**
   - Status atual consolidado
   - Métricas detalhadas
   - Módulos implementados
   - **Quando usar**: Para reuniões, relatórios, planejamento

4. 📊 **[RESUMO_EXECUTIVO.md](RESUMO_EXECUTIVO.md)**
   - Visão executiva
   - Conquistas
   - Próximos passos
   - **Quando usar**: Para apresentações executivas

---

### 🧪 **QA / TESTER**

#### Testando APIs
1. ⭐ **[INTEGRACAO_FRONTEND_BACKEND.md](INTEGRACAO_FRONTEND_BACKEND.md)**
   - Todos os endpoints com exemplos
   - Request/Response esperados
   - Status codes
   - **Quando usar**: Para criar casos de teste

2. 📊 **[MAPA_ENDPOINTS_COMPLETO.md](MAPA_ENDPOINTS_COMPLETO.md)**
   - Lista completa de endpoints
   - Operações disponíveis
   - **Quando usar**: Para checklist de cobertura

#### Problemas
3. 🛠️ **[GUIA_TROUBLESHOOTING.md](GUIA_TROUBLESHOOTING.md)**
   - Erros conhecidos
   - Comportamentos esperados
   - **Quando usar**: Para validar bugs reportados

---

### 📊 **GESTOR / PRODUCT OWNER**

#### Status do Projeto
1. 📊 **[STATUS_CONSOLIDADO_PROJETO.md](STATUS_CONSOLIDADO_PROJETO.md)**
   - Status geral do projeto
   - Métricas atuais
   - Progresso por módulo
   - **Quando usar**: Reuniões de status, relatórios

2. 📊 **[RESUMO_EXECUTIVO.md](RESUMO_EXECUTIVO.md)**
   - Resumo executivo
   - Conquistas principais
   - **Quando usar**: Apresentações para stakeholders

#### Planejamento
3. 📋 **[INDICE_GERAL.md](INDICE_GERAL.md)**
   - Índice completo da documentação
   - Organização por categoria
   - **Quando usar**: Para navegar toda a documentação

---

## 🎯 NAVEGAÇÃO POR TAREFA

### "Preciso consumir uma API"
1. ⭐ **[INTEGRACAO_FRONTEND_BACKEND.md](INTEGRACAO_FRONTEND_BACKEND.md)** - Encontre o endpoint
2. 📊 **[MAPA_ENDPOINTS_COMPLETO.md](MAPA_ENDPOINTS_COMPLETO.md)** - Referência rápida
3. 🛠️ **[GUIA_TROUBLESHOOTING.md](GUIA_TROUBLESHOOTING.md)** - Se houver problemas

### "Preciso implementar uma nova API"
1. 📋 **[desenvolvimento/NORMALIZACAO_E_REGULAS.md](desenvolvimento/NORMALIZACAO_E_REGULAS.md)** - Regras
2. 🔌 **[desenvolvimento/API_ADMINISTRACAO.md](desenvolvimento/API_ADMINISTRACAO.md)** - Padrões
3. 📝 **[TEMPLATES_CODIGO.md](TEMPLATES_CODIGO.md)** - Templates
4. 🔍 **[AUDITORIA_COMPLETA_CRUDS.md](AUDITORIA_COMPLETA_CRUDS.md)** - Exemplos

### "Preciso trabalhar com ETL"
1. 🔄 **[etls/README.md](etls/README.md)** - Guia geral
2. 📊 **Análises específicas** - Documentos de análise do ETL específico
3. 🛠️ **[GUIA_TROUBLESHOOTING.md](GUIA_TROUBLESHOOTING.md)** - Problemas

### "Preciso entender a arquitetura"
1. 🏗️ **[arquitetura/README.md](arquitetura/README.md)** - Visão geral
2. 🔒 **[arquitetura/MULTI_TENANCY.md](arquitetura/MULTI_TENANCY.md)** - Multi-tenancy
3. 📊 **[STATUS_CONSOLIDADO_PROJETO.md](STATUS_CONSOLIDADO_PROJETO.md)** - Estado atual

### "Preciso resolver um problema"
1. 🛠️ **[GUIA_TROUBLESHOOTING.md](GUIA_TROUBLESHOOTING.md)** - PRIMEIRO LUGAR
2. ⭐ **[INTEGRACAO_FRONTEND_BACKEND.md](INTEGRACAO_FRONTEND_BACKEND.md)** - Se for API
3. 🔄 **[etls/README.md](etls/README.md)** - Se for ETL

### "Preciso fazer onboarding"
**DIA 1**:
1. 📖 **[README.md](README.md)** - Visão geral
2. 🗺️ **Este documento** - Navegação
3. 📊 **[STATUS_CONSOLIDADO_PROJETO.md](STATUS_CONSOLIDADO_PROJETO.md)** - Estado atual

**DIA 2** (Frontend):
4. ⭐ **[INTEGRACAO_FRONTEND_BACKEND.md](INTEGRACAO_FRONTEND_BACKEND.md)** - Endpoints
5. 📝 **[TEMPLATES_CODIGO.md](TEMPLATES_CODIGO.md)** - Padrões

**DIA 2** (Backend):
4. 👨‍💻 **[desenvolvimento/README.md](desenvolvimento/README.md)** - Setup
5. 📋 **[desenvolvimento/NORMALIZACAO_E_REGULAS.md](desenvolvimento/NORMALIZACAO_E_REGULAS.md)** - Regras

---

## 📚 TIPOS DE DOCUMENTAÇÃO

### 📖 **Tutoriais** (Como fazer)
- **[desenvolvimento/README.md](desenvolvimento/README.md)** - Setup do ambiente
- **[desenvolvimento/API_ADMINISTRACAO.md](desenvolvimento/API_ADMINISTRACAO.md)** - Implementar APIs
- **[etls/README.md](etls/README.md)** - Trabalhar com ETLs

### 📋 **Referência** (Consulta rápida)
- ⭐ **[INTEGRACAO_FRONTEND_BACKEND.md](INTEGRACAO_FRONTEND_BACKEND.md)** - Todos os endpoints
- 📊 **[MAPA_ENDPOINTS_COMPLETO.md](MAPA_ENDPOINTS_COMPLETO.md)** - Tabela visual
- 📝 **[TEMPLATES_CODIGO.md](TEMPLATES_CODIGO.md)** - Templates de código

### 🧠 **Conceitual** (Entender o sistema)
- 🏗️ **[arquitetura/README.md](arquitetura/README.md)** - Arquitetura geral
- 🔒 **[arquitetura/MULTI_TENANCY.md](arquitetura/MULTI_TENANCY.md)** - Multi-tenancy
- 📋 **[desenvolvimento/NORMALIZACAO_E_REGULAS.md](desenvolvimento/NORMALIZACAO_E_REGULAS.md)** - Princípios

### 🛠️ **Troubleshooting** (Resolver problemas)
- 🛠️ **[GUIA_TROUBLESHOOTING.md](GUIA_TROUBLESHOOTING.md)** - Guia de problemas
- 📊 **Análises de ETL** - Problemas específicos de ETLs

### 📊 **Status e Relatórios** (Acompanhamento)
- 📊 **[STATUS_CONSOLIDADO_PROJETO.md](STATUS_CONSOLIDADO_PROJETO.md)** - Status detalhado
- 📊 **[RESUMO_EXECUTIVO.md](RESUMO_EXECUTIVO.md)** - Resumo executivo
- 📊 **[RELATORIO_FINAL_CRUDS.md](RELATORIO_FINAL_CRUDS.md)** - Relatório de CRUDs

### 📝 **Histórico** (Contexto e decisões)
- 📝 **[DESCOBERTA_SISTEMA_IMPLEMENTADO.md](DESCOBERTA_SISTEMA_IMPLEMENTADO.md)** - Descoberta
- 📝 **[ATUALIZACAO_DOC_INTEGRACAO.md](ATUALIZACAO_DOC_INTEGRACAO.md)** - Atualização
- 📝 **[AUDITORIA_COMPLETA_CRUDS.md](AUDITORIA_COMPLETA_CRUDS.md)** - Auditoria

---

## 🔥 TOP 10 DOCUMENTOS MAIS USADOS

| # | Documento | Uso | Quando Usar |
|---|-----------|-----|-------------|
| 1 | ⭐ **INTEGRACAO_FRONTEND_BACKEND.md** | 🔥🔥🔥🔥🔥 | Consumir/Documentar APIs |
| 2 | 🛠️ **GUIA_TROUBLESHOOTING.md** | 🔥🔥🔥🔥 | Resolver problemas |
| 3 | 📊 **MAPA_ENDPOINTS_COMPLETO.md** | 🔥🔥🔥🔥 | Referência rápida |
| 4 | 📋 **desenvolvimento/NORMALIZACAO_E_REGULAS.md** | 🔥🔥🔥 | Implementar código |
| 5 | 👨‍💻 **desenvolvimento/README.md** | 🔥🔥🔥 | Setup e padrões |
| 6 | 📝 **TEMPLATES_CODIGO.md** | 🔥🔥🔥 | Seguir padrões |
| 7 | 🔄 **etls/README.md** | 🔥🔥 | Trabalhar com ETLs |
| 8 | 🏗️ **arquitetura/README.md** | 🔥🔥 | Entender arquitetura |
| 9 | 📊 **STATUS_CONSOLIDADO_PROJETO.md** | 🔥🔥 | Status e métricas |
| 10 | 🔌 **desenvolvimento/API_ADMINISTRACAO.md** | 🔥 | Implementar APIs |

---

## 📊 ESTRUTURA VISUAL

```
📚 GESTK DOCUMENTATION
│
├── 🎯 INÍCIO RÁPIDO
│   ├── ⭐ INTEGRACAO_FRONTEND_BACKEND.md ← PRINCIPAL
│   ├── 📊 MAPA_ENDPOINTS_COMPLETO.md
│   ├── 🗺️ MAPA_DOCUMENTACAO.md (este arquivo)
│   └── 📖 README.md
│
├── 📊 STATUS E RESUMOS
│   ├── STATUS_CONSOLIDADO_PROJETO.md
│   ├── RESUMO_EXECUTIVO.md
│   └── INDICE_GERAL.md
│
├── 🔌 API E INTEGRACAO
│   ├── INTEGRACAO_FRONTEND_BACKEND.md (2109 linhas)
│   ├── MAPA_ENDPOINTS_COMPLETO.md
│   ├── RELATORIO_FINAL_CRUDS.md
│   ├── AUDITORIA_COMPLETA_CRUDS.md
│   └── RESUMO_CRUDS_ADMIN.md
│
├── 🏗️ ARQUITETURA
│   ├── arquitetura/README.md
│   └── arquitetura/MULTI_TENANCY.md
│
├── 👨‍💻 DESENVOLVIMENTO
│   ├── desenvolvimento/README.md
│   ├── desenvolvimento/API_ADMINISTRACAO.md
│   ├── desenvolvimento/NORMALIZACAO_E_REGULAS.md
│   ├── TEMPLATES_CODIGO.md
│   └── GUIA_TROUBLESHOOTING.md
│
├── 🔄 ETLs
│   ├── etls/README.md
│   └── [análises específicas]
│
└── 📚 HISTÓRICO
    └── [documentos históricos]
```

---

## 🎓 FLUXOS DE APRENDIZADO

### Frontend Developer (3-5 dias)
```
DIA 1: Fundamentos
├── README.md (30 min)
├── MAPA_DOCUMENTACAO.md (30 min)
└── STATUS_CONSOLIDADO_PROJETO.md (30 min)

DIA 2-3: APIs
├── INTEGRACAO_FRONTEND_BACKEND.md (4-6 horas)
├── MAPA_ENDPOINTS_COMPLETO.md (1 hora)
└── Implementar primeiro endpoint (2-3 horas)

DIA 4-5: Prática
├── TEMPLATES_CODIGO.md (2 horas)
├── Implementar features (4-6 horas)
└── GUIA_TROUBLESHOOTING.md (quando necessário)
```

### Backend Developer (3-5 dias)
```
DIA 1: Fundamentos
├── README.md (30 min)
├── desenvolvimento/README.md (2 horas)
├── arquitetura/README.md (2 horas)
└── arquitetura/MULTI_TENANCY.md (1 hora)

DIA 2: Regras e Padrões
├── desenvolvimento/NORMALIZACAO_E_REGULAS.md (3 horas)
├── desenvolvimento/API_ADMINISTRACAO.md (2 horas)
└── TEMPLATES_CODIGO.md (2 horas)

DIA 3-5: Implementação
├── RELATORIO_FINAL_CRUDS.md (exemplos) (2 horas)
├── Implementar features (6-8 horas)
└── GUIA_TROUBLESHOOTING.md (quando necessário)
```

---

## 💡 DICAS DE USO

### ✅ FAÇA
- ✅ Use CTRL+F para buscar palavras-chave
- ✅ Consulte este mapa quando estiver perdido
- ✅ Comece sempre pelo documento ⭐ do seu papel
- ✅ Use troubleshooting ANTES de perguntar

### ❌ NÃO FAÇA
- ❌ Não leia toda a documentação de uma vez
- ❌ Não ignore os padrões em NORMALIZACAO_E_REGULAS.md
- ❌ Não implemente sem consultar TEMPLATES_CODIGO.md
- ❌ Não copie código sem entender

---

## 🔄 ESTE DOCUMENTO

**Atualização**: Este mapa é atualizado sempre que:
- Novos documentos são adicionados
- Estrutura da documentação muda
- Novos fluxos de trabalho são estabelecidos

**Contribuindo**: Se você notar que:
- Um link está quebrado
- Um documento importante não está listado
- Um fluxo de trabalho está desatualizado
- Por favor, atualize este mapa!

---

**Criado em**: 20/10/2025  
**Última atualização**: 20/10/2025  
**Mantenedor**: Tech Lead  
**Status**: ✅ COMPLETO

---

## 🎯 PRÓXIMOS PASSOS

**Agora que você conhece o mapa**:
1. Identifique seu papel
2. Encontre seu documento ⭐ principal
3. Comece a trabalhar!
4. Consulte este mapa sempre que necessário

**Boa documentação leva a bom código! 🚀**
