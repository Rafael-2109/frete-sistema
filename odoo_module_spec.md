# 📋 ESPECIFICAÇÕES TÉCNICAS - MÓDULO ODOO SISTEMA DE FRETES

## 🎯 **1. ROTA: ATUALIZAÇÃO DA CARTEIRA DE PEDIDOS**

### **Endpoint:** `POST /api/v1/carteira/bulk-update`

### **Descrição:**
Atualiza/cria registros na carteira de pedidos baseado nos dados do Odoo.

### **Campos Obrigatórios:**
```json
{
  "num_pedido": "string",           // Número do pedido (chave primária)
  "cod_produto": "string",          // Código do produto (chave primária)
  "nome_produto": "string",         // Nome do produto
  "qtd_produto_pedido": "float",    // Quantidade original
  "qtd_saldo_produto_pedido": "float", // Saldo a faturar
  "cnpj_cpf": "string",            // CNPJ do cliente
  "preco_produto_pedido": "float"   // Preço unitário
}
```

### **Campos Opcionais (Dados do Pedido):**
```json
{
  "pedido_cliente": "string",       // Pedido de compra do cliente
  "data_pedido": "date",           // Data de criação (YYYY-MM-DD)
  "data_atual_pedido": "date",     // Data da última alteração
  "status_pedido": "string"        // Status: "Pedido de venda", "Cancelado", "Cotação"
}
```

### **Campos Opcionais (Dados do Cliente):**
```json
{
  "raz_social": "string",          // Razão Social completa
  "raz_social_red": "string",      // Nome reduzido
  "municipio": "string",           // Cidade do cliente
  "estado": "string",              // UF do cliente (2 caracteres)
  "vendedor": "string",            // Vendedor responsável
  "equipe_vendas": "string"        // Equipe de vendas
}
```

### **Campos Opcionais (Dados do Produto):**
```json
{
  "unid_medida_produto": "string",     // Unidade de medida
  "embalagem_produto": "string",       // Categoria
  "materia_prima_produto": "string",   // Sub categoria
  "categoria_produto": "string"        // Sub sub categoria
}
```

### **Campos Opcionais (Quantidades e Valores):**
```json
{
  "qtd_cancelada_produto_pedido": "float", // Quantidade cancelada
  "cond_pgto_pedido": "string",           // Condições de pagamento
  "forma_pgto_pedido": "string",          // Forma de pagamento
  "incoterm": "string",                   // Incoterm
  "metodo_entrega_pedido": "string",      // Método de entrega
  "data_entrega_pedido": "date",          // Data de entrega
  "cliente_nec_agendamento": "string",    // "Sim" ou "Não"
  "observ_ped_1": "text"                  // Observações
}
```

### **Campos Opcionais (Endereço de Entrega):**
```json
{
  "cnpj_endereco_ent": "string",      // CNPJ do local de entrega
  "empresa_endereco_ent": "string",   // Nome do local de entrega
  "cep_endereco_ent": "string",       // CEP
  "nome_cidade": "string",            // Cidade de entrega
  "cod_uf": "string",                 // UF de entrega
  "bairro_endereco_ent": "string",    // Bairro
  "rua_endereco_ent": "string",       // Rua
  "endereco_ent": "string",           // Número
  "telefone_endereco_ent": "string"   // Telefone
}
```

### **Campos Opcionais (Análise de Estoque):**
```json
{
  "estoque": "float",                        // Estoque atual D0
  "menor_estoque_produto_d7": "float",       // Previsão ruptura 7 dias
  "saldo_estoque_pedido": "float",           // Estoque na data expedição
  "saldo_estoque_pedido_forcado": "float",   // Just-in-time
  "qtd_total_produto_carteira": "float"      // Qtd total produto na carteira
}
```

### **Campos Opcionais (Projeção de Estoque D0-D28):**
```json
{
  "estoque_d0": "float",   // Estoque final D0
  "estoque_d1": "float",   // Estoque final D1
  "estoque_d2": "float",   // Estoque final D2
  // ... até estoque_d28
  "estoque_d28": "float"   // Estoque final D28
}
```

