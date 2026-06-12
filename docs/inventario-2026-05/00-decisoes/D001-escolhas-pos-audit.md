<!-- doc:meta
tipo: explanation
camada: L3
sot_de: —
hub: docs/inventario-2026-05/00-decisoes/INDEX.md
superseded_by: —
atualizado: 2026-06-03
-->
# D001 — Escolhas pós-audit: MATRIZ_INTERCOMPANY final

> **Papel:** D001 — Escolhas pós-audit: MATRIZ_INTERCOMPANY final.

## Indice

- [COMPANY_LOCATIONS final](#company_locations-final)
- [PICKING_TYPES finais](#picking_types-finais)
- [MATRIZ_INTERCOMPANY final](#matriz_intercompany-final)
- [Surpresa importante: NF 147772 vem do CD, não da FB](#surpresa-importante-nf-147772-vem-do-cd-não-da-fb)
- [Itens em aberto (G003 — investigar)](#itens-em-aberto-g003-investigar)
- [Decisões a propagar](#decisões-a-propagar)
- [G003 — Resultado da investigação (2026-05-17)](#g003-resultado-da-investigação-2026-05-17)
  - [transf-filial CD → FB](#transf-filial-cd-fb)
  - [dev-industrializacao FB → LF](#dev-industrializacao-fb-lf)
  - [dev-industrializacao LF → FB](#dev-industrializacao-lf-fb)
  - [dev-industrializacao LF → CD](#dev-industrializacao-lf-cd)
- [G003 — Variacoes confirmadas (audit 00d)](#g003-variacoes-confirmadas-audit-00d)
- [Contexto](#contexto)

**Data:** 2026-05-17
**Origem:** F0 Task 0.1 + investigação G001/INV-002 (`00b_investigar_gotchas.py`)
**Resolve:** L1, L3 (parcial), L8 do spec; G001, INV-002
**Substituído por:** D002 (matriz final) e [D014](D014-cfop-entradas-e-operacoes-referencia.md) (entradas + CFOP por tipo de produto). A linha "dev-industrializacao LF→CD fp 64 REMESSA DE VASILHAME" desta página está **corrigida em D014** (fp 64 é `dev-vasilhame` LF→FB CFOP 5921).

## COMPANY_LOCATIONS final

Para `app/odoo/constants/locations.py`:

```python
COMPANY_LOCATIONS = {
    1: 8,    # FB — FB/Estoque
    4: 32,   # CD — CD/Estoque
    5: 42,   # LF — LF/Estoque
}
```

Confirmado em audit F0. SC (`company_id=3`) fora de escopo.

## PICKING_TYPES finais

Substituindo o que está em `.claude/references/odoo/IDS_FIXOS.md` (que tem `LF=16` errado):

| Company | Recebimento (principal) | Industrialização | Devoluções | Entre Filiais |
|---------|------------------------|------------------|------------|---------------|
| FB (1) | **1** | 52 | 6 | 54 |
| CD (4) | **13** | — | 18 | 50 |
| LF (5) | **19** | 64 | 24 | — |

**INV-002 resolvido**: `stock.picking.type id=16` é `Conferência (CD)`, code=`internal`, `active=False`. **Não tem nada a ver com LF**. Corrigir `IDS_FIXOS.md`.

## MATRIZ_INTERCOMPANY final

Para `app/odoo/constants/operacoes_fiscais.py`:

```python
MATRIZ_INTERCOMPANY = {
    'industrializacao': {
        'cfop': '5901',
        'l10n_br_tipo_pedido': 'industrializacao',
        'move_type': 'out_invoice',
        'direcao': ('FB', 'LF'),  # uni-direcional confirmado
        'tipo_produto': [1, 2, 3],
        'nf_referencia': 94457,
        'account_move_id_referencia': 607443,  # template direto
        'fiscal_position_id': {
            1: 25,  # FB: 'REMESSA PARA INDUSTRIALIZAÇÃO'
        },
        'partner_id_destino': {
            'LF': 35,  # res.partner.id de LA FAMIGLIA - LF
        },
    },
    'perda': {
        'cfop': '5903',
        'l10n_br_tipo_pedido': 'perda',
        'move_type': 'out_invoice',
        'direcao': ('LF', 'FB'),
        'tipo_produto': [1, 2, 3],
        'nf_referencia': 13075,
        'account_move_id_referencia': 588209,
        'fiscal_position_id': {
            5: 91,  # LF: 'SAÍDA - PERDAS'
        },
        'partner_id_destino': {
            'FB': 1,  # res.partner.id de NACOM GOYA - FB
        },
    },
    'dev-industrializacao': {
        'cfop': '5949',
        'l10n_br_tipo_pedido': 'dev-industrializacao',
        'move_type': 'out_invoice',
        'direcao': 'BIDIRECIONAL',  # CD↔LF na NF ref (surpresa!), mas pode ser FB↔LF
        'tipo_produto': [4],
        'nf_referencia': 147772,
        'account_move_id_referencia': 590839,
        'fiscal_position_id': {
            4: 74,  # CD: 'SAÍDA - REMESSA PARA RETRABALHO'
            # 1: ?  — FB precisa investigar (G003)
            # 5: ?  — LF precisa investigar (G003)
        },
        'partner_id_destino': {
            'LF': 35,
            # 'FB': 1, 'CD': 34 — direcoes inversas, ver G003
        },
    },
    'transf-filial': {
        'cfop': '5152',
        'l10n_br_tipo_pedido': 'transf-filial',
        'move_type': 'out_invoice',
        'direcao': 'BIDIRECIONAL_FB_CD',
        'tipo_produto': [1, 2, 3, 4],
        'nf_referencia': 94410,
        'account_move_id_referencia': 604472,
        'fiscal_position_id': {
            1: 20,  # FB: 'SAÍDA - TRANSFERÊNCIA ENTRE FILIAIS'
            # 4: ?  — CD precisa investigar (G003)
        },
        'partner_id_destino': {
            'CD': 34,
            # 'FB': 1 — direcao inversa, ver G003
        },
    },
}
```

## Surpresa importante: NF 147772 vem do CD, não da FB

O prompt do usuário (`prompt_inventario.md:106`) descreveu:
> `"dev-industrializacao"` - Saída entre **[FB,LF]** de produto [4] CFOP [5949]

Mas o audit revelou que a NF 147772 (ref) sai de **CD para LF**, não FB para LF.

**Implicação**: a operação dev-industrializacao pode ocorrer em **3 direções**, não 2:
- FB → LF (devolver retrabalho de produto da FB)
- CD → LF (devolver retrabalho de produto do CD)
- LF → FB ou LF → CD (devolução do retrabalho de volta)

Para o inventário 05/2026: vamos precisar mapear, para cada produto tipo 4 com ajuste na LF, **qual é a origem real do produto** (FB ou CD) antes de emitir a NF dev-industrializacao.

## Itens em aberto (G003 — investigar)

- [ ] `fiscal_position_id` de **dev-industrializacao** em FB (1) e LF (5) — direções inversas
- [ ] `fiscal_position_id` de **transf-filial** em CD (4) — direção CD→FB
- [ ] `partner_id_destino` completo (todos os caminhos)
- [ ] Confirmar regras de origem (FB×CD) para produtos tipo 4 em dev-industrializacao

Estes não bloqueiam a implementação dos services (`stock_lot_service`, `stock_picking_service`, `account_move_intercompany_service` base), mas bloqueiam a execução real das NFs nessas direções.

## Decisões a propagar

1. Atualizar `MATRIZ_INTERCOMPANY` em `app/odoo/constants/operacoes_fiscais.py` (Fase 1) com os valores acima
2. Atualizar `COMPANY_LOCATIONS` em `app/odoo/constants/locations.py` (Fase 1) com FB=8, CD=32, LF=42
3. Corrigir `.claude/references/odoo/IDS_FIXOS.md` (LF picking_type = 19, não 16) — fora desta branch, em main
4. Investigar G003 (fiscal_position_ids faltantes) antes da Fase 5 (execução)
5. Considerar premissa P11: dev-industrializacao tem 3+ direções possíveis (FB→LF, CD→LF, LF→origem)

---
## G003 — Resultado da investigação (2026-05-17)

### transf-filial CD → FB

- Nenhuma NF de SAÍDA com CFOP 5152 confirmada na company 4 ainda. Direcao pode nao ter precedente no Odoo — investigar manualmente.

### dev-industrializacao FB → LF

- Nenhuma NF de SAÍDA com CFOP 5949 confirmada na company 1 ainda. Direcao pode nao ter precedente no Odoo — investigar manualmente.

### dev-industrializacao LF → FB

`fiscal_position_id` candidatos:
- `[89, 'SAÍDA - RETRABALHO']` (exemplo: account.move.id=606403)

### dev-industrializacao LF → CD

`fiscal_position_id` candidatos:
- `[89, 'SAÍDA - RETRABALHO']` (exemplo: account.move.id=606403)


---
## G003 — Variacoes confirmadas (audit 00d)

Filtro partner_id restrito (companies em Santana de Parnaiba/SP):

| Direcao | CFOPs distribuidos | fiscal_position_id distintos |
|---|---|---|
| industrializacao FB → LF | 5901:10 | id=25 (REMESSA PARA INDUSTRIALIZAÇÃO) |
| perda LF → FB | 5903:10 | id=91 (SAÍDA - PERDAS) |
| dev-industrializacao FB → LF | — | — |
| dev-industrializacao CD → LF | 5949:10 | id=74 (SAÍDA - REMESSA PARA RETRABALHO) |
| dev-industrializacao LF → FB | — | — |
| dev-industrializacao LF → CD | 5949:10 | id=89 (SAÍDA - RETRABALHO); id=64 (REMESSA DE VASILHAME) |
| transf-filial FB → CD | 5152:10 | id=20 (SAÍDA - TRANSFERÊNCIA ENTRE FILIAIS) |
| transf-filial CD → FB | 5151:10 | id=49 (SAÍDA - TRANSFERÊNCIA ENTRE FILIAIS) |

## Contexto

ADR (decisao de arquitetura) — ciclo de inventario NACOM/LF/CD/FB 2026-05. Tema: Escolhas pós-audit: MATRIZ_INTERCOMPANY final
