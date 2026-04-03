"""
Reprocessar NFs CarVia sem itens de produto
=============================================

Baixa PDFs do S3, re-parseia com o parser atual, insere itens
faltantes e roda deteccao de motos.

Dois modos:
  --diagnostico  Apenas mostra o que seria feito (DRY RUN)
  --executar     Efetivamente salva no banco

Pré-requisito: Rodar em ambiente com acesso ao S3 (producao/Render).

Uso:
  python scripts/migrations/reprocessar_nfs_sem_itens.py --diagnostico
  python scripts/migrations/reprocessar_nfs_sem_itens.py --executar
"""

import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from app import create_app, db


def buscar_nfs_sem_itens():
    """Retorna NFs ativas de moto sem itens (emitente != NOTCO/NACOM)."""
    rows = db.session.execute(db.text("""
        SELECT nf.id, nf.numero_nf, nf.nome_emitente, nf.arquivo_pdf_path, nf.tipo_fonte
        FROM carvia_nfs nf
        WHERE nf.status = 'ATIVA'
          AND nf.tipo_fonte = 'PDF_DANFE'
          AND nf.arquivo_pdf_path IS NOT NULL
          AND UPPER(COALESCE(nf.nome_emitente, '')) NOT LIKE '%NOTCO%'
          AND UPPER(COALESCE(nf.nome_emitente, '')) NOT LIKE '%NACOM%'
          AND NOT EXISTS (SELECT 1 FROM carvia_nf_itens ni WHERE ni.nf_id = nf.id)
        ORDER BY nf.id
    """)).fetchall()
    return rows


def buscar_nfs_itens_sem_modelo():
    """Retorna NFs com itens de moto sem modelo_moto_id detectado."""
    rows = db.session.execute(db.text("""
        SELECT DISTINCT nf.id, nf.numero_nf, nf.nome_emitente,
               nf.arquivo_pdf_path, nf.tipo_fonte
        FROM carvia_nfs nf
        JOIN carvia_nf_itens ni ON ni.nf_id = nf.id
        WHERE nf.status = 'ATIVA'
          AND nf.tipo_fonte = 'PDF_DANFE'
          AND nf.arquivo_pdf_path IS NOT NULL
          AND UPPER(COALESCE(nf.nome_emitente, '')) NOT LIKE '%NOTCO%'
          AND UPPER(COALESCE(nf.nome_emitente, '')) NOT LIKE '%NACOM%'
          AND ni.modelo_moto_id IS NULL
        ORDER BY nf.id
    """)).fetchall()
    return rows


def reprocessar_nf(nf_row, storage, dry_run=True):
    """Re-parseia PDF de uma NF e insere itens faltantes.

    Returns:
        dict com resultado: {'itens_parseados': int, 'itens_inseridos': int,
                             'motos_detectadas': int, 'desc_atualizadas': int, 'erro': str|None}
    """
    from app.carvia.services.parsers.danfe_pdf_parser import DanfePDFParser
    from app.carvia.models import CarviaNfItem
    from app.carvia.services.pricing.moto_recognition_service import MotoRecognitionService

    resultado = {
        'itens_parseados': 0, 'itens_inseridos': 0,
        'motos_detectadas': 0, 'desc_atualizadas': 0, 'erro': None,
    }

    nf_id = nf_row.id
    pdf_path = nf_row.arquivo_pdf_path

    if not pdf_path:
        resultado['erro'] = 'Sem arquivo_pdf_path'
        return resultado

    # Baixar PDF
    pdf_bytes = storage.download_file(pdf_path)
    if not pdf_bytes:
        resultado['erro'] = f'Falha ao baixar: {pdf_path}'
        return resultado

    # Parsear
    parser = DanfePDFParser(pdf_bytes=pdf_bytes)
    if not parser.is_valid():
        resultado['erro'] = 'PDF invalido pelo parser'
        return resultado

    itens = parser.get_itens_produto()
    resultado['itens_parseados'] = len(itens)

    if not itens:
        # Dump texto para diagnostico
        linhas = parser._linhas()
        dump_path = f'/tmp/danfe_debug_nf_{nf_id}.txt'
        try:
            with open(dump_path, 'w') as f:
                f.write(f"NF {nf_id} | #{nf_row.numero_nf} | {nf_row.nome_emitente}\n")
                f.write(f"Total linhas: {len(linhas)}\n")
                f.write("=" * 60 + "\n")
                for i, linha in enumerate(linhas):
                    f.write(f"L{i:04d}: {linha}\n")
            print(f"    [DEBUG] Texto raw salvo em {dump_path}")
        except Exception:
            pass
        resultado['erro'] = 'Parser retornou 0 itens (formato nao suportado?)'
        return resultado

    # Verificar se ja tem itens no banco
    count_existente = db.session.execute(db.text(
        "SELECT COUNT(*) FROM carvia_nf_itens WHERE nf_id = :nf_id"
    ), {'nf_id': nf_id}).scalar()

    if count_existente == 0:
        # CASO 1: NF sem nenhum item — inserir todos
        if not dry_run:
            for item_data in itens:
                item = CarviaNfItem(
                    nf_id=nf_id,
                    codigo_produto=item_data.get('codigo_produto'),
                    descricao=item_data.get('descricao'),
                    ncm=item_data.get('ncm'),
                    cfop=item_data.get('cfop'),
                    unidade=item_data.get('unidade'),
                    quantidade=item_data.get('quantidade'),
                    valor_unitario=item_data.get('valor_unitario'),
                    valor_total_item=item_data.get('valor_total_item'),
                )
                db.session.add(item)
            db.session.flush()
        resultado['itens_inseridos'] = len(itens)
    else:
        # CASO 2: NF com itens existentes — atualizar descricoes (se truncadas/incorretas)
        existentes = CarviaNfItem.query.filter_by(nf_id=nf_id).all()
        for existente in existentes:
            # Buscar item correspondente por NCM + posicao
            for item_data in itens:
                if (item_data.get('ncm') == existente.ncm
                        and item_data.get('codigo_produto') == existente.codigo_produto):
                    desc_nova = item_data.get('descricao', '')
                    desc_atual = existente.descricao or ''
                    if len(desc_nova) > len(desc_atual) and desc_atual in desc_nova:
                        if not dry_run:
                            existente.descricao = desc_nova
                        resultado['desc_atualizadas'] += 1
                    break

    # Rodar deteccao de motos
    if not dry_run:
        db.session.flush()
        moto_svc = MotoRecognitionService()
        moto_count = moto_svc.reprocessar_itens_nf(nf_id)
        resultado['motos_detectadas'] = moto_count.get('detectados', 0)
    else:
        # Simular: verificar quantos itens parseados matcham um modelo
        moto_svc = MotoRecognitionService()
        from app.carvia.models import CarviaModeloMoto
        modelos = CarviaModeloMoto.query.filter_by(ativo=True).all()
        for item_data in itens:
            nome = moto_svc._match_descricao(
                item_data.get('descricao', ''), modelos,
                item_data.get('codigo_produto'), ncm=item_data.get('ncm'),
            )
            if nome:
                resultado['motos_detectadas'] += 1

    return resultado


