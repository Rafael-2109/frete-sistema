# 🔄 COMO FUNCIONA O REFRESH TOKEN NO TAGPLUS

**Data**: 2025-11-06
**Versão**: 2.0 - Com persistência em banco de dados

---

## 🎯 OBJETIVO

Minimizar a necessidade de autorização manual no site do TagPlus, permitindo renovação automática de tokens por **30-90 dias**.

---

## 📋 FLUXO COMPLETO DO OAUTH2

### 1️⃣ PRIMEIRA AUTORIZAÇÃO (Manual - Apenas 1 vez a cada 30-90 dias)

```
Usuário → TagPlus → Autoriza App → Callback → Sistema recebe CÓDIGO
                                                     ↓
                                    Troca CÓDIGO por TOKENS
                                                     ↓
                             ┌────────────────────────────────────┐
                             │  access_token  (válido 24h)        │
                             │  refresh_token (válido 30-90 dias) │
                             └────────────────────────────────────┘
                                                     ↓
                                    ✅ SALVA NO BANCO DE DADOS
                                       (NÃO em session!)
```

**Endpoints usados:**
```python
# 1. Redireciona usuário para:
https://developers.tagplus.com.br/authorize?
    response_type=code&
    client_id=XXX&
    redirect_uri=https://sistema-fretes.onrender.com/tagplus/oauth/callback/nfe

# 2. TagPlus redireciona de volta com código:
https://sistema-fretes.onrender.com/tagplus/oauth/callback/nfe?code=ABC123

# 3. Sistema troca código por tokens:
POST https://api.tagplus.com.br/oauth2/token
{
  "grant_type": "authorization_code",
  "code": "ABC123",
  "client_id": "XXX",
  "client_secret": "YYY"
}

# 4. TagPlus retorna tokens:
{
  "access_token": "eyJhbGc...",      // ⏰ Expira em 24h
  "refresh_token": "dGVzdCByZWZ...", // ♻️ Dura 30-90 dias
  "expires_in": 86400,                // Segundos (24h)
  "token_type": "Bearer"
}

# 5. Sistema salva no banco PostgreSQL
INSERT INTO tagplus_oauth_token (api_type, access_token, refresh_token, expires_at, ...)
```

---

### 2️⃣ RENOVAÇÃO AUTOMÁTICA (Automático - Acontece sozinho)

```
     ┌──────────────────────────────────────┐
     │  Sistema faz requisição à API        │
     └──────────────────────────────────────┘
                      ↓
     ┌──────────────────────────────────────┐
     │  Verifica: access_token expirou?     │
     │  (Margem: 5 minutos antes)           │
     └──────────────────────────────────────┘
                      ↓
                    SIM
                      ↓
     ┌──────────────────────────────────────┐
     │  Tem refresh_token no banco?         │
     └──────────────────────────────────────┘
                      ↓
                    SIM
                      ↓
     ┌──────────────────────────────────────┐
     │  Renova automaticamente              │
     │  POST /oauth2/token                  │
     │  grant_type=refresh_token            │
     └──────────────────────────────────────┘
                      ↓
     ┌──────────────────────────────────────┐
     │  TagPlus retorna NOVOS tokens        │
     │  (access_token + refresh_token)      │
     └──────────────────────────────────────┘
                      ↓
     ┌──────────────────────────────────────┐
     │  ✅ Atualiza banco de dados          │
     │  ✅ Incrementa contador refreshes    │
     │  ✅ Registra timestamp                │
     └──────────────────────────────────────┘
                      ↓
     ┌──────────────────────────────────────┐
     │  Usa NOVO access_token na requisição │
     └──────────────────────────────────────┘
```

**Código da renovação:**
```python
POST https://api.tagplus.com.br/oauth2/token
{
  "grant_type": "refresh_token",
  "refresh_token": "dGVzdCByZWZ...",
  "client_id": "XXX",
  "client_secret": "YYY"
}

# TagPlus retorna NOVOS tokens (antigos são INVALIDADOS!):
{
  "access_token": "novo_token_aqui...",
  "refresh_token": "novo_refresh_aqui...",  // ⚠️ NOVO! Antigo é invalidado
  "expires_in": 86400
}
```

**⚠️ IMPORTANTE:**
- Cada renovação **invalida os tokens antigos**
- TagPlus retorna **novo refresh_token** a cada renovação
- **NÃO** tente renovar 2x com o mesmo refresh_token → **ERRO**

---

## 🗄️ ESTRUTURA DO BANCO DE DADOS

### Tabela: `tagplus_oauth_token`

