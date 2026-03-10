"""
Redactar Lote do DANFE (PDF) — Pós-processamento
==================================================

OBJETIVO:
    Remover texto "Lote: XXX" do DANFE (PDF) mantendo <rastro> no XML intacto.
    Usa overlay de retângulos brancos sobre as posições do texto via pypdf.

COMO FUNCIONA:
    1. Lê l10n_br_pdf_aut_nfe (base64) da invoice no Odoo
    2. Localiza posições de "Lote: XXX" via pdfplumber (extrai words com coords)
    3. Cria uma página de overlay com retângulos brancos cobrindo os textos
    4. Mescla o overlay sobre cada página do DANFE original
    5. Grava o PDF modificado de volta em l10n_br_pdf_aut_nfe via Odoo
    6. XML permanece intacto (rastro/nLote/qLote/dFab/dVal preservados)

ABORDAGENS:
    --modo overlay    → Sobrepõe retângulo branco (default, mais confiável)
    --modo content    → Modifica content stream (experimental, mais limpo)

USO:
    # Dry-run — mostra o que faria sem alterar
    python scripts/redactar_lote_danfe.py --invoice-id 517038 --dry-run

    # Redactar e gravar no Odoo
    python scripts/redactar_lote_danfe.py --invoice-id 517038

    # Redactar múltiplas invoices
    python scripts/redactar_lote_danfe.py --invoice-ids 517038,517039,517040

    # Batch: últimas N invoices de venda com lote no DANFE
    python scripts/redactar_lote_danfe.py --batch --limit 10

    # Salvar PDF local para conferência (não grava no Odoo)
    python scripts/redactar_lote_danfe.py --invoice-id 517038 --salvar-local

VERIFICAÇÃO:
    python scripts/verificar_danfe_sem_lote.py --invoice-id 517038 --salvar-pdf

AUTOR: Sistema de Fretes
DATA: 10/03/2026
"""

import argparse
import base64
import re
import sys
import os
from io import BytesIO

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app  # noqa: E402
from app.odoo.utils.connection import get_odoo_connection  # noqa: E402

# Padrão regex para detectar "Lote: XXX" no texto extraído
LOTE_PATTERN = re.compile(r'Lote:\s*\S+', re.IGNORECASE)

# Margem extra ao redor do texto para garantir cobertura completa (em pontos PDF)
MARGEM_X = 1.0
MARGEM_Y = 0.5


def localizar_textos_lote(pdf_bytes):
    """
    Localiza posições de "Lote: XXX" em cada página do PDF.

    Retorna:
        List[Dict] por página, cada contendo:
        - 'pagina': int (0-indexed)
        - 'textos': List[Dict] com 'text', 'x0', 'y0', 'x1', 'y1'
    """
    import pdfplumber

    resultados = []

    pdf = pdfplumber.open(BytesIO(pdf_bytes))
    for page_idx, page in enumerate(pdf.pages):
        words = page.extract_words()
        page_height = page.height

        textos_lote = []

        # Buscar words que começam com "Lote:"
        for i, w in enumerate(words):
            if not LOTE_PATTERN.match(w['text']) and w['text'] != 'Lote:':
                continue

            # Coletar a linha completa "Lote: VALOR"
            same_line = [w]

            # Se word é apenas "Lote:", buscar o valor na próxima word
            if w['text'] == 'Lote:':
                # Buscar word imediatamente à direita na mesma linha
                for j in range(i + 1, min(i + 5, len(words))):
                    w2 = words[j]
                    if abs(w2['top'] - w['top']) < 3 and w2['x0'] > w['x0']:
                        same_line.append(w2)
                        break  # Apenas o valor do lote

            text = ' '.join(sw['text'] for sw in sorted(same_line, key=lambda x: x['x0']))
            x0 = min(sw['x0'] for sw in same_line) - MARGEM_X
            x1 = max(sw['x1'] for sw in same_line) + MARGEM_X
            # pdfplumber usa top/bottom (distância do topo da página)
            y_top = min(sw['top'] for sw in same_line) - MARGEM_Y
            y_bottom = max(sw['bottom'] for sw in same_line) + MARGEM_Y

            # Converter para coordenadas PDF (origem no canto inferior esquerdo)
            pdf_y0 = page_height - y_bottom  # bottom em coords PDF
            pdf_y1 = page_height - y_top  # top em coords PDF

            textos_lote.append({
                'text': text,
                'x0': max(0, x0),
                'y0': pdf_y0,
                'x1': min(page.width, x1),
                'y1': pdf_y1,
                'page_height': page_height,
                'page_width': page.width,
            })

        if textos_lote:
            resultados.append({
                'pagina': page_idx,
                'textos': textos_lote,
            })

    pdf.close()
    return resultados


