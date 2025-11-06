# 🔐 SEGURANÇA DOS WEBHOOKS TAGPLUS

**Data de Criação**: 08/10/2025
**Última Atualização**: 06/11/2025

---

## 📋 EVENTOS SUPORTADOS

### Eventos de NFE (Endpoint: `/webhook/tagplus/nfe`)

| Evento | Ação | Descrição |
|--------|------|-----------|
| `nfe_autorizada` | ✅ PROCESSAR | NFe autorizada pela SEFAZ - Cria faturamento e vincula com pedidos |
| `autorizada` | ✅ PROCESSAR | Alias para nfe_autorizada |
| `nfe_aprovada` | ✅ PROCESSAR | Alias para nfe_autorizada |
| **(vazio)** | ✅ PROCESSAR | Assume automaticamente nfe_autorizada |
| `nfe_cancelada` | ❌ CANCELAR | NFe cancelada - Marca itens como cancelados |
| `cancelada` | ❌ CANCELAR | Alias para nfe_cancelada |
| `nfe_denegada` | ❌ CANCELAR | NFe denegada pela SEFAZ - Trata como cancelamento |
| `nfe_rejeitada` | ❌ CANCELAR | NFe rejeitada - Trata como cancelamento |
| `nfe_alterada` | ⏭️ IGNORAR | Ignora (não processa) |
| `nfe_apagada` | ⏭️ IGNORAR | Ignora (não processa) |

### Eventos de Cliente (Endpoint: `/webhook/tagplus/cliente`)

| Evento | Ação | Descrição |
|--------|------|-----------|
| `cliente_criado` | ✅ CRIAR | Cria novo cliente no sistema |
| `criado` | ✅ CRIAR | Alias para cliente_criado |
| `cliente_atualizado` | ✅ ATUALIZAR | Atualiza dados do cliente |
| `atualizado` | ✅ ATUALIZAR | Alias para cliente_atualizado |

### ⚠️ Comportamento Especial: Evento Vazio

O TagPlus pode enviar webhooks **sem o campo `evento`** ou com **`evento=""`**. Nestes casos:
- ✅ Sistema assume automaticamente `nfe_autorizada`
- 📝 Log registra: `"⚠️ Evento vazio recebido - assumindo 'nfe_autorizada'"`
- ✅ Processa normalmente a NFe

---

## 🚨 PROBLEMAS RESOLVIDOS

### Erro Anterior:
```
[POST]400 /webhook/tagplus/nfe
[POST]400 /webhook/tagplus/cliente
Erro: "The CSRF token is missing."
```

### Causa:
- Webhooks externos (TagPlus) NÃO possuem tokens CSRF
- CSRF estava habilitado globalmente bloqueando requisições externas
- Webhooks eram rejeitados com erro 400 antes de processar

### Solução Implementada:
✅ Adicionado `@csrf.exempt` em todas as rotas de webhook
✅ Mantida validação HMAC com `X-Hub-Secret`
✅ Logs detalhados de segurança para auditoria
✅ Suporte a dois modos de validação (secret plano e HMAC)

---

## 🔒 CONFIGURAÇÃO DE SEGURANÇA

### 1. Secret Configurado no Sistema

**Arquivo**: `app/integracoes/tagplus/webhook_routes.py`
**Linha**: 24

```python
WEBHOOK_SECRET = 'frete2024tagplus#secret'
```

⚠️ **IMPORTANTE**: Este mesmo valor DEVE ser configurado no TagPlus!

---

### 2. Configuração no TagPlus

Ao cadastrar o webhook no TagPlus, configure:

**Campo "X-Hub-Secret"**:
```
frete2024tagplus#secret
```

**URLs dos Webhooks**:
```
Cliente:  https://sistema-fretes.onrender.com/webhook/tagplus/cliente
NFE:      https://sistema-fretes.onrender.com/webhook/tagplus/nfe
Teste:    https://sistema-fretes.onrender.com/webhook/tagplus/teste
```

---

## 🔍 MODOS DE VALIDAÇÃO

O sistema aceita DOIS modos de validação (conforme TagPlus configurar):

### MODO 1: X-Hub-Secret (Recomendado)
TagPlus envia o secret em texto plano no header:
```http
POST /webhook/tagplus/nfe
X-Hub-Secret: frete2024tagplus#secret
Content-Type: application/json
```

**Validação**: Compara string exata
**Log**: `🔐 Validação via X-Hub-Secret: OK`

---

### MODO 2: X-TagPlus-Signature (HMAC-SHA256)
TagPlus envia hash HMAC do payload:
```http
POST /webhook/tagplus/nfe
X-TagPlus-Signature: a1b2c3d4e5f6...
Content-Type: application/json
```

**Validação**: Calcula HMAC-SHA256 e compara
**Log**: `🔐 Validação via X-TagPlus-Signature (HMAC): OK`

---

### MODO 3: Sem Validação (⚠️ INSEGURO)
Se nenhum header for enviado:
- ✅ Aceita a requisição (para não quebrar integração)
- ⚠️ Registra WARNING nos logs
- 🔓 Recomendação: Configure X-Hub-Secret no TagPlus!

**Log**: `⚠️ WEBHOOK SEM ASSINATURA | IP: xxx.xxx.xxx.xxx`

---

## 📊 LOGS DE SEGURANÇA

