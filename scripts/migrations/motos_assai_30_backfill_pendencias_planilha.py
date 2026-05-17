"""Migration 30: backfill de eventos a partir de "backfill pendencias.xlsx" (17/05/2026).

Dois cenarios cobertos:

  BLOCO 1 — DISPONIVEL backfill (5 chassis SOL, planilha=DISPONIVEL, banco=PENDENTE):
    PENDENTE -> PENDENCIA_RESOLVIDA -> MONTADA -> DISPONIVEL
    (3 eventos por chassi = 15 eventos)

  BLOCO 2 — PENDENTE backfill (3 chassis DOT PRETO, planilha=PENDENTE, banco=DISPONIVEL):
    DISPONIVEL -> REVERTIDA_PARA_MONTADA -> PENDENTE (motivo/descricao=PLACA)
    (2 eventos por chassi = 6 eventos)

  Total: 21 eventos.

NAO TOCA:
  - 126 chassis ja sincronizados
  - 11 chassis planilha=FATURADAS, banco=PENDENTE (aguardar import NF Q.P.A.)

Operador: Claude Code (id=74) — usuario ja existente (administrador).

Idempotente: nao re-insere eventos com dados_extras->>'origem'='backfill_planilha_2026_05_17'.

Rodar:
  python scripts/migrations/motos_assai_30_backfill_pendencias_planilha.py --dry-run
  python scripts/migrations/motos_assai_30_backfill_pendencias_planilha.py
"""
import os
import sys
import argparse
import json
from datetime import timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app import create_app, db  # noqa: E402
from app.utils.timezone import agora_brasil_naive  # noqa: E402
from sqlalchemy import text  # noqa: E402

OPERADOR_ID = 74  # Claude Code (administrador, claude@local.com)

# --- BLOCO 1: DISPONIVEL backfill ---
CHASSIS_BACKFILL_DISPONIVEL = [
    '172922504673431',
    '172922504672472',
    '172922504672396',
    '172922504672366',
    '172922512170018',
]
SEQUENCIA_DISPONIVEL = [
    ('PENDENCIA_RESOLVIDA', 'Backfill 2026-05-17: pendencia resolvida fora do sistema (planilha)'),
    ('MONTADA',             'Backfill 2026-05-17: montagem registrada via planilha'),
    ('DISPONIVEL',          'Backfill 2026-05-17: disponibilizada manualmente via planilha'),
]

# --- BLOCO 2: PENDENTE backfill (DISPONIVEL no banco mas planilha diz PENDENTE com PLACA) ---
CHASSIS_BACKFILL_PENDENTE = [
    'LA2025SA110004615',
    'LA2025SA110004682',
    'LA2025SA110009008',
]
SEQUENCIA_PENDENTE = [
    ('REVERTIDA_PARA_MONTADA', 'PLACA — reverter DISPONIVEL para registrar pendencia conforme planilha 2026-05-17'),
    ('PENDENTE',               'PLACA'),
]

ORIGEM_TAG = 'backfill_planilha_2026_05_17'
DADOS_EXTRAS_DISPONIVEL = json.dumps({
    'origem': ORIGEM_TAG,
    'arquivo': 'backfill pendencias.xlsx',
    'solicitante': 'Rafael',
    'bloco': 'disponivel',
})
DADOS_EXTRAS_PENDENTE = json.dumps({
    'origem': ORIGEM_TAG,
    'arquivo': 'backfill pendencias.xlsx',
    'solicitante': 'Rafael',
    'bloco': 'pendente',
    'motivo': 'PLACA',
})


def validar_operador() -> None:
    """Garante que Claude Code (id=74) existe antes de prosseguir."""
    row = db.session.execute(
        text("SELECT nome FROM usuarios WHERE id = :uid"),
        {'uid': OPERADOR_ID},
    ).fetchone()
    if row is None:
        raise RuntimeError(f'Usuario id={OPERADOR_ID} nao encontrado. Abortando.')
    print(f'  [ok] Operador validado: id={OPERADOR_ID} nome="{row[0]}"')


def _status_efetivo(chassi: str) -> str | None:
    """Retorna tipo do ultimo evento ou None se nao houver eventos."""
    row = db.session.execute(
        text("""
            SELECT tipo FROM assai_moto_evento
            WHERE chassi = :chassi
            ORDER BY ocorrido_em DESC, id DESC
            LIMIT 1
        """),
        {'chassi': chassi},
    ).fetchone()
    return row[0] if row is not None else None


def _ja_processado(chassi: str, bloco: str) -> int:
    """Conta eventos previamente inseridos pelo backfill no bloco indicado."""
    return db.session.execute(
        text("""
            SELECT COUNT(*) FROM assai_moto_evento
            WHERE chassi = :chassi
              AND (dados_extras->>'origem') = :tag
              AND (dados_extras->>'bloco') = :bloco
        """),
        {'chassi': chassi, 'tag': ORIGEM_TAG, 'bloco': bloco},
    ).scalar() or 0


