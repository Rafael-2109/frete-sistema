"""[ARQUIVADO 2026-05-24 v6] F7.6b (D007) — Propor ajustes da pre-etapa CD (Onda 5).

⚠️ SUPERADO pela Skill 6 `planejando-pre-etapa-odoo` (modos `propor`/`listar-onda`/`aprovar-onda`).
Mantido como museum vivo para reproducibilidade historica.
Para uso operacional:
    SK=.claude/skills/planejando-pre-etapa-odoo/scripts/planejar_pre_etapa.py
    python "$SK" --modo propor --company-id 4 --usuario rafael --confirmar
    python "$SK" --modo listar-onda --company-id 4
    python "$SK" --modo aprovar-onda --company-id 4 --hash <sha> --usuario rafael --confirmar

Spec D007: docs/inventario-2026-05/00-decisoes/D007-pre-etapa-cd-fb-minimizar-nf.md
Skill 6: .claude/skills/planejando-pre-etapa-odoo/SKILL.md
Service: app/odoo/estoque/scripts/pre_etapa.py (capinado de services/)

----- Conteudo original abaixo -----

Le /tmp/plano_pre_etapa_cd.json (gerado por 03b), DELETE ajustes CD
PROPOSTO existentes (com backup automatico SQL antes), INSERT novos
ajustes com 3 novas acoes + TRANSFERIR_FB_CD residual.

Acoes geradas (D007):
- AJUSTE_CD_TRANSF_INTERNA_POS: doador (CD) → lote alvo (CD)
- AJUSTE_CD_TRANSF_INTERNA_NEG: doador (CD) → MIGRAÇÃO (CD)
- AJUSTE_CD_POSITIVO_PURO: inventory adjustment direto
- TRANSFERIR_FB_CD: residual FB→CD via NF (CFOP 5152)

Onda: 5 (executa ANTES de Onda 2).

Tambem suporta --listar-onda=5 e --aprovar-onda=5 --hash=<sha>.
"""
import argparse
import hashlib
import json
import os
import subprocess
import sys
from decimal import Decimal
from pathlib import Path

_THIS = Path(__file__).resolve()
sys.path.insert(0, str(_THIS.parents[4]))  # arquivado: parents[2] -> parents[4]

from sqlalchemy import text  # noqa: E402

from app import create_app, db  # noqa: E402
from app.odoo.models import AjusteEstoqueInventario  # noqa: E402
from app.utils.timezone import agora_utc_naive  # noqa: E402

CICLO = 'INVENTARIO_2026_05'
CD_CID = 4
INPUT_JSON = '/tmp/plano_pre_etapa_cd.json'
BACKUP_DIR = '/tmp/backup_inventario_2026_05'

# Novas acoes da Onda 5 (D007) — somente operacoes INTERNAS (sem NF).
# TRANSFERIR_FB_CD continua na Onda 2 do 04_propor_ajustes.py existente.
ACOES_ONDA5 = {
    'AJUSTE_CD_TRANSF_INTERNA_POS',
    'AJUSTE_CD_TRANSF_INTERNA_NEG',
    'AJUSTE_CD_POSITIVO_PURO',
}


def fazer_backup() -> str:
    """Cria pg_dump dos ajustes CD PROPOSTO atuais. Retorna path."""
    os.makedirs(BACKUP_DIR, exist_ok=True)
    from datetime import datetime
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    path = f'{BACKUP_DIR}/ajustes_cd_pre_etapa_04b_{ts}.sql'

    env = os.environ.copy()
    env['PGPASSWORD'] = 'frete_senha_2024'
    result = subprocess.run(
        [
            'pg_dump',
            '-h', 'localhost', '-U', 'frete_user', '-d', 'frete_sistema',
            '--data-only', '--table=ajuste_estoque_inventario',
            '--inserts', '--no-comments', '-f', path,
        ],
        env=env, capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f'pg_dump falhou: {result.stderr}')
    return path


