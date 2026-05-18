"""F7.4 — Persiste propostas de ajuste em ajuste_estoque_inventario (status=PROPOSTO).

Tambem suporta `--listar-onda=N` para inspecionar e
`--aprovar-onda=N --hash=<sha>` para mover PROPOSTO → APROVADO
travando exatamente o conjunto inspecionado.

Mapeia (tipo_produto, company_id, sinal) → acao_decidida via
resolver_operacao_por_tipo_produto() do constants/operacoes_fiscais.py.

Ondas:
- 1: LF↔FB (industrializacao, perda, dev-industrializacao)
- 2: CD↔FB (transf-filial)
- 3: indisponibilizar (gerado em script 05_canary_estoque_staging, nao aqui)
- 4: renomear lote (tipo_divergencia=APENAS_LOTE)

Uso:
    # Propor (carrega /tmp/diff_inventario_2026_05.json)
    python scripts/inventario_2026_05/04_propor_ajustes.py --propor [--dry-run]

    # Listar onda + hash (NAO aprova ainda)
    python scripts/inventario_2026_05/04_propor_ajustes.py --listar-onda=1

    # Aprovar onda travando o conjunto via hash
    python scripts/inventario_2026_05/04_propor_ajustes.py \\
        --aprovar-onda=1 --hash=<sha> --usuario=rafael [--dry-run]

Spec: docs/superpowers/plans/2026-05-17-ajuste-inventario-nacom-lf.md Task 7.4
"""
import argparse
import hashlib
import json
import os
import sys
from decimal import Decimal
from pathlib import Path

# sys.path para `from app import ...`
_THIS = Path(__file__).resolve()
sys.path.insert(0, str(_THIS.parents[2]))

from app import create_app, db  # noqa: E402
from app.odoo.constants.operacoes_fiscais import (  # noqa: E402
    resolver_operacao_por_tipo_produto,
)
from app.odoo.models import AjusteEstoqueInventario  # noqa: E402
from app.utils.timezone import agora_utc_naive  # noqa: E402

CICLO = 'INVENTARIO_2026_05'
INPUT_JSON = '/tmp/diff_inventario_2026_05.json'


def buscar_arquivados() -> set:
    """Retorna set de default_code de produtos com active=False no Odoo.

    Decisao usuario 2026-05-17: produtos arquivados com saldo Odoo viram
    INDISPONIBILIZAR_LOTE/LOCAL em vez de transferir/perda/dev. Saldo
    fantasma (produtos descontinuados que nao devem mais movimentar
    fiscalmente).
    """
    from app.odoo.utils.connection import get_odoo_connection
    odoo = get_odoo_connection()
    arq = odoo.search_read(
        'product.product',
        [['active', '=', False]],
        ['default_code'],
        limit=5000,
    )
    return {
        (p.get('default_code') or '').strip()
        for p in arq if p.get('default_code')
    }


def _indisponibilizar(d: dict) -> str:
    """Opção 1 (lote) se houver lote_odoo, opção 2 (local) senão.

    Conforme prompt_inventario.md ordem=3: "indisponibilização por lote"
    é tentada primeiro; se não funcionar, "por local". Aqui marcamos
    INDISPONIBILIZAR_LOTE quando ha lote identificavel no Odoo —
    canary efetivo de viabilidade fica na F5/F7.5-7.10.
    """
    return (
        'INDISPONIBILIZAR_LOTE'
        if (d.get('lote_odoo') or '').strip()
        else 'INDISPONIBILIZAR_LOCAL'
    )


