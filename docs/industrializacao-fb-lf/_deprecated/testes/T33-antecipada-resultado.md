# T33 (ANTECIPADA) — Desativar BoM 14833 (subcontract antiga)

**Status final**: ✅ done (antecipada — originalmente planejada como pós-piloto)
**Executado em**: 2026-05-28
**Executor**: Claude (write XML-RPC) com autorização Rafael
**Decisão originadora**: D18 (sessão 2026-05-28) — antecipar T33 para garantir que Odoo escolha o caminho Opção 2 (inter-company normal) em T13, em vez de subcontract antigo (BoM 14833).

## Comando

```python
conn.write('mrp.bom', 14833, {'active': False})
```

## Antes / depois

| | Antes | Depois |
|---|---|---|
| `mrp.bom` id=14833 `active` | True | **False** |

## Pré-validação (CHK1 da sessão)

- 0 MOs ativas usando 14833 (state ∈ draft/confirmed/progress/to_close/assigned/waiting)
- 0 MOs done recentes usando 14833 (busca últimas 5)
- 0 pickings ativos em pt=74 FB Subcontratação

Desativação 100% segura, sem efeito sobre fluxos em curso.

## Estado pós-desativação

BoMs ATIVAS do produto piloto 4870112:

```
bom=3646 type=normal  cmp=LF  cons=strict  [3800018] BATELADA DE SHOYU
bom=3695 type=normal  cmp=LF  cons=strict  [4870112] MOLHO SHOYU - PET 12X1,01 L - CAMPO BELO
```

Apenas o caminho Opção 2 (inter-company + MO normal LF + BoM hierárquica 3695→3646) está disponível. Não há mais ambiguidade na escolha de BoM.

## Por que antecipou

Roadmap original (T33) previa desativar 14833 SÓ APÓS o piloto validar (D13). Mas Rafael autorizou antecipar pelo seguinte risco:

- BoMs ativas conflitantes: 14833 (subcontract FB, sub=[35]) + 3695 (normal LF)
- Quando o PO FB→LF para o partner LF (35) entrar, o módulo `mrp_subcontracting` pode disparar via 14833 (subcontract path) **antes** do `sale_purchase_inter_company_rules` criar SO em LF.
- Resultado seria: MO subcontract em FB (cmp=1), não MO normal em LF (cmp=5). Anularia a Opção 2 silenciosamente.

Desativar 14833 elimina a ambiguidade.

## Rollback

```python
conn.write('mrp.bom', 14833, {'active': True})
```

(Rollback reativa a BoM subcontract. Não afeta histórico de MOs/pickings.)

## Implicação na T33 original do roadmap

T33 antiga (pós-piloto): mantida no roadmap como ✅ done antecipada. Não é necessário re-executar.
