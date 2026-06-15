# 📋 Integração TagPlus - Instruções Completas

## 🔑 Credenciais Fornecidas

- **CLIENT ID**: `FGDgfhaHfqkZLL9kLtU0wfN71c3hq7AD`
- **CLIENT SECRET**: `uNWYSWyOHGFJvJoEdw1H5xgZnCM92Ey7`
- **URL DE RETORNO**: `https://app.tagplus.com.br/xldby0d6/`

## 🚀 Como Configurar

### 1. Acesse a Página de Configuração OAuth

```
https://sistema-fretes.onrender.com/integracoes/tagplus/oauth
```

### 2. Fluxo OAuth2 (Recomendado)

O fluxo OAuth2 padrão requer:

1. **Autorização**: Usuário clica em "Autorizar no TagPlus"
2. **Login**: Faz login no TagPlus
3. **Permissão**: Autoriza o aplicativo
4. **Callback**: É redirecionado de volta com um código
5. **Token**: Sistema troca código por access_token

### 3. Alternativas

#### A. Token Manual
Se você já tem um access_token:
1. Cole o token na página OAuth
2. Clique em "Salvar Tokens"

#### B. Importação via Excel
1. Exporte dados do TagPlus em Excel
2. Use a importação por arquivo

## 🔧 Configuração Técnica

### Arquivos Criados/Modificados

1. **`app/integracoes/tagplus/config.py`**
   - Configuração centralizada
   - Credenciais OAuth2

2. **`app/integracoes/tagplus/oauth_flow.py`**
   - Fluxo OAuth2 completo
   - Página de autorização

3. **`app/templates/integracoes/tagplus_oauth.html`**
   - Interface para configuração
   - Teste de conexão

4. **Scripts de Teste**
   - `test_tagplus_integration.py`
   - `test_tagplus_oauth.py`
   - `test_tagplus_response.py`

## 🌐 URLs e Endpoints

### URLs OAuth2 (a confirmar com TagPlus)
- Autorização: `https://api.tagplus.com.br/oauth/authorize`
- Token: `https://api.tagplus.com.br/oauth/token`
- API Base: `https://api.tagplus.com.br/v1`

### Endpoints da API
- `/clientes` - Lista de clientes
- `/nfes` - Notas fiscais eletrônicas
- `/produtos` - Catálogo de produtos
- `/pedidos` - Pedidos de venda

## ⚠️ Problemas Encontrados

1. **Autenticação OAuth2**: As URLs padrão retornaram erro 401
2. **Documentação**: Pode ser necessário confirmar URLs corretas com TagPlus
3. **Método**: Talvez precise de outro método além de OAuth2

## 📝 Próximos Passos

1. **Confirmar com TagPlus**:
   - URLs corretas da API
   - Método de autenticação
   - Se as credenciais estão ativas

2. **Testar Fluxo Completo**:
   - Autorizar aplicação
   - Obter access_token
   - Fazer chamadas à API

3. **Implementar Webhooks**:
   - Configurar URLs de webhook no TagPlus
   - Processar notificações em tempo real

## 🛠️ Comandos Úteis

```bash
# Testar integração localmente
python3 test_tagplus_integration.py

# Testar OAuth2
python3 test_tagplus_oauth.py

# Verificar resposta detalhada
python3 test_tagplus_response.py
```

## 📌 Observações

- Access Token válido por 24 horas
- Refresh Token válido por 15 dias
- Novos tokens invalidam os anteriores
- Use HTTPS em produção