def calcular_acao_decidida(d: dict, arquivados: set | None = None) -> str:
    """Mapeia diff → acao_decidida do AjusteEstoqueInventario.

    Implementa ORDENS 1/2/3 do prompt_inventario.md (2026-05-17):

    ORDEM 1 (LF↔FB, NF):
        - LF tipo[1,2,3] sinal>0 → INDUSTRIALIZACAO_FB_LF (CFOP 5901)
        - LF tipo[1,2,3] sinal<0 → PERDA_LF_FB (CFOP 5903)
        - LF tipo[4]            → DEV_LF_FB / DEV_FB_LF (CFOP 5949)

    ORDEM 2 (FB↔CD, NF transferência — APENAS combinações válidas):
        - FB tipo[4]            → TRANSFERIR_FB_CD/CD_FB (CFOP 5152/5151)
        - CD tipo[1,2,3]        → TRANSFERIR_CD_FB/FB_CD

    ORDEM 3 (segregação fantasma via indisponibilização):
        - FB tipo[1,2,3]        → INDISPONIBILIZAR_LOTE/LOCAL
        - CD tipo[4]            → INDISPONIBILIZAR_LOTE/LOCAL
        - Produtos arquivados   → INDISPONIBILIZAR_LOTE/LOCAL

    Args:
        d: diff dict
        arquivados: set de cods com active=False no Odoo (override).
    """
    if d['tipo_divergencia'] in ('APENAS_LOTE', 'RENOMEAR_LOTE_PARCIAL'):
        return 'RENOMEAR_LOTE'
    qtd_ajuste = Decimal(d['qtd_ajuste'])
    if qtd_ajuste == 0:
        return 'SEM_ACAO'

    cid = d['company_id']
    tipo = d['tipo_produto']

    # Override: arquivados sempre indisponibilizam (saldo fantasma)
    if arquivados is not None and d['cod_produto'] in arquivados:
        return _indisponibilizar(d)

    # ORDEM 3: tipo errado na empresa errada → indisponibilizar
    # FB nao deveria ter tipo[1,2,3]; CD nao deveria ter tipo[4].
    if cid == 1 and tipo in (1, 2, 3):
        return _indisponibilizar(d)
    if cid == 4 and tipo == 4:
        return _indisponibilizar(d)

    # ORDEM 1 (LF, company_id=5)
    if cid == 5:
        if tipo == 4:
            # dev-industrializacao bi-direcional FB↔LF
            return 'DEV_LF_FB' if qtd_ajuste < 0 else 'DEV_FB_LF'
        if tipo in (1, 2, 3):
            return 'INDUSTRIALIZACAO_FB_LF' if qtd_ajuste > 0 else 'PERDA_LF_FB'
        # tipo invalido em LF (5/6) → indisponibilizar (decisao 2026-05-17)
        return _indisponibilizar(d)

    # ORDEM 2: tipo certo na empresa certa → transferência FB↔CD
    sinal = 1 if qtd_ajuste > 0 else -1
    if cid == 1 and tipo == 4:
        # FB tipo[4]: excesso (sinal<0) → FB→CD; falta (sinal>0) → CD→FB
        return 'TRANSFERIR_FB_CD' if sinal < 0 else 'TRANSFERIR_CD_FB'
    if cid == 4 and tipo in (1, 2, 3):
        # CD tipo[1,2,3]: excesso → CD→FB; falta → FB→CD
        return 'TRANSFERIR_CD_FB' if sinal < 0 else 'TRANSFERIR_FB_CD'

    # Fallback usa matriz original (caso nao mapeado acima)
    tipo_op = resolver_operacao_por_tipo_produto(
        tipo=tipo, company_id=cid, sinal=sinal,
    )
    if tipo_op == 'transf-filial':
        return 'TRANSFERIR_CD_FB' if cid == 4 else 'TRANSFERIR_FB_CD'
    raise ValueError(
        f'combinacao nao mapeada: cid={cid} tipo={tipo} sinal={sinal} '
        f'tipo_op={tipo_op}'
    )


def determinar_onda(acao: str) -> int:
    """Onda alvo para cada acao_decidida (0 = sem ondas)."""
    return {
        'INDUSTRIALIZACAO_FB_LF': 1,
        'PERDA_LF_FB': 1,
        'DEV_FB_LF': 1,
        'DEV_LF_FB': 1,
        'DEV_CD_LF': 1,
        'DEV_LF_CD': 1,
        'TRANSFERIR_CD_FB': 2,
        'TRANSFERIR_FB_CD': 2,
        'INDISPONIBILIZAR_LOTE': 3,
        'INDISPONIBILIZAR_LOCAL': 3,
        'RENOMEAR_LOTE': 4,
        'SEM_ACAO': 0,
    }.get(acao, 0)


def calcular_hash_onda(ajustes: list) -> str:
    """Hash sha256 do payload da onda. Usado em --aprovar-onda para
    travar exatamente o conjunto inspecionado (defesa contra novos
    diffs entrarem entre listar e aprovar)."""
    h = hashlib.sha256()
    for a in sorted(ajustes, key=lambda x: x.id):
        h.update(
            f'{a.id}|{a.cod_produto}|{a.company_id}|{a.lote_odoo}|'
            f'{a.qtd_ajuste}|{a.acao_decidida}'.encode()
        )
    return h.hexdigest()