def cmd_propor(usuario: str, dry_run: bool) -> None:
    """DELETE PROPOSTO CD + INSERT novos ajustes Onda 5."""
    if not os.path.exists(INPUT_JSON):
        raise FileNotFoundError(
            f'Input ausente: {INPUT_JSON}. Rode 03b_planejar_pre_etapa_cd.py.'
        )
    with open(INPUT_JSON) as f:
        plano = json.load(f)

    # 1. Backup
    print('1. Backup...')
    backup_path = fazer_backup()
    print(f'   Backup: {backup_path}')

    # 2. Contar PROPOSTO CD antes
    n_antes = db.session.execute(text(
        "SELECT COUNT(*) FROM ajuste_estoque_inventario "
        "WHERE ciclo=:c AND company_id=:cid AND status='PROPOSTO'"
    ), {'c': CICLO, 'cid': CD_CID}).scalar()
    print(f'\n2. CD PROPOSTO antes do DELETE: {n_antes}')

    if dry_run:
        print('\n[DRY-RUN] nao executara DELETE nem INSERT.')

    # 3. DELETE
    if not dry_run:
        print('\n3. DELETE CD PROPOSTO...')
        result = db.session.execute(text(
            "DELETE FROM ajuste_estoque_inventario "
            "WHERE ciclo=:c AND company_id=:cid AND status='PROPOSTO'"
        ), {'c': CICLO, 'cid': CD_CID})
        print(f'   Deletados: {result.rowcount} ajustes')

    # 4. Preparar inserts
    print('\n4. Inserindo novos ajustes Onda 5...')

    def tipo_de_cod(cod: str) -> int:
        return int(cod[0])

    contador = {
        'AJUSTE_CD_TRANSF_INTERNA_POS': 0,
        'AJUSTE_CD_TRANSF_INTERNA_NEG': 0,
        'AJUSTE_CD_POSITIVO_PURO': 0,
        'TRANSFERIR_FB_CD': 0,
    }

    # 4a. Transferencias internas (POS + NEG)
    for t in plano['transferencias_internas']:
        cod = t['cod_produto']
        if t['tipo'] == 'POS':
            acao = 'AJUSTE_CD_TRANSF_INTERNA_POS'
            lote_inv = t['lote_destino_nome']
            qtd_inv = t['qty']
            qtd_odoo_val = t['qty']
        else:  # NEG
            acao = 'AJUSTE_CD_TRANSF_INTERNA_NEG'
            lote_inv = ''  # lote_origem (que sai) nao esta no inv
            qtd_inv = 0
            qtd_odoo_val = t['qty']

        rec = AjusteEstoqueInventario(
            ciclo=CICLO,
            cod_produto=cod,
            tipo_produto=tipo_de_cod(cod),
            company_id=CD_CID,
            lote_inventariado=lote_inv,
            lote_odoo=t['lote_origem_nome'],
            lote_origem=t['lote_origem_nome'] or None,
            lote_destino=t['lote_destino_nome'],
            qtd_inventario=Decimal(str(qtd_inv)),
            qtd_odoo=Decimal(str(qtd_odoo_val)),
            qtd_ajuste=Decimal('0'),  # interno: nao muda saldo total
            custo_medio=Decimal(t['custo_medio']),
            acao_decidida=acao,
            criado_por=usuario,
        )
        db.session.add(rec)
        contador[acao] += 1

    # 4b. Residual FB→CD (NF)
    for r in plano['residual_fb_cd']:
        cod = r['cod_produto']
        rec = AjusteEstoqueInventario(
            ciclo=CICLO,
            cod_produto=cod,
            tipo_produto=tipo_de_cod(cod),
            company_id=CD_CID,
            lote_inventariado=r['lote_destino_cd_nome'],
            lote_odoo='',  # origem fiscal na FB (lote separado)
            lote_origem=r['lote_origem_fb_sugerido'] or 'MIGRAÇÃO',
            lote_destino=r['lote_destino_cd_nome'],
            qtd_inventario=Decimal(str(r['qty'])),
            qtd_odoo=Decimal('0'),
            qtd_ajuste=Decimal(str(r['qty'])),  # positivo: CD ganha qty
            custo_medio=Decimal(r['custo_medio']),
            acao_decidida='TRANSFERIR_FB_CD',
            criado_por=usuario,
        )
        db.session.add(rec)
        contador['TRANSFERIR_FB_CD'] += 1

    # 4c. Ajustes positivos puros
    for a in plano['ajustes_positivos_puros']:
        cod = a['cod_produto']
        rec = AjusteEstoqueInventario(
            ciclo=CICLO,
            cod_produto=cod,
            tipo_produto=tipo_de_cod(cod),
            company_id=CD_CID,
            lote_inventariado=a['lote_destino_nome'],
            lote_odoo='',
            lote_origem=None,  # sem origem
            lote_destino=a['lote_destino_nome'],
            qtd_inventario=Decimal(str(a['qty'])),
            qtd_odoo=Decimal('0'),
            qtd_ajuste=Decimal(str(a['qty'])),  # positivo puro
            custo_medio=Decimal(a['custo_medio']),
            acao_decidida='AJUSTE_CD_POSITIVO_PURO',
            criado_por=usuario,
        )
        db.session.add(rec)
        contador['AJUSTE_CD_POSITIVO_PURO'] += 1

    # 5. Commit ou rollback
    if dry_run:
        db.session.rollback()
        print('\n[DRY-RUN] rolled back')
    else:
        db.session.commit()

    # 6. Resumo
    print('\n=========== INSERIDOS ===========')
    for acao, n in contador.items():
        print(f'  {acao:<40} {n:>6}')
    total = sum(contador.values())
    print(f'  {"TOTAL":<40} {total:>6}')

    # 7. Validar pos-insert
    if not dry_run:
        n_pos = db.session.execute(text(
            "SELECT COUNT(*) FROM ajuste_estoque_inventario "
            "WHERE ciclo=:c AND company_id=:cid AND status='PROPOSTO'"
        ), {'c': CICLO, 'cid': CD_CID}).scalar()
        print(f'\n  CD PROPOSTO apos INSERT: {n_pos} (era {n_antes}, diff={n_pos - n_antes})')


