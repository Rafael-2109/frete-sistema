# Referencia Tecnica - Gerindo Expedicao

Documentacao tecnica das tabelas, campos e constantes utilizadas pelos scripts.

## Tabelas Principais

### CarteiraPrincipal

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

---

### Separacao

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

### CadastroPalletizacao

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

### ContatoAgendamento

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

### CidadeAtendida

**Tabela:** `cidade_atendida`
**Proposito:** Transportadoras que atendem cada cidade com lead time

| Campo | Tipo | Descricao |
|-------|------|-----------|
| `codigo_ibge` | String(10) | Codigo IBGE |
| `transportadora_id` | Integer | ID da transportadora |
| `nome_tabela` | String(50) | Nome da tabela de frete |
| `lead_time` | Integer | Dias de transito |

---

### MovimentacaoEstoque

**Tabela:** `movimentacao_estoque`
**Proposito:** Movimentacoes de estoque (entradas e saidas)

| Campo | Tipo | Descricao |
|-------|------|-----------|
| `cod_produto` | String(50) | Codigo do produto |
| `qtd` | Numeric | Quantidade (+ entrada, - saida) |
| `data_movimentacao` | DateTime | Data da movimentacao |
| `tipo_movimentacao` | String | Tipo (PRODUCAO, VENDA, etc) |
| `local_movimentacao` | String | Local/linha |

---

## Grupos Empresariais

Prefixos CNPJ para identificacao de grupos:

```python
GRUPOS_EMPRESARIAIS = {
    'atacadao': ['93.209.76', '75.315.33', '00.063.96'],
    'assai': ['06.057.22'],
    'tenda': ['01.157.55']
}
```

---

## Constantes de Negocio

```python
# Limites para carga direta (exige agendamento)
LIMITE_PALLETS_CARGA_DIRETA = 26
LIMITE_PESO_CARGA_DIRETA = 20000  # kg

# Limites para envio parcial obrigatorio
LIMITE_PALLETS_ENVIO_PARCIAL = 30
LIMITE_PESO_ENVIO_PARCIAL = 25000  # kg

# Regras de parcial
LIMITE_FALTA_PARCIAL_AUTO = 0.10        # 10%
LIMITE_FALTA_CONSULTAR = 0.20           # 20%
DIAS_DEMORA_PARA_PARCIAL = 3
VALOR_MINIMO_CONSULTAR_COMERCIAL = 10000
VALOR_PEDIDO_PEQUENO = 15000
```

---

## UFs para Regras de Expedicao

```python
# SC/PR com carga direta > 2.000kg = D-2
UFS_CARGA_DIRETA_D2 = ['SC', 'PR']
LIMITE_PESO_CARGA_DIRETA_SC_PR = 2000  # kg
```

---

## Leadtimes de Planejamento

### Com data_entrega_pedido definida

| Destino | Expedicao |
|---------|-----------|
| SC/PR (>2.000kg) | data_entrega_pedido - 2 dias uteis |
| SP | data_entrega_pedido - 1 dia util |

### Necessita de agendamento

| Campo | Calculo |
|-------|---------|
| Expedicao | D+3 |
| Agendamento sugerido | D+3 + leadtime |

### Outros casos

| Expedicao |
|-----------|
| D+1 |

---

## Calculos de Estoque

### Estoque Atual
```python
estoque_atual = ServicoEstoqueSimples.calcular_estoque_atual(cod_produto)
```

### Projecao de Estoque
```python
projecao = ServicoEstoqueSimples.calcular_projecao(cod_produto, dias=28)
# Retorna: {
#   'dia_ruptura': 'YYYY-MM-DD' ou None,
#   'projecao': [{'data': '...', 'saldo_final': N}, ...]
# }
```

---

## Calculos de Separacao

### Peso e Pallets
```python
peso = qtd_saldo * peso_bruto  # Do CadastroPalletizacao
pallet = qtd_saldo / palletizacao  # Do CadastroPalletizacao
```

### Rota e Sub-rota
```python
from app.carteira.utils.separacao_utils import buscar_rota_por_uf, buscar_sub_rota_por_uf_cidade

rota = buscar_rota_por_uf(cod_uf)
sub_rota = buscar_sub_rota_por_uf_cidade(cod_uf, nome_cidade)
```

---

## Identificacao de Gestores

Extraido do campo `equipe_vendas`:

| Valor no Campo | Gestor | Canal |
|----------------|--------|-------|
| VENDA EXTERNA ATACADAO | Junior | WhatsApp |
| VENDA EXTERNA SENDAS SP | Junior | WhatsApp |
| VENDA EXTERNA MILER | Miler | WhatsApp |
| VENDA EXTERNA FERNANDO | Fernando | WhatsApp |
| VENDA EXTERNA JUNIOR | Junior | WhatsApp |
| VENDA INTERNA DENISE | Denise | Teams |

---

## Normalizacao de Texto

Para comparacoes de nomes (cidades, produtos):

```python
from resolver_entidades import normalizar_texto

normalizar_texto("Itanhaem")  # -> "itanhaem"
normalizar_texto("Sao Paulo")  # -> "sao paulo"
```

---

## Glossario - Termos do Dominio

| Termo | Significado |
|-------|-------------|
| Matar pedido | Completar 100% do pedido |
| Ruptura | Falta de estoque para atender demanda |
| Falta absoluta | Estoque < demanda (mesmo sem outros pedidos) |
| Falta relativa | Estoque comprometido com outros pedidos |
| RED | Redespacho via SP |
| FOB | Cliente coleta no CD |
| CIF | Nacom entrega no cliente |
| BD IND | Balde Industrial |
| D-2, D-1, D0 | Dias relativos a data de entrega |
| BD | Balde |