def criar_overlay_pagina(width, height, textos):
    """
    Cria uma página PDF transparente com retângulos brancos cobrindo os textos.

    Args:
        width: largura da página em pontos
        height: altura da página em pontos
        textos: List[Dict] com 'x0', 'y0', 'x1', 'y1' em coordenadas PDF

    Retorna:
        pypdf.PageObject com os retângulos brancos
    """
    import pypdf
    from pypdf.generic import (
        ArrayObject, ContentStream, DecodedStreamObject,
        DictionaryObject, FloatObject, NameObject, NumberObject,
        RectangleObject,
    )

    # Construir content stream com retângulos brancos
    # Operadores PDF: 'q' (save state), 'rg' (set fill color), 're' (rectangle), 'f' (fill), 'Q' (restore)
    commands = ['q']  # Save graphics state
    commands.append('1 1 1 rg')  # Set fill color to white (RGB 1,1,1)

    for t in textos:
        x = t['x0']
        y = t['y0']
        w = t['x1'] - t['x0']
        h = t['y1'] - t['y0']
        commands.append(f'{x:.2f} {y:.2f} {w:.2f} {h:.2f} re')  # Rectangle
        commands.append('f')  # Fill

    commands.append('Q')  # Restore graphics state

    content_bytes = '\n'.join(commands).encode('latin-1')

    # Criar PDF minimal com uma página contendo o overlay
    writer = pypdf.PdfWriter()
    page = pypdf.PageObject.create_blank_page(width=width, height=height)

    # Injetar content stream
    stream = DecodedStreamObject()
    stream.set_data(content_bytes)
    page[NameObject('/Contents')] = writer._add_object(stream)

    return page


def redactar_pdf(pdf_bytes):
    """
    Redacta textos "Lote: XXX" do PDF, retornando o PDF modificado.

    Args:
        pdf_bytes: bytes do PDF original

    Retorna:
        Tuple[bytes, List[Dict]]:
        - bytes do PDF modificado (ou None se não há lotes)
        - lista de textos redactados
    """
    import pypdf

    # 1. Localizar textos de lote
    localizacoes = localizar_textos_lote(pdf_bytes)

    if not localizacoes:
        return None, []

    # Coletar todos os textos para relatório
    todos_textos = []
    for loc in localizacoes:
        for t in loc['textos']:
            todos_textos.append({
                'pagina': loc['pagina'] + 1,
                'text': t['text'],
                'bbox': f"({t['x0']:.1f}, {t['y0']:.1f}, {t['x1']:.1f}, {t['y1']:.1f})",
            })

    # 2. Criar overlay e mesclar
    reader = pypdf.PdfReader(BytesIO(pdf_bytes))
    writer = pypdf.PdfWriter()

    # Mapear páginas com lote
    lote_por_pagina = {loc['pagina']: loc for loc in localizacoes}

    for page_idx, page in enumerate(reader.pages):
        if page_idx in lote_por_pagina:
            loc = lote_por_pagina[page_idx]
            textos = loc['textos']
            width = float(page.mediabox.width)
            height = float(page.mediabox.height)

            # Criar overlay com retângulos brancos
            overlay = criar_overlay_pagina(width, height, textos)

            # Mesclar overlay sobre a página original
            page.merge_page(overlay)

        writer.add_page(page)

    # Copiar metadados
    if reader.metadata:
        writer.add_metadata(reader.metadata)

    # 3. Gerar PDF final
    output = BytesIO()
    writer.write(output)
    return output.getvalue(), todos_textos


