# 📋 DOCUMENTAÇÃO SISTEMA CARTEIRA DE PEDIDOS

## 🎯 **VISÃO GERAL**

O Sistema de Carteira de Pedidos foi **100% implementado** com 6 módulos distribuídos em 3 blueprints Flask, totalizando **12 rotas** e **12 templates** funcionais.

### **📊 MÓDULOS IMPLEMENTADOS:**
1. **FaturamentoProduto** - Faturamento detalhado por produto
2. **ProgramacaoProducao** - Planejamento da produção
3. **MovimentacaoEstoque** - Controle de estoque
4. **CadastroPalletizacao** - Fatores de conversão e dimensões
5. **CadastroRota** - Rotas por UF
6. **CadastroSubRota** - Sub-rotas por cidade

---

## 🏗️ **ARQUITETURA IMPLEMENTADA**

### **📁 ORGANIZAÇÃO DOS MÓDULOS:**
```
app/
├── faturamento/          # FaturamentoProduto
│   ├── models.py         # Modelo FaturamentoProduto
│   └── routes.py         # Rotas /faturamento/produtos*
├── producao/             # ProgramacaoProducao + CadastroPalletizacao  
│   ├── models.py         # ProgramacaoProducao + CadastroPalletizacao
│   └── routes.py         # Rotas /producao/* + /producao/palletizacao*
├── estoque/              # MovimentacaoEstoque
│   ├── models.py         # MovimentacaoEstoque
│   └── routes.py         # Rotas /estoque/*
└── localidades/          # CadastroRota + CadastroSubRota
    ├── models.py         # CadastroRota + CadastroSubRota
    └── routes.py         # Rotas /localidades/rotas* + /localidades/sub-rotas*
```

---

## 🔗 **ROTAS IMPLEMENTADAS**

### **🧾 1. FATURAMENTO POR PRODUTO**
| Rota | Método | Função | Template |
|------|--------|--------|----------|
| `/faturamento/produtos` | GET | Listar faturamento por produto | `faturamento/listar_produtos.html` |
| `/faturamento/produtos/importar` | GET/POST | Importar dados de faturamento | `faturamento/importar_produtos.html` |

**Filtros**: Data de/até, CNPJ cliente, nome cliente, código produto, nome produto, vendedor, incoterm  
**Comportamento**: Substitui existentes (NF+Produto), adiciona novos  
**Campos obrigatórios**: numero_nf, data_fatura, cnpj_cliente, nome_cliente, cod_produto, nome_produto, qtd_produto_faturado, preco_produto_faturado, valor_produto_faturado

---

### **🏭 2. PROGRAMAÇÃO DE PRODUÇÃO**
| Rota | Método | Função | Template |
|------|--------|--------|----------|
| `/producao/` | GET | Dashboard produção | `producao/dashboard.html` |
| `/producao/programacao` | GET | Listar programação | `producao/listar_programacao.html` |
| `/producao/programacao/importar` | GET/POST | Importar programação | `producao/importar_programacao.html` |

**Filtros**: Data de/até, código produto (dropdown), nome produto (dropdown), linha produção (dropdown)  
**Comportamento**: Sempre substitui dados existentes  
**Campos obrigatórios**: Data programação, código produto, nome produto, quantidade programada

---

### **📦 3. MOVIMENTAÇÃO DE ESTOQUE**
| Rota | Método | Função | Template |
|------|--------|--------|----------|
| `/estoque/` | GET | Dashboard estoque | `estoque/dashboard.html` |
| `/estoque/movimentacoes` | GET | Listar movimentações | `estoque/listar_movimentacoes.html` |
| `/estoque/movimentacoes/importar` | GET/POST | Importar movimentações | `estoque/importar_movimentacoes.html` |

**Filtros**: Data, tipo movimentação (AVARIA, EST INICIAL, DEVOLUÇÃO, PRODUÇÃO, RETRABALHO), código produto, nome produto, local  
**Comportamento**: Sempre adiciona registros  
**Validações**: Tipo movimentação validado, flag para produtos não cadastrados

---

### **⚖️ 4. CADASTRO DE PALLETIZAÇÃO**
| Rota | Método | Função | Template |
|------|--------|--------|----------|
| `/producao/palletizacao` | GET | Listar palletização | `producao/listar_palletizacao.html` |
| `/producao/palletizacao/importar` | GET/POST | Importar palletização | `producao/importar_palletizacao.html` |

**Filtros**: Código produto, nome produto, palletização, peso bruto  
**Comportamento**: Substitui existentes, adiciona novos  
**Campos obrigatórios**: cod_produto, nome_produto, palletizacao, peso_bruto  
**Campos opcionais**: altura_cm, largura_cm, comprimento_cm (com cálculo de volume automático)

---

