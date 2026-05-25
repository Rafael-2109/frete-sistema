"""planejar_pre_etapa.py — skill `planejando-pre-etapa-odoo`: 4 modos.

Expoe PreEtapaEstoqueService (1 produto) + helpers top-level
(planejar_pre_etapa_batch_company, propor_ajustes_pre_etapa,
listar_onda_pre_etapa, aprovar_onda_pre_etapa) via CLI unificada.

Modos:
  planejar:      READ Odoo (quants 1 company + complementar) + grava JSON+Excel
  propor:        WRITE banco local (DELETE+INSERT em ajuste_estoque_inventario)
  listar-onda:   READ banco local (lista PROPOSTO + hash sha256)
  aprovar-onda:  WRITE banco local (UPDATE status PROPOSTO -> APROVADO)

--dry-run eh DEFAULT em planejar/propor/aprovar-onda. listar-onda eh sempre READ.

Exemplos:
  python planejar_pre_etapa.py --modo planejar --company-id 4
  python planejar_pre_etapa.py --modo planejar --company-id 4 --confirmar
  python planejar_pre_etapa.py --modo propor --company-id 4 --usuario rafael --confirmar
  python planejar_pre_etapa.py --modo listar-onda --company-id 4
  python planejar_pre_etapa.py --modo aprovar-onda --company-id 4 --hash <sha> \
      --usuario rafael --confirmar

Exit: 0 efetivado · 4 dry-run OK · 1 falha · 2 uso.

Spec D007: docs/inventario-2026-05/00-decisoes/D007-pre-etapa-cd-fb-minimizar-nf.md
"""
import argparse
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

_THIS = Path(__file__).resolve()
sys.path.insert(0, str(_THIS.parents[4]))

from app.odoo.estoque._cli_utils import (  # noqa: E402
    adicionar_args_padrao, setup_cli_completo,
)
from app.odoo.estoque.scripts.pre_etapa import (  # noqa: E402
    COMPANY_LOCATIONS_PRE_ETAPA,
    ONDA_NUM_POR_CID,
    aprovar_onda_pre_etapa,
    gerar_excel_plano_pre_etapa,
    listar_onda_pre_etapa,
    planejar_pre_etapa_batch_company,
    propor_ajustes_pre_etapa,
)
from app.odoo.utils.connection import get_odoo_connection  # noqa: E402
from app.utils.timezone import agora_brasil_naive  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)-7s %(name)s | %(message)s',
)
logger = logging.getLogger('planejar_pre_etapa')


_CICLO_DEFAULT = 'INVENTARIO_2026_05'
_INPUT_ESTOQUE_DEFAULT = '/tmp/estoque_odoo_2026_05.json'
_INPUT_INV_DEFAULT = '/tmp/inventario_fisico_2026_05.json'
_OUTPUT_JSON_TPL = '/tmp/plano_pre_etapa_{cid}.json'
_OUTPUT_XLSX_DIR_DEFAULT = 'docs/inventario-2026-05/07-relatorios'
_OUTPUT_XLSX_NAME_TPL = 'plano-pre-etapa-{cid}.xlsx'


# ============================================================
# MODO planejar
# ============================================================

def _carregar_inputs_planejar(
    input_estoque: str,
    input_inv: str,
    company_id: int,
    complementar: str,
) -> Dict[str, Any]:
    """Le JSONs estoque + inv. Retorna {quants_company_raw, quants_complementar_raw,
    linhas_inv_raw, ok, erro}.
    """
    if not os.path.exists(input_estoque):
        return {'ok': False, 'erro': f'FALHA_INPUT_AUSENTE: {input_estoque}'}
    if not os.path.exists(input_inv):
        return {'ok': False, 'erro': f'FALHA_INPUT_AUSENTE: {input_inv}'}

    with open(input_estoque) as f:
        estoque = json.load(f)
    with open(input_inv) as f:
        inv = json.load(f)

    cid_str = str(company_id)
    quants_company_raw = estoque.get('companies', {}).get(
        cid_str, {},
    ).get('quants', [])
    linhas_inv_raw = inv.get('companies', {}).get(cid_str, {}).get('linhas', [])

    quants_complementar_raw: Optional[List[Dict[str, Any]]] = None
    if company_id == 4 and complementar == 'fb':
        # CD pode puxar de FB (Onda 5, ANTES de FB passar pela pre-etapa)
        quants_complementar_raw = estoque.get('companies', {}).get(
            '1', {},
        ).get('quants', [])
    # FB (cid=1) ou complementar=none: nao tem complementar

    return {
        'ok': True,
        'quants_company_raw': quants_company_raw,
        'quants_complementar_raw': quants_complementar_raw,
        'linhas_inv_raw': linhas_inv_raw,
    }


