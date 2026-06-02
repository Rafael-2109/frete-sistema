# etapa: monitor
# doc-dono: scripts/inventario_2026_05/INDEX.md
"""Helpers compartilhados pelos scripts 1-4 do monitor de inventario."""
import json
import os
import sys

# Path setup para imports do app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')))

import pandas as pd  # noqa: E402

# ============================================================
# CONSTANTES
# ============================================================
INVENTARIO_DIR_DEFAULT = '/mnt/c/Users/rafael.nascimento/Downloads/INVENTARIO 16-05-26'
CACHE_DIR_DEFAULT = '/tmp/inventario_monitor'
RELATORIOS_DIR = '/home/rafaelnascimento/projetos/frete_sistema/docs/inventario-2026-05/07-relatorios'

DATA_INICIO_INV = '2026-05-16 00:00:00'
COMPANIES = [1, 4, 5]
COMPANY_NAME = {1: 'FB', 4: 'CD', 5: 'LF'}
COMPANY_FULL = {1: 'NACOM GOYA - FB', 4: 'NACOM GOYA - CD', 5: 'LA FAMIGLIA - LF'}
FILIAL_TO_COMPANY = {'FB': 1, 'CD': 4, 'LF': 5}

ODOO_BATCH_SIZE = 200

# Usuario Odoo Rafael (descoberto via res.users) — mesmo UID do XML-RPC
RAFAEL_ODOO_UID = 42

# Env var com External Database URL do Render Postgres
ENV_RENDER_DB_URL = 'DATABASE_URL_PROD'

# Lotes considerados MIGRACAO (variantes encoding)
LOTES_MIGRACAO = {'MIGRACAO', 'MIGRAÇÃO', 'MIGRACÃO', 'MIGRAÇAO', 'MIG'}

# Lotes que devem ser tratados como vazio (criados a partir de "sem lote")
LOTES_PROXY_VAZIO = {'P-15/05'}


# ============================================================
# NORMALIZADORES
# ============================================================
def norm_lote(x):
    """Normaliza nome de lote (str, sem .0 de float-int).

    LOTES_PROXY_VAZIO (ex: 'P-15/05') sao tratados como vazio — foram criados
    a partir de produtos sem lote para nao deixar o produto orfao no Odoo.
    """
    if x is None:
        return ''
    if isinstance(x, float):
        if pd.isna(x):
            return ''
        if x == int(x):
            s = str(int(x))
        else:
            s = str(x)
    elif isinstance(x, int):
        s = str(x)
    else:
        s = str(x).strip()
    if s in LOTES_PROXY_VAZIO:
        return ''
    return s


def norm_cod(x):
    """Normaliza codigo produto (apenas digitos)."""
    if x is None:
        return ''
    if isinstance(x, float):
        if pd.isna(x):
            return ''
        if x == int(x):
            return str(int(x))
        return str(x)
    if isinstance(x, int):
        return str(x)
    s = str(x).strip()
    if s.endswith('.0'):
        s = s[:-2]
    return s


def is_migracao(lote):
    """Detecta variantes do lote MIGRACAO."""
    if pd.isna(lote) or not lote:
        return False
    return str(lote).upper().strip() in LOTES_MIGRACAO


def is_location_interna(loc_name):
    """Verdadeiro se loc_name eh stock interno de FB/CD/LF (nao virtual)."""
    if not loc_name:
        return False
    if not (loc_name.startswith('FB/') or loc_name.startswith('CD/') or loc_name.startswith('LF/')):
        return False
    virtual_kw = ['Virtual', 'Parceiros', 'Production', 'Inventory adjustment',
                  'Cliente', 'Customers', 'Vendors', 'Fornecedor']
    return not any(k in loc_name for k in virtual_kw)


# ============================================================
# CLASSIFICACAO DE NEGOCIO (compra / venda / ajuste) — scripts 2 e 4
# ============================================================
# Locations VIRTUAIS de ajuste de inventario. 3 variantes coexistem no Odoo
# CIEL IT (idioma/encoding): PT 'Ajuste de Inventario' e 'Ajuste de Estoque',
# EN 'Inventory adjustment'. Validado no movimentacoes.csv (2026-05-21).
LOC_KW_AJUSTE = ('Ajuste de Inventario', 'Inventory adjustment', 'Ajuste de Estoque')
LOC_KW_FORNECEDOR = ('Fornecedor', 'Vendor')   # entrada de compra
LOC_KW_CLIENTE = ('Cliente', 'Customer')        # saida de venda


