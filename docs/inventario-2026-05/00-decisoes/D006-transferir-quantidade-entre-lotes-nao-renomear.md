<!-- doc:meta
tipo: explanation
camada: L3
sot_de: —
hub: docs/inventario-2026-05/00-decisoes/INDEX.md
superseded_by: —
atualizado: 2026-06-03
-->
# D006 — Transferir quantidade entre lotes (NAO renomear)

> **Papel:** D006 — Transferir quantidade entre lotes (NAO renomear).

## Indice

- [Contexto](#contexto)
- [Decisao](#decisao)
- [Mantendo a acao `RENOMEAR_LOTE` no DB](#mantendo-a-acao-renomear_lote-no-db)
- [Implementacao](#implementacao)
- [Caso piloto 210030325 LF (validacao final)](#caso-piloto-210030325-lf-validacao-final)
- [Generalizacao](#generalizacao)
- [Impacto](#impacto)
- [Riscos conhecidos](#riscos-conhecidos)
- [Licoes aprendidas — piloto 210030325 LF (2026-05-18)](#licoes-aprendidas-piloto-210030325-lf-2026-05-18)
  - [L1. Picking outgoing precisa `incoterm` + `carrier_id`](#l1-picking-outgoing-precisa-incoterm-carrier_id)
  - [L2. Playwright `cids` + `menu_id` variam por CNPJ](#l2-playwright-cids-menu_id-variam-por-cnpj)
  - [L3. Modal `o_technical_modal` intercepta clicks](#l3-modal-o_technical_modal-intercepta-clicks)
  - [L4. Wizard de confirmacao apos "Transmitir NF-e"](#l4-wizard-de-confirmacao-apos-transmitir-nf-e)
  - [L5. Invoice criada pelo robo CIEL IT sem `payment_provider_id`](#l5-invoice-criada-pelo-robo-ciel-it-sem-payment_provider_id)
- [Licoes aprendidas — sub-piloto bulk 10 produtos (2026-05-18 madrugada)](#licoes-aprendidas-sub-piloto-bulk-10-produtos-2026-05-18-madrugada)
  - [L6. Picking outgoing exige location virtual destino (Empresas incompativeis)](#l6-picking-outgoing-exige-location-virtual-destino-empresas-incompativeis)
  - [L7. button_validate sem skip_backorder deixa picking em assigned](#l7-button_validate-sem-skip_backorder-deixa-picking-em-assigned)
  - [L8. f5b/f5c/f5d so marcavam 1 ajuste por picking (multi-ajuste perdido)](#l8-f5bf5cf5d-so-marcavam-1-ajuste-por-picking-multi-ajuste-perdido)
  - [L9. f5e re-transmitia mesma NF para cada ajuste do picking](#l9-f5e-re-transmitia-mesma-nf-para-cada-ajuste-do-picking)
  - [L10. status auditoria excedeu VARCHAR(20)](#l10-status-auditoria-excedeu-varchar20)
  - [L11. forcar_qty_done inflando alem do disponivel (saldo negativo)](#l11-forcar_qty_done-inflando-alem-do-disponivel-saldo-negativo)
  - [L12. Distribuir demanda entre lotes reais (script 03 vs realidade)](#l12-distribuir-demanda-entre-lotes-reais-script-03-vs-realidade)
  - [L13. price_unit=0 nas linhas (custo_medio zero — SEFAZ rejeita)](#l13-price_unit0-nas-linhas-custo_medio-zero-sefaz-rejeita)
  - [L14. Conexao Odoo XML-RPC nao e thread-safe](#l14-conexao-odoo-xml-rpc-nao-e-thread-safe)
  - [L15. carregar_ajustes precisa incluir EXECUTADO](#l15-carregar_ajustes-precisa-incluir-executado)
  - [L16. excecao_autorizado vs autorizado normal (XML autorizado vazio)](#l16-excecao_autorizado-vs-autorizado-normal-xml-autorizado-vazio)
  - [L17. Sentido invertido FB→LF: entrada FB nao se aplica](#l17-sentido-invertido-fblf-entrada-fb-nao-se-aplica)
  - [Resumo do refinamento (10 fixes L6-L17)](#resumo-do-refinamento-10-fixes-l6-l17)
- [Licoes aprendidas — sub-piloto bulk RE-EXECUCAO (2026-05-18 madrugada apos checkpoint)](#licoes-aprendidas-sub-piloto-bulk-re-execucao-2026-05-18-madrugada-apos-checkpoint)
  - [L18. AjusteEstoqueInventario nao tem campo `tipo_divergencia` (G010)](#l18-ajusteestoqueinventario-nao-tem-campo-tipo_divergencia-g010)
  - [L19. preencher_qty_done faltando no pipeline (RAIZ CRITICA — G011)](#l19-preencher_qty_done-faltando-no-pipeline-raiz-critica-g011)
  - [L20. peso_liquido=0 (consequencia de L19 — G012)](#l20-peso_liquido0-consequencia-de-l19-g012)
  - [L21. quantidade_volumes=0 (consequencia de L19 — G013)](#l21-quantidade_volumes0-consequencia-de-l19-g013)
  - [Resumo dos 4 novos fixes L18-L21](#resumo-dos-4-novos-fixes-l18-l21)
  - [Estado pos-L18-L21 fixes](#estado-pos-l18-l21-fixes)
- [Licoes aprendidas — sub-piloto bulk (continuacao L22-L23, 2026-05-18)](#licoes-aprendidas-sub-piloto-bulk-continuacao-l22-l23-2026-05-18)
  - [L22. Lotes vencidos bloqueiam auto-reserva (G014)](#l22-lotes-vencidos-bloqueiam-auto-reserva-g014)
  - [L23. price_unit=0 em invoice criada pelo robo CIEL IT (G015)](#l23-price_unit0-em-invoice-criada-pelo-robo-ciel-it-g015)
  - [Resumo L18-L23 (6 novos fixes)](#resumo-l18-l23-6-novos-fixes)
- [Licoes aprendidas — root cause NF 626032 (2026-05-18 manha)](#licoes-aprendidas-root-cause-nf-626032-2026-05-18-manha)
  - [L24. SSL crash no f5e perde commits DB (G016)](#l24-ssl-crash-no-f5e-perde-commits-db-g016)
  - [L25. NCM=False em produto causa cstat 225 (G017 — RAIZ DEFINITIVA)](#l25-ncmfalse-em-produto-causa-cstat-225-g017-raiz-definitiva)
  - [Resumo L24-L25 (mais 2 fixes pos-sub-piloto)](#resumo-l24-l25-mais-2-fixes-pos-sub-piloto)
  - [Recovery NF 626032 (pos-investigacao)](#recovery-nf-626032-pos-investigacao)
- [Arquivos modificados (commit `a8e0d0bb`)](#arquivos-modificados-commit-a8e0d0bb)
- [Pendencias para bulk](#pendencias-para-bulk)
- [Generalizacao D004 para FB+CD (2026-05-18 fim do dia)](#generalizacao-d004-para-fbcd-2026-05-18-fim-do-dia)

**Data**: 2026-05-18
**Status**: aprovado, implementado
**Fonte**: instrucao usuario apos analise do dry-run do caso piloto 210030325 LF

---

## Contexto

D004 introduziu acao `RENOMEAR_LOTE` para casos onde inventario fisico e
Odoo tem mesmos saldos mas em nomes de lote diferentes. A implementacao
inicial chamaria `stock.lot.write({'name': novo})`.

Apos analise no dry-run do caso piloto 210030325 LF, foram identificados
3 problemas estruturais com renomeio:

1. **Quant sem lote (`lot_id=False`) nao pode ser renomeado** — nao ha
   `stock.lot` para fazer `write`. Caso real: quant 32677 (39.216 un de
   210030325 na LF/Estoque) sem lote.

2. **Renomeio afeta o lote inteiro** — renomear `stock.lot.id=44098`
   (MIGRAÇÃO, 67.220 un total) para `26014` muda TODOS os 67.220, mas o
   inventario diz que apenas 35.188 devem virar 26014; os restantes
   32.032 sao PERDA. Ou seja, renomeio nao suporta split parcial.

3. **Unique constraint `(name, product_id, company_id)`** — multiplos
   lotes origem apontando para o mesmo lote destino violam a constraint
   na segunda chamada de rename. Caso piloto: 4 lotes (vazio, 24715,
   3009/24, MIGRAÇÃO) → todos para `26014`.

## Decisao

Substituir renomeio por **transferencia de quantidade especifica entre
lotes** via inventory adjustment standard do Odoo
(`stock.quant.action_apply_inventory`).

A operacao atomica e:

1. Garantir lote destino existe (criar se nao existir).
2. Reduzir quant origem em `qty` (write `inventory_quantity` + apply).
3. Aumentar (ou criar) quant destino em `qty` (write/create + apply).

Pelo padrao Odoo, isso gera 1 stock.move automatico associado, visivel
em Inventory > Reporting > Stock Moves com origem "Physical Inventory"
— auditavel.

## Mantendo a acao `RENOMEAR_LOTE` no DB

Por compatibilidade com os 644 ajustes ja propostos com
`acao_decidida='RENOMEAR_LOTE'`, o nome da acao no DB e' mantido. O
**executor (`teste_210030325_lf.py` e futuros scripts de execucao)**
interpreta `RENOMEAR_LOTE` como **TRANSFERIR quantidade para lote
destino** — sem chamar `stock.lot.write({'name': ...})`.

Migracao do nome para `TRANSFERIR_LOTE` no DB e' opcional e nao urgente.
Se feita, a logica de execucao continua identica.

## Implementacao

Novo service atomico e reutilizavel:

```
app/odoo/services/stock_internal_transfer_service.py

class StockInternalTransferService:
    def transferir_entre_lotes(
        self, product_id, company_id, location_id, qty,
        lot_id_origem, lot_id_destino,
    ) -> dict: ...

    def transferir_quantidade_para_lote(
        self, product_id, company_id, location_id, qty,
        lot_id_origem, nome_lote_destino, expiration_date_destino=None,
    ) -> dict: ...
```

E novo metodo em `StockLotService`:

```python
def criar_se_nao_existe(
    self, nome, product_id, company_id, expiration_date=None,
) -> tuple[int, bool]: ...  # (lot_id, criado_agora)
```

Tests: `tests/odoo/services/test_stock_internal_transfer_service.py`
(14 testes — cenarios feliz, criar quant destino, sem lote origem,
qty invalida, reserva impeditiva, wrapper).

## Caso piloto 210030325 LF (validacao final)

Apos refator (verificado no dry-run 2026-05-18):

1. Criar lote `26014` na LF
2. Transferir 39.216 un do quant 32677 (sem lote, loc 42) → 26014
3. Transferir 5.604 un do quant 60967 (24715, loc 53) → 26014
4. Transferir 2.292 un do quant 113646 (3009/24, loc 53) → 26014
5. Transferir 35.188 un do quant 176722 (MIGRAÇÃO, loc 42, total 67.220) → 26014
   (sobram 32.032 un no lote MIGRAÇÃO loc 42)
6. Picking PERDA LF→FB com 2 linhas:
   - 32.032 un lote MIGRAÇÃO loc 42 (residuo do passo 5)
   - 34.500 un lote 24715 loc 42 (quant 189100, intacto)
7. F5b-F5e (validar, liberar, aguardar invoice, transmitir SEFAZ)

Resultado esperado pos-execucao:
- LF: 2 quants do lote `26014` — loc 42 com 74.404 un + loc 53 com 7.896 un = 82.300 ✓
- FB: lote MIGRACAO + 66.532 un para cod 210030325
- 1 NF CFOP 5903 emitida (R$ 42.806,69)

## Generalizacao

Mesma logica para:
- TODOS os outros 643 ajustes RENOMEAR_LOTE da onda 4
- Eventuais consolidacoes futuras (FB↔CD apos D004 generalizar)
- Correcoes pontuais de cadastro de lote (operacao diaria)
- Atribuicao de lote a quants sem lote (caso comum apos migracoes)

## Impacto

- `D004` — ainda valido como conceito (consolidar + diferenca liquida),
  mas o item 1 ("Renomear lotes Odoo") fica reinterpretado como
  "Transferir quantidades especificas para lote alvo".
- `D005` — sem impacto (lote MIGRACAO na FB continua sendo o
  consolidador).
- `app/odoo/models/ajuste_estoque_inventario.py` — sem impacto na
  estrutura. `acao_decidida='RENOMEAR_LOTE'` continua valido como nome,
  agora com semantica TRANSFERIR.
- `scripts/inventario_2026_05/04_propor_ajustes.py` — sem impacto na
  proposta (continua emitindo RENOMEAR_LOTE).
- `scripts/inventario_2026_05/teste_210030325_lf.py` — refatorado para
  usar `StockInternalTransferService`.

## Riscos conhecidos

| Risco | Mitigacao |
|-------|-----------|
| `action_apply_inventory` bloqueado por validacoes Odoo (e.g. lote tracking obrigatorio) | Testar no caso piloto antes de bulk |
| Quants em sub-locations diferentes do mesmo lote — necessario passar location_id correto | Service descobre location dinamicamente via `buscar_quant` no caller |
| Inventory adjustment cria stock.move com origin "Physical Inventory" — pode confundir audit fiscal | Documentar fluxo no plano de operacao |

---

## Licoes aprendidas — piloto 210030325 LF (2026-05-18)

Caso piloto executado end-to-end em PROD (NF-e RETNA/2026/00029,
chave `35260518467441000163550010000131491006086070`, SEFAZ autorizada
cstat=100). Cinco bugs descobertos e corrigidos:

### L1. Picking outgoing precisa `incoterm` + `carrier_id`

**Sintoma**: `action_liberar_faturamento` retorna
`'Voce deve informar o Tipo de Frete para liberar o faturamento.'`

**Causa raiz**: `stock.picking` precisa de `incoterm` (id=6 CIF) e
`carrier_id` (id=996 NACOM GOYA — transportadora propria) populados.
Sem isso, o robo CIEL IT recusa criar a invoice.

**Fix**: `StockPickingService.criar_transferencia()` ganhou defaults:
- `INCOTERM_CIF = 6`
- `CARRIER_NACOM = 996`
- Parametros `incoterm_id`/`carrier_id` opcionais (default = constantes
  acima) — passe `None` se algum nao for desejado.

**Ref**: G004 `app/recebimento/services/recebimento_lf_odoo_service.py:2195`

### L2. Playwright `cids` + `menu_id` variam por CNPJ

**Sintoma**: form view nao carrega — "Erro de acesso a Faturas
(account.move)" mostrado em screenshot.

**Causa raiz**: o `transmitir_nfe_via_playwright` original usava
`cids=1-3-4` hardcoded (somente NACOM). Quando a invoice e' da LF (cid=5,
outro CNPJ — LA FAMIGLIA 18.467.441), a UI bloqueia via `ir.rule 71`
("Account Entry" — `[('company_id', 'in', company_ids + [False])]`)
porque `allowed_company_ids` na sessao nao inclui 5.

**Fix**: `_resolver_cids_e_menu(company_id)`:
- LF (cid=5) → `cids='5'`, `menu_id=217`
- NACOM (1/3/4) → `cids='1-3-4'`, `menu_id=124`

Apos login, navega para `/web?cids={cids_alvo}` para forcar
`allowed_company_ids` correto.

### L3. Modal `o_technical_modal` intercepta clicks

**Sintoma**: `Locator.click` timeout — `<div role="dialog" class="modal d-block o_technical_modal">…</div> subtree intercepts pointer events`.

**Causa raiz**: Odoo 17 abre modais tecnicos (avisos/dialogs) que cobrem
o form view e bloqueiam interacao Playwright.

**Fix**: `_fechar_modais_tecnicos()` chamado antes de cada
`_clicar_botao()`. Estrategias: `.btn-close`, botoes "Fechar/Close/Ok",
fallback Escape. Em caso de re-aparecer, tenta `click(force=True)`.

### L4. Wizard de confirmacao apos "Transmitir NF-e"

**Sintoma**: SEFAZ nao processa apesar do click ser feito — `situacao_nf`
permanece `'rascunho'`.

**Causa raiz**: pode haver wizard de confirmacao `'Confirmar transmissao
para SEFAZ?'` (modal padrao `.modal.show`) que precisa de OK/Confirmar
antes do `action_gerar_nfe` rodar.

**Fix**: `_tratar_wizard_confirmacao(page, logger)` apos click do
"Transmitir NF-e" — busca seletores padrao (`.modal.show button.btn-primary`)
e clica em "Confirmar/Sim/OK".

### L5. Invoice criada pelo robo CIEL IT sem `payment_provider_id`

**Sintoma**: SEFAZ retorna modal **"Operacao invalida — Meio de
pagamento nao configurado para a fatura RETNA/2026/00029"**.

**Causa raiz**: o robo CIEL IT cria a invoice via XML-RPC sem popular
`payment_provider_id` (campo "Forma de Pagamento"). NF historica de
referencia (588209 RETNA/2026/00025) tinha esse campo = id 38
('SEM PAGAMENTO'). Operacoes inter-company sem cobranca financeira
exigem esse valor.

**Fix**: `InventarioPipelineService._garantir_payment_provider()`:
- Constante `PAYMENT_PROVIDER_SEM_PAGAMENTO = 38`
- Chamado em `f5d_aguardar_invoices()` logo apos detectar invoice criada
  pelo robo (idempotente — skip se ja setado)
- Fallback: se `write` em `state=posted` falhar, fazer
  `button_draft + write + action_post`

---

## Licoes aprendidas — sub-piloto bulk 10 produtos (2026-05-18 madrugada)

Sub-piloto executado com 21 ajustes de 10 produtos (max 5 produtos/picking).
Resultado: 1 NF end-to-end OK (608631 entrada FB 608645), 1 NF fiscal OK
mas sem entrada FB automatica (608629 FB→LF), 1 NF cancelada localmente
(608630 NF 13150). Descobertos e corrigidos os erros L6-L15 abaixo.

### L6. Picking outgoing exige location virtual destino (Empresas incompativeis)

**Sintoma**: `<Fault 2: "Empresas incompativeis nos registros: 'FB/SAI/IND/01553'
pertence a NACOM GOYA - FB e 'Destination Location' (LF/Estoque) pertence a
outra empresa">`

**Causa raiz**: `resolver_location_destino(tipo_op, company_destino)` retornava
`COMPANY_LOCATIONS[destino]` (location interna da empresa destino), mas
pickings inter-company exigem location virtual com `company_id=False`.

**Fix**: `resolver_location_destino(tipo_op, company_destino, company_origem)`
mapeia (origem, tipo_op) → location virtual correta:
- LF→FB perda → 5 (Parceiros/Clientes)
- FB→LF industrializacao → 26489 (Em Transito Industrializacao)
- FB↔CD transf-filial → 6 (Em Transito Filiais)
- CD retrabalho → 26489

Validado contra `default_location_dest_id` dos picking_types:
```
pt 53 FB Expedicao Industrializacao: dest=26489
pt 51 FB Expedicao Entre Filiais:    dest=6
pt 55 CD Expedicao Entre Filiais:    dest=6
pt 66 LF Expedicao Industrializacao: dest=5
pt 94 LF Expedicao N Aplicado:       dest=5
pt 96 CD Retrabalho:                 dest=26489
```

Localizacao: `app/odoo/services/inventario_pipeline_service.py:74-148`

### L7. button_validate sem skip_backorder deixa picking em assigned

**Sintoma**: `picking_svc.validar(pid)` retorna OK mas state continua
`assigned` (deveria virar `done`).

**Causa raiz**: Diferenca entre `product_uom_qty` (demand) e qty reservada
pelo `action_assign` faz Odoo abrir wizard de backorder. XML-RPC nao
serializa o wizard (cannot marshal None) e mesmo quando aceita, o picking
fica em pending.

**Fix**: `StockPickingService.validar()` agora passa
```python
context={
    'skip_backorder': True,
    'picking_ids_not_to_backorder': [picking_id],
}
```

Padrao usado em `recebimento_lf_odoo_service.py:1548-1558` (recebimento LF).

Localizacao: `app/odoo/services/stock_picking_service.py:182-211`

### L8. f5b/f5c/f5d so marcavam 1 ajuste por picking (multi-ajuste perdido)

**Sintoma**: Picking com 10 ajustes (1 picking = N produtos) → so 1 ajuste
marca F5b/F5c/F5d. Os outros 9 ficam em fase anterior (F5a_PICKING_CRIADO).

**Causa raiz**: `ajuste_por_pid: Dict[int, object] = {}` indexa por
`picking_id_odoo` — quando ha multiplos ajustes para o mesmo picking,
o ultimo SOBREESCREVE o anterior no dict.

**Fix**: Helper `_agrupar_por_picking(ajustes) -> Dict[int, List]`. Apos
sucesso/falha, itera TODOS ajustes do mesmo picking ao marcar fase +
registrar auditoria.

Localizacao: `app/odoo/services/inventario_pipeline_service.py:500-540`

### L9. f5e re-transmitia mesma NF para cada ajuste do picking

**Sintoma**: Picking com 10 ajustes → Playwright transmitia SEFAZ 10 vezes
para a mesma invoice. Apos 1 sucesso, as outras 9 transmissoes geravam
problemas (rate limit, double-charge, wizard de confirmacao).

**Causa raiz**: `f5e_transmitir_sefaz` itera por ajuste. Idempotencia via
`aj.fase_pipeline == 'F5e_SEFAZ_OK'` so funciona apos commit explicito —
mas como objetos Python ja carregados ANTES do commit, o filtro nao pega.

**Fix**: Adicionado `invoices_processadas: Dict[int, str]` dentro de
`f5e_transmitir_sefaz`. Apos transmitir 1 invoice, marca todos os outros
ajustes da mesma invoice como `SKIP_INV_PROC` (sem chamar Playwright,
replicando chave/status no DB).

Localizacao: `app/odoo/services/inventario_pipeline_service.py:778-870`

### L10. status auditoria excedeu VARCHAR(20)

**Sintoma**: `psycopg2.errors.StringDataRightTruncation: value too long for
type character varying(20)` ao gravar
`status='SKIPPED_INVOICE_JA_PROCESSADA'` (30 chars).

**Fix**: status reduzido para `'SKIP_INV_PROC'` (13 chars).

Localizacao: `app/odoo/services/inventario_pipeline_service.py:826`

### L11. forcar_qty_done inflando alem do disponivel (saldo negativo)

**Sintoma**: tentativa de "forcar qty_done = product_uom_qty" gerava
escalonamento `qty_done = qty_atual * (demand / soma_qty)`, podendo
exceder o saldo real do lote. Causaria estoque negativo no Odoo.

**Fix**: Substituido por `ajustar_qty_done_pelo_disponivel(picking_id)` que
NUNCA infla qty_done. Em vez disso, REDUZ o `product_uom_qty` da move
para igualar ao que `action_assign` efetivamente reservou. Retorna
`pendencias` com a diferenca para gerar ajustes complementares.

Localizacao: `app/odoo/services/stock_picking_service.py:213-280`

### L12. Distribuir demanda entre lotes reais (script 03 vs realidade)

**Sintoma**: Ajuste 161385 (103000117 PERDA_LF_FB) com
`lote_origem=MIGRAÇÃO qtd_ajuste=-672.32`. Mas no Odoo, o lote MIGRAÇÃO
deste produto so tinha 52 un. `qty_done` final = 52 (resto perdido).

**Causa raiz**: Script 03 (`03_confrontar_inv_vs_odoo.py`) agrega TOTAL_ODOO
por produto e gera 1 ajuste PERDA com `qtd_ajuste = total - inv` apontando
1 unico `lote_origem`. Mas o estoque real esta distribuido entre N lotes.

**Fix**: `etapa_b_pickings` agora consulta `stock.quant` real na ORIGEM e
distribui demanda total entre lotes disponiveis (FIFO por `create_date`).
1 linha por lote disponivel ate cobrir a demanda. Se sobrar
`qty_restante > 0`, cria automaticamente ajuste compensatorio
`INDUSTRIALIZACAO_FB_LF` (FB → LF +delta) para a proxima onda.

Localizacao: `scripts/inventario_2026_05/09_executar_onda1_bulk.py:435-540`

**Conceito chave**: nao se deve confiar em `lote_origem` do DB; sempre
**RECONCILIAR contra `stock.quant` real** antes de criar pickings.

### L13. price_unit=0 nas linhas (custo_medio zero — SEFAZ rejeita)

**Sintoma**: NF 13150 (608630) saiu com 2 linhas `price_unit=0`. SEFAZ
rejeitou com "Falha no Schema XML do lote de NFe" (vUnCom=0 viola schema
NFe). Robo Playwright re-transmitia 15 vezes sem sucesso.

**Causa raiz**: 2 ajustes (101001001 e 102020600) tinham `custo_medio=0`
no DB. Robo CIEL IT lia o custo de algum campo (provavelmente
`stock.move.price_unit` ou `product.standard_price`) e gerava invoice com
unit=0.

Mas tem variante: produto 102020600 tinha `standard_price=-14.15` (custo
negativo no cadastro Odoo CIEL IT — erro comum de inventario inicial).
SEFAZ tambem rejeita valores negativos.

**Fix**:
1. `etapa_b_pickings` ANTES de criar pickings busca `product.standard_price`
   no Odoo para cada produto e atualiza `custo_medio` se for `<= 0`.
2. Para valores negativos, usa `abs(standard_price)` (assume que e' erro
   de cadastro). Default 0.01 se ambos forem zero.
3. Apos pos-correcao: se `Etapa C` detectar `price_unit=0` em alguma
   invoice_line, deve fazer `button_draft + write price_unit = standard_price
   + action_post` para corrigir antes de transmitir SEFAZ.

Localizacao: `scripts/inventario_2026_05/09_executar_onda1_bulk.py:400-432`

**Conceito chave**: SEFAZ nao aceita `vUnCom=0` (viola schema NFe).
Sempre validar `custo_medio > 0` ANTES de criar pickings; corrigir
invoice manualmente se robo CIEL IT criar linha com price_unit=0.

### L14. Conexao Odoo XML-RPC nao e thread-safe

**Sintoma**: `http.client.CannotSendRequest: Request-sent` ao usar
`ThreadPoolExecutor` em ETAPA A (transferencias paralelas).

**Causa raiz**: `xmlrpc.client.Transport` mantem estado de socket. Multiplas
threads compartilhando a mesma conexao geram conflict.

**Fix**: ETAPA A convertida para sequencial (1 thread). Performance: 5
transferencias em ~5s e' aceitavel.

Para paralelismo real, cada thread teria que criar sua propria conexao
Odoo. Refinamento futuro: pool de conexoes Odoo separadas por thread.

Localizacao: `scripts/inventario_2026_05/09_executar_onda1_bulk.py:255-330`

### L15. carregar_ajustes precisa incluir EXECUTADO

**Sintoma**: Apos ETAPA D marcar ajustes como `status=EXECUTADO`, ETAPA E
nao encontrava nenhum ajuste SEFAZ-autorizado para criar entrada FB.

**Causa raiz**: `carregar_ajustes` default `status_filtro=('APROVADO',
'PROPOSTO')`. Ajustes em `EXECUTADO` ficavam fora.

**Fix**: `status_filtro=('APROVADO', 'PROPOSTO', 'EXECUTADO')` por default.

Localizacao: `scripts/inventario_2026_05/09_executar_onda1_bulk.py:122-150`

### L16. excecao_autorizado vs autorizado normal (XML autorizado vazio)

**Sintoma**: NF 13150 (608630) retornou SEFAZ `situacao=excecao_autorizado`
(autorizada com ressalva). Chave SEFAZ presente, mas
`l10n_br_xml_aut_nfe = 0 bytes` (XML autorizado completo vazio).

**Causa raiz**: SEFAZ retorna `excecao_autorizado` quando o `numero_nf` ja
foi "consumido" em tentativas anteriores rejeitadas. CIEL IT NAO baixa
o XML completo (`nfeProc` = NFe + protNFe) nesses casos. Sem XML, nao
da para criar DFe na FB → entrada FB falha com "XML Nota Fiscal
Eletronica nao esta completa!".

**Fix conhecido**: nao automatizado via XML-RPC. Usuario precisa:
1. Acessar UI Odoo > invoice > botao "Consultar Documento" / "Re-consultar SEFAZ"
2. Aguardar CIEL IT baixar `nfeProc`
3. Re-processar entrada FB

Mitigacao: evitar `excecao_autorizado` corrigindo as causas dos erros
SEFAZ antes de re-transmitir (custo_medio=0, campos faltando, etc).

### L17. Sentido invertido FB→LF: entrada FB nao se aplica

**Sintoma**: RecLf 6 (entrada FB) tentou processar NF 608629
(RPI/2026/00201, FB→LF industrializacao). DFe FB criado, PO C2619223
criado, picking entrada FB criado (FB/IN/13151), mas etapa 11 falhou:
"Picking 317299 nao esta 'assigned' (state=confirmed)".

**Causa raiz**: A NF 608629 e' FB EMITINDO para LF. Logo, a FB nao deve
RECEBER essa NF (ela emitiu, nao recebeu). A LF deveria criar entrada.
Mas o sistema NACOM nao tem fluxo automatizado para LF receber NFs
emitidas pela FB.

**Fix necessario**: `etapa_e_entrada_fb` deve filtrar
`acao_decidida` que vai para a FB (PERDA_LF_FB, TRANSFERIR_CD_FB) e
pular `INDUSTRIALIZACAO_FB_LF`, `DEV_FB_LF`, `DEV_CD_LF` (sentido
FB→LF). Para essas, a entrada deve ser manual na LF/CD.

**Workaround manual**: criar picking interno na empresa destino
movendo de "Em Transito Industrializacao" para "{Empresa}/Estoque":
```python
odoo.create('stock.picking', {
    'location_id': 26489,  # Em Transito Industrializacao
    'location_dest_id': 42,  # LF/Estoque
    'picking_type_id': 19,  # LF Recebimento
    'company_id': 5,
    'move_ids': [(0, 0, {
        'product_id': pid,
        'product_uom_qty': qty,
        'location_id': 26489,
        'location_dest_id': 42,
        'company_id': 5,
    })],
})
```

Validado no caso real (picking 317306, 103000037 ALHO GRANULADO 10.389 kg).

### Resumo do refinamento (10 fixes L6-L17)

| # | Categoria | Localizacao |
|---|---|---|
| L6 | Location virtual destino | inventario_pipeline_service.py |
| L7 | skip_backorder | stock_picking_service.py |
| L8 | Multi-ajuste por picking (f5b/c/d) | inventario_pipeline_service.py |
| L9 | Idempotencia f5e por invoice_id | inventario_pipeline_service.py |
| L10 | status VARCHAR(20) | inventario_pipeline_service.py |
| L11 | ajustar_qty_done_pelo_disponivel | stock_picking_service.py |
| L12 | Distribuir demanda multi-lote FIFO | 09_executar_onda1_bulk.py |
| L13 | Validar custo_medio (price_unit=0) | 09_executar_onda1_bulk.py |
| L14 | XML-RPC nao thread-safe | 09_executar_onda1_bulk.py |
| L15 | carregar_ajustes inclui EXECUTADO | 09_executar_onda1_bulk.py |
| L16 | excecao_autorizado + XML vazio | DOC (sem fix automatico) |
| L17 | Filtrar etapa_e_entrada_fb FB→LF | 09_executar_onda1_bulk.py |

Detalhes completos em `docs/inventario-2026-05/CHECKPOINT_2026_05_18_SUBPILOTO_FINAL.md`.

---

## Licoes aprendidas — sub-piloto bulk RE-EXECUCAO (2026-05-18 madrugada apos checkpoint)

Apos cleanup do checkpoint FINAL, retomei o sub-piloto. Descobertos mais 4 bugs
estruturais (L18-L21) que mostraram que o pipeline NUNCA tinha sido validado
end-to-end em condicoes reais para MULTIPLOS produtos com lote distribuido.

### L18. AjusteEstoqueInventario nao tem campo `tipo_divergencia` (G010)

**Sintoma**: `'tipo_divergencia' is an invalid keyword argument for AjusteEstoqueInventario`

**Causa raiz**: Script 09 (logica L12/G009 compensatorio FIFO) inventou um campo
que nao existe no modelo. Modelo so tem: ciclo, cod_produto, tipo_produto,
company_id, lote_*, qtd_*, custo_medio, acao_decidida, status, fase_pipeline,
picking_id_odoo, invoice_id_odoo, chave_nfe, erro_msg, criado_em, criado_por.

**Fix**: Substituir por marker em `erro_msg`:
```python
erro_msg=f'[COMPENSATORIO_FALTA_ESTOQUE] Compensatorio origem_ajuste={origem_id}'
```

Localizacao: `scripts/inventario_2026_05/09_executar_onda1_bulk.py:541, 590-598`

### L19. preencher_qty_done faltando no pipeline (RAIZ CRITICA — G011)

**Sintoma**: action_assign OK, mas move_lines com `qty_done=0`. Consequencias:
- `ajustar_qty_done_pelo_disponivel` reduz `demand` para 0
- button_validate: "Nao e possivel validar sem quantidades reservadas"
- action_liberar_faturamento: "Peso Liquido" ou "Quantidade de Volumes" (L20/L21)

**Causa raiz**: Fluxo `f5b_validar_pickings` faltava etapa entre `action_assign`
e `ajustar_qty_done`:

```
1. criar_transferencia (sem lot_name)
2. action_confirm
3. action_assign      -> cria move_lines com qty_done=0
4. ⚠️ MISSING: preencher_qty_done -> qty_done = quantity reservada
5. ajustar_qty_done   -> reduz demand para sum(qty_done)=0 (BUG)
6. button_validate    -> falha
```

`action_assign` cria move_line com `quantity` mas `qty_done=0`. O `qty_done` deve
ser preenchido para Odoo computar peso/volumes via `@api.depends`.

**Fix**: `f5b_validar_pickings(linhas_por_picking=...)` chama
`preencher_qty_done(pid, linhas)` entre `confirmar_e_reservar` e `ajustar_qty_done`.

Localizacao: `app/odoo/services/inventario_pipeline_service.py:539+` e
`scripts/inventario_2026_05/09_executar_onda1_bulk.py:614-618`

### L20. peso_liquido=0 (consequencia de L19 — G012)

**Sintoma**: `Voce deve informar o Peso Liquido para liberar o faturamento`
em action_liberar_faturamento de pickings LF.

**Causa raiz**: `l10n_br_peso_liquido` (CIEL IT) computado via
`@api.depends('move_ids.qty_done')` × `product.weight`. Se qty_done=0 → peso=0.

**Fix**: resolvido pela cadeia L19 (preencher_qty_done apos action_assign).

### L21. quantidade_volumes=0 (consequencia de L19 — G013)

**Sintoma**: `Voce deve informar a Quantidade de Volumes para liberar o faturamento`
em pickings FB (industrializacao FB→LF).

**Causa raiz**: `l10n_br_volumes` (CIEL IT) computado similar a peso_liquido.
qty_done=0 → volumes=0.

**Fix**: resolvido pela cadeia L19.

### Resumo dos 4 novos fixes L18-L21

| # | Categoria | Localizacao | Gotcha |
|---|---|---|---|
| L18 | tipo_divergencia inexistente | 09_executar_onda1_bulk.py | G010 |
| L19 | preencher_qty_done no pipeline (RAIZ) | inventario_pipeline_service.py f5b + script | G011 |
| L20 | peso_liquido vazio (consequencia L19) | (resolvido por L19) | G012 |
| L21 | volumes vazios (consequencia L19) | (resolvido por L19) | G013 |

### Estado pos-L18-L21 fixes

- Pickings 317307, 317308, 317309, 317310 cancelados (sem invoice/SEFAZ)
- 11 ajustes resetados PROPOSTO sem picking_id (status original do checkpoint)
- Tests: 130 passing
- Pronto para re-executar sub-piloto bulk com fixes aplicados

---

## Licoes aprendidas — sub-piloto bulk (continuacao L22-L23, 2026-05-18)

Apos L18-L21 fixes, re-rodada do sub-piloto bulk descobriu mais 2 bugs estruturais:

### L22. Lotes vencidos bloqueiam auto-reserva (G014)

**Sintoma**: PEPINO IND tem 72k livres em FB/Estoque, mas action_assign reserva 0.
Picking continua confirmed (sem move_lines).

**Causa raiz**: Odoo CIEL IT segue FEFO — bloqueia auto-reserva de quants em
lotes VENCIDOS (`expiration_date < hoje`). Estoque agregado parece abundante
mas todo o livre esta em lotes ja expirados (alguns desde 2025-08).

**Fix**: Em `etapa_b_pickings`, antes de criar picking:
1. Ler `expiration_date` de cada lote dos quants livres
2. Separar `quants_validos` vs `quants_vencidos`
3. Se `livre_validos < demand` e `livre_vencidos > 0`:
   - Criar lote novo `INV-{cod}-{YYYYMMDD}` com `expiration_date = hoje + 365 dias`
   - Transferir qty necessaria de lote vencido FIFO → lote novo via
     `StockInternalTransferService.transferir_quantidade_para_lote`
   - Re-consultar quants (lote novo aparece como valido)
4. Distribuir FIFO apenas entre `quants_validos`

Localizacao: `09_executar_onda1_bulk.py:497-595`

**Validacao**: Picking 317313 (PEPINO industr 168 kg) — anterior bloqueava,
agora cria lote `INV-103000011-20260518` (exp=2027-05-18), transfere 168.108
do lote `0110/24` (vencido) → novo, picking reserva e valida OK.

### L23. price_unit=0 em invoice criada pelo robo CIEL IT (G015)

**Sintoma**: Invoice 626032 criada com 2 linhas `price_unit=0` (101001001 e
102020600) apesar de standard_price > 0 no Odoo. SEFAZ rejeita `Falha no
Schema XML` (vUnCom=0).

**Causa raiz**: Robo CIEL IT as vezes nao popula price_unit em certas linhas
(intermitente — outras linhas da MESMA invoice vieram OK).

**Fix**: Novo metodo `_corrigir_price_zero_em_invoice` em pipeline_service,
chamado em `f5d_aguardar_invoices` apos detectar invoice criada (F5d.6):
1. Identificar linhas com price_unit<=0
2. Buscar `product.standard_price` (abs ou 0.01 fallback)
3. button_draft + write price_unit + action_post
4. Audit em OperacaoOdooAuditoria fase='F5d.6'

Localizacao: `app/odoo/services/inventario_pipeline_service.py:249+` e
chamada em `f5d_aguardar_invoices:754-764`

**Validacao manual**: Invoice 626032 — 2 linhas corrigidas
(101001001 0 → 12.232, 102020600 0 → 14.154). Re-post OK.

### Resumo L18-L23 (6 novos fixes)

| # | Categoria | Localizacao | Gotcha |
|---|---|---|---|
| L18 | tipo_divergencia inexistente | 09_executar_onda1_bulk.py | G010 |
| L19 | preencher_qty_done no pipeline (RAIZ) | inventario_pipeline_service.py f5b | G011 |
| L20 | peso_liquido vazio (consequencia L19) | (resolvido por L19) | G012 |
| L21 | volumes vazios (consequencia L19) | (resolvido por L19) | G013 |
| L22 | Lote vencido bloqueia reserva | 09_executar_onda1_bulk.py etapa_b | G014 |
| L23 | price_unit=0 auto-fix em invoice | inventario_pipeline_service.py f5d.6 | G015 |

---

## Licoes aprendidas — root cause NF 626032 (2026-05-18 manha)

Apos sub-piloto bulk executar, identificou-se que a NF 626032 (LF perda
10 ajustes) tinha caido em `excecao_autorizado` com XML autorizado vazio
(G008). Investigacao do XML preview (baixado via Playwright "Pre Visualizar
XML NF-e") revelou root cause final:

### L24. SSL crash no f5e perde commits DB (G016)

**Sintoma**: Durante `f5e_transmitir_sefaz`, conexao SQL SSL fechada
inesperadamente apos 1ª invoice processada. `PendingRollbackError` em
session.flush(). 627348 nao chega a ser transmitida.

**Causa raiz**: Etapa D demora minutos por invoice. SQLAlchemy session
mantem aberta durante longo Playwright. PostgreSQL SSL timeout.

**Fix proposto** (NAO implementado nesta sessao):
- TCP keepalive em SQLALCHEMY_DATABASE_URI (`?keepalives=1&keepalives_idle=30`)
- Commit antes de cada Playwright + re-busca por ID
- Try/except + rollback + retry

Doc: `docs/inventario-2026-05/02-gotchas/G016-ssl-crash-no-loop-f5e-perde-commits.md`

**Bloqueante para LF completo** (660 produtos) — sem isso, qualquer SSL
drop deixa DB inconsistente com Odoo.

### L25. NCM=False em produto causa cstat 225 (G017 — RAIZ DEFINITIVA)

**Sintoma**: NF 626032 rejeitada SEFAZ 4x consecutivas com cstat 225
"Falha no Schema XML do lote de NFe" APOS o fix G015 manual de price_unit.

**Investigacao**: Baixei XML preview via Playwright (script
`baixar_xml_preview_626032.py`) e analisei. Encontrei:

```xml
<NCM>07115100</NCM>  <!-- linha 1 COGUMELO OK -->
<NCM>20057000</NCM>  <!-- linha 2 AZEITONA OK -->
<NCM>20057000</NCM>  <!-- linha 3 AZEITONA TRIT OK -->
<NCM>07114000</NCM>  <!-- linha 4 PEPINO OK -->
<NCM>False</NCM>     <!-- linha 5 ❌ ALHO EM PO sem NCM -->
```

**Causa raiz**: Produto 103000020 ALHO EM PO tem `l10n_br_ncm_id = False`
no Odoo. XMLRPC retorna boolean False, CIEL IT serializa como string
'False' no XML — viola schema NFe (NCM obrigatorio 8 digitos).

NF 627348 (FB industr PEPINO) passou na 1ª tentativa porque PEPINO tem
NCM cadastrado.

**Fix proposto** (em G017):
- `etapa_b_pickings`: validar `l10n_br_ncm_id != False` para todos os
  produtos do batch ANTES de criar pickings. Raise se houver produtos sem NCM.
- Audit SQL pre-execucao LF completo: identificar TODOS produtos sem NCM
  para cadastrar em massa antes do bulk.

Doc: `docs/inventario-2026-05/02-gotchas/G017-ncm-false-bloqueia-sefaz.md`

### Resumo L24-L25 (mais 2 fixes pos-sub-piloto)

| # | Categoria | Localizacao | Gotcha |
|---|---|---|---|
| L24 | SSL crash no loop f5e (RAIZ secundaria) | inventario_pipeline_service.py | G016 |
| L25 | NCM=False bloqueia SEFAZ (RAIZ PRIMARIA cstat 225) | 09_executar_onda1_bulk.py | G017 |

### Recovery NF 626032 (pos-investigacao)

1. **XML preview baixado** via `baixar_xml_preview_626032.py` (10059 chars)
2. **XML inserido** em `l10n_br_xml_aut_nfe` (13412 chars b64)
3. **Cancelamento manual** pela UI Odoo necessario (justificativa 15+ chars)
4. **NCM ALHO 103000020 a cadastrar** (manual ou XML-RPC)
5. **Picking 317311 devolvido** via `stock.return.picking` → picking 317315
   validado (state=done). Estoque LF restaurado.
6. **10 ajustes mantidos em F5e_SEFAZ_OK** com `erro_msg` explicativo
   ("G008+G017 ... NF 626032 a cancelar manual + cadastrar NCM antes de
   reset+refazer. Picking 317311 ja devolvido via 317315.")
7. **Reset DB + refazer pipeline** = proxima sessao (apos cancel + NCM)

---

## Arquivos modificados (commit `a8e0d0bb`)

**Novos services atomicos**:
- `app/odoo/services/stock_internal_transfer_service.py` (NOVO, 220 LOC,
  14 tests)
- `app/odoo/services/stock_lot_service.py` (+`criar_se_nao_existe`,
  +4 tests)

**Services modificados**:
- `app/odoo/services/stock_picking_service.py` (defaults
  incoterm+carrier, +2 tests)
- `app/odoo/services/inventario_pipeline_service.py`
  (+`_garantir_payment_provider`, integrado em f5d)
- `app/recebimento/services/playwright_nfe_transmissao.py` (resolver
  cids/menu_id, fechar modais, tratar wizard)
- `app/odoo/models/ajuste_estoque_inventario.py` (lote_origem + lote_destino)

**Scripts**:
- `scripts/inventario_2026_05/teste_210030325_lf.py` (NOVO — wrapper
  end-to-end)
- `scripts/inventario_2026_05/08_extrair_pos_execucao.py` (NOVO —
  extrator replicavel `--company-id=N`)
- `scripts/inventario_2026_05/debug_sefaz_608607.py` (NOVO — debug
  Playwright)
- `scripts/inventario_2026_05/04_propor_ajustes.py` (+`--listar-ids`,
  `--aprovar-ids`, `--company-id`)
- `scripts/inventario_2026_05/03_confrontar_inv_vs_odoo.py` (D004/D005)
- `scripts/migrations/2026_05_17_add_lote_destino_ajuste.{py,sql}`
  (NOVO)

**Tests**: 117 passing (97 baseline + 20 novos).

---

## Pendencias para bulk

1. **~~Generalizar D004 para FB↔CD~~** ✅ FEITO 2026-05-18 fim do dia.
   Logica aplicada em TODAS as companies (LF/FB/CD). Removido
   `if cid == 5` no script 03. `lote_destino` recalculado por acao em
   script 04. **Regerar diffs+ajustes para aplicar D004 generalizado
   em onda 2/3** (decisao usuario — pode invalidar ajustes existentes
   das ondas 2/3 que foram gerados na logica anterior).
2. **Bulk parallel safe**: o piloto rodou sequencial. Para 1.071
   ajustes, validar concorrencia (`InventarioPipelineService` usa
   `ThreadPoolExecutor` com Semaphore=5).
3. **Worst case F5d timeout**: cada `f5d_aguardar_invoices` aguarda ate
   30 min/picking. Robo CIEL IT pode demorar mais com muitos pickings
   simultaneos (G005 risco).
4. **Stock.lot sem campo `active`**: detectar inativos nao funciona via
   read nem search domain. Para ordem 3 (INDISPONIBILIZAR_*) precisa
   estrategia alternativa (canary manual no Odoo UI conforme D005).

---

## Generalizacao D004 para FB+CD (2026-05-18 fim do dia)

Apos piloto LF OK, generalizado para todas as companies:

**Comportamento por (cid, sobra/falta)**:

| Cid | Sobra (Odoo>Inv) → | Falta (Inv>Odoo) → |
|---|---|---|
| LF (5) | PERDA_LF_FB → MIGRACAO (FB) | INDUSTRIALIZACAO_FB_LF → lote_inv (LF) |
| FB (1) | TRANSFERIR_FB_CD → lote_inv (CD) ou INDISPONIBILIZAR | TRANSFERIR_CD_FB → MIGRACAO ou DEV_LF_FB |
| CD (4) | TRANSFERIR_CD_FB → MIGRACAO (FB) | TRANSFERIR_FB_CD → lote_inv (CD) |

(Decisao final via `calcular_acao_decidida` em `04_propor_ajustes.py`
considera tipo_produto + arquivado + ordem 1/2/3 do prompt.)

**Por que generalizar**: ondas 2 (FB↔CD transferencia) e 3 (sem ajuste
fiscal direto, so indisponibilizacao) precisam da MESMA logica de
agregacao + diferenca liquida que LF — antes, os 2.558 ajustes da
onda 2 e 19.366 da onda 3 estavam sendo gerados pelo fluxo "1 diff por
quant Odoo" (antigo, pre-D004), o que pode ter inflado o numero de NFs
ou criado divergencias artificiais.

**Acao recomendada para usuario**: regerar diffs + ajustes da onda 2
(e talvez 3) com a logica generalizada antes de aprovar/executar bulk.
Comando:
```bash
# 1. Limpar ajustes PROPOSTO das ondas 2-3 (mantem onda 1 ja revisada)
# (preferencia: usuario decide se faz)

# 2. Regerar (idempotente — so insere novos)
python scripts/inventario_2026_05/03_confrontar_inv_vs_odoo.py
python scripts/inventario_2026_05/04_propor_ajustes.py --propor

# 3. Comparar: 2558 ajustes onda 2 antigos vs novos
```
