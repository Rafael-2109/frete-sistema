"""Recalcula `pessoal_transacoes.hash_transacao` com algoritmo novo
(`base_parser.gerar_hash_transacao`) que normaliza `documento` (lstrip '0')
e `valor` (quantize 2 casas).

Necessidade: sem regenerar, futuras re-importacoes nao reconhecerao as
transacoes antigas como duplicatas (porque o hash velho continua armazenado).

Estrategia:
1. Para cada transacao existente, recalcula o hash com a logica atual
   determinando `sequencia` a partir do agrupamento por chave normalizada,
   ordenado por id ASC (preserva ordem historica).
2. Detecta colisoes ANTES de aplicar:
   - Se 2 transacoes existentes terao o MESMO novo hash, sao duplicatas reais
     (mesmo conta+data+histNorm+valor+tipo+docNorm+sequencia).
   - Lista as colisoes para revisao manual; nao aplica enquanto houver.
3. Aplica UPDATE em batch (so onde mudar).

Uso:
    source .venv/bin/activate
    python scripts/migrations/recalcular_hash_transacao_pessoal.py             # dry-run + relatorio
    python scripts/migrations/recalcular_hash_transacao_pessoal.py --aplicar   # aplica
    python scripts/migrations/recalcular_hash_transacao_pessoal.py --aplicar --ignorar-colisoes
                                                                                # aplica mantendo o hash antigo
                                                                                # nas IDs colidentes (forma segura
                                                                                # de avancar quando duplicatas
                                                                                # serao tratadas separadamente)

Idempotente: rodar 2x sem efeito quando hashes ja estao atualizados.
"""
from __future__ import annotations

import os
import sys
from collections import defaultdict

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from app import create_app, db  # noqa: E402
from app.pessoal.models import PessoalTransacao  # noqa: E402
from app.pessoal.services.parsers.base_parser import (  # noqa: E402
    gerar_hash_transacao, normalizar_historico, normalizar_documento, normalizar_valor,
)


def _chave_base(t: PessoalTransacao) -> str:
    """Mesma chave usada em routes/importacao.py para contagem de sequencia."""
    return (
        f"{t.conta_id}|{t.data.isoformat()}|{normalizar_historico(t.historico)}|"
        f"{normalizar_valor(t.valor)}|{t.tipo}|{normalizar_documento(t.documento)}"
    )


def main(aplicar: bool = False, ignorar_colisoes: bool = False):
    app = create_app()
    with app.app_context():
        print(f"[*] Modo: {'APLICAR' if aplicar else 'DRY-RUN'}"
              f"{' (ignorar colisoes)' if ignorar_colisoes else ''}")

        txs = PessoalTransacao.query.order_by(
            PessoalTransacao.importacao_id.asc(),
            PessoalTransacao.id.asc(),
        ).all()
        print(f'[*] Transacoes a processar: {len(txs)}')

        # 1. Atribuir sequencia POR IMPORTACAO (replica fielmente o parser:
        #    `contagem_chaves = {}` reseta no inicio de cada importacao).
        #    Assim, duplicatas que vivem em importacoes distintas mas com mesma
        #    chave normalizada VAO colidir — o que e o comportamento correto.
        contadores: dict[tuple[int, str], int] = defaultdict(int)
        plano = []  # (id, hash_antigo, hash_novo, chave_base, seq, importacao_id)
        for t in txs:
            chave = _chave_base(t)
            chave_imp = (t.importacao_id, chave)
            seq = contadores[chave_imp]
            contadores[chave_imp] += 1
            novo = gerar_hash_transacao(
                t.conta_id, t.data, t.historico, t.valor, t.tipo,
                t.documento or '', sequencia=seq,
            )
            plano.append((t.id, t.hash_transacao, novo, chave, seq, t.importacao_id))

        # 2. Detectar colisoes (mesmo novo hash em IDs diferentes = duplicatas
        #    reais que escaparam do dedup com algoritmo antigo)
        por_hash = defaultdict(list)
        for tid, _antigo, h_novo, _c, _s, _imp in plano:
            por_hash[h_novo].append(tid)
        colisoes = {h: ids for h, ids in por_hash.items() if len(ids) > 1}

        # 3. Total de mudancas
        a_mudar = [(tid, antigo, novo) for tid, antigo, novo, *_ in plano if antigo != novo]
        ja_ok = len(plano) - len(a_mudar)

        print(f'[*] Hashes ja corretos: {ja_ok}')
        print(f'[*] Hashes a regenerar: {len(a_mudar)}')
        print(f'[*] Grupos com colisao novo-novo: {len(colisoes)}')
        if colisoes:
            print('    (sao duplicatas reais que escaparam ao dedup atual)')
            for h, ids in list(colisoes.items())[:20]:
                print(f'    novo_hash={h[:16]}... ids={ids}')
            if len(colisoes) > 20:
                print(f'    ... +{len(colisoes) - 20} grupos omitidos')

        if not aplicar:
            print('[OK] DRY-RUN concluido. Reexecute com --aplicar para gravar.')
            return

        if colisoes and not ignorar_colisoes:
            print('[ERRO] Existem colisoes — abortando. Limpe as duplicatas primeiro '
                  'OU rode com --aplicar --ignorar-colisoes para preservar hashes '
                  'antigos nas IDs colidentes.')
            return

        # IDs que farao parte de colisao (preservar hash antigo se ignorar_colisoes)
        ids_em_colisao: set[int] = set()
        if ignorar_colisoes:
            for ids in colisoes.values():
                # Mantem 1a (menor id) com novo hash; demais ficam com antigo
                ids_em_colisao.update(ids[1:])

        atualizados = 0
        pulados_colisao = 0
        for tid, antigo, novo in a_mudar:
            if antigo == novo:
                continue
            if tid in ids_em_colisao:
                pulados_colisao += 1
                continue
            db.session.execute(
                db.text('UPDATE pessoal_transacoes SET hash_transacao = :h WHERE id = :i'),
                {'h': novo, 'i': tid},
            )
            atualizados += 1
            if atualizados % 500 == 0:
                db.session.flush()
                print(f'    [progresso] {atualizados} atualizados...')

        db.session.commit()
        print(f'[OK] UPDATE concluido: {atualizados} hashes regenerados, '
              f'{pulados_colisao} preservados (em colisao)')


if __name__ == '__main__':
    aplicar = '--aplicar' in sys.argv
    ignorar = '--ignorar-colisoes' in sys.argv
    main(aplicar=aplicar, ignorar_colisoes=ignorar)
