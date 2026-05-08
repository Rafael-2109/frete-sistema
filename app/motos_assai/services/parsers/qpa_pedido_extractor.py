"""Extrator determinístico do PDF de Pedido de Compras Q.P.A. → Sendas/Assaí.

Layout de referência (Consinco): cada PÁGINA do PDF representa UMA loja Sendas
com header próprio + tabela de produtos. O PDF é multi-loja.

Header relevante por página:
  PEDIDO DE COMPRAS 21439695/L
  FORNECEDOR 4442498
  R. Social Q.P.A DISTRIBUICAO LTDA           CNPJ 53.780.554/0001-15
  ... DADOS PARA FATURAMENTO
  R. Social SENDAS DISTRIBUIDORA S/A LJ12     CNPJ 06.057.223/0272-90
  ENDEREÇO PARA ENTREGA
  Cidade JUNDIAÍ - SP

Linhas de produto (após "Cod Forn Seq Produtos a Receber"):
  1342056AUTOPROPELIDO X11 MINI 1000W 60V 20AH UN 1 10,00 7.100,0000 71.000,00 0,00 ...

Datas:
  Data da emissão     22/04/2026
  Previsão de entrega 22/04/2026

A confiança final é calculada em `pedido_service` a partir de:
  conf = (paginas_com_itens / paginas_total) * (lojas_resolvidas / lojas_total)
"""

from __future__ import annotations

import re
from decimal import Decimal
from typing import Dict, List, Any, Optional

import pdfplumber

from app.pedidos.leitura.base import PDFExtractor


