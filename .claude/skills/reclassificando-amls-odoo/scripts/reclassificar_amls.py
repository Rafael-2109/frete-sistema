"""reclassificar_amls.py — skill WRITE `reclassificando-amls-odoo`.

Expoe o atomo ReclassificacaoService via CLI: reclassifica em lote as
account.move.line de uma conta_origem para conta_destino, no periodo/company/
journal, preservando a chave fiscal (ciclo button_draft -> write account_id ->
action_post por move). `--dry-run` e o DEFAULT — sem `--confirmar` e so preview.

GUARDS (codificados no service, ver app/odoo/estoque/scripts/reclassificacao.py):
- GUARD SEFAZ: move com l10n_br_situacao_nf in (autorizado/excecao_autorizado/
  enviado) NAO entra no plano (button_draft invalidaria a chave fiscal).
- CONTADOR REAL pos-write: validar_lote da skill READ irma
  `auditando-reclassificacao-odoo` (integro + processadas==total + moves_draft==0).
- INVARIANTE pos action_post: re-le state; != posted -> FALHA e PARA o batch.
- Reclassifica SO as linhas na conta_origem (nunca as demais linhas do move).

--user-id e OBRIGATORIO e validado contra a tabela usuarios. Propaga
`executado_por` (nome do usuario) para o hook de auditoria operacao_odoo_odoo
(button_draft/write/action_post ja na whitelist app/utils/odoo_audit_helpers.py).

Exemplo:
  SK=.claude/skills/reclassificando-amls-odoo/scripts/reclassificar_amls.py
  # 1) dry-run (default): preview 26784 -> 26844, company 4, journal 845
  python "$SK" --conta-origem 26784 --conta-destino 26844 \
      --data-inicio 2025-09-01 --data-fim 2025-09-30 --company-id 4 --user-id 74
  # 2) efetivar (apos revisar o plano)
  python "$SK" --conta-origem 26784 --conta-destino 26844 \
      --data-inicio 2025-09-01 --data-fim 2025-09-30 --company-id 4 \
      --user-id 74 --confirmar

Exit: 0 efetivado · 4 dry-run OK · 1 falha/EXECUTADO_PARCIAL · 2 uso invalido.
"""
import argparse
import json
import os
import sys
from pathlib import Path

_THIS = Path(__file__).resolve()
# .claude/skills/<skill>/scripts/<f> -> repo root = parents[4]
sys.path.insert(0, str(_THIS.parents[4]))

from app.odoo.estoque._cli_utils import (  # noqa: E402
    adicionar_args_padrao, setup_cli_completo,
)
from app.odoo.estoque.scripts.reclassificacao import (  # noqa: E402
    DEFAULT_COMPANY_ID, DEFAULT_JOURNAL_ID, get_service,
)
from app.odoo.utils.connection import get_odoo_connection  # noqa: E402

_FALHAS = {'FALHA_POST_NAO_POSTED', 'FALHA_ODOO', 'EXECUTADO_PARCIAL'}


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=(__doc__ or '').strip().split('\n')[0])
    ap.add_argument('--conta-origem', type=int, required=True,
                    help='account.account de ORIGEM (ex: 26784)')
    ap.add_argument('--conta-destino', type=int, required=True,
                    help='account.account de DESTINO (ex: 26844)')
    ap.add_argument('--data-inicio', required=True, help='YYYY-MM-DD')
    ap.add_argument('--data-fim', required=True, help='YYYY-MM-DD')
    ap.add_argument('--company-id', type=int, default=DEFAULT_COMPANY_ID,
                    help=f'company_id (default {DEFAULT_COMPANY_ID})')
    ap.add_argument('--journal-id', type=int, default=DEFAULT_JOURNAL_ID,
                    help=f'journal_id (default {DEFAULT_JOURNAL_ID})')
    ap.add_argument('--batch', type=int, default=None,
                    help='limite de moves por execucao (default: todos do plano)')
    ap.add_argument('--user-id', type=int, required=True, dest='user_id',
                    help='OBRIGATORIO — id do usuario (validado contra usuarios; '
                         'propaga executado_por p/ auditoria)')
    ap.add_argument('--confirmar', action='store_true',
                    help='EFETIVA no Odoo. Sem isso = dry-run (preview).')
    ap.add_argument('--json', action='store_true',
                    help='Saida JSON (default: tambem JSON; flag reservada)')
    adicionar_args_padrao(ap)  # --quiet + --forcar-concorrencia
    return ap


