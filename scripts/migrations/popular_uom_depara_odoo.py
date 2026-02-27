"""
Popular UoM IDs no De-Para e sincronizar para o Odoo
=====================================================

Para TODOS os registros De-Para com um_fornecedor preenchido:
1. Lista UoMs do Odoo e tenta mapear cada um_fornecedor local
2. Mostra mapeamento (matches e gaps)
3. Com --apply: salva odoo_product_uom_id local + escreve product_uom no Odoo

Fluxo recomendado:
    # 1. Ver mapeamento (dry-run por default)
    python scripts/migrations/popular_uom_depara_odoo.py

    # 2. Aplicar
    python scripts/migrations/popular_uom_depara_odoo.py --apply

Uso:
    source .venv/bin/activate
    python scripts/migrations/popular_uom_depara_odoo.py [--apply]
"""

import sys
import os
import argparse
import logging

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app import create_app, db
from app.recebimento.models import ProdutoFornecedorDepara
from app.odoo.utils.connection import get_odoo_connection

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# Mapeamento manual: um_fornecedor local → nome da UoM no Odoo
# Chaves em UPPERCASE para comparacao case-insensitive.
# Validado contra Odoo producao em 2026-02-27 (57 UoMs, 7 categorias).
MAPEAMENTO_MANUAL = {
    # === Unidades (categoria Unit, ID 1) ===
    'UN': 'Units',       # Odoo ID 1
    'UND': 'Units',
    'UNITS': 'Units',
    'PEÇA': 'Units',
    'PÇ': 'Units',
    'PECA': 'Units',     # variante sem acento

    # Odoo ja tem essas com nomes exatos — match direto funciona:
    # PC (ID 87), BC (ID 29), BR (ID 92), CX (ID 28),
    # LA (ID 91), PL (ID 182), RL (ID 30), SC (ID 90),
    # PT (ID 172), BD (ID 138, cat Unit)
    # Mas precisamos do mapeamento explicito para variantes:
    'CAIXAS': 'CAIXAS',  # Odoo ID 160
    'BL': 'BC',          # Balde → BC (ID 29) — mais proximo

    # Milhar (categoria Unit, ID 1)
    'ML': 'MI',          # Odoo ID 181 (MI, factor=1000)
    'MI': 'MI',
    'MIL': 'MI',
    'MLH': 'MI',

    # === Peso (categoria Weight, ID 2) ===
    'KG': 'kg',          # Odoo ID 12
    'KILO': 'kg',
    'KG LIQ': 'kg',
    'QUILOG': 'kg',
    'G': 'gr',           # Odoo ID 162 (gr, nao g)

    # === Volume (categoria Volume, ID 6) ===
    'L': 'Litros',       # Odoo ID 96
    'LT': 'Litros',
    'LITROS': 'Litros',
    'LATAS': 'Latas',    # Odoo ID 10
    'GAL (US)': 'gal (US)',  # Odoo ID 24

    # === Comprimento (categoria Length, ID 4) ===
    'M': 'm',            # Odoo ID 5

    # === Sem match no Odoo (serao ignorados) ===
    # BRC, BAR, TAM, TB, SCO, TA, BA — nao existem no Odoo
    # Total: ~25 registros. Podem ser criados no Odoo se necessario.
}


def carregar_uoms_odoo(odoo):
    """
    Carrega todas as UoMs do Odoo.
    Retorna dict {nome_lower: {id, name, ...}}.
    Para nomes duplicados, prioriza categoria Unit (ID 1).
    """
    uom_ids = odoo.search('uom.uom', [], limit=200)
    uoms = odoo.read('uom.uom', uom_ids, ['id', 'name', 'category_id', 'uom_type', 'factor'])

    resultado = {}
    for u in uoms:
        if not u:
            continue
        key = u['name'].lower()
        cat_id = u['category_id'][0] if isinstance(u.get('category_id'), (list, tuple)) else None
        info = {
            'id': u['id'],
            'name': u['name'],
            'category_id': cat_id,
            'uom_type': u.get('uom_type'),
            'factor': u.get('factor'),
        }
        # Se ja existe, priorizar categoria Unit (ID 1)
        if key in resultado:
            if cat_id == 1:
                resultado[key] = info
        else:
            resultado[key] = info

    return resultado


def resolver_uom(um_local, uoms_odoo):
    """
    Tenta resolver um_fornecedor local para UoM do Odoo.

    Estrategia:
    1. Mapeamento manual (MAPEAMENTO_MANUAL)
    2. Match exato case-insensitive contra UoMs do Odoo
    3. Retorna None se nao encontrar
    """
    um_upper = um_local.strip().upper()
    um_lower = um_local.strip().lower()

    # 1. Mapeamento manual
    if um_upper in MAPEAMENTO_MANUAL:
        nome_odoo = MAPEAMENTO_MANUAL[um_upper]
        match = uoms_odoo.get(nome_odoo.lower())
        if match:
            return match

    # 2. Match exato case-insensitive
    match = uoms_odoo.get(um_lower)
    if match:
        return match

    return None


