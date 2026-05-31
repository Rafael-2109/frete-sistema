#!/usr/bin/env python3
"""
Setup Sprint 0 — Industrialização FB↔LF
Multi-task script. Cada task é idempotente e modular.

Uso:
    source .venv/bin/activate
    python docs/industrializacao-fb-lf/scripts/setup_s0.py --task T02 --dry-run
    python docs/industrializacao-fb-lf/scripts/setup_s0.py --task T02 --execute

Tasks disponíveis:
    T02 — Criar location LF/Materiais de Terceiros
    T03 — Criar location LF/PA de Terceiros
    T04 — Alterar property_stock_subcontractor da LF
    T05 — Reativar picking_type 74 (FB Subcontratação)
    T06 — Reativar picking_type 80 (LF Subcontratação)
    T07 — Criar picking_type LF/SAI/IND/RET
    T08 — Criar regras na rota 162
    T09 — Criar regras na rota 166 (avaliar necessidade)
    T10 — Alterar BoM 3695: consumption=strict
    T11 — Adicionar rota MTO ao 4870112 (cmp=LF)
    T12 — Verificar journals inter-company
    T33 — Desativar BoM 14833 (pós-piloto)
"""
import argparse
import sys
sys.path.insert(0, '/home/rafaelnascimento/projetos/frete_sistema')

from app.odoo.utils.connection import get_odoo_connection

# Constantes — VERIFICADAS EM 2026-05-28
CMP_FB = 1
CMP_LF = 5
WH_FB_ID = 1
WH_LF_ID = 4
LOC_FB_ESTOQUE = 8
LOC_LF_ESTOQUE = 42
LOC_EM_TRANSITO_IND = 26489
LOC_SUBCONTRATACAO_DEFAULT = 30713
PARTNER_LF_EM_FB = 35

# Picking types existentes
PT_FB_SAI_IND = 53
PT_RECEB_FB_IND = 52
PT_LF_RECEB_IND = 64
PT_RES_FB = 75
PT_FB_SUBCONTRATACAO = 74
PT_LF_SUBCONTRATACAO = 80

# Routes
ROUTE_FB_REPOSICAO_SUBCONTRATACAO = 162
ROUTE_LF_REPOSICAO_SUBCONTRATACAO = 166
ROUTE_LF_FABRICAR = 134

# Produto e BoMs
PRODUCT_PA_4870112 = 27834
BOM_SUBCONTRACT_FB = 14833
BOM_NORMAL_LF = 3695

# State global
DRY_RUN = True
LOG_PREFIX = "[DRY]"

def log(msg):
    print(f"{LOG_PREFIX} {msg}")

def setlog(dry):
    global DRY_RUN, LOG_PREFIX
    DRY_RUN = dry
    LOG_PREFIX = "[DRY]" if dry else "[EXEC]"

# Conexão Odoo (lazy)
_conn = None
def odoo():
    global _conn
    if _conn is None:
        _conn = get_odoo_connection()
    return _conn

# Helpers
def create_or_skip(model, search_domain, vals):
    """Cria registro se não existir; retorna id."""
    existing = odoo().search_read(model, search_domain, ['id'], limit=1)
    if existing:
        log(f"{model} já existe id={existing[0]['id']} (skip)")
        return existing[0]['id']
    log(f"create {model}: {vals}")
    if DRY_RUN:
        return f"DRY_{model}"
    return odoo().create(model, vals)

def write_or_skip(model, rec_id, vals):
    """Escreve campos se diferentes."""
    current = odoo().search_read(model, [('id','=',rec_id)], list(vals.keys()), limit=1)
    if not current:
        log(f"ERRO: {model} id={rec_id} não encontrado")
        return False
    needs_update = False
    for k, v in vals.items():
        cur_v = current[0].get(k)
        if isinstance(cur_v, list):
            cur_v = cur_v[0] if cur_v else None
        if cur_v != v:
            needs_update = True
    if not needs_update:
        log(f"{model} id={rec_id}: já está no estado desejado (skip)")
        return True
    log(f"write {model} id={rec_id}: {vals}")
    if not DRY_RUN:
        odoo().write(model, rec_id, vals)
    return True

# ========================================
# TASK IMPLEMENTATIONS
# ========================================

