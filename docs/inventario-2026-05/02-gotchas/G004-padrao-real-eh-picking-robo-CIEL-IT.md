<!-- doc:meta
tipo: reference
camada: L3
sot_de: —
hub: docs/inventario-2026-05/02-gotchas/INDEX.md
superseded_by: —
atualizado: 2026-06-03
-->
# G004 — Padrão real de NF inter-company é picking + robô CIEL IT, não account.move direto

> **Papel:** G004 — Padrão real de NF inter-company é picking + robô CIEL IT, não account.move direto.

## Indice

- [Padrão verdadeiro do sistema NACOM (extraído de `recebimento_lf_odoo_service.py`)](#padrão-verdadeiro-do-sistema-nacom-extraído-de-recebimento_lf_odoo_servicepy)
- [O que estava errado no design](#o-que-estava-errado-no-design)
- [Padrão correto (reescrito)](#padrão-correto-reescrito)
- [Decisões necessárias](#decisões-necessárias)
  - [Decisão D004-A: Padrão para ajuste de inventário](#decisão-d004-a-padrão-para-ajuste-de-inventário)
- [Impactos no spec original](#impactos-no-spec-original)

**Descoberto em:** 2026-05-17 (audit 00e + leitura `recebimento_lf_odoo_service.py:2122-2700`)
**Severidade:** **CRITICA** — invalida parcialmente o design original do spec

## Padrão verdadeiro do sistema NACOM (extraído de `recebimento_lf_odoo_service.py`)

Para transferências inter-company (FB→CD), o sistema **NÃO cria** `account.move` diretamente via XML-RPC. Ao invés disso:

```
1. Criar stock.picking OUTGOING
   - picking_type_id: 51 (Expedição Entre Filiais FB)
   - location_id: 8 (FB/Estoque)
   - location_dest_id: 5 (Parceiros/Clientes — virtual!)
   - partner_id: 34 (res.partner da company destino)
   - incoterm_id: CIF (OBRIGATORIO)
   - carrier_id: 996 (transportadora propria — OBRIGATORIO)
   - move_ids: produtos + quantidades

2. action_confirm + action_assign + preencher lotes + button_validate
   (fire-and-poll, trata 'cannot marshal None')

3. action_liberar_faturamento (no picking) — sinaliza para o robô CIEL IT

4. AGUARDAR robô CIEL IT criar account.move automaticamente
   (até 30 min de polling, busca via ref=picking_name)

5. Transmitir NF-e via Playwright UI (campos nfe_infnfe_* stale via XML-RPC,
   SEFAZ erro 225 se transmitir sem Playwright)
```

## O que estava errado no design

O spec/plano original (v2, `2026-05-17-ajuste-inventario-nacom-lf-design.md`) projetava:

```python
account_move_intercompany_service.executar(payload)
  # cria account.move via XML-RPC
  # chama action_post
```

**Não funciona para o padrão NACOM**:
- Account.move criado via XML-RPC tem `nfe_infnfe_*` stale → SEFAZ 225
- Pode não gerar picking, gerar picking errado, ou impedir movimento de estoque
- Não há precedente histórico de NF de transf-filial criada via XML-RPC direto

## Padrão correto (reescrito)

O service deve **orquestrar 5 etapas** (espelhando `recebimento_lf_odoo_service`):

```python
class AccountMoveIntercompanyService:
    def executar(self, payload):
        # Etapa 1: Criar picking via stock_picking_service
        picking_id = self.stock_picking_svc.criar_transferencia(...)
        # Etapa 2: Confirmar + reservar + preencher lotes
        self.stock_picking_svc.confirmar_e_reservar(picking_id)
        self.stock_picking_svc.preencher_qty_done(picking_id, linhas)
        # Etapa 3: Validar (button_validate)
        self.stock_picking_svc.validar(picking_id)
        # Etapa 4: action_liberar_faturamento
        odoo.execute_kw('stock.picking', 'action_liberar_faturamento',
                        [[picking_id]])
        # Etapa 5: Aguardar robô criar account.move (fire-and-poll)
        invoice_id = self._aguardar_invoice_robo(picking_id)
        # Etapa 6: Transmitir via Playwright UI (separado)
        # ...
        return invoice_id
```

## Decisões necessárias

### Decisão D004-A: Padrão para ajuste de inventário

**Opção 1**: Seguir o padrão NACOM (picking → robô → SEFAZ) — **maior precedente, fiscalmente seguro, mas mais complexo**
- Requer Playwright para todas as NFs (rede de seguranca SEFAZ 225)
- Requer `action_liberar_faturamento` (verificar se existe para todas as 4 operações: industrializacao, perda, dev, transf-filial — `recebimento_lf` usa apenas para transf-filial)
- Aguardo de até 30 min por NF (não escalavel para bulk)

**Opção 2**: account.move direto (modelo do spec original) — **mais simples, mas SEM PRECEDENTE**
- Risco: SEFAZ 225, picking não criado, movimentações errado
- Provavelmente não funciona no Odoo CIEL IT atual

**Opção 3**: Híbrido — picking automatizado via XML-RPC + transmissão Playwright orquestrada
- Para inventário (não-bulk crítico): aceitar 30 min por NF
- Para operações futuras com diferentes características: revisitar

## Impactos no spec original

Será necessário **reescrever §6.2 do spec** (arquitetura dos services):

- `account_move_intercompany_service` muda de **criador** para **orquestrador** (picking → robô → Playwright)
- `stock_picking_service` é **dependência** crítica, não auxiliar
- Adicionar dependência **Playwright** (já em `app/recebimento/services/playwright_nfe_transmissao.py`)
- Aguardar robô = **fire-and-poll de até 30 min** por NF
- Implica **revisar a Fase 5 (execução)** do plano: bulk de 50+ NFs significaria 50 × 30min = 25h
