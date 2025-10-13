# 🛠️ Guia de Troubleshooting - GESTK Backend

## 📋 Índice
1. [Problemas de Autenticação](#autenticação)
2. [Erros 403 Forbidden](#erros-403)
3. [Problemas de CORS](#cors)
4. [Middleware Multitenancy](#middleware)
5. [Problemas Comuns](#problemas-comuns)

---

## 🔐 Autenticação

### Erro: "Authentication credentials were not provided"
**Causa**: Token JWT não está sendo enviado ou está inválido.

**Solução**:
```bash
# 1. Verifique se o header está correto
Authorization: Bearer <seu_token_aqui>

# 2. Teste a autenticação
curl -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"username": "seu_usuario", "password": "sua_senha"}'

# 3. Verifique se o token não expirou
# Tokens de acesso expiram em 60 minutos
# Use o refresh token para obter novo access token
```

### Token Expirado
**Solução**:
```bash
# Renovar token com refresh
curl -X POST http://localhost:8000/api/auth/refresh/ \
  -H "Content-Type: application/json" \
  -d '{"refresh": "seu_refresh_token"}'
```

---

## ❌ Erros 403 Forbidden

### Erro: "You do not have permission to perform this action"

**Causas Comuns**:
1. Usuário sem permissões suficientes
2. Middleware bloqueando acesso
3. Tentando acessar dados de outra contabilidade

**Diagnóstico**:
```python
# Verifique o tipo de usuário
print(request.user.tipo_usuario)  # Deve ser: SUPERUSER, ADMIN, ou USER

# Verifique a contabilidade do usuário
print(request.user.contabilidade_id)

# Verifique se o middleware está ativo
print(request.contabilidade)  # Deve retornar a contabilidade do contexto
```

**Soluções por Tipo de Usuário**:

#### SUPERUSER
- ✅ Acesso total a todas as contabilidades
- ✅ Pode criar/editar/deletar qualquer recurso
- ⚠️ Verifique se `tipo_usuario == 'SUPERUSER'`

#### ADMIN
- ✅ Acesso apenas à sua contabilidade
- ✅ Pode gerenciar usuários e contratos da sua contabilidade
- ⚠️ Verifique se `contabilidade_id` está correto

#### USER
- ✅ Acesso read-only à sua contabilidade
- ❌ Não pode criar/editar/deletar recursos
- ⚠️ Use apenas endpoints GET

---

## 🌐 CORS

### Erro: "CORS policy: No 'Access-Control-Allow-Origin' header"

**Verificação da Configuração**:

```python
# Em settings.py, verifique:

# 1. INSTALLED_APPS
INSTALLED_APPS = [
    ...
    'corsheaders',  # ✅ Deve estar presente
    ...
]

# 2. MIDDLEWARE (ordem correta!)
MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',  # ✅ DEVE SER O PRIMEIRO
    'django.middleware.security.SecurityMiddleware',
    ...
]

# 3. CORS_ALLOWED_ORIGINS
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",  # ✅ Frontend React/Next.js
    "http://localhost:3001",
    "http://127.0.0.1:3000",
]

# 4. Headers customizados
CORS_ALLOW_HEADERS = [
    *default_headers,
    'x-contabilidade-id',  # ✅ Header customizado para multitenancy
    'x-app-context',
]

# 5. Permitir credenciais
CORS_ALLOW_CREDENTIALS = True  # ✅ Para cookies/sessions
```

**Teste de CORS**:
```bash
# Teste do navegador
curl -H "Origin: http://localhost:3000" \
     -H "Access-Control-Request-Method: GET" \
     -H "Access-Control-Request-Headers: Authorization" \
     -X OPTIONS http://localhost:8000/api/dashboards/demografico/indicadores/

# Resposta esperada deve incluir:
# Access-Control-Allow-Origin: http://localhost:3000
# Access-Control-Allow-Credentials: true
```

---

## 🔄 Middleware Multitenancy

### Problema: Dados de outras contabilidades aparecem

**Causa**: Middleware não está aplicando filtros corretamente.

**Verificação**:
```python
# Em apps/api/shared/middleware.py

class MultitenancyMiddleware:
    def __call__(self, request):
        if request.user.is_authenticated:
            # ✅ Deve definir request.contabilidade
            if request.user.tipo_usuario == 'SUPERUSER':
                request.contabilidade = None  # Acesso total
            else:
                request.contabilidade = request.user.contabilidade
        
        response = self.get_response(request)
        return response
```

**Teste o Middleware**:
```python
# Em qualquer view, adicione print para debug:
print(f"User: {request.user.username}")
print(f"Tipo: {request.user.tipo_usuario}")
print(f"Contabilidade: {request.contabilidade}")
```

---

## 🐛 Problemas Comuns

### 1. Queries muito lentas

**Solução**: Use select_related e prefetch_related
```python
# ❌ Ruim (N+1 queries)
funcionarios = Funcionario.objects.all()
for f in funcionarios:
    print(f.cargo.nome)  # Query para cada funcionário!

# ✅ Bom (1 query)
funcionarios = Funcionario.objects.select_related('cargo').all()
for f in funcionarios:
    print(f.cargo.nome)
```

### 2. Serializer não retorna dados esperados

**Verificação**:
```python
# Certifique-se que os campos estão em Meta.fields
class MeuSerializer(serializers.ModelSerializer):
    class Meta:
        model = MeuModel
        fields = ['id', 'nome', 'data']  # ✅ Liste todos os campos
        # OU
        fields = '__all__'  # ✅ Todos os campos
```

### 3. Filtros não funcionam

**Verificação**:
```python
# Em filters.py
class MeuFilterSet(django_filters.FilterSet):
    class Meta:
        model = MeuModel
        fields = ['campo1', 'campo2']  # ✅ Campos devem existir no model

# Em views.py
class MeuViewSet(viewsets.ModelViewSet):
    filterset_class = MeuFilterSet  # ✅ Use filterset_class, não filter_class
```

### 4. Testes falhando com 401/403

**Solução**:
```python
# Em tests.py
def setUp(self):
    self.client = APIClient()
    
    # ✅ Criar usuário de teste
    self.user = Usuario.objects.create_user(
        username='test',
        password='test123',
        tipo_usuario='SUPERUSER'
    )
    
    # ✅ Autenticar cliente
    self.client.force_authenticate(user=self.user)

def test_meu_endpoint(self):
    # Agora o cliente está autenticado!
    response = self.client.get('/api/endpoint/')
    self.assertEqual(response.status_code, 200)
```

### 5. Migrações com erro

**Solução**:
```bash
# 1. Verificar migrações pendentes
python manage.py showmigrations

# 2. Criar novas migrações
python manage.py makemigrations

# 3. Aplicar migrações
python manage.py migrate

# 4. Se tiver conflito, fazer merge manual
python manage.py makemigrations --merge

# 5. Em último caso, resetar migrações (CUIDADO!)
# python manage.py migrate <app> zero
# python manage.py migrate <app>
```

---

## 📞 Suporte

Se o problema persistir:

1. ✅ Verifique os logs do Django: `python manage.py runserver` com `DEBUG=True`
2. ✅ Execute os testes: `python manage.py test`
3. ✅ Verifique o arquivo `.env` com configurações corretas
4. ✅ Consulte a documentação em `docs/`
5. ✅ Verifique exemplos em `docs/TEMPLATES_CODIGO.md`

---

## 🔧 Comandos Úteis

```bash
# Verificar configuração atual
python manage.py check

# Shell interativo
python manage.py shell

# Criar superusuário
python manage.py createsuperuser

# Coletar arquivos estáticos
python manage.py collectstatic

# Limpar cache
python manage.py clearcache

# Executar testes específicos
python manage.py test apps.api.gestao.superuser.tests

# Executar testes com verbose
python manage.py test --verbosity=2

# Executar apenas um teste
python manage.py test apps.api.gestao.superuser.tests.ContabilidadeViewSetTests.test_list_contabilidades_superuser
```

---

**Última Atualização**: 13/10/2025
