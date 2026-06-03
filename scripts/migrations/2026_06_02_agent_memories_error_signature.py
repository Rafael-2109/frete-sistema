"""Fase 3 (loop corretivo): colunas de MEDICAO POR OUTCOME + assinatura de erro em
agent_memories. Adiciona 3 colunas + 1 indice composto, todas idempotentes.

- error_signature VARCHAR(64): assinatura ESTAVEL da INTENCAO do erro (nao do texto
  literal). Casa reincidencia entre sessoes e alimenta a metrica de reincidencia por
  assinatura ANTES vs DEPOIS da promocao (DoD do loop corretivo).
- harmful_count INTEGER: regra 'mandatory' injetada e o MESMO erro reincidiu mesmo
  assim -> a regra dura falhou (sinal de outcome NEGATIVO, alimenta demote/reescrita).
- helpful_count INTEGER: regra 'mandatory' injetada e SEM reincidencia por K sessoes
  -> a regra funcionou (sinal de outcome POSITIVO). Desacoplado do eco textual
  (effective_count, que permanece intacto so para o dashboard).
- ix_agent_memories_user_errsig (user_id, error_signature): a metrica conta
  reincidencia por (user, assinatura).

Dual-artefato (regra CLAUDE.md): este .py (create_app + verificacao before/after) + o
.sql idempotente par para o Render Shell.
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app import create_app, db
from sqlalchemy import text, inspect

_COLUNAS = {
    'error_signature': "ALTER TABLE agent_memories ADD COLUMN IF NOT EXISTS error_signature VARCHAR(64)",
    'harmful_count': "ALTER TABLE agent_memories ADD COLUMN IF NOT EXISTS harmful_count INTEGER NOT NULL DEFAULT 0",
    'helpful_count': "ALTER TABLE agent_memories ADD COLUMN IF NOT EXISTS helpful_count INTEGER NOT NULL DEFAULT 0",
}


def _colunas_existentes():
    insp = inspect(db.engine)
    return {c['name'] for c in insp.get_columns('agent_memories')}


def _tem_indice():
    insp = inspect(db.engine)
    return any(ix['name'] == 'ix_agent_memories_user_errsig'
               for ix in insp.get_indexes('agent_memories'))


def main():
    app = create_app()
    with app.app_context():
        cols_antes = _colunas_existentes()
        ix_antes = _tem_indice()
        print(f"[loop-corretivo migration] colunas ANTES: "
              f"{ {c: (c in cols_antes) for c in _COLUNAS} } | indice ANTES? {ix_antes}")

        for nome, ddl in _COLUNAS.items():
            if nome not in cols_antes:
                db.session.execute(text(ddl))
        db.session.commit()

        if not ix_antes:
            db.session.execute(text(
                "CREATE INDEX IF NOT EXISTS ix_agent_memories_user_errsig "
                "ON agent_memories (user_id, error_signature)"
            ))
            db.session.commit()

        cols_depois = _colunas_existentes()
        ix_depois = _tem_indice()
        print(f"[loop-corretivo migration] colunas DEPOIS: "
              f"{ {c: (c in cols_depois) for c in _COLUNAS} } | indice DEPOIS? {ix_depois}")
        for nome in _COLUNAS:
            assert nome in cols_depois, f"Falha: coluna {nome} nao criada"
        assert ix_depois, "Falha: indice ix_agent_memories_user_errsig nao criado"
        print("[loop-corretivo migration] OK")


if __name__ == '__main__':
    main()
