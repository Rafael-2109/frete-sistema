"""
Diagnostica por que CTeXMLParser.get_impostos() retorna aliquota_icms=None
para operacoes CarVia antigas.

Baixa o XML do S3, imprime o bloco <imp>...</imp> (e blocos relacionados),
roda o parser e mostra o resultado final.

Uso:
    python scripts/debug_cte_xml_impostos.py [op_id]

    op_id default = 63 (CE-014, CAR-59-1). Pode passar qualquer id.
"""
import os
import re
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


def inspecionar(op_id):
    from app import create_app, db
    from app.carvia.models import CarviaOperacao
    from app.utils.file_storage import get_file_storage
    from app.carvia.services.parsers.cte_xml_parser_carvia import (
        CTeXMLParserCarvia,
    )

    app = create_app()
    with app.app_context():
        op = db.session.get(CarviaOperacao, op_id)
        if not op:
            print(f"[ERRO] Operacao {op_id} nao encontrada")
            return

        print("=" * 70)
        print(f"Operacao id={op_id}")
        print(f"  CTRC:           {op.ctrc_numero}")
        print(f"  icms_aliquota:  {op.icms_aliquota}")
        print(f"  cte_xml_path:   {op.cte_xml_path}")
        print("=" * 70)

        storage = get_file_storage()
        xml_bytes = storage.download_file(op.cte_xml_path)
        if not xml_bytes:
            print("[ERRO] Nao conseguiu baixar XML do S3")
            return

        xml_str = xml_bytes.decode('utf-8', errors='replace')
        print(f"XML size: {len(xml_str)} chars\n")

        # 1. Extrai bloco <imp>...</imp> completo
        match_imp = re.search(r'<imp\b.*?</imp>', xml_str, re.DOTALL)
        if match_imp:
            print("=== BLOCO <imp> ===")
            bloco = match_imp.group(0)
            # Limita a 4000 chars para nao poluir muito
            print(bloco[:4000])
            if len(bloco) > 4000:
                print(f"\n... (truncado, total {len(bloco)} chars) ...")
        else:
            print("!! <imp> NAO encontrado no XML")

        # 2. Lista TODAS as tags que contem 'ICMS' (case-insensitive)
        print("\n=== Tags com 'ICMS' (case-insensitive) ===")
        tags_icms = sorted(set(
            re.findall(r'<(\w*[Ii][Cc][Mm][Ss]\w*)', xml_str)
        ))
        for t in tags_icms:
            # Conta ocorrencias (abertura)
            count = len(re.findall(rf'<{re.escape(t)}\b', xml_str))
            print(f"  <{t}> (x{count})")

        # 3. Extrai todos os <vICMS*>, <pICMS*>, <vBC*> com valor
        print("\n=== Valores numericos de ICMS encontrados ===")
        for padrao in [
            r'<v[A-Z][a-zA-Z]*ICMS\w*>([^<]+)</v[A-Z][a-zA-Z]*ICMS\w*>',
            r'<p[A-Z][a-zA-Z]*ICMS\w*>([^<]+)</p[A-Z][a-zA-Z]*ICMS\w*>',
            r'<vICMS\b[^>]*>([^<]+)</vICMS>',
            r'<pICMS\b[^>]*>([^<]+)</pICMS>',
            r'<vBC\b[^>]*>([^<]+)</vBC>',
            r'<vICMSOutraUF>([^<]+)</vICMSOutraUF>',
            r'<pICMSOutraUF>([^<]+)</pICMSOutraUF>',
            r'<vICMSUFFim>([^<]+)</vICMSUFFim>',
            r'<pICMSUFFim>([^<]+)</pICMSUFFim>',
        ]:
            for m in re.finditer(padrao, xml_str):
                # Captura a tag completa do match
                tag_full = xml_str[m.start():m.start()+50].split('>')[0] + '>'
                print(f"  {tag_full} = {m.group(1)}")

        # 4. Tenta outros blocos relacionados a tributos
        print("\n=== Outros blocos relevantes ===")
        for tag_busca in ['vPrest', 'Comp', 'vTotTrib', 'infCTeNorm', 'IBSCBS']:
            matches = re.findall(rf'<{tag_busca}\b[^>]*>', xml_str)
            if matches:
                print(f"  {len(matches)}x <{tag_busca}>")

        # 5. Roda o parser oficial
        print("\n=== Parser CTeXMLParserCarvia.get_impostos() ===")
        parser = CTeXMLParserCarvia(xml_str)
        impostos = parser.get_impostos()
        for k, v in impostos.items():
            print(f"  {k}: {v}")

        # 6. Tipo do CTe
        print("\n=== Metadados do CTe ===")
        print(f"  numero:         {parser.get_numero_cte()}")
        print(f"  cfop:           {parser.get_cfop()}")
        print(f"  natOp:          {parser.get_natureza_operacao()}")
        print(f"  modal:          {parser.get_modal()}")
        print(f"  cst_icms:       {parser.get_situacao_tributaria_icms()}")

        rota = parser.get_dados_rota()
        print(f"  origem:         {rota.get('uf_origem')}/{rota.get('cidade_origem')}")
        print(f"  destino:        {rota.get('uf_destino')}/{rota.get('cidade_destino')}")


if __name__ == '__main__':
    op_id = int(sys.argv[1]) if len(sys.argv) > 1 else 63
    inspecionar(op_id)