def main():
    parser = argparse.ArgumentParser(description='Popular UoM IDs no De-Para e Odoo')
    parser.add_argument('--apply', action='store_true',
                        help='Aplicar alteracoes (default: apenas mostrar mapeamento)')
    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        # ==============================================================
        # PASSO 1: Conectar ao Odoo e carregar UoMs
        # ==============================================================
        logger.info("=== PASSO 1: Carregar UoMs do Odoo ===")

        odoo = get_odoo_connection()
        if not odoo.authenticate():
            logger.error("Falha ao autenticar no Odoo")
            sys.exit(1)

        uoms_odoo = carregar_uoms_odoo(odoo)
        logger.info(f"UoMs no Odoo: {len(uoms_odoo)}")
        for _, info in sorted(uoms_odoo.items(), key=lambda x: x[1]['id']):
            logger.info(f"  ID={info['id']:>4} | {info['name']:<20} | tipo={info['uom_type']} | fator={info['factor']}")

        # ==============================================================
        # PASSO 2: Buscar De-Para sem odoo_product_uom_id
        # ==============================================================
        logger.info("\n=== PASSO 2: Buscar De-Para pendentes ===")

        pendentes = ProdutoFornecedorDepara.query.filter(
            ProdutoFornecedorDepara.ativo == True,
            ProdutoFornecedorDepara.um_fornecedor.isnot(None),
            ProdutoFornecedorDepara.um_fornecedor != '',
            ProdutoFornecedorDepara.odoo_product_uom_id.is_(None)
        ).all()

        logger.info(f"Registros pendentes: {len(pendentes)}")

        # ==============================================================
        # PASSO 3: Mapear um_fornecedor → UoM Odoo
        # ==============================================================
        logger.info("\n=== PASSO 3: Mapeamento ===")

        # Agrupar por um_fornecedor
        por_um = {}
        for r in pendentes:
            um = r.um_fornecedor.strip()
            if um not in por_um:
                por_um[um] = []
            por_um[um].append(r)

        matches = {}       # um_local → uom_odoo_info
        sem_match = {}     # um_local → contagem

        for um_local, registros in sorted(por_um.items(), key=lambda x: -len(x[1])):
            uom = resolver_uom(um_local, uoms_odoo)
            if uom:
                matches[um_local] = uom
                logger.info(f"  MATCH: '{um_local}' ({len(registros)} registros) → Odoo '{uom['name']}' (ID={uom['id']})")
            else:
                sem_match[um_local] = len(registros)
                logger.warning(f"  SEM MATCH: '{um_local}' ({len(registros)} registros) → ???")

        total_match = sum(len(por_um[um]) for um in matches)
        total_sem = sum(sem_match.values())

        logger.info(f"\nResumo: {total_match} registros com match, {total_sem} sem match")

        if sem_match:
            logger.info("\n--- UoMs SEM MATCH (precisam de mapeamento manual ou criar no Odoo) ---")
            for um, qtd in sorted(sem_match.items(), key=lambda x: -x[1]):
                logger.info(f"  '{um}': {qtd} registros")
            logger.info(
                "\nPara resolver: adicionar entrada em MAPEAMENTO_MANUAL no script, "
                "ou criar a UoM no Odoo."
            )

        if not args.apply:
            logger.info("\n[DRY-RUN] Use --apply para executar as alteracoes")
            return

        # ==============================================================
        # PASSO 4: Aplicar — UPDATE local
        # ==============================================================
        logger.info("\n=== PASSO 4: UPDATE local (odoo_product_uom_id) ===")

        atualizados_local = 0
        for um_local, uom_info in matches.items():
            for r in por_um[um_local]:
                r.odoo_product_uom_id = uom_info['id']
                atualizados_local += 1

        db.session.commit()
        logger.info(f"Registros atualizados localmente: {atualizados_local}")

        # ==============================================================
        # PASSO 5: Aplicar — UPDATE Odoo (product.supplierinfo.product_uom)
        # ==============================================================
        logger.info("\n=== PASSO 5: UPDATE Odoo (product_uom) ===")

        atualizados_odoo = 0
        erros_odoo = 0

        for um_local, uom_info in matches.items():
            for r in por_um[um_local]:
                if not r.odoo_supplierinfo_id:
                    continue
                try:
                    odoo.write(
                        'product.supplierinfo',
                        [r.odoo_supplierinfo_id],
                        {'product_uom': uom_info['id']}
                    )
                    atualizados_odoo += 1
                    if atualizados_odoo % 50 == 0:
                        logger.info(f"  ... {atualizados_odoo} supplierinfos atualizados")
                except Exception as e:
                    erros_odoo += 1
                    logger.error(f"  Supplierinfo {r.odoo_supplierinfo_id} (DePara {r.id}): {e}")

        # ==============================================================
        # RESUMO
        # ==============================================================
        logger.info("\n" + "=" * 60)
        logger.info("RESUMO")
        logger.info("=" * 60)
        logger.info(f"Total pendentes:           {len(pendentes)}")
        logger.info(f"Com match:                 {total_match}")
        logger.info(f"Sem match:                 {total_sem}")
        logger.info(f"Atualizados local:         {atualizados_local}")
        logger.info(f"Atualizados Odoo:          {atualizados_odoo}")
        logger.info(f"Erros Odoo:                {erros_odoo}")
        logger.info("=" * 60)

        if erros_odoo:
            logger.warning("Houve erros ao atualizar Odoo. Verifique logs acima.")
        else:
            logger.info("Concluido com sucesso!")


if __name__ == '__main__':
    main()