def task_T02():
    """Criar location LF/Materiais de Terceiros."""
    log("T02 — Criar location LF/Materiais de Terceiros")
    # Resolver WH LF view location
    wh = odoo().search_read('stock.warehouse',[('id','=',WH_LF_ID)],
                            ['view_location_id'], limit=1)[0]
    parent_id = wh['view_location_id'][0]
    log(f"  parent location: {wh['view_location_id'][1]} (id={parent_id})")

    vals = {
        'name': 'Materiais de Terceiros',
        'location_id': parent_id,
        'usage': 'internal',
        'company_id': CMP_LF,
        'active': True,
    }
    loc_id = create_or_skip('stock.location',
        [('name','=','Materiais de Terceiros'),('company_id','=',CMP_LF)],
        vals)
    log(f"  resultado: location id={loc_id}")
    return loc_id

def task_T03():
    """Criar location LF/PA de Terceiros."""
    log("T03 — Criar location LF/PA de Terceiros")
    wh = odoo().search_read('stock.warehouse',[('id','=',WH_LF_ID)],
                            ['view_location_id'], limit=1)[0]
    parent_id = wh['view_location_id'][0]
    vals = {
        'name': 'PA de Terceiros',
        'location_id': parent_id,
        'usage': 'internal',
        'company_id': CMP_LF,
        'active': True,
    }
    loc_id = create_or_skip('stock.location',
        [('name','=','PA de Terceiros'),('company_id','=',CMP_LF)],
        vals)
    log(f"  resultado: location id={loc_id}")
    return loc_id

def task_T04():
    """Alterar property_stock_subcontractor da LF (35) para LF/Materiais de Terceiros."""
    log("T04 — Alterar property_stock_subcontractor da LF")
    loc = odoo().search_read('stock.location',
        [('name','=','Materiais de Terceiros'),('company_id','=',CMP_LF)],
        ['id','complete_name'], limit=1)
    if not loc:
        log("ERRO: location LF/Materiais de Terceiros não encontrada. Execute T02 primeiro.")
        return False
    new_loc_id = loc[0]['id']
    log(f"  nova location: {loc[0]['complete_name']} (id={new_loc_id})")

    current = odoo().search_read('res.partner',[('id','=',PARTNER_LF_EM_FB)],
        ['name','property_stock_subcontractor'], limit=1)[0]
    cur_loc = current.get('property_stock_subcontractor')
    log(f"  atual: {cur_loc[1] if cur_loc else 'NULL'}")

    if cur_loc and cur_loc[0] == new_loc_id:
        log("  já configurado (skip)")
        return True
    write_or_skip('res.partner', PARTNER_LF_EM_FB,
        {'property_stock_subcontractor': new_loc_id})
    return True

def task_T05():
    """Reativar picking_type 74 (FB Subcontratação)."""
    log("T05 — Reativar picking_type 74")
    # OdooConnection.search_read não aceita context — usar execute_kw direto
    # para passar active_test=False (encontrar registros inativos)
    rec = odoo().execute_kw('stock.picking.type', 'search_read',
                             [[('id','=',PT_FB_SUBCONTRATACAO)]],
                             {'fields': ['name','active'],
                              'context': {'active_test': False},
                              'limit': 1})
    if not rec:
        log(f"  ERRO: picking_type id={PT_FB_SUBCONTRATACAO} não encontrado")
        return False
    if rec[0]['active']:
        log(f"  já ativo: {rec[0]['name']}")
        return True
    log(f"  reativar: {rec[0]['name']}")
    if not DRY_RUN:
        odoo().write('stock.picking.type', PT_FB_SUBCONTRATACAO, {'active': True})
    return True

def task_T06():
    """Reativar picking_type 80 (LF Subcontratação)."""
    log("T06 — Reativar picking_type 80")
    rec = odoo().execute_kw('stock.picking.type', 'search_read',
                             [[('id','=',PT_LF_SUBCONTRATACAO)]],
                             {'fields': ['name','active'],
                              'context': {'active_test': False},
                              'limit': 1})
    if not rec:
        log(f"  ERRO: picking_type id={PT_LF_SUBCONTRATACAO} não encontrado")
        return False
    if rec[0]['active']:
        log(f"  já ativo: {rec[0]['name']}")
        return True
    log(f"  reativar: {rec[0]['name']}")
    if not DRY_RUN:
        odoo().write('stock.picking.type', PT_LF_SUBCONTRATACAO, {'active': True})
    return True

