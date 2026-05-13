#!/usr/bin/env python
"""Backfill VOE FATURADO ATE 11.05 — modulo motos_assai.

Le scripts/migrations/data/backfill_voe_11_05.json (gerado a partir da planilha
"VOE - FATURADO ATE 11.05.xlsx" com 729 motos) e cria:
- 1 compra guarda-chuva: MA-BACKFILL-VOE-2026-05-11 (idempotente: aborta se ja existe)
- N recibos (1 por DATA DE CHEGADA distinta, com numero BACKFILL-YYYYMMDD)
- AssaiReciboItem por chassi (conferido=True, sem foto)
- AssaiMoto por chassi (insert-once)
- Cadeia de eventos por chassi baseada em STATUS Excel + PROBLEMA NO CHASSI:

    STATUS Excel    | Sem problema                        | Com problema
    --------------- | ----------------------------------- | -----------------------------------------------------
    ESTOQUE         | ESTOQUE                             | ESTOQUE -> PENDENTE -> PENDENCIA_RESOLVIDA
    PENDENTE        | ESTOQUE -> PENDENTE                 | ESTOQUE -> PENDENTE (com descricao)
    DISPONIVEL      | ESTOQUE -> MONTADA -> DISPONIVEL    | ESTOQUE -> PENDENTE -> PENDENCIA_RESOLVIDA -> MONTADA -> DISPONIVEL
    FATURADAS       | ESTOQUE -> MONTADA -> DISPONIVEL    | ESTOQUE -> PENDENTE -> PENDENCIA_RESOLVIDA -> MONTADA -> DISPONIVEL

Regra 4: FATURADAS lance como DISPONIVEL (NF chegara depois e fara DISPONIVEL -> FATURADA).
Regra 6: PROBLEMA NO CHASSI sempre registra evento PENDENTE para historico,
         mesmo que status final nao seja PENDENTE.

IDEMPOTENTE — pode rodar em todo deploy (build.sh):
- Aborta limpo se compra "MA-BACKFILL-VOE-2026-05-11" ja existe (exit 0 com mensagem).
- Aborta se qualquer chassi do JSON ja existe em assai_moto (exit 1 com diagnostico).

Uso:
    # Dry-run (default)
    python scripts/migrations/backfill_motos_assai_voe_11_05.py

    # Executar
    python scripts/migrations/backfill_motos_assai_voe_11_05.py --executar
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from datetime import date, datetime, time
from pathlib import Path

# sys.path para rodar tanto local quanto Render Shell
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app import create_app, db  # noqa: E402 # type: ignore
from app.auth.models import Usuario  # noqa: E402 # type: ignore
from app.motos_assai.models import (  # noqa: E402 # type: ignore
    AssaiCompraMotochefe,
    AssaiMoto,
    AssaiMotoEvento,
    AssaiReciboItem,
    AssaiReciboMotochefe,
    COMPRA_STATUS_FECHADA,
    EVENTO_DISPONIVEL,
    EVENTO_ESTOQUE,
    EVENTO_MONTADA,
    EVENTO_PENDENCIA_RESOLVIDA,
    EVENTO_PENDENTE,
    RECIBO_STATUS_CONCLUIDO,
)
from app.motos_assai.services.modelo_resolver import resolver_modelo  # noqa: E402 # type: ignore

NUMERO_COMPRA = 'MA-BACKFILL-VOE-2026-05-11'
JSON_PATH_DEFAULT = Path(__file__).parent / 'data' / 'backfill_voe_11_05.json'

# Offsets de horario para a cadeia de eventos (mantem ORDER BY ocorrido_em correto)
OFFSETS = {
    EVENTO_ESTOQUE: time(9, 0, 0),
    EVENTO_PENDENTE: time(10, 0, 0),
    EVENTO_PENDENCIA_RESOLVIDA: time(11, 0, 0),
    EVENTO_MONTADA: time(12, 0, 0),
    EVENTO_DISPONIVEL: time(13, 0, 0),
}


def mapear_eventos(status_excel: str, tem_problema: bool) -> list:
    """Retorna lista ordenada de tipos de evento conforme STATUS + PROBLEMA."""
    if status_excel == 'ESTOQUE':
        if tem_problema:
            return [EVENTO_ESTOQUE, EVENTO_PENDENTE, EVENTO_PENDENCIA_RESOLVIDA]
        return [EVENTO_ESTOQUE]
    if status_excel == 'PENDENTE':
        return [EVENTO_ESTOQUE, EVENTO_PENDENTE]
    if status_excel in ('DISPONIVEL', 'FATURADAS'):
        if tem_problema:
            return [
                EVENTO_ESTOQUE,
                EVENTO_PENDENTE,
                EVENTO_PENDENCIA_RESOLVIDA,
                EVENTO_MONTADA,
                EVENTO_DISPONIVEL,
            ]
        return [EVENTO_ESTOQUE, EVENTO_MONTADA, EVENTO_DISPONIVEL]
    raise ValueError(f'STATUS desconhecido: {status_excel}')


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--executar',
        action='store_true',
        help='Aplica as alteracoes (sem isso, faz dry-run com ROLLBACK)',
    )
    parser.add_argument(
        '--json',
        default=str(JSON_PATH_DEFAULT),
        help=f'Caminho do JSON com os registros (default: {JSON_PATH_DEFAULT})',
    )
    args = parser.parse_args()

    dry_run = not args.executar

    print('=' * 72)
    print(f'BACKFILL VOE FATURADO ATE 11.05  ({"DRY-RUN" if dry_run else "EXECUTAR"})')
    print('=' * 72)
    print(f'JSON: {args.json}')

    # 1) Le JSON embarcado
    with open(args.json, 'r', encoding='utf-8') as f:
        payload = json.load(f)
    registros = payload.get('registros', [])
    if not registros:
        print('ERRO: JSON sem registros.')
        return 1
    print(f'Origem: {payload.get("origem", "?")}')
    print(f'Gerado em: {payload.get("gerado_em", "?")}')
    print(f'Registros: {len(registros)} (declarado: {payload.get("total")})')

    # Validacoes basicas
    chassis = [r['chassi'].strip().upper() for r in registros]
    if any(not c for c in chassis):
        print('ERRO: registros com chassi vazio.')
        return 1
    if len(set(chassis)) != len(chassis):
        from collections import Counter
        dups = [c for c, n in Counter(chassis).items() if n > 1]
        print(f'ERRO: chassis duplicados no JSON: {dups[:10]}')
        return 1

    app = create_app()
    with app.app_context():
        # 2) Idempotencia: se compra ja existe, sai limpo (exit 0)
        existente = AssaiCompraMotochefe.query.filter_by(numero=NUMERO_COMPRA).first()
        if existente:
            print(f'\n[OK] Compra "{NUMERO_COMPRA}" ja existe (id={existente.id}). '
                  f'Backfill ja foi aplicado anteriormente — nada a fazer.')
            return 0

        # 3) Operador (admin)
        operador = (
            Usuario.query.filter_by(perfil='administrador', status='ativo')
            .order_by(Usuario.id)
            .first()
        )
        if not operador:
            print('ERRO: nenhum admin ativo encontrado.')
            return 1
        print(f'Operador: id={operador.id} {operador.nome}')

        # 4) Resolve modelos (cache)
        modelos_unicos = sorted({r['modelo'].strip().upper() for r in registros})
        cache_modelo = {}
        invalidos = []
        for txt in modelos_unicos:
            m = resolver_modelo(txt)
            if m:
                cache_modelo[txt] = m
            else:
                invalidos.append(txt)
        if invalidos:
            print(f'ERRO: modelos nao resolvidos: {invalidos}')
            return 1
        print('Modelos resolvidos:')
        for k, v in cache_modelo.items():
            print(f'  "{k}" -> id={v.id} codigo={v.codigo}')

        # 5) Verifica chassis em conflito
        chassis_conflito = {
            c[0]
            for c in db.session.query(AssaiMoto.chassi)
            .filter(AssaiMoto.chassi.in_(chassis))
            .all()
        }
        if chassis_conflito:
            print(f'\nERRO: {len(chassis_conflito)} chassis ja existem em assai_moto.')
            print(f'  Amostra: {sorted(chassis_conflito)[:5]}')
            return 1

        # 6) Cria compra guarda-chuva
        compra = AssaiCompraMotochefe(
            numero=NUMERO_COMPRA,
            data_emissao=date(2026, 5, 11),
            motochefe_cnpj=None,
            status=COMPRA_STATUS_FECHADA,
            criada_por_id=operador.id,
        )
        db.session.add(compra)
        db.session.flush()
        print(f'\nCompra criada: id={compra.id} numero={compra.numero}')

        # 7) Agrupa por data de chegada
        por_data: dict[str, list[dict]] = defaultdict(list)
        for r in registros:
            por_data[r['data_chegada']].append(r)
        datas_ord = sorted(por_data.keys())
        print(f'\nDatas de chegada distintas: {len(datas_ord)} -> {datas_ord}')

        stats = {
            'recibos': 0,
            'itens': 0,
            'motos': 0,
            'eventos': 0,
            'eventos_por_tipo': defaultdict(int),
            'linhas_por_status': defaultdict(int),
            'linhas_com_problema_por_status': defaultdict(int),
        }

        for data_str in datas_ord:
            d = datetime.strptime(data_str, '%Y-%m-%d').date()
            sub = por_data[data_str]
            recibo = AssaiReciboMotochefe(
                compra_id=compra.id,
                numero_recibo=f'BACKFILL-{d.strftime("%Y%m%d")}',
                data_recibo=d,
                equipe='BACKFILL',
                conferente_motochefe='BACKFILL',
                total_motos_declarado=len(sub),
                tipo_documento='BACKFILL',
                parser_usado='backfill_xlsx',
                status=RECIBO_STATUS_CONCLUIDO,
                criado_por_id=operador.id,
            )
            db.session.add(recibo)
            db.session.flush()
            stats['recibos'] += 1
            print(f'  [{d}] recibo id={recibo.id} numero={recibo.numero_recibo} motos={len(sub)}')

            for r in sub:
                chassi = r['chassi'].strip().upper()
                modelo_txt = r['modelo'].strip().upper()
                modelo = cache_modelo[modelo_txt]
                cor = r['cor'].strip().upper()
                status_excel = r['status'].strip().upper()
                problema = r.get('problema')
                tem_problema = bool(problema and str(problema).strip())

                stats['linhas_por_status'][status_excel] += 1
                if tem_problema:
                    stats['linhas_com_problema_por_status'][status_excel] += 1

                item = AssaiReciboItem(
                    recibo_id=recibo.id,
                    chassi=chassi,
                    modelo_texto_recibo=modelo_txt,
                    modelo_id=modelo.id,
                    cor_texto=cor,
                    motor=None,
                    conferido=True,
                    qr_code_lido=False,
                    foto_s3_key=None,
                    tipo_divergencia=None,
                    ativo=True,
                )
                db.session.add(item)
                db.session.flush()
                stats['itens'] += 1

                moto = AssaiMoto(
                    chassi=chassi,
                    modelo_id=modelo.id,
                    cor=cor,
                    motor=None,
                    ano=None,
                    criada_em=datetime.combine(d, time(8, 0, 0)),
                )
                db.session.add(moto)
                stats['motos'] += 1

                tipos = mapear_eventos(status_excel, tem_problema)
                for tipo in tipos:
                    ocor = datetime.combine(d, OFFSETS[tipo])
                    dados_extras = {'origem': 'backfill_xlsx'}
                    obs = None
                    if tipo == EVENTO_ESTOQUE:
                        dados_extras['recibo_id'] = recibo.id
                        dados_extras['item_id'] = item.id
                    if tipo == EVENTO_PENDENTE and tem_problema:
                        dados_extras['descricao'] = str(problema).strip()
                        obs = str(problema).strip()
                    ev = AssaiMotoEvento(
                        chassi=chassi,
                        tipo=tipo,
                        ocorrido_em=ocor,
                        operador_id=operador.id,
                        observacao=obs,
                        dados_extras=dados_extras,
                    )
                    db.session.add(ev)
                    stats['eventos'] += 1
                    stats['eventos_por_tipo'][tipo] += 1

        print()
        print('=' * 72)
        print('RESUMO')
        print('=' * 72)
        print(f'Compra:    1 ({NUMERO_COMPRA})')
        print(f'Recibos:   {stats["recibos"]}')
        print(f'Itens:     {stats["itens"]}')
        print(f'Motos:     {stats["motos"]}')
        print(f'Eventos:   {stats["eventos"]}')

        print('\nEventos por tipo:')
        for t, n in sorted(stats['eventos_por_tipo'].items()):
            print(f'  {t:<25} {n}')

        print('\nLinhas por STATUS Excel:')
        for s, n in sorted(stats['linhas_por_status'].items()):
            com_prob = stats['linhas_com_problema_por_status'].get(s, 0)
            print(f'  {s:<15} {n:>4}  (com problema: {com_prob})')

        if dry_run:
            db.session.rollback()
            print('\n[DRY-RUN] Rollback aplicado. Nada foi persistido.')
            print('Para executar de fato, rode com --executar')
        else:
            db.session.commit()
            print('\n[EXECUTADO] Commit realizado.')

    return 0


if __name__ == '__main__':
    sys.exit(main())
