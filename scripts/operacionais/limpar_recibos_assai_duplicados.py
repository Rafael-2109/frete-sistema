"""Remove recibos Motos Assai duplicados (re-importacao do mesmo arquivo).

CENARIO DETECTADO em 2026-05-09 (Render):
  Compra 1 tem 5 recibos com o MESMO doc_s3_key e mesmo conteudo. Apenas o
  recibo #4 esta em EM_CONFERENCIA. Os outros 4 sao re-importacoes orfas.

REGRAS DE SEGURANCA:
  1. Detecta clusters de duplicados por (compra_id, doc_s3_key) e/ou por
     equivalencia 100% de chassis ativos.
  2. Em cada cluster, escolhe o "alvo" (recibo a manter) usando o ranking:
        a) Tem itens conferidos (mais conferidos primeiro)
        b) Status EM_CONFERENCIA / COM_DIVERGENCIA / CONCLUIDO
        c) Tem itens com divergencia
        d) Recibo mais antigo (id menor) — desempate
  3. Para os "duplicados a excluir":
        - Hard-block se algum item conferido=True OU tipo_divergencia
          preenchido OU evento referenciando o recibo_id no JSONB.
        - Caso contrario, hard-delete do recibo (cascade dos itens).
  4. NUNCA deleta o arquivo do S3 (e compartilhado entre os recibos do
     cluster — manter para o "alvo").

USO:
  python scripts/operacionais/limpar_recibos_assai_duplicados.py            # dry-run
  python scripts/operacionais/limpar_recibos_assai_duplicados.py --executar # aplica
  python scripts/operacionais/limpar_recibos_assai_duplicados.py --compra 1 # so essa compra
"""

from __future__ import annotations

import argparse
import os
import sys
from collections import defaultdict
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app import create_app, db  # noqa: E402 
from sqlalchemy import text  # noqa: E402


STATUS_RANK = {
    'CONCLUIDO': 4,
    'COM_DIVERGENCIA': 3,
    'EM_CONFERENCIA': 2,
    'RESOLVENDO_DUPLICIDADE': 1,
    'RECEBIDO_AGUARDANDO_CONFERENCIA': 0,
}


def carregar_clusters(compra_id: Optional[int]) -> Dict[Tuple[int, Optional[str]], List[Dict]]:
    """Agrupa recibos por (compra_id, doc_s3_key).

    Retorna apenas clusters com >= 2 recibos (ou seja, candidatos a duplicidade).
    """
    where_compra = 'AND r.compra_id = :compra_id' if compra_id else ''
    rows = db.session.execute(text(f"""
        SELECT
            r.id,
            r.compra_id,
            r.numero_recibo,
            r.status,
            r.doc_s3_key,
            r.tipo_documento,
            r.parser_usado,
            r.criado_em,
            (SELECT COUNT(*) FROM assai_recibo_item
                WHERE recibo_id = r.id AND ativo = TRUE)                          AS itens_ativos,
            (SELECT COUNT(*) FROM assai_recibo_item
                WHERE recibo_id = r.id AND ativo = TRUE AND conferido = TRUE)     AS conferidos,
            (SELECT COUNT(*) FROM assai_recibo_item
                WHERE recibo_id = r.id AND ativo = TRUE AND tipo_divergencia IS NOT NULL) AS com_div
        FROM assai_recibo_motochefe r
        WHERE 1=1
          {where_compra}
        ORDER BY r.compra_id, r.criado_em, r.id
    """), {'compra_id': compra_id} if compra_id else {}).mappings().all()

    clusters: Dict[Tuple[int, Optional[str]], List[Dict]] = defaultdict(list)
    for r in rows:
        chave = (r['compra_id'], r['doc_s3_key'])
        clusters[chave].append(dict(r))

    return {k: v for k, v in clusters.items() if len(v) >= 2}


def chassis_de(recibo_id: int) -> set:
    rows = db.session.execute(text("""
        SELECT chassi FROM assai_recibo_item
        WHERE recibo_id = :rid AND ativo = TRUE
    """), {'rid': recibo_id}).all()
    return {r[0] for r in rows}


def escolher_alvo(recibos: List[Dict]) -> Dict:
    def chave(r):
        return (
            r['conferidos'],
            STATUS_RANK.get(r['status'], -1),
            r['com_div'],
            -r['id'],
        )
    return max(recibos, key=chave)