class QpaPedidoExtractor(PDFExtractor):
    """Extrai dados de pedido VOE Q.P.A. → Sendas em formato lista de items."""

    REGEX_NUMERO_PEDIDO = re.compile(
        r'PEDIDO\s+DE\s+COMPRAS\s+(\d+/[A-Z])'
    )
    REGEX_DATA_EMISSAO = re.compile(
        r'Data\s+da\s+emiss[aã]o\s+(\d{2}/\d{2}/\d{4})'
    )
    REGEX_PREVISAO = re.compile(
        r'Previs[aã]o\s+de\s+entrega\s+(\d{2}/\d{2}/\d{4})'
    )
    REGEX_FORNECEDOR_CNPJ = re.compile(
        r'Q\.?P\.?A\s*DISTRIBUI[CÇ][AÃ]O.*?CNPJ\s+([\d\.\-/]+)',
        re.DOTALL
    )
    REGEX_LOJA_NUMERO_E_NOME = re.compile(
        r'SENDAS\s+DISTRIBUIDORA\s+S/A\s+LJ(\d+)\s+\d+\s+([A-ZÀ-Ÿ /]+)'
    )
    # CNPJ da loja: o segundo CNPJ por página (primeiro é Q.P.A.)
    REGEX_CNPJ = re.compile(r'(\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2})')
    # Linha de produto (Cod Forn): código 7 dígitos + descrição + UN 1 + qtd + valor_unit + valor_total
    # Tolera espaços variáveis e acentos na descrição.
    REGEX_PRODUTO = re.compile(
        r'^(\d{7})\s*([A-ZÀ-Ÿ0-9 ]+?)\s+UN\s+1\s+'
        r'([\d\.,]+)\s+([\d\.,]+)\s+([\d\.,]+)'
    )

    def __init__(self):
        super().__init__()
        self.formato = 'QPA_PEDIDO'

    def extract(self, pdf_path: str, texto_pre_extraido: str = None) -> List[Dict[str, Any]]:
        """Retorna lista flat de items: 1 item = (loja × produto).

        Cada item tem o numero_pedido + data_emissao do header (repetidos)
        + numero_loja + cnpj_loja + razao_social_loja + cidade_loja + uf_loja
        + codigo_qpa + descricao + qtd + valor_unitario + valor_total.
        """
        items: List[Dict[str, Any]] = []
        try:
            with pdfplumber.open(pdf_path) as pdf:
                # Header global (mesmo em todas as páginas)
                texto_pag1 = pdf.pages[0].extract_text() or ''
                numero_pedido = self._match(self.REGEX_NUMERO_PEDIDO, texto_pag1)
                data_emissao = self._match(self.REGEX_DATA_EMISSAO, texto_pag1)
                previsao_entrega = self._match(self.REGEX_PREVISAO, texto_pag1)
                fornecedor_cnpj_raw = self._match(self.REGEX_FORNECEDOR_CNPJ, texto_pag1)
                fornecedor_cnpj = self.sanitize_cnpj(fornecedor_cnpj_raw) if fornecedor_cnpj_raw else None

                if not numero_pedido:
                    self.errors.append('numero_pedido não encontrado na página 1')

                # Itera páginas: cada página = 1 loja
                for idx, page in enumerate(pdf.pages):
                    texto = page.extract_text() or ''
                    page.flush_cache()
                    if idx > 0 and idx % 20 == 0:
                        import gc; gc.collect()

                    loja_dados = self._extract_loja_da_pagina(texto)
                    if not loja_dados:
                        self.warnings.append(f'Página {idx+1}: loja não identificada')
                        continue

                    produtos = self._extract_produtos_da_pagina(texto)
                    if not produtos:
                        self.warnings.append(
                            f'Página {idx+1} (loja {loja_dados.get("numero_loja")}): zero produtos extraídos'
                        )
                        continue

                    for prod in produtos:
                        items.append({
                            'numero_pedido': numero_pedido,
                            'data_emissao': data_emissao,
                            'previsao_entrega': previsao_entrega,
                            'fornecedor_cnpj': fornecedor_cnpj,
                            **loja_dados,
                            **prod,
                            'pagina': idx + 1,
                        })

        except Exception as e:
            import traceback
            self.errors.append(f'Erro ao processar PDF: {e}')
            self.errors.append(traceback.format_exc())

        return items

    def validate(self, data: Dict[str, Any]) -> bool:
        """Valida 1 item: campos obrigatórios + qtd > 0 + valor > 0."""
        for k in ('numero_pedido', 'numero_loja', 'codigo_qpa', 'qtd', 'valor_unitario'):
            if data.get(k) in (None, ''):
                return False
        if (data.get('qtd') or 0) <= 0:
            return False
        if (data.get('valor_unitario') or Decimal('0')) <= 0:
            return False
        return True

    def sanitize_quantity(self, qty: str) -> int:
        """Converte quantidade para inteiro.

        Sobrescreve a base para tratar formato brasileiro com decimais:
        '10,00' → 10  (não 1000 como a base faria ao remover a vírgula)
        '34,00' → 34
        """
        if not qty:
            return 0
        qty = str(qty).strip()
        # Converte vírgula decimal BR para ponto antes de truncar
        qty = qty.replace(',', '.')
        # Remove separador de milhar (ponto antes de vírgula já convertida)
        parts = qty.split('.')
        if len(parts) > 2:
            # Tem separador de milhar: 1.234.000 → 1234000
            qty = ''.join(parts[:-1]) + '.' + parts[-1]
        try:
            return int(float(qty))
        except Exception:
            return 0

    # ============== helpers privados ==============

    def _match(self, regex: re.Pattern, texto: str) -> Optional[str]:
        m = regex.search(texto)
        return m.group(1).strip() if m else None

    def _extract_loja_da_pagina(self, texto: str) -> Optional[Dict[str, Any]]:
        m = self.REGEX_LOJA_NUMERO_E_NOME.search(texto)
        if not m:
            return None
        numero_loja = m.group(1).strip()
        razao_apos_LJ = m.group(2).strip()  # ex: "012 JUNDIAI" ou "JOÃO DIAS"

        # CNPJs da página: o primeiro é Q.P.A., o segundo é a loja Sendas
        cnpjs = self.REGEX_CNPJ.findall(texto)
        cnpj_loja = cnpjs[1] if len(cnpjs) >= 2 else None

        # Cidade/UF: vem na linha "Cidade XXXX - UF" do bloco DADOS PARA FATURAMENTO
        cidade = None
        uf = None
        for ln in texto.split('\n'):
            m_cid = re.search(r'Cidade\s+([A-ZÀ-Ÿ ]+?)\s*-\s*([A-Z]{2})\s', ln)
            if m_cid:
                cidade = m_cid.group(1).strip()
                uf = m_cid.group(2).strip()
                break  # primeiro match: dados para faturamento

        return {
            'numero_loja': numero_loja,
            'razao_social_loja': f'SENDAS DISTRIBUIDORA S/A LJ{numero_loja}',
            'cnpj_loja': cnpj_loja,
            'cidade_loja': cidade,
            'uf_loja': uf,
        }

    def _extract_produtos_da_pagina(self, texto: str) -> List[Dict[str, Any]]:
        produtos = []
        for linha in texto.split('\n'):
            linha = linha.strip()
            if not linha:
                continue
            m = self.REGEX_PRODUTO.match(linha)
            if not m:
                continue
            codigo, descricao, qtd_str, vu_str, vt_str = m.groups()
            produtos.append({
                'codigo_qpa': codigo.strip(),
                'descricao': descricao.strip(),
                'qtd': self.sanitize_quantity(qtd_str),
                'valor_unitario': self.sanitize_decimal(vu_str),
                'valor_total': self.sanitize_decimal(vt_str),
            })
        return produtos