### **Formato da Requisição:**
```json
{
  "items": [
    {
      "num_pedido": "123456",
      "cod_produto": "4220179",
      "nome_produto": "AZEITONA PRETA AZAPA - VD 12X360 GR",
      "qtd_produto_pedido": 100.0,
      "qtd_saldo_produto_pedido": 80.0,
      "cnpj_cpf": "75.315.333/0103-33",
      "preco_produto_pedido": 32.81,
      "raz_social": "ATACADAO 103",
      "municipio": "Olímpia",
      "estado": "SP",
      "vendedor": "12 SCHIAVINATTO REP COM SC LTDA",
      "data_pedido": "2024-12-01",
      "status_pedido": "Pedido de venda",
      "incoterm": "CIF",
      "nome_cidade": "Olímpia",
      "cod_uf": "SP",
      "estoque": 500.0,
      "estoque_d0": 500.0,
      "estoque_d1": 480.0,
      "estoque_d7": 400.0
    }
  ]
}
```

### **Resposta de Sucesso:**
```json
{
  "success": true,
  "message": "Carteira atualizada com sucesso",
  "processed": 1,
  "created": 1,
  "updated": 0,
  "errors": []
}
```

---

## 🎯 **2. ROTA: ATUALIZAÇÃO DO FATURAMENTO**

### **Endpoint:** `POST /api/v1/faturamento/bulk-update`

### **Descrição:**
Atualiza/cria registros de faturamento baseado nos dados do Odoo.

### **Campos Obrigatórios (Faturamento Consolidado):**
```json
{
  "numero_nf": "string",           // Número da NF (chave primária)
  "data_fatura": "date",           // Data da fatura (YYYY-MM-DD)
  "cnpj_cliente": "string",        // CNPJ do cliente
  "nome_cliente": "string",        // Nome do cliente
  "valor_total": "float",          // Valor total da NF
  "origem": "string"               // Número do pedido origem
}
```

### **Campos Opcionais (Faturamento Consolidado):**
```json
{
  "peso_bruto": "float",               // Peso bruto da NF
  "cnpj_transportadora": "string",     // CNPJ da transportadora
  "nome_transportadora": "string",     // Nome da transportadora
  "municipio": "string",               // Cidade do cliente
  "estado": "string",                  // UF do cliente
  "codigo_ibge": "string",             // Código IBGE da cidade
  "incoterm": "string",                // Incoterm
  "vendedor": "string"                 // Vendedor responsável
}
```

### **Campos Obrigatórios (Faturamento por Produto):**
```json
{
  "numero_nf": "string",               // Número da NF
  "data_fatura": "date",               // Data da fatura
  "cnpj_cliente": "string",            // CNPJ do cliente
  "nome_cliente": "string",            // Nome do cliente
  "cod_produto": "string",             // Código do produto
  "nome_produto": "string",            // Nome do produto
  "qtd_produto_faturado": "float",     // Quantidade faturada
  "preco_produto_faturado": "float",   // Preço unitário
  "valor_produto_faturado": "float"    // Valor total do produto
}
```

### **Campos Opcionais (Faturamento por Produto):**
```json
{
  "municipio": "string",               // Cidade do cliente
  "estado": "string",                  // UF do cliente
  "vendedor": "string",                // Vendedor responsável
  "incoterm": "string",                // Incoterm
  "origem": "string",                  // Número do pedido origem
  "status_nf": "string",               // Status: "Lançado", "Cancelado", "Provisório"
  "peso_total": "float"                // Peso total do produto
}
```

### **Formato da Requisição (Faturamento Consolidado):**
```json
{
  "tipo": "consolidado",
  "items": [
    {
      "numero_nf": "128944",
      "data_fatura": "2024-12-01",
      "cnpj_cliente": "75.315.333/0103-33",
      "nome_cliente": "ATACADAO 103",
      "valor_total": 5331.85,
      "origem": "123456",
      "peso_bruto": 150.5,
      "municipio": "Olímpia",
      "estado": "SP",
      "incoterm": "CIF",
      "vendedor": "12 SCHIAVINATTO REP COM SC LTDA"
    }
  ]
}
```

### **Formato da Requisição (Faturamento por Produto):**
```json
{
  "tipo": "produto",
  "items": [
    {
      "numero_nf": "128944",
      "data_fatura": "2024-12-01",
      "cnpj_cliente": "75.315.333/0103-33",
      "nome_cliente": "ATACADAO 103",
      "cod_produto": "4220179",
      "nome_produto": "AZEITONA PRETA AZAPA - VD 12X360 GR",
      "qtd_produto_faturado": 10.0,
      "preco_produto_faturado": 328.11,
      "valor_produto_faturado": 3281.10,
      "municipio": "Olímpia",
      "estado": "SP",
      "origem": "123456",
      "status_nf": "Lançado",
      "vendedor": "12 SCHIAVINATTO REP COM SC LTDA",
      "incoterm": "CIF"
    }
  ]
}
```