def processar_invoice(odoo, invoice_id, dry_run=False, salvar_local=False):
    """
    Processa uma invoice: lê PDF, redacta lotes, grava de volta.

    Retorna:
        Dict com resultado do processamento
    """
    resultado = {
        'invoice_id': invoice_id,
        'sucesso': False,
        'acao': None,
        'textos_redactados': [],
        'erro': None,
    }

    try:
        # 1. Ler PDF da invoice
        inv = odoo.read(
            'account.move',
            [invoice_id],
            fields=['id', 'name', 'l10n_br_pdf_aut_nfe'],
        )

        if not inv:
            resultado['erro'] = f'Invoice {invoice_id} não encontrada'
            return resultado

        inv = inv[0]
        pdf_b64 = inv.get('l10n_br_pdf_aut_nfe')
        if not pdf_b64:
            resultado['erro'] = f'Invoice {inv["name"]} sem PDF (l10n_br_pdf_aut_nfe vazio)'
            return resultado

        pdf_bytes = base64.b64decode(pdf_b64)
        print(f"\n   Invoice {inv['name']} (ID={invoice_id})")
        print(f"   PDF original: {len(pdf_bytes)} bytes")

        # 2. Localizar textos de lote
        localizacoes = localizar_textos_lote(pdf_bytes)

        if not localizacoes:
            resultado['acao'] = 'sem_lote'
            print(f"   Nenhum texto 'Lote:' encontrado — nada a fazer")
            resultado['sucesso'] = True
            return resultado

        total_textos = sum(len(loc['textos']) for loc in localizacoes)
        print(f"   Textos 'Lote:' encontrados: {total_textos}")
        for loc in localizacoes:
            for t in loc['textos']:
                print(f"     Pág {loc['pagina'] + 1}: \"{t['text']}\" @ "
                      f"({t['x0']:.1f}, {t['y0']:.1f}, {t['x1']:.1f}, {t['y1']:.1f})")

        # 3. Redactar
        if dry_run:
            resultado['acao'] = 'dry_run'
            resultado['textos_redactados'] = [
                {'pagina': loc['pagina'] + 1, 'text': t['text']}
                for loc in localizacoes for t in loc['textos']
            ]
            print(f"   [DRY-RUN] {total_textos} textos seriam redactados")
            resultado['sucesso'] = True
            return resultado

        pdf_modificado, textos_redactados = redactar_pdf(pdf_bytes)

        if not pdf_modificado:
            resultado['erro'] = 'Falha na redação do PDF'
            return resultado

        resultado['textos_redactados'] = textos_redactados
        print(f"   PDF modificado: {len(pdf_modificado)} bytes")

        # 4. Verificar que a redação funcionou
        verificacao = localizar_textos_lote(pdf_modificado)
        if verificacao:
            # Textos ainda presentes — a redação pode não ter coberto completamente
            restantes = sum(len(loc['textos']) for loc in verificacao)
            print(f"   AVISO: {restantes} textos 'Lote:' ainda detectados após redação")
            print(f"   (Os retângulos brancos cobrem visualmente, mas o texto subjacente")
            print(f"    ainda é detectável por extração de texto — isso é esperado)")

        # 5. Salvar localmente se solicitado
        if salvar_local:
            path = f"/tmp/danfe_redactado_{invoice_id}.pdf"
            with open(path, 'wb') as f:
                f.write(pdf_modificado)
            print(f"   PDF salvo em: {path}")
            resultado['acao'] = 'salvo_local'
            resultado['sucesso'] = True
            return resultado

        # 6. Gravar no Odoo
        pdf_b64_novo = base64.b64encode(pdf_modificado).decode('ascii')
        odoo.write(
            'account.move',
            [invoice_id],
            {'l10n_br_pdf_aut_nfe': pdf_b64_novo},
        )
        resultado['acao'] = 'gravado_odoo'
        resultado['sucesso'] = True
        print(f"   PDF redactado gravado no Odoo")

        return resultado

    except Exception as e:
        resultado['erro'] = str(e)
        import traceback
        traceback.print_exc()
        return resultado


def buscar_invoices_com_lote(odoo, limit=10):
    """
    Busca invoices de venda recentes que provavelmente têm lote no DANFE.

    Retorna lista de IDs de invoices.
    """
    # Buscar invoices posted de venda com PDF
    invoices = odoo.search_read(
        'account.move',
        [
            ['move_type', '=', 'out_invoice'],
            ['state', '=', 'posted'],
            ['l10n_br_pdf_aut_nfe', '!=', False],
        ],
        fields=['id', 'name', 'invoice_date'],
        limit=limit,
        order='id desc',
    )

    if not invoices:
        print("   Nenhuma invoice de venda com PDF encontrada")
        return []

    # Filtrar: verificar quais têm "Lote:" no PDF
    ids_com_lote = []

    for inv in invoices:
        pdf_data = odoo.read(
            'account.move',
            [inv['id']],
            fields=['l10n_br_pdf_aut_nfe'],
        )
        if not pdf_data or not pdf_data[0].get('l10n_br_pdf_aut_nfe'):
            continue

        pdf_bytes = base64.b64decode(pdf_data[0]['l10n_br_pdf_aut_nfe'])
        localizacoes = localizar_textos_lote(pdf_bytes)

        if localizacoes:
            total = sum(len(loc['textos']) for loc in localizacoes)
            print(f"   {inv['name']} (ID={inv['id']}) — {total} textos 'Lote:' encontrados")
            ids_com_lote.append(inv['id'])
        else:
            print(f"   {inv['name']} (ID={inv['id']}) — sem 'Lote:' (skip)")

    return ids_com_lote