def modo_planejar(args: argparse.Namespace) -> Dict[str, Any]:
    """Modo planejar: READ Odoo + grava JSON+Excel."""
    t0 = time.time()
    out: Dict[str, Any] = {
        'modo': 'planejar',
        'ts_inicio': agora_brasil_naive().isoformat(timespec='seconds'),
        'dry_run': args.dry_run,
        'company_id': args.company_id,
        'ciclo': args.ciclo,
    }

    inputs = _carregar_inputs_planejar(
        args.input_estoque, args.input_inv, args.company_id, args.complementar,
    )
    if not inputs['ok']:
        out['status'] = 'FALHA_INPUT_AUSENTE'
        out['erro'] = inputs['erro']
        out['tempo_ms'] = int((time.time() - t0) * 1000)
        return out

    odoo = get_odoo_connection()
    location_id = COMPANY_LOCATIONS_PRE_ETAPA[args.company_id]
    cods_filter = (
        [s.strip() for s in args.cods.split(',') if s.strip()]
        if args.cods else None
    )

    try:
        plano_total = planejar_pre_etapa_batch_company(
            odoo=odoo,
            company_id=args.company_id,
            location_id=location_id,
            quants_company_raw=inputs['quants_company_raw'],
            linhas_inv_raw=inputs['linhas_inv_raw'],
            quants_complementar_raw=inputs['quants_complementar_raw'],
            cods_filter=cods_filter,
        )
    except Exception as exc:
        out['status'] = 'FALHA_ODOO'
        out['erro'] = str(exc)
        out['tempo_ms'] = int((time.time() - t0) * 1000)
        return out

    # Sumarios (sem dump completo no JSON do exit — plano completo vai pro --output-json)
    cod_to_name = plano_total.pop('cod_to_name', {})
    n_pos = sum(
        1 for t in plano_total['transferencias_internas'] if t['tipo'] == 'POS'
    )
    n_neg = sum(
        1 for t in plano_total['transferencias_internas'] if t['tipo'] == 'NEG'
    )
    out.update({
        'produtos_processados': plano_total['produtos_processados'],
        'produtos_sem_mudanca': plano_total['produtos_sem_mudanca'],
        'outliers_skipados': plano_total.get('outliers_skipados', []),
        'total_pos': n_pos,
        'total_neg': n_neg,
        'total_residual_fb_cd': len(plano_total['residual_fb_cd']),
        'total_positivos_puros': len(plano_total['ajustes_positivos_puros']),
        'total_warnings': len(plano_total['warnings']),
    })

    # Grava arquivos se --confirmar
    output_json_path = args.output_json or _OUTPUT_JSON_TPL.format(cid=args.company_id)
    xlsx_dir = args.output_xlsx_dir or _OUTPUT_XLSX_DIR_DEFAULT
    xlsx_name = _OUTPUT_XLSX_NAME_TPL.format(cid=args.company_id)
    output_xlsx_path = args.output_xlsx or os.path.join(xlsx_dir, xlsx_name)

    if args.dry_run:
        out['status'] = 'DRY_RUN_OK_PLANEJADO'
        out['output_json_path'] = None
        out['output_xlsx_path'] = None
    else:
        # Inclui metadados no JSON
        plano_total_full = {
            **plano_total,
            'cod_to_name': cod_to_name,
            'timestamp': out['ts_inicio'],
            'ciclo': args.ciclo,
        }
        with open(output_json_path, 'w') as f:
            json.dump(plano_total_full, f, default=str, indent=2)
        os.makedirs(os.path.dirname(output_xlsx_path) or '.', exist_ok=True)
        gerar_excel_plano_pre_etapa(plano_total, output_xlsx_path, cod_to_name)
        out['status'] = 'PLANEJADO'
        out['output_json_path'] = output_json_path
        out['output_xlsx_path'] = output_xlsx_path

    out['tempo_ms'] = int((time.time() - t0) * 1000)
    return out


