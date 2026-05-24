"""app/odoo/estoque/_utils.py — gold-utils de estoque (helpers reutilizáveis).

**RESOLVERS DE PREMISSAS** — o que o subagente `gestor-estoque-odoo` pesquisa e
valida ANTES de operar (loop passo 4). Centraliza lógica que estava COPIADA em
vários scripts ad-hoc (ex.: resolver_produto duplicado em ajuste_inventario.py,
transferir_lote.py, etc.). Toda skill-átomo e o subagente resolvem premissas
DAQUI — fonte única. Ver `app/odoo/estoque/CLAUDE.md` §3 (contrato/premissas).

Conteúdo (cresce conforme as skills capinam):
  - EMPRESAS                      tupla de códigos válidos (FB/CD/LF) p/ argparse/validação
  - resolver_empresa(emp,local)   código -> {company_id, location_id} (constants)
  - resolver_produto(odoo,cod)    default_code -> {pid, tracking, name, active, n_matches}
  - (futuro) buscar_quant, resolver_lote, norm_lote/is_migracao — ao capinar transfer
"""
from typing import Dict, Optional

from app.odoo.constants.locations import COMPANY_LOCATIONS
from app.odoo.constants.operacoes_fiscais import CODIGO_PARA_COMPANY_ID

# Códigos de empresa válidos (FB/CD/LF) — fonte para choices de argparse e validação.
EMPRESAS = tuple(sorted(CODIGO_PARA_COMPANY_ID))


def resolver_empresa(empresa: str, *, local: Optional[int] = None) -> Dict:
    """Código de empresa (FB/CD/LF) -> {empresa, company_id, location_id}.

    location_id = `local` se informado; senão COMPANY_LOCATIONS[company_id].
    Raises ValueError se empresa desconhecida ou sem location mapeada (e sem `local`).
    """
    empresa = (empresa or '').strip().upper()
    company_id = CODIGO_PARA_COMPANY_ID.get(empresa)
    if company_id is None:
        raise ValueError(
            f'empresa {empresa!r} desconhecida (use {list(EMPRESAS)})')
    location_id = local or COMPANY_LOCATIONS.get(company_id)
    if location_id is None:
        raise ValueError(
            f'empresa {empresa} (company={company_id}) sem entrada em '
            f'COMPANY_LOCATIONS; informe `local` explicitamente')
    return {'empresa': empresa, 'company_id': company_id, 'location_id': location_id}


def resolver_produto(odoo, cod: str) -> Optional[Dict]:
    """default_code -> {pid, tracking, name, active, n_matches} | None.

    Escolhe o produto ATIVO se houver (senão o primeiro); reporta n_matches
    (>1 = default_code duplicado). Fonte única — substitui as cópias ad-hoc.
    """
    cod = str(cod).strip()
    if cod.endswith('.0'):  # default_code numérico lido como float
        cod = cod[:-2]
    res = odoo.search_read(
        'product.product', [['default_code', '=', cod]],
        ['id', 'active', 'tracking', 'name'], limit=10,
    )
    if not res:
        return None
    ativos = [r for r in res if r.get('active')]
    e = ativos[0] if ativos else res[0]
    return {
        'pid': e['id'],
        'tracking': e.get('tracking') or 'none',
        'name': e.get('name'),
        'active': bool(e.get('active')),
        'n_matches': len(res),
    }
