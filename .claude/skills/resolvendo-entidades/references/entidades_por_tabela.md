<!-- doc:meta
tipo: reference
camada: L2
sot_de: —
hub: .claude/skills/resolvendo-entidades/SKILL.md
superseded_by: —
atualizado: 2026-06-02
-->
# Entidades por Tabela

> **Papel:** Entidades por Tabela.

## Indice

- [CLIENTE (CNPJ/Nome)](#cliente-cnpjnome)
  - [Formato do CNPJ](#formato-do-cnpj)
- [PRODUTO (cod_produto)](#produto-cod_produto)
  - [Cadastro Master](#cadastro-master)
- [PEDIDO (num_pedido)](#pedido-num_pedido)
  - [Formato do Pedido](#formato-do-pedido)
- [CIDADE/UF](#cidadeuf)
  - [Normalizacao](#normalizacao)
- [Uso nas Skills](#uso-nas-skills)
  - [resolver_grupo.py](#resolver_grupopy)
  - [resolver_cliente.py](#resolver_clientepy)
  - [resolver_produto.py](#resolver_produtopy)
  - [resolver_pedido.py](#resolver_pedidopy)
  - [resolver_cidade.py](#resolver_cidadepy)

Mapeamento de onde cada entidade aparece no sistema.

---

## CLIENTE (CNPJ/Nome)

| Tabela | Campo CNPJ | Campo Nome | Observacao |
|--------|------------|------------|------------|
| CarteiraPrincipal | cnpj_cpf | raz_social_red | Pedidos pendentes |
| Separacao | cnpj_cpf | raz_social_red | Pedidos em separacao |
| EmbarqueItem | cnpj | nome_cliente | Pedidos embarcados |
| Frete | cnpj_cpf | nome_cliente | Frete calculado |
| EntregasMonitoradas | cnpj_cliente | cliente | Status de entrega |
| NFDevolucao | cnpj_emitente | nome_emitente | Devolucoes recebidas |
| FaturamentoProduto | cnpj | cliente | NFs faturadas |

### Formato do CNPJ

O CNPJ nos campos segue formato com pontuacao: `XX.XXX.XXX/YYYY-ZZ`

Para grupos empresariais, usar prefixo: `XX.XXX.XX%`

---

## PRODUTO (cod_produto)

| Tabela | Campo | Observacao |
|--------|-------|------------|
| CadastroPalletizacao | cod_produto | Cadastro master (fonte de verdade) |
| CarteiraPrincipal | cod_produto | Demanda em carteira |
| Separacao | cod_produto | Em separacao |
| MovimentacaoEstoque | cod_produto | Entradas/saidas |
| UnificacaoCodigos | cod_produto | De-para codigos antigos |
| FaturamentoProduto | cod_produto | NFs faturadas |
| EstoqueReal | cod_produto | Posicao de estoque |

### Cadastro Master

Para buscar informacoes do produto, SEMPRE usar `CadastroPalletizacao`:

```python
# Campos importantes
CadastroPalletizacao.cod_produto       # Codigo unico
CadastroPalletizacao.nome_produto      # Nome completo
CadastroPalletizacao.tipo_materia_prima # CI, CF, AZ VF, etc.
CadastroPalletizacao.tipo_embalagem    # BD, VIDRO, POUCH, etc.
CadastroPalletizacao.categoria_produto # MEZZANI, CAMPO BELO, etc.
CadastroPalletizacao.ativo             # True = ativo
CadastroPalletizacao.produto_vendido   # True = vendido (nao intermediario)
```

---

## PEDIDO (num_pedido)

| Tabela | Campo | Observacao |
|--------|-------|------------|
| CarteiraPrincipal | num_pedido | Pedidos pendentes |
| Separacao | num_pedido | Pedidos em separacao |
| EmbarqueItem | num_pedido | Pedidos embarcados |
| FaturamentoProduto | num_pedido | NFs faturadas |

### Formato do Pedido

- **VCD**: Pedidos de venda (ex: VCD2565291)
- **VFB**: Pedidos bonificacao (ex: VFB123456)
- **SAL**: Pedidos saldo (ex: SAL789012)

---

## CIDADE/UF

| Tabela | Campo Cidade | Campo UF |
|--------|--------------|----------|
| CarteiraPrincipal | nome_cidade | cod_uf |
| Separacao | nome_cidade | cod_uf |
| EmbarqueItem | cidade | uf |
| EntregasMonitoradas | municipio | uf |

### Normalizacao

Cidades podem ter acentuacao variada. Usar normalizacao:
- "Itanhaém" = "itanhaem"
- "São Paulo" = "sao paulo"
- "PERUÍBE" = "peruibe"

---

## Uso nas Skills

### resolver_grupo.py
- Busca em: CarteiraPrincipal, Separacao, EntregasMonitoradas
- Campo: cnpj_cpf ou cnpj_cliente

### resolver_cliente.py
- Busca em: CarteiraPrincipal, Separacao, EntregasMonitoradas
- Campo: cnpj_cpf/raz_social_red ou cnpj_cliente/cliente

### resolver_produto.py
- Busca em: CadastroPalletizacao
- Campo: cod_produto, nome_produto, tipo_*, categoria_*

### resolver_pedido.py
- Busca em: CarteiraPrincipal, Separacao
- Campo: num_pedido

### resolver_cidade.py
- Busca em: CarteiraPrincipal, Separacao, EntregasMonitoradas
- Campo: nome_cidade/municipio, cod_uf/uf