def pode_excluir(recibo_id: int) -> Tuple[bool, str]:
    """Retorna (pode, motivo). Bloqueia se algum item conferido OU divergencia OU evento referenciando."""
    conferidos = db.session.execute(text("""
        SELECT COUNT(*) FROM assai_recibo_item
        WHERE recibo_id = :rid AND conferido = TRUE
    """), {'rid': recibo_id}).scalar()
    if conferidos:
        return False, f'{conferidos} chassis conferidos'

    com_div = db.session.execute(text("""
        SELECT COUNT(*) FROM assai_recibo_item
        WHERE recibo_id = :rid AND tipo_divergencia IS NOT NULL
    """), {'rid': recibo_id}).scalar()
    if com_div:
        return False, f'{com_div} itens com divergencia'

    eventos = db.session.execute(text("""
        SELECT COUNT(*) FROM assai_moto_evento
        WHERE (dados_extras->>'recibo_id')::int = :rid
    """), {'rid': recibo_id}).scalar()
    if eventos:
        return False, f'{eventos} eventos referenciando'

    return True, ''


def montar_plano(compra_id: Optional[int]) -> List[Dict]:
    """Retorna lista de planos por cluster.

    Cada plano:
        {
            'chave': (compra_id, doc_s3_key),
            'alvo': dict-recibo,
            'duplicados': [{'recibo': dict-recibo, 'pode': bool, 'motivo': str, 'sao_iguais': bool}, ...],
        }
    """
    clusters = carregar_clusters(compra_id)
    planos = []
    for chave, recibos in clusters.items():
        alvo = escolher_alvo(recibos)
        chassis_alvo = chassis_de(alvo['id'])
        duplicados_info = []
        for r in recibos:
            if r['id'] == alvo['id']:
                continue
            ok, motivo = pode_excluir(r['id'])
            chassis_r = chassis_de(r['id'])
            sao_iguais = chassis_r == chassis_alvo or chassis_r.issubset(chassis_alvo)
            duplicados_info.append({
                'recibo': r,
                'pode': ok,
                'motivo': motivo,
                'sao_iguais': sao_iguais,
                'chassis_intersect': len(chassis_r & chassis_alvo),
                'chassis_total': len(chassis_r),
            })
        if duplicados_info:
            planos.append({'chave': chave, 'alvo': alvo, 'duplicados': duplicados_info})
    return planos


def imprimir_plano(planos: List[Dict]) -> None:
    if not planos:
        print('Nenhum cluster com duplicados encontrado.')
        return

    print(f'\n{len(planos)} cluster(s) com duplicidade encontrados:\n')
    for p in planos:
        compra_id, s3 = p['chave']
        alvo = p['alvo']
        print(f'-- Compra #{compra_id} | s3={s3 or "<sem-s3>"}')
        print(f'   ALVO (manter):  recibo #{alvo["id"]:<4} status={alvo["status"]:<32} '
              f'conferidos={alvo["conferidos"]} divs={alvo["com_div"]} itens={alvo["itens_ativos"]}')
        for d in p['duplicados']:
            r = d['recibo']
            marca = 'EXCLUIR' if d['pode'] else 'BLOQUEADO'
            extra = f'({d["motivo"]})' if d['motivo'] else ''
            iguais = 'iguais' if d['sao_iguais'] else f'diff ({d["chassis_intersect"]}/{d["chassis_total"]})'
            print(f'   {marca:>9}: recibo #{r["id"]:<4} status={r["status"]:<32} '
                  f'conferidos={r["conferidos"]} divs={r["com_div"]} itens={r["itens_ativos"]} '
                  f'[{iguais}] {extra}')
        print()


def executar(planos: List[Dict]) -> Tuple[int, int]:
    """Executa exclusoes. Retorna (excluidos, bloqueados)."""
    excluidos = 0
    bloqueados = 0
    for p in planos:
        for d in p['duplicados']:
            r = d['recibo']
            if not d['pode']:
                print(f'  SKIP   recibo #{r["id"]}: {d["motivo"]}')
                bloqueados += 1
                continue
            if not d['sao_iguais']:
                print(f'  SKIP   recibo #{r["id"]}: chassis nao sao subconjunto do alvo')
                bloqueados += 1
                continue
            db.session.execute(
                text('DELETE FROM assai_recibo_motochefe WHERE id = :rid'),
                {'rid': r['id']},
            )
            print(f'  DELETE recibo #{r["id"]} (compra={r["compra_id"]})')
            excluidos += 1
    if excluidos:
        db.session.commit()
    return excluidos, bloqueados


def main():
    parser = argparse.ArgumentParser(description='Limpa recibos Motos Assai duplicados.')
    parser.add_argument('--executar', action='store_true', help='Aplicar (default = dry-run)')
    parser.add_argument('--compra', type=int, help='Limita a uma compra especifica')
    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        planos = montar_plano(args.compra)
        imprimir_plano(planos)

        if not planos:
            return

        if args.executar:
            print('\n>>> APLICANDO (--executar)\n')
            excl, blk = executar(planos)
            print(f'\nResultado: {excl} excluidos / {blk} bloqueados.\n')
        else:
            print('\n[DRY-RUN] Nenhuma alteracao feita. Use --executar para aplicar.\n')


if __name__ == '__main__':
    main()