def calcular_hash_onda(ajustes) -> str:
    """Hash sha256 do payload da onda 5."""
    h = hashlib.sha256()
    for a in sorted(ajustes, key=lambda x: x.id):
        h.update(
            f'{a.id}|{a.cod_produto}|{a.company_id}|{a.lote_odoo}|'
            f'{a.qtd_ajuste}|{a.acao_decidida}'.encode()
        )
    return h.hexdigest()


def cmd_listar() -> None:
    """Lista ajustes Onda 5 (acoes AJUSTE_CD_*) + hash."""
    ajustes = (
        AjusteEstoqueInventario.query
        .filter_by(ciclo=CICLO, status='PROPOSTO', company_id=CD_CID)
        .filter(AjusteEstoqueInventario.acao_decidida.in_(ACOES_ONDA5))
        .all()
    )
    print(f'Onda 5 (CD pre-etapa): {len(ajustes)} ajustes PROPOSTO')

    if not ajustes:
        print('(nada para listar)')
        return

    # Quebrar por acao
    por_acao = {}
    for a in ajustes:
        por_acao.setdefault(a.acao_decidida, []).append(a)
    print('\nQuebra por acao:')
    for acao, lista in sorted(por_acao.items()):
        valor = sum(
            abs(a.qtd_ajuste * (a.custo_medio or Decimal('0')))
            for a in lista
        )
        print(f'  {acao:<40} {len(lista):>6} ajustes  R$ {valor:>18,.2f}')

    h = calcular_hash_onda(ajustes)
    valor_total = sum(
        abs(a.qtd_ajuste * (a.custo_medio or Decimal('0')))
        for a in ajustes
    )
    print(f'\nHash da onda 5: {h}')
    print(f'Valor total fiscal (TRANSFERIR_FB_CD): R$ {valor_total:,.2f}')


def cmd_aprovar(hash_esperado: str, usuario: str, dry_run: bool) -> None:
    """Aprova ajustes Onda 5 com hash check."""
    ajustes = (
        AjusteEstoqueInventario.query
        .filter_by(ciclo=CICLO, status='PROPOSTO', company_id=CD_CID)
        .filter(AjusteEstoqueInventario.acao_decidida.in_(ACOES_ONDA5))
        .all()
    )
    if not ajustes:
        print('Nenhum ajuste PROPOSTO da Onda 5 encontrado.')
        return

    h_atual = calcular_hash_onda(ajustes)
    print(f'Hash atual:    {h_atual}')
    print(f'Hash esperado: {hash_esperado}')
    if h_atual != hash_esperado:
        print('HASH DIVERGENTE — aprovacao bloqueada. Re-rode --listar-onda=5.')
        sys.exit(2)

    print(f'{len(ajustes)} ajustes prontos para aprovar.')
    if dry_run:
        print('[DRY-RUN] aprovacao nao aplicada')
        return

    agora = agora_utc_naive()
    for a in ajustes:
        a.status = 'APROVADO'
        a.aprovado_em = agora
        a.aprovado_por = usuario
    db.session.commit()
    print(f'OK: {len(ajustes)} ajustes APROVADOS por {usuario}')


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--propor', action='store_true',
                        help='DELETE PROPOSTO CD + INSERT novos Onda 5 do plano')
    parser.add_argument('--listar-onda', type=int,
                        help='lista ajustes Onda N (so suporta 5)')
    parser.add_argument('--aprovar-onda', type=int,
                        help='aprova ajustes Onda N (so suporta 5)')
    parser.add_argument('--hash', help='hash esperado para aprovacao')
    parser.add_argument('--usuario',
                        default=os.environ.get('USER', 'desconhecido'))
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        if args.propor:
            cmd_propor(args.usuario, args.dry_run)
        elif args.listar_onda is not None:
            if args.listar_onda != 5:
                print('ERRO: este script so suporta Onda 5. Use 04_propor_ajustes.py para outras ondas.')
                sys.exit(3)
            cmd_listar()
        elif args.aprovar_onda is not None:
            if args.aprovar_onda != 5:
                print('ERRO: este script so suporta Onda 5.')
                sys.exit(3)
            if not args.hash:
                print('ERRO: --aprovar-onda exige --hash=<sha>')
                sys.exit(2)
            cmd_aprovar(args.hash, args.usuario, args.dry_run)
        else:
            parser.print_help()


if __name__ == '__main__':
    main()
