# Esquema das Tabelas Principais

Este documento descreve as tabelas do banco de dados utilizadas pelo agente logistico.

---

## CarteiraPrincipal

**Proposito:** Pedidos originais com saldo pendente (fonte de verdade para demanda)

**Tabela:** `carteira_principal`

**Campos principais:**
| Campo | Tipo | Descricao |
|-------|------|-----------|
| num_pedido | String(50) | Numero do pedido (index) |
| cod_produto | String(50) | Codigo do produto (index) |
| qtd_produto_pedido | Numeric(15,3) | Quantidade original |
| qtd_saldo_produto_pedido | Numeric(15,3) | Saldo pendente (o que falta enviar) |
| preco_produto_pedido | Numeric(15,2) | Preco unitario |
| cnpj_cpf | String(20) | CNPJ/CPF do cliente (index) |
| raz_social_red | String(100) | Nome do cliente (reduzido) |
| forma_pgto_pedido | String | Forma de pagamento |
| data_entrega_pedido | Date | Data de entrega solicitada |
| nome_cidade | String(100) | Cidade do cliente |
| cod_uf | String(2) | UF do cliente |
| cep_endereco_ent | String(10) | CEP de entrega |

**Regras:**
- `qtd_saldo_produto_pedido > 0` significa item pendente
- Bonificacao: `forma_pgto_pedido LIKE 'Sem Pagamento%'`

---

## Separacao

**Proposito:** Itens reservados/separados para envio (projeta saida de estoque)

**Tabela:** `separacoes`

**Campos principais:**
| Campo | Tipo | Descricao |
|-------|------|-----------|
| separacao_lote_id | String(50) | ID do lote de separacao |
| num_pedido | String(50) | Numero do pedido |
| cod_produto | String(50) | Codigo do produto |
| qtd_saldo | Float | Quantidade separada |
| valor_saldo | Float | Valor separado |
| expedicao | Date | Data de expedicao planejada |
| agendamento | Date | Data de agendamento |
| status | String(20) | Status: PREVISAO, ABERTO, COTADO, EMBARCADO, FATURADO |
| sincronizado_nf | Boolean | True = faturado (tem NF) |
| cnpj_cpf | String(20) | CNPJ do cliente |
| raz_social_red | String(255) | Nome do cliente |
| nome_cidade | String(100) | Cidade |
| cod_uf | String(2) | UF |

**Regras criticas:**
- `sincronizado_nf = False` -> Item aparece na carteira, projeta estoque
- `sincronizado_nf = True` -> Faturado, NAO projeta estoque
- `status = 'PREVISAO'` -> Pre-separacao (ignorado pela VIEW Pedido)
- `status = 'ABERTO'` -> Separado, nao roteirizado

---

## MovimentacaoEstoque

**Proposito:** Movimentos de entrada/saida de estoque

**Tabela:** `movimentacao_estoque`

**Campos principais:**
| Campo | Tipo | Descricao |
|-------|------|-----------|
| cod_produto | String(50) | Codigo do produto |
| qtd_movimentacao | Float | Quantidade (+ entrada, - saida) |
| tipo_movimentacao | String | ENTRADA, SAIDA, AJUSTE, COMPRA |
| data_movimentacao | DateTime | Data/hora da movimentacao |
| ativo | Boolean | Se o registro esta ativo |

**Calculo de estoque atual:**
```sql
SELECT SUM(qtd_movimentacao)
FROM movimentacao_estoque
WHERE cod_produto = ? AND ativo = True
```

---

## ProgramacaoProducao

**Proposito:** Producoes futuras planejadas (entrada de estoque futura)

**Tabela:** `programacao_producao`

**Campos principais:**
| Campo | Tipo | Descricao |
|-------|------|-----------|
| cod_produto | String(50) | Codigo do produto |
| data_programacao | Date | Data prevista da producao |
| qtd_programada | Float | Quantidade a ser produzida |
| linha_producao | String(50) | Linha de producao |
| status | String | Status da programacao |

