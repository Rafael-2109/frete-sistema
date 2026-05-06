"""Migration HORA 30: seed inicial de hora_modelo_alias.

Para cada HoraModelo existente, cria entradas em hora_modelo_alias
preservando os nomes/codigos atuais como aliases validos:

  1. (NOME_LIVRE, nome_modelo) -> modelo_id
  2. Se ha HoraTagPlusProdutoMap:
       (TAGPLUS_CODIGO, tagplus_codigo) -> modelo_id  (se nao vazio)
       (TAGPLUS_PRODUTO_ID, tagplus_produto_id) -> modelo_id

Idempotente: rodar 2x nao duplica (ON CONFLICT no UNIQUE (tipo, nome_alias)
ou via SELECT-then-INSERT).

Uso:
    python scripts/migrations/hora_30_seed_aliases_atuais.py
    python scripts/migrations/hora_30_seed_aliases_atuais.py --dry-run
"""
import argparse
import logging
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app import create_app, db  # noqa: E402

logger = logging.getLogger(__name__)


def main(dry_run: bool = False) -> None:
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    app = create_app()
    with app.app_context():
        from app.hora.models import (  # noqa: E402
            HoraModelo,
            HoraModeloAlias,
            HoraTagPlusProdutoMap,
            ALIAS_TIPO_NOME_LIVRE,
            ALIAS_TIPO_TAGPLUS_CODIGO,
            ALIAS_TIPO_TAGPLUS_PRODUTO_ID,
        )

        # 0. Garante modelo "DESCONHECIDO" sentinela — usado por
        # _garantir_moto em recebimento_service quando chassi extra surge
        # sem nome na NF. Sem isso, recebimento criaria pendencia em loop.
        sentinela = HoraModelo.query.filter_by(nome_modelo='DESCONHECIDO').first()
        if not sentinela:
            sentinela = HoraModelo(
                nome_modelo='DESCONHECIDO',
                ativo=True,
                descricao='Modelo sentinela usado quando ingestao nao identifica o modelo. '
                          'Operador deve mover chassis para o modelo correto via tela de '
                          'edicao manual.',
            )
            db.session.add(sentinela)
            db.session.flush()
            print(f'Modelo sentinela DESCONHECIDO criado (id={sentinela.id})')
        else:
            print(f'Modelo sentinela DESCONHECIDO ja existia (id={sentinela.id})')

        # Aliases sentinela (mapas para o modelo DESCONHECIDO)
        contadores_sent = {'NOME_LIVRE': 0, 'ja_existia': 0}
        for nome_sentinela in [
            'DESCONHECIDO',
            'MODELO_DESCONHECIDO',
            'CHASSI_EXTRA_DESCONHECIDO',
            'NAO_INFORMADO',
        ]:
            _criar_se_nao_existe(
                modelo_id=sentinela.id,
                tipo=ALIAS_TIPO_NOME_LIVRE,
                nome=nome_sentinela,
                observacao='Seed sentinela — usado em recebimento/parser quando modelo nao identificado',
                contadores=contadores_sent,
                counter_key='NOME_LIVRE',
            )
        print(f'Aliases sentinela: criados={contadores_sent["NOME_LIVRE"]} ja_existiam={contadores_sent["ja_existia"]}')

        modelos = HoraModelo.query.all()
        print(f'\nModelos a processar: {len(modelos)}')

        contadores = {
            'NOME_LIVRE': 0,
            'TAGPLUS_CODIGO': 0,
            'TAGPLUS_PRODUTO_ID': 0,
            'ja_existia': 0,
            'pulados_inativos_merged': 0,
        }

        for m in modelos:
            # Modelos ja merged ficam com seus nomes como alias do canonico
            # (acontece via merge_service automaticamente). Aqui apenas pulamos
            # para nao sobrescrever o canonico.
            if m.merged_em_id is not None:
                contadores['pulados_inativos_merged'] += 1
                continue

            # 1. NOME_LIVRE com nome_modelo
            if m.nome_modelo:
                _criar_se_nao_existe(
                    modelo_id=m.id,
                    tipo=ALIAS_TIPO_NOME_LIVRE,
                    nome=m.nome_modelo,
                    observacao='Seed inicial — preserva nome canonico atual',
                    contadores=contadores,
                    counter_key='NOME_LIVRE',
                )

            # 2. TagPlus (legado em hora_tagplus_produto_map)
            tp = HoraTagPlusProdutoMap.query.filter_by(modelo_id=m.id).first()
            if tp:
                if tp.tagplus_codigo:
                    _criar_se_nao_existe(
                        modelo_id=m.id,
                        tipo=ALIAS_TIPO_TAGPLUS_CODIGO,
                        nome=tp.tagplus_codigo,
                        observacao='Seed inicial — migrado de hora_tagplus_produto_map.tagplus_codigo',
                        contadores=contadores,
                        counter_key='TAGPLUS_CODIGO',
                    )
                if tp.tagplus_produto_id:
                    _criar_se_nao_existe(
                        modelo_id=m.id,
                        tipo=ALIAS_TIPO_TAGPLUS_PRODUTO_ID,
                        nome=tp.tagplus_produto_id,
                        observacao='Seed inicial — migrado de hora_tagplus_produto_map.tagplus_produto_id',
                        contadores=contadores,
                        counter_key='TAGPLUS_PRODUTO_ID',
                    )

        if dry_run:
            print('DRY-RUN: rollback sem persistir.')
            db.session.rollback()
        else:
            db.session.commit()
            print('Commit OK.')

        print('\n=== Resumo do seed ===')
        for k, v in contadores.items():
            print(f'  {k}: {v}')

        # Verificacao
        total_aliases = HoraModeloAlias.query.count()
        print(f'\nTotal hora_modelo_alias apos seed: {total_aliases}')


def _criar_se_nao_existe(
    *,
    modelo_id: int,
    tipo: str,
    nome: str,
    observacao: str,
    contadores: dict,
    counter_key: str,
) -> None:
    """Idempotente: SELECT-then-INSERT respeitando UNIQUE (tipo, nome_alias)."""
    from app.hora.models import HoraModeloAlias

    nome_str = (nome or '').strip()
    if not nome_str:
        return

    existente = (
        HoraModeloAlias.query
        .filter_by(tipo=tipo, nome_alias=nome_str)
        .first()
    )
    if existente:
        if existente.modelo_id != modelo_id:
            logger.warning(
                'CONFLITO: alias (tipo=%s, nome=%r) ja aponta para modelo %s, '
                'nao para %s. Pulado.',
                tipo, nome_str, existente.modelo_id, modelo_id,
            )
        contadores['ja_existia'] += 1
        return

    db.session.add(HoraModeloAlias(
        modelo_id=modelo_id,
        nome_alias=nome_str,
        tipo=tipo,
        criado_por='seed_hora_30',
        observacao=observacao,
    ))
    contadores[counter_key] += 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true',
                        help='Nao persiste mudancas — apenas reporta.')
    args = parser.parse_args()
    main(dry_run=args.dry_run)
