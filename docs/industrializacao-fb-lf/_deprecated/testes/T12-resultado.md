# T12 — Mapear journals inter-company (informativo)

**Status final**: ✅ done
**Executado em**: 2026-05-28
**Executor**: Claude (`setup_s0.py --task T12`)
**Modo**: leitura informativa

## Output

```
[DRY] T12 — Verificar journals inter-company
[DRY]   FB (id=1):
[DRY]     SALE journals: [(1, 'VND'), (897, 'CBFB'), (1031, 'COMPL')]
[DRY]     PURCHASE journals: [(11, 'CMPMP'), (892, 'CPMPR'), (2, 'CMPUC')]
[DRY]   LF (id=5):
[DRY]     SALE journals: [(898, 'CBLF'), (857, 'CONS'), (1038, 'DVEND')]
[DRY]     PURCHASE journals: [(990, 'CEBLF'), (848, 'CMPMP'), (849, 'CMPUC')]
```

## Mapeamento

### FB (id=1)

| Tipo | Code | Journal id | Comentário |
|---|---|---|---|
| SALE | VND | 1 | Vendas gerais (default) |
| SALE | CBFB | 897 | Vendas inter-company FB→outra? |
| SALE | COMPL | 1031 | NF complementar |
| PURCHASE | CMPMP | 11 | Compras matéria-prima |
| PURCHASE | CPMPR | 892 | (a confirmar) |
| PURCHASE | CMPUC | 2 | Compras uso/consumo |

### LF (id=5)

| Tipo | Code | Journal id | Comentário |
|---|---|---|---|
| SALE | CBLF | 898 | Vendas inter-company LF→FB? |
| SALE | CONS | 857 | Consignação? |
| SALE | DVEND | 1038 | Devolução de venda |
| PURCHASE | CEBLF | 990 | Compras LF (entrada NF) |
| PURCHASE | CMPMP | 848 | Compras matéria-prima |
| PURCHASE | CMPUC | 849 | Compras uso/consumo |

## Para T21/T22 (piloto)

A NF de remessa de FB→LF (CFOP 5901) precisa ser emitida em algum dos journals SALE de FB. Candidatos:

- **VND (1)** — vendas gerais. Mais seguro como default.
- **CBFB (897)** — talvez seja específico para inter-company com nome sugestivo "Conta Bancária FB"? Verificar com Contábil.
- **COMPL (1031)** — para a NF complementar do D14 (PO complementar).

A NF de retorno LF→FB (CFOPs 5124+5902+5903) precisa ser emitida em journal SALE de LF. Candidatos:

- **CBLF (898)** — análogo a CBFB.
- **CONS (857)** — consignação.

## Decisão pendente

Não há decisão a tomar agora — esta task é informativa. Quando T22 chegar (emitir NF saída FB CFOP 5901 via CIEL IT), o CIEL IT provavelmente escolhe o journal automaticamente baseado no `partner.l10n_br_cnpj` + CFOP. Validar nesse momento.

Se Fiscal pedir separação especial de NFs inter-company em journal dedicado (S2), criar journal específico (fora do escopo S0).

## Impacto

Nenhum. Informativo puro.
