<!-- doc:meta
tipo: index
camada: L1
sot_de: —
hub: docs/inventario-2026-05/02-gotchas/INDEX.md
superseded_by: —
atualizado: 2026-06-03
-->
# 02-gotchas — indice

> **Papel:** indice de `docs/inventario-2026-05/02-gotchas`. So ponteiros (PAD-A Onda 4f).

- [G-MO-05 — `medir_consumo_mo` indistinto por `state` inflava FURO_CONTABIL em MOs com apenas RESERVA FANTASMA](./G-MO-05-falso-positivo-reserva-fantasma.md)
- [G001 — NFs de referência do prompt são ENTRADAS, não SAÍDAS](./G001-nfs-referencia-sao-entradas-nao-saidas.md)
- [G002 — Divergência picking_type_id da LF](./G002-picking-type-LF-divergente.md)
- [G003 — CFOP real no Odoo diverge do prompt original](./G003-cfop-real-divergente-do-prompt.md)
- [G004 — Padrão real de NF inter-company é picking + robô CIEL IT, não account.move direto](./G004-padrao-real-eh-picking-robo-CIEL-IT.md)
- [G006 — Picking inter-company exige location virtual destino](./G006-picking-inter-company-location-virtual.md)
- [G007 — custo_medio=0 gera price_unit=0 e SEFAZ rejeita schema XML](./G007-custo-zero-rejeita-sefaz.md)
- [G008 — excecao_autorizado: NF autorizada mas XML autorizado vazio](./G008-excecao-autorizado-xml-vazio.md)
- [G009 — Script 03 emite 1 ajuste por produto, mas estoque esta em N lotes](./G009-multi-lote-distribuir-fifo.md)
- [G010 — AjusteEstoqueInventario nao tem campo `tipo_divergencia`](./G010-tipo-divergencia-nao-existe.md)
- [G011 — preencher_qty_done faltando no pipeline (cascateia L20/L21)](./G011-preencher-qty-done-faltando.md)
- [G012 — peso_liquido vazio em picking (consequencia de G011)](./G012-peso-liquido-vazio.md)
- [G013 — quantidade_volumes vazio em picking (consequencia de G011)](./G013-quantidade-volumes-vazio.md)
- [G014 — FEFO bloqueia auto-reserva em lotes vencidos (PEPINO IND)](./G014-fefo-lotes-vencidos-bloqueia-reserva.md)
- [G015 — Protecao automatica price_unit=0 em invoice pos-CIEL IT](./G015-protecao-price-zero-automatica.md)
- [G016 — SSL crash no meio do f5e_transmitir_sefaz perde commits](./G016-ssl-crash-no-loop-f5e-perde-commits.md)
- [G017 — NCM=False em produto causa cstat 225 (Schema XML invalido)](./G017-ncm-false-bloqueia-sefaz.md)
- [G018 — weight=0 no produto bloqueia F5c liberar_faturamento](./G018-weight-zero-bloqueia-f5c.md)
- [G019 — f5b validar() engole erro e marca F5b_VALIDADO sem picking estar done](./G019-f5b-validar-engole-erro.md)
- [G020 — f5c liberar_faturamento NÃO checa pre-condicao state=done](./G020-f5c-sem-checar-state-done.md)
- [G021 — ETAPA A reporta resultado prematuro (race condition A↔B)](./G021-etapa-a-reporta-prematuro.md)
- [G022 — ETAPA B não re-valida saldo entre action_assign e button_validate](./G022-etapa-b-sem-revalidar-saldo.md)
- [G023 — ETAPA F: entrada manual destino para NFs FB→{LF,CD}](./G023-etapa-f-entrada-destino-manual.md)
- [G024 — `stock.quant.reserved_quantity` NAO recompute apos `unlink` de move_line orfa](./G024-reserved-quantity-nao-recompute-apos-unlink.md)
- [G025 — Orfaos de `stock.move.line` recorrentes no CD](./G025-orfaos-move-lines-recorrentes-cd.md)
- [G026 — Tabela de fixes L6-L17 (sub-piloto bulk 10 produtos)](./G026-fixes-l6-l17-locator-table.md)
- [G027 — Bugs latentes do `09b_executar_pre_etapa.py` (B1 + B2)](./G027-09b-bugs-latentes-b1-b2.md)
- [G028 — Over-reservation em action_assign após renomeação de lote](./G028-over-reservation-action-assign-pos-renomeacao.md)
- [G029 — payment_provider_id ausente em recovery manual de NF](./G029-payment-provider-recovery-manual.md)
- [G030 — Pipeline RecebimentoLfOdooService trava em Fase 4 (rare)](./G030-pipeline-reclf-trava-em-fase-4.md)
- [G030 — `stock.move.line.quant_id` em Odoo CIEL IT é COMPUTED `store: False`](./G030-quant-id-em-stock-move-line-eh-computed.md)
- [G031 — `stock.lot` é POR PRODUTO; `LOTES_MIGRACAO_POR_COMPANY` NÃO é FK universal](./G031-lot-migracao-por-produto.md)
- [G034 — Robô CIEL IT aplica defaults PT 66 em DEV_* (CFOP 5124 errado)](./G034-robo-ciel-it-aplica-defaults-pt-66-em-dev-industr.md)
- [G035 — `product.barcode` invalido como GTIN quebra SEFAZ Schema 225](./G035-product-barcode-invalido-quebra-sefaz-schema-225.md)
- [G036 — Lote com vírgula é literal real + lotes duplicados quebram operador `=`](./G036-lote-virgula-literal-e-duplicado-operador-igual.md)
- [G037 — Picking ETAPA F criado manualmente sem PO precisa de `l10n_br_cfop_id` explícito (CAMINHO B PALIATIVO)](./G037-operacao-nao-cadastrada-exige-cfop-explicito.md)
- [G038 — `product.l10n_br_origem` ausente bloqueia transmissão SEFAZ via modal Odoo silencioso](./G038-l10n-br-origem-ausente-bloqueia-sefaz.md)
- [G040 — `P-15/05` é `stock.lot` REAL (não proxy-vazio) em produto `tracking='lot'`](./G040-p15-05-lote-real-vs-proxy-vazio-por-tracking.md)
- [G041 — `picking_type.reservation_method='manual'` faz `action_assign` reservar ZERO → faturamento multi-lote falha não-deterministicamente](./G041-reservation-method-manual-nao-auto-reserva-faturamento-multilote.md)
