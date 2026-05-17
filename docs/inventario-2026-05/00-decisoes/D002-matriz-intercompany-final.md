# D002 — MATRIZ_INTERCOMPANY final (após audit 00d)

**Data:** 2026-05-17
**Resolve:** G003 (com info correta sobre Santana de Parnaiba/SP)
**Substitui:** seções da matriz em D001 (parcialmente errada por falso positivo)

## Correção do falso positivo

A NF `SPI/2026/00007` (id=559045) retornada em 00c como "FB→LF" era na verdade:
- `partner_id`: 88012 = **BIDOLUX** (não LA FAMIGLIA)
- `state_id`: Santa Catarina (interestadual)
- CFOP 6902 (saída interestadual produto industrializado)

Filtro restrito por `partner_id` em 00d eliminou o falso positivo. Confirma: **FB, CD, LF todas em Santana de Parnaíba/SP**, todas as operações intra-estaduais.

## MATRIZ_INTERCOMPANY confirmada

```python
MATRIZ_INTERCOMPANY = {
    'industrializacao': {
        'l10n_br_tipo_pedido': 'industrializacao',
        'move_type': 'out_invoice',
        'tipo_produto': [1, 2, 3],
        'fiscal_position_id': {
            (1, 5): 25,  # FB → LF: REMESSA PARA INDUSTRIALIZAÇÃO
        },
        'cfop_esperado': {'5901': True},  # informacional, Odoo decide
        'nf_referencia': 94457,
        'account_move_id_referencia': 607443,
        'nfs_historicas_10_recentes': 10,
    },
    'perda': {
        'l10n_br_tipo_pedido': 'perda',
        'move_type': 'out_invoice',
        'tipo_produto': [1, 2, 3],
        'fiscal_position_id': {
            (5, 1): 91,  # LF → FB: SAÍDA - PERDAS
        },
        'cfop_esperado': {'5903': True},
        'nf_referencia': 13075,
        'account_move_id_referencia': 588209,
        'nfs_historicas_10_recentes': 10,
    },
    'dev-industrializacao': {
        'l10n_br_tipo_pedido': 'dev-industrializacao',
        'move_type': 'out_invoice',
        'tipo_produto': [4],
        'fiscal_position_id': {
            (4, 5): 74,  # CD → LF: SAÍDA - REMESSA PARA RETRABALHO
            (5, 4): 89,  # LF → CD: SAÍDA - RETRABALHO (mais comum)
            # Variante (5, 4): 64 'REMESSA DE VASILHAME' aparece em historico
            # antigo — usar 89 como default; auditar se vasilhame eh relevante
        },
        'cfop_esperado': {'5949': True},
        'nf_referencia': 147772,
        'account_move_id_referencia': 590839,
        'nfs_historicas_10_recentes': 10,
        'direcoes_sem_precedente_historico': [
            (1, 5),  # FB → LF
            (5, 1),  # LF → FB
        ],
    },
    'transf-filial': {
        'l10n_br_tipo_pedido': 'transf-filial',
        'move_type': 'out_invoice',
        'tipo_produto': [1, 2, 3, 4],
        'fiscal_position_id': {
            (1, 4): 20,  # FB → CD: SAÍDA - TRANSFERÊNCIA ENTRE FILIAIS
            (4, 1): 49,  # CD → FB: SAÍDA - TRANSFERÊNCIA ENTRE FILIAIS
        },
        'cfop_esperado': {'5152': '(1,4)', '5151': '(4,1)'},
        'nf_referencia': 94410,
        'account_move_id_referencia': 604472,
        'nfs_historicas_10_recentes': 10,
    },
}


COMPANY_PARTNER_ID = {
    1: 1,    # FB
    4: 34,   # CD
    5: 35,   # LF
}


COMPANY_LOCATIONS = {
    1: 8,    # FB/Estoque
    4: 32,   # CD/Estoque
    5: 42,   # LF/Estoque
}
```

## Direções sem precedente histórico — atenção do Rafael

| Direção | Tipo | Status |
|---|---|---|
| `(1, 5)` FB → LF | dev-industrializacao | **0 NFs históricas** |
| `(5, 1)` LF → FB | dev-industrializacao | **0 NFs históricas** |

Hipótese: o fluxo padrão de retrabalho é **CD ↔ LF** (CD envia, LF devolve para CD). Faz sentido — CD é o distribuidor que detecta produtos com problema; LF é quem retraba; produto volta para CD para distribuição.

**FB nunca participa de dev-industrializacao** no histórico do Odoo.

### Implicação para o inventário

Se o inventário revelar produto **tipo 4** com ajuste **na LF** e o produto for de origem **FB** (não CD), a operação correta é provavelmente:

1. LF → CD (dev-industrializacao 5949, fiscal_pos 89)
2. CD → FB (transf-filial 5151, fiscal_pos 49)

Ou seja: para ajustar produto 4 na LF que pertence a FB, **2 NFs** podem ser necessárias (LF→CD→FB), não 1 (LF→FB direto).

**Pergunta para Rafael:** o sistema NACOM aceita LF→FB direto, mesmo sem precedente histórico? Ou devemos modelar como cadeia LF→CD→FB?

## Decisões finais propostas

1. `MATRIZ_INTERCOMPANY` usa `fiscal_position_id` por tupla `(origem, destino)`.
2. Service `account_move_intercompany_service.executar()` **não seta CFOP** — Odoo decide.
3. CFOP fica como `cfop_esperado` (informacional, para humanos e logs).
4. Para `dev-industrializacao` em ajustes de inventário de tipo 4 na LF: avaliar se cadeia LF→CD→FB é necessária quando produto origem é FB.

## Variante histórica em LF→CD: 89 vs 64

`(5, 4)` retornou 2 fiscal_positions em histórico:
- 89 SAÍDA - RETRABALHO (mais recente, padrão)
- 64 REMESSA DE VASILHAME (mais antigo, possivelmente para vasilhame específico)

Default para inventário: usar **89**. Se ajuste envolver vasilhame, reavaliar.
