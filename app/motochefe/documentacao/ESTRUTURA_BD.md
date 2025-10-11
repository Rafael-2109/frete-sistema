# 📊 ESTRUTURA DO BANCO DE DADOS - SISTEMA MOTOCHEFE

**Versão**: 1.0.0
**Data**: Outubro 2025
**Autor**: Sistema gerado com Claude AI

---

## 🎯 VISÃO GERAL

O sistema MotoCHEFE foi projetado para controlar **TODAS** as operações de uma empresa de motos elétricas:
- ✅ Estoque (FIFO automático por chassi)
- ✅ Vendas (Pedido → Faturamento → Envio)
- ✅ Financeiro (Títulos a receber, Comissões)
- ✅ Logística (Embarques com rateio de frete)
- ✅ Custos Operacionais (Montagem, Movimentação)

---

## 📋 TABELAS (14 TOTAL)

### **GRUPO 1: CADASTROS** (4 tabelas)
| # | Tabela | Descrição | Registros |
|---|--------|-----------|-----------|
| 1 | `equipe_vendas_moto` | Equipes de vendas | Poucos |
| 2 | `vendedor_moto` | Vendedores (FK: equipe) | Dezenas |
| 3 | `transportadora_moto` | Transportadoras | Poucos |
| 4 | `cliente_moto` | Clientes (CNPJ único) | Centenas |

### **GRUPO 2: PRODUTOS** (2 tabelas)
| # | Tabela | Descrição | PK | Índices |
|---|--------|-----------|----|----|
| 5 | `modelo_moto` | Catálogo (Modelo+Potência+Preço Tabela) | `id` | - |
| 6 | `moto` | **CENTRAL** - 1 chassi = 1 registro | `numero_chassi` | `status`, `reservado`, `data_entrada` |

### **GRUPO 3: VENDAS** (2 tabelas)
| # | Tabela | Descrição | Relacionamento |
|---|--------|-----------|----------------|
| 7 | `pedido_venda_moto` | Pedido que vira Venda | 1 Pedido = N Itens |
| 8 | `pedido_venda_moto_item` | Itens (chassi via FIFO) | FK: pedido_id, numero_chassi |

### **GRUPO 4: FINANCEIRO** (2 tabelas)
| # | Tabela | Descrição | Cálculo |
|---|--------|-----------|---------|
| 9 | `titulo_financeiro` | Parcelas a receber | 1 Venda = N Títulos |
| 10 | `comissao_vendedor` | Comissão (Fixa + Excedente) | Rateada por equipe |

### **GRUPO 5: LOGÍSTICA** (2 tabelas)
| # | Tabela | Descrição | Lógica |
|---|--------|-----------|--------|
| 11 | `embarque_moto` | Embarque de entregas | 1 Embarque = N Pedidos |
| 12 | `embarque_pedido` | Relação N:N | Rateio frete por moto |

### **GRUPO 6: OPERACIONAL** (2 tabelas)
| # | Tabela | Descrição | Uso |
|---|--------|-----------|-----|
| 13 | `custos_operacionais` | Valores fixos (montagem, movimentação) | 1 registro ativo |
| 14 | `despesa_mensal` | Despesas (salário, aluguel, etc) | Cálculo margem |

---

## 🔄 FLUXO DE DADOS

### **1. ENTRADA DE MOTOS**
```
NF Entrada (1) → N Motos (cada chassi = 1 registro)
├── Armazena: nf_entrada, fornecedor, custo_aquisicao
├── Define: modelo_id (FK → modelo_moto)
└── Status inicial: DISPONIVEL, reservado=FALSE
```

### **2. CRIAÇÃO DE PEDIDO (FIFO AUTOMÁTICO)**
```
Vendedor cria Pedido → Sistema aloca chassi via FIFO:

SELECT numero_chassi FROM moto
WHERE modelo_id=X AND cor='Vermelho'
  AND status='DISPONIVEL' AND reservado=FALSE
ORDER BY data_entrada ASC  -- ✅ FIFO
LIMIT 2

→ Atualiza Moto: reservado=TRUE, status='RESERVADA'
→ Insere PedidoVendaMotoItem com numero_chassi
```

