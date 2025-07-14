# 🔗 API ODOO - INTEGRAÇÃO SISTEMA DE FRETES

## 📋 **VISÃO GERAL**

A API Odoo fornece endpoints REST para sincronização bidirecional entre o Odoo e o Sistema de Fretes. Implementa autenticação robusta, validação de dados e processamento em lote otimizado.

## 🚀 **ENDPOINTS DISPONÍVEIS**

### 1. **Teste de Conectividade**
```
GET /api/v1/odoo/test
```
Valida conectividade e autenticação.

### 2. **Carteira de Pedidos**
```
POST /api/v1/odoo/carteira/bulk-update
```
Atualiza/cria registros na carteira de pedidos em lote.

### 3. **Faturamento**
```
POST /api/v1/odoo/faturamento/bulk-update
```
Atualiza/cria registros de faturamento (consolidado ou por produto).

## 🔐 **AUTENTICAÇÃO**

### **Dupla Autenticação (API Key + JWT)**

**Headers obrigatórios:**
```http
X-API-Key: odoo-integration-key-2024
Authorization: Bearer <jwt_token>
Content-Type: application/json
```

### **Obter JWT Token**
```python
from app.api.odoo.auth import generate_jwt_token

token = generate_jwt_token(
    user_id=1,
    username='odoo_user',
    permissions=['carteira', 'faturamento'],
    expires_in_hours=24
)
```

## 📊 **CARTEIRA DE PEDIDOS**

### **Campos Obrigatórios**
```json
{
  "items": [
    {
      "num_pedido": "string",
      "cod_produto": "string", 
      "nome_produto": "string",
      "qtd_produto_pedido": "float",
      "qtd_saldo_produto_pedido": "float",
      "cnpj_cpf": "string",
      "preco_produto_pedido": "float"
    }
  ]
}
```

### **Campos Opcionais**
```json
{
  "pedido_cliente": "string",
  "data_pedido": "YYYY-MM-DD",
  "status_pedido": "string",
  "raz_social": "string",
  "raz_social_red": "string",
  "municipio": "string",
  "estado": "string",
  "vendedor": "string",
  "equipe_vendas": "string",
  "unid_medida_produto": "string",
  "embalagem_produto": "string",
  "materia_prima_produto": "string",
  "categoria_produto": "string",
  "qtd_cancelada_produto_pedido": "float",
  "cond_pgto_pedido": "string",
  "forma_pgto_pedido": "string",
  "incoterm": "string",
  "metodo_entrega_pedido": "string",
  "data_entrega_pedido": "YYYY-MM-DD",
  "cliente_nec_agendamento": "string",
  "observ_ped_1": "string",
  "cnpj_endereco_ent": "string",
  "empresa_endereco_ent": "string",
  "cep_endereco_ent": "string",
  "nome_cidade": "string",
  "cod_uf": "string",
  "bairro_endereco_ent": "string",
  "rua_endereco_ent": "string",
  "endereco_ent": "string",
  "telefone_endereco_ent": "string",
  "estoque": "float",
  "menor_estoque_produto_d7": "float",
  "saldo_estoque_pedido": "float",
  "saldo_estoque_pedido_forcado": "float",
  "qtd_total_produto_carteira": "float",
  "estoque_d0": "float",
  "estoque_d1": "float",
  "...": "...",
  "estoque_d28": "float"
}
```

### **Exemplo de Requisição**
```python
import requests

url = "https://sistema-fretes.onrender.com/api/v1/odoo/carteira/bulk-update"
headers = {
    'X-API-Key': 'odoo-integration-key-2024',
    'Authorization': 'Bearer <jwt_token>',
    'Content-Type': 'application/json'
}

data = {
    "items": [
        {
            "num_pedido": "PED001",
            "cod_produto": "PROD001",
            "nome_produto": "Produto Exemplo",
            "qtd_produto_pedido": 100.0,
            "qtd_saldo_produto_pedido": 80.0,
            "cnpj_cpf": "12345678901234",
            "preco_produto_pedido": 15.50,
            "raz_social": "Cliente Exemplo LTDA",
            "municipio": "São Paulo",
            "estado": "SP",
            "vendedor": "João Silva"
        }
    ]
}

response = requests.post(url, headers=headers, json=data)
print(response.json())
```

## 💰 **FATURAMENTO**

