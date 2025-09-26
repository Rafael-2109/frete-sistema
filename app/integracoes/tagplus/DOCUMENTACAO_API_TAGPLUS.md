# 📚 DOCUMENTAÇÃO COMPLETA DA API TAGPLUS

**Data de Criação**: 26/09/2025
**Última Atualização**: 26/09/2025
**Versão da API**: 2.0

## 🔑 AUTENTICAÇÃO

### URLs OAuth2 (FUNCIONANDO)
```
Authorization URL: https://developers.tagplus.com.br/authorize
Token URL: https://api.tagplus.com.br/oauth2/token
API Base URL: https://api.tagplus.com.br
```

### Headers Obrigatórios
```javascript
{
  'Authorization': 'Bearer {ACCESS_TOKEN}',
  'X-Api-Version': '2.0',
  'Accept': 'application/json'
}
```

---

## 📋 ENDPOINTS TESTADOS E FUNCIONANDO

### 1. LISTAR NOTAS FISCAIS (Resumo)
**Endpoint**: `GET /nfes`

#### Parâmetros que FUNCIONAM:
```javascript
{
  'since': '2025-08-26',      // Data inicial (YYYY-MM-DD)
  'until': '2025-09-25',      // Data final (YYYY-MM-DD)
  'per_page': 100,            // Quantidade por página
  'page': 1                   // Número da página
}
```

#### Resposta (LISTA DIRETA):
```json
[
  {
    "id": 2659,                // ID para buscar detalhes
    "id_nota": 2686,           // ID alternativo
    "numero": 3706,            // Número da NF
    "serie": 1,                // Série
    "cfop": "5.403",           // CFOP
    "valor_nota": 28594.78,    // Valor total da nota
    "data_entrada_saida": null,// Data (pode vir null)
    "destinatario": {          // Cliente/Destinatário
      "id": 1375,
      "tipo": "J",             // J=Jurídica, F=Física
      "razao_social": "CESTA BASICA BRASIL COMERCIO DE ALIMENTOS LT",
      "cpf": null,
      "cnpj": "04.108.518/0001-02",
      "enderecos": [...]      // Array de endereços
    }
  }
]
```

**⚠️ IMPORTANTE**: Esta listagem NÃO traz:
- Itens/produtos da NF
- Chave de acesso
- Datas de emissão completas
- Detalhes fiscais

---

### 2. BUSCAR DETALHES COMPLETOS DA NF
**Endpoint**: `GET /nfes/{id}`

Exemplo: `GET /nfes/2659`

#### Resposta (OBJETO COMPLETO):
```json
{
  "id": 2659,
  "id_nota": 2686,
  "numero": 3706,
  "serie": 1,
  "chave_acesso": "35240823456789012345678901234567890123456789",
  "status": "1",              // Status da NF
  "tipo": "S",                // S=Saída, E=Entrada
  "valor_nota": 28594.78,
  "data_emissao": "2024-08-15T10:30:00Z",
  "data_entrada_saida": "2024-08-15",

  "destinatario": {
    "id": 1375,
    "razao_social": "CESTA BASICA BRASIL COMERCIO DE ALIMENTOS LT",
    "cnpj": "04.108.518/0001-02",
    "enderecos": [...]
  },

  "itens": [                  // 🔴 ARRAY DE PRODUTOS
    {
      "id": 123,
      "item": 1,              // Número sequencial do item
      "qtd": 44,              // 🔴 QUANTIDADE
      "valor_unitario": 69.58,// 🔴 VALOR UNITÁRIO
      "valor_subtotal": 3061.52,// Valor total do item (qtd * valor_unit)

      "produto": {            // 🔴 DADOS DO PRODUTO
        "id": 150,
        "codigo": "4320147",  // 🔴 CÓDIGO DO PRODUTO
        "codigo_barras": "7898075649964",
        "descricao": "AZEITONA VERDE FATIADA POUCH 18x150 GR - CB", // 🔴 DESCRIÇÃO
        "categoria": {
          "id": 10,
          "descricao": "CONSERVA"
        }
      },

      // Campos fiscais
      "cfop": "5403",
      "cst_a": "00",
      "cst_b": "00",
      "aliquota_icms": 18.00,
      "base_calculo_icms": 3061.52,
      "valor_icms": 551.07,
      "base_calculo_icms_st": 3500.00,
      "valor_icms_st": 150.00,

      // Muitos outros campos fiscais...
    }
  ]
}
```

