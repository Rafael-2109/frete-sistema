"""Detecta e remove duplicatas de pessoal_transacoes pelo algoritmo NOVO de
dedup (`base_parser.gerar_hash_transacao` apos correcoes de 2026-05-10
em documento e valor).

Logica:
- Recalcula a chave normalizada para cada transacao usando os mesmos
  normalizadores do hash atual (`normalizar_documento`, `normalizar_valor`,
  `normalizar_historico`).
- Atribui sequencia POR IMPORTACAO (replica o parser).
- Identifica colisoes: 2+ IDs com mesma (importacao_id, chave_norm, seq) — NAO,
  na verdade colisao e a mesma chave_norm + mesma seq em IMPORTACOES DIFERENTES.
  Em uma mesma importacao, sequencia ja diferencia. Cross-import pode dar
  colisao quando a re-importacao (52) trouxe os mesmos itens.
- Para cada grupo de colisao: mantem MENOR id (mais antigo); deleta os demais
  apos validar que valor_compensado=0 e que ZERO referencias apontam para eles
  em pessoal_compensacoes/pessoal_provisoes/pessoal_importacoes.
- Ajusta linhas_importadas/linhas_duplicadas das importacoes afetadas.

Uso:
    source .venv/bin/activate
    python scripts/migrations/limpar_duplicatas_dedup_v2.py             # dry-run
    python scripts/migrations/limpar_duplicatas_dedup_v2.py --aplicar   # aplica

Idempotente: rodar 2x e a 2a vez nao remove nada (porque ja foram removidas).
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
    normalizar_historico, normalizar_documento, normalizar_valor,
)


def _chave_norm(t: PessoalTransacao) -> str:
    return (
        f"{t.conta_id}|{t.data.isoformat()}|{normalizar_historico(t.historico)}|"
        f"{normalizar_valor(t.valor)}|{t.tipo}|{normalizar_documento(t.documento)}"
    )


def _check_referencias(ids: list[int]) -> dict:
    if not ids:
        return {'compensacoes': 0, 'provisoes': 0, 'importacoes_pagamento': 0}
    placeholders = ','.join(str(i) for i in ids)
    out = {}
    out['compensacoes'] = db.session.execute(db.text(f"""
        SELECT COUNT(*) FROM pessoal_compensacoes
         WHERE saida_id IN ({placeholders}) OR entrada_id IN ({placeholders})
    """)).scalar() or 0
    out['provisoes'] = db.session.execute(db.text(f"""
        SELECT COUNT(*) FROM pessoal_provisoes WHERE transacao_id IN ({placeholders})
    """)).scalar() or 0
    out['importacoes_pagamento'] = db.session.execute(db.text(f"""
        SELECT COUNT(*) FROM pessoal_importacoes
         WHERE transacao_pagamento_id IN ({placeholders})
    """)).scalar() or 0
    return out


def main(aplicar: bool = False):
    app = create_app()
    with app.app_context():
        print(f"[*] Modo: {'APLICAR' if aplicar else 'DRY-RUN'}")

        txs = PessoalTransacao.query.order_by(
            PessoalTransacao.importacao_id.asc(),
            PessoalTransacao.id.asc(),
        ).all()
        print(f'[*] Transacoes carregadas: {len(txs)}')

        # Atribui sequencia por importacao+chave_norm
        contadores: dict[tuple[int, str], int] = defaultdict(int)
        # Map global: (chave_norm, seq) -> [id1, id2, ...]
        grupos_globais: dict[tuple[str, int], list[int]] = defaultdict(list)
        for t in txs:
            chave = _chave_norm(t)
            chave_imp = (t.importacao_id, chave)
            seq = contadores[chave_imp]
            contadores[chave_imp] += 1
            grupos_globais[(chave, seq)].append(t.id)

        # Colisoes = grupos com 2+ ids (cross-import)
        colisoes = {k: ids for k, ids in grupos_globais.items() if len(ids) > 1}
        print(f'[*] Grupos colidentes (duplicatas reais): {len(colisoes)}')
        if not colisoes:
            print('[OK] Nenhuma duplicata detectada. Nada a fazer.')
            return

        # Listar e separar: manter MENOR id, deletar os demais
        para_deletar: list[int] = []
        manter: list[int] = []
        for (chave, seq), ids in colisoes.items():
            ids_sorted = sorted(ids)
            manter.append(ids_sorted[0])
            para_deletar.extend(ids_sorted[1:])

        # Verificacao de seguranca: valor_compensado=0 e zero referencias
        bloqueios: list[int] = []
        if para_deletar:
            placeholders = ','.join(str(i) for i in para_deletar)
            rows = db.session.execute(db.text(f"""
                SELECT id, valor_compensado FROM pessoal_transacoes
                 WHERE id IN ({placeholders}) AND COALESCE(valor_compensado, 0) > 0
            """)).fetchall()
            bloqueios = [r.id for r in rows]
        refs = _check_referencias(para_deletar)
        print(f'[*] IDs a deletar: {len(para_deletar)} (manter {len(manter)})')
        print(f'[*] Bloqueios por valor_compensado>0: {bloqueios or "[]"}')
        print(f'[*] Referencias externas: {refs}')

        if bloqueios:
            print('[ERRO] Algumas duplicatas tem compensacao registrada — abortar.')
            return
        if any(v > 0 for v in refs.values()):
            print('[ERRO] Algumas duplicatas tem referencias externas — abortar.')
            return

        # Preview
        print('[*] Amostra (ate 30):')
        for (chave, seq), ids in list(colisoes.items())[:30]:
            print(f"    chave={chave!r} seq={seq} ids={sorted(ids)} (manter {min(ids)})")

        if not aplicar:
            print('[OK] DRY-RUN concluido. Reexecute com --aplicar para deletar.')
            return

        # DELETE em batch
        # Conta quantas linhas serao removidas por importacao para ajustar contadores
        impacto_imp: dict[int, int] = defaultdict(int)
        rows_imp = db.session.execute(db.text(f"""
            SELECT id, importacao_id FROM pessoal_transacoes WHERE id IN ({placeholders})
        """)).fetchall()
        for r in rows_imp:
            impacto_imp[r.importacao_id] += 1

        result = db.session.execute(db.text(f"""
            DELETE FROM pessoal_transacoes WHERE id IN ({placeholders})
        """))
        deletadas = result.rowcount or 0
        print(f'[OK] DELETE: {deletadas} linhas')

        for imp_id, n in impacto_imp.items():
            db.session.execute(db.text("""
                UPDATE pessoal_importacoes
                   SET linhas_importadas = GREATEST(linhas_importadas - :n, 0),
                       linhas_duplicadas = linhas_duplicadas + :n
                 WHERE id = :i
            """), {'n': n, 'i': imp_id})
            print(f'    [contador] imp={imp_id}: -{n} importadas / +{n} duplicadas')

        db.session.commit()
        print('[OK] Commit ok.')


if __name__ == '__main__':
    aplicar = '--aplicar' in sys.argv
    main(aplicar=aplicar)