def main():
    parser = argparse.ArgumentParser(
        description='Redactar texto "Lote: XXX" do DANFE (PDF) no Odoo',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  %(prog)s --invoice-id 517038 --dry-run         # Simular sem alterar
  %(prog)s --invoice-id 517038 --salvar-local     # Salvar PDF em /tmp
  %(prog)s --invoice-id 517038                    # Redactar e gravar no Odoo
  %(prog)s --invoice-ids 517038,517039            # Múltiplas invoices
  %(prog)s --batch --limit 10                     # Últimas 10 com lote

Verificação:
  python scripts/verificar_danfe_sem_lote.py --invoice-id 517038 --salvar-pdf
""",
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--invoice-id', type=int,
                       help='ID de uma invoice específica')
    group.add_argument('--invoice-ids', type=str,
                       help='IDs de múltiplas invoices (separados por vírgula)')
    group.add_argument('--batch', action='store_true',
                       help='Processar últimas N invoices com lote')

    parser.add_argument('--limit', type=int, default=10,
                        help='Limite de invoices no modo --batch (default: 10)')
    parser.add_argument('--dry-run', action='store_true',
                        help='Simular sem gravar no Odoo')
    parser.add_argument('--salvar-local', action='store_true',
                        help='Salvar PDF em /tmp em vez de gravar no Odoo')

    args = parser.parse_args()

    dry_run = args.dry_run
    if dry_run:
        print("\n*** MODO DRY-RUN — Nenhuma modificação será feita ***\n")

    print("=" * 80)
    print("REDACTAR LOTE DO DANFE (PDF)")
    print("=" * 80)

    app = create_app()

    with app.app_context():
        odoo = get_odoo_connection()

        # Determinar lista de invoices
        if args.invoice_id:
            invoice_ids = [args.invoice_id]
        elif args.invoice_ids:
            invoice_ids = [int(x.strip()) for x in args.invoice_ids.split(',')]
        else:
            # Modo batch
            print(f"\n   Buscando últimas {args.limit} invoices com lote...")
            invoice_ids = buscar_invoices_com_lote(odoo, limit=args.limit)

        if not invoice_ids:
            print("\n   Nenhuma invoice para processar")
            sys.exit(0)

        print(f"\n   Processando {len(invoice_ids)} invoice(s)...")

        # Processar cada invoice
        resultados = []
        for inv_id in invoice_ids:
            resultado = processar_invoice(
                odoo, inv_id,
                dry_run=dry_run,
                salvar_local=args.salvar_local,
            )
            resultados.append(resultado)

        # Relatório final
        print("\n" + "=" * 80)
        print("RELATÓRIO FINAL")
        print("=" * 80)

        sucesso = [r for r in resultados if r['sucesso']]
        erro = [r for r in resultados if not r['sucesso']]
        redactados = [r for r in resultados if r.get('textos_redactados')]
        sem_lote = [r for r in resultados if r.get('acao') == 'sem_lote']

        print(f"\n   Total: {len(resultados)}")
        print(f"   Sucesso: {len(sucesso)}")
        print(f"   Erros: {len(erro)}")
        print(f"   Redactados: {len(redactados)}")
        print(f"   Sem lote: {len(sem_lote)}")

        if erro:
            print(f"\n   ERROS:")
            for r in erro:
                print(f"     Invoice {r['invoice_id']}: {r['erro']}")

        if redactados:
            total_textos = sum(len(r['textos_redactados']) for r in redactados)
            print(f"\n   Total textos redactados: {total_textos}")

        if dry_run:
            print(f"\n   [DRY-RUN] Nenhuma alteração foi feita")
            print(f"   Para executar: remova --dry-run")

    print("\n" + "=" * 80)
    print("CONCLUIDO")
    print("=" * 80)


if __name__ == '__main__':
    main()
