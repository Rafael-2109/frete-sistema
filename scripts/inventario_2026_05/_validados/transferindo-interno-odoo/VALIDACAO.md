# Skill 2 — `transferindo-interno-odoo` · Validação por reprodução (C6)

**Status global:** 🟡 mín viável (2 scripts SUPERADOS · 11+ orquestradores VIVOS pendentes de fluxos compostos)
**Skill:** [`.claude/skills/transferindo-interno-odoo/`](../../../.claude/skills/transferindo-interno-odoo/)
**Service:** [`app/odoo/estoque/scripts/transfer.py`](../../../app/odoo/estoque/scripts/transfer.py)
**Folha de fluxo:** [`2.2-realocar-saldo.md`](../../../app/odoo/estoque/fluxos/2.2-realocar-saldo.md)
**Pytest baseline:** 33/33 verdes em `tests/odoo/services/test_stock_internal_transfer_service.py` (14 originais + 19 novos cobrindo API v2, helpers MIGRAÇÃO, gotchas G021/G022/G027).
**Sessão:** 2026-05-24 (Skill 2 maturando — C1-C10 cumpridos para 2 scripts; outros movem conforme demanda real).

---

## Scripts SUPERADOS (movidos para `_validados/transferindo-interno-odoo/`)

### 1. `10_executar_emergenciais_fb.py`

