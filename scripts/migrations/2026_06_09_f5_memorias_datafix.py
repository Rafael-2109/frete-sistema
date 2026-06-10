"""Data-fix F5 PAD-CTX: consolidar system-pitfalls duplicado + marcar memorias promovidas.

Plano: docs/superpowers/plans/2026-06-09-arquitetura-contexto-boot-agente.md FASE 5
(backlog system-pitfalls + tarefa 5.6). Sem DDL — data fix Python only.

O que faz (idempotente):
1. system-pitfalls.json (user 0) -> is_cold=true.
   O .json e a FONTE DE VERDADE do tool log_system_pitfall (lido por
   get_by_path, que NAO filtra cold); o .xml e o formato RENDERIZADO para
   injecao (_regenerate_pitfalls_xml). Ambos eram injetados JUNTOS todo turno
   (mesmo conteudo, 2 formatos, ~25KB). is_cold tira o .json da injecao e da
   busca semantica SEM quebrar o tool.
2. Memorias ja PROMOVIDAS a codigo (MEMORY_PROTOCOL.md §Promocao) ->
   is_cold=true + meta.promovida_para:
   - tmpdir divergente  -> guard em app/agente/routes/_constants.py (AGENTE_FILES_ROOT)
   - arquivo vazio      -> guard _verificar_entrega em exportando-arquivos (P7 #787)
   Saem da injecao; historico segue buscavel via search_cold_memories.

Uso:
    python scripts/migrations/2026_06_09_f5_memorias_datafix.py            # dry-run
    python scripts/migrations/2026_06_09_f5_memorias_datafix.py --confirmar
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

ALVOS = [
    # (user_id, path, promovida_para ou None)
    (0, '/memories/empresa/armadilhas/system-pitfalls.json', None),
    (0, '/memories/empresa/armadilhas/integracao/tmpdir-divergente-entre-agente-e-web-server.xml',
     'app/agente/routes/_constants.py (AGENTE_FILES_ROOT — guard determinista do TMPDIR)'),
    (1, '/memories/corrections/agente-enviou-link-de-arquivo-vazio-usuario-confirmou-que-o.xml',
     '.claude/skills/exportando-arquivos/scripts/exportar.py (_verificar_entrega — guard P7 #787)'),
]


def main():
    confirmar = '--confirmar' in sys.argv

    from app import create_app, db
    from app.agente.models import AgentMemory

    app = create_app()
    with app.app_context():
        mudancas = 0
        for user_id, path, promovida_para in ALVOS:
            mem = AgentMemory.get_by_path(user_id, path)
            if mem is None:
                print(f'[SKIP] nao existe: user={user_id} {path}')
                continue

            ja_cold = bool(mem.is_cold)
            meta = dict(mem.meta or {})
            ja_marcada = bool(meta.get('promovida_para')) if promovida_para else True

            if ja_cold and ja_marcada:
                print(f'[OK-IDEMPOTENTE] ja aplicado: id={mem.id} {path}')
                continue

            acao = []
            if not ja_cold:
                acao.append('is_cold=true')
            if promovida_para and not meta.get('promovida_para'):
                acao.append(f'meta.promovida_para={promovida_para!r}')

            print(f'[{"APPLY" if confirmar else "DRY-RUN"}] id={mem.id} '
                  f'user={user_id} {path}\n         -> {", ".join(acao)}')
            mudancas += 1

            if confirmar:
                mem.is_cold = True
                if promovida_para:
                    meta['promovida_para'] = promovida_para
                    mem.meta = meta  # atribui dict NOVO (R7 — sem flag_modified)

        if confirmar and mudancas:
            db.session.commit()
            print(f'\n[OK] {mudancas} memoria(s) atualizada(s) e commitada(s).')
        elif not confirmar:
            print(f'\n[DRY-RUN] {mudancas} mudanca(s) pendente(s). '
                  'Re-rode com --confirmar para aplicar.')
        else:
            print('\n[OK] nada a fazer (idempotente).')


if __name__ == '__main__':
    main()
