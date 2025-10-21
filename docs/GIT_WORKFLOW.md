# 🌳 Git Workflow - GESTK Backend

Este documento descreve o fluxo de trabalho Git para o time de desenvolvimento do backend GESTK.

---

## 📋 Índice

1. [Estrutura de Branches](#estrutura-de-branches)
2. [Criando uma Nova Feature](#criando-uma-nova-feature)
3. [Fazendo Commits](#fazendo-commits)
4. [Atualizando sua Branch](#atualizando-sua-branch)
5. [Criando Pull Request](#criando-pull-request)
6. [Code Review](#code-review)
7. [Merge e Finalização](#merge-e-finalização)
8. [Comandos Úteis](#comandos-úteis)

---

## 🌳 Estrutura de Branches

```
main (produção)
  └── Development (branch principal de desenvolvimento)
        ├── feature/dashboard-demografico
        ├── feature/dashboard-fiscal
        ├── feature/endpoints-carteira
        └── hotfix/bug-critico
```

### **Tipos de Branches:**

| Tipo | Prefixo | Exemplo | Quando Usar |
|------|---------|---------|-------------|
| Feature | `feature/` | `feature/dashboard-demografico` | Nova funcionalidade |
| Bugfix | `bugfix/` | `bugfix/corrige-autenticacao` | Correção de bug |
| Hotfix | `hotfix/` | `hotfix/erro-critico-producao` | Correção urgente |
| Refactor | `refactor/` | `refactor/otimiza-queries` | Refatoração |

---

## 🚀 Criando uma Nova Feature

### **Passo 1: Atualizar Development**
```bash
git checkout Development
git pull origin Development
```

### **Passo 2: Criar Branch de Feature**
```bash
# Padrão: feature/[modulo]-[funcionalidade]
git checkout -b feature/dashboard-demografico

# Outros exemplos:
git checkout -b feature/carteira-resumo-endpoint
git checkout -b feature/dashboard-fiscal-kpis
git checkout -b bugfix/401-erro-autenticacao
```

### **Passo 3: Verificar Branch Atual**
```bash
git branch
# * feature/dashboard-demografico
#   Development
```

---

## 💾 Fazendo Commits

### **Convenção de Commits (Conventional Commits)**

Use prefixos padronizados:

```bash
feat:      Nova funcionalidade
fix:       Correção de bug
refactor:  Refatoração de código
docs:      Alteração em documentação
test:      Adição/modificação de testes
style:     Formatação de código (sem mudança de lógica)
perf:      Melhoria de performance
chore:     Tarefas de manutenção
```

### **Exemplos Práticos:**

```bash
# Nova funcionalidade
git commit -m "feat(dashboard): Adiciona endpoint de KPIs demográficos"
git commit -m "feat(carteira): Implementa filtro por regime tributário"

# Correção de bug
git commit -m "fix(auth): Corrige validação de token JWT expirado"
git commit -m "fix(carteira): Resolve filtro de clientes ativos"

# Refatoração
git commit -m "refactor(views): Extrai lógica de superuser para mixin"
git commit -m "refactor(models): Otimiza queries de contratos"

# Documentação
git commit -m "docs(api): Atualiza documentação de endpoints de carteira"
git commit -m "docs(readme): Adiciona instruções de setup do projeto"

# Testes
git commit -m "test(carteira): Adiciona testes para endpoint de resumo"
```

### **Processo de Commit:**

```bash
# 1. Ver arquivos modificados
git status

# 2. Adicionar arquivos específicos
git add apps/api/dashboards/views.py
git add apps/api/dashboards/serializers.py

# Ou adicionar todos
git add .

# 3. Fazer commit
git commit -m "feat(dashboard): Implementa endpoint de turnover mensal"

# 4. Push para branch remota
git push origin feature/dashboard-demografico

# Primeira vez? Use -u para configurar tracking
git push -u origin feature/dashboard-demografico
```

---

## 🔄 Atualizando sua Branch

**IMPORTANTE:** Mantenha sua branch sempre atualizada com `Development` para evitar conflitos grandes!

### **Método 1: Merge (Recomendado para iniciantes)**

```bash
# 1. Commit suas mudanças atuais
git add .
git commit -m "feat: trabalho em progresso"

# 2. Ir para Development e atualizar
git checkout Development
git pull origin Development

# 3. Voltar para sua branch
git checkout feature/dashboard-demografico

# 4. Merge Development na sua branch
git merge Development

# 5. Se houver conflitos, resolva e commit
# Edite os arquivos com conflito
git add .
git commit -m "merge: Resolve conflitos com Development"

# 6. Push das mudanças
git push origin feature/dashboard-demografico
```

### **Método 2: Rebase (Avançado - histórico mais limpo)**

```bash
git fetch origin
git rebase origin/Development

# Se houver conflitos:
# 1. Resolva os conflitos nos arquivos
# 2. git add .
# 3. git rebase --continue

# Forçar push (cuidado!)
git push --force-with-lease origin feature/dashboard-demografico
```

---

## 📤 Criando Pull Request

### **No GitHub/GitLab:**

1. **Push da branch:**
```bash
git push origin feature/dashboard-demografico
```

2. **No navegador:**
   - Acesse o repositório no GitHub
   - Clique em "Compare & pull request"
   - Preencha o template do PR (veja abaixo)
   - Adicione reviewers (outros devs)
   - Adicione labels (feature, bug, urgent, etc.)

### **Template de PR:**

```markdown
## 📋 Descrição
Implementa endpoints de KPIs do dashboard demográfico, incluindo:
- Total de funcionários
- Taxa de turnover
- Distribuição por gênero
- Distribuição por faixa etária

## 🎯 Tipo de Mudança
- [x] Nova funcionalidade (feature)
- [ ] Correção de bug (fix)
- [ ] Refatoração (refactor)

## 🧪 Como Testar
1. Reinicie o servidor: `python manage.py runserver`
2. Obtenha token JWT:
   ```bash
   curl -X POST http://localhost:8000/api/auth/login/ \
     -d '{"username": "wando", "password": "senha123"}'
   ```
3. Teste endpoint:
   ```bash
   GET http://localhost:8000/api/dashboards/demografico/kpis/
   Authorization: Bearer {token}
   ```
4. Resultado esperado: JSON com total_funcionarios, turnover_rate, etc.

## 📊 Endpoints Afetados
- `GET /api/dashboards/demografico/kpis/` (NOVO)
- `GET /api/dashboards/demografico/turnover/` (NOVO)

## ✅ Checklist
- [x] Código segue os padrões do projeto
- [x] Testado localmente com usuário normal e superuser
- [x] Lógica de superuser implementada
- [x] Logs adicionados para debug
- [x] Documentação atualizada (se necessário)
- [ ] Migrations criadas (não foi necessário)

## 📸 Screenshots
![Postman Test](link-para-screenshot.png)

## 🔗 Issue Relacionada
Closes #15
```

---

## 👀 Code Review

### **Para o Revisor:**

Checklist de revisão:

- [ ] **Código limpo e legível**
- [ ] **Segue padrões do projeto**
- [ ] **Lógica de superuser implementada** (quando aplicável)
- [ ] **Sem código comentado ou debug prints**
- [ ] **Tratamento de erros adequado**
- [ ] **Logs informativos adicionados**
- [ ] **Performance aceitável** (queries otimizadas)
- [ ] **Testes manuais realizados**
- [ ] **Documentação atualizada**

### **Comentando no PR:**

```markdown
# Aprovar
LGTM! 🚀 (Looks Good To Me)
Código está limpo e funcional.

# Sugerir mudanças
💡 Sugestão: Considere extrair essa lógica para um método separado
para melhorar a legibilidade.

# Solicitar mudanças
⚠️ Problema: A query na linha 45 pode causar N+1. 
Sugestão: Use select_related() ou prefetch_related()
```

---

## ✅ Merge e Finalização

### **Após Aprovação do PR:**

1. **Merge via interface do GitHub** (recomendado)
   - Clique em "Merge pull request"
   - Escolha tipo: "Squash and merge" ou "Merge commit"
   - Confirme

2. **Limpeza local:**
```bash
# Voltar para Development
git checkout Development

# Atualizar com as mudanças merged
git pull origin Development

# Deletar branch local
git branch -d feature/dashboard-demografico

# Deletar branch remota
git push origin --delete feature/dashboard-demografico
```

---

## 🛠️ Comandos Úteis

### **Atalhos Rápidos:**

```bash
# Criar feature a partir de Development (tudo em um comando)
git checkout Development && git pull && git checkout -b feature/minha-feature

# Commit rápido de tudo
git add . && git commit -m "feat: descrição"

# Push e criar upstream tracking
git push -u origin HEAD

# Atualizar com Development (método rápido)
git fetch origin && git merge origin/Development

# Ver todas as branches (local e remota)
git branch -a

# Ver status detalhado
git status -sb

# Ver log resumido
git log --oneline --graph --all -10
```

### **Resolução de Problemas:**

```bash
# Desfazer último commit (mantém alterações)
git reset --soft HEAD~1

# Descartar todas as mudanças locais (CUIDADO!)
git reset --hard HEAD

# Ver diferenças antes de commit
git diff

# Ver diferenças staged
git diff --staged

# Recuperar arquivo específico do último commit
git checkout HEAD -- arquivo.py

# Ver quem modificou cada linha de um arquivo
git blame arquivo.py

# Ver branches já merged
git branch --merged

# Ver branches não merged
git branch --no-merged
```

### **Stash (Guardar mudanças temporariamente):**

```bash
# Guardar mudanças não commitadas
git stash

# Guardar com mensagem descritiva
git stash save "WIP: implementando filtro de data"

# Listar stashes
git stash list

# Recuperar último stash
git stash pop

# Recuperar stash específico
git stash apply stash@{0}

# Deletar stash
git stash drop stash@{0}
```

---

## 🚨 Situações Especiais

### **Esqueci de criar branch e commitei na Development:**

```bash
# 1. Criar branch com as mudanças atuais
git checkout -b feature/minha-feature

# 2. Voltar Development para estado anterior
git checkout Development
git reset --hard origin/Development

# 3. Continuar trabalhando na feature
git checkout feature/minha-feature
```

### **Preciso fazer hotfix urgente:**

```bash
# 1. Criar hotfix a partir de main
git checkout main
git pull origin main
git checkout -b hotfix/corrige-erro-critico

# 2. Fazer correção e commit
git add .
git commit -m "hotfix: Corrige erro crítico de autenticação"

# 3. Push e criar PR para main
git push -u origin hotfix/corrige-erro-critico

# 4. Após merge em main, também merge em Development
git checkout Development
git pull origin Development
git merge main
git push origin Development
```

### **Conflitos de Merge:**

```bash
# Ao fazer merge e aparecer conflito:

# 1. Ver arquivos com conflito
git status

# 2. Abrir arquivo e procurar por:
<<<<<<< HEAD
código da sua branch
=======
código da Development
>>>>>>> Development

# 3. Escolher qual código manter (ou combinar)
# 4. Remover marcadores de conflito
# 5. Salvar arquivo

# 6. Marcar conflito como resolvido
git add arquivo_com_conflito.py

# 7. Continuar merge
git commit -m "merge: Resolve conflitos com Development"
```

---

## 📚 Recursos Adicionais

- [Git Official Documentation](https://git-scm.com/doc)
- [Conventional Commits](https://www.conventionalcommits.org/)
- [GitHub Flow](https://guides.github.com/introduction/flow/)
- [Atlassian Git Tutorial](https://www.atlassian.com/git/tutorials)

---

## 🤝 Dúvidas?

- Consulte este documento primeiro
- Pergunte ao tech lead (Wando)
- Pergunte ao time no Slack/Teams
- Não tenha medo de perguntar! Melhor perguntar que fazer errado 😊

---

**Última atualização:** 21/10/2025  
**Mantenedor:** Equipe GESTK Backend