def _exit_para_status(status: str, dry_run: bool) -> int:
    """Mapeia status do service -> exit code do CLI."""
    if status in _FALHAS:
        return 1
    if dry_run:
        return 4 if status == 'DRY_RUN_OK' else 1
    return 0 if status == 'EXECUTADO' else 1


def _validar_user(user_id):
    """Valida --user-id contra a tabela usuarios. Retorna (ok, nome|motivo)."""
    from app.auth.models import Usuario
    u = Usuario.query.get(user_id)
    if not u:
        return False, 'usuario_nao_encontrado'
    return True, u.nome


def _emitir(out: dict) -> None:
    print(json.dumps(out, ensure_ascii=False, indent=2, default=str))


def main() -> int:
    args = build_parser().parse_args()
    dry_run = not args.confirmar

    app = setup_cli_completo(__file__, args.quiet, args.forcar_concorrencia)
    with app.app_context():
        # 1) Autorizacao OBRIGATORIA (--user-id valido)
        ok_user, nome_ou_motivo = _validar_user(args.user_id)
        if not ok_user:
            _emitir({'status': 'FALHA_AUTORIZACAO', 'erro': nome_ou_motivo,
                     'user_id': args.user_id})
            return 1
        # Propaga executado_por p/ o hook de auditoria (se ainda nao setado
        # pelo PreToolUse hook do agente). NAO sobrescreve contexto existente.
        os.environ.setdefault('AGENT_USER_NAME', nome_ou_motivo)

        odoo = get_odoo_connection()
        if not odoo.authenticate():
            _emitir({'status': 'FALHA_ODOO', 'erro': 'autenticacao Odoo falhou'})
            return 1
        svc = get_service(odoo)

        # 2) Planejar (aplica GUARD SEFAZ)
        plano = svc.planejar(
            args.conta_origem, args.conta_destino,
            args.data_inicio, args.data_fim,
            company_id=args.company_id, journal_id=args.journal_id,
        )

        # 3) --batch: limita moves desta execucao (retomavel)
        if args.batch is not None and args.batch >= 0:
            move_ids = list(plano['grupos'].keys())[:args.batch]
            plano['grupos'] = {m: plano['grupos'][m] for m in move_ids}
            plano['n_moves'] = len(plano['grupos'])
            plano['n_linhas'] = sum(len(v) for v in plano['grupos'].values())
            plano['total_debito'] = round(
                sum(l['debit'] for v in plano['grupos'].values() for l in v), 2)

        preview = {
            'conta_origem': plano['conta_origem'],
            'conta_destino': plano['conta_destino'],
            'company_id': plano['company_id'],
            'journal_id': plano['journal_id'],
            'periodo': plano['periodo'],
            'n_moves': plano['n_moves'],
            'n_linhas': plano['n_linhas'],
            'total_debito': plano['total_debito'],
            'skip_sefaz': plano['skip_sefaz'],
        }

        # 4) Executar (dry-run ou WRITE)
        res = svc.executar(plano, confirmar=args.confirmar)
        status = res['status']

        out = {
            'modo': 'dry-run' if dry_run else 'confirmado',
            'user_id': args.user_id,
            'executado_por': nome_ou_motivo,
            'plano': preview,
            'resultado': res,
        }

        # 5) CONTADOR REAL pos-write (so quando efetivou com sucesso)
        if not dry_run and status == 'EXECUTADO':
            val = svc.validar_pos_write(
                plano, conta_destino=args.conta_destino,
                conta_origem=args.conta_origem)
            out['validacao'] = val
            integro_total = (
                val.get('integro') is True
                and val.get('processadas') == val.get('total_esperado')
                and val.get('moves_draft') == 0
            )
            if not integro_total:
                status = 'EXECUTADO_PARCIAL'
                out['resultado']['status'] = status
                out['resultado']['motivo_parcial'] = {
                    'divergentes': val.get('divergentes'),
                    'ausentes': val.get('ausentes'),
                    'pendentes': val.get('pendentes'),
                    'moves_draft': val.get('moves_draft'),
                }

        _emitir(out)
        return _exit_para_status(status, dry_run)


if __name__ == '__main__':
    sys.exit(main())