Todos os webhooks geram logs detalhados para auditoria:

### Webhook Recebido:
```
🔔 WEBHOOK RECEBIDO | Endpoint: /webhook/tagplus/nfe | IP: 52.6.206.165
🔍 Headers: {'X-Hub-Secret': 'frete...', 'Content-Type': 'application/json'}
```

### Validação OK:
```
✅ WEBHOOK VALIDADO | X-Hub-Secret válido
📦 WEBHOOK NFE | Evento: nfe_aprovada | NF: 3706
```

### Validação FALHOU:
```
🚫 WEBHOOK REJEITADO | Motivo: X-Hub-Secret inválido | IP: 52.6.206.165
```

### Sem Segurança:
```
⚠️ WEBHOOK SEM ASSINATURA | IP: 52.6.206.165 | Headers: ['Content-Type', 'User-Agent']
🔓 MODO INSEGURO: Aceitando webhook sem validação (configure X-Hub-Secret no TagPlus!)
```

---

## 🛡️ PROTEÇÃO CSRF

### Rotas com @csrf.exempt:
```python
@csrf.exempt
@tagplus_webhook.route('/webhook/tagplus/cliente', methods=['POST'])

@csrf.exempt
@tagplus_webhook.route('/webhook/tagplus/nfe', methods=['POST'])

@csrf.exempt
@tagplus_webhook.route('/webhook/tagplus/teste', methods=['GET', 'POST'])
```

**Por que?**
- Webhooks externos NÃO possuem token CSRF (normal e esperado)
- CSRF protege contra ataques de navegador (não se aplica a webhooks)
- Usamos validação HMAC/Secret como proteção alternativa

---

## 🧪 TESTE DOS WEBHOOKS

### 1. Endpoint de Teste
```bash
curl -X POST https://sistema-fretes.onrender.com/webhook/tagplus/teste \
  -H "Content-Type: application/json" \
  -H "X-Hub-Secret: frete2024tagplus#secret" \
  -d '{"teste": "ok"}'
```

**Resposta Esperada**:
```json
{
  "status": "ok",
  "mensagem": "Webhook TagPlus funcionando",
  "timestamp": "2025-10-08T20:30:00"
}
```

---

### 2. Teste de Cliente
```bash
curl -X POST https://sistema-fretes.onrender.com/webhook/tagplus/cliente \
  -H "Content-Type: application/json" \
  -H "X-Hub-Secret: frete2024tagplus#secret" \
  -d '{
    "evento": "cliente_criado",
    "cliente": {
      "cnpj": "12.345.678/0001-99",
      "razao_social": "EMPRESA TESTE LTDA",
      "cidade": "São Paulo",
      "uf": "SP"
    }
  }'
```

**Resposta Esperada**: `{"status": "ok"}`

---

### 3. Teste de NFE
```bash
curl -X POST https://sistema-fretes.onrender.com/webhook/tagplus/nfe \
  -H "Content-Type: application/json" \
  -H "X-Hub-Secret: frete2024tagplus#secret" \
  -d '{
    "evento": "nfe_aprovada",
    "nfe": {
      "numero": "12345",
      "data_emissao": "2025-10-08",
      "cliente": {
        "cnpj": "12.345.678/0001-99"
      },
      "itens": []
    }
  }'
```

**Resposta Esperada**: `{"status": "ok"}`

---

## 🔐 CHECKLIST DE SEGURANÇA

### ✅ Configurações Implementadas:
- [x] `@csrf.exempt` em todas as rotas de webhook
- [x] Validação dupla (X-Hub-Secret + X-TagPlus-Signature)
- [x] Logs detalhados de todas as requisições
- [x] IP do cliente registrado em logs
- [x] Headers completos em modo DEBUG
- [x] Motivo de rejeição detalhado
- [x] Warnings para webhooks sem assinatura

### 📋 Próximos Passos:
- [ ] Configurar X-Hub-Secret no painel TagPlus
- [ ] Monitorar logs para confirmar recebimento
- [ ] Testar eventos: cliente_criado, nfe_aprovada, nfe_cancelada
- [ ] Validar processamento completo (NF → Movimentação → Estoque)

---

## 📞 SUPORTE

**Em caso de erro nos webhooks**:
1. Verificar logs do sistema (`/var/log/sistema-fretes.log`)
2. Procurar por `🔔 WEBHOOK RECEBIDO` ou `🚫 WEBHOOK REJEITADO`
3. Confirmar secret no TagPlus: `frete2024tagplus#secret`
4. Testar com endpoint `/webhook/tagplus/teste` primeiro

---

## 🔄 CHANGELOG

### 06/11/2025
- ✅ Corrigido tratamento de evento vazio (TagPlus envia `evento=""`)
- ✅ Adicionado suporte a `nfe_autorizada` (evento padrão TagPlus)
- ✅ Adicionado suporte a `nfe_denegada` e `nfe_rejeitada` (cancelamento)
- ✅ Evento vazio agora assume automaticamente `nfe_autorizada`
- ✅ Corrigido import do csrf para topo do arquivo (PEP8)
- ✅ Melhorados logs com emojis para melhor visualização

### 08/10/2025
- ✅ Adicionado `@csrf.exempt` em todas as rotas
- ✅ Implementada validação dupla (X-Hub-Secret + HMAC)
- ✅ Logs de segurança detalhados
- ✅ Documentação completa criada
