"""
Leitor de Comprovantes de Pagamento de Boleto - SICOOB
======================================================

Extrai informações estruturadas de PDFs de comprovantes de pagamento
gerados pelo Internet Banking do Sicoob.

Dependências:
    pip install pypdfium2 tesserocr pillow

Configuração:
    - Requer dados treinados do Tesseract (por.traineddata)
    - Definir TESSDATA_PREFIX apontando para o diretório com os dados

Uso:
    python scripts/leitor_comprovantes_sicoob.py <caminho_do_pdf>
    python scripts/leitor_comprovantes_sicoob.py comprovantes.pdf --formato json
    python scripts/leitor_comprovantes_sicoob.py comprovantes.pdf --formato csv
"""

import os

# Configurar TESSDATA antes de importar tesserocr
TESSDATA_DIR = os.environ.get(
    'TESSDATA_PREFIX',
    os.path.expanduser('~/tessdata')
)
os.environ['TESSDATA_PREFIX'] = TESSDATA_DIR

import re  # noqa: E402
import json  # noqa: E402
import csv  # noqa: E402
from io import StringIO  # noqa: E402
from dataclasses import dataclass, asdict  # noqa: E402
from typing import Optional  # noqa: E402

import pypdfium2 as pdfium  # noqa: E402
import tesserocr  # noqa: E402
from PIL import Image  # noqa: E402


# ---------------------------------------------------------------------------
# Modelo de dados
# ---------------------------------------------------------------------------

@dataclass
class ComprovanteBoleto:
    """Representa um comprovante de pagamento de boleto SICOOB."""
    # Cabeçalho
    data_comprovante: Optional[str] = None
    cooperativa: Optional[str] = None
    conta: Optional[str] = None
    cliente: Optional[str] = None
    linha_digitavel: Optional[str] = None
    numero_documento: Optional[str] = None
    nosso_numero: Optional[str] = None
    numero_agendamento: Optional[str] = None
    instituicao_emissora: Optional[str] = None
    tipo_documento: Optional[str] = None

    # Beneficiário
    beneficiario_razao_social: Optional[str] = None
    beneficiario_nome_fantasia: Optional[str] = None
    beneficiario_cnpj_cpf: Optional[str] = None

    # Pagador
    pagador_razao_social: Optional[str] = None
    pagador_nome_fantasia: Optional[str] = None
    pagador_cnpj_cpf: Optional[str] = None

    # Datas
    data_realizado: Optional[str] = None
    data_pagamento: Optional[str] = None
    data_vencimento: Optional[str] = None

    # Valores
    valor_documento: Optional[str] = None
    valor_desconto_abatimento: Optional[str] = None
    valor_juros_multa: Optional[str] = None
    valor_pago: Optional[str] = None

    # Status
    situacao: Optional[str] = None
    autenticacao: Optional[str] = None

    # Metadados
    pagina: Optional[int] = None


# ---------------------------------------------------------------------------
# Mapeamento de campos (label OCR → atributo do dataclass)
# ---------------------------------------------------------------------------

# Mapeamento direto: label normalizado → campo do dataclass
MAPEAMENTO_CAMPOS = {
    'cooperativa': 'cooperativa',
    'conta': 'conta',
    'cliente': 'cliente',
    'linha digitavel': 'linha_digitavel',
    'linha digitável': 'linha_digitavel',
    'numero do documento': 'numero_documento',
    'número do documento': 'numero_documento',
    'nosso numero': 'nosso_numero',
    'nosso número': 'nosso_numero',
    'numero do agendamento': 'numero_agendamento',
    'número do agendamento': 'numero_agendamento',
    'instituicao emissora': 'instituicao_emissora',
    'instituição emissora': 'instituicao_emissora',
    'tipo documento': 'tipo_documento',
    'situacao': 'situacao',
    'situação': 'situacao',
    'autenticacao': 'autenticacao',
    'autenticação': 'autenticacao',
}

