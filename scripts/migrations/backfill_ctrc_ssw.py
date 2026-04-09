"""
Backfill: corrigir ctrc_numero em carvia_operacoes.

Problema: o parser usava nCT do XML como CTRC, mas no SSW o CTRC e uma
sequencia separada do CT-e (nCT SEFAZ). Exemplo: CTRC 113 = CT-e 110.
O cDV da chave SEFAZ tambem difere do DV do CTRC.

Estrategia:
  1. Varrer CTRCs no SSW (opcao 101) de 1 ate max_ctrc
  2. Para cada, capturar CT-e associado + ctrc_completo
  3. Construir mapa nCT → ctrc_formatado
  4. Atualizar carvia_operacoes.ctrc_numero onde necessario

Uso:
    source .venv/bin/activate
    python scripts/migrations/backfill_ctrc_ssw.py [--max-ctrc 150] [--dry-run]
"""
import argparse
import asyncio
import json
import logging
import os
import re
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

SSW_SCRIPTS = os.path.join(
    os.path.dirname(__file__), '..', '..', '.claude', 'skills', 'operando-ssw', 'scripts'
)


def formatar_ctrc(ctrc_completo):
    """CAR000113-9 → CAR-113-9"""
    m = re.match(r'^([A-Z]{2,4})0*(\d+)-(\d)$', ctrc_completo)
    if m:
        return f'{m.group(1)}-{m.group(2)}-{m.group(3)}'
    return ctrc_completo


def extrair_nct_de_cte_field(cte_field):
    """'001 000000110' → 110"""
    if not cte_field:
        return None
    m = re.search(r'0*(\d+)$', cte_field.strip())
    return int(m.group(1)) if m else None


async def consultar_ctrc_ssw(ctrc_num, filial='CAR'):
    """Consulta 1 CTRC no SSW e retorna (nCT, ctrc_completo) ou (None, None)."""
    if SSW_SCRIPTS not in sys.path:
        sys.path.insert(0, os.path.abspath(SSW_SCRIPTS))

    from consultar_ctrc_101 import consultar_ctrc

    args = argparse.Namespace(
        ctrc=str(ctrc_num),
        nf=None,
        filial=filial,
        baixar_xml=False,
        baixar_dacte=False,
        output_dir='/tmp/ssw_operacoes/backfill_ctrc',
    )
    resultado = await consultar_ctrc(args)

    if not resultado.get('sucesso'):
        return None, None

    dados = resultado.get('dados', {})
    ctrc_completo = dados.get('ctrc_completo')
    cte_field = dados.get('cte')
    nct = extrair_nct_de_cte_field(cte_field)

    return nct, ctrc_completo


async def build_nct_to_ctrc_map(max_ctrc, filial='CAR'):
    """Varre CTRCs 1..max_ctrc no SSW e constroi mapa nCT → ctrc_formatado."""
    nct_map = {}  # nCT (int) → ctrc_formatado (str)

    logger.info("Varrendo CTRCs 1..%d no SSW (filial=%s)...", max_ctrc, filial)

    for ctrc_num in range(1, max_ctrc + 1):
        try:
            nct, ctrc_completo = await consultar_ctrc_ssw(ctrc_num, filial)
            if nct is not None and ctrc_completo:
                ctrc_fmt = formatar_ctrc(ctrc_completo)
                nct_map[nct] = ctrc_fmt
                logger.info(
                    "  CTRC %d → CT-e %d → %s",
                    ctrc_num, nct, ctrc_fmt
                )
            else:
                logger.debug("  CTRC %d: nao encontrado ou sem CT-e", ctrc_num)
        except Exception as e:
            logger.warning("  CTRC %d: erro — %s", ctrc_num, e)

        # Breve pausa para nao sobrecarregar SSW
        await asyncio.sleep(1)

    logger.info("Mapa construido: %d entradas nCT→CTRC", len(nct_map))
    return nct_map


def aplicar_backfill(nct_map, dry_run=False):
    """Aplica o mapa nCT→CTRC no banco."""
    from app import create_app, db

    app = create_app()
    with app.app_context():
        conn = db.engine.raw_connection()
        cursor = conn.cursor()

        try:
            # Buscar operacoes com cte_numero (que e o nCT do XML)
            cursor.execute("""
                SELECT id, cte_numero, ctrc_numero
                FROM carvia_operacoes
                WHERE cte_numero IS NOT NULL
                  AND cte_numero ~ '^\d+$'
                ORDER BY id
            """)
            rows = cursor.fetchall()
            logger.info("Operacoes com cte_numero: %d", len(rows))

            atualizados = 0
            sem_mapa = 0
            ja_corretos = 0

            for op_id, cte_numero, ctrc_atual in rows:
                nct = int(cte_numero)
                ctrc_correto = nct_map.get(nct)

                if not ctrc_correto:
                    sem_mapa += 1
                    continue

                if ctrc_atual == ctrc_correto:
                    ja_corretos += 1
                    continue

                if dry_run:
                    logger.info(
                        "  [DRY RUN] op=%d: %s → %s",
                        op_id, ctrc_atual, ctrc_correto
                    )
                else:
                    cursor.execute(
                        "UPDATE carvia_operacoes SET ctrc_numero = %s WHERE id = %s",
                        (ctrc_correto, op_id)
                    )
                atualizados += 1

            if not dry_run:
                conn.commit()

            logger.info(
                "Backfill %s: %d atualizados, %d ja corretos, %d sem mapa SSW",
                "DRY RUN" if dry_run else "APLICADO",
                atualizados, ja_corretos, sem_mapa
            )

        finally:
            cursor.close()
            conn.close()


def main():
    parser = argparse.ArgumentParser(description="Backfill CTRC via SSW opcao 101")
    parser.add_argument('--max-ctrc', type=int, default=150,
                        help='Numero maximo de CTRC a varrer (default: 150)')
    parser.add_argument('--filial', default='CAR', help='Filial SSW')
    parser.add_argument('--dry-run', action='store_true', help='Apenas mostrar, nao atualizar')
    parser.add_argument('--map-file', default='/tmp/nct_ctrc_map.json',
                        help='Salvar/carregar mapa em arquivo JSON (evita re-varrer)')
    args = parser.parse_args()

    map_file = args.map_file

    # Se ja temos mapa salvo, reusar
    if os.path.exists(map_file):
        logger.info("Carregando mapa de %s", map_file)
        with open(map_file) as f:
            nct_map = {int(k): v for k, v in json.load(f).items()}
    else:
        # Varrer SSW
        nct_map = asyncio.run(build_nct_to_ctrc_map(args.max_ctrc, args.filial))
        # Salvar para reusar
        with open(map_file, 'w') as f:
            json.dump({str(k): v for k, v in nct_map.items()}, f, indent=2)
        logger.info("Mapa salvo em %s", map_file)

    # Aplicar no banco
    aplicar_backfill(nct_map, dry_run=args.dry_run)


if __name__ == '__main__':
    main()
