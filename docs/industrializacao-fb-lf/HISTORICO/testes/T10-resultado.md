# T10 — Alterar BoM 3695: consumption='strict'

**Status final**: ✅ done
**Executado em**: 2026-05-28
**Executor**: Claude (`setup_s0.py`) com autorização Rafael
**Modo**: dry-run → execute

## Comando

```bash
python docs/industrializacao-fb-lf/scripts/setup_s0.py --task T10 --execute
```

## Output execute

```
[EXEC] T10 — Alterar BoM 3695: consumption='strict'
[EXEC]   atual: [4870112] MOLHO SHOYU - PET 12X1,01 L - CAMPO BELO consumption=warning
[EXEC]   alterar para 'strict'
✅ Task T10 OK (result=True)
```

## Antes / depois

| Campo | Antes | Depois |
|---|---|---|
| `mrp.bom` id=3695 `consumption` | warning | **strict** |

## Validação pós-execução (XML-RPC)

```
mrp.bom id=3695 '[4870112] MOLHO SHOYU - PET 12X1,01 L - CAMPO BELO'
  consumption = 'strict'
  active = True
  type = 'normal'
  company_id = [5, 'LA FAMIGLIA - LF']
```

## Significado operacional

Implementa **Decisão D05 — Opção B strict**. A partir de agora, quando o PCP LF apontar uma MO baseada na BoM 3695:

- Tentativa de apontar `qty_done > qty_planejada × qty_produced` em qualquer componente: **bloqueada pelo Odoo** com mensagem de erro.
- Se ocorrer perda real > coeficiente de remessa: PCP LF aciona Compras FB via protocolo D14 (PO complementar com SLA <2h).

## Próxima task destravada

- T24 (apontamento da MO no piloto). Subcenário T24b (tentar consumir acima do planejado) agora pode ser validado de verdade.

## Idempotência

Re-executar `--execute` retornaria: `já strict (skip)`.