### **3. FATURAMENTO**
```
Pedido (faturado=FALSE) → Venda (faturado=TRUE)
├── Atualiza: numero_nf, data_nf, faturado=TRUE
├── Atualiza Moto: status='VENDIDA'
├── Cria TituloFinanceiro (se parcelado)
└── Cria ComissaoVendedor (fixa + excedente)
```

### **4. EMBARQUE E RATEIO DE FRETE**
```
EmbarqueMoto (valor_frete_pago=R$ 1.000)
├── Contém 3 pedidos:
│   ├── Pedido A: 2 motos
│   ├── Pedido B: 3 motos
│   └── Pedido C: 1 moto
│
└── Rateio automático:
    Total motos = 6
    Frete por moto = R$ 1.000 / 6 = R$ 166,67

    EmbarquePedido:
    ├── Pedido A: 2 * R$ 166,67 = R$ 333,34
    ├── Pedido B: 3 * R$ 166,67 = R$ 500,01
    └── Pedido C: 1 * R$ 166,67 = R$ 166,67
```

---

## 💰 CÁLCULOS FINANCEIROS

### **COMISSÃO**
```python
# Valores fixos (pegar de custos_operacionais)
comissao_fixa = R$ 500,00

# Excedente (soma de todos itens do pedido)
for item in pedido.itens:
    preco_venda = item.preco_venda  # Ex: R$ 11.500
    preco_tabela = item.moto.modelo.preco_tabela  # Ex: R$ 10.000

    if preco_venda > preco_tabela:
        excedente += (preco_venda - preco_tabela)  # R$ 1.500

# Total
valor_total = comissao_fixa + excedente  # R$ 2.000

# Rateio entre vendedores da equipe
qtd_vendedores_equipe = 2
valor_rateado = valor_total / qtd_vendedores  # R$ 1.000 cada
```

### **MARGEM BRUTA (por moto)**
```python
# Receitas
receita_venda = item.preco_venda
receita_frete = pedido.valor_frete_cliente / qtd_motos_pedido
receita_montagem = item.valor_montagem (se montagem_contratada=TRUE)

# Custos
custo_moto = item.moto.custo_aquisicao
custo_comissao = comissao_total_pedido / qtd_motos_pedido
custo_frete = embarque_pedido.valor_frete_rateado / qtd_motos_pedido
custo_montagem = custos_operacionais.custo_montagem (se montagem=TRUE)
custo_movimentacao = custos_operacionais.custo_movimentacao_rj OU nacom

# Margem
margem_bruta = (receita_venda + receita_frete + receita_montagem)
               - (custo_moto + custo_comissao + custo_frete
                  + custo_montagem + custo_movimentacao)
```

### **MARGEM MENSAL**
```python
# 1. Soma margem bruta de todas vendas do mês (faturado=TRUE)
margem_bruta_total = SOMA(margem_bruta de cada moto vendida)

# 2. Despesas operacionais do mês
despesas = SELECT SUM(valor) FROM despesa_mensal
           WHERE mes_competencia=X AND ano_competencia=Y

# 3. Margem líquida
margem_liquida = margem_bruta_total - despesas
```

---

## 🔑 CHAVES E CONSTRAINTS

### **Foreign Keys Principais**:
```sql
moto.modelo_id → modelo_moto.id
pedido_venda_moto.cliente_id → cliente_moto.id
pedido_venda_moto.vendedor_id → vendedor_moto.id
pedido_venda_moto_item.numero_chassi → moto.numero_chassi
embarque_pedido.embarque_id → embarque_moto.id
embarque_pedido.pedido_id → pedido_venda_moto.id
```

### **Unique Constraints**:
```sql
moto.numero_chassi (PK)
moto.numero_motor (UNIQUE)
modelo_moto.nome_modelo (UNIQUE)
cliente_moto.cnpj_cliente (UNIQUE)
pedido_venda_moto.numero_pedido (UNIQUE)
pedido_venda_moto.numero_nf (UNIQUE, nullable)
embarque_pedido(embarque_id, pedido_id) (UNIQUE composta)
```

