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


def calcular_acao_decidida(d: dict) -> str:
    """Mapeia diff → acao_decidida do AjusteEstoqueInventario."""
    if d['tipo_divergencia'] == 'APENAS_LOTE':
        return 'RENOMEAR_LOTE'
    qtd_ajuste = Decimal(d['qtd_ajuste'])
    if qtd_ajuste == 0:
        return 'SEM_ACAO'
    sinal = 1 if qtd_ajuste > 0 else -1
    tipo_op = resolver_operacao_por_tipo_produto(
        tipo=d['tipo_produto'],
        company_id=d['company_id'],
        sinal=sinal,
    )
    cid = d['company_id']
    if tipo_op == 'industrializacao':
        return 'INDUSTRIALIZACAO_FB_LF'
    if tipo_op == 'perda':
        return 'PERDA_LF_FB'
    if tipo_op == 'dev-industrializacao':
        # LF perdeu (origem LF, destino FB): DEV_LF_FB
        # FB perdeu (origem FB, destino LF): DEV_FB_LF
        # Para tipo_produto=4 com sinal negativo em LF → DEV_LF_FB
        # Para CD ↔ LF, plano original cobre apenas via D003.
        # Aqui mantemos compat: cid=5 e sinal<0 → DEV_LF_FB; senao DEV_FB_LF.
        return 'DEV_LF_FB' if cid == 5 and sinal < 0 else 'DEV_FB_LF'
    if tipo_op == 'transf-filial':
        if cid == 4:
            return 'TRANSFERIR_CD_FB'
        return 'TRANSFERIR_FB_CD'
    raise ValueError(f'tipo_op desconhecido: {tipo_op}')


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

    contador = {'inserido': 0, 'ja_existe': 0, 'sem_acao': 0}
    for d in diffs:
        acao = calcular_acao_decidida(d)
        if acao == 'SEM_ACAO':
            contador['sem_acao'] += 1
            continue

        existe = AjusteEstoqueInventario.query.filter_by(
            ciclo=CICLO,
            cod_produto=d['cod_produto'],
            company_id=d['company_id'],
            lote_odoo=d['lote_odoo'],
        ).first()
        if existe:
            contador['ja_existe'] += 1
            continue

        rec = AjusteEstoqueInventario(
            ciclo=CICLO,
            cod_produto=d['cod_produto'],
            tipo_produto=d['tipo_produto'],
            company_id=d['company_id'],
            lote_inventariado=d['lote_inventariado'],
            lote_odoo=d['lote_odoo'],
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


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--propor', action='store_true',
                        help='le diff_inventario.json e cria ajustes PROPOSTO')
    parser.add_argument('--listar-onda', type=int,
                        help='lista ajustes PROPOSTO da onda + hash + valor')
    parser.add_argument('--aprovar-onda', type=int,
                        help='aprova ajustes PROPOSTO da onda (exige --hash)')
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
        elif args.aprovar_onda is not None:
            if not args.hash:
                print('ERRO: --aprovar-onda exige --hash=<sha>')
                sys.exit(2)
            cmd_aprovar(
                args.aprovar_onda, args.hash, args.usuario, args.dry_run
            )
        else:
            parser.print_help()


if __name__ == '__main__':
    main()
