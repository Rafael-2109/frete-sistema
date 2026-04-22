"""Fix: importacao #13 (Bradesco cartao 38451 NOVEMBRO/2025) com datas em 2026.

BUG: parser inferiu ano_corrente=2026 ao invés do ano da fatura (2025).
Resultado: 7 transacoes com data 1 ano a frente, 3 delas > hoje (futuras).

Acao:
1. Verifica se nenhuma das 7 tx colide (conta_id + data-1yr + historico + valor + tipo) com
   transacao ja existente (evita duplicata).
2. Subtrai 1 ano da coluna data.
3. Regenera hash_transacao conforme novo valor de data.
4. Atualiza periodo_inicio/periodo_fim da importacao_id=13.
5. Deleta imp #19 e #25 (vazias, criadas por tentativas repetidas de reimportacao).

USO:
    python scripts/fix_importacao_13_ano_errado.py --dry-run
    python scripts/fix_importacao_13_ano_errado.py
"""
from __future__ import annotations

import argparse
import logging
import sys

from app import create_app, db
from app.pessoal.models import PessoalImportacao, PessoalTransacao
from app.pessoal.services.parsers.base_parser import gerar_hash_transacao, normalizar_historico

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger('fix_imp13')

IMP_ID = 13
IMPS_VAZIAS = [19, 25]


def subtract_one_year(d):
    try:
        return d.replace(year=d.year - 1)
    except ValueError:
        # 29/fev -> 28/fev do ano anterior
        return d.replace(year=d.year - 1, day=28)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--dry-run', action='store_true')
    args = p.parse_args()

    app = create_app()
    with app.app_context():
        # 1. Checar colisoes
        txs = PessoalTransacao.query.filter_by(importacao_id=IMP_ID).order_by(
            PessoalTransacao.data, PessoalTransacao.id,
        ).all()
        logger.info('Imp #%d tem %d transacoes', IMP_ID, len(txs))

        plano = []
        colisoes = []

        # Contador de sequencia por chave base (como o parser original faz)
        contagem_chaves = {}
        for t in txs:
            nova_data = subtract_one_year(t.data)

            # Regera hash na nova data (mesmo padrao do parser de importacao)
            chave_base = (
                f"{t.conta_id}|{nova_data.isoformat()}|"
                f"{normalizar_historico(t.historico)}|{t.valor}|{t.tipo}|{t.documento or ''}"
            )
            seq = contagem_chaves.get(chave_base, 0)
            contagem_chaves[chave_base] = seq + 1
            novo_hash = gerar_hash_transacao(
                t.conta_id, nova_data, t.historico, t.valor, t.tipo,
                t.documento or '', sequencia=seq,
            )

            # Verifica colisao
            colisao = PessoalTransacao.query.filter(
                PessoalTransacao.id != t.id,
                PessoalTransacao.hash_transacao == novo_hash,
            ).first()
            if colisao:
                colisoes.append({
                    'tx_id': t.id, 'tx_hash_novo': novo_hash,
                    'colide_com_id': colisao.id, 'colide_em_imp': colisao.importacao_id,
                })
                logger.warning(
                    'COLISAO tx_id=%d -> hash %s ja existe em tx_id=%d (imp=%d)',
                    t.id, novo_hash[:16], colisao.id, colisao.importacao_id,
                )

            plano.append({
                'id': t.id, 'data_atual': t.data, 'data_nova': nova_data,
                'hash_atual': t.hash_transacao, 'hash_novo': novo_hash,
                'historico': t.historico, 'valor': float(t.valor), 'tipo': t.tipo,
            })

        if colisoes:
            logger.error('HA %d COLISOES DE HASH — abortando.', len(colisoes))
            for c in colisoes:
                print(f'  {c}')
            sys.exit(1)

        logger.info('Nenhuma colisao. Plano:')
        for p_ in plano:
            logger.info(
                '  tx=%d %s -> %s | %s R$%.2f | %s',
                p_['id'], p_['data_atual'], p_['data_nova'],
                p_['tipo'], p_['valor'], p_['historico'],
            )

        imp = db.session.get(PessoalImportacao, IMP_ID)
        novo_periodo_inicio = subtract_one_year(imp.periodo_inicio) if imp.periodo_inicio else None
        novo_periodo_fim = subtract_one_year(imp.periodo_fim) if imp.periodo_fim else None
        logger.info('Imp periodo: %s..%s -> %s..%s',
                    imp.periodo_inicio, imp.periodo_fim,
                    novo_periodo_inicio, novo_periodo_fim)

        # Imp vazias a deletar
        imps_vazias = PessoalImportacao.query.filter(
            PessoalImportacao.id.in_(IMPS_VAZIAS),
        ).all()
        for iv in imps_vazias:
            n = PessoalTransacao.query.filter_by(importacao_id=iv.id).count()
            logger.info('Imp vazia #%d (arq=%s): %d transacoes %s',
                        iv.id, iv.nome_arquivo, n,
                        'OK para deletar' if n == 0 else 'NAO VAZIA — pulando')

        if args.dry_run:
            logger.info('[DRY-RUN] Nada aplicado.')
            return

        # APLICAR — flush por update para pegar colisao intra-batch precocemente
        for p_ in plano:
            t = db.session.get(PessoalTransacao, p_['id'])
            t.data = p_['data_nova']
            t.hash_transacao = p_['hash_novo']
            try:
                db.session.flush()
            except Exception as ex:
                logger.error('Falha no flush tx_id=%d: %s', p_['id'], ex)
                db.session.rollback()
                raise
        imp.periodo_inicio = novo_periodo_inicio
        imp.periodo_fim = novo_periodo_fim

        for iv in imps_vazias:
            n = PessoalTransacao.query.filter_by(importacao_id=iv.id).count()
            if n == 0:
                db.session.delete(iv)
                logger.info('Imp #%d deletada', iv.id)

        db.session.commit()
        logger.info('[OK] Aplicado. %d transacoes corrigidas.', len(plano))


if __name__ == '__main__':
    main()
