"""Migration 25: backfill divergencias legadas — assai_nf_qpa_item.tipo_divergencia -> assai_divergencia.

Spec: §2.2 (S8=a + A12)
Plano: Task 23

Para cada AssaiNfQpaItem.tipo_divergencia nao nulo, cria linha em assai_divergencia.
Idempotente: nao cria duplicatas (verifica por (nf_id, chassi, tipo)).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app import create_app, db  # noqa: E402
from app.motos_assai.models import (  # noqa: E402
    AssaiNfQpaItem, AssaiSeparacaoItem, AssaiDivergencia, DIVERGENCIA_TIPOS_VALIDOS,
)
from sqlalchemy import and_  # noqa: E402


def main():
    app = create_app()
    with app.app_context():
        items_legados = AssaiNfQpaItem.query.filter(
            AssaiNfQpaItem.tipo_divergencia.isnot(None)
        ).all()

        print(f'[start] {len(items_legados)} items com tipo_divergencia legado')

        criadas = 0
        skipadas = 0

        # Pre-cache: separacao_id por separacao_item_id (evita N+1)
        sep_item_ids = [i.separacao_item_id for i in items_legados if i.separacao_item_id]
        sep_id_map = {}
        if sep_item_ids:
            for si in AssaiSeparacaoItem.query.filter(AssaiSeparacaoItem.id.in_(sep_item_ids)).all():
                sep_id_map[si.id] = si.separacao_id

        for item in items_legados:
            tipo = item.tipo_divergencia

            # Validacao: tipo deve estar nos validos da nova tabela
            if tipo not in DIVERGENCIA_TIPOS_VALIDOS:
                print(f'  [skip] item #{item.id} tipo invalido: {tipo}')
                skipadas += 1
                continue

            # Idempotente: verificar se ja existe
            ja_existe = AssaiDivergencia.query.filter(and_(
                AssaiDivergencia.nf_id == item.nf_id,
                AssaiDivergencia.chassi == item.chassi,
                AssaiDivergencia.tipo == tipo,
            )).first()

            if ja_existe:
                skipadas += 1
                continue

            sep_id = sep_id_map.get(item.separacao_item_id) if item.separacao_item_id else None

            # Code review fix M6 (2026-05-13): usar sanitize_for_json em vez
            # de float() manual. Regra global CLAUDE.md JSON SANITIZATION:
            # "SEMPRE usar sanitize_for_json em queries SQLAlchemy com
            # colunas Numeric/DECIMAL". Embora float() funcione hoje, sanitize
            # protege contra adicao futura de campos Decimal/datetime/UUID.
            from app.utils.json_helpers import sanitize_for_json
            div = AssaiDivergencia(
                tipo=tipo,
                chassi=item.chassi,
                nf_id=item.nf_id,
                separacao_id=sep_id,
                detalhes=sanitize_for_json({
                    'origem': 'backfill_migration_25',
                    'nf_qpa_item_id': item.id,
                    'modelo_extraido': item.modelo_extraido,
                    'valor_extraido': item.valor_extraido,
                }),
            )
            db.session.add(div)
            criadas += 1

        db.session.commit()
        print(f'[done] criadas: {criadas}, skipadas (ja existentes ou invalidas): {skipadas}')
        print('[ok] Migration 25 aplicada')


if __name__ == '__main__':
    main()
