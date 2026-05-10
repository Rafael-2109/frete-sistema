"""Data fix: Remove duplicatas da importacao 52 (re-importacao do extrato Bradesco
em 10/05/2026).

Causa: o `documento` entra cru no `gerar_hash_transacao` (`base_parser.py:115`).
A imp 44 gravou docs com zero a esquerda ('0111654'); a imp 52 gravou sem
('111654'). Resultado: hashes diferentes -> dedup falhou para 22 transacoes.

Apos verificar (LTRIM('0') confere): TODAS as 22 IDs alvo estao em imp 52,
todas com `valor_compensado=0` e ZERO compensacoes ATIVAS apontando para
elas (consultado via MCP Render em 2026-05-10). Logo, DELETE direto e seguro.

Outras tabelas que referenciam pessoal_transacoes (sem ON DELETE CASCADE
explicito; checar antes de remover):
- pessoal_compensacoes.{saida_id, entrada_id}  -> consultado: 0 linhas
- pessoal_provisoes.transacao_id               -> consultado abaixo
- pessoal_importacoes.transacao_pagamento_id   -> consultado abaixo

Uso:
    source .venv/bin/activate
    python scripts/migrations/limpar_duplicatas_importacao_52.py             # dry-run
    python scripts/migrations/limpar_duplicatas_importacao_52.py --aplicar   # aplica

Idempotente: ja deletadas nao causam erro.
"""
from __future__ import annotations

import os
import sys

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from app import create_app, db  # noqa: E402
from sqlalchemy import text  # noqa: E402


# IDs identificados como duplicatas reais (importacao 52, mesmo conta+data+valor+tipo
# que outra ja existente, diferindo apenas no zero a esquerda do documento).
IDS_DUPLICATAS = [
    3834, 3835, 3837, 3840, 3841, 3842, 3843, 3844, 3846, 3848, 3849, 3850,
    3851, 3852, 3856, 3857, 3860, 3861, 3862, 3863, 3868, 3870,
]


def _check_referencias(ids: list[int]) -> dict:
    """Consulta tabelas que apontam para pessoal_transacoes para evitar surpresas."""
    placeholders = ','.join(str(i) for i in ids)
    queries = {
        'compensacoes_ativas': f"""
            SELECT COUNT(*) FROM pessoal_compensacoes
             WHERE status='ATIVA' AND (saida_id IN ({placeholders}) OR entrada_id IN ({placeholders}))
        """,
        'compensacoes_revertidas': f"""
            SELECT COUNT(*) FROM pessoal_compensacoes
             WHERE status='REVERTIDA' AND (saida_id IN ({placeholders}) OR entrada_id IN ({placeholders}))
        """,
        'provisoes_vinculadas': f"""
            SELECT COUNT(*) FROM pessoal_provisoes WHERE transacao_id IN ({placeholders})
        """,
        'importacoes_vinculadas': f"""
            SELECT COUNT(*) FROM pessoal_importacoes WHERE transacao_pagamento_id IN ({placeholders})
        """,
    }
    out = {}
    for k, sql in queries.items():
        out[k] = db.session.execute(text(sql)).scalar() or 0
    return out


def main(aplicar: bool = False):
    app = create_app()
    with app.app_context():
        print(f"[*] Modo: {'APLICAR (DELETE real)' if aplicar else 'DRY-RUN (somente preview)'}")
        print(f"[*] IDs alvo: {len(IDS_DUPLICATAS)} transacoes da importacao 52")

        # Snapshot ANTES (para auditoria + idempotencia)
        existentes = db.session.execute(text("""
            SELECT id, data, historico, descricao, documento, valor, tipo, importacao_id
              FROM pessoal_transacoes
             WHERE id = ANY(:ids)
             ORDER BY id
        """), {'ids': IDS_DUPLICATAS}).fetchall()

        if not existentes:
            print('[OK] Nenhuma das IDs alvo existe mais — nada a fazer.')
            return

        print(f'[*] {len(existentes)} transacoes alvo encontradas:')
        for r in existentes:
            print(f"    id={r.id} data={r.data} doc={r.documento!r} valor={r.valor} "
                  f"tipo={r.tipo} hist={r.historico!r} desc={r.descricao!r}")

        # Verificacao defensiva: nada deve apontar para essas IDs
        refs = _check_referencias(IDS_DUPLICATAS)
        print(f'[*] Referencias externas: {refs}')
        bloqueios = [k for k, v in refs.items() if v > 0]
        if bloqueios:
            print(f'[ERRO] Bloqueio: {bloqueios} > 0. Investigar antes de deletar.')
            return

        if not aplicar:
            print('[OK] DRY-RUN concluido. Reexecute com --aplicar para deletar.')
            return

        # DELETE em batch + ajuste de contadores na pessoal_importacoes
        ids_existentes = [r.id for r in existentes]
        result = db.session.execute(text("""
            DELETE FROM pessoal_transacoes WHERE id = ANY(:ids)
        """), {'ids': ids_existentes})
        deletadas = result.rowcount or 0
        print(f'[OK] DELETE: {deletadas} linhas removidas')

        # Ajustar contador linhas_importadas e somar em linhas_duplicadas
        atualiz = db.session.execute(text("""
            UPDATE pessoal_importacoes
               SET linhas_importadas = GREATEST(linhas_importadas - :n, 0),
                   linhas_duplicadas = linhas_duplicadas + :n
             WHERE id = 52
        """), {'n': deletadas})
        print(f'[OK] pessoal_importacoes.id=52 contadores ajustados ({atualiz.rowcount} linha)')

        db.session.commit()
        print('[OK] Commit ok.')

        # Verificacao DEPOIS
        sobra = db.session.execute(text(
            "SELECT COUNT(*) FROM pessoal_transacoes WHERE id = ANY(:ids)"
        ), {'ids': IDS_DUPLICATAS}).scalar()
        print(f'[OK] Verificacao final: {sobra} IDs alvo ainda existem (esperado: 0)')


if __name__ == '__main__':
    aplicar = '--aplicar' in sys.argv
    main(aplicar=aplicar)