# Campos que dependem do contexto (seção atual)
# "beneficiario final" mapeia para os MESMOS campos de "beneficiario" — sobrescreve
# automaticamente porque a seção "Beneficiário final" vem DEPOIS no PDF.
CAMPOS_CONTEXTUAIS = {
    'nome/razao social': {
        'beneficiario': 'beneficiario_razao_social',
        'beneficiario final': 'beneficiario_razao_social',
        'pagador': 'pagador_razao_social',
    },
    'nome/razão social': {
        'beneficiario': 'beneficiario_razao_social',
        'beneficiario final': 'beneficiario_razao_social',
        'pagador': 'pagador_razao_social',
    },
    'nome fantasia': {
        'beneficiario': 'beneficiario_nome_fantasia',
        'beneficiario final': 'beneficiario_nome_fantasia',
        'pagador': 'pagador_nome_fantasia',
    },
    'cpf/cnpj': {
        'beneficiario': 'beneficiario_cnpj_cpf',
        'beneficiario final': 'beneficiario_cnpj_cpf',
        'pagador': 'pagador_cnpj_cpf',
    },
}

# Campos de datas
CAMPOS_DATAS = {
    'realizado': 'data_realizado',
    'pagamento': 'data_pagamento',
    'vencimento': 'data_vencimento',
}

# Campos de valores
CAMPOS_VALORES = {
    'documento': 'valor_documento',
    'desconto/abatimento': 'valor_desconto_abatimento',
    'juros/multa': 'valor_juros_multa',
    'pago': 'valor_pago',
}

# Seções que mudam o contexto
# "Beneficiário final" aparece em alguns PDFs (FIDC/cessão) — ao encontrar,
# SOBRESCREVE os campos do beneficiário original (que era o intermediário).
SECOES = {
    'beneficiário', 'beneficiario',
    'beneficiário final', 'beneficiario final',
    'pagador', 'datas', 'valores',
}


# ---------------------------------------------------------------------------
# Funções de extração
# ---------------------------------------------------------------------------

def renderizar_pagina(pdf_path: str, pagina_idx: int, escala: float = 4.0) -> Image.Image:
    """Renderiza uma página do PDF como imagem PIL."""
    pdf = pdfium.PdfDocument(pdf_path)
    page = pdf[pagina_idx]
    bitmap = page.render(scale=escala)
    return bitmap.to_pil()


def extrair_texto_ocr(imagem: Image.Image, idioma: str = 'por') -> str:
    """Executa OCR em uma imagem PIL e retorna o texto."""
    return tesserocr.image_to_text(imagem, lang=idioma)


def normalizar_label(label: str) -> str:
    """Normaliza um label removendo ':' e espaços extras."""
    return label.strip().rstrip(':').strip().lower()


def _detectar_formato(linhas: list[str]) -> str:
    """
    Detecta o formato do OCR.

    Formato A (labels separadas): Labels vêm ANTES do cabeçalho SICOOB,
        valores vêm DEPOIS. OCR leu coluna esquerda toda, depois coluna direita.

    Formato B (inline): Cabeçalho SICOOB vem PRIMEIRO, seguido de linhas
        no formato "Label: Valor". OCR leu da esquerda para direita, linha a linha.
    """
    for i, linha in enumerate(linhas):
        if 'SICOOB - SISTEMA DE COOPERATIVAS' in linha.upper():
            # Se SICOOB aparece nas primeiras 3 linhas → Formato B (inline)
            if i <= 2:
                return 'B'
            # Se aparece mais tarde → Formato A (labels separadas)
            return 'A'
    return 'B'  # fallback