def cmd_propor(usuario: str, dry_run: bool) -> None:
    if not os.path.exists(INPUT_JSON):
        raise FileNotFoundError(
            f'Input ausente: {INPUT_JSON}. Rode script 03 antes.'
        )
    with open(INPUT_JSON) as f:
        data = json.load(f)
    diffs = data['diffs']
    print(f'Carregados {len(diffs)} diffs do confronto')

    # Buscar arquivados (active=False) uma vez — diffs apontando para
    # arquivados viram INDISPONIBILIZAR_* (decisao usuario 2026-05-17).
    arquivados = buscar_arquivados()
    print(f'Produtos arquivados (active=False) no Odoo: {len(arquivados)}')

    contador = {'inserido': 0, 'ja_existe': 0, 'sem_acao': 0}
    for d in diffs:
        acao = calcular_acao_decidida(d, arquivados=arquivados)
        if acao == 'SEM_ACAO':
            contador['sem_acao'] += 1
            continue

        # Chave dedup inclui lote_inventariado (fix 2026-05-17):
        # INVENTARIO_SEM_ODOO gera 1 diff por lote do inv com lote_odoo=''
        # — sem lote_inventariado na chave, multiplos lotes distintos
        # colapsam em um unico registro (bug critico: ~2400 ajustes
        # perdidos em 4320147 etc).
        existe = AjusteEstoqueInventario.query.filter_by(
            ciclo=CICLO,
            cod_produto=d['cod_produto'],
            company_id=d['company_id'],
            lote_odoo=d['lote_odoo'],
            lote_inventariado=d['lote_inventariado'],
        ).first()
        if existe:
            contador['ja_existe'] += 1
            continue

        # D004/D005: lote_origem/destino — preferir do diff; senao
        # default por acao (PERDA/TRANSF para FB usa MIGRACAO).
        lote_origem = d.get('lote_origem') or d.get('lote_odoo') or None
        lote_destino = d.get('lote_destino')
        if not lote_destino:
            # Defaults conforme acao
            if acao in ('PERDA_LF_FB', 'TRANSFERIR_CD_FB', 'TRANSFERIR_FB_CD'):
                # Sai/entra na FB? Para PERDA_LF_FB destino=FB.
                # Para TRANSFERIR_FB_CD destino=CD (sem MIGRACAO).
                # Para TRANSFERIR_CD_FB destino=FB (MIGRACAO).
                if acao in ('PERDA_LF_FB', 'TRANSFERIR_CD_FB'):
                    lote_destino = 'MIGRACAO'
                else:
                    lote_destino = (
                        d.get('lote_inventariado') or d.get('lote_odoo') or None
                    )
            elif acao == 'INDUSTRIALIZACAO_FB_LF':
                lote_destino = (
                    d.get('lote_inventariado') or d.get('lote_odoo') or None
                )
            elif acao in ('DEV_FB_LF', 'DEV_LF_FB'):
                lote_destino = (
                    d.get('lote_inventariado') or d.get('lote_odoo') or None
                )
            elif acao == 'RENOMEAR_LOTE':
                lote_destino = d.get('lote_inventariado') or None

        rec = AjusteEstoqueInventario(
            ciclo=CICLO,
            cod_produto=d['cod_produto'],
            tipo_produto=d['tipo_produto'],
            company_id=d['company_id'],
            lote_inventariado=d['lote_inventariado'],
            lote_odoo=d['lote_odoo'],
            lote_origem=lote_origem,
            lote_destino=lote_destino,
            qtd_inventario=Decimal(d['qtd_inventario']),
            qtd_odoo=Decimal(d['qtd_odoo']),
            qtd_ajuste=Decimal(d['qtd_ajuste']),
            custo_medio=Decimal(d.get('custo_medio') or 0),
            acao_decidida=acao,
            criado_por=usuario,
        )
        db.session.add(rec)
        contador['inserido'] += 1

    if dry_run:
        db.session.rollback()
        print(
            f'[DRY RUN] iria inserir {contador["inserido"]}, '
            f'ja existem {contador["ja_existe"]}, '
            f'sem_acao {contador["sem_acao"]}'
        )
    else:
        db.session.commit()
        print(
            f'OK: inseridos {contador["inserido"]} ajustes '
            f'(ciclo={CICLO}) + {contador["ja_existe"]} ja existentes '
            f'+ {contador["sem_acao"]} sem_acao'
        )