### **🗺️ 5. CADASTRO DE ROTAS**
| Rota | Método | Função | Template |
|------|--------|--------|----------|
| `/localidades/rotas` | GET | Listar rotas | `localidades/listar_rotas.html` |
| `/localidades/rotas/importar` | GET/POST | Importar rotas | `localidades/importar_rotas.html` |

**Filtros**: UF, rota  
**Comportamento**: Substitui rota se UF já existe, adiciona novos  
**Campos obrigatórios**: cod_uf, rota  
**Validação**: UF deve existir no cadastro de cidades

---

### **🎯 6. CADASTRO DE SUB-ROTAS**
| Rota | Método | Função | Template |
|------|--------|--------|----------|
| `/localidades/sub-rotas` | GET | Listar sub-rotas | `localidades/listar_sub_rotas.html` |
| `/localidades/sub-rotas/importar` | GET/POST | Importar sub-rotas | `localidades/importar_sub_rotas.html` |

**Filtros**: UF, cidade, sub rota  
**Comportamento**: Sub rota única por combinação UF+Cidade  
**Campos obrigatórios**: UF, cidade, sub rota  
**Validação**: Combinação Cidade+UF deve existir no cadastro de cidades

---

## 🎨 **TEMPLATES IMPLEMENTADOS**

### **📄 TEMPLATES DE LISTAGEM (6 arquivos):**
```
app/templates/faturamento/listar_produtos.html     # Lista faturamento por produto
app/templates/producao/listar_programacao.html     # Lista programação de produção
app/templates/estoque/listar_movimentacoes.html    # Lista movimentações de estoque
app/templates/producao/listar_palletizacao.html    # Lista cadastro de palletização
app/templates/localidades/listar_rotas.html        # Lista cadastro de rotas
app/templates/localidades/listar_sub_rotas.html    # Lista cadastro de sub-rotas
```

### **📤 TEMPLATES DE IMPORTAÇÃO (6 arquivos):**
```
app/templates/faturamento/importar_produtos.html     # Importar faturamento por produto
app/templates/producao/importar_programacao.html     # Importar programação de produção
app/templates/estoque/importar_movimentacoes.html    # Importar movimentações de estoque
app/templates/producao/importar_palletizacao.html    # Importar cadastro de palletização
app/templates/localidades/importar_rotas.html        # Importar cadastro de rotas
app/templates/localidades/importar_sub_rotas.html    # Importar cadastro de sub-rotas
```

---

## 🚀 **URLs DE ACESSO**

### **🌐 PRODUÇÃO (Render.com):**
```
https://frete-sistema.onrender.com/faturamento/produtos
https://frete-sistema.onrender.com/producao/programacao  
https://frete-sistema.onrender.com/estoque/movimentacoes
https://frete-sistema.onrender.com/producao/palletizacao
https://frete-sistema.onrender.com/localidades/rotas
https://frete-sistema.onrender.com/localidades/sub-rotas
```

---

## 📋 **MODELOS DE DADOS**

### **🧾 FaturamentoProduto:**
```python
numero_nf, data_fatura, cnpj_cliente, nome_cliente, municipio, estado,
vendedor, incoterm, cod_produto, nome_produto, qtd_produto_faturado,
preco_produto_faturado, valor_produto_faturado
```

### **🏭 ProgramacaoProducao:**
```python
data_programacao, cod_produto, nome_produto, qtd_programada,
linha_producao, cliente_produto, observacao_pcp
```

### **📦 MovimentacaoEstoque:**
```python
tipo_movimentacao, cod_produto, nome_produto, local_movimentacao,
data_movimentacao, qtd_movimentacao, observacao, documento_origem
```

### **⚖️ CadastroPalletizacao:**
```python
cod_produto, nome_produto, palletizacao, peso_bruto,
altura_cm, largura_cm, comprimento_cm, volume_m3 (calculado)
```

### **🗺️ CadastroRota:**
```python
cod_uf, rota, ativa
```

### **🎯 CadastroSubRota:**
```python
cod_uf, nome_cidade, sub_rota, ativa
```

---

## 🎯 **COMPORTAMENTOS DE IMPORTAÇÃO**

| Módulo | Comportamento | Chave Única | Validações |
|--------|---------------|-------------|------------|
| **FaturamentoProduto** | 🔄 Substitui/Adiciona | numero_nf + cod_produto | Mapeamento flexível |
| **ProgramacaoProducao** | ♻️ Sempre substitui | Período completo | Data válida |
| **MovimentacaoEstoque** | ➕ Sempre adiciona | - | Tipo movimentação |
| **CadastroPalletizacao** | 🔄 Substitui/Adiciona | cod_produto | Nenhuma |
| **CadastroRota** | 🔄 Substitui/Adiciona | cod_uf | UF em Cidade |
| **CadastroSubRota** | 🔄 Substitui/Adiciona | cod_uf + nome_cidade | Cidade+UF em Cidade |