### **Índices para Performance**:
```sql
-- Moto (FIFO e buscas frequentes)
idx_moto_status
idx_moto_reservado
idx_moto_data_entrada
idx_moto_modelo_id

-- Pedidos (queries frequentes)
idx_pedido_faturado
idx_pedido_enviado
idx_pedido_numero_nf

-- Financeiro
idx_titulo_status
idx_comissao_status

-- Logística
idx_embarque_status
```

---

## 📈 REGRAS DE NEGÓCIO IMPLEMENTADAS

| # | Regra | Implementação |
|---|-------|---------------|
| RN1 | FIFO de chassi | `ORDER BY data_entrada ASC` |
| RN2 | 1 Pedido = 1 NF | Sem faturamento parcial |
| RN3 | Comissão = Fixa + Excedente | Calculada em `ComissaoVendedor` |
| RN4 | Rateio de comissão | Dividida igualmente por vendedores da equipe |
| RN5 | Rateio de frete | Proporcional a qtd motos no embarque |
| RN6 | Status da Moto | DISPONIVEL → RESERVADA → VENDIDA |
| RN7 | Cancelamento de pedido | Libera chassi (reservado=FALSE, status=DISPONIVEL) |
| RN8 | Montagem opcional | Gera receita + despesa |
| RN9 | Margem mensal | Σ(Margem Bruta) - Despesas |

---

## 🛠️ INSTRUÇÕES DE USO

### **1. Criar tabelas no Render**
```bash
# 1. Acesse o Shell do PostgreSQL no Render
# 2. Copie o conteúdo de: app/motochefe/scripts/create_tables.sql
# 3. Cole e execute no Shell
```

### **2. Importar models no Python**
```python
from app.motochefe.models import (
    ModeloMoto, Moto,
    PedidoVendaMoto, PedidoVendaMotoItem,
    TituloFinanceiro, ComissaoVendedor,
    EmbarqueMoto, EmbarquePedido
)
```

### **3. Exemplo: Criar pedido com FIFO**
```python
# Ver: app/motochefe/services/venda_service.py (futuro)
# Lógica de alocação automática de chassi
```

---

## 📁 ESTRUTURA DE ARQUIVOS

```
app/motochefe/
├── __init__.py
├── ESTRUTURA_BD.md (este arquivo)
├── escopo.md (especificação original)
├── models/
│   ├── __init__.py
│   ├── cadastro.py (VendedorMoto, EquipeVendasMoto, etc)
│   ├── produto.py (ModeloMoto, Moto)
│   ├── vendas.py (PedidoVendaMoto, Items)
│   ├── financeiro.py (Titulo, Comissao)
│   ├── logistica.py (Embarque)
│   └── operacional.py (Custos, Despesas)
├── services/ (futuro - regras de negócio)
├── routes/ (futuro - APIs)
└── scripts/
    ├── create_tables.py (gerador de SQL)
    └── create_tables.sql (SQL final)
```

---

## ⚠️ MODELOS OBSOLETOS (NÃO USAR)

As seguintes pastas contêm models antigos e **NÃO** devem ser usadas:
- ❌ `app/motochefe/_old_cadastro/`
- ❌ `app/motochefe/_old_entrada/`
- ❌ `app/motochefe/_old_estoque/`
- ❌ `app/motochefe/_old_saida/`
- ❌ `app/motochefe/_old_financeiro/`

**Motivo**: Estrutura antiga tinha problemas de normalização e falta de FKs.

---

## 🔄 PRÓXIMOS PASSOS

1. ✅ Criar tabelas no banco (via SQL)
2. ⏳ Implementar services (regras de negócio)
3. ⏳ Criar rotas/APIs
4. ⏳ Desenvolver telas/dashboards
5. ⏳ Testes automatizados

---

## 📞 SUPORTE

Para dúvidas sobre a estrutura, consulte:
- Este arquivo (`ESTRUTURA_BD.md`)
- Escopo original (`escopo.md`)
- Models em `app/motochefe/models/`

**Versão do documento**: 1.0.0
**Última atualização**: Outubro 2025
