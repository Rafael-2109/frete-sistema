---
name: ajustando-quant-odoo
description: >-
  Skill WRITE (átomo C1) para AJUSTAR o saldo de UM stock.quant no Odoo via
  inventory adjustment: somar/subtrair (--delta), definir (--valor-absoluto),
  zerar (--valor-absoluto 0), criar saldo (--criar-se-faltar) ou corrigir
  reserva órfã/negativa (--resetar-reserva). Usar quando o pedido é "ajusta o
  saldo do lote X", "soma N un no quant", "zera esse quant fantasma", "cria
  saldo do produto Y na empresa Z", "corrige a reserva negativa". `--dry-run`
  é o DEFAULT; só efetiva com `--confirmar`.
  NÃO USAR PARA:
  - mover saldo entre 2 lotes/locais (= 2 ajustes) -> transferindo-interno-odoo
  - transferir saldo entre CÓDIGOS de produto -> transferencia-saldo-codigo
  - só consultar/projetar saldo (não altera) -> subagente gestor-estoque-producao
  - resolver/criar lote isolado (sem ajustar saldo) -> StockLotService (util)
allowed-tools: Read, Bash, Glob, Grep
---

# ajustando-quant-odoo (WRITE — átomo C1)

Átomo de **ajuste atômico de 1 quant**. Aplica `inventory_quantity` + `action_apply_inventory`
(padrão Odoo 16+) gerando 1 `stock.move` auditável ("Physical Inventory"). É o ÁTOMO de ajuste
de estoque: operações maiores (transferência = 2 ajustes; net-zero = N) se compõem dele.

Constituição: `app/odoo/estoque/CLAUDE.md`. Service: `app/odoo/estoque/scripts/quant.py`.

---

## REGRAS CRÍTICAS
1. **`--dry-run` é o DEFAULT.** Sem `--confirmar`, o script só calcula e mostra o plano (exit 4). Sempre rode dry-run e **apresente o plano** antes de `--confirmar`.
2. **`--confirmar` efetiva** no Odoo (escreve). Operação reversível por outro ajuste, mas confirme com o usuário antes.
3. **Verificar no Odoo** após efetivar (não confiar só no output) — operação viva.
4. **Não inventar lote.** `--lote` ausente = SEM lote (`lot_id=False`). Para lote a criar, use `--criar-se-faltar` (só com `--delta > 0`).

## Contrato (átomo componível)
```
objeto:        stock.quant
input:         (--cod --empresa [--local] [--lote]) XOR --quant-id ; (--delta XOR --valor-absoluto) ; [--criar-se-faltar] [--resetar-reserva] [--delta-esperado X [--tolerancia-delta T] [--corrigir-para-esperado]] [--confirmar]
output (JSON): {modo, chave{...}, resultado{status,qty_antes,qty_apos,ajuste_aplicado,reservada,acao,quant_id,tempo_ms,erro, auto_correcao_aplicada?, delta_original_solicitado?, ajuste_aplicado_original?, delta_esperado?, divergencia?/divergencia_resolvida?}}
pré-condições: produto existe (1 ativo p/ default_code); tracking != serial; se tracking=lot, --lote obrigatório
pós-condições: 1 stock.move 'Physical Inventory' (no --confirmar); quant criado se --criar-se-faltar e qty_apos>=0
gotchas-invariante (no service quant.py):
  - delta XOR valor_absoluto; validar_nao_negativar; validar_nao_abaixo_reserva
  - G002 (lot.name busca via `in`+`=like`); NÃO inflar quant negativo
  - GUARD delta_esperado vs ajuste_aplicado (anti-bug CICLAMATO 2026-05-23):
    sem --corrigir-para-esperado bloqueia (FALHA_DELTA_DIVERGENTE);
    com --corrigir-para-esperado aplica delta_esperado (EXECUTADO_AUTO_CORRIGIDO).
modos:         --dry-run (default, exit 4) -> --confirmar (exit 0)
status:        EXECUTADO · EXECUTADO_AUTO_CORRIGIDO · DRY_RUN_OK · NOOP · FALHA_PRODUTO · BLOQUEADO_SERIAL · FALHA_LOTE · FALHA_QUANT_NEGATIVO · FALHA_RESERVADO · FALHA_DELTA_DIVERGENTE · FALHA_ODOO
```

