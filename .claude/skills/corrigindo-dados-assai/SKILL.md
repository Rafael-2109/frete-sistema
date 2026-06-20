---
name: corrigindo-dados-assai
description: >-
  Skill WRITE de BACKFILL e CORRECAO MANUAL de dados do modulo Motos Assai (B2B
  Q.P.A.) — para o que os fluxos normais (upload PDF da NF, CCe, telas 1-a-1) NAO
  alcancam: carga historica em LOTE a partir de planilha Excel, eventos de estado
  com DATA RETROATIVA, cadastros (loja/modelo), itens de pedido ABERTO, gravar
  faturamento (NF Q.P.A.), alterar chassi em NF e registrar devolucao (NFd).
  Gatilhos: "fazer backfill das
  motos Assai", "a Rayssa mandou uma planilha de chassis para subir", "carregar
  historico de motos Q.P.A.", "corrigir o status/estado retroativo de uma moto",
  "marcar motos como demonstracao", "gravar o faturamento de uma NF Q.P.A. antiga",
  "alterar/corrigir o chassi numa NF Q.P.A.", "registrar a devolucao (NFd) de
  motos Q.P.A.", "cadastrar/corrigir loja ou modelo Assai". Tambem traz o MAPA do
  modulo (tabelas, relacoes, services, guard-rails)
  para o agente escrever scripts Python ad-hoc quando a skill nao cobrir. Sempre
  exige --user-id; dry-run e o default, so efetiva com --confirmar. NAO usar para
  operacao pontual do dia a dia de 1 chassi -> registrando-evento-moto-assai; nem
  para apenas consultar -> consultando-estoque-assai / rastreando-chassi-assai.
  Matriz USAR/NAO-USAR completa no corpo.
allowed-tools: Read, Bash, Glob, Grep, Write
---

# Corrigindo Dados Assai (WRITE — backfill / correcao manual)

Skill WRITE para **backfill e correcao manual** do modulo Motos Assai. Cobre o
que os fluxos normais nao alcancam: carga historica de chassis em lote (planilha
Excel), eventos de estado com **data retroativa**, cadastros, itens de pedido
ABERTO, **gravar faturamento (NF Q.P.A.)** e **alterar chassi em NF**. Reusa os
services do modulo (nunca SQL/UPDATE/DELETE cru) e respeita os guard-rails do
append-only e do faturamento lastreado.