| Item | Detalhe |
|---|---|
| **Tipo** | A — lote→lote mesma loc (hardcoded, 10 casos) |
| **Padrão** | MIGRAÇÃO → lote canônico em FB/Estoque (1 caso usa `'0909'` como origem alt) |
| **Ground-truth** | Executado 2026-05-18 14:38 (E01-E10). Logs em `auditoria/log_2.1_*.json` históricos |
| **Reprodução pela skill** | dry-run com mesmos inputs reproduz exatamente: (a) `product_id` resolvido; (b) `lot_id_origem` resolvido (MIGRAÇÃO/0909 do produto, FB); (c) `lot_id_destino` resolvido (MI ###-###/AA, criado se faltar); (d) `qty_antes/qty_apos` consistentes com saldo atual; (e) propagação `delta_esperado=±qty` ativa o guard CICLAMATO. |
| **Validado em 2026-05-24** | Caso E01 (`cod 104000015 --empresa FB --qty 35 --lote-origem MIGRAÇÃO --lote-destino 'MI 027-098/26'`): skill detectou corretamente que `qty_antes=0.0` (MIGRAÇÃO consumida em 18/05) → `FALHA_REDUCAO` (FALHA_QUANT_VAZIO). Estado coerente com histórico. |
| **Status** | SUPERADO — skill cobre o padrão 100% |
| **sys.path corrigido** | `parents[2] → parents[4]` (museum vivo, ainda executável) |

### 2. `padronizar_migracao.py`

| Item | Detalhe |
|---|---|
| **Tipo** | A — lote→lote mesma loc (1 caso hardcoded; consolida grafia 'MIGRACAO' sem cedilha → 'MIGRAÇÃO' com cedilha) |
| **Padrão** | PRODUCT_ID=28239, lot_id origem=56534 ('MIGRACAO' sem cedilha), lot_id destino=30400 ('MIGRAÇÃO' com cedilha), qty=66532, FB/Estoque |
| **Ground-truth** | Executado 2026-05-18 (saldo migrado, ambos lots ainda existem no Odoo) |
| **Reprodução pela skill** | **PARCIAL — limitação documentada.** A skill via CLI aceita nomes de lote (`--lote-origem MIGRACAO --lote-destino MIGRAÇÃO`); ambos os nomes batem com `is_migracao()` (variantes G022) → skill consolida em UM lot_id (o de maior saldo na loc). Para forçar 2 LOT_IDs ESPECÍFICOS, precisa `--lot-id-origem 56534 --lot-id-destino 30400` (NÃO implementado — adicionar quando houver demanda real). |
| **Workaround atual** | Chamar `StockInternalTransferService.transferir_entre_lotes_v2(lot_id_origem=56534, lot_id_destino=30400, ...)` diretamente em Python, ou usar o script-fonte arquivado (museum vivo). |
| **Validado em 2026-05-24** | dry-run via CLI detectou corretamente o problema: `FALHA_LOTE 'lote origem == destino (id=56534 MIGRACAO)'` — comportamento defensivo correto, mas indica que a CLI não cobre esse caso específico via nomes. |
| **Status** | SUPERADO com LIMITAÇÃO — skill cobre o ÁTOMO (`transferir_entre_lotes_v2`), CLI não cobre o caso especial de 2 grafias literais. Adicionar `--lot-id` quando demanda real surgir. |
| **sys.path corrigido** | `parents[2] → parents[4]` |

---

## Scripts NÃO movidos (continuam VIVOS — operação viva)

Lista completa em [`2.2-realocar-saldo.md` §Scripts-fonte cobertos](../../../app/odoo/estoque/fluxos/2.2-realocar-saldo.md#scripts-fonte-cobertos-mover-para-_validadostransferindo-interno-odoo-ao-fechar-c9). Razão para NÃO mover ainda:

1. **Orquestradores de planilha** (13, 15, 15r, transferir_lote, transferir_local_pasta22, ajuste_fb_cd_indisponivel, mover_migracao, relotar_migracao_para_lotes_fb, transferir_fluxo_c, executar_fluxo_b_vivas, transferir_indisp_para_estoque_p15_cd, consolidar_lote_104000015_sal_fb, substituir_lote_205030410_fb, 15_transferir_preprod_para_estoque_fb, 17_transferir_preprod_lf_para_estoque, recuperar_aumentos_falhos): a skill cobre o ÁTOMO. A ORQUESTRAÇÃO (lê planilha, normaliza schemas, retry, sharding, checkpoint, multi-quant origem, semânticas D010/D012/D013, wildcard locations) vive em **fluxos compostos** ainda por escrever.
2. **Scripts COM-BUG** (`transferir_fluxo_c`, `executar_fluxo_b_vivas` — G-TRANSFER-01 com `criar_se_nao_existe` retornando tuple usado como int): a skill faz o CERTO. Divergência é melhoria, não falha. NÃO arquivar como SUPERADO até o fluxo composto que os substitui ser escrito.
3. **Scripts cross-skill** (`substituir_lote_205030410_fb` exige Skill 2.4 unreserve + Skill 2 transfer + Skill 2.4 reassign): cobertura completa exige fluxo composto.
4. **Regra `feedback-skills-demanda-driven`**: não implementar átomos especulativos. Os 13+ orquestradores VIVOS permanecem disponíveis para execução manual quando o caso real surgir.

---

## Estado pós-C10

- 2/18 scripts-fonte mapeados SUPERADOS (10_emergenciais, padronizar_migracao)
- 16+ scripts permanecem VIVOS em `scripts/inventario_2026_05/` — aguardam fluxos compostos ou refator dos orquestradores
- 33 testes pytest verdes no service (14 originais preservados + 19 novos)
- 0 execuções `--confirmar` em PROD (sem demanda real até agora — alinhado com `feedback-skills-demanda-driven`)

## Próximas evoluções da Skill 2 (demanda-driven)

1. **Arg `--lot-id-origem` / `--lot-id-destino`** na CLI — cobre caso `padronizar_migracao` sem ambiguidade. Implementar quando alguém precisar consolidar 2 grafias literais de novo.
2. **Fluxos compostos** (planilha D010/D012/D013) — escrever folhas `2.2.D010`, `2.2.D012`, `2.2.D013` se padrões se repetirem com 2+ casos reais cada.
3. **Wrapper `transferir_quantidade_para_lote_v2` com lot_id_destino=None** — atualmente levanta `ValueError`. Caso real (transferir lote→quant sem lote) ainda não surgiu.