def _parse_formato_a(linhas: list[str], comprovante: ComprovanteBoleto) -> None:
    """
    Parse do Formato A: labels e valores em blocos separados.
    O OCR leu toda a coluna esquerda, depois toda a coluna direita.
    """
    # Encontrar separador (SICOOB - SISTEMA...)
    idx_separador = None
    for i, linha in enumerate(linhas):
        if 'SICOOB - SISTEMA DE COOPERATIVAS' in linha.upper():
            idx_separador = i
            break

    if idx_separador is None:
        return

    bloco_labels_raw = linhas[:idx_separador]
    bloco_valores_raw = linhas[idx_separador:]

    # Filtrar cabeçalho SICOOB dos valores
    valores_inicio = 0
    for i, linha in enumerate(bloco_valores_raw):
        if any(kw in linha.upper() for kw in [
            'SICOOB', 'SISBR', 'COMPROVANTE', 'PAGAMENTO DE BOLETO'
        ]):
            valores_inicio = i + 1
            continue
        else:
            valores_inicio = i
            break

    bloco_valores = bloco_valores_raw[valores_inicio:]

    # Filtrar OUVIDORIA, versão e hora solta
    bloco_valores = [
        v for v in bloco_valores
        if not any(kw in v.upper() for kw in ['OUVIDORIA', 'V1.0'])
        and not re.match(r'^\d{2}:\d{2}:\d{2}$', v.strip())
    ]

    # Processar labels
    labels = []
    for linha in bloco_labels_raw:
        if comprovante.data_comprovante is None and re.match(r'^\d{2}/\d{2}/\d{4}$', linha.strip()):
            comprovante.data_comprovante = linha.strip()
            continue
        label_limpo = normalizar_label(linha)
        if label_limpo:
            labels.append(label_limpo)

    # Parear labels com valores
    idx_valor = 0
    secao_atual = None

    for label in labels:
        if label in SECOES:
            secao_atual = label.replace('á', 'a').replace('é', 'e')
            continue

        if idx_valor >= len(bloco_valores):
            break

        valor = bloco_valores[idx_valor].strip()
        idx_valor += 1

        _atribuir_campo(comprovante, label, valor, secao_atual)


def _parse_formato_b(linhas: list[str], comprovante: ComprovanteBoleto) -> None:
    """
    Parse do Formato B: labels e valores inline ("Label: Valor").
    O OCR leu linha por linha, da esquerda para direita.
    """
    # Pular cabeçalho SICOOB e extrair data do comprovante da linha mista
    secao_atual = None
    valores_pendentes = []  # Para labels sem valor na mesma linha

    for linha in linhas:
        # Ignorar linhas de cabeçalho/rodapé
        if any(kw in linha.upper() for kw in [
            'SICOOB - SISTEMA', 'SISBR - SISTEMA', 'COMPROVANTE DE',
            'OUVIDORIA', 'V1.0'
        ]):
            continue

        # Linha com data + "PAGAMENTO DE BOLETO" + hora
        match_data_cabecalho = re.match(
            r'^(\d{2}/\d{2}/\d{4})\s+PAGAMENTO DE BOLETO\s+(\d{2}:\d{2}:\d{2})$',
            linha.strip()
        )
        if match_data_cabecalho:
            comprovante.data_comprovante = match_data_cabecalho.group(1)
            continue

        # Hora solta (rodapé)
        if re.match(r'^\d{2}:\d{2}:\d{2}$', linha.strip()):
            continue

        # Detectar seções
        label_normalizado = normalizar_label(linha)
        if label_normalizado in SECOES:
            secao_atual = label_normalizado.replace('á', 'a').replace('é', 'e')
            continue

        # Tentar formato "Label: Valor" (com dois-pontos seguido de valor)
        match_inline = re.match(r'^(.+?):\s+(.+)$', linha.strip())
        if match_inline:
            label = normalizar_label(match_inline.group(1))
            valor = match_inline.group(2).strip()

            # Verificar se não é label sem valor (label que termina em ":" sozinha)
            _atribuir_campo(comprovante, label, valor, secao_atual)
            continue

        # Linha que é apenas um label com ":" (sem valor)
        if linha.strip().endswith(':'):
            label = normalizar_label(linha)
            valores_pendentes.append((label, secao_atual))
            continue

        # Linha que é apenas um valor (sem label) — consumir label pendente
        if valores_pendentes:
            label, secao_contexto = valores_pendentes.pop(0)
            _atribuir_campo(comprovante, label, linha.strip(), secao_contexto)
            continue


def _atribuir_campo(
    comprovante: ComprovanteBoleto,
    label: str,
    valor: str,
    secao_atual: Optional[str]
) -> bool:
    """
    Atribui um valor ao campo correto do comprovante baseado no label e seção.

    Returns:
        True se o campo foi atribuído, False caso contrário.
    """
    # 1. Campos diretos
    if label in MAPEAMENTO_CAMPOS:
        setattr(comprovante, MAPEAMENTO_CAMPOS[label], valor)
        return True

    # 2. Campos contextuais (dependem da seção)
    if label in CAMPOS_CONTEXTUAIS:
        if secao_atual and secao_atual in CAMPOS_CONTEXTUAIS[label]:
            setattr(comprovante, CAMPOS_CONTEXTUAIS[label][secao_atual], valor)
            return True

    # 3. Campos de datas
    if label in CAMPOS_DATAS and secao_atual in ('datas', None):
        setattr(comprovante, CAMPOS_DATAS[label], valor)
        return True

    # 4. Campos de valores
    if label in CAMPOS_VALORES and secao_atual in ('valores', None):
        setattr(comprovante, CAMPOS_VALORES[label], valor)
        return True

    return False