## Indice
- [Quando usar / Quando NAO usar](#quando-usar--quando-nao-usar)
- [REGRAS CRITICAS](#regras-criticas)
- [Modos](#modos-exatamente-1-por-invocacao)
- [Decision Tree](#decision-tree)
- [Invocacao](#invocacao)
- [Exit Codes](#exit-codes)
- [Output JSON (exemplos)](#output-json-exemplos)
- [Quando a skill nao cobre: script ad-hoc](#quando-a-skill-nao-cobre-script-ad-hoc)
- [Skills relacionadas](#skills-relacionadas)

> **Antes de operar, leia o mapa do modulo** — `references/MAPA_MODULO.md`:
> maquina de status, FKs, services reutilizaveis, guard-rails e **template para
> escrever scripts ad-hoc** quando a skill nao cobrir um caso.

## Quando usar / Quando NAO usar

**USAR QUANDO:**
- "a Rayssa mandou uma planilha de chassis para subir", "fazer backfill das motos Assai"
- "carregar historico de motos Q.P.A. com data de chegada retroativa"
- "corrigir/mudar o estado de uma moto (PENDENTE/DISPONIVEL/...) retroativo"
- "marcar essas motos como DEMONSTRACAO"
- "cadastrar/corrigir loja ou modelo Assai" (ex: padronizar `numero` 014->14)
- "adicionar/editar/remover item de um pedido VOE ABERTO"
- "gravar o faturamento de uma NF Q.P.A. (subir o PDF)" / "baixar NF orfa num pedido"
- "alterar/corrigir o chassi numa NF Q.P.A." / "cancelar uma NF Q.P.A."

**NAO USAR PARA:**
- Operacao pontual do dia a dia de 1 chassi (montar/disponibilizar/separar agora) -> `registrando-evento-moto-assai`
- Apenas consultar estado/historico -> `consultando-estoque-assai` / `rastreando-chassi-assai`
- Conferir recibo Motochefe (wizard) -> `conferindo-recibo-assai`
- Carregamento fisico (escaneio Sep->NF) -> `carregando-motos-assai`
- Lojas HORA / pedidos Nacom tradicionais -> dominios diferentes

---

## REGRAS CRITICAS

### 1. --user-id OBRIGATORIO
Toda invocacao exige `--user-id <id>` com `pode_acessar_motos_assai()=True`
(admin ou flag `sistema_motos_assai` + status ativo). FK de autoria do evento.
Em backfill sem operador humano, use `74` (Claude) ou `1` (Rafael) — **nunca inventar**.

### 2. --confirmar OBRIGATORIO PARA EFETIVAR
Sem `--confirmar` = dry-run (exit 4): mostra o estado atual e o que faria (cadeia
de eventos prevista, linhas da planilha), sem mutar nada. Com `--confirmar` chama
os services e commita.

### 3. Append-only — correcao = NOVO evento
Estado da moto = ULTIMO evento. A skill so INSERE eventos (via service), **nunca**
UPDATE/DELETE. Para corrigir um estado errado, emita o evento compensatorio (com
`--ocorrido-em` retroativo se preciso).

### 4. Faturamento e lastreado, nao avulso
O proibido e o evento `FATURADA` **orfao** (sem `AssaiNfQpa` por tras) — quebra
devolucao/pos-venda/resumo. NAO significa "so via PDF": grave o faturamento pela
NF real, seja por **PDF** (`--importar-nf`) ou por **registro manual** sem PDF
(`--registrar-nf-manual`, dados em JSON) — em ambos a propria NF e o lastro. O
match (baixa do pedido) cria/usa a separacao FATURADA, que reflete na **logistica**
Nacom (embarque/entrega); o **financeiro** Q.P.A. continua isolado. `--definir-estado`
nunca sobe a FATURADA: seus alvos sao ESTOQUE/MONTADA/PENDENTE/DISPONIVEL/DEMONSTRACAO.

### 5. Idempotente
Re-rodar nao duplica: pula chassi cujo `status_efetivo` ja esta no alvo; eventos
sao tagueados `dados_extras.origem='backfill:corrigindo-dados-assai'`.

### 6. Lote = tudo-ou-nada
`--planilha-estado --confirmar` commita uma vez no fim; se qualquer linha der erro,
faz rollback e reporta TODAS as linhas problematicas (nada e persistido).

---

## Modos (exatamente 1 por invocacao)

| Modo | Args principais | Faz |
|------|-----------------|-----|
| `--criar-moto` | `--chassi` `--modelo-id`\|`--modelo` `[--cor --motor --ano --ocorrido-em]` | cria AssaiMoto + evento ESTOQUE (retroativo) |
| `--definir-estado` | `--chassi` `--estado` `[--ocorrido-em --motivo]` | leva o chassi ao estado-alvo via cadeia de eventos |
| `--cadastrar-loja` | `--campos '{json}'` | cria AssaiLoja (reusa `loja_service`) |
| `--corrigir-loja` | `--loja-id` `--campos '{json}'` | atualiza AssaiLoja |
| `--cadastrar-modelo` | `--campos '{json}'` | cria AssaiModelo |
| `--corrigir-modelo` | `--modelo-id` `--campos '{json}'` | atualiza AssaiModelo |
| `--item-pedido` | `--acao add\|edit\|remove` `[--pedido-id --loja-id --modelo-id --item-id --qtd --valor]` | item de pedido **ABERTO** |
| `--planilha-estado` | `--excel <path>` `[--criar-faltantes --motivo --coluna-*]` | carga em LOTE (modo principal) |
| `--importar-nf` | `--pdf <path>` | grava faturamento Q.P.A. do PDF + match |
| `--registrar-nf-manual` | `--nf-json '{...}'` | grava faturamento Q.P.A. **sem PDF** (dados em JSON) + match |
| `--corrigir-chassi-nf` | `--nf-id` `--de-chassi --para-chassi`\|`--pares-json` `[--numero-cce]` | troca chassi(s) em NF Q.P.A. |
| `--cancelar-nf` | `--nf-id` `--motivo` | cancela NF Q.P.A. (reverte FATURADA) |
| `--vincular-nf` | `--nf-id` `--pedido-id` | vincula NF NAO_RECONCILIADO ao pedido (CNPJ) |
| `--registrar-devolucao-nfd` | `--nf-id` `--numero-nfd` `--data-devolucao` `--motivo` `--chassi`\|`--chassis-json` | devolucao (NFd) de 1+ chassis de NF FATURADA: chassi volta PENDENTE + saldo do modelo retorna; NF original **NAO** cancelada. Anexos so via tela |

`--estado`: `ESTOQUE`, `MONTADA`, `PENDENTE`, `DISPONIVEL`, `DEMONSTRACAO` (cadeia
calculada do estado atual ate o alvo; PENDENTE/REVERTIDA exigem `--motivo>=3`).

---

## Decision Tree

| Pedido | Modo |
|--------|------|
| "sobe essa planilha de chassis (estoque/status)" | `--planilha-estado --excel <x> --criar-faltantes` |
| "cadastra o chassi X em estoque (chegou em <data>)" | `--criar-moto --chassi X --modelo-id N --ocorrido-em <data>` |
| "poe o chassi X como disponivel" | `--definir-estado --chassi X --estado DISPONIVEL` |
| "marca o chassi X como pendente (motivo)" | `--definir-estado --chassi X --estado PENDENTE --motivo "..."` |
| "essas 3 motos sao de demonstracao" | `--definir-estado ... --estado DEMONSTRACAO` (1 por chassi) |
| "padroniza o numero da loja 014->14" | `--corrigir-loja --loja-id N --campos '{"numero":"14"}'` |
| "adiciona item ao pedido VOE ABERTO" | `--item-pedido --acao add --pedido-id ... --loja-id ... --modelo-id ... --qtd ... --valor ...` |
| "grava o faturamento dessa NF (tenho o PDF)" | `--importar-nf --pdf <x>` |
| "grava o faturamento dessa NF (so tenho os dados, sem PDF)" | `--registrar-nf-manual --nf-json '{...}'` |
| "corrige o chassi errado na NF Y" | `--corrigir-chassi-nf --nf-id Y --de-chassi A --para-chassi B` |
| "vincula essa NF orfa ao pedido P" | `--vincular-nf --nf-id Y --pedido-id P` |
| "registra a devolucao (NFd) do(s) chassi(s) da NF Y" | `--registrar-devolucao-nfd --nf-id Y --numero-nfd <nfd> --data-devolucao <data> --motivo "..." --chassi X` (ou `--chassis-json '["X","Z"]'`) |
| algo que nenhum modo cobre | escreva script ad-hoc (ver `references/MAPA_MODULO.md` secao 7) |

---

## Invocacao

```bash
cd /home/rafaelnascimento/projetos/frete_sistema
source .venv/bin/activate
SK=.claude/skills/corrigindo-dados-assai/scripts/corrigindo_dados_assai.py

# Dry-run (preview) — SEMPRE rode primeiro
python $SK --planilha-estado --excel /caminho/planilha.xlsx --criar-faltantes \
    --motivo "carga historica" --user-id 74

# Efetivar
python $SK --planilha-estado --excel /caminho/planilha.xlsx --criar-faltantes \
    --motivo "carga historica" --user-id 74 --confirmar
```

Output: JSON em stdout.

---

## Exit Codes

| Code | Significado |
|------|-------------|
| 0 | Sucesso (efetivado) |
| 1 | Erro de validacao (dado invalido / estado-alvo proibido / arg faltando / lote com erro) |
| 2 | Erro de infra (DB, app boot, leitura de arquivo) |
| 3 | Sem autorizacao (`pode_acessar_motos_assai`=False ou usuario inexistente) |
| 4 | Dry-run preview (sem `--confirmar`) |
| 5 | Conflito (UNIQUE / chassi em estado do fluxo de venda / NF ja importada) |

---

## Output JSON (exemplos)

### Dry-run `--definir-estado` (cadeia prevista)
```json
{
  "dry_run": true, "modo": "definir-estado", "chassi": "LA25...",
  "status_efetivo_atual": "ESTOQUE", "alvo": "DISPONIVEL",
  "cadeia_eventos": ["MONTADA", "DISPONIVEL"], "exit_code": 4
}
```

### Sucesso `--definir-estado --confirmar`
```json
{
  "ok": true, "modo": "definir-estado", "chassi": "LA25...",
  "de": "ESTOQUE", "para": "DISPONIVEL",
  "eventos": [{"tipo": "MONTADA", "evento_id": 901}, {"tipo": "DISPONIVEL", "evento_id": 902}],
  "exit_code": 0
}
```

### Idempotente (ja no alvo)
```json
{ "ok": true, "modo": "definir-estado", "chassi": "LA25...",
  "skipped": true, "motivo_skip": "ja esta em DISPONIVEL", "exit_code": 0 }
```

### Estado-alvo proibido (faturamento)
```json
{
  "ok": false, "tipo_erro": "validacao", "exit_code": 1,
  "erro": "estado-alvo 'FATURADA' nao e operavel por backfill. ... suba a NF real."
}
```

### Planilha (dry-run, resumo + linhas)
```json
{
  "dry_run": true, "modo": "planilha-estado", "fonte": "planilha.xlsx",
  "resumo": {"linhas": 3, "criadas": 2, "estado_aplicado": 2, "puladas": 0, "erros": 0, "sem_status": 1},
  "linhas": [{"chassi": "...", "status": "ok", "alvo": "DISPONIVEL", "eventos_previstos": ["ESTOQUE","MONTADA","DISPONIVEL"]}],
  "exit_code": 4
}
```

---

## Quando a skill nao cobre: script ad-hoc

Casos fora dos 13 modos (ex.: reconciliacao com regra propria, carga com
cronologia fina por evento) sao resolvidos com um **script Python sob medida**
reusando os services. O agente web **escreve o script em `/tmp/` via Write**
(`permissions.py` so' libera Write/Edit em `/tmp` — fail-closed, NUNCA toca codigo
de producao) e o executa via **Bash**; no Claude Code (dev/4-maos) cria-se direto
em `scripts/migrations/`. O template seguro, o mapa de tabelas/relacoes e os
guard-rails estao em `references/MAPA_MODULO.md` (secao 7). Regra: dry-run default,
reusar services (nunca SQL cru / DELETE de evento), commit unico no fim, nunca
inventar usuario.

---

## Skills relacionadas

| Skill | Quando |
|-------|--------|
| `registrando-evento-moto-assai` | transicao pontual do dia a dia (1 chassi, agora) |
| `consultando-estoque-assai` / `rastreando-chassi-assai` | consultar (READ) |
| `conferindo-recibo-assai` | conferencia de recibo (wizard) |
| `carregando-motos-assai` | carregamento fisico (Sep->NF) |
