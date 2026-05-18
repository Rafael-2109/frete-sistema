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
