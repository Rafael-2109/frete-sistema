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

### **🧾 1. FATURAMENTO POR PRODUTO** ✅ **IMPLEMENTADO COMPLETO**
| Rota | Método | Função | Template |
|------|--------|--------|----------|
| `/faturamento/produtos` | GET | Listar faturamento por produto | `faturamento/listar_produtos.html` |
| `/faturamento/produtos/importar` | GET/POST | Importar dados de faturamento | `faturamento/importar_produtos.html` ✅ |

**Colunas Excel específicas**:
- `Linhas da fatura/NF-e` → numero_nf
- `Linhas da fatura/Parceiro/CNPJ` → cnpj_cliente  
- `Linhas da fatura/Parceiro` → nome_cliente
- `Linhas da fatura/Parceiro/Município` → municipio (extrai cidade/UF)
- `Linhas da fatura/Produto/Referência` → cod_produto
- `Linhas da fatura/Produto/Nome` → nome_produto
- `Linhas da fatura/Quantidade` → qtd_produto_faturado
- `Linhas da fatura/Valor Total do Item da NF` → valor_produto_faturado
- `Linhas da fatura/Data` → data_fatura
- `Status` → status_nf (Forward Fill)
- `Vendedor` → vendedor (Forward Fill)
- `Incoterm` → incoterm (Forward Fill)

**Funcionalidades especiais**: Forward Fill automático, extração Cidade(UF), conversão valores BR, validação status

---

### **🏭 2. PROGRAMAÇÃO DE PRODUÇÃO** ✅ **CORRIGIDO 29/06/2025**
| Rota | Método | Função | Template |
|------|--------|--------|----------|
| `/producao/` | GET | Dashboard produção | `producao/dashboard.html` |
| `/producao/programacao` | GET | Listar programação | `producao/listar_programacao.html` |
| `/producao/programacao/importar` | GET/POST | Importar programação | `producao/importar_programacao.html` ✅ |

**🔧 CORREÇÃO APLICADA**: Rota de importação renomeada de `/producao/importar` para `/producao/programacao/importar` para coincidir com o template.

**Colunas Excel específicas**:
- `DATA` → data_programacao (formato DD/MM/YYYY)
- `SEÇÃO / MÁQUINA` → linha_producao
- `CÓDIGO` → cod_produto
- `OP` → observacao_pcp
- `DESCRIÇÃO` → nome_produto
- `CLIENTE` → cliente_produto
- `QTDE` → qtd_programada

**Comportamento**: Sempre substitui dados existentes (limpa antes de importar)

---

### **📦 3. MOVIMENTAÇÃO DE ESTOQUE** ✅ **ATUALIZADA CONFORME ARQUIVO 6**
| Rota | Método | Função | Template |
|------|--------|--------|----------|
| `/estoque/` | GET | Dashboard estoque | `estoque/dashboard.html` |
| `/estoque/movimentacoes` | GET | Listar movimentações | `estoque/listar_movimentacoes.html` |
| `/estoque/movimentacoes/importar` | GET/POST | Importar movimentações | `estoque/importar_movimentacoes.html` ✅ |

**Colunas Excel específicas**:
- `tipo_movimentacao` → tipo_movimentacao (EST INICIAL, AVARIA, DEVOLUÇÃO, PRODUÇÃO, RETRABALHO)
- `cod_produto` → cod_produto
- `nome_produto` → nome_produto 
- `local_movimentacao` → local_movimentacao
- `data_movimentacao` → data_movimentacao (formato DD/MM/YYYY)
- `qtd_movimentacao` → qtd_movimentacao

**Comportamento**: Sempre adiciona registros (nunca remove)
**Validações**: Tipos permitidos validados automaticamente

---

### **⚖️ 4. CADASTRO DE PALLETIZAÇÃO** ✅ **ATUALIZADA CONFORME ARQUIVO 8**
| Rota | Método | Função | Template |
|------|--------|--------|----------|
| `/producao/palletizacao` | GET | Listar palletização | `producao/listar_palletizacao.html` |
| `/producao/palletizacao/importar` | GET/POST | Importar palletização | `producao/importar_palletizacao.html` ✅ |

**Colunas Excel específicas**:
- `Cód.Produto` → cod_produto
- `Descrição Produto` → nome_produto
- `PALLETIZACAO` → palletizacao (fator conversão para pallets)
- `PESO BRUTO` → peso_bruto (fator conversão para peso)
- `altura_cm` → altura_cm (opcional)
- `largura_cm` → largura_cm (opcional)
- `comprimento_cm` → comprimento_cm (opcional)