def cmd_listar(onda: int) -> None:
    ajustes = AjusteEstoqueInventario.query.filter_by(
        ciclo=CICLO, status='PROPOSTO',
    ).all()
    ajustes_onda = [
        a for a in ajustes if determinar_onda(a.acao_decidida) == onda
    ]
    print(f'Onda {onda}: {len(ajustes_onda)} ajustes PROPOSTO')

    if not ajustes_onda:
        print('(nada para aprovar nesta onda)')
        return

    h = calcular_hash_onda(ajustes_onda)
    valor_total = sum(
        abs(a.qtd_ajuste * (a.custo_medio or Decimal('0')))
        for a in ajustes_onda
    )
    print(f'Hash da onda (para aprovacao): {h}')
    print(f'Valor total: R$ {valor_total}')
    print()
    print(
        f'{"id":>6}  {"cod_produto":<12}  {"company":>8}  '
        f'{"acao":<25}  {"qtd":>12}  {"custo_unit":>10}'
    )
    for a in ajustes_onda:
        print(
            f'{a.id:>6}  {a.cod_produto:<12}  {a.company_id:>8}  '
            f'{a.acao_decidida:<25}  {a.qtd_ajuste:>12}  '
            f'{(a.custo_medio or 0):>10}'
        )


def cmd_aprovar(
    onda: int, hash_esperado: str, usuario: str, dry_run: bool
) -> None:
    ajustes = AjusteEstoqueInventario.query.filter_by(
        ciclo=CICLO, status='PROPOSTO',
    ).all()
    ajustes_onda = [
        a for a in ajustes if determinar_onda(a.acao_decidida) == onda
    ]
    print(f'Onda {onda}: {len(ajustes_onda)} ajustes PROPOSTO')
    if not ajustes_onda:
        print('(nada para aprovar)')
        return

    hash_atual = calcular_hash_onda(ajustes_onda)
    print(f'Hash atual:    {hash_atual}')
    print(f'Hash esperado: {hash_esperado}')
    if hash_atual != hash_esperado:
        print(
            'HASH DIVERGENTE — aprovacao bloqueada. Re-rode '
            f'--listar-onda={onda} e confirme antes de aprovar.'
        )
        sys.exit(2)

    valor_total = sum(
        abs(a.qtd_ajuste * (a.custo_medio or Decimal('0')))
        for a in ajustes_onda
    )
    print(f'Valor total da onda: R$ {valor_total}')

    if dry_run:
        print('[DRY RUN] aprovacao nao aplicada')
        return

    agora = agora_utc_naive()
    for a in ajustes_onda:
        a.status = 'APROVADO'
        a.aprovado_em = agora
        a.aprovado_por = usuario
    db.session.commit()
    print(f'OK: {len(ajustes_onda)} ajustes APROVADOS por {usuario}')


def cmd_listar_ids(ids: list) -> None:
    """Lista ajustes por IDs especificos (PROPOSTO) + hash do conjunto."""
    ajustes = (
        AjusteEstoqueInventario.query
        .filter(AjusteEstoqueInventario.id.in_(ids))
        .filter_by(status='PROPOSTO')
        .all()
    )
    print(f'IDs solicitados: {sorted(ids)}')
    print(f'Ajustes PROPOSTO encontrados: {len(ajustes)}')
    if not ajustes:
        print('(nenhum ajuste PROPOSTO com esses IDs)')
        return
    encontrados = {a.id for a in ajustes}
    faltam = set(ids) - encontrados
    if faltam:
        print(f'  IDs nao encontrados (ou ja aprovados/executados): {sorted(faltam)}')

    h = calcular_hash_onda(ajustes)
    valor_total = sum(
        abs(a.qtd_ajuste * (a.custo_medio or Decimal('0')))
        for a in ajustes
    )
    print(f'Hash dos ajustes (para aprovacao): {h}')
    print(f'Valor total: R$ {valor_total}')
    print()
    print(
        f'{"id":>6}  {"cod_produto":<12}  {"company":>8}  '
        f'{"acao":<25}  {"lote_origem":<12}  {"lote_destino":<12}  '
        f'{"qty_inv":>10}  {"qty_aj":>12}'
    )
    for a in sorted(ajustes, key=lambda x: x.id):
        print(
            f'{a.id:>6}  {a.cod_produto:<12}  {a.company_id:>8}  '
            f'{a.acao_decidida:<25}  {(a.lote_origem or ""):<12}  '
            f'{(a.lote_destino or ""):<12}  {a.qtd_inventario:>10}  '
            f'{a.qtd_ajuste:>12}'
        )


