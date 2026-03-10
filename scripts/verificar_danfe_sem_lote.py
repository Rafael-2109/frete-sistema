"""
Verificar DANFE Sem Lote — Validação Antes/Depois
==================================================

OBJETIVO:
    Verificar se o DANFE (PDF) de uma NF-e de venda NÃO contém informações
    de lote, enquanto o XML mantém os dados de rastreabilidade (<rastro>).

USO:
    python scripts/verificar_danfe_sem_lote.py
    python scripts/verificar_danfe_sem_lote.py --invoice-id 12345
    python scripts/verificar_danfe_sem_lote.py --dfe-id 67890
    python scripts/verificar_danfe_sem_lote.py --salvar-pdf  # Salva PDF em /tmp

AUTOR: Sistema de Fretes
DATA: 09/03/2026
"""

import argparse
import sys
import os
import base64
import json
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app  # noqa: E402
from app.odoo.utils.connection import get_odoo_connection  # noqa: E402

# Keywords que indicam dados de lote no DANFE PDF
LOTE_KEYWORDS_PDF = [
    'lote', 'nlote', 'qlote', 'dfab', 'dval',
    'rastreabilidade', 'rastro', 'validade',
    'data fabricação', 'data fabricacao',
]

# Namespace da NF-e para parsear XML
NFE_NS = {'nfe': 'http://www.portalfiscal.inf.br/nfe'}


def encontrar_dfe_venda(odoo, invoice_id=None, dfe_id=None):
    """Encontra um DFe de venda para verificação"""
    if dfe_id:
        dfe = odoo.read(
            'l10n_br_ciel_it_account.dfe',
            [dfe_id],
            fields=['id', 'name', 'l10n_br_pdf_dfe', 'l10n_br_xml_dfe',
                    'nfe_infnfe_ide_nnf', 'l10n_br_tipo_pedido',
                    'protnfe_infnfe_chnfe', 'l10n_br_status'],
        )
        return dfe[0] if dfe else None

    if invoice_id:
        # Buscar campos DFe na invoice
        campos_move = odoo.execute_kw(
            'account.move',
            'fields_get',
            [],
            {'attributes': ['type']},
        )
        campos_dfe = [k for k in campos_move if 'dfe' in k.lower() and campos_move[k]['type'] in ('many2one', 'integer')]
        if campos_dfe:
            inv = odoo.read('account.move', [invoice_id], fields=campos_dfe + ['name'])
            if inv:
                for campo in campos_dfe:
                    val = inv[0].get(campo)
                    if val:
                        dfe_id_resolved = val[0] if isinstance(val, (list, tuple)) else val
                        print(f"   DFe via invoice campo {campo}: ID={dfe_id_resolved}")
                        return encontrar_dfe_venda(odoo, dfe_id=dfe_id_resolved)

    # Fallback: buscar DFe de venda recente
    print("   Buscando DFe de venda recente...")
    dfes = odoo.search_read(
        'l10n_br_ciel_it_account.dfe',
        [['l10n_br_tipo_pedido', '=', 'venda']],
        fields=['id', 'name', 'l10n_br_pdf_dfe', 'l10n_br_xml_dfe',
                'nfe_infnfe_ide_nnf', 'l10n_br_tipo_pedido',
                'protnfe_infnfe_chnfe', 'l10n_br_status'],
        limit=5,
        order='id desc',
    )

    if not dfes:
        # Tentar qualquer DFe com PDF
        print("   Nenhum DFe de venda. Buscando qualquer DFe com PDF...")
        dfes = odoo.search_read(
            'l10n_br_ciel_it_account.dfe',
            [['l10n_br_pdf_dfe', '!=', False]],
            fields=['id', 'name', 'l10n_br_pdf_dfe', 'l10n_br_xml_dfe',
                    'nfe_infnfe_ide_nnf', 'l10n_br_tipo_pedido',
                    'protnfe_infnfe_chnfe', 'l10n_br_status'],
            limit=5,
            order='id desc',
        )

    if dfes:
        # Preferir um que tenha PDF E XML
        for dfe in dfes:
            if dfe.get('l10n_br_pdf_dfe') and dfe.get('l10n_br_xml_dfe'):
                return dfe
        # Se nenhum tem ambos, retornar o primeiro com PDF
        for dfe in dfes:
            if dfe.get('l10n_br_pdf_dfe'):
                return dfe
        return dfes[0]

    return None


def verificar_pdf(pdf_bytes):
    """Analisa PDF do DANFE buscando keywords de lote"""
    try:
        import pypdf
    except ImportError:
        print("   ERRO: pypdf não instalado. Execute: pip install pypdf")
        return None

    from io import BytesIO

    reader = pypdf.PdfReader(BytesIO(pdf_bytes))
    resultado = {
        'paginas': len(reader.pages),
        'tem_lote': False,
        'keywords_encontradas': [],
        'linhas_lote': [],
    }

    for i, page in enumerate(reader.pages):
        texto = page.extract_text() or ''
        texto_lower = texto.lower()

        for kw in LOTE_KEYWORDS_PDF:
            if kw in texto_lower:
                if kw not in resultado['keywords_encontradas']:
                    resultado['keywords_encontradas'].append(kw)
                resultado['tem_lote'] = True

                # Capturar linhas que contêm a keyword
                for linha in texto.split('\n'):
                    if kw in linha.lower() and linha.strip():
                        resultado['linhas_lote'].append({
                            'pagina': i + 1,
                            'keyword': kw,
                            'linha': linha.strip(),
                        })

    return resultado


