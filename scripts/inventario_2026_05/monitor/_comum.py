"""Helpers compartilhados pelos scripts 1-4 do monitor de inventario."""
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

ODOO_BATCH_SIZE = 200

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


def garantir_relatorios_dir():
    os.makedirs(RELATORIOS_DIR, exist_ok=True)
    return RELATORIOS_DIR