### **Resposta de Sucesso:**
```json
{
  "success": true,
  "message": "Faturamento atualizado com sucesso",
  "processed": 1,
  "created": 1,
  "updated": 0,
  "errors": []
}
```

---

## 🔐 **3. AUTENTICAÇÃO E SEGURANÇA**

### **Headers Obrigatórios:**
```
Content-Type: application/json
Authorization: Bearer <token_jwt>
X-API-Key: <api_key>
```

### **Validação de Token:**
- Token JWT válido
- Permissões adequadas para carteira/faturamento
- Rate limiting: 100 requests/minuto

---

## 🚨 **4. VALIDAÇÕES E REGRAS DE NEGÓCIO**

### **Carteira de Pedidos:**
1. **Chave Única:** `num_pedido` + `cod_produto`
2. **Validação:** `qtd_saldo_produto_pedido` ≤ `qtd_produto_pedido`
3. **Preservação:** Campos operacionais (expedicao, agendamento, protocolo, lote_separacao_id) são preservados
4. **Atualização Inteligente:** Detecta alterações importantes e notifica sistemas dependentes

### **Faturamento:**
1. **Chave Única:** `numero_nf` (para consolidado) ou `numero_nf` + `cod_produto` (para produto)
2. **Validação:** `data_fatura` não pode ser futura
3. **Validação:** `status_nf` deve ser "Lançado", "Cancelado" ou "Provisório"
4. **Integração:** Automaticamente sincroniza com monitoramento de entregas

---

## 📊 **5. CÓDIGOS DE ERRO**

### **Respostas de Erro:**
```json
{
  "success": false,
  "message": "Erro na validação dos dados",
  "errors": [
    {
      "field": "num_pedido",
      "message": "Campo obrigatório",
      "code": "FIELD_REQUIRED"
    },
    {
      "field": "qtd_saldo_produto_pedido",
      "message": "Saldo não pode ser maior que quantidade do pedido",
      "code": "BUSINESS_RULE_VIOLATION"
    }
  ]
}
```

### **Códigos de Status HTTP:**
- `200` - Sucesso
- `400` - Erro de validação
- `401` - Não autorizado
- `403` - Sem permissão
- `422` - Erro de regra de negócio
- `500` - Erro interno

---

## 🔄 **6. PROCESSAMENTO AUTOMÁTICO**

### **Após Atualização da Carteira:**
1. Recalcula totalizadores por cliente
2. Atualiza análise de estoque
3. Notifica sistema de separação se houver lote vinculado
4. Valida necessidade de aprovação para cotações

### **Após Atualização do Faturamento:**
1. Sincroniza automaticamente com monitoramento de entregas
2. Processa baixa automática na carteira
3. Revalida embarques pendentes
4. Lança fretes automaticamente para CNPJs importados

---

## 🧪 **7. EXEMPLO DE TESTE**

### **Comando cURL para Carteira:**
```bash
curl -X POST http://localhost:5000/api/v1/carteira/bulk-update \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{
    "items": [
      {
        "num_pedido": "123456",
        "cod_produto": "4220179",
        "nome_produto": "AZEITONA PRETA AZAPA",
        "qtd_produto_pedido": 100.0,
        "qtd_saldo_produto_pedido": 80.0,
        "cnpj_cpf": "75.315.333/0103-33",
        "preco_produto_pedido": 32.81
      }
    ]
  }'
```

### **Comando cURL para Faturamento:**
```bash
curl -X POST http://localhost:5000/api/v1/faturamento/bulk-update \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{
    "tipo": "consolidado",
    "items": [
      {
        "numero_nf": "128944",
        "data_fatura": "2024-12-01",
        "cnpj_cliente": "75.315.333/0103-33",
        "nome_cliente": "ATACADAO 103",
        "valor_total": 5331.85,
        "origem": "123456"
      }
    ]
  }'
```

---

## 📝 **8. OBSERVAÇÕES IMPORTANTES**

### **Carteira de Pedidos:**
- Sistema preserva dados operacionais existentes
- Atualização inteligente com detecção de alterações
- Suporte a projeção de estoque D0-D28
- Integração automática com sistema de separação

### **Faturamento:**
- Suporta dois tipos: consolidado e por produto
- Sincronização automática com monitoramento
- Processamento de baixa automática na carteira
- Validação de inconsistências entre sistemas

### **Performance:**
- Processamento em lote para múltiplos registros
- Validação otimizada com transações
- Logging detalhado para auditoria
- Rollback automático em caso de erro 