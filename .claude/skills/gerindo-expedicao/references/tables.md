# Tabelas - Gerindo Expedicao

Schemas resumidos das tabelas utilizadas pelos scripts desta skill.

> **Quando usar:** Consulte este arquivo quando precisar saber quais campos existem nas tabelas para construir queries ou entender os dados retornados pelos scripts.

---

## Indice

1. [CarteiraPrincipal](#carteiraprincipal)
2. [Separacao](#separacao)
3. [CadastroPalletizacao](#cadastropalletizacao)
4. [ContatoAgendamento](#contatoagendamento)
5. [CidadeAtendida](#cidadeatendida)
6. [MovimentacaoEstoque](#movimentacaoestoque)

---

## CarteiraPrincipal

**Tabela:** `carteira_principal`
**Proposito:** Pedidos originais com saldo pendente (fonte de verdade para demanda)

| Campo | Tipo | Descricao |
|-------|------|-----------|
| `num_pedido` | String(50) | Numero do pedido |
| `cod_produto` | String(50) | Codigo do produto |
| `nome_produto` | String(255) | Nome do produto |
| `qtd_produto_pedido` | Numeric(15,3) | Quantidade original |
| `qtd_saldo_produto_pedido` | Numeric(15,3) | Saldo disponivel |
| `preco_produto_pedido` | Numeric(15,2) | Preco unitario |
| `cnpj_cpf` | String(20) | CNPJ/CPF cliente |
| `raz_social_red` | String(100) | Razao Social reduzida |
| `nome_cidade` | String(100) | Cidade do cliente |
| `cod_uf` | String(2) | UF do cliente |
| `data_entrega_pedido` | Date | Data entrega negociada |
| `data_pedido` | Date | Data do pedido |
| `equipe_vendas` | String(100) | Equipe de vendas |
| `vendedor` | String(100) | Vendedor |
| `incoterm` | String(10) | Incoterm (CIF, FOB, RED) |
| `codigo_ibge` | String(10) | Codigo IBGE da cidade |
| `pedido_cliente` | String(100) | Pedido de Compra do Cliente |
| `forma_pgto_pedido` | String(100) | Forma de pagamento (usado para identificar bonificacao) |
| `observ_ped_1` | Text | Observacoes do pedido |
| `tags_pedido` | Text | Tags do Odoo em JSON: [{"name": "VIP", "color": 5}] |
| `cnpj_endereco_ent` | String(20) | CNPJ do endereco de entrega |
| `empresa_endereco_ent` | String(255) | Nome do local de entrega |
| `cep_endereco_ent` | String(10) | CEP de entrega |
| `bairro_endereco_ent` | String(100) | Bairro de entrega |
| `rua_endereco_ent` | String(255) | Rua de entrega |
| `endereco_ent` | String(20) | Numero do endereco |
| `telefone_endereco_ent` | String(20) | Telefone de entrega |

---

## Separacao

**Tabela:** `separacoes`
**Proposito:** Itens separados/reservados para expedicao

| Campo | Tipo | Descricao |
|-------|------|-----------|
| `separacao_lote_id` | String(50) | ID do lote de separacao |
| `num_pedido` | String(50) | Numero do pedido |
| `cod_produto` | String(50) | Codigo do produto |
| `qtd_saldo` | Float | Quantidade separada |
| `valor_saldo` | Float | Valor separado |
| `peso` | Float | Peso total |
| `pallet` | Float | Quantidade de pallets |
| `expedicao` | Date | Data de expedicao |
| `agendamento` | Date | Data de agendamento |
| `protocolo` | String(50) | Protocolo de agendamento |
| `status` | String(20) | Status (PREVISAO, ABERTO, COTADO, EMBARCADO) |
| `sincronizado_nf` | Boolean | Se ja foi faturado |
| `cnpj_cpf` | String(20) | CNPJ cliente |
| `raz_social_red` | String(255) | Razao Social |
| `nome_cidade` | String(100) | Cidade |
| `cod_uf` | String(2) | UF |
| `rota` | String(50) | Rota |
| `sub_rota` | String(50) | Sub-rota |

**REGRA CRITICA:**
- `sincronizado_nf=False` → Item aparece na carteira, projeta estoque
- `sincronizado_nf=True` → Foi faturado, NAO aparece na carteira

---

## CadastroPalletizacao

**Tabela:** `cadastro_palletizacao`
**Proposito:** Cadastro de produtos com informacoes de peso e palletizacao

| Campo | Tipo | Descricao |
|-------|------|-----------|
| `cod_produto` | String(50) | Codigo do produto |
| `peso_bruto` | Numeric | Peso bruto unitario |
| `palletizacao` | Numeric | Unidades por pallet |
| `tipo_materia_prima` | String | Tipo de MP (AZ, COG, etc) |
| `tipo_embalagem` | String | Tipo de embalagem (POUCH, BD, etc) |
| `categoria_produto` | String | Categoria/marca |

---

## ContatoAgendamento

**Tabela:** `contato_agendamento`
**Proposito:** Clientes que exigem agendamento

| Campo | Tipo | Descricao |
|-------|------|-----------|
| `cnpj` | String(20) | CNPJ do cliente |
| `forma` | String(50) | Forma de agendamento |

**Valores de `forma`:**
- `SEM AGENDAMENTO` - Nao precisa agendar
- Outros valores - Precisa agendar

---

## CidadeAtendida

**Tabela:** `cidade_atendida`
**Proposito:** Transportadoras que atendem cada cidade com lead time

| Campo | Tipo | Descricao |
|-------|------|-----------|
| `codigo_ibge` | String(10) | Codigo IBGE |
| `transportadora_id` | Integer | ID da transportadora |
| `nome_tabela` | String(50) | Nome da tabela de frete |
| `lead_time` | Integer | Dias de transito |

---

## MovimentacaoEstoque

**Tabela:** `movimentacao_estoque`
**Proposito:** Movimentacoes de estoque (entradas e saidas)

| Campo | Tipo | Descricao |
|-------|------|-----------|
| `cod_produto` | String(50) | Codigo do produto |
| `qtd` | Numeric | Quantidade (+ entrada, - saida) |
| `data_movimentacao` | DateTime | Data da movimentacao |
| `tipo_movimentacao` | String | Tipo (PRODUCAO, VENDA, etc) |
| `local_movimentacao` | String | Local/linha |
