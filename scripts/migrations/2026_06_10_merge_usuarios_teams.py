"""Data-fix: merge de usuarios fantasma do Teams (@teams.nacomgoya.local) em usuarios reais.

Reaponta TODAS as referencias a usuarios(id) — FKs formais + tabelas do dominio
do agente sem FK (agent_sessions, agent_step, etc.) — do fantasma para o real,
e bloqueia o fantasma. Reusa app.teams.services.merge_usuario_teams.

Uso:
    # Dry-run (default) de um par especifico:
    python scripts/migrations/2026_06_10_merge_usuarios_teams.py \
        --user-fantasma-id 99 --user-real-id 1

    # Executar de verdade:
    python scripts/migrations/2026_06_10_merge_usuarios_teams.py \
        --user-fantasma-id 99 --user-real-id 1 --confirmar

    # Modo auto: casa cada fantasma cujo NOME bate com usuario real ja
    # vinculado (teams_user_id preenchido) e migra (dry-run sem --confirmar):
    python scripts/migrations/2026_06_10_merge_usuarios_teams.py --auto

    # Apenas listar fantasmas existentes:
    python scripts/migrations/2026_06_10_merge_usuarios_teams.py --listar
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app import create_app, db  # noqa: E402


def _listar_fantasmas():
    from app.auth.models import Usuario
    return Usuario.query.filter(
        Usuario.email.like('%@teams.nacomgoya.local')
    ).order_by(Usuario.id).all()


def _executar_par(fantasma_id: int, real_id: int, confirmar: bool) -> None:
    from app.auth.models import Usuario
    from app.teams.services import merge_usuario_teams

    fantasma = db.session.get(Usuario, fantasma_id)
    real = db.session.get(Usuario, real_id)
    if not fantasma or not real:
        print(f'ERRO: usuario nao encontrado (fantasma={fantasma_id}, real={real_id})')
        sys.exit(1)
    if '@teams.nacomgoya.local' not in (fantasma.email or ''):
        print(f'ERRO: user {fantasma_id} ({fantasma.email}) NAO e fantasma Teams. Abortando.')
        sys.exit(1)
    if fantasma_id == real_id:
        print('ERRO: fantasma e real sao o mesmo usuario.')
        sys.exit(1)

    modo = 'EXECUTANDO' if confirmar else 'DRY-RUN'
    print(f'[{modo}] {fantasma.nome} (id={fantasma_id}, {fantasma.email})')
    print(f'       -> {real.nome} (id={real_id}, {real.email})')
    out = merge_usuario_teams(fantasma_id, real_id, dry_run=not confirmar)
    for chave, n in sorted(out['tabelas'].items()):
        print(f'  {chave}: {n} linha(s)')
    if not out['tabelas']:
        print('  (nenhuma linha a migrar)')
    for erro in out['erros']:
        print(f'  ERRO: {erro}')


def _executar_auto(confirmar: bool) -> None:
    """Casa fantasmas com usuarios reais pelo NOME (real ja vinculado via codigo/email)."""
    from sqlalchemy import func as sa_func
    from app.auth.models import Usuario

    fantasmas = _listar_fantasmas()
    if not fantasmas:
        print('Nenhum usuario fantasma encontrado.')
        return
    pares = []
    for f in fantasmas:
        if f.status == 'bloqueado':
            continue  # ja mergeado
        real = Usuario.query.filter(
            sa_func.lower(Usuario.nome) == (f.nome or '').lower().strip(),
            Usuario.teams_user_id.isnot(None),
            Usuario.status == 'ativo',
            Usuario.id != f.id,
        ).first()
        if real:
            pares.append((f, real))
        else:
            print(f'  SEM PAR: {f.nome} (id={f.id}) — nenhum usuario real vinculado com mesmo nome')
    print(f'\n{len(pares)} par(es) encontrados.\n')
    for f, r in pares:
        _executar_par(f.id, r.id, confirmar)
        print()


def main() -> None:
    parser = argparse.ArgumentParser(description='Merge de usuarios fantasma Teams -> reais')
    parser.add_argument('--user-fantasma-id', type=int, help='id do usuario @teams.nacomgoya.local')
    parser.add_argument('--user-real-id', type=int, help='id do usuario web verdadeiro')
    parser.add_argument('--auto', action='store_true',
                        help='casa fantasmas por nome com usuarios reais ja vinculados')
    parser.add_argument('--listar', action='store_true', help='apenas lista os fantasmas')
    parser.add_argument('--confirmar', action='store_true',
                        help='executa de verdade (default: dry-run)')
    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        if args.listar:
            for f in _listar_fantasmas():
                vinculo = f' [MERGED]' if f.status == 'bloqueado' else ''
                print(f'  id={f.id} nome="{f.nome}" email={f.email}{vinculo}')
            return
        if args.auto:
            _executar_auto(args.confirmar)
            return
        if args.user_fantasma_id and args.user_real_id:
            _executar_par(args.user_fantasma_id, args.user_real_id, args.confirmar)
            return
        parser.print_help()
        sys.exit(1)


if __name__ == '__main__':
    main()