### **Faturamento Consolidado**
```json
{
  "tipo": "consolidado",
  "items": [
    {
      "numero_nf": "string",
      "data_fatura": "YYYY-MM-DD",
      "cnpj_cliente": "string",
      "nome_cliente": "string",
      "valor_total": "float",
      "origem": "string",
      "peso_bruto": "float",
      "cnpj_transportadora": "string",
      "nome_transportadora": "string",
      "municipio": "string",
      "estado": "string",
      "codigo_ibge": "string",
      "incoterm": "string",
      "vendedor": "string"
    }
  ]
}
```

### **Faturamento por Produto**
```json
{
  "tipo": "produto",
  "items": [
    {
      "numero_nf": "string",
      "data_fatura": "YYYY-MM-DD",
      "cnpj_cliente": "string",
      "nome_cliente": "string",
      "cod_produto": "string",
      "nome_produto": "string",
      "qtd_produto_faturado": "float",
      "preco_produto_faturado": "float",
      "valor_produto_faturado": "float",
      "municipio": "string",
      "estado": "string",
      "vendedor": "string",
      "incoterm": "string",
      "origem": "string",
      "status_nf": "string",
      "peso_total": "float"
    }
  ]
}
```

## 🔧 **RESPOSTAS DA API**

### **Resposta de Sucesso**
```json
{
  "success": true,
  "message": "Operação realizada com sucesso",
  "timestamp": "2024-01-15T10:30:00",
  "processed": 100,
  "created": 60,
  "updated": 40,
  "errors": []
}
```

### **Resposta de Erro**
```json
{
  "success": false,
  "message": "Erros de validação encontrados",
  "timestamp": "2024-01-15T10:30:00",
  "errors": [
    "Item 1: Campo obrigatório 'num_pedido' não informado",
    "Item 2: qtd_produto_pedido deve ser um número positivo"
  ]
}
```

## 📋 **VALIDAÇÕES**

### **Regras de Negócio**
- `qtd_saldo_produto_pedido` ≤ `qtd_produto_pedido`
- `data_fatura` não pode ser futura
- CNPJ deve ter 11 ou 14 dígitos
- Valores numéricos devem ser positivos
- Campos obrigatórios não podem estar vazios

### **Formatos de Data**
- **Aceitos**: `YYYY-MM-DD`, `DD/MM/YYYY`
- **Retornado**: `YYYY-MM-DD`

## 🛡️ **SEGURANÇA**

### **Rate Limiting**
- **Limite**: 100 requisições/hora por API Key
- **Headers**: `X-RateLimit-Remaining`, `X-RateLimit-Reset`

### **Logs de Auditoria**
Todas as operações são registradas com:
- Timestamp
- Usuário/API Key
- Operação realizada
- Dados processados
- Resultados

## 🚨 **CÓDIGOS DE ERRO**

| Código | Descrição |
|---------|-----------|
| 200 | Sucesso |
| 400 | Dados inválidos |
| 401 | Não autorizado |
| 403 | Permissão insuficiente |
| 429 | Rate limit excedido |
| 500 | Erro interno |

## 🧪 **TESTES**

### **Executar Testes**
```bash
python test_odoo_api.py
```

### **Testes Disponíveis**
- ✅ Autenticação
- ✅ Bulk Update Carteira
- ✅ Bulk Update Faturamento
- ✅ Validação de Erros
- ✅ Falha na Autenticação

## 📈 **PERFORMANCE**

### **Otimizações**
- Processamento em lote otimizado
- Commits em lotes de 1000 registros
- Validação em paralelo
- Cache de permissões

### **Limites Recomendados**
- **Carteira**: Até 1000 itens por requisição
- **Faturamento**: Até 500 itens por requisição
- **Timeout**: 300 segundos

## 📞 **SUPORTE**

### **Configurações de Produção**
```python
# Variáveis de ambiente
JWT_SECRET_KEY=sua-chave-secreta-super-segura
ODOO_API_TIMEOUT=300
ODOO_BATCH_SIZE=1000
```

### **Logs de Debug**
```python
import logging
logging.getLogger('app.api.odoo').setLevel(logging.DEBUG)
```

### **Contato**
- **Sistema**: Sistema de Fretes
- **URL**: https://sistema-fretes.onrender.com
- **Documentação**: `/api/v1/odoo/test`

---

**Versão**: 1.0.0  
**Data**: 2024-01-15  
**Autor**: Sistema de Fretes - Integração Odoo 