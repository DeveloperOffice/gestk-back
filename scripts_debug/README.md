# 🛠️ Scripts de Debug e Testes

Esta pasta contém scripts auxiliares criados durante o desenvolvimento para testes, análises e debug do sistema.

## 📂 Organização dos Scripts

### 🔐 Scripts de Autenticação e API
- `debug_api_carteira.py` - Debug da API de carteira de clientes
- `testar_carteira.py` - Testes do módulo de carteira
- `testar_fluxo_completo.py` - Teste do fluxo completo (login → token → API)
- `testar_login.py` - Testes de autenticação
- `testar_superuser.py` - Testes de lógica de superuser
- `verificar_usuarios.py` - Verificação de usuários no banco

### 📊 Scripts de ETL
- `analisar_erros_etl19.py` - Análise de erros no ETL19
- `analisar_resultado_etl19_final.py` - Análise de resultados do ETL19
- `monitorar_etl_06.py` - Monitoramento do ETL06
- `verificar_etl15_regra_ouro.py` - Verificação do ETL15 (Regra Ouro)
- `verificar_status_etls.py` - Status geral de todos os ETLs
- `validar_etl03_regime_cnae.py` - ⭐ **NOVO** Validação ETL03_1 (Regime Tributário e CNAE)

### 📝 Scripts de Análise de Dados
- `analisar_rubricas.py` - Análise de rubricas
- `test_rubricas.py` - Testes de rubricas
- `check_notas.py` - Verificação de notas fiscais
- `verificar_banco.py` - Verificação geral do banco de dados
- `verificar_mapeamento.py` - Verificação de mapeamentos
- `verify_cnpj_contratos.py` - Verificação de CNPJs em contratos

## ⚠️ Importante

**Estes scripts são apenas para desenvolvimento e debug.**

- ✅ Podem ser executados localmente
- ❌ NÃO devem ser usados em produção
- ❌ NÃO devem ser commitados (exceto se documentados)
- 🔒 Alguns podem conter tokens/senhas de teste

## 🚀 Como Usar

```bash
# Executar qualquer script
cd scripts_debug
python nome_do_script.py
```

## 📖 Documentação Relacionada

Documentações técnicas foram movidas para a pasta `/docs`:
- `ANALISE_FRONTEND_VS_BACKEND.md`
- `IMPLEMENTACAO_SUPERUSER.md`
- `STATUS_IMPLEMENTACAO_SUPERUSER.md`
- `TESTE_POSTMAN.md`
- `SOLUCAO_ERRO_403_CSRF.txt`
- `SOLUCAO_PROBLEMAS_LOGIN.txt`