# ============================================================
# MODO propor
# ============================================================

def modo_propor(args: argparse.Namespace) -> Dict[str, Any]:
    """Modo propor: WRITE banco local (DELETE+INSERT em ajuste_estoque_inventario)."""
    t0 = time.time()
    out: Dict[str, Any] = {
        'modo': 'propor',
        'ts_inicio': agora_brasil_naive().isoformat(timespec='seconds'),
        'dry_run': args.dry_run,
        'company_id': args.company_id,
        'ciclo': args.ciclo,
    }

    plano_json_path = args.plano_json or _OUTPUT_JSON_TPL.format(cid=args.company_id)
    if not os.path.exists(plano_json_path):
        out['status'] = 'FALHA_PLANO_AUSENTE'
        out['erro'] = (
            f'Plano nao encontrado: {plano_json_path}. Rode --modo planejar '
            f'--company-id {args.company_id} --confirmar antes.'
        )
        out['tempo_ms'] = int((time.time() - t0) * 1000)
        return out

    with open(plano_json_path) as f:
        plano_total = json.load(f)

    # Backup opcional
    backup_path: Optional[str] = None
    if args.backup_pg_dump and not args.dry_run:
        try:
            from app.odoo.estoque.scripts.pre_etapa import (  # lazy
                _fazer_backup_pg_dump,
            )
            backup_dir = args.backup_pg_dump_dir or '/tmp/backup_inventario_2026_05'
            backup_path = _fazer_backup_pg_dump(
                backup_dir=backup_dir,
                db_password=args.backup_pg_dump_password,
            )
        except Exception as exc:
            out['status'] = 'FALHA_BACKUP'
            out['erro'] = str(exc)
            out['tempo_ms'] = int((time.time() - t0) * 1000)
            return out

    try:
        r = propor_ajustes_pre_etapa(
            plano_total=plano_total,
            ciclo=args.ciclo,
            company_id=args.company_id,
            usuario=args.usuario,
            dry_run=args.dry_run,
        )
    except Exception as exc:
        out['status'] = 'FALHA_BANCO'
        out['erro'] = str(exc)
        out['tempo_ms'] = int((time.time() - t0) * 1000)
        return out

    out.update(r)
    out['backup_path'] = backup_path
    out['status'] = 'DRY_RUN_OK_PROPOSTO' if args.dry_run else 'PROPOSTO'
    out['tempo_ms'] = int((time.time() - t0) * 1000)
    return out


# ============================================================
# MODO listar-onda
# ============================================================

def modo_listar_onda(args: argparse.Namespace) -> Dict[str, Any]:
    """Modo listar-onda: READ banco local + hash sha256."""
    t0 = time.time()
    out: Dict[str, Any] = {
        'modo': 'listar-onda',
        'ts_inicio': agora_brasil_naive().isoformat(timespec='seconds'),
        'company_id': args.company_id,
        'ciclo': args.ciclo,
    }

    try:
        r = listar_onda_pre_etapa(
            ciclo=args.ciclo,
            company_id=args.company_id,
            onda_num=args.onda_num,
        )
    except Exception as exc:
        out['status'] = 'FALHA_BANCO'
        out['erro'] = str(exc)
        out['tempo_ms'] = int((time.time() - t0) * 1000)
        return out

    out.update(r)
    out['status'] = 'LISTADO' if r['total'] > 0 else 'LISTADO_VAZIO'
    out['tempo_ms'] = int((time.time() - t0) * 1000)
    return out


# ============================================================
# MODO aprovar-onda
# ============================================================

