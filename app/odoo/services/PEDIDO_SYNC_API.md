# 📡 API de Sincronização Manual de Pedidos - Documentação

## 📋 Visão Geral

API REST para sincronizar pedidos específicos com o Odoo de forma manual.

**Endpoint Base**: `/api/v1/odoo/pedido/<num_pedido>/sync`

---

## 🔐 Autenticação

A API requer **DUPLA AUTENTICAÇÃO**:

### 1. API Key (Header)
```http
X-API-Key: sua-api-key-aqui
```

### 2. JWT Token (Header)
```http
Authorization: Bearer seu-jwt-token-aqui
```

**IMPORTANTE**: Ambos os headers são obrigatórios. A requisição será rejeitada com `401 Unauthorized` se algum estiver ausente ou inválido.

---

## 🚀 Endpoint: Sincronizar Pedido Específico

### **POST** `/api/v1/odoo/pedido/<num_pedido>/sync`

Sincroniza um pedido específico com o Odoo.

### Comportamento

| Situação no Odoo | Ação no Sistema | Status HTTP |
|-----------------|-----------------|-------------|
| ✅ Pedido encontrado | **ATUALIZA** conforme Odoo | `200 OK` |
| ❌ Pedido NÃO encontrado | **EXCLUI** do sistema | `200 OK` |
| 🚫 Pedido CANCELADO | **EXCLUI** do sistema | `200 OK` |
| ⚠️ Erro na operação | Retorna erro | `500 Error` |

---

## 📨 Exemplos de Requisição

### Usando cURL

```bash
curl -X POST "http://localhost:5000/api/v1/odoo/pedido/VSC12345/sync" \
  -H "X-API-Key: sua-api-key" \
  -H "Authorization: Bearer seu-jwt-token" \
  -H "Content-Type: application/json"
```

### Usando Python (requests)

```python
import requests

url = "http://localhost:5000/api/v1/odoo/pedido/VSC12345/sync"

headers = {
    "X-API-Key": "sua-api-key",
    "Authorization": "Bearer seu-jwt-token",
    "Content-Type": "application/json"
}

response = requests.post(url, headers=headers)
print(response.json())
```

### Usando JavaScript (fetch)

```javascript
const numPedido = 'VSC12345';
const url = `http://localhost:5000/api/v1/odoo/pedido/${numPedido}/sync`;

const response = await fetch(url, {
  method: 'POST',
  headers: {
    'X-API-Key': 'sua-api-key',
    'Authorization': 'Bearer seu-jwt-token',
    'Content-Type': 'application/json'
  }
});