def verificar_xml(xml_bytes):
    """Analisa XML da NF-e buscando elementos <rastro>"""
    resultado = {
        'tem_rastro': False,
        'rastros': [],
        'total_itens': 0,
        'itens_com_rastro': 0,
    }

    try:
        # Tentar parsear como XML
        xml_str = xml_bytes.decode('utf-8') if isinstance(xml_bytes, bytes) else xml_bytes

        # Remover possível BOM
        if xml_str.startswith('\ufeff'):
            xml_str = xml_str[1:]

        root = ET.fromstring(xml_str)

        # Buscar <det> (itens) e <rastro> dentro deles
        # Tentar com namespace e sem namespace
        for ns_prefix in [NFE_NS, {}]:
            ns = ns_prefix.get('nfe', '')
            prefix = f'{{{ns}}}' if ns else ''

            dets = root.iter(f'{prefix}det')
            for det in dets:
                resultado['total_itens'] += 1
                prod = det.find(f'{prefix}prod')

                rastros = det.findall(f'.//{prefix}rastro')
                if not rastros and prod is not None:
                    rastros = prod.findall(f'{prefix}rastro')

                if rastros:
                    resultado['itens_com_rastro'] += 1
                    resultado['tem_rastro'] = True
                    for rastro in rastros:
                        info = {}
                        for campo in ['nLote', 'qLote', 'dFab', 'dVal']:
                            elem = rastro.find(f'{prefix}{campo}')
                            if elem is not None:
                                info[campo] = elem.text
                        xprod = prod.find(f'{prefix}xProd') if prod is not None else None
                        info['produto'] = xprod.text if xprod is not None else '?'
                        resultado['rastros'].append(info)

            if resultado['total_itens'] > 0:
                break  # Encontrou com este namespace

        # Se não encontrou com namespace, tentar busca textual
        if resultado['total_itens'] == 0:
            if '<rastro>' in xml_str or '<nfe:rastro>' in xml_str:
                resultado['tem_rastro'] = True
                resultado['rastros'].append({'nota': 'Encontrado via busca textual'})

    except ET.ParseError as e:
        print(f"   AVISO: Erro ao parsear XML: {e}")
        # Fallback: busca textual
        xml_text = xml_bytes.decode('utf-8', errors='replace') if isinstance(xml_bytes, bytes) else xml_bytes
        if '<rastro>' in xml_text or 'nLote' in xml_text:
            resultado['tem_rastro'] = True
            resultado['rastros'].append({'nota': 'Encontrado via busca textual (XML malformado)'})

    return resultado


