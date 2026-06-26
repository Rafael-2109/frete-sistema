---
name: consultando-cliente-odoo
description: >-
  READ-only de clientes (res.partner) AO VIVO no Odoo: busca por CNPJ/nome/cidade, contagem de
  ativos, pedidos por vendedor (sale.order). Usar: "dados do cliente X no Odoo", "quantos clientes
  ativos", "clientes do vendedor Z", "ranking por vendedor". NAO: cnpj/nome que ja esta no DB
  local -> consultando-sql; rastrear NF/PO -> rastreando-odoo.
allowed-tools: Read, Bash, Glob, Grep
---

# consultando-cliente-odoo

READ-only de `res.partner` (e agregacao de `sale.order`) **direto no Odoo ao vivo**, via
`.claude/skills/consultando-cliente-odoo/scripts/consultar_clientes.py`. Sem `--dry-run`/`--confirmar`:
e' sempre leitura (`search_read` / `search_count` / `read_group`), nunca escreve.

## Indice

- [Quando usar / Quando NAO usar](#quando-usar--quando-nao-usar)
- [Modos (atomos READ)](#modos-atomos-read)
- [Constantes](#constantes)
- [Receitas (pergunta -> args)](#receitas-pergunta---args)
- [Exemplos](#exemplos)
- [Saida](#saida)
- [Armadilhas](#armadilhas)
- [Validacao](#validacao)

## Quando usar / Quando NAO usar

| USAR QUANDO (gatilhos) | NAO USAR PARA | Por que / use |
|---|---|---|
| "dados cadastrais do cliente X no Odoo" (CNPJ, IE, cidade, contato) | dados que ja estao no banco LOCAL (cnpj_cliente, nome_cliente em carteira/faturamento) | **consultando-sql** — mais barato, sem XML-RPC |
| "quantos clientes ativos no Odoo", "clientes de <cidade>" | rastrear NF / PO / pedido de venda de um cliente | **rastreando-odoo** (fluxo documental) |
| "clientes do vendedor Z", "ranking de pedidos por vendedor" | CRIAR / EDITAR cliente, mudar vendedor | WRITE — feito na web, **nao** pelo agente |
| "customer_rank / data de criacao / esta ativo?" (so existe no Odoo) | estoque de produto / quants | **consultando-quant-odoo** |
| cross-ref rapido cliente -> ultimas vendas | analise P1-P7 da carteira | **analista-carteira** |

## Modos (atomos READ)

| `--modo` | O que faz | Metodo Odoo |
|---|---|---|
| `clientes` (default) | busca/lista clientes por filtro + total | `search_count` + `search_read` em `res.partner` |
| `detalhes` | cadastro completo de UM cliente + ultimas vendas | `search_read` `res.partner` + `sale.order` |
| `por-vendedor` | agrupa pedidos por vendedor (valor + qtd) | `read_group` em `sale.order` por `user_id` |

**Contrato** (todos os modos): `input` = flags CLI; `output` = JSON (ou tabela) JSON-serializavel;
`pre-condicoes` = conexao Odoo viva (`get_odoo_connection`); `pos-condicoes` = nenhuma (read);
`status` = sempre OK (lista vazia se nada casar).

## Constantes

- **Companies** (`--company-id`): `1=FB`, `3=SC`, `4=CD`, `5=LF` (IDS_FIXOS.md). NAO confundir com o
  "CD=34" de documentos financeiros (aquele NAO e' company_id do Odoo).
- **CNPJ e' formatado no Odoo** (`18.467.441/0001-63`). A skill ja reconstroi a mascara a partir
  dos digitos — pode passar `--cnpj 18467441000163`, `--cnpj 184674` (parcial) ou ja formatado.
- **Filtros default**: so' `active=True` e `customer_rank>0` (e' cliente). Use `--incluir-inativos`
  e/ou `--todos` (inclui fornecedores/contatos) para afrouxar.
- **Robustez de schema**: o script descobre via `fields_get` quais campos existem em `res.partner`
  antes de pedi-los — campos opcionais ausentes na instancia nao quebram a consulta.

## Receitas (pergunta -> args)

| Preciso de... | Args |
|---|---|
| Contar clientes ativos | `--apenas-total` |
| Cliente por CNPJ (completo ou parcial) | `--cnpj 18467441000163` |
| Clientes de uma cidade | `--cidade "Goiania" --limit 50` |
| Buscar por nome/razao | `--nome "ATACADAO"` |
| Cliente de UMA empresa do grupo | `--company-id 5` (LF) |
| Detalhe + ultimas vendas | `--modo detalhes --cnpj <cnpj>` (ou `--cliente-id <id>`) |
| Quanto cada vendedor vendeu (confirmado) | `--modo por-vendedor --confirmados` |
| Ranking de vendedor numa empresa, desde data | `--modo por-vendedor --company-id 1 --confirmados --desde 2026-01-01` |

## Exemplos

```bash
SK=.claude/skills/consultando-cliente-odoo/scripts/consultar_clientes.py

# Contagem de clientes ativos
python "$SK" --apenas-total

# Clientes de Goiania (JSON)
python "$SK" --cidade "Goiania" --limit 50 --json

# Detalhe de um cliente por CNPJ + ultimas 10 vendas
python "$SK" --modo detalhes --cnpj 18467441000163 --json

# Ranking de pedidos por vendedor na FB, confirmados
python "$SK" --modo por-vendedor --company-id 1 --confirmados --json
```

> Em batch (varias chamadas), adicione `--quiet`. Se houver outra execucao concorrente do mesmo
> script, use `--forcar-concorrencia` (read-only — sem risco de duplicar escrita).

## Saida

`--formato tabela` (default, legivel) ou `--formato json` / `--json` (estruturado, para
encadear/raciocinar). Many2one vem como `{"id": N, "nome": "..."}`; ausente vem `null`.

## Armadilhas

- **CNPJ por digitos puros nao casa** o campo formatado — a skill ja trata, mas se voce escrever
  query Odoo ad-hoc, lembre da mascara (`_fmt_cnpj_parcial` no script).
- **`l10n_br_cnpj` vs `l10n_br_cpf`**: pessoa juridica usa `l10n_br_cnpj`; o `--cnpj` busca no campo
  CNPJ. Para PF, o campo e' `l10n_br_cpf` (exposto no output como `cpf`).
- **`por-vendedor` sem `--confirmados`** conta TODOS os estados (inclui `draft`/`cancel`). Para
  faturamento real use `--confirmados` (state in `sale`,`done`).
- A propria empresa do grupo aparece como `res.partner` (ex.: "LA FAMIGLIA - LF") com
  `customer_rank` alto mas sem `sale.order` proprias — e' esperado.

## Validacao

Smoke ao vivo (READ) executado na criacao (2026-06-25): `--apenas-total` = 2708 clientes ativos;
`--cidade Goiania` = 13; `--modo detalhes --cnpj 18467441000163` = LA FAMIGLIA - LF (id 35);
`--modo por-vendedor --company-id 1 --confirmados` = 10 vendedores (top R$ 2.32M). Os 3 modos OK.