def task_T07():
    """Criar picking_type LF/SAI/IND/RET."""
    log("T07 — Criar picking_type LF/SAI/IND/RET")
    loc_pa = odoo().search_read('stock.location',
        [('name','=','PA de Terceiros'),('company_id','=',CMP_LF)],
        ['id'], limit=1)
    if not loc_pa:
        log("  ERRO: LF/PA de Terceiros não existe. Execute T03 primeiro.")
        return False
    vals = {
        'name': 'Retorno Industrialização (LF)',
        'sequence_code': 'LF/SAI/IND/RET',
        'code': 'outgoing',
        'company_id': CMP_LF,
        'warehouse_id': WH_LF_ID,
        'default_location_src_id': loc_pa[0]['id'],
        'default_location_dest_id': LOC_EM_TRANSITO_IND,
        'return_picking_type_id': PT_LF_RECEB_IND,
        'show_operations': True,
        'show_reserved': True,
        'use_create_lots': False,
        'use_existing_lots': True,
    }
    pt_id = create_or_skip('stock.picking.type',
        [('sequence_code','=','LF/SAI/IND/RET')],
        vals)
    log(f"  resultado: picking_type id={pt_id}")
    return pt_id

def task_T08():
    """Criar stock.rule na rota 162 (FB Reposição p/ subcontratação)."""
    log("T08 — Criar stock.rule na rota 162")
    loc_mat = odoo().search_read('stock.location',
        [('name','=','Materiais de Terceiros'),('company_id','=',CMP_LF)],
        ['id'], limit=1)
    if not loc_mat:
        log("  ERRO: LF/Materiais de Terceiros não existe. Execute T02 primeiro.")
        return False

    existing = odoo().search_read('stock.rule',
        [('route_id','=',ROUTE_FB_REPOSICAO_SUBCONTRATACAO),
         ('location_dest_id','=',loc_mat[0]['id'])],
        ['id','name'], limit=1)
    if existing:
        log(f"  regra já existe id={existing[0]['id']}")
        return existing[0]['id']

    vals = {
        'name': 'FB/Estoque → LF/Materiais de Terceiros (subcontract resupply)',
        'route_id': ROUTE_FB_REPOSICAO_SUBCONTRATACAO,
        'action': 'pull',
        'picking_type_id': PT_RES_FB,
        'location_src_id': LOC_FB_ESTOQUE,
        'location_dest_id': loc_mat[0]['id'],
        'procure_method': 'make_to_stock',
        'company_id': CMP_FB,
    }
    rule_id = create_or_skip('stock.rule',
        [('name','=',vals['name'])], vals)
    log(f"  resultado: stock.rule id={rule_id}")
    return rule_id

def task_T09():
    """Avaliar/criar regras na rota 166 (LF Reposição p/ subcontratação)."""
    log("T09 — Avaliar rota 166")
    log("  LF não subcontrata (subcontracting_to_resupply=False)")
    log("  Esta rota provavelmente não é necessária.")
    log("  Marcar como ⛔ skipped a menos que o piloto T13 indique necessidade.")
    return None

def task_T10():
    """Alterar BoM 3695 (cmp=LF normal): consumption='strict'."""
    log("T10 — Alterar BoM 3695: consumption='strict'")
    current = odoo().search_read('mrp.bom',[('id','=',BOM_NORMAL_LF)],
        ['display_name','consumption'], limit=1)
    if not current:
        log(f"  ERRO: BoM id={BOM_NORMAL_LF} não encontrada")
        return False
    log(f"  atual: {current[0]['display_name']} consumption={current[0]['consumption']}")
    if current[0]['consumption'] == 'strict':
        log("  já strict (skip)")
        return True
    log(f"  alterar para 'strict'")
    if not DRY_RUN:
        odoo().write('mrp.bom', BOM_NORMAL_LF, {'consumption': 'strict'})
    return True