def _loc_match(name, kws):
    if name is None or (isinstance(name, float) and pd.isna(name)):
        return False
    low = str(name).lower()
    return any(k.lower() in low for k in kws)


def is_loc_ajuste(name):
    """Location virtual de ajuste de inventario (qualquer das 3 variantes)."""
    return _loc_match(name, LOC_KW_AJUSTE)


def is_loc_fornecedor(name):
    """Location de fornecedor (compra)."""
    return _loc_match(name, LOC_KW_FORNECEDOR)


def is_loc_cliente(name):
    """Location de cliente (venda)."""
    return _loc_match(name, LOC_KW_CLIENTE)


def buscar_partner_ids_empresas(odoo):
    """Set de partner_ids de TODAS as res.company do grupo.

    Validado 2026-05-21: FB=1, SC=33, CD=34, LF=35. Usado para identificar
    NF entre empresas (commercial_partner_id do picking dentro deste set =
    inter-company) e excluir das colunas de compra/venda EXTERNA.
    """
    ids = set()
    for c in odoo.search_read('res.company', [], ['partner_id']):
        if c.get('partner_id'):
            ids.add(c['partner_id'][0])
    return ids


# ============================================================
# HELPERS PANDAS / ODOO
# ============================================================
def m2o_id(x):
    """Extrai id de campo many2one (vem como [id, name])."""
    if isinstance(x, list) and len(x) >= 1:
        return x[0]
    return None


def m2o_name(x):
    """Extrai name de campo many2one."""
    if isinstance(x, list) and len(x) >= 2:
        return x[1]
    return ''


def garantir_cache_dir(path=CACHE_DIR_DEFAULT):
    os.makedirs(path, exist_ok=True)
    return path


# ============================================================
# SNAPSHOT META (horario da extracao de estoque)
# ============================================================
SNAPSHOT_META_FILE = 'snapshot_meta.json'


def salvar_snapshot_meta(cache_dir, snapshot_utc):
    """Grava o horario UTC do snapshot de estoque (script 1).

    `snapshot_utc`: string 'YYYY-MM-DD HH:MM:SS' em UTC (comparavel com
    stock.move.line.date). O script 2 usa como TETO para excluir movs
    posteriores ao snapshot — evita descasamento estoque x movimentacoes.
    """
    path = os.path.join(cache_dir, SNAPSHOT_META_FILE)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump({'snapshot_utc': snapshot_utc}, f)
    return path


def ler_snapshot_meta(cache_dir):
    """Le o horario UTC do snapshot de estoque. Retorna str ou None se ausente."""
    path = os.path.join(cache_dir, SNAPSHOT_META_FILE)
    if not os.path.exists(path):
        return None
    try:
        with open(path, encoding='utf-8') as f:
            return json.load(f).get('snapshot_utc')
    except (ValueError, OSError):
        return None


def garantir_relatorios_dir():
    os.makedirs(RELATORIOS_DIR, exist_ok=True)
    return RELATORIOS_DIR


def consultar_pickings_recebimento_lf_render(data_inicio='2026-05-16'):
    """Consulta tabela recebimento_lf NO RENDER (producao) via psycopg2.

    Requer env var DATABASE_URL_PROD (External Database URL do Render).
    Carrega .env automaticamente se python-dotenv disponivel.
    Se nao configurada, retorna set vazio + warning (nao deduz).

    Retorna set de odoo_picking_id (incluindo transfer_out e transfer_in).
    """
    # Carregar .env
    try:
        from dotenv import load_dotenv
        env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '.env'))
        load_dotenv(env_path)
    except ImportError:
        pass
    url = os.environ.get(ENV_RENDER_DB_URL)
    if not url:
        print(f'AVISO: env var {ENV_RENDER_DB_URL} nao configurada — pickings Render = []')
        print('         (sem deducao: External Database URL do Render precisa estar em .env)')
        return set()

    try:
        import psycopg2
    except ImportError:
        print('AVISO: psycopg2 nao instalado — pickings Render = []')
        return set()

    pickings = set()
    try:
        conn = psycopg2.connect(url, connect_timeout=10)
        cur = conn.cursor()
        cur.execute(
            """
            SELECT odoo_picking_id, odoo_transfer_out_picking_id, odoo_transfer_in_picking_id
            FROM recebimento_lf
            WHERE criado_em >= %s
            """,
            (data_inicio,)
        )
        for row in cur.fetchall():
            for pid in row:
                if pid:
                    pickings.add(int(pid))
        cur.close()
        conn.close()
    except Exception as e:
        print(f'ERRO ao consultar Render: {e}')
        print('  pickings Render = [] (nao deduz)')
        return set()
    return pickings