---

## CadastroPalletizacao

**Proposito:** Cadastro de produtos com dados de palletizacao e categorias

**Tabela:** `cadastro_palletizacao`

**Campos principais:**
| Campo | Tipo | Descricao |
|-------|------|-----------|
| cod_produto | String(50) | Codigo do produto (unique) |
| nome_produto | String(255) | Nome/descricao do produto |
| palletizacao | Float | Fator de conversao para pallets |
| peso_bruto | Float | Peso bruto unitario |
| categoria_produto | String(50) | Categoria (ex: CONSERVAS) |
| subcategoria | String(50) | Subcategoria (ex: AZEITONA) |
| tipo_materia_prima | String(50) | Materia-prima (ex: VERDE) |
| tipo_embalagem | String(50) | Embalagem (ex: VIDRO, POUCH) |
| linha_producao | String(50) | Linha de producao associada |

**Uso:** Buscar produtos por nome ou caracteristicas
```sql
SELECT * FROM cadastro_palletizacao
WHERE nome_produto ILIKE '%palmito%'
```

---

## ContatoAgendamento

**Proposito:** Exigencia de agendamento por cliente (CNPJ)

**Tabela:** `contatos_agendamento`

**Campos principais:**
| Campo | Tipo | Descricao |
|-------|------|-----------|
| cnpj | String(20) | CNPJ do cliente |
| forma | String(50) | Forma de agendamento |
| contato | String(255) | Usuario/telefone/email |
| observacao | String(255) | Observacoes |

**Valores de `forma`:**
- `'SEM AGENDAMENTO'` ou NULL -> Nao exige agendamento
- `'Portal'` -> Agendamento via portal
- `'Telefone'` -> Agendamento por telefone
- `'E-mail'` -> Agendamento por email
- `'WhatsApp'` -> Agendamento por WhatsApp

---

## CidadeAtendida

**Proposito:** Lead time por transportadora/cidade

**Tabela:** `cidades_atendidas`

**Campos principais:**
| Campo | Tipo | Descricao |
|-------|------|-----------|
| cidade_id | Integer | FK para tabela cidades |
| codigo_ibge | String(10) | Codigo IBGE da cidade |
| transportadora_id | Integer | FK para transportadoras |
| nome_tabela | String(50) | Nome da tabela de frete |
| lead_time | Integer | Dias para entrega |
| uf | String(2) | UF da cidade |

**Uso:** Calcular prazo de entrega
```sql
SELECT t.razao_social, c.lead_time
FROM cidades_atendidas c
JOIN transportadoras t ON t.id = c.transportadora_id
WHERE c.codigo_ibge = ?
ORDER BY c.lead_time ASC
```

---

## CadastroSubRota

**Proposito:** Mapeamento de cidade para sub-rota

**Tabela:** `cadastro_sub_rotas`

**Campos principais:**
| Campo | Tipo | Descricao |
|-------|------|-----------|
| cod_uf | String(2) | UF |
| nome_cidade | String(100) | Nome da cidade |
| sub_rota | String(50) | Codigo da sub-rota |

**Uso:** Identificar sub-rota para consolidacao
```sql
SELECT sub_rota FROM cadastro_sub_rotas
WHERE cod_uf = ? AND nome_cidade ILIKE ?
```

---

## Servico: ServicoEstoqueSimples

**Localizacao:** `app/estoque/services/estoque_simples.py`

**Metodos disponiveis:**
```python
ServicoEstoqueSimples.calcular_estoque_atual(cod_produto)
# Retorna: float (estoque atual)

ServicoEstoqueSimples.calcular_projecao(cod_produto, dias)
# Retorna: {estoque_atual, projecao[], dia_ruptura}

ServicoEstoqueSimples.validar_disponibilidade(cod_produto, qtd, data)
# Retorna: {disponivel: bool, falta: float}

ServicoEstoqueSimples.calcular_multiplos_produtos(cod_produtos, dias)
# Retorna: {cod_produto: projecao}
```
