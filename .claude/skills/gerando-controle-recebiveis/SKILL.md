---
name: gerando-controle-recebiveis
description: >-
  Gera a planilha de CONTROLE DE TITULOS A RECEBER do sistema (contas_a_receber,
  sem upload): aba Titulos (Situacao CONFIRMADO/Vencido/Em Aberto) + aba Vencidos
  por GESTOR, formatacao contabil. Gatilhos: "controle/planilha de recebiveis",
  "titulos vencidos por gestor", "minha carteira de cobranca", "contas a receber
  vencidas". Anti: baixar/conciliar titulo -> executando-odoo-financeiro;
  rastrear 1 NF -> rastreando-odoo.
allowed-tools: Read, Bash, Glob, Grep
---

# Gerando Controle de Recebiveis

Gera, **a partir do sistema** (nao de upload), a planilha de controle de titulos a
receber que o financeiro usa para acompanhar cobranca — equivalente ao controle que
era montado a mao conciliando o extrato do Banco Grafeno.

## Quando usar

O usuario quer o controle/planilha de **titulos a receber**: status de pagamento,
**vencidos por gestor de carteira**, valores em aberto, para cobranca. Origem 100%
do banco — o usuario **nao precisa anexar** base/extrato/relatorio.

## Como funciona (determinístico)

Fonte: `contas_a_receber` (dados do Odoo enriquecidos). Para cada titulo:

- **Situacao** (derivada): `CONFIRMADO` se `parcela_paga`; `Vencido` se venceu e nao
  pago; `Em Aberto` se ainda a vencer.
- **Vendedor**: de `entregas_monitoradas` (via `entrega_monitorada_id`).
- **Gestor de carteira**: `equipe_vendas` do Odoo (ex.: "VENDA INTERNA DENISE"),
  resolvido pelo faturamento mais recente do mesmo CNPJ.

Saida: `.xlsx` com aba **Titulos** (escopo todo) + aba **Vencidos** (so vencidos,
agrupados por gestor, com subtotal por grupo e total geral), formatacao contabil
(datas dd/mm/aaaa, valores R$).

## Uso

```bash
# Padrao (ultimos 12 meses de vencimento, todos os clientes):
python .claude/skills/gerando-controle-recebiveis/scripts/gerar_controle_recebiveis.py \
  --session-id "<session_id_do_agente>"

# Por gestor de carteira:
python ... --gestor "DENISE" --session-id "<sid>"

# Por cliente (CNPJ/raiz ou nome — repetivel) e so vencidos:
python ... --cliente "BORGES" --cliente "42385121" --apenas-vencidos --session-id "<sid>"

# Por empresa (1=FB, 2=SC, 3=CD) e janela de vencimento:
python ... --empresa 3 --desde 2026-01-01 --session-id "<sid>"
```

Retorno (stdout JSON): `{sucesso, arquivo, url, resumo}`. Entregue ao usuario a `url`
de download (`/agente/api/files/<sid>/<arquivo>`).

> **IMPORTANTE — passar o `--session-id` real do agente** (nao 'default'), senao o
> download cai na pasta errada e volta 404 (gotcha #787).

## Limite conhecido (MVP)

`CONFIRMADO` vem de `parcela_paga` do **Odoo**. Pagamentos recebidos no **extrato
Grafeno** mas ainda **nao baixados** no Odoo aparecem como Vencido/Em Aberto (a
conciliacao automatica do Grafeno esta parada desde jan/2026). Se o usuario apontar
um titulo "ja pago" marcado como vencido, e esse gap — encaminhar para reativar a
conciliacao do extrato Grafeno, nao tratar como erro da planilha.

## Detalhes de scripts

Ver [SCRIPTS.md](SCRIPTS.md).