def main():
    parser = argparse.ArgumentParser(description='Reprocessar NFs CarVia sem itens')
    grupo = parser.add_mutually_exclusive_group(required=True)
    grupo.add_argument('--diagnostico', action='store_true', help='DRY RUN — apenas mostrar')
    grupo.add_argument('--executar', action='store_true', help='Efetivamente salvar')
    args = parser.parse_args()

    dry_run = args.diagnostico

    app = create_app()
    with app.app_context():
        from app.utils.file_storage import get_file_storage
        storage = get_file_storage()

        print("=" * 70)
        print(f"MODO: {'DIAGNOSTICO (DRY RUN)' if dry_run else 'EXECUCAO'}")
        print("=" * 70)

        # Parte 1: NFs sem itens
        nfs_sem = buscar_nfs_sem_itens()
        print(f"\n--- PARTE 1: {len(nfs_sem)} NF(s) sem nenhum item ---")

        total_inseridos = 0
        total_motos = 0

        for nf_row in nfs_sem:
            print(f"\n  NF {nf_row.id} | #{nf_row.numero_nf} | {nf_row.nome_emitente}")
            res = reprocessar_nf(nf_row, storage, dry_run=dry_run)

            if res['erro']:
                print(f"    [ERRO] {res['erro']}")
            else:
                print(f"    Parseados: {res['itens_parseados']}, "
                      f"Inseridos: {res['itens_inseridos']}, "
                      f"Motos detectadas: {res['motos_detectadas']}")
                total_inseridos += res['itens_inseridos']
                total_motos += res['motos_detectadas']

        # Parte 2: NFs com itens sem modelo
        nfs_modelo = buscar_nfs_itens_sem_modelo()
        print(f"\n--- PARTE 2: {len(nfs_modelo)} NF(s) com itens sem modelo_moto_id ---")

        total_desc_atualizadas = 0
        total_motos_p2 = 0

        for nf_row in nfs_modelo:
            print(f"\n  NF {nf_row.id} | #{nf_row.numero_nf} | {nf_row.nome_emitente}")
            res = reprocessar_nf(nf_row, storage, dry_run=dry_run)

            if res['erro']:
                print(f"    [ERRO] {res['erro']}")
            else:
                print(f"    Desc atualizadas: {res['desc_atualizadas']}, "
                      f"Motos detectadas: {res['motos_detectadas']}")
                total_desc_atualizadas += res['desc_atualizadas']
                total_motos_p2 += res['motos_detectadas']

        # Commit
        if not dry_run:
            db.session.commit()
            print(f"\n[COMMIT] Transacao salva com sucesso!")

        print(f"\n{'=' * 70}")
        print(f"RESUMO:")
        print(f"  Parte 1: {total_inseridos} itens inseridos, {total_motos} motos detectadas")
        print(f"  Parte 2: {total_desc_atualizadas} descricoes atualizadas, {total_motos_p2} motos detectadas")
        print(f"  Modo: {'DRY RUN (nada salvo)' if dry_run else 'EXECUTADO'}")
        print(f"{'=' * 70}")


if __name__ == '__main__':
    main()