---

## 🔴 CAMPOS ESSENCIAIS DOS PRODUTOS

### No Array de Itens:
| Campo | Tipo | Descrição | Exemplo |
|-------|------|-----------|---------|
| `qtd` | int | Quantidade do produto | 44 |
| `valor_unitario` | float | Preço unitário | 69.58 |
| `valor_subtotal` | float | Total do item (qtd × unitário) | 3061.52 |
| `produto.codigo` | string | Código interno do produto | "4320147" |
| `produto.descricao` | string | Descrição completa | "AZEITONA VERDE..." |
| `produto.codigo_barras` | string | EAN/GTIN | "7898075649964" |

---

## 💡 FLUXO DE IMPORTAÇÃO RECOMENDADO

### 1. LISTAR NFs (Visão Geral)
```python
# Busca lista resumida
response = requests.get(
    'https://api.tagplus.com.br/nfes',
    headers=headers,
    params={
        'since': '2025-08-01',
        'until': '2025-08-31',
        'per_page': 100
    }
)
nfs_resumo = response.json()  # Lista com resumo das NFs
```

### 2. BUSCAR DETALHES DE CADA NF
```python
for nf_resumo in nfs_resumo:
    nf_id = nf_resumo['id']

    # Busca detalhes completos
    response = requests.get(
        f'https://api.tagplus.com.br/nfes/{nf_id}',
        headers=headers
    )
    nf_completa = response.json()

    # Processa itens
    for item in nf_completa['itens']:
        codigo = item['produto']['codigo']
        descricao = item['produto']['descricao']
        quantidade = item['qtd']
        valor_unit = item['valor_unitario']
        valor_total = item['valor_subtotal']
```

---

## ⚠️ OBSERVAÇÕES IMPORTANTES

### 1. PAGINAÇÃO
- A API retorna no máximo 100 registros por página
- Use `page` e `per_page` para navegar

### 2. FILTROS DE DATA
- Use `since` e `until` (formato YYYY-MM-DD)
- NÃO use `data_emissao_inicio` ou `data_emissao_fim`

### 3. ESTRUTURA DE RESPOSTA
- Lista de NFs: Retorna ARRAY direto `[{}, {}]`
- Detalhe de NF: Retorna OBJETO único `{}`

### 4. CAMPOS QUE PODEM VIR NULL
- `data_entrada_saida`
- `data_emissao` (na listagem)
- `cpf` ou `cnpj` (dependendo do tipo)

### 5. DESTINATÁRIO vs CLIENTE
- Use `destinatario` (não `cliente`)
- Dentro do destinatário: `razao_social` e `cnpj`/`cpf`

---

## 📂 ARQUIVOS DE EXEMPLO

### Estruturas Salvas:
- `exemplo_nfe_tagplus.json` - NF resumida da listagem
- `nf_completa.json` - NF com todos os detalhes e produtos

---

## 🔧 TROUBLESHOOTING

### Token Expirado
- **Erro**: Status 401
- **Solução**: Renovar token via OAuth2

### Sem NFs no Período
- **Erro**: Lista vazia `[]`
- **Solução**: Aumentar período ou remover filtros

### Endpoint Não Encontrado
- **Erro**: Status 404
- **Solução**: Use `/nfes` (plural) não `/nfe`

---

## 📝 CHANGELOG

### 26/09/2025
- Documentação inicial criada
- Endpoints `/nfes` e `/nfes/{id}` testados
- Estrutura de produtos mapeada
- Exemplos reais salvos