def _inserir_sequencia(chassi: str, sequencia: list, dados_extras_json: str) -> None:
    """Insere N eventos sequenciais (+1s entre eles) para o chassi."""
    base = agora_brasil_naive()
    for offset, (tipo, obs) in enumerate(sequencia):
        db.session.execute(
            text("""
                INSERT INTO assai_moto_evento
                    (chassi, tipo, ocorrido_em, operador_id, observacao, dados_extras)
                VALUES
                    (:chassi, :tipo, :ts, :op, :obs, CAST(:dx AS jsonb))
            """),
            {
                'chassi': chassi,
                'tipo': tipo,
                'ts': base + timedelta(seconds=offset),
                'op': OPERADOR_ID,
                'obs': obs,
                'dx': dados_extras_json,
            },
        )


def backfill_eventos_disponivel(dry_run: bool) -> dict:
    """Bloco 1: PENDENTE -> PENDENCIA_RESOLVIDA -> MONTADA -> DISPONIVEL.

    Aplica apenas para chassis com status efetivo == PENDENTE.
    """
    stats = {
        'processados': 0,
        'pulados_status_diferente': 0,
        'pulados_ja_backfill': 0,
        'eventos_inseridos': 0,
    }
    n_eventos = len(SEQUENCIA_DISPONIVEL)

    for chassi in CHASSIS_BACKFILL_DISPONIVEL:
        status = _status_efetivo(chassi)
        if status is None:
            print(f'  [skip] {chassi}: sem nenhum evento')
            stats['pulados_status_diferente'] += 1
            continue
        if status != 'PENDENTE':
            print(f'  [skip] {chassi}: status efetivo = {status} (esperado PENDENTE)')
            stats['pulados_status_diferente'] += 1
            continue

        ja = _ja_processado(chassi, 'disponivel')
        if ja > 0:
            print(f'  [skip] {chassi}: ja tem {ja} eventos no bloco disponivel')
            stats['pulados_ja_backfill'] += 1
            continue

        if dry_run:
            print(f'  [dry-run] {chassi}: registraria PENDENCIA_RESOLVIDA -> MONTADA -> DISPONIVEL')
        else:
            _inserir_sequencia(chassi, SEQUENCIA_DISPONIVEL, DADOS_EXTRAS_DISPONIVEL)
            print(f'  [ok] {chassi}: {n_eventos} eventos inseridos (PENDENCIA_RESOLVIDA -> MONTADA -> DISPONIVEL)')

        stats['processados'] += 1
        stats['eventos_inseridos'] += n_eventos

    return stats


def backfill_eventos_pendente(dry_run: bool) -> dict:
    """Bloco 2: DISPONIVEL -> REVERTIDA_PARA_MONTADA -> PENDENTE.

    Aplica apenas para chassis com status efetivo == DISPONIVEL.
    Motivo/descricao: PLACA (conforme planilha).
    """
    stats = {
        'processados': 0,
        'pulados_status_diferente': 0,
        'pulados_ja_backfill': 0,
        'eventos_inseridos': 0,
    }
    n_eventos = len(SEQUENCIA_PENDENTE)

    for chassi in CHASSIS_BACKFILL_PENDENTE:
        status = _status_efetivo(chassi)
        if status is None:
            print(f'  [skip] {chassi}: sem nenhum evento')
            stats['pulados_status_diferente'] += 1
            continue
        if status != 'DISPONIVEL':
            print(f'  [skip] {chassi}: status efetivo = {status} (esperado DISPONIVEL)')
            stats['pulados_status_diferente'] += 1
            continue

        ja = _ja_processado(chassi, 'pendente')
        if ja > 0:
            print(f'  [skip] {chassi}: ja tem {ja} eventos no bloco pendente')
            stats['pulados_ja_backfill'] += 1
            continue

        if dry_run:
            print(f'  [dry-run] {chassi}: registraria REVERTIDA_PARA_MONTADA -> PENDENTE (PLACA)')
        else:
            _inserir_sequencia(chassi, SEQUENCIA_PENDENTE, DADOS_EXTRAS_PENDENTE)
            print(f'  [ok] {chassi}: {n_eventos} eventos inseridos (REVERTIDA_PARA_MONTADA -> PENDENTE [PLACA])')

        stats['processados'] += 1
        stats['eventos_inseridos'] += n_eventos

    return stats


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry-run', action='store_true', help='Mostra o que faria sem aplicar')
    args = ap.parse_args()

    app = create_app()
    with app.app_context():
        modo = 'DRY-RUN' if args.dry_run else 'APLICANDO'
        print(f'=== Migration 30 — backfill pendencias planilha ({modo}) ===')

        print('\n[1] Validando operador (id=74 Claude Code)...')
        validar_operador()

        print('\n[2] BLOCO 1 — DISPONIVEL backfill (PENDENCIA_RESOLVIDA -> MONTADA -> DISPONIVEL)...')
        stats_disp = backfill_eventos_disponivel(args.dry_run)

        print('\n[3] BLOCO 2 — PENDENTE backfill (REVERTIDA_PARA_MONTADA -> PENDENTE [PLACA])...')
        stats_pend = backfill_eventos_pendente(args.dry_run)

        print(f'\n[stats] bloco_disponivel: {stats_disp}')
        print(f'[stats] bloco_pendente:   {stats_pend}')
        total_eventos = stats_disp["eventos_inseridos"] + stats_pend["eventos_inseridos"]
        print(f'[stats] total_eventos:    {total_eventos}')

        if args.dry_run:
            print('\n[dry-run] Nada commitado. Rode sem --dry-run para aplicar.')
        else:
            db.session.commit()
            print('\n[commit] OK')

        print('\n=== Fim ===')


if __name__ == '__main__':
    main()