def modo_aprovar_onda(args: argparse.Namespace) -> Dict[str, Any]:
    """Modo aprovar-onda: WRITE banco local com hash check."""
    t0 = time.time()
    out: Dict[str, Any] = {
        'modo': 'aprovar-onda',
        'ts_inicio': agora_brasil_naive().isoformat(timespec='seconds'),
        'dry_run': args.dry_run,
        'company_id': args.company_id,
        'ciclo': args.ciclo,
    }

    if not args.hash:
        out['status'] = 'FALHA_USO'
        out['erro'] = 'Modo aprovar-onda exige --hash <sha256> (de listar-onda).'
        out['tempo_ms'] = int((time.time() - t0) * 1000)
        return out

    try:
        r = aprovar_onda_pre_etapa(
            ciclo=args.ciclo,
            company_id=args.company_id,
            hash_esperado=args.hash,
            usuario=args.usuario,
            onda_num=args.onda_num,
            dry_run=args.dry_run,
        )
    except Exception as exc:
        out['status'] = 'FALHA_BANCO'
        out['erro'] = str(exc)
        out['tempo_ms'] = int((time.time() - t0) * 1000)
        return out

    out.update(r)
    if not r['sucesso']:
        out['status'] = f'FALHA_{r["erro"]}'
    else:
        out['status'] = 'DRY_RUN_OK_APROVADO' if args.dry_run else 'APROVADO'
    out['tempo_ms'] = int((time.time() - t0) * 1000)
    return out


# ============================================================
# Output e dispatch
# ============================================================

_FALHAS_STATUS = {
    'FALHA_INPUT_AUSENTE', 'FALHA_PLANO_AUSENTE', 'FALHA_BANCO',
    'FALHA_BACKUP', 'FALHA_ODOO', 'FALHA_USO',
    'FALHA_HASH_DIVERGENTE', 'FALHA_NENHUM_PROPOSTO',
}
_REAL_OKS = {'PLANEJADO', 'PROPOSTO', 'LISTADO', 'LISTADO_VAZIO', 'APROVADO'}
_DRY_OKS = {
    'DRY_RUN_OK_PLANEJADO', 'DRY_RUN_OK_PROPOSTO', 'DRY_RUN_OK_APROVADO',
}


def _salvar_log(out: Dict[str, Any], dry_run: bool, modo: str) -> Optional[str]:
    """Salva log JSON em scripts/inventario_2026_05/auditoria/."""
    try:
        base = (
            _THIS.parents[4]
            / 'scripts' / 'inventario_2026_05' / 'auditoria'
        )
        base.mkdir(parents=True, exist_ok=True)
        ts = agora_brasil_naive().strftime('%Y%m%d_%H%M%S')
        sufixo = 'dryrun' if dry_run else 'real'
        nome = f'log_skill6_pre_etapa_{modo.replace("-", "_")}_{sufixo}_{ts}.json'
        path = base / nome
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(out, f, ensure_ascii=False, indent=2, default=str)
        logger.info(f'Log salvo: {path}')
        return str(path)
    except Exception as exc:
        logger.warning(f'Falha ao salvar log: {exc}')
        return None


def _emitir(out: Dict[str, Any], dry_run: bool) -> int:
    """Imprime JSON e retorna exit code conforme status."""
    print(json.dumps(out, ensure_ascii=False, indent=2, default=str))

    status = out.get('status', '')
    if status in _FALHAS_STATUS:
        return 1
    # CR-F3: READ-only (listar-onda) sempre exit 0 independente de dry_run —
    # contrato da SKILL.md diz "exit: 0 sempre (READ-only)". main() forca
    # dry_run=False para listar-onda mas se _emitir for chamado programaticamente
    # com dry_run=True, LISTADO/LISTADO_VAZIO ainda exit 0.
    if status in {'LISTADO', 'LISTADO_VAZIO'}:
        return 0
    if dry_run:
        return 4 if status in _DRY_OKS else 1
    if status in _REAL_OKS:
        return 0
    return 1