```sql
CREATE TABLE tagplus_oauth_token (
    id SERIAL PRIMARY KEY,

    -- Tipo de API
    api_type VARCHAR(50) UNIQUE,  -- 'clientes', 'notas'

    -- Tokens
    access_token TEXT NOT NULL,   -- Expira 24h
    refresh_token TEXT,           -- Dura 30-90 dias

    -- Controle
    expires_at TIMESTAMP,         -- Quando expira
    ultimo_refresh TIMESTAMP,     -- Última renovação
    total_refreshes INTEGER,      -- Contador

    -- Status
    ativo BOOLEAN DEFAULT TRUE
);
```

**Exemplo de registro:**
```
id: 1
api_type: 'notas'
access_token: 'eyJhbGc...' (2000 caracteres)
refresh_token: 'dGVzdCBy...' (500 caracteres)
expires_at: '2025-11-07 10:30:00'
ultimo_refresh: '2025-11-06 10:35:00'
total_refreshes: 15
ativo: true
```

---

## 🔒 SEGURANÇA

### ✅ O que está SEGURO:

1. **Tokens no banco PostgreSQL** (não em session)
2. **Client Secret** configurado em variável de ambiente
3. **HTTPS** em todas as comunicações
4. **Margem de 5 minutos** antes da expiração (previne race conditions)

### ⚠️ Recomendações:

1. ✅ **Criptografar** `access_token` e `refresh_token` no banco (futuro)
2. ✅ **Rotação periódica** - Autorizar novamente a cada 30 dias (boas práticas)
3. ✅ **Monitorar** `total_refreshes` - Se > 1000, algo errado
4. ✅ **Logs de auditoria** - Quem usou, quando usou

---

## ⏰ TIMELINE DE RENOVAÇÃO

```
Dia 0: Autorização manual → access_token + refresh_token
            ↓
Dia 0 (23h50min): Sistema detecta expiração → RENOVA → novos tokens
            ↓
Dia 1 (23h50min): Sistema detecta expiração → RENOVA → novos tokens
            ↓
            ... (repete automaticamente todos os dias)
            ↓
Dia 30-90: refresh_token expira → ⚠️ PRECISA AUTORIZAR NOVAMENTE
```

**Cálculo:**
- 1 renovação por dia = 30-90 renovações até expirar
- `total_refreshes` deve estar entre 0-90

---

## 🚀 VANTAGENS DA IMPLEMENTAÇÃO

### ✅ ANTES (Session):
- ❌ Tokens perdidos a cada deploy
- ❌ Usuário precisa autorizar após cada deploy
- ❌ Sem controle de renovações
- ❌ Sem auditoria

### ✅ DEPOIS (Banco de Dados):
- ✅ Tokens persistem entre deploys
- ✅ Autorização manual apenas 1x a cada 30-90 dias
- ✅ Renovação automática diária
- ✅ Auditoria completa (quando, quantas vezes)
- ✅ Estatísticas de uso

---

## 📊 MONITORAMENTO

### Query úteis:

```sql
-- Ver status de todos os tokens
SELECT
    api_type,
    CASE WHEN expires_at > NOW() THEN 'VÁLIDO' ELSE 'EXPIRADO' END as status,
    expires_at,
    ultimo_refresh,
    total_refreshes,
    (expires_at - NOW()) as tempo_restante
FROM tagplus_oauth_token
WHERE ativo = true;

-- Ver histórico de renovações
SELECT
    api_type,
    total_refreshes,
    ultimo_refresh,
    (NOW() - ultimo_refresh) as tempo_desde_ultimo_refresh
FROM tagplus_oauth_token
ORDER BY ultimo_refresh DESC;
```

---

## 🛠️ COMO USAR

### 1. Primeira vez (Autorização Manual):

```python
# Usuário clica em "Autorizar TagPlus"
# Sistema redireciona para TagPlus
# TagPlus redireciona de volta com código
# Sistema troca código por tokens e salva no banco
```

### 2. Uso diário (Automático):

```python
from app.integracoes.tagplus.oauth2_v2 import TagPlusOAuth2V2

# Criar cliente
client = TagPlusOAuth2V2(api_type='notas')

# Fazer requisição (renovação automática se necessário)
response = client.make_request('GET', '/nfes', params={'per_page': 100})

# ✅ Sistema verifica automaticamente:
# 1. Token expirou? → Renova com refresh_token
# 2. Refresh_token expirou? → Lança exceção (reautorizar)
# 3. Tudo OK? → Usa access_token existente
```

---

## 🎯 RESUMO

1. **Autorize 1x manualmente** → Ganha 30-90 dias
2. **Sistema renova automaticamente** → Sem intervenção manual
3. **Tokens no banco** → Sobrevive deploys
4. **Após 30-90 dias** → Autorize novamente (rápido, 30 segundos)

**Resultado:** 99% do tempo sem precisar tocar no TagPlus! 🎉
