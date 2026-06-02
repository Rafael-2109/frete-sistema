# Troca de NF — Atacadão 881 (operação temporária)

**Criado**: 2026-06-01 · **Cliente**: ATACADAO 881 (CNPJ 93.209.765/0364-99) · **Empresa**: CD (Odoo company_id=4)

## Objetivo

Viabilizar uma **troca de NF** das 2 notas faturadas para o Atacadão 881, ajustando o estoque
do CD temporariamente:

1. **Tarefa 1 (feita 01/06)** — transferir o saldo das 2 NFs de `CD/Indisponivel` (lote `MIGRAÇÃO`)
   → `CD/Estoque` (lote `P-01/06`), deixando o estoque **disponível** para refaturar.
2. **Tarefa 2 (este cron)** — quando cada NF for **revertida** (entrada via NF de crédito), devolver
   o saldo para `CD/Indisponivel` (lote `MIGRAÇÃO`), desfazendo a Tarefa 1.

## NFs e quantidades (qtds originais)

| NF | Itens | Qtd total | Faturada | Pedido |
|----|------:|----------:|----------|--------|
| 146390 | 21 | 238 cx | 25/03/2026 | VCD2667970 |
| 146608 | 3 | 37 cx | 31/03/2026 | VCD2667970 |

Lista completa produto→qtd: ver `NFS` em `verificar_reversao_e_devolver.py`.

## Como a reversão é detectada

Quando uma NF é revertida por nota de crédito, o sistema grava em `movimentacao_estoque` (Render PROD):

```
tipo_movimentacao = 'ENTRADA'
local_movimentacao = 'REVERSAO'
numero_nf          = <NF ORIGINAL>     (ex: 146390)
status_nf          = 'REVERTIDA'
observacao         = 'Reversao NF <orig> via NC <ref>'
qtd_movimentacao   > 0                 (por produto)
```

**Critério (decisão do usuário)**: granularidade **"NF inteira"** — só devolve quando **todos**
os produtos da NF tiverem `qtd_revertida >= qtd_original` (NF 100% revertida). Devolve as qtds
originais inteiras.

## Execução (decisão do usuário): automática, "tanto faz o lote"

Ao detectar 100% revertida, o cron executa a volta **automaticamente** (`transferir.py --confirmar`).

**Estratégia de lote** (decisão do usuário — "tanto faz o lote, desde que automático"): para cada
produto, baixa a qtd da NF de `CD/Estoque` consultando os quants **ao vivo** e consumindo:
1. o lote `P-01/06` primeiro (o ajuste dedicado);
2. se faltar (caso a nova NF venha a consumir o `P-01/06`), completa dos **demais lotes** de
   `CD/Estoque` com saldo **livre**, do maior para o menor.

Destino sempre `CD/Indisponivel`/`MIGRAÇÃO`.

Salvaguardas:
- **planejamento + dry-run de cada movimento antes do real**;
- **não toca saldo reservado** — se não houver saldo **livre** suficiente em `CD/Estoque`, a NF é
  **abortada sem escrita** (nunca parcial) e o erro é logado para revisão manual;
- **Idempotência** via `estado_reversao.json` — uma NF devolvida nunca repete.

> Teste da cadeia sem reversão real (consulta de quants → plano → dry-run, nunca escreve):
> `python .../verificar_reversao_e_devolver.py --testar-devolucao [--nf 146390]`

## Fontes de dados

| O quê | Onde | Como |
|-------|------|------|
| Detecção de reversão | Render PROD | `DATABASE_URL_PROD` (.env) — **não** o localhost de teste |
| Volta no estoque | Odoo PROD | skill `transferindo-interno-odoo` (`transferir.py`, MODO D invertido) |

## Uso manual

```bash
cd /home/rafaelnascimento/projetos/frete_sistema && source .venv/bin/activate

# checagem (não escreve nada — só detecta e reporta):
python scripts/operacionais/troca_nf_atacadao881/verificar_reversao_e_devolver.py

# executa a volta quando detectar NF 100% revertida:
python scripts/operacionais/troca_nf_atacadao881/verificar_reversao_e_devolver.py --confirmar

# uma NF só / forçar reprocessamento (debug):
python .../verificar_reversao_e_devolver.py --confirmar --nf 146390 --force
```

## Crontab (instalado)

```cron
# Troca NF Atacadao 881 — verifica reversao e devolve ao Indisponivel (diario 11:30 BRT)
30 11 * * * cd /home/rafaelnascimento/projetos/frete_sistema && .venv/bin/python scripts/operacionais/troca_nf_atacadao881/verificar_reversao_e_devolver.py --confirmar >> /tmp/troca_nf_881.log 2>&1
```

Log: `/tmp/troca_nf_881.log`.

## Encerramento automático (auto-neutralização)

Quando **todas** as NFs forem devolvidas (`status: DEVOLVIDA`), o script:
1. cria `CONCLUIDO.flag` nesta pasta;
2. nas execuções seguintes vira **no-op** (não conecta em nada) — o cron deixa de agir
   mesmo sem remover a linha do crontab;
3. registra no log: `OPERACAO CONCLUIDA — ... Remover linha do crontab quando quiser`.

Ou seja, **não é preciso ação urgente**. A linha do crontab fica inócua. Para limpar de vez
(opcional): `sudo crontab -u rafaelnascimento -e` e remover a linha "Troca NF Atacadao 881".

> Notificação: o script **não** envia WhatsApp/e-mail. O sinal de conclusão é o
> `CONCLUIDO.flag` + o `estado_reversao.json` (status `DEVOLVIDA`) + o log. O Claude Code
> avisa o usuário na próxima conversa ao consultar o estado.

O script é idempotente: mesmo que continue rodando, NFs já devolvidas são puladas.

## Reversão da Tarefa 1 (rollback manual, se a troca for cancelada antes da reversão)

Para desfazer a Tarefa 1 sem esperar a reversão (cada produto):

```bash
python .claude/skills/transferindo-interno-odoo/scripts/transferir.py --quiet \
  --cod <COD> --empresa CD --qty <QTY> --loc-e-lote \
  --loc-origem 32 --loc-destino 31090 \
  --lote-origem 'P-01/06' --lote-destino 'MIGRAÇÃO' --confirmar
```