const data = await response.json();
console.log(data);
```

---

## 📤 Exemplos de Resposta

### ✅ Caso 1: Pedido Atualizado com Sucesso

**Status**: `200 OK`

```json
{
  "success": true,
  "message": "Pedido VSC12345 atualizado conforme dados do Odoo",
  "data": {
    "acao": "ATUALIZADO",
    "num_pedido": "VSC12345",
    "detalhes": {
      "num_pedido": "VSC12345",
      "itens_processados": 5,
      "tipo_processamento": "ALTERACOES_APLICADAS",
      "alteracoes": [
        {
          "tipo": "REDUCAO",
          "cod_produto": "PROD001",
          "qtd_reduzida": 10.5
        }
      ],
      "alertas": []
    },
    "tempo_execucao": 1.23,
    "timestamp": "2025-01-20T10:30:15.123456"
  }
}
```

### 🗑️ Caso 2: Pedido Excluído (Não Encontrado no Odoo)

**Status**: `200 OK`

```json
{
  "success": true,
  "message": "Pedido VSC12345 excluído completamente do sistema (não encontrado no Odoo)",
  "data": {
    "acao": "EXCLUIDO",
    "num_pedido": "VSC12345",
    "detalhes": {
      "num_pedido": "VSC12345",
      "motivo": "Pedido não encontrado ou cancelado no Odoo"
    },
    "tempo_execucao": 0.87,
    "timestamp": "2025-01-20T10:30:15.123456"
  }
}
```

### ❌ Caso 3: Erro na Sincronização

**Status**: `500 Internal Server Error`

```json
{
  "success": false,
  "message": "Erro ao sincronizar pedido: Conexão com Odoo indisponível",
  "data": {
    "acao": "NAO_PROCESSADO",
    "num_pedido": "VSC12345",
    "detalhes": {},
    "tempo_execucao": 0.05,
    "timestamp": "2025-01-20T10:30:15.123456"
  }
}
```

### 🔒 Caso 4: Autenticação Falhou

**Status**: `401 Unauthorized`

```json
{
  "success": false,
  "message": "API Key inválida ou ausente"
}
```

---

## 🔍 Detalhes de Processamento

### Quando o Pedido é ATUALIZADO

O sistema executa as seguintes ações:

1. ✅ Busca dados atualizados do pedido no Odoo
2. ✅ Identifica todas as separações relacionadas ao pedido
3. ✅ Aplica alterações conforme hierarquia:
   - **Separação TOTAL**: Substitui completamente os dados
   - **Separação PARCIAL**: Aplica ajustes incrementais
4. ✅ Atualiza quantidades, preços e status
5. ✅ Gera alertas se separação estiver COTADA
6. ✅ Recalcula peso e pallets automaticamente

### Quando o Pedido é EXCLUÍDO

O sistema executa as seguintes ações:

1. 🗑️ Cancela todos os `EmbarqueItem` relacionados
2. 🗑️ Exclui todas as `Separacao` do pedido
3. 🗑️ Exclui todos os itens da `CarteiraPrincipal`
4. 🗑️ Remove `PreSeparacaoItem` se existirem
5. ✅ Registra log de auditoria completo

---

## ⚠️ Proteções e Validações

### Proteções Implementadas

- ✅ **Pedidos com NF processada sem lote**: NÃO são alterados (proteção contra redução indevida)
- ✅ **Separações sincronizadas** (`sincronizado_nf=True`): NÃO são alteradas
- ✅ **Separações FATURADAS/EMBARCADAS**: Apenas atualizadas em casos específicos
- ✅ **Dados de lote preservados**: Rota, transportadora, datas são mantidas
- ✅ **Recálculo automático**: Peso e pallets recalculados via `CadastroPalletizacao`

### Alertas Gerados

- 🚨 **Separação COTADA alterada**: Alerta CRÍTICO gerado automaticamente
- ⚠️ **Produto novo em separação parcial**: Alerta informativo
- ⚠️ **Aumento em separação COTADA**: Requer análise manual

---

## 📊 Casos de Uso

### Caso 1: Cliente alterou quantidade no pedido

```bash
# Cliente alterou VSC12345 de 100 para 80 unidades no Odoo
curl -X POST "http://localhost:5000/api/v1/odoo/pedido/VSC12345/sync" \
  -H "X-API-Key: sua-key" \
  -H "Authorization: Bearer token"

# Resultado: Pedido atualizado, quantidade reduzida para 80
```

### Caso 2: Pedido foi cancelado no Odoo

```bash
# Pedido VSC12345 foi cancelado no Odoo
curl -X POST "http://localhost:5000/api/v1/odoo/pedido/VSC12345/sync" \
  -H "X-API-Key: sua-key" \
  -H "Authorization: Bearer token"

# Resultado: Pedido completamente excluído do sistema
```

### Caso 3: Sincronização após inconsistência

```bash
# Detectada inconsistência no pedido VSC12345
# Forçar sincronização manual
curl -X POST "http://localhost:5000/api/v1/odoo/pedido/VSC12345/sync" \
  -H "X-API-Key: sua-key" \
  -H "Authorization: Bearer token"

