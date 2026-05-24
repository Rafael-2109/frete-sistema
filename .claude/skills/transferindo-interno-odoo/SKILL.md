---
name: transferindo-interno-odoo
description: >-
  Skill WRITE (átomo C2) para TRANSFERIR saldo de estoque DENTRO de uma mesma
  empresa no Odoo (NÃO emite NF). Suporta 2 modos atômicos: (a) lote→lote na
  MESMA location (`--lote-origem` → `--lote-destino`); (b) location→location
  com o MESMO lote (`--loc-origem` → `--loc-destino`). Internamente delega a
  `ajustar_quant` 2x (reduz origem, aumenta destino), propagando
  `delta_esperado` para herdar o guard anti-bug CICLAMATO da Skill 1 (regra
  inviolável 11 do roadmap 2026-05-24). Usar quando o pedido é "transfere
  N un do lote A pro lote B", "move o saldo do lote MIGRAÇÃO para o lote
  canônico", "manda esse saldo pra Indisponível", "mesma empresa, sem NF".
  `--dry-run` é o DEFAULT; só efetiva com `--confirmar`.
  NÃO USAR PARA:
  - ajustar saldo de 1 quant (soma/zera/cria) → ajustando-quant-odoo
  - transferir saldo entre CÓDIGOS de produto → transferencia-saldo-codigo
  - transferir entre EMPRESAS diferentes (emite NF) → faturando-odoo/escriturando-odoo
  - cancelar reserva órfã ANTES de transferir → operando-reservas-odoo (skill 2.4)
  - operação que precisa de PICKING (recebimento, devolução) → operando-picking-odoo
  - só consultar/projetar saldo (não altera) → subagente gestor-estoque-producao
allowed-tools: Read, Bash, Glob, Grep
---

# transferindo-interno-odoo (WRITE — átomo C2)

Átomo de **transferência interna de estoque** no Odoo, dentro da mesma empresa.
Internamente é composição de 2 chamadas a `ajustar_quant` (Skill 1):
1. **Reduzir** quant origem (`delta=-qty`, `delta_esperado=-qty`)
2. **Aumentar** (criar se faltar) quant destino (`delta=+qty`, `delta_esperado=+qty`)

Cada passo herda TODOS os guards da Skill 1 (G002, G028, anti-negativar, anti-reserva,
`delta_esperado`). NÃO emite NF (inventory adjustment puro — gera 2 `stock.move`
auditáveis com origem "Physical Inventory").

Constituição: `app/odoo/estoque/CLAUDE.md`. Service: `app/odoo/estoque/scripts/transfer.py`.

---

## REGRAS CRÍTICAS

1. **`--dry-run` é o DEFAULT.** Sem `--confirmar`, simula ambos passos e mostra plano (exit 4). Sempre apresentar plano antes de `--confirmar`.
2. **`--confirmar` efetiva** no Odoo (2 writes + 2 `action_apply_inventory`). Reversível, mas confirme com o usuário antes.
3. **Verificar no Odoo após efetivar** (não confiar só no output) — operação viva.
4. **Empresas DIFERENTES exigem NF.** Esta skill é APENAS intra-empresa. Para inter-company use `faturando-odoo` (saída) + `escriturando-odoo` (entrada).

## Contrato (átomo componível)

```
objeto:        stock.quant (2 ajustes — composição de Skill 1)
input (modo lote→lote):
  --cod <default_code> --empresa <FB|CD|LF> [--local <id>]
  --qty <float positivo>
  --lote-origem <nome|VAZIO> --lote-destino <nome>
  [--resetar-reserva-origem] [--tolerancia-delta T] [--confirmar]
input (modo loc→loc):
  --cod <default_code> --empresa <FB|CD|LF>
  --qty <float positivo>
  --loc-origem <id> --loc-destino <id>
  [--lote <nome|VAZIO>] (mesmo lote nos 2 lados; default = sem lote)
  [--resetar-reserva-origem] [--tolerancia-delta T] [--confirmar]
output (JSON): {modo, chave{...}, resultado{
  status, qty_transferida, lot_id_origem, lot_id_destino,
  reducao_origem{...resultado ajustar_quant...},
  aumento_destino{...resultado ajustar_quant...},
  tempo_ms, erro?, location_id_origem?, location_id_destino?, lot_id?
}}
pré-condições:
  - produto existe (1 ativo p/ default_code); tracking != serial
  - lote-origem e lote-destino existem (lote-destino é criado se MIGRAÇÃO ou via wrapper v2)
  - origem tem qty livre >= qty solicitada (ou clamp por tolerancia 0.001)
pós-condições:
  - 2 stock.move 'Physical Inventory' (no --confirmar)
  - quant destino criado se faltar
gotchas-invariante (codificados no service transfer.py):
  - G021 (lot_id de empresa errada): TODA busca de lote filtra company_id
  - G022 (2 lotes MIGRACAO/produto): wildcard 3 grafias (MIGRAÇÃO/MIGRACAO/MIGRAÇAO),
    escolhe o de MAIOR saldo na loc alvo, ou cria canônico 'MIGRAÇÃO'
  - G027 (reserved_quantity vem de saída): default RESPEITA reserva;
    --resetar-reserva-origem zera ANTES do ajuste (defensivo, preserva picking)
  - G028 (consolidar_move_lines): herdado de ajustar_quant
  - G002 (lot.name search '=' instável): herdado de StockLotService (operador 'in')
  - G_proxy_vazio: 'P-15/05' = lote literal + também cobre quant sem lote (lot_id=False)
  - delta_esperado: propagado a CADA chamada (regra inviolável 11 pos-CICLAMATO)
  - G-TRANSFER-01 (bugs em fluxo_c, fluxo_b_vivas): criar_se_nao_existe retorna
    tuple (id, bool); a skill NUNCA usa o retorno como int direto.
modos:         --dry-run (default, exit 4) -> --confirmar (exit 0)
status:        EXECUTADO · DRY_RUN_OK · FALHA_REDUCAO · FALHA_AUMENTO ·
               FALHA_PRODUTO · FALHA_LOTE · FALHA_LOCAL · BLOQUEADO_SERIAL · FALHA_ODOO
```

