# 🚀 GUIA DE TESTE NO POSTMAN

## ⚠️ IMPORTANTE: Servidor Precisa Estar Rodando

Antes de testar, certifique-se que o servidor Django está rodando:

```bash
python manage.py runserver
```

---

## 📋 TOKENS PRONTOS PARA TESTE

### 🔑 SUPERUSER: wando
```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzYxMDc3MjM2LCJpYXQiOjE3NjEwNDg0MzYsImp0aSI6IjIwMTkzNDY4MTc5ZDQxODA4ZGM3YzUwNjlhZTRkM2RlIiwidXNlcl9pZCI6ImFkMDkyY2Q1LWZiMjMtNDkxNi05YTg3LWEwMTNmMDY2MGU1NiJ9.Dl3Blp6_zXBP7UPFmxmGgN8mh6dUVb2HN06dBuFVxS4
```
**Resultado Esperado**: 2186 contratos (todos do BD)

### 👤 USUÁRIO: teste_silpa
```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzYxMDc3MjM2LCJpYXQiOjE3NjEwNDg0MzYsImp0aSI6IjRlNWY0MjlmMjk5YTRiNDk5MWU3NTRiYzhlODYzYTlkIiwidXNlcl9pZCI6IjI4MTk1Nzk3LWZkMGQtNGE5MC05NDI4LTI0OWM2N2E1MmY5ZSJ9.rud_lgkrvaffMK4pW31xLakPvE-bZF_6NDmcX5kpdE4
```
**Resultado Esperado**: 906 contratos (SILPA TREINAMENTOS)

### 👤 USUÁRIO: testuser
```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzYxMDc3MjM2LCJpYXQiOjE3NjEwNDg0MzYsImp0aSI6IjVmNjc0ODFlOWZjYjRkZWRhNWU4MjgxNjFiZTc5OGJiIiwidXNlcl9pZCI6IjdmYzY5Y2JjLWU0NmItNDA0YS1hMzdlLTgyYTg4YzBmYzYxMSJ9.6ixaO7LdEjPRZjCITbIXFqx26MTtnvjpXd_alWgCO1k
```
**Resultado Esperado**: 594 contratos (ASSESSORIA CONTABIL)

---

## 🔧 PASSO A PASSO NO POSTMAN

### 1️⃣ Criar Nova Requisição
- Method: `GET`
- URL: `http://127.0.0.1:8000/api/gestao/carteira/clientes/`

### 2️⃣ Configurar Headers
Clique na aba "Headers" e adicione:

| Key | Value |
|-----|-------|
| `Authorization` | `Bearer SEU_TOKEN_AQUI` |
| `Content-Type` | `application/json` |

**⚠️ ATENÇÃO**: 
- Coloque um **espaço** entre "Bearer" e o token
- Use o token completo (sem quebras de linha)

### 3️⃣ Exemplo de Header Correto
```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzYxMDc3MjM2LCJpYXQiOjE3NjEwNDg0MzYsImp0aSI6IjIwMTkzNDY4MTc5ZDQxODA4ZGM3YzUwNjlhZTRkM2RlIiwidXNlcl9pZCI6ImFkMDkyY2Q1LWZiMjMtNDkxNi05YTg3LWEwMTNmMDY2MGU1NiJ9.Dl3Blp6_zXBP7UPFmxmGgN8mh6dUVb2HN06dBuFVxS4
```

### 4️⃣ Enviar Requisição
Clique no botão "Send"

---

## ✅ RESPOSTAS ESPERADAS

### Para Superuser (wando):
```json
{
    "summary": {
        "total_clientes": 2186,
        "clientes_ativos": 1550,
        "clientes_inativos": 636,
        "clientes_novos": 0,
        "clientes_sem_movimentacao": 0,
        "percentual_ativo": 70.91
    },
    "results": []
}
```

### Para teste_silpa:
```json
{
    "summary": {
        "total_clientes": 906,
        "clientes_ativos": 573,
        "clientes_inativos": 333,
        "clientes_novos": 0,
        "clientes_sem_movimentacao": 0,
        "percentual_ativo": 63.25
    },
    "results": []
}
```

### Para testuser:
```json
{
    "summary": {
        "total_clientes": 594,
        "clientes_ativos": 387,
        "clientes_inativos": 207,
        "clientes_novos": 0,
        "clientes_sem_movimentacao": 0,
        "percentual_ativo": 65.15
    },
    "results": []
}
```

---

## 🔍 SE AINDA RETORNAR ZEROS

### 1. Verifique o Console do Django
Procure por logs como:
```
[CARTEIRA] Requisição recebida de usuário: wando
[CARTEIRA] ✅ Superuser 'wando' acessando TODOS os contratos do banco de dados
[CARTEIRA] 📊 Total de contratos encontrados: 2186
```

### 2. Erros Comuns

#### ❌ Erro: Token Expirado
```json
{
    "detail": "Given token not valid for any token type",
    "code": "token_not_valid",
    "messages": [
        {
            "token_class": "AccessToken",
            "token_type": "access",
            "message": "Token is expired"
        }
    ]
}
```
**Solução**: Gere um novo token fazendo login novamente

#### ❌ Erro: Token Inválido
```json
{
    "detail": "Authentication credentials were not provided."
}
```
**Solução**: 
- Verifique se o header está correto: `Authorization: Bearer TOKEN`
- Certifique-se que há um espaço entre "Bearer" e o token
- Verifique se não há quebras de linha no token

#### ❌ Erro: Usuário sem Contabilidade
```json
{
    "error": "Usuário não possui contabilidade associada"
}
```
**Solução**: Use um superuser (wando/admin) ou um usuário com contabilidade (teste_silpa/testuser)

### 3. Gerar Novo Token

Se o token expirou, faça login novamente:

```bash
POST http://127.0.0.1:8000/api/auth/token/
Content-Type: application/json

{
    "username": "wando",
    "password": "SUA_SENHA_AQUI"
}
```

---

## 📊 VERIFICAR LOGS EM TEMPO REAL

Execute o servidor com logs visíveis:
```bash
python manage.py runserver
```

Quando fizer a requisição no Postman, você verá no console:
```
[21/Oct/2025 10:30:45] "GET /api/gestao/carteira/clientes/ HTTP/1.1" 200 XXX
[CARTEIRA] Requisição recebida de usuário: wando
[CARTEIRA] ✅ Superuser 'wando' acessando TODOS os contratos do banco de dados
[CARTEIRA] 📊 Total de contratos encontrados: 2186
[CARTEIRA] 📈 Cálculos: Total=2186, Ativos=1550, Inativos=636, Novos=0
[CARTEIRA] ✅ Resposta montada com sucesso: {'total_clientes': 2186, ...}
```

---

## 🆘 AINDA COM PROBLEMAS?

Execute o script de debug:
```bash
python debug_api_carteira.py
```

Isso vai:
1. ✅ Gerar novos tokens
2. ✅ Verificar a lógica da API
3. ✅ Mostrar os dados esperados
4. ✅ Fornecer instruções detalhadas

---

## 📝 CHECKLIST

Antes de testar, verifique:

- [ ] Servidor Django está rodando (`python manage.py runserver`)
- [ ] URL está correta: `http://127.0.0.1:8000/api/gestao/carteira/clientes/`
- [ ] Method é `GET`
- [ ] Header `Authorization` está configurado
- [ ] Token começa com `Bearer ` (com espaço)
- [ ] Token não tem quebras de linha
- [ ] Token não está expirado

Se todos os itens estão ✅, a API deve funcionar!