## Receitas (caso real -> args)
| Preciso de... | Args | Vinha do ad-hoc |
|---------------|------|-----------------|
| Somar +X num lote (cria se faltar) | `--cod C --empresa E --lote L --delta +X --criar-se-faltar` | 12, 13, 14_v2, criar_saldo |
| Ajuste negativo residual (não cria; valida) | `--cod C --empresa E --lote L --delta -X` | 11 |
| Zerar um quant fantasma por id | `--quant-id Q --valor-absoluto 0 --confirmar` | limpar_quants_ghost |
| Definir saldo exato (contagem absoluta) | `--cod C --empresa E --lote L --valor-absoluto X` | — |
| Corrigir reserva negativa + zerar | `--quant-id Q --valor-absoluto 0 --resetar-reserva --confirmar` | corrigir_reserved |
| **Retomada de FALHA com guard** (NOVO 2026-05-24) | `--quant-id Q --delta X --delta-esperado Y` (bloqueia se divergente) | bug CICLAMATO |
| **Retomada de planilha c/ auto-correção** (NOVO 2026-05-24) | `--quant-id Q --delta X --delta-esperado Y --corrigir-para-esperado --confirmar` (aplica Y se diverge) | orquestrador de planilha |

## Exemplos
```bash
SK=.claude/skills/ajustando-quant-odoo/scripts/ajustar_quant.py
# 1) dry-run (default): somar 50 num lote da LF, criar se faltar
python "$SK" --cod 28239 --empresa LF --lote 26014 --delta 50 --criar-se-faltar
# 2) efetivar (após revisar o plano)
python "$SK" --cod 28239 --empresa LF --lote 26014 --delta 50 --criar-se-faltar --confirmar
# 3) zerar quant fantasma por id, corrigindo reserva órfã
python "$SK" --quant-id 12073 --valor-absoluto 0 --resetar-reserva --confirmar
# 4) [NOVO 2026-05-24] retomada de FALHA com guard: bloqueia se diverge do pedido original
python "$SK" --quant-id 258975 --valor-absoluto 0 --resetar-reserva --delta-esperado -7.0
# Saída esperada se divergente: FALHA_DELTA_DIVERGENTE com mensagem "Cruzar quant_id com pedido original"
# 5) [NOVO 2026-05-24] retomada com auto-correção: aplica delta_esperado em vez de bloquear
python "$SK" --quant-id 258975 --valor-absoluto 0 --resetar-reserva --delta-esperado -7.0 --corrigir-para-esperado --confirmar
# Status final: EXECUTADO_AUTO_CORRIGIDO (aplicou -7.0 em vez de zerar; preservou auditoria do pedido original)
```

## Armadilhas
- **`--delta` XOR `--valor-absoluto`** — exatamente um (argparse já força).
- **`--criar-se-faltar` exige chave + `--delta > 0`** — não cria com `--valor-absoluto` nem por `--quant-id`; lote a criar só com saldo positivo (evita lote órfão).
- **tracking=serial** é bloqueado (ajuste por qtd não suportado); **tracking=lot** exige `--lote`; **tracking=none** ignora `--lote`.
- **Não usar para mover saldo** entre lotes/locais — isso é `transferindo-interno-odoo` (faz os 2 ajustes atomicamente).
- **(NOVO 2026-05-24) Em retomadas de FALHA**, sempre passar `--delta-esperado <pedido_original>`. Sem isso, política homogênea (`--valor-absoluto 0 --resetar-reserva`) pode over-reduzir como no bug CICLAMATO 2026-05-23 (-40.7319 em vez de -7). O guard ABORTA quando diverge — re-execute com args corretos, OU use `--corrigir-para-esperado` para aplicar o pedido original automaticamente.
- **(2026-05-24) `--delta-esperado 0` ativa o guard esperando NOOP.** Se sua planilha tem campos vazios que viram `0.0` numérico, NÃO passe para `--delta-esperado` (ou converta para `None`). Caso contrário, o guard vai bloquear qualquer ajuste real divergente de 0.
- **(2026-05-24) `--tolerancia-delta` negativo levanta `ValueError`** (sem o erro, desarmaria o guard silenciosamente — `divergencia > -0.5` é sempre True).

## Composição em FLUXOS (este átomo serve a vários)
- **Ajuste por planilha** (Família A): orquestrador `scripts/inventario_2026_05/ajuste_inventario.py` (1 chamada ao átomo por linha) — vira a folha `app/odoo/estoque/fluxos/2.1-*`.
- **Net-zero / transferência**: compõe 2 ajustes — ver `transferindo-interno-odoo`.

## Validação (este átomo é validado por reprodução dos ad-hoc — ver ROADMAP C6)
Os scripts `11/12/13/14_v2/criar_saldo` são o ground-truth: `ajustar_quant.py --dry-run` com os mesmos inputs deve reproduzir o plano. Validados migram para `scripts/inventario_2026_05/_validados/ajustando-quant-odoo/`.
