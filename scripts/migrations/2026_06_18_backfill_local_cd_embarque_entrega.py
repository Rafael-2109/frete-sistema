"""Backfill: alinhar `local_cd` de EmbarqueItem (CARVIA-%) e EntregaMonitorada (origem
CARVIA) ao `local_cd` da CarviaNf (fonte = Coleta CarVia).

Contexto: a propagacao da Coleta cobria carvia_nfs/carvia_pedidos/carvia_cotacoes, mas NAO
EmbarqueItem (nascia com default VICTORIO_MARCHEZINE e nunca era re-propagado) nem reescrevia
EntregaMonitorada fora do sincronizador. Resultado em prod (2026-06-18): 34 embarque_itens
ativos + 15 entregas divergentes (ex.: NF 38966 = TENENTE na coleta/NF/entrega, VICTORIO no
embarque_item). O fix de codigo (helper app/utils/propagacao_local_cd.py + hook no coleta_service)
corrige dali pra frente; este script corrige o passado. Idempotente — reusa o mesmo helper.

Uso:
    python scripts/migrations/2026_06_18_backfill_local_cd_embarque_entrega.py            # dry-run
    python scripts/migrations/2026_06_18_backfill_local_cd_embarque_entrega.py --apply    # efetiva
"""
import logging
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app import create_app, db  # noqa: E402
from app.carvia.models import CarviaNf  # noqa: E402
from app.embarques.models import EmbarqueItem  # noqa: E402
from app.monitoramento.models import EntregaMonitorada  # noqa: E402
from app.utils.propagacao_local_cd import propagar_local_cd_carvia  # noqa: E402

logger = logging.getLogger(__name__)


def _contar_divergentes():
    """(embarque_itens, entregas) divergentes da CarviaNf ATIVA correspondente."""
    emb = (
        db.session.query(db.func.count(EmbarqueItem.id))
        .join(CarviaNf, db.and_(
            CarviaNf.numero_nf == EmbarqueItem.nota_fiscal,
            CarviaNf.status == 'ATIVA',
        ))
        .filter(
            EmbarqueItem.separacao_lote_id.ilike('CARVIA-%'),
            EmbarqueItem.local_cd.isnot(None),
            EmbarqueItem.local_cd != CarviaNf.local_cd,
        )
        .scalar()
    )
    ent = (
        db.session.query(db.func.count(EntregaMonitorada.id))
        .join(CarviaNf, db.and_(
            CarviaNf.numero_nf == EntregaMonitorada.numero_nf,
            CarviaNf.status == 'ATIVA',
        ))
        .filter(
            EntregaMonitorada.origem == 'CARVIA',
            EntregaMonitorada.local_cd != CarviaNf.local_cd,
        )
        .scalar()
    )
    return emb or 0, ent or 0


def main():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    aplicar = '--apply' in sys.argv

    app = create_app()
    with app.app_context():
        emb_antes, ent_antes = _contar_divergentes()
        print(f'ANTES  -> embarque_itens divergentes: {emb_antes} | entregas divergentes: {ent_antes}')

        total = 0
        nfs = CarviaNf.query.filter_by(status='ATIVA').all()
        for nf in nfs:
            if not nf.local_cd:
                continue
            total += propagar_local_cd_carvia(nf.numero_nf, nf.local_cd)

        if aplicar:
            db.session.commit()
            emb_depois, ent_depois = _contar_divergentes()
            print(f'APLICADO -> linhas atualizadas: {total}')
            print(f'DEPOIS -> embarque_itens divergentes: {emb_depois} | entregas divergentes: {ent_depois}')
            assert emb_depois == 0 and ent_depois == 0, 'Ainda ha divergencias apos backfill!'
            print('OK — local_cd consistente em embarque_itens + entregas (origem CarVia).')
        else:
            db.session.rollback()
            print(f'DRY-RUN -> {total} linha(s) SERIAM atualizadas. Rode com --apply para efetivar.')


if __name__ == '__main__':
    main()
