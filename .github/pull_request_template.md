## 📋 Descrição

<!-- Descreva brevemente o que foi implementado/corrigido neste PR -->

## 🎯 Tipo de Mudança

Marque o tipo da mudança:

- [ ] 🚀 Nova funcionalidade (feature)
- [ ] 🐛 Correção de bug (fix)
- [ ] ♻️ Refatoração (refactor)
- [ ] 📝 Documentação (docs)
- [ ] 🧪 Testes (test)
- [ ] 🎨 Estilo/Formatação (style)
- [ ] ⚡ Performance (perf)
- [ ] 🔧 Manutenção (chore)

## 📊 Endpoints Afetados

Liste os endpoints criados/modificados:

- `GET /api/...` - Descrição
- `POST /api/...` - Descrição

## 🧪 Como Testar

Descreva os passos para testar as mudanças:

1. Reinicie o servidor: `python manage.py runserver`
2. Obtenha token JWT:
   ```bash
   curl -X POST http://localhost:8000/api/auth/login/ \
     -H "Content-Type: application/json" \
     -d '{"username": "testuser", "password": "senha123"}'
   ```
3. Teste o endpoint:
   ```bash
   GET http://localhost:8000/api/...
   Authorization: Bearer {seu_token}
   ```
4. **Resultado esperado:** ...

## ✅ Checklist

Antes de solicitar review, verifique:

### Código
- [ ] Código segue os padrões do projeto (PEP 8)
- [ ] Código está limpo e legível
- [ ] Nomes de variáveis/funções são descritivos
- [ ] Sem código comentado ou debug prints
- [ ] Sem código duplicado

### Funcionalidade
- [ ] **Lógica de superuser implementada** (quando aplicável)
- [ ] Tratamento de erros adequado
- [ ] Validação de entrada implementada
- [ ] Permissões configuradas corretamente

### Logging & Debug
- [ ] **Logs informativos adicionados** (`logger.info`, `logger.error`)
- [ ] Logs usam prefixo apropriado (ex: `[CARTEIRA]`, `[DASHBOARD]`)
- [ ] Mensagens de erro são claras

### Performance
- [ ] Queries otimizadas (uso de `select_related`, `prefetch_related`)
- [ ] Sem N+1 queries
- [ ] Paginação implementada (quando necessário)

### Testes
- [ ] Testado localmente com **usuário normal**
- [ ] Testado localmente com **superuser**
- [ ] Testado com diferentes cenários (dados vazios, muitos dados, etc.)
- [ ] Testes automatizados criados (opcional, mas recomendado)

### Database
- [ ] Migrations criadas (se houver mudança em models)
- [ ] Migrations testadas (`makemigrations` + `migrate`)

### Documentação
- [ ] Docstrings adicionadas/atualizadas
- [ ] Documentação da API atualizada (se necessário)
- [ ] README atualizado (se necessário)

### Segurança
- [ ] Sem credenciais hardcoded
- [ ] Sem dados sensíveis nos logs
- [ ] Permissões verificadas

## 📸 Screenshots (opcional)

<!-- Cole prints do Postman, Insomnia ou da aplicação mostrando a funcionalidade -->

<details>
<summary>Ver screenshots</summary>

![Screenshot 1](url-da-imagem)

</details>

## 🔗 Issues Relacionadas

<!-- Link para issues do GitHub -->

- Closes #123
- Relates to #456

## 📝 Notas Adicionais

<!-- Informações extras para os revisores -->

<!-- Exemplos:
- Esta mudança requer atualização no frontend
- Esta mudança altera comportamento existente
- Esta mudança requer migration
- Performance melhorada em X%
-->

## 👀 Reviewers

<!-- Marque desenvolvedores específicos se necessário -->

<!-- @wando @dev1 @dev2 -->

---

**Obrigado por contribuir! 🚀**