def task_T11():
    """Adicionar rota MTO ao produto 4870112 (cmp=LF)."""
    log("T11 — Adicionar rota MTO ao produto 4870112")
    # Buscar rota MTO — aceita 'MTO' (Nacom/CIEL IT) ou 'Make to Order' (Odoo padrão)
    mto = odoo().search_read('stock.route',
        ['|', ('name','=','MTO'), ('name','ilike','Make to Order')],
        ['id','name','company_id','active','product_selectable'], limit=5)
    if not mto:
        log("  ERRO: rota MTO/Make To Order não encontrada")
        return False
    log(f"  rotas MTO encontradas:")
    for r in mto:
        cid = r['company_id'][1] if r['company_id'] else 'GLOBAL'
        log(f"    id={r['id']} {r['name']} cmp={cid}")

    # Pegar a primeira global
    mto_id = mto[0]['id']

    # Adicionar ao produto
    prod = odoo().search_read('product.product',[('id','=',PRODUCT_PA_4870112)],
        ['product_tmpl_id','route_ids'], limit=1)[0]
    tmpl_id = prod['product_tmpl_id'][0]
    current_routes = prod['route_ids']
    log(f"  product_tmpl_id={tmpl_id} route_ids={current_routes}")

    if mto_id in current_routes:
        log(f"  rota {mto_id} já está no template (skip)")
        return True
    log(f"  adicionar route_id={mto_id} ao template")
    if not DRY_RUN:
        odoo().write('product.template', tmpl_id, {
            'route_ids': [(4, mto_id)],
        })
    return True

def task_T12():
    """Verificar journals inter-company."""
    log("T12 — Verificar journals inter-company")
    for cmp_id, cmp_name in [(CMP_FB,'FB'),(CMP_LF,'LF')]:
        sale = odoo().search_read('account.journal',
            [('company_id','=',cmp_id),('type','=','sale'),('active','=',True)],
            ['id','name','code'], limit=3)
        purchase = odoo().search_read('account.journal',
            [('company_id','=',cmp_id),('type','=','purchase'),('active','=',True)],
            ['id','name','code'], limit=3)
        log(f"  {cmp_name} (id={cmp_id}):")
        log(f"    SALE journals: {[(j['id'],j['code']) for j in sale]}")
        log(f"    PURCHASE journals: {[(j['id'],j['code']) for j in purchase]}")
    log("")
    log("  AÇÃO MANUAL: TI confirma que journals adequados estão configurados em")
    log("  Settings > Companies > Inter-Company Transactions de cada cia.")
    return True

def task_T33():
    """Desativar BoM 14833 (pós-piloto)."""
    log("T33 — Desativar BoM 14833 (subcontract não usada na Opção 2)")
    current = odoo().search_read('mrp.bom',[('id','=',BOM_SUBCONTRACT_FB)],
        ['display_name','active'], limit=1)
    if not current:
        log(f"  ERRO: BoM id={BOM_SUBCONTRACT_FB} não encontrada")
        return False
    log(f"  atual: {current[0]['display_name']} active={current[0]['active']}")
    if not current[0]['active']:
        log("  já inativa (skip)")
        return True
    log(f"  desativar")
    if not DRY_RUN:
        odoo().write('mrp.bom', BOM_SUBCONTRACT_FB, {'active': False})
    return True

# ========================================
# DISPATCH
# ========================================

TASKS = {
    'T02': task_T02,
    'T03': task_T03,
    'T04': task_T04,
    'T05': task_T05,
    'T06': task_T06,
    'T07': task_T07,
    'T08': task_T08,
    'T09': task_T09,
    'T10': task_T10,
    'T11': task_T11,
    'T12': task_T12,
    'T33': task_T33,
}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--task', required=True, choices=list(TASKS.keys()),
                        help='Task a executar')
    parser.add_argument('--execute', action='store_true',
                        help='Executar de verdade (default: dry-run)')
    args = parser.parse_args()

    setlog(dry=not args.execute)
    print("="*72)
    print(f"setup_s0.py — task {args.task} ({'EXECUTE' if args.execute else 'DRY-RUN'})")
    print("="*72)

    result = TASKS[args.task]()

    print("="*72)
    if result is None or result is False:
        print(f"⚠️  Task {args.task} terminou sem resultado ou com erro.")
        if not args.execute:
            print("Modo DRY-RUN — re-executar com --execute para aplicar.")
    else:
        print(f"✅ Task {args.task} OK (result={result})")
        if not args.execute:
            print("Modo DRY-RUN — re-executar com --execute para aplicar.")
        else:
            print("ATUALIZAR STATUS.md marcando esta task como ✅ done.")
            print(f"DOCUMENTAR resultado em testes/{args.task}-resultado.md")
    print("="*72)

if __name__ == '__main__':
    main()
