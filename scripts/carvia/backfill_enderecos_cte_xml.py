#!/usr/bin/env python3
"""C5 / A4.3 (2026-04-19): Backfill de enderecos textuais em
CarviaOperacao via re-parse do XML do CTe.

Cenario: A4.1 adicionou 8 campos de endereco (remetente/destinatario
logradouro/numero/bairro/cep). NOVOS imports populam automaticamente.
Este script preenche operacoes IMPORTADO ja existentes que tenham
`cte_xml_path` mas `destinatario_logradouro IS NULL`.

Fluxo:
  1. Query candidatos
  2. Para cada (batch de 50): download XML S3 -> parse -> atualiza
     campos vazios + audit CarviaEnderecoCorrecao (motivo='BACKFILL_XML')
  3. Commit por batch + sleep entre batches

Dry-run por default. --apply para executar.

Uso:
    source .venv/bin/activate
    python scripts/carvia/backfill_enderecos_cte_xml.py                # dry-run
    python scripts/carvia/backfill_enderecos_cte_xml.py --apply
    python scripts/carvia/backfill_enderecos_cte_xml.py --apply --limit 10
"""

import argparse
import json
import logging
import sys
import time
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app import create_app, db  # noqa: E402
from sqlalchemy import text  # noqa: E402

logging.basicConfig(
    level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s'
)
logger = logging.getLogger(__name__)


CAMPOS_ENDERECO = [
    ('remetente_logradouro', 'logradouro'),
    ('remetente_numero', 'numero'),
    ('remetente_bairro', 'bairro'),
    ('remetente_cep', 'cep'),
    ('destinatario_logradouro', 'logradouro'),
    ('destinatario_numero', 'numero'),
    ('destinatario_bairro', 'bairro'),
    ('destinatario_cep', 'cep'),
]


def listar_candidatos(limit=None):
    q = text("""
        SELECT id, cte_numero, cte_xml_path, criado_em
        FROM carvia_operacoes
        WHERE tipo_entrada = 'IMPORTADO'
          AND cte_xml_path IS NOT NULL
          AND destinatario_logradouro IS NULL
          AND status != 'CANCELADO'
        ORDER BY criado_em DESC
    """)
    rows = db.session.execute(q).fetchall()
    if limit:
        rows = rows[:limit]
    return [dict(r._mapping) for r in rows]


