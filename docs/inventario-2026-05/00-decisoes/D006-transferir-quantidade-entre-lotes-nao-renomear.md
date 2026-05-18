# D006 — Transferir quantidade entre lotes (NAO renomear)

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

## Pendencias para bulk (onda 1 — 1.071 ajustes LF)

1. **Generalizar D004 para FB↔CD**: a logica `_custo_medio_cod` +
   "rename+diferenca liquida" so foi aplicada em `cid=5` (LF) no script
   03. Generalizar para FB (cid=1) e CD (cid=4) quando rodar ondas 2.
2. **Bulk parallel safe**: o piloto rodou sequencial. Para 1.071
   ajustes, validar concorrencia (`InventarioPipelineService` usa
   `ThreadPoolExecutor` com Semaphore=5).
3. **Worst case F5d timeout**: cada `f5d_aguardar_invoices` aguarda ate
   30 min/picking. Robo CIEL IT pode demorar mais com muitos pickings
   simultaneos (G005 risco).
4. **Stock.lot sem campo `active`**: detectar inativos nao funciona via
   read nem search domain. Para ordem 3 (INDISPONIBILIZAR_*) precisa
   estrategia alternativa (canary manual no Odoo UI conforme D005).