def _validar_comprovante(comprovante: ComprovanteBoleto) -> ComprovanteBoleto:
    """
    Valida campos do comprovante após OCR para detectar parsing incorreto.

    Campos cujo valor não bate com o padrão esperado são anulados (None)
    para evitar dados incorretos no banco (ex: CNPJ no campo de razão social).
    """
    # numero_agendamento deve ser numérico
    if comprovante.numero_agendamento and not re.match(r'^\d+$', comprovante.numero_agendamento):
        print(f"  ⚠️  p.{comprovante.pagina}: numero_agendamento inválido: '{comprovante.numero_agendamento}' → None")
        comprovante.numero_agendamento = None

    # CNPJ/CPF deve conter apenas dígitos, pontos, barras, hífens
    for campo in ('beneficiario_cnpj_cpf', 'pagador_cnpj_cpf'):
        valor = getattr(comprovante, campo, None)
        if valor and not re.match(r'^[\d./ -]+$', valor):
            print(f"  ⚠️  p.{comprovante.pagina}: {campo} inválido: '{valor}' → None")
            setattr(comprovante, campo, None)

    # Valores devem conter R$ ou padrão numérico (com separadores BR)
    for campo in ('valor_documento', 'valor_desconto_abatimento', 'valor_juros_multa', 'valor_pago'):
        valor = getattr(comprovante, campo, None)
        if valor and not re.match(r'^R?\$?\s*[\d.,]+$', valor):
            print(f"  ⚠️  p.{comprovante.pagina}: {campo} inválido: '{valor}' → None")
            setattr(comprovante, campo, None)

    return comprovante


def _eh_comprovante_boleto(texto: str) -> bool:
    """
    Verifica se o texto OCR corresponde a um comprovante de PAGAMENTO DE BOLETO.

    O cabeçalho "SICOOB - SISTEMA DE COOPERATIVAS..." aparece em TODOS os
    comprovantes Sicoob (boleto, PIX, TED, etc.). O que diferencia é o
    sub-cabeçalho "PAGAMENTO DE BOLETO" — presente APENAS em boletos.

    Se o texto não contém "PAGAMENTO DE BOLETO", não é um comprovante de
    boleto e deve ser pulado pelo parser.
    """
    return 'PAGAMENTO DE BOLETO' in texto.upper()


def parse_comprovante(texto: str, pagina: int) -> ComprovanteBoleto:
    """
    Faz o parsing do texto OCR de um comprovante e retorna os dados estruturados.

    Detecta automaticamente o formato do OCR:
    - Formato A: Labels em bloco separado dos valores (OCR leu colunas separadas)
    - Formato B: Labels e valores inline "Label: Valor" (OCR leu linha a linha)
    """
    comprovante = ComprovanteBoleto(pagina=pagina)

    linhas = texto.strip().split('\n')
    linhas = [ln.strip() for ln in linhas if ln.strip()]

    if not linhas:
        return comprovante

    formato = _detectar_formato(linhas)

    if formato == 'A':
        _parse_formato_a(linhas, comprovante)
    else:
        _parse_formato_b(linhas, comprovante)

    # Validação pós-parse: anula campos com valores inconsistentes (OCR errado)
    comprovante = _validar_comprovante(comprovante)

    return comprovante