## Receitas (caso real → args)

| Preciso de... | Args | Vinha do ad-hoc |
|---------------|------|-----------------|
| Transferir N un de lote A para lote B (mesma loc) | `--cod C --empresa E --qty N --lote-origem A --lote-destino B` | 10 emergenciais, 13 transf_migr, substituir_lote, padronizar_migracao |
| Mover lote MIGRAÇÃO para lote canônico | `--cod C --empresa E --qty N --lote-origem MIGRAÇÃO --lote-destino "MI 027-098/26"` | 10, 13 (446 linhas) |
| Mover saldo do estoque para Indisponível (mesmo lote) | `--cod C --empresa FB --qty N --lote MIGRAÇÃO --loc-origem 8 --loc-destino 31088` | mover_migracao_para_indisponivel |
| Consolidar 2 grafias de MIGRAÇÃO (MIGRACAO sem cedilha→MIGRAÇÃO com cedilha) | `--cod C --empresa E --qty N --lote-origem MIGRACAO --lote-destino MIGRAÇÃO` | padronizar_migracao |
| Devolver de Indisponível para Estoque (mesmo lote, locs diferentes) | `--cod C --empresa CD --qty N --lote MIGRAÇÃO --loc-origem 31090 --loc-destino 32` | mover_migracao reverse |
| Reduzir lote A com reserva órfã + transferir (RESETAR reserva primeiro) | `--cod C --empresa E --qty N --lote-origem A --lote-destino B --resetar-reserva-origem` | corrigir_reserved_negativo |

## Exemplos

```bash
SK=.claude/skills/transferindo-interno-odoo/scripts/transferir.py

# 1) dry-run (default): mover 35 un do lote MIGRAÇÃO para 'MI 027-098/26' em FB/Estoque
python "$SK" --cod 104000015 --empresa FB --qty 35.0 \
    --lote-origem 'MIGRAÇÃO' --lote-destino 'MI 027-098/26'

# 2) efetivar (após revisar o plano)
python "$SK" --cod 104000015 --empresa FB --qty 35.0 \
    --lote-origem 'MIGRAÇÃO' --lote-destino 'MI 027-098/26' --confirmar

# 3) mover saldo do mesmo lote MIGRAÇÃO de FB/Estoque (8) para FB/Indisponivel (31088)
python "$SK" --cod 104000015 --empresa FB --qty 1175.0 \
    --lote 'MIGRAÇÃO' --loc-origem 8 --loc-destino 31088 --confirmar

# 4) padronizar grafia MIGRACAO (sem cedilha) -> MIGRAÇÃO (com cedilha) no mesmo produto
python "$SK" --cod 210030325 --empresa FB --qty 66532.0 \
    --lote-origem 'MIGRACAO' --lote-destino 'MIGRAÇÃO' --confirmar

# 5) caso com reserva órfã na origem: resetar antes do ajuste
python "$SK" --cod 104000037 --empresa FB --qty 5.0 \
    --lote-origem 'MIGRAÇÃO' --lote-destino 'MI 074-177/25' \
    --resetar-reserva-origem --confirmar
```

## Armadilhas