**Comportamento**: Substitui existentes, adiciona novos (por cod_produto)
**Funcionalidades**: Cálculo automático de volume (altura × largura × comprimento)

---

### **🗺️ 5. CADASTRO DE ROTAS** ✅ **ATUALIZADA CONFORME ARQUIVO 9**
| Rota | Método | Função | Template |
|------|--------|--------|----------|
| `/localidades/rotas` | GET | Listar rotas | `localidades/listar_rotas.html` |
| `/localidades/rotas/importar` | GET/POST | Importar rotas | `localidades/importar_rotas.html` ✅ |

**Colunas Excel específicas**:
- `ESTADO` → cod_uf (2 caracteres, ex: ES, SP, RJ)
- `ROTA` → rota (descrição da rota de entrega)

**Comportamento**: Substitui rota se UF já existe, adiciona novos
**Validação**: UF deve existir no cadastro de cidades

---

### **🎯 6. CADASTRO DE SUB-ROTAS** ✅ **ATUALIZADA CONFORME ARQUIVO 10**
| Rota | Método | Função | Template |
|------|--------|--------|----------|
| `/localidades/sub-rotas` | GET | Listar sub-rotas | `localidades/listar_sub_rotas.html` |
| `/localidades/sub-rotas/importar` | GET/POST | Importar sub-rotas | `localidades/importar_sub_rotas.html` ✅ |

**Colunas Excel específicas**:
- `ESTADO` → cod_uf (2 caracteres, ex: AC, RJ, SP)
- `CIDADE` → nome_cidade (nome da cidade, ex: RIO BRANCO)
- `SUB ROTA` → sub_rota (descrição da sub-rota, ex: CAP)

**Comportamento**: Sub rota única por combinação UF+Cidade
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
app/templates/faturamento/importar_produtos.html     # ✅ Importar faturamento por produto
app/templates/producao/importar_programacao.html     # ✅ Importar programação de produção
app/templates/estoque/importar_movimentacoes.html    # ✅ Importar movimentações de estoque
app/templates/producao/importar_palletizacao.html    # ✅ Importar cadastro de palletização
app/templates/localidades/importar_rotas.html        # ✅ Importar cadastro de rotas
app/templates/localidades/importar_sub_rotas.html    # ✅ Importar cadastro de sub-rotas
```

---

## 🔥 **ATUALIZAÇÕES REALIZADAS - JANEIRO 2025**

### **✅ COMPLETAMENTE ATUALIZADAS CONFORME ARQUIVOS CSV:**

1. **Faturamento por Produto** (arquivo 3) - Forward Fill automático implementado
2. **Programação de Produção** (arquivo 5) - Colunas exatas mapeadas
3. **Movimentações de Estoque** (arquivo 6) - Tipos validados automaticamente
4. **Cadastro Palletização** (arquivo 8) - Medidas opcionais incluídas
5. **Cadastro de Rotas** (arquivo 9) - Validação com cadastro de cidades
6. **Cadastro de Sub-rotas** (arquivo 10) - Validação UF+Cidade

### **🎯 FUNCIONALIDADES ESPECIAIS IMPLEMENTADAS:**

- **Forward Fill**: Preenchimento automático de campos vazios (arquivo 3)
- **Extração Cidade/UF**: Parse automático "Cidade (UF)" → campos separados
- **Conversão valores brasileiros**: 3.281,10 → 3281.10 automaticamente
- **Validação status**: Status permitidos validados (Lançado, Cancelado, Provisório)
- **Validação tipos**: Tipos movimentação validados automaticamente
- **Cálculo automático**: Preço unitário = valor_total ÷ quantidade
- **Volume automático**: Cálculo m³ baseado em dimensões
- **Validação referencial**: UF/Cidade devem existir no cadastro

### **🔄 COMPORTAMENTOS ESPECÍFICOS:**

| Módulo | Comportamento | Justificativa |
|--------|---------------|---------------|
| **Faturamento** | Substitui/Adiciona | NF+Produto = chave única |
| **Programação** | Substitui tudo | Sempre limpa antes (planejamento) |
| **Estoque** | Sempre adiciona | Histórico de movimentações |
| **Palletização** | Substitui/Adiciona | Cadastro mestre por produto |
| **Rotas** | Substitui/Adiciona | Rota única por UF |
| **Sub-rotas** | Substitui/Adiciona | Sub-rota única por UF+Cidade |

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
| **CadastroSubRota** | �� Substitui/Adiciona | cod_uf + nome_cidade | Cidade+UF em Cidade |