def extrair_comprovantes(pdf_path: str) -> list[ComprovanteBoleto]:
    """
    Extrai todos os comprovantes de um PDF.

    Args:
        pdf_path: Caminho do arquivo PDF

    Returns:
        Lista de ComprovanteBoleto extraídos
    """
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"Arquivo não encontrado: {pdf_path}")

    pdf = pdfium.PdfDocument(pdf_path)
    total_paginas = len(pdf)
    comprovantes = []

    print(f"Processando: {pdf_path}")
    print(f"Total de páginas: {total_paginas}")
    print("-" * 60)

    pulados = 0

    for i in range(total_paginas):
        print(f"  Página {i + 1}/{total_paginas}... ", end="", flush=True)

        # Renderizar e OCR
        imagem = renderizar_pagina(pdf_path, i)
        texto = extrair_texto_ocr(imagem)

        # Verificar se é comprovante de boleto
        if not _eh_comprovante_boleto(texto):
            print("PULADA (não é boleto)")
            pulados += 1
            continue

        # Parsear
        comprovante = parse_comprovante(texto, pagina=i + 1)
        comprovantes.append(comprovante)

        # Feedback
        if comprovante.beneficiario_razao_social:
            print(f"OK → {comprovante.beneficiario_razao_social}")
        else:
            print("OK (sem beneficiário identificado)")

    print("-" * 60)
    print(f"Total extraído: {len(comprovantes)} comprovante(s)")
    if pulados:
        print(f"Páginas puladas (não são boleto): {pulados}")

    return comprovantes


def extrair_comprovantes_from_bytes(pdf_bytes: bytes) -> list[ComprovanteBoleto]:
    """
    Extrai comprovantes a partir de bytes do PDF (uso em APIs web).

    Args:
        pdf_bytes: Conteúdo binário do PDF

    Returns:
        Lista de ComprovanteBoleto extraídos
    """
    pdf = pdfium.PdfDocument(pdf_bytes)
    total_paginas = len(pdf)
    comprovantes = []

    for i in range(total_paginas):
        page = pdf[i]
        bitmap = page.render(scale=4.0)
        imagem = bitmap.to_pil()
        texto = extrair_texto_ocr(imagem)

        # Pular páginas que não são comprovante de boleto (PIX, TED, etc.)
        if not _eh_comprovante_boleto(texto):
            continue

        comprovante = parse_comprovante(texto, pagina=i + 1)
        comprovantes.append(comprovante)

    return comprovantes


# ---------------------------------------------------------------------------
# Formatação de saída
# ---------------------------------------------------------------------------

def formatar_tabela(comprovantes: list[ComprovanteBoleto]) -> str:
    """Formata os comprovantes em uma tabela legível."""
    saida = []

    for i, c in enumerate(comprovantes):
        saida.append(f"\n{'='*70}")
        saida.append(f" COMPROVANTE {i+1} (Página {c.pagina})")
        saida.append(f"{'='*70}")

        saida.append(f"\n  📅 Data:                  {c.data_comprovante or 'N/A'}")
        saida.append(f"  🏦 Cooperativa:           {c.cooperativa or 'N/A'}")
        saida.append(f"  💳 Conta:                 {c.conta or 'N/A'}")
        saida.append(f"  👤 Cliente:               {c.cliente or 'N/A'}")
        saida.append(f"  📝 Linha Digitável:       {c.linha_digitavel or 'N/A'}")
        saida.append(f"  📄 Nº Documento:          {c.numero_documento or 'N/A'}")
        saida.append(f"  🔢 Nosso Número:          {c.nosso_numero or 'N/A'}")
        saida.append(f"  📋 Nº Agendamento:        {c.numero_agendamento or 'N/A'}")
        saida.append(f"  🏛️  Instituição Emissora:  {c.instituicao_emissora or 'N/A'}")
        saida.append(f"  📌 Tipo Documento:        {c.tipo_documento or 'N/A'}")

        saida.append(f"\n  --- BENEFICIÁRIO ---")
        saida.append(f"  🏢 Razão Social:          {c.beneficiario_razao_social or 'N/A'}")
        saida.append(f"  🏪 Nome Fantasia:         {c.beneficiario_nome_fantasia or 'N/A'}")
        saida.append(f"  📋 CNPJ/CPF:              {c.beneficiario_cnpj_cpf or 'N/A'}")

        saida.append(f"\n  --- PAGADOR ---")
        saida.append(f"  🏢 Razão Social:          {c.pagador_razao_social or 'N/A'}")
        saida.append(f"  🏪 Nome Fantasia:         {c.pagador_nome_fantasia or 'N/A'}")
        saida.append(f"  📋 CNPJ/CPF:              {c.pagador_cnpj_cpf or 'N/A'}")

        saida.append(f"\n  --- DATAS ---")
        saida.append(f"  ✅ Realizado:              {c.data_realizado or 'N/A'}")
        saida.append(f"  💰 Pagamento:             {c.data_pagamento or 'N/A'}")
        saida.append(f"  📅 Vencimento:            {c.data_vencimento or 'N/A'}")

        saida.append(f"\n  --- VALORES ---")
        saida.append(f"  💵 Documento:             {c.valor_documento or 'N/A'}")
        saida.append(f"  🔽 Desconto/Abatimento:   {c.valor_desconto_abatimento or 'N/A'}")
        saida.append(f"  📈 Juros/Multa:           {c.valor_juros_multa or 'N/A'}")
        saida.append(f"  💰 PAGO:                  {c.valor_pago or 'N/A'}")

        saida.append(f"\n  --- STATUS ---")
        saida.append(f"  📊 Situação:              {c.situacao or 'N/A'}")
        saida.append(f"  🔐 Autenticação:          {c.autenticacao or 'N/A'}")

    return '\n'.join(saida)