- **Modo lote→lote XOR modo loc→loc** — você fornece (`--lote-origem` + `--lote-destino`) OU (`--loc-origem` + `--loc-destino`), nunca os dois.
- **`--qty` é SEMPRE positivo.** A redução de origem usa `delta=-qty` internamente; aumento de destino usa `delta=+qty`. Negativo levanta erro.
- **`--lote-origem == --lote-destino`** (e nada diferente entre eles) levanta `ValueError`. Idem `--loc-origem == --loc-destino`.
- **Lote destino MIGRAÇÃO** é resolvido com WILDCARD das 3 grafias (G022): se há 2 variantes (com/sem cedilha), consolida no de MAIOR saldo na loc; se nenhuma existe, cria a canônica `'MIGRAÇÃO'`.
- **Lote-origem inexistente** → `FALHA_REDUCAO` (reducao_origem.status=FALHA_QUANT_VAZIO). Verificar se o lote existe ANTES (usar `consultando-quant-odoo`).
- **Reserva ativa na origem**: por default a reducao RESPEITA reserva (se `qty_apos < reservada`, `FALHA_REDUCAO`). Para resetar: `--resetar-reserva-origem`. ATENÇÃO: não cancela picking — só limpa cache stale.
- **`--resetar-reserva-origem` em produção** — usar com cautela; se o picking estiver ATIVO (não fantasma), reservar de novo no `action_assign` futuro pode causar surpresa. Para cirurgia de ML órfãs use **skill 2.4 `operando-reservas-odoo`** ANTES desta.
- **tracking=serial** é bloqueado (`BLOQUEADO_SERIAL`).
- **Empresas diferentes** NÃO suportadas — só intra-empresa. Inter-company emite NF (use `faturando-odoo` + `escriturando-odoo`).
- **Quant origem com qty NEGATIVO** + intenção de reduzir mais ainda → `FALHA_QUANT_NEGATIVO` (skill 1 já protege).
- **action_apply_inventory infla quant negativo** (gotcha conhecido). Se destino tem qty<0 (raro), prefira `transferir_entre_lotes_v2` que valida via `ajustar_quant`.

## Composição em FLUXOS

Este átomo serve a múltiplos fluxos (folhas da árvore em `app/odoo/estoque/fluxos/`):

- **2.2.a lote→lote mesma loc** (10/13/padronizar/consolidar/transferir_lote): atômico direto.
- **2.2.b local→local mesmo lote** (mover_migracao FB/CD, indisp_p15_cd): modo loc→loc.
- **2.2.c lote→MIGRAÇÃO consolidador** (ajuste_fb_cd_indisponivel SAÍDA): modo lote→lote com destino MIGRAÇÃO.
- **2.2.d MIGRAÇÃO→lote real** (RETORNO Indisponível→Estoque): modo lote→lote com origem MIGRAÇÃO.
- **2.2.e net-zero planilha multi-empresa** (transferir_lote): orquestrador externo chama esta skill 1x por linha (ou usa `ajustar_quant` diretamente em loop).
- **2.2.f wildcard De-Local** (transferir_local_pasta22, ajuste_fb_cd_indisponivel): orquestrador externo + esta skill para a transferência atômica em cada quant resolvido.
- **2.2.g multi-grafia consolidação** (padronizar_migracao, consolidar_lote_104000015): modo lote→lote.
- **2.2.h unreserve→transfer→reassign** (substituir_lote_205030410): composição com **skill 2.4** ANTES de chamar esta.

## Validação (este átomo é validado por reprodução dos ad-hoc — ROADMAP C6)

Os scripts ad-hoc são o ground-truth:

- `10_executar_emergenciais_fb`, `13_transferencia_migracao_fb`, `padronizar_migracao`, `consolidar_lote_104000015_sal_fb`: EVAL — `--dry-run` reproduz o plano da execução real (log JSON).
- `15_transferencia_para_migracao` (4.888 linhas D010), `15r_transferencia_reversa`: EVAL — orquestradores de planilha que chamam o atomo 1x por linha. A skill cobre o ATOMO; o orquestrador permanece (folha de fluxo).
- `transferir_lote` (D012 net-zero), `transferir_local_pasta22` (D013 wildcard), `ajuste_fb_cd_indisponivel` (D013 + checkpoint): EVAL como orquestradores externos que compõem este átomo.
- `transferir_fluxo_c`, `executar_fluxo_b_vivas`: COM-BUG (G-TRANSFER-01 — usam `criar_se_nao_existe` retornando tuple como int). A skill faz o CERTO; divergência é melhoria, não falha.
- `substituir_lote_205030410_fb`: EVAL — caso `unreserve→transfer→reassign` (passos 1 e 3 → skill 2.4, passo 2 → esta skill).
- `recuperar_aumentos_falhos`: EVAL — re-aumento sem net-zero (não é transfer atômica, mas confirma o gotcha G021 que esta skill codifica).

Validados migram para `scripts/inventario_2026_05/_validados/transferindo-interno-odoo/` no checkpoint C9.