def cmd_aprovar_ids(
    ids: list, hash_esperado: str, usuario: str, dry_run: bool,
    company_id: int,
) -> None:
    """Aprova subset de ajustes por IDs com hash check + company_id filtro.

    Permite aprovar apenas o caso piloto (6 ajustes) ou qualquer subset
    sem aprovar a onda inteira.

    Regra: scripts sempre tem --company-id, conforme decisao usuario
    2026-05-18. Aqui usado como camada extra de seguranca para garantir
    que IDs realmente pertencem a empresa esperada.
    """
    ajustes = (
        AjusteEstoqueInventario.query
        .filter(AjusteEstoqueInventario.id.in_(ids))
        .filter_by(status='PROPOSTO')
        .all()
    )
    if not ajustes:
        print('(nenhum ajuste PROPOSTO encontrado)')
        return
    # Validar company_id: todos os ajustes devem ser da company esperada
    companies_distintas = {a.company_id for a in ajustes}
    if companies_distintas != {company_id}:
        print(
            f'ERRO: IDs solicitados pertencem a companies '
            f'{sorted(companies_distintas)} mas --company-id={company_id} '
            f'foi passado. Aprovacao bloqueada.'
        )
        sys.exit(7)

    hash_atual = calcular_hash_onda(ajustes)
    print(f'IDs encontrados (PROPOSTO): {len(ajustes)}')
    print(f'Hash atual:    {hash_atual}')
    print(f'Hash esperado: {hash_esperado}')
    if hash_atual != hash_esperado:
        print(
            'HASH DIVERGENTE — aprovacao bloqueada. Re-rode '
            '--listar-ids para capturar hash atual.'
        )
        sys.exit(2)

    valor_total = sum(
        abs(a.qtd_ajuste * (a.custo_medio or Decimal('0')))
        for a in ajustes
    )
    print(f'Valor total dos IDs: R$ {valor_total}')

    if dry_run:
        print('[DRY RUN] aprovacao nao aplicada')
        return

    agora = agora_utc_naive()
    for a in ajustes:
        a.status = 'APROVADO'
        a.aprovado_em = agora
        a.aprovado_por = usuario
    db.session.commit()
    print(f'OK: {len(ajustes)} ajustes APROVADOS por {usuario}')


def _parse_ids(arg: str) -> list:
    """Parse '139003,139004,...' or '139003-139008' em lista de ints."""
    if '-' in arg and ',' not in arg:
        ini, fim = arg.split('-', 1)
        return list(range(int(ini), int(fim) + 1))
    return [int(x.strip()) for x in arg.split(',') if x.strip()]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--propor', action='store_true',
                        help='le diff_inventario.json e cria ajustes PROPOSTO')
    parser.add_argument('--listar-onda', type=int,
                        help='lista ajustes PROPOSTO da onda + hash + valor')
    parser.add_argument('--listar-ids', type=str,
                        help='lista ajustes por IDs (ex: "139003,139004" ou "139003-139008")')
    parser.add_argument('--aprovar-onda', type=int,
                        help='aprova ajustes PROPOSTO da onda (exige --hash)')
    parser.add_argument('--aprovar-ids', type=str,
                        help='aprova subset de IDs (exige --hash e --company-id)')
    parser.add_argument('--company-id', type=int, choices=[1, 4, 5],
                        help='filtra/valida por empresa (1=FB, 4=CD, 5=LF). '
                             'Obrigatorio com --aprovar-ids.')
    parser.add_argument('--hash',
                        help='hash esperado para travar conjunto aprovado')
    parser.add_argument('--usuario',
                        default=os.environ.get('USER', 'desconhecido'),
                        help='usuario que opera (default: $USER)')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        if args.propor:
            cmd_propor(args.usuario, args.dry_run)
        elif args.listar_onda is not None:
            cmd_listar(args.listar_onda)
        elif args.listar_ids is not None:
            cmd_listar_ids(_parse_ids(args.listar_ids))
        elif args.aprovar_onda is not None:
            if not args.hash:
                print('ERRO: --aprovar-onda exige --hash=<sha>')
                sys.exit(2)
            cmd_aprovar(
                args.aprovar_onda, args.hash, args.usuario, args.dry_run
            )
        elif args.aprovar_ids is not None:
            if not args.hash:
                print('ERRO: --aprovar-ids exige --hash=<sha>')
                sys.exit(2)
            if args.company_id is None:
                print('ERRO: --aprovar-ids exige --company-id=N')
                sys.exit(2)
            cmd_aprovar_ids(
                _parse_ids(args.aprovar_ids), args.hash, args.usuario,
                args.dry_run, args.company_id,
            )
        else:
            parser.print_help()


if __name__ == '__main__':
    main()