def main() -> int:
    ap = argparse.ArgumentParser(
        description='planejando-pre-etapa-odoo: planejar/propor/listar/aprovar pre-etapa D007',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    ap.add_argument(
        '--modo', required=True,
        choices=['planejar', 'propor', 'listar-onda', 'aprovar-onda'],
        help='Modo de operacao (4 modos disponiveis).',
    )
    ap.add_argument(
        '--company-id', type=int, required=True, choices=[4, 1],
        help='OBRIGATORIO. 4=CD (Onda 5), 1=FB (Onda 6 futura).',
    )
    ap.add_argument('--ciclo', default=_CICLO_DEFAULT,
                    help=f'Identificador do ciclo. Default: {_CICLO_DEFAULT}')
    ap.add_argument('--usuario', default=os.environ.get('USER', 'desconhecido'),
                    help='Usuario para auditoria (criado_por/aprovado_por).')

    # Modo planejar
    ap.add_argument('--input-estoque', default=_INPUT_ESTOQUE_DEFAULT,
                    help='JSON do script 01_extrair_estoque_odoo.')
    ap.add_argument('--input-inv', default=_INPUT_INV_DEFAULT,
                    help='JSON do script 02_carregar_inventario_xlsx.')
    ap.add_argument('--output-json', default='',
                    help='Path JSON do plano (default /tmp/plano_pre_etapa_<cid>.json).')
    ap.add_argument('--output-xlsx', default='',
                    help='Path Excel do plano (default docs/.../plano-pre-etapa-<cid>.xlsx).')
    ap.add_argument('--output-xlsx-dir', default='',
                    help='Dir do Excel (default docs/inventario-2026-05/07-relatorios).')
    ap.add_argument('--cods', default='',
                    help='Subset de default_codes (csv); default = todos validos.')
    ap.add_argument('--complementar', choices=['fb', 'none'], default='fb',
                    help='CD (cid=4) pode puxar de FB (default). FB (cid=1) ou none = skip.')

    # Modo propor
    ap.add_argument('--plano-json', default='',
                    help='Path JSON do plano (default /tmp/plano_pre_etapa_<cid>.json).')
    ap.add_argument('--backup-pg-dump', action='store_true', default=False,
                    help='Faz pg_dump --data-only ANTES de DELETE+INSERT (cinto+suspensorio).')
    ap.add_argument('--backup-pg-dump-dir', default='',
                    help='Dir do backup (default /tmp/backup_inventario_2026_05).')
    ap.add_argument('--backup-pg-dump-password', default='',
                    help='PGPASSWORD para pg_dump. Default: env PGPASSWORD.')

    # Modo listar-onda / aprovar-onda
    ap.add_argument('--onda-num', type=int, default=0,
                    help='Onda 5 (CD) ou 6 (FB). Default = inferido de company-id.')
    ap.add_argument('--hash', default='',
                    help='Hash sha256 esperado (obrigatorio para aprovar-onda).')

    # Execucao
    ap.add_argument('--dry-run', action='store_true', default=True,
                    help='Default seguro (calcula mas NAO grava/escreve).')
    ap.add_argument('--confirmar', action='store_true', default=False,
                    help='Executa real (grava JSON/XLSX em planejar; DELETE+INSERT em propor; UPDATE em aprovar-onda).')
    adicionar_args_padrao(ap)  # --quiet + --forcar-concorrencia (v7)
    args = ap.parse_args()

    if args.confirmar:
        args.dry_run = False

    # listar-onda eh sempre READ — ignora dry_run/confirmar
    if args.modo == 'listar-onda':
        args.dry_run = False

    # Normalizar onda_num (0 = None -> inferir)
    if args.onda_num == 0:
        args.onda_num = ONDA_NUM_POR_CID.get(args.company_id)

    # Validar modo aprovar-onda exige --hash
    if args.modo == 'aprovar-onda' and not args.hash:
        logger.error('Modo aprovar-onda exige --hash <sha256> (obtido via listar-onda).')
        return 2

    app = setup_cli_completo(__file__, args.quiet, args.forcar_concorrencia)
    with app.app_context():
        if args.modo == 'planejar':
            out = modo_planejar(args)
        elif args.modo == 'propor':
            out = modo_propor(args)
        elif args.modo == 'listar-onda':
            out = modo_listar_onda(args)
        elif args.modo == 'aprovar-onda':
            out = modo_aprovar_onda(args)
        else:
            ap.error(f'Modo invalido: {args.modo}')
            return 2  # unreachable

        # Sempre salvar log (mesmo dry-run) — auditoria
        log_path = _salvar_log(out, args.dry_run, args.modo)
        if log_path:
            out['log_path'] = log_path

        return _emitir(out, args.dry_run)


if __name__ == '__main__':
    sys.exit(main())