def formatar_json(comprovantes: list[ComprovanteBoleto]) -> str:
    """Formata os comprovantes como JSON."""
    dados = [asdict(c) for c in comprovantes]
    return json.dumps(dados, ensure_ascii=False, indent=2)


def formatar_csv(comprovantes: list[ComprovanteBoleto]) -> str:
    """Formata os comprovantes como CSV."""
    if not comprovantes:
        return ""

    output = StringIO()
    campos = list(asdict(comprovantes[0]).keys())
    writer = csv.DictWriter(output, fieldnames=campos, delimiter=';')
    writer.writeheader()
    for c in comprovantes:
        writer.writerow(asdict(c))

    return output.getvalue()


def formatar_resumo(comprovantes: list[ComprovanteBoleto]) -> str:
    """Formata um resumo consolidado dos pagamentos."""
    saida = []
    saida.append(f"\n{'='*70}")
    saida.append(f" RESUMO DE PAGAMENTOS ({len(comprovantes)} comprovante(s))")
    saida.append(f"{'='*70}\n")

    total_pago = 0.0
    for c in comprovantes:
        valor_str = (c.valor_pago or '0').replace('R$', '').replace('.', '').replace(',', '.').strip()
        try:
            valor = float(valor_str)
        except ValueError:
            valor = 0.0
        total_pago += valor

        saida.append(
            f"  Pg.{c.pagina:>2} | {c.beneficiario_razao_social or 'N/A':<45} | "
            f"{c.beneficiario_cnpj_cpf or 'N/A':<20} | {c.valor_pago or 'N/A':>12} | "
            f"Venc: {c.data_vencimento or 'N/A'}"
        )

    saida.append(f"\n{'─'*70}")
    saida.append(f"  TOTAL PAGO: R$ {total_pago:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))
    saida.append(f"{'─'*70}")

    return '\n'.join(saida)


def formatar_xlsx(comprovantes: list[ComprovanteBoleto], caminho_saida: str) -> str:
    """Gera arquivo Excel (.xlsx) com os comprovantes."""
    import openpyxl
    from openpyxl.styles import Font, Alignment, PatternFill, Border, Side

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = 'Comprovantes'

    header_font = Font(bold=True, color='FFFFFF', size=11)
    header_fill = PatternFill(start_color='2E5090', end_color='2E5090', fill_type='solid')
    border = Border(
        left=Side(style='thin'), right=Side(style='thin'),
        top=Side(style='thin'), bottom=Side(style='thin')
    )

    colunas = [
        ('pagina', 'Página'),
        ('data_comprovante', 'Data'),
        ('beneficiario_razao_social', 'Beneficiário'),
        ('beneficiario_cnpj_cpf', 'CNPJ Beneficiário'),
        ('pagador_razao_social', 'Pagador'),
        ('pagador_cnpj_cpf', 'CNPJ Pagador'),
        ('numero_documento', 'Nº Documento'),
        ('nosso_numero', 'Nosso Número'),
        ('numero_agendamento', 'Nº Agendamento'),
        ('valor_documento', 'Valor Documento'),
        ('valor_desconto_abatimento', 'Desconto'),
        ('valor_juros_multa', 'Juros/Multa'),
        ('valor_pago', 'Valor Pago'),
        ('data_pagamento', 'Data Pagamento'),
        ('data_vencimento', 'Data Vencimento'),
        ('data_realizado', 'Realizado'),
        ('situacao', 'Situação'),
        ('autenticacao', 'Autenticação'),
        ('cooperativa', 'Cooperativa'),
        ('conta', 'Conta'),
        ('cliente', 'Cliente'),
        ('linha_digitavel', 'Linha Digitável'),
        ('instituicao_emissora', 'Inst. Emissora'),
        ('tipo_documento', 'Tipo Documento'),
    ]

    # Header
    for col_idx, (_, nome) in enumerate(colunas, 1):
        cell = ws.cell(row=1, column=col_idx, value=nome)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal='center')
        cell.border = border

    # Dados
    for row_idx, comp in enumerate(comprovantes, 2):
        dados = asdict(comp)
        for col_idx, (campo, _) in enumerate(colunas, 1):
            cell = ws.cell(row=row_idx, column=col_idx, value=dados.get(campo, ''))
            cell.border = border
            cell.alignment = Alignment(horizontal='center' if campo == 'pagina' else 'left')

    # Auto-ajustar largura
    for col_idx, (campo, nome) in enumerate(colunas, 1):
        max_len = len(nome)
        for row in range(2, len(comprovantes) + 2):
            val = str(ws.cell(row=row, column=col_idx).value or '')
            max_len = max(max_len, len(val))
        ws.column_dimensions[openpyxl.utils.get_column_letter(col_idx)].width = min(max_len + 3, 45)

    ws.freeze_panes = 'A2'
    ws.auto_filter.ref = ws.dimensions

    wb.save(caminho_saida)
    return f"Arquivo Excel salvo: {caminho_saida}"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    import argparse

    parser = argparse.ArgumentParser(
        description='Leitor de Comprovantes de Pagamento de Boleto - SICOOB',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  python leitor_comprovantes_sicoob.py comprovantes.pdf
  python leitor_comprovantes_sicoob.py comprovantes.pdf --formato json
  python leitor_comprovantes_sicoob.py comprovantes.pdf --formato csv --saida pagamentos.csv
  python leitor_comprovantes_sicoob.py comprovantes.pdf --formato resumo
  python leitor_comprovantes_sicoob.py comprovantes.pdf --formato xlsx --saida comprovantes.xlsx
        """
    )
    parser.add_argument('pdf', help='Caminho do arquivo PDF')
    parser.add_argument(
        '--formato', '-f',
        choices=['tabela', 'json', 'csv', 'resumo', 'xlsx'],
        default='tabela',
        help='Formato de saída (padrão: tabela)'
    )
    parser.add_argument(
        '--saida', '-o',
        help='Arquivo de saída (padrão: stdout). Obrigatório para xlsx.'
    )
    parser.add_argument(
        '--escala',
        type=float,
        default=4.0,
        help='Escala de renderização para OCR (padrão: 4.0 = ~288 DPI)'
    )

    args = parser.parse_args()

    # Validar xlsx requer --saida
    if args.formato == 'xlsx' and not args.saida:
        parser.error("--saida é obrigatório quando --formato=xlsx")

    # Extrair
    comprovantes = extrair_comprovantes(args.pdf)

    # Formato xlsx tem tratamento especial (binário)
    if args.formato == 'xlsx':
        print(formatar_resumo(comprovantes))
        msg = formatar_xlsx(comprovantes, args.saida)
        print(f"\n{msg}")
        return

    # Formatos texto
    formatadores = {
        'tabela': formatar_tabela,
        'json': formatar_json,
        'csv': formatar_csv,
        'resumo': formatar_resumo,
    }

    resultado = formatadores[args.formato](comprovantes)

    # Sempre mostrar resumo no stderr quando salvando em arquivo
    if args.saida:
        print(formatar_resumo(comprovantes))

    # Saída
    if args.saida:
        with open(args.saida, 'w', encoding='utf-8') as f:
            f.write(resultado)
        print(f"\nArquivo salvo: {args.saida}")
    else:
        print(resultado)


if __name__ == '__main__':
    main()
