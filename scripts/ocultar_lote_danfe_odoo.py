"""
Ocultar Lotes do DANFE (PDF) no Odoo — NF-e de Venda
=====================================================

OBJETIVO:
    Remover informacoes de lote/rastreabilidade do DANFE (PDF) mantendo no XML.
    O lote aparece no DANFE via infAdProd ("Lote: XXX"), gerado dinamicamente
    pelo CIEL IT a partir dos dados de rastreabilidade (<rastro>).

ABORDAGEM (validada 10/03/2026):
    O CIEL IT gera o DANFE a partir dos dados de invoice/stock.lot, NAO do XML.
    action_gerar_xmldanfe_nfe() REGENERA o XML inteiro a partir dos dados.
    Nao existe config CIEL IT para ocultar lote.

    Solucao: Pos-processamento do PDF com PyMuPDF (fitz):
    1. Ler o PDF do DANFE (l10n_br_pdf_aut_nfe)
    2. Localizar texto "Lote: XXX" via fitz.search_for()
    3. Aplicar redacao real (fitz.add_redact_annot + apply_redactions)
    4. Gravar PDF redactado de volta no Odoo

    A redacao PyMuPDF REMOVE o texto do content stream (nao overlay).
    O XML (l10n_br_xml_aut_nfe) NAO e tocado — <rastro> permanece intacto.

ACOES:
    --acao verificar      -> Mostra estado atual de configs e invoice
    --acao redactar       -> Redacta lote do DANFE de uma invoice especifica
    --acao redactar-batch -> Redacta lote das ultimas N invoices autorizadas

FLAGS:
    --dry-run             -> Mostra o que faria sem executar
    --invoice-id ID       -> Invoice especifica (para redactar)
    --limit N             -> Limite de invoices no batch (default: 10)
    --salvar-local        -> Salvar PDF em /tmp (sem gravar no Odoo)

DEPENDENCIAS:
    PyMuPDF (fitz) >= 1.24.0 — pip install PyMuPDF

VERIFICACAO:
    python scripts/verificar_danfe_sem_lote.py --invoice-id <id> --salvar-pdf

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

import fitz  # noqa: E402 — PyMuPDF

from app import create_app  # noqa: E402
from app.odoo.utils.connection import get_odoo_connection  # noqa: E402

# IDs e constantes
SERVER_ACTION_DANFE_ID = 874
CONFIG_IMPRIMIR_VALIDADE = 'l10n_br_ciel_it_account.imprimir_validade_danfe'
CONFIG_QTY_LOT_XML = 'l10n_br_ciel_it_account.qty_lot_xml_nfe'

# Regex para localizar "Lote: XXX" no texto extraido do PDF
LOTE_PATTERN = re.compile(r'Lote:\s*\S+', re.IGNORECASE)

# Margem extra (pontos) para expandir a area de redacao alem do texto encontrado
# Cobre o valor do lote que vem apos "Lote:"
REDACT_EXPAND_RIGHT = 150


def _redactar_pdf_lote(pdf_bytes):
    """
    Redacta texto "Lote: XXX" do PDF usando PyMuPDF.
    A redacao remove o texto do content stream (nao e overlay).

    Args:
        pdf_bytes: bytes do PDF original

    Returns:
        (pdf_redactado_bytes, n_redactados) ou (None, 0) se nada a redactar
    """
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    n_redacted = 0
    pages_redacted = []

    for page_num, page in enumerate(doc):
        # Buscar "Lote:" no texto da pagina
        instances = page.search_for("Lote:")

        if not instances:
            continue

        page_count = 0
        for rect in instances:
            # Expandir retangulo para cobrir o valor do lote (ex: "134/25", "MIGRACAO")
            expanded = fitz.Rect(
                rect.x0 - 1,      # margem esquerda minima
                rect.y0 - 1,      # margem superior minima
                rect.x1 + REDACT_EXPAND_RIGHT,  # cobrir valor do lote
                rect.y1 + 1,      # margem inferior minima
            )

            # Extrair texto na area para confirmar e logar
            text_in_area = page.get_text("text", clip=expanded).strip()

            # Adicionar anotacao de redacao (preenchimento branco)
            page.add_redact_annot(expanded, fill=(1, 1, 1))
            n_redacted += 1
            page_count += 1
            print(f"     Pag {page_num + 1}: redactado '{text_in_area}'")

        # Aplicar redacoes da pagina
        if page_count > 0:
            page.apply_redactions()
            pages_redacted.append(page_num + 1)

    if n_redacted == 0:
        doc.close()
        return None, 0

    # Salvar PDF redactado em memoria
    output = BytesIO()
    doc.save(output, garbage=4, deflate=True)
    doc.close()

    return output.getvalue(), n_redacted


def _verificar_pdf_tem_lote(pdf_bytes):
    """
    Verifica se o PDF contem texto "Lote:" via PyMuPDF.
    Retorna lista de textos encontrados.
    """
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    encontrados = []

    for page_num, page in enumerate(doc):
        text = page.get_text()
        for line in text.split('\n'):
            if LOTE_PATTERN.search(line):
                encontrados.append((page_num + 1, line.strip()))

    doc.close()
    return encontrados


def _verificar_xml_tem_rastro(xml_bytes):
    """Verifica se o XML contem elementos <rastro> e retorna detalhes."""
    xml_str = xml_bytes.decode('utf-8')
    # Tags podem ter namespace prefix (ex: <nfe:nLot> ou <nLot>)
    rastros = re.findall(
        r'<(?:\w+:)?nLot>([^<]*)</(?:\w+:)?nLot>.*?'
        r'<(?:\w+:)?qLot>([^<]*)</(?:\w+:)?qLot>',
        xml_str, re.DOTALL,
    )
    # Fallback: contar tags <rastro> se regex acima nao encontrar
    if not rastros:
        count = len(re.findall(r'<(?:\w+:)?rastro\b', xml_str))
        if count > 0:
            return [(f'(tag #{i+1})', '?') for i in range(count)]
    return rastros


def acao_verificar(odoo, invoice_id=None):
    """Mostra estado atual de configs e opcionalmente verifica uma invoice"""
    print("\n" + "=" * 80)
    print("VERIFICACAO — Estado Atual")
    print("=" * 80)

    # 1. Configs CIEL IT
    configs_check = [
        (CONFIG_IMPRIMIR_VALIDADE, 'imprimir_validade_danfe'),
        (CONFIG_QTY_LOT_XML, 'qty_lot_xml_nfe'),
    ]

    print(f"\n   Configs CIEL IT:")
    for key, label in configs_check:
        result = odoo.search_read(
            'ir.config_parameter',
            [['key', '=', key]],
            fields=['value'],
        )
        valor = result[0]['value'] if result else 'NAO EXISTE'
        print(f"     {label}: {valor}")

    # 2. Server action 874
    action = odoo.read('ir.actions.server', [SERVER_ACTION_DANFE_ID],
                       fields=['id', 'name', 'code'])
    if action:
        action = action[0]
        code = (action.get('code') or '').strip()
        print(f"\n   Server Action {SERVER_ACTION_DANFE_ID}:")
        print(f"     Nome: {action['name']}")
        print(f"     Codigo: {code[:80]}")

    # 3. Invoice especifica (se informada)
    if invoice_id:
        print(f"\n   Invoice {invoice_id}:")
        inv = odoo.read('account.move', [invoice_id], fields=[
            'name', 'l10n_br_situacao_nf',
            'l10n_br_xml_aut_nfe', 'l10n_br_pdf_aut_nfe',
        ])
        if not inv:
            print(f"     NAO ENCONTRADA")
            return

        inv = inv[0]
        print(f"     Nome: {inv['name']}")
        print(f"     Situacao: {inv.get('l10n_br_situacao_nf')}")

        pdf_b64 = inv.get('l10n_br_pdf_aut_nfe')
        xml_b64 = inv.get('l10n_br_xml_aut_nfe')

        if pdf_b64:
            pdf_bytes = base64.b64decode(pdf_b64)
            print(f"     PDF: {len(pdf_bytes)} bytes")
            lotes = _verificar_pdf_tem_lote(pdf_bytes)
            if lotes:
                print(f"     DANFE contem {len(lotes)} linhas com 'Lote:':")
                for pag, texto in lotes:
                    print(f"       Pag {pag}: {texto}")
            else:
                print(f"     DANFE: LIMPO (sem 'Lote:')")
        else:
            print(f"     PDF: AUSENTE")

        if xml_b64:
            xml_bytes = base64.b64decode(xml_b64)
            print(f"     XML: {len(xml_bytes)} bytes")
            rastros = _verificar_xml_tem_rastro(xml_bytes)
            if rastros:
                print(f"     XML contem {len(rastros)} <rastro>:")
                for nlot, qlot in rastros:
                    print(f"       Lote={nlot}, Qtd={qlot}")
            else:
                print(f"     XML: sem <rastro>")
        else:
            print(f"     XML: AUSENTE")

    print()


def acao_redactar(odoo, invoice_id, dry_run=False, salvar_local=False):
    """
    Redacta "Lote: XXX" do DANFE via PyMuPDF.

    Abordagem:
    1. Le PDF (l10n_br_pdf_aut_nfe) da invoice
    2. Localiza texto "Lote:" com fitz.search_for()
    3. Aplica redacao real (remove texto do content stream)
    4. Grava PDF redactado de volta (ou salva localmente se --salvar-local)

    O XML NAO e tocado — <rastro> permanece intacto.
    """
    print("\n" + "=" * 80)
    print(f"REDACTAR LOTE — Invoice {invoice_id}")
    print("=" * 80)

    # Ler invoice
    inv = odoo.read('account.move', [invoice_id], fields=[
        'id', 'name', 'l10n_br_situacao_nf',
        'l10n_br_pdf_aut_nfe',
    ])

    if not inv:
        print(f"\n   Invoice {invoice_id} nao encontrada")
        return False

    inv = inv[0]
    print(f"\n   Invoice: {inv['name']} (ID={invoice_id})")
    print(f"   Situacao: {inv.get('l10n_br_situacao_nf')}")

    if inv.get('l10n_br_situacao_nf') != 'autorizado':
        print(f"   NF-e nao autorizada — so processa NF-e autorizadas")
        return False

    pdf_b64 = inv.get('l10n_br_pdf_aut_nfe')
    if not pdf_b64:
        print(f"   Sem PDF — nada a fazer")
        return False

    # Decodar PDF
    pdf_bytes = base64.b64decode(pdf_b64)
    print(f"   PDF original: {len(pdf_bytes)} bytes")

    # Verificar se tem "Lote:" no PDF
    lotes = _verificar_pdf_tem_lote(pdf_bytes)
    if not lotes:
        print(f"   Nenhum 'Lote:' encontrado no DANFE — nada a fazer")
        return True  # Sucesso (ja limpo)

    print(f"   Encontrados {len(lotes)} 'Lote:' no DANFE:")
    for pag, texto in lotes:
        print(f"     Pag {pag}: {texto}")

    if dry_run:
        print(f"\n   [DRY-RUN] {len(lotes)} 'Lote:' seriam redactados")
        return True

    # Redactar
    print(f"\n   Aplicando redacao PyMuPDF...")
    pdf_redactado, n_redactados = _redactar_pdf_lote(pdf_bytes)

    if not pdf_redactado:
        print(f"   ERRO: Redacao nao retornou PDF")
        return False

    print(f"   PDF redactado: {len(pdf_redactado)} bytes ({len(pdf_redactado)/len(pdf_bytes):.2f}x)")

    # Verificar resultado
    lotes_pos = _verificar_pdf_tem_lote(pdf_redactado)
    if lotes_pos:
        print(f"   AVISO: PDF redactado ainda contem {len(lotes_pos)} 'Lote:':")
        for pag, texto in lotes_pos:
            print(f"     Pag {pag}: {texto}")
    else:
        print(f"   Verificacao: PDF LIMPO")

    # Salvar localmente se solicitado
    if salvar_local:
        path = f"/tmp/danfe_sem_lote_{invoice_id}.pdf"
        with open(path, 'wb') as f:
            f.write(pdf_redactado)
        print(f"   PDF salvo localmente: {path}")

    # Gravar no Odoo (se nao for apenas local)
    if not salvar_local:
        pdf_redactado_b64 = base64.b64encode(pdf_redactado).decode('ascii')
        print(f"   Gravando PDF redactado no Odoo...")
        odoo.write('account.move', [invoice_id], {
            'l10n_br_pdf_aut_nfe': pdf_redactado_b64,
        })
        print(f"   PDF atualizado no Odoo com sucesso")

        # Verificacao final — reler do Odoo
        inv_final = odoo.read('account.move', [invoice_id],
                               fields=['l10n_br_pdf_aut_nfe'])
        if inv_final and inv_final[0].get('l10n_br_pdf_aut_nfe'):
            pdf_final = base64.b64decode(inv_final[0]['l10n_br_pdf_aut_nfe'])
            lotes_final = _verificar_pdf_tem_lote(pdf_final)
            if lotes_final:
                print(f"   AVISO: Verificacao final mostra {len(lotes_final)} 'Lote:' restantes!")
            else:
                print(f"   Verificacao final: DANFE no Odoo esta LIMPO")

    # Confirmar XML intacto
    inv_xml = odoo.read('account.move', [invoice_id],
                         fields=['l10n_br_xml_aut_nfe'])
    if inv_xml and inv_xml[0].get('l10n_br_xml_aut_nfe'):
        xml_bytes = base64.b64decode(inv_xml[0]['l10n_br_xml_aut_nfe'])
        rastros = _verificar_xml_tem_rastro(xml_bytes)
        print(f"   XML intacto: {len(rastros)} <rastro> preservados")

    print(f"\n   Resultado: DANFE sem lote + XML com <rastro> intacto")
    return True


def acao_redactar_batch(odoo, limit=10, dry_run=False, salvar_local=False):
    """Redacta lote das ultimas N invoices autorizadas"""
    print("\n" + "=" * 80)
    print(f"REDACTAR BATCH — Ultimas {limit} invoices")
    print("=" * 80)

    # Buscar invoices de venda autorizadas
    invoices = odoo.search_read(
        'account.move',
        [
            ['move_type', '=', 'out_invoice'],
            ['state', '=', 'posted'],
            ['l10n_br_situacao_nf', '=', 'autorizado'],
            ['l10n_br_pdf_aut_nfe', '!=', False],
        ],
        fields=['id', 'name', 'invoice_date'],
        limit=limit,
        order='id desc',
    )

    if not invoices:
        print(f"\n   Nenhuma invoice autorizada com PDF encontrada")
        return

    print(f"\n   Encontradas {len(invoices)} invoices")

    sucesso = 0
    erro = 0
    sem_lote = 0
    ja_limpo = 0

    for inv in invoices:
        print(f"\n   --- {inv['name']} (ID={inv['id']}) ---")
        try:
            resultado = acao_redactar(
                odoo, inv['id'],
                dry_run=dry_run, salvar_local=salvar_local,
            )
            if resultado:
                sucesso += 1
            else:
                sem_lote += 1
        except Exception as e:
            print(f"   ERRO: {e}")
            erro += 1

    print(f"\n" + "=" * 80)
    print(f"   RESUMO BATCH:")
    print(f"     Processadas: {len(invoices)}")
    print(f"     Sucesso: {sucesso}")
    print(f"     Sem lote: {sem_lote}")
    print(f"     Ja limpos: {ja_limpo}")
    print(f"     Erros: {erro}")


def main():
    parser = argparse.ArgumentParser(
        description='Ocultar lotes do DANFE (PDF) no Odoo',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  %(prog)s --acao verificar                                # Ver configs
  %(prog)s --acao verificar --invoice-id 517038            # Ver invoice
  %(prog)s --acao redactar --invoice-id 517038 --dry-run   # Simular
  %(prog)s --acao redactar --invoice-id 517038 --salvar-local  # Testar local
  %(prog)s --acao redactar --invoice-id 517038             # Redactar e gravar
  %(prog)s --acao redactar-batch --limit 5 --dry-run       # Simular batch
  %(prog)s --acao redactar-batch --limit 5                 # Batch
""",
    )
    parser.add_argument(
        '--acao',
        choices=['verificar', 'redactar', 'redactar-batch'],
        required=True,
        help='Acao a executar',
    )
    parser.add_argument('--invoice-id', type=int,
                        help='ID da invoice (para verificar/redactar)')
    parser.add_argument('--limit', type=int, default=10,
                        help='Limite de invoices no batch (default: 10)')
    parser.add_argument('--dry-run', action='store_true',
                        help='Mostrar o que faria sem executar')
    parser.add_argument('--salvar-local', action='store_true',
                        help='Salvar PDF em /tmp (sem gravar no Odoo)')

    args = parser.parse_args()

    dry_run = args.dry_run
    if dry_run:
        print("\n*** MODO DRY-RUN — Nenhuma modificacao sera feita ***\n")

    print("=" * 80)
    print(f"OCULTAR LOTES DO DANFE — Acao: {args.acao.upper()}")
    print("=" * 80)

    app = create_app()

    with app.app_context():
        odoo = get_odoo_connection()

        if args.acao == 'verificar':
            acao_verificar(odoo, args.invoice_id)

        elif args.acao == 'redactar':
            if not args.invoice_id:
                parser.error('--invoice-id e obrigatorio para redactar')
            acao_redactar(odoo, args.invoice_id, dry_run, args.salvar_local)

        elif args.acao == 'redactar-batch':
            acao_redactar_batch(odoo, args.limit, dry_run, args.salvar_local)

    print("\n" + "=" * 80)
    print("CONCLUIDO")
    print("=" * 80)


if __name__ == '__main__':
    main()
