<!-- doc:meta
tipo: reference
camada: L3
sot_de: —
hub: docs/inventario-2026-05/02-gotchas/INDEX.md
superseded_by: —
atualizado: 2026-06-03
-->
# G017 — NCM=False em produto causa cstat 225 (Schema XML invalido)

> **Papel:** G017 — NCM=False em produto causa cstat 225 (Schema XML invalido).

## Indice

- [Sintoma](#sintoma)
- [Root cause](#root-cause)
- [Solução: validação pré-pickings](#solução-validação-pré-pickings)
- [Recovery NF ja rejeitada (caso 626032)](#recovery-nf-ja-rejeitada-caso-626032)
- [Como evitar (LF completo) — FIX IMPLEMENTADO](#como-evitar-lf-completo-fix-implementado)
- [Diagnóstico de outras NFs](#diagnóstico-de-outras-nfs)
- [Ref](#ref)

**Descoberta**: 2026-05-18 root cause analysis NF 626032
**Severidade**: HIGH (NF rejeitada SEFAZ + risco excecao_autorizado G008)
**Status**: ✅ **FIX IMPLEMENTADO** (2026-05-18 manha sessao 2) em
`scripts/inventario_2026_05/09_executar_onda1_bulk.py:139-211` —
funcao `validar_cadastro_fiscal` + flag CLI `--validacao-fiscal`.
Tambem cobre G012/G013 (weight=0).

---

## Sintoma

NF emitida via robo CIEL IT, transmitida via Playwright, rejeitada SEFAZ
6x com `cstat=225 Falha no Schema XML do lote de NFe`. Após 5 tentativas
rejeitadas, SEFAZ pode marcar como `excecao_autorizado` (G008) — chave
SEFAZ consumida MAS XML autorizado vazio.

## Root cause

XML preview da NF (baixado via "Pré Visualizar XML NF-e") mostra:

```xml
<NCM>07115100</NCM>  <!-- linha 1 OK -->
<NCM>20057000</NCM>  <!-- linha 2 OK -->
<NCM>20057000</NCM>  <!-- linha 3 OK -->
<NCM>07114000</NCM>  <!-- linha 4 OK -->
<NCM>False</NCM>     <!-- linha 5 ❌ ALHO EM PÓ sem NCM -->
```

O XMLRPC retorna `False` (boolean Python) quando o campo many2one
`l10n_br_ncm_id` está vazio no produto. CIEL IT serializa `False` como
string `'False'` no XML — violando schema NFe (NCM deve ser 8 digitos).

Caso real (NF 626032 RETNA/2026/00032):
- Produto 103000020 ALHO EM PÓ: `l10n_br_ncm_id = False` em product.product
- 4 outros produtos da mesma NF tinham NCM cadastrado

## Solução: validação pré-pickings

Em `etapa_b_pickings` (script `09_executar_onda1_bulk.py`), adicionar
validação ANTES de criar picking:

```python
def validar_cadastro_fiscal(odoo, pids: List[int]) -> Dict[str, List[str]]:
    """Valida campos fiscais obrigatorios para SEFAZ.
    
    Returns:
        {'sem_ncm': [...], 'sem_outros': [...]}.
    """
    prods = odoo.read('product.product', pids,
        ['default_code', 'name', 'l10n_br_ncm_id'])
    sem_ncm = [
        f"{p['default_code']} ({p['name'][:30]})"
        for p in prods
        if not p.get('l10n_br_ncm_id')
    ]
    return {'sem_ncm': sem_ncm}

# Antes de criar pickings:
issues = validar_cadastro_fiscal(odoo, list(prod_cache.values()))
if issues['sem_ncm']:
    raise RuntimeError(
        f"NCM ausente em {len(issues['sem_ncm'])} produtos: "
        f"{issues['sem_ncm']}. Cadastrar l10n_br_ncm_id antes de rodar bulk."
    )
```

Para LF completo (660 produtos), audit SQL pre-execucao:

```python
# Query todos produtos do batch
cods_distintos = sorted({a.cod_produto for a in ajustes_pendentes})
prods = odoo.search_read('product.product',
    [['default_code', 'in', cods_distintos]],
    ['default_code', 'l10n_br_ncm_id', 'l10n_br_cest_id'])

sem_ncm = [p['default_code'] for p in prods if not p.get('l10n_br_ncm_id')]
if sem_ncm:
    print(f"⚠️ {len(sem_ncm)} produtos sem NCM: {sem_ncm[:20]}")
    # Decidir: cadastrar NCMs manualmente OU excluir do batch
```

## Recovery NF ja rejeitada (caso 626032)

Apos identificar produto sem NCM:

1. **Cadastrar NCM no produto** via UI Odoo ou XML-RPC:
   ```python
   # Buscar NCM compativel ao produto
   ncm = odoo.search_read('l10n_br_fiscal.ncm',
       [['code_unmasked', '=', '07129090']], ['id'], limit=1)
   if ncm:
       odoo.write('product.product', [27709],  # ALHO EM PÓ
           {'l10n_br_ncm_id': ncm[0]['id']})
   ```

2. **Baixar XML autorizado** (G008 recovery) — usar
   `scripts/inventario_2026_05/baixar_xml_preview_626032.py`:
   - Login Odoo
   - Clica "Pré Visualizar XML NF-e"
   - Captura `download` (não abre nova aba — gera arquivo)
   - Escreve em `l10n_br_xml_aut_nfe` via base64

3. **Cancelar NF SEFAZ** via UI Odoo:
   - Botão "Cancelar NFe"
   - Justificativa min 15 chars (ex: "Inventario 2026-05 LF: NFe com
     Schema XML invalido (cstat 225) - re-emissao corrigida")

4. **Devolver picking** correspondente via `stock.return.picking` wizard

5. **Reset DB local**: ajustes para PROPOSTO sem picking_id/fase

6. **Refazer pipeline** com fix G017 ativo

## Como evitar (LF completo) — FIX IMPLEMENTADO

A funcao `validar_cadastro_fiscal(odoo, prod_cache, modo)` agora roda
automaticamente em `etapa_b_pickings` antes de criar pickings:

- `modo='strict'` (default): raise RuntimeError listando produtos sem
  NCM ou weight, aborta etapa B.
- `modo='warn'`: imprime aviso e segue (USAR COM CUIDADO).
- `modo='skip'`: nao valida (apenas se houver razao explicita).

Flag CLI:

```bash
python scripts/inventario_2026_05/09_executar_onda1_bulk.py \
    --company-id=5 --onda=1 --confirmar \
    --validacao-fiscal=strict   # default
```

Audit pre-bulk (escopo onda 1 LF):

```sql
SELECT DISTINCT cod_produto FROM ajuste_estoque_inventario
WHERE ciclo='INVENTARIO_2026_05' AND company_id=5 AND status='PROPOSTO'
  AND acao_decidida IN (
    'PERDA_LF_FB', 'INDUSTRIALIZACAO_FB_LF',
    'DEV_LF_FB', 'DEV_FB_LF', 'DEV_LF_CD', 'DEV_CD_LF',
    'TRANSFERIR_CD_FB', 'TRANSFERIR_FB_CD',
    'RENOMEAR_LOTE', 'TRANSFERIR_LOTE'
  )
ORDER BY cod_produto;
```

E para cada produto, query no Odoo `product.product.l10n_br_ncm_id`.
Snapshot atual (2026-05-18): 3 produtos sem NCM, 109 sem weight em
acao de picking (`docs/inventario-2026-05/07-relatorios/audit_fiscal_LF.md`).

## Diagnóstico de outras NFs

A NF 626032 teve 5 linhas, apenas 1 sem NCM. Mesmo padrão pode acontecer
em outras NFs do bulk se algum produto tiver cadastro fiscal incompleto.

Recommended audit para LF completo:
- l10n_br_ncm_id (CRITICO)
- l10n_br_cest_id (depende NCM/UF)
- list_price ou standard_price > 0 (G007)
- weight > 0 (G012/G013)

## Ref

- G007 (price_unit=0 — caso similar de cadastro incompleto)
- G008 (excecao_autorizado — consequencia de tentativas SEFAZ rejeitadas)
- G015 (proteção price_unit=0 automatica em f5d.6)
- D006 secao a adicionar