def main():
    parser = argparse.ArgumentParser(
        description='Verificar se DANFE não tem lote e XML mantém rastro',
    )
    parser.add_argument('--invoice-id', type=int, help='ID da invoice')
    parser.add_argument('--dfe-id', type=int, help='ID do DFe')
    parser.add_argument('--salvar-pdf', action='store_true',
                        help='Salvar PDF em /tmp para inspeção manual')
    args = parser.parse_args()

    print("=" * 80)
    print("VERIFICAÇÃO — DANFE SEM LOTE / XML COM RASTRO")
    print("=" * 80)

    app = create_app()

    with app.app_context():
        odoo = get_odoo_connection()

        pdf_base64 = None
        xml_base64 = None
        fonte = None
        ref_id = None
        ref_nome = None

        # 1. Buscar fonte de PDF/XML
        print("\n1. Buscando DANFE e XML...")

        if args.invoice_id:
            # Ler diretamente do account.move (NF-e de venda usa estes campos)
            inv = odoo.read(
                'account.move',
                [args.invoice_id],
                fields=['id', 'name', 'move_type',
                        'l10n_br_pdf_aut_nfe', 'l10n_br_xml_aut_nfe',
                        'l10n_br_pdf_aut_nfe_fname', 'l10n_br_xml_aut_nfe_fname'],
            )
            if inv and (inv[0].get('l10n_br_pdf_aut_nfe') or inv[0].get('l10n_br_xml_aut_nfe')):
                pdf_base64 = inv[0].get('l10n_br_pdf_aut_nfe')
                xml_base64 = inv[0].get('l10n_br_xml_aut_nfe')
                fonte = 'account.move'
                ref_id = inv[0]['id']
                ref_nome = inv[0].get('name')
                print(f"   Fonte: account.move ID={ref_id} ({ref_nome})")
                print(f"   Tipo: {inv[0].get('move_type')}")
                print(f"   PDF: {'SIM' if pdf_base64 else 'NAO'} ({inv[0].get('l10n_br_pdf_aut_nfe_fname', '')})")
                print(f"   XML: {'SIM' if xml_base64 else 'NAO'} ({inv[0].get('l10n_br_xml_aut_nfe_fname', '')})")
            else:
                print(f"   Invoice {args.invoice_id} sem PDF/XML direto. Tentando via DFe...")

        if not pdf_base64 and not xml_base64:
            # Fallback: buscar via DFe
            dfe = encontrar_dfe_venda(odoo, invoice_id=args.invoice_id, dfe_id=args.dfe_id)
            if not dfe:
                print("\n   ERRO: Nenhuma fonte de PDF/XML encontrada!")
                sys.exit(1)

            pdf_base64 = dfe.get('l10n_br_pdf_dfe')
            xml_base64 = dfe.get('l10n_br_xml_dfe')
            fonte = 'l10n_br_ciel_it_account.dfe'
            ref_id = dfe['id']
            ref_nome = dfe.get('nfe_infnfe_ide_nnf')
            print(f"   Fonte: DFe ID={ref_id} | NF={ref_nome}")
            print(f"   Tipo: {dfe.get('l10n_br_tipo_pedido')} | Status: {dfe.get('l10n_br_status')}")
            print(f"   Chave: {dfe.get('protnfe_infnfe_chnfe')}")
            print(f"   PDF: {'SIM' if pdf_base64 else 'NAO'}")
            print(f"   XML: {'SIM' if xml_base64 else 'NAO'}")

        # 2. Verificar PDF (DANFE)
        print("\n" + "-" * 60)
        print("2. Analisando DANFE (PDF)...")
        print("-" * 60)

        resultado_pdf = None
        if pdf_base64:
            pdf_bytes = base64.b64decode(pdf_base64)
            print(f"   PDF: {len(pdf_bytes)} bytes")

            if args.salvar_pdf:
                path = f"/tmp/danfe_{fonte.replace('.', '_')}_{ref_id}.pdf"
                with open(path, 'wb') as f:
                    f.write(pdf_bytes)
                print(f"   PDF salvo em: {path}")

            resultado_pdf = verificar_pdf(pdf_bytes)

            if resultado_pdf:
                print(f"   Páginas: {resultado_pdf['paginas']}")
                if resultado_pdf['tem_lote']:
                    print(f"   DANFE CONTÉM LOTE!")
                    print(f"   Keywords: {resultado_pdf['keywords_encontradas']}")
                    for item in resultado_pdf['linhas_lote'][:10]:
                        print(f"      Pág {item['pagina']} [{item['keyword']}]: {item['linha']}")
                else:
                    print(f"   DANFE NÃO CONTÉM LOTE (OK)")
        else:
            print("   PDF não disponível")

        # 3. Verificar XML
        print("\n" + "-" * 60)
        print("3. Analisando XML da NF-e...")
        print("-" * 60)

        resultado_xml = None
        if xml_base64:
            xml_bytes = base64.b64decode(xml_base64)
            print(f"   XML: {len(xml_bytes)} bytes")

            resultado_xml = verificar_xml(xml_bytes)

            if resultado_xml:
                print(f"   Total itens: {resultado_xml['total_itens']}")
                print(f"   Itens com rastro: {resultado_xml['itens_com_rastro']}")
                if resultado_xml['tem_rastro']:
                    print(f"   XML CONTÉM <rastro> (OK)")
                    for r in resultado_xml['rastros'][:10]:
                        if 'nLote' in r:
                            print(f"      Lote={r.get('nLote')} | Qtd={r.get('qLote')} | "
                                  f"Fab={r.get('dFab')} | Val={r.get('dVal')} | "
                                  f"Produto={r.get('produto', '?')}")
                        elif 'nota' in r:
                            print(f"      {r['nota']}")
                else:
                    print(f"   XML NÃO CONTÉM <rastro>")
        else:
            print("   XML não disponível no DFe")

        # 4. Resultado final
        print("\n" + "=" * 80)
        print("RESULTADO FINAL")
        print("=" * 80)

        danfe_tem_lote = resultado_pdf['tem_lote'] if resultado_pdf else None
        xml_tem_rastro = resultado_xml['tem_rastro'] if resultado_xml else None

        resultado_final = {
            'fonte': fonte,
            'ref_id': ref_id,
            'ref_nome': ref_nome,
            'danfe_tem_lote': danfe_tem_lote,
            'xml_tem_rastro': xml_tem_rastro,
        }

        print(f"\n   {json.dumps(resultado_final, indent=4, ensure_ascii=False)}")

        if danfe_tem_lote is False and xml_tem_rastro is True:
            print("\n   SUCESSO: DANFE sem lote + XML com rastro")
        elif danfe_tem_lote is True and xml_tem_rastro is True:
            print("\n   PENDENTE: DANFE ainda contém lote — override não aplicado ou insuficiente")
        elif danfe_tem_lote is None:
            print("\n   INCONCLUSIVO: PDF não disponível para análise")
        elif xml_tem_rastro is None:
            print("\n   INCONCLUSIVO: XML não disponível para análise")
        elif xml_tem_rastro is False:
            print("\n   ATENÇÃO: XML não contém <rastro> — produtos podem não ter tracking")

    print("\n" + "=" * 80)


if __name__ == '__main__':
    main()