# Resultado: Pedido atualizado conforme estado real no Odoo
```

---

## 🔧 Troubleshooting

### Problema: `401 Unauthorized`

**Causa**: API Key ou JWT Token inválidos

**Solução**:
1. Verificar se ambos os headers estão presentes
2. Verificar se a API Key está correta
3. Verificar se o JWT Token não expirou

### Problema: `500 Internal Server Error`

**Causa**: Erro na conexão com Odoo ou processamento

**Solução**:
1. Verificar conectividade com Odoo
2. Verificar logs do servidor: `tail -f logs/app.log`
3. Verificar se pedido existe no banco de dados

### Problema: Pedido não atualizado

**Causa**: Separação pode estar protegida

**Solução**:
1. Verificar se separação tem NF processada
2. Verificar status da separação (FATURADO não é alterado)
3. Verificar logs para mensagens de proteção

---

## 📝 Logs e Auditoria

### Logs Gerados

Todos os eventos são logados em `logs/app.log`:

```
🔄 Iniciando sincronização manual do pedido VSC12345
🔍 Buscando pedido VSC12345 no Odoo...
✅ Pedido VSC12345 encontrado no Odoo - State: sale, Tipo: venda
📦 Encontradas 5 linhas para o pedido VSC12345
📝 Atualizando pedido VSC12345 no sistema...
📊 5 itens mapeados para processamento
✅ Pedido VSC12345 ATUALIZADO com sucesso
✅ Sincronização do pedido VSC12345 concluída em 1.23s - Ação: ATUALIZADO
```

### Auditoria

- ✅ Cada alteração é registrada com timestamp
- ✅ Usuário responsável é registrado (via JWT)
- ✅ Ações de exclusão são auditadas completamente
- ✅ Alertas críticos são persistidos no banco

---

## 🧪 Testando a API

### Teste de Conectividade

```bash
curl -X GET "http://localhost:5000/api/v1/odoo/test" \
  -H "X-API-Key: sua-key" \
  -H "Authorization: Bearer token"
```

### Teste com Pedido Real

```bash
# Substituir VSC12345 por um pedido real do seu sistema
curl -X POST "http://localhost:5000/api/v1/odoo/pedido/VSC12345/sync" \
  -H "X-API-Key: sua-key" \
  -H "Authorization: Bearer token" \
  -v  # Modo verbose para ver detalhes
```

---

## 📚 Referências

### Arquivos Relacionados

- **Serviço**: [app/odoo/services/pedido_sync_service.py](app/odoo/services/pedido_sync_service.py)
- **Rota**: [app/api/odoo/routes.py](app/api/odoo/routes.py) (linha 305)
- **Serviço de Ajuste**: [app/odoo/services/ajuste_sincronizacao_service.py](app/odoo/services/ajuste_sincronizacao_service.py)
- **Serviço de Carteira**: [app/odoo/services/carteira_service.py](app/odoo/services/carteira_service.py)

### Modelos Afetados

- `Separacao` - Principal modelo afetado
- `CarteiraPrincipal` - Excluído se pedido cancelado
- `EmbarqueItem` - Cancelado se pedido excluído
- `PreSeparacaoItem` - Removido se existir (modelo deprecated)

---

## ⚡ Performance

### Métricas Esperadas

- **Tempo médio**: 0.5 - 2 segundos
- **Timeout**: 30 segundos (configurável)
- **Conexões simultâneas**: Suporta múltiplas requisições

### Otimizações

- ✅ Queries otimizadas com índices
- ✅ Batch processing de produtos
- ✅ Cache de palletização
- ✅ Transações atômicas

---

## 🔄 Diferenças vs Sincronização Automática

| Característica | Manual (esta API) | Automática (Incremental) |
|---------------|-------------------|--------------------------|
| **Acionamento** | Sob demanda | Periódica (cron/job) |
| **Escopo** | Um pedido por vez | Todos os pedidos alterados |
| **Performance** | Imediata | Agendada |
| **Uso** | Correção pontual | Manutenção rotineira |
| **Autenticação** | API Key + JWT | Interna |

---

## 💡 Dicas de Uso

1. **Use para correções pontuais**: Quando um pedido específico precisa ser ressincronizado
2. **Não abuse**: Para sincronizações em massa, use a sincronização incremental automática
3. **Monitore logs**: Sempre verifique os logs após executar
4. **Teste primeiro**: Use endpoint de teste para validar conectividade
5. **Guarde tokens**: API Key e JWT Token devem ser mantidos seguros

---

## 📞 Suporte

Em caso de dúvidas ou problemas:

1. Verifique os logs em `logs/app.log`
2. Consulte a documentação do sistema em `CLAUDE.md`
3. Verifique regras de negócio em `REGRAS_NEGOCIO.md`
4. Entre em contato com o time de desenvolvimento

---

**Última atualização**: 2025-01-20
**Versão da API**: 1.0.0
**Autor**: Sistema de Fretes