def processar_operacao(op_id, cte_xml_path, apply_changes, audit_file):
    from app.carvia.models import CarviaOperacao, CarviaEnderecoCorrecao
    from app.carvia.services.parsers.cte_xml_parser_carvia import (
        CTeXMLParserCarvia,
    )
    from app.utils.file_storage import get_file_storage

    resultado = {
        'op_id': op_id,
        'status': 'SKIPPED',
        'campos_atualizados': [],
    }

    try:
        storage = get_file_storage()
        xml_bytes = storage.download_file(cte_xml_path)
        if not xml_bytes:
            resultado['status'] = 'ERRO'
            resultado['erro'] = 'xml_bytes vazio'
            return resultado

        xml_str = (
            xml_bytes.decode('utf-8', errors='replace')
            if isinstance(xml_bytes, bytes) else xml_bytes
        )
        parser = CTeXMLParserCarvia(xml_content=xml_str)
        end_rem = parser.get_endereco_remetente() or {}
        end_dest = parser.get_endereco_destinatario() or {}

        op = db.session.get(CarviaOperacao, op_id)
        if not op:
            resultado['status'] = 'ERRO'
            resultado['erro'] = 'op_nao_encontrada'
            return resultado

        atualizados = []
        for campo_model, campo_parser in CAMPOS_ENDERECO:
            if getattr(op, campo_model) is not None:
                continue
            fonte = end_rem if campo_model.startswith('remetente_') else end_dest
            valor = fonte.get(campo_parser)
            if valor:
                atualizados.append({'campo': campo_model, 'valor_novo': valor})
                if apply_changes:
                    setattr(op, campo_model, valor)
                    db.session.add(CarviaEnderecoCorrecao(
                        operacao_id=op_id,
                        campo=campo_model,
                        valor_anterior=None,
                        valor_novo=valor,
                        motivo='BACKFILL_XML',
                        criado_por='backfill_script',
                    ))

        if atualizados:
            resultado['status'] = 'ATUALIZADO' if apply_changes else 'DRY_RUN'
            resultado['campos_atualizados'] = atualizados
        else:
            resultado['status'] = 'SEM_DADOS_NO_XML'

    except Exception as e:
        logger.exception(f'Erro no op_id={op_id}: {e}')
        resultado['status'] = 'ERRO'
        resultado['erro'] = str(e)

    if audit_file:
        audit_file.write(json.dumps({
            'timestamp': datetime.now().isoformat(),
            **resultado,
        }, ensure_ascii=False) + '\n')
        audit_file.flush()

    return resultado


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--limit', type=int, default=None)
    parser.add_argument('--batch', type=int, default=50)
    parser.add_argument('--sleep', type=float, default=2.0)
    args = parser.parse_args()

    mode = 'APPLY' if args.apply else 'DRY-RUN'
    app = create_app()
    with app.app_context():
        candidatos = listar_candidatos(limit=args.limit)
        print(f'[{mode}] Candidatos: {len(candidatos)}')
        if not candidatos:
            print('Nada a fazer.')
            return

        audit_path = (
            PROJECT_ROOT / 'logs' / 'audit' /
            'carvia_backfill_enderecos.jsonl'
        )
        audit_path.parent.mkdir(parents=True, exist_ok=True)
        audit_file = open(audit_path, 'a', encoding='utf-8')

        stats = {
            'total': len(candidatos),
            'atualizado': 0,
            'dry_run': 0,
            'sem_dados': 0,
            'erro': 0,
            'campos_preenchidos': 0,
        }

        try:
            for i in range(0, len(candidatos), args.batch):
                batch = candidatos[i:i + args.batch]
                for cand in batch:
                    r = processar_operacao(
                        op_id=cand['id'],
                        cte_xml_path=cand['cte_xml_path'],
                        apply_changes=args.apply,
                        audit_file=audit_file,
                    )
                    n_campos = len(r['campos_atualizados'])
                    stats['campos_preenchidos'] += n_campos
                    if r['status'] == 'ATUALIZADO':
                        stats['atualizado'] += 1
                        print(f'  +{cand["cte_numero"]} id={cand["id"]} '
                              f'{n_campos} campos')
                    elif r['status'] == 'DRY_RUN':
                        stats['dry_run'] += 1
                        print(f'  ~{cand["cte_numero"]} id={cand["id"]} '
                              f'({n_campos} seriam atualizados)')
                    elif r['status'] == 'SEM_DADOS_NO_XML':
                        stats['sem_dados'] += 1
                    else:
                        stats['erro'] += 1
                        print(f'  !{cand["cte_numero"]} id={cand["id"]} '
                              f'ERRO: {r.get("erro")}')

                if args.apply:
                    try:
                        db.session.commit()
                        print(f'  Batch {i // args.batch + 1}: commit OK')
                    except Exception as e:
                        logger.exception(f'Commit do batch falhou: {e}')
                        db.session.rollback()
                        stats['erro'] += len(batch)

                if i + args.batch < len(candidatos):
                    time.sleep(args.sleep)
        finally:
            audit_file.close()

        print('=' * 60)
        print(f'[{mode}] Resumo final:')
        for k, v in stats.items():
            print(f'  {k:25s}: {v}')
        print(f'Audit log: {audit_path}')

        if not args.apply and stats['dry_run'] > 0:
            print('\nPara aplicar: python ... --apply')


if __name__ == '__main__':
    main()
