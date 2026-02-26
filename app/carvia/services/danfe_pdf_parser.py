"""
Parser de DANFE PDF para o modulo CarVia
=========================================

Extrai dados de DANFE (Documento Auxiliar de NF-e) a partir de PDF.
Utiliza pdfplumber (primario) + pypdf (fallback).

Reutiliza utilitarios de app/pedidos/leitura/base.py:
- sanitize_cnpj, sanitize_decimal, parse_date

IMPORTANTE: A extracao de PDF e inerentemente menos confiavel que XML.
O campo 'confianca' indica o nivel de confianca dos dados extraidos.
"""

import logging
import re
from decimal import Decimal
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class DanfePDFParser:
    """Parser para extrair informacoes de DANFE em PDF"""

    def __init__(self, pdf_path: str = None, pdf_bytes: bytes = None):
        """
        Args:
            pdf_path: Caminho para o arquivo PDF
            pdf_bytes: Bytes do PDF (alternativa a pdf_path)
        """
        self.pdf_path = pdf_path
        self.pdf_bytes = pdf_bytes
        self.texto_completo = ''
        self.paginas = []
        self.confianca = 0.0
        self._extrair_texto()

    def _extrair_texto(self):
        """Extrai texto do PDF usando pdfplumber (primario) + pypdf (fallback)"""
        texto = self._extrair_com_pdfplumber()
        if not texto or len(texto.strip()) < 50:
            texto_fallback = self._extrair_com_pypdf()
            if texto_fallback and len(texto_fallback.strip()) > len(texto.strip()):
                texto = texto_fallback

        self.texto_completo = texto or ''

    def _extrair_com_pdfplumber(self) -> str:
        """Extrai texto usando pdfplumber"""
        try:
            import pdfplumber

            if self.pdf_path:
                pdf = pdfplumber.open(self.pdf_path)
            elif self.pdf_bytes:
                import io
                pdf = pdfplumber.open(io.BytesIO(self.pdf_bytes))
            else:
                return ''

            textos = []
            for page in pdf.pages:
                texto = page.extract_text()
                if texto:
                    textos.append(texto)
                    self.paginas.append(texto)
            pdf.close()
            return '\n'.join(textos)
        except Exception as e:
            logger.warning(f"pdfplumber falhou: {e}")
            return ''

    def _extrair_com_pypdf(self) -> str:
        """Extrai texto usando pypdf (fallback)"""
        try:
            import pypdf

            if self.pdf_path:
                reader = pypdf.PdfReader(self.pdf_path)
            elif self.pdf_bytes:
                import io
                reader = pypdf.PdfReader(io.BytesIO(self.pdf_bytes))
            else:
                return ''

            textos = []
            for page in reader.pages:
                texto = page.extract_text()
                if texto:
                    textos.append(texto)
            return '\n'.join(textos)
        except Exception as e:
            logger.warning(f"pypdf falhou: {e}")
            return ''

    def is_valid(self) -> bool:
        """Verifica se o texto foi extraido com sucesso"""
        return len(self.texto_completo.strip()) > 50

    def get_chave_acesso(self) -> Optional[str]:
        """Extrai chave de acesso (44 digitos) do DANFE"""
        # Buscar sequencia de 44 digitos
        matches = re.findall(r'\d{44}', self.texto_completo)
        if matches:
            self.confianca += 0.3
            return matches[0]
        return None

    def get_numero_nf(self) -> Optional[str]:
        """Extrai numero da NF"""
        patterns = [
            r'N[°ºo.]\s*[:.]?\s*(\d{1,9})',
            r'N[UÚ]MERO\s*[:.]?\s*(\d{1,9})',
            r'NF-?e?\s*[Nn][°ºo.]\s*[:.]?\s*(\d{1,9})',
            r'(?:NOTA\s*FISCAL|NF)\s*(?:ELETR[OÔ]NICA)?\s*[Nn]?\s*[°ºo.]?\s*[:.]?\s*(\d{1,9})',
        ]
        for pattern in patterns:
            match = re.search(pattern, self.texto_completo, re.IGNORECASE)
            if match:
                self.confianca += 0.1
                return match.group(1).lstrip('0') or '0'
        return None

    def get_serie(self) -> Optional[str]:
        """Extrai serie da NF"""
        patterns = [
            r'S[EÉ]RIE\s*[:.]?\s*(\d{1,3})',
            r'SER\.\s*[:.]?\s*(\d{1,3})',
        ]
        for pattern in patterns:
            match = re.search(pattern, self.texto_completo, re.IGNORECASE)
            if match:
                return match.group(1)
        return None

    def get_cnpj_emitente(self) -> Optional[str]:
        """Extrai CNPJ do emitente"""
        # Primeiro CNPJ no documento geralmente e o emitente
        pattern = r'(\d{2}[.\s]?\d{3}[.\s]?\d{3}[/\s]?\d{4}[-\s]?\d{2})'
        matches = re.findall(pattern, self.texto_completo)
        if matches:
            cnpj = re.sub(r'\D', '', matches[0])
            if len(cnpj) == 14:
                self.confianca += 0.1
                return cnpj
        return None

    def get_cnpj_destinatario(self) -> Optional[str]:
        """Extrai CNPJ do destinatario"""
        # Buscar CNPJ apos marcador de destinatario
        dest_patterns = [
            r'DESTINAT[AÁ]RIO.*?(\d{2}[.\s]?\d{3}[.\s]?\d{3}[/\s]?\d{4}[-\s]?\d{2})',
            r'DEST\s*/\s*REM.*?(\d{2}[.\s]?\d{3}[.\s]?\d{3}[/\s]?\d{4}[-\s]?\d{2})',
        ]
        for pattern in dest_patterns:
            match = re.search(pattern, self.texto_completo, re.IGNORECASE | re.DOTALL)
            if match:
                cnpj = re.sub(r'\D', '', match.group(1))
                if len(cnpj) == 14:
                    return cnpj

        # Fallback: segundo CNPJ no documento
        pattern = r'(\d{2}[.\s]?\d{3}[.\s]?\d{3}[/\s]?\d{4}[-\s]?\d{2})'
        matches = re.findall(pattern, self.texto_completo)
        if len(matches) >= 2:
            cnpj = re.sub(r'\D', '', matches[1])
            if len(cnpj) == 14:
                return cnpj
        return None

    def get_valor_total(self) -> Optional[float]:
        """Extrai valor total da NF"""
        patterns = [
            r'VALOR\s*TOTAL\s*DA\s*NOTA\s*[:.]?\s*R?\$?\s*([\d.,]+)',
            r'V\.\s*TOTAL\s*(?:DA\s*)?NF\s*[:.]?\s*R?\$?\s*([\d.,]+)',
            r'TOTAL\s*GERAL\s*[:.]?\s*R?\$?\s*([\d.,]+)',
        ]
        for pattern in patterns:
            match = re.search(pattern, self.texto_completo, re.IGNORECASE)
            if match:
                valor = self._parse_valor_br(match.group(1))
                if valor and valor > 0:
                    self.confianca += 0.1
                    return valor
        return None

    def get_peso_bruto(self) -> Optional[float]:
        """Extrai peso bruto"""
        patterns = [
            r'PESO\s*BRUTO\s*[:.]?\s*([\d.,]+)',
            r'P\.\s*BRUTO\s*[:.]?\s*([\d.,]+)',
        ]
        for pattern in patterns:
            match = re.search(pattern, self.texto_completo, re.IGNORECASE)
            if match:
                return self._parse_valor_br(match.group(1))
        return None

    def get_peso_liquido(self) -> Optional[float]:
        """Extrai peso liquido"""
        patterns = [
            r'PESO\s*L[IÍ]QUIDO\s*[:.]?\s*([\d.,]+)',
            r'P\.\s*L[IÍ]QUIDO\s*[:.]?\s*([\d.,]+)',
        ]
        for pattern in patterns:
            match = re.search(pattern, self.texto_completo, re.IGNORECASE)
            if match:
                return self._parse_valor_br(match.group(1))
        return None

    def get_quantidade_volumes(self) -> Optional[int]:
        """Extrai quantidade de volumes"""
        patterns = [
            r'QUANTIDADE\s*[:.]?\s*(\d+)',
            r'QTD\s*[:.]?\s*(\d+)',
            r'VOLUMES?\s*[:.]?\s*(\d+)',
        ]
        for pattern in patterns:
            match = re.search(pattern, self.texto_completo, re.IGNORECASE)
            if match:
                try:
                    return int(match.group(1))
                except ValueError:
                    pass
        return None

    def get_data_emissao(self) -> Optional[str]:
        """Extrai data de emissao"""
        patterns = [
            r'(?:DATA\s*(?:DA\s*)?EMISS[AÃ]O|EMITIDO\s*EM)\s*[:.]?\s*(\d{2}[/.-]\d{2}[/.-]\d{4})',
            r'(\d{2}/\d{2}/\d{4})',  # Fallback: primeira data no formato BR
        ]
        for pattern in patterns:
            match = re.search(pattern, self.texto_completo, re.IGNORECASE)
            if match:
                return match.group(1)
        return None

    def get_nome_emitente(self) -> Optional[str]:
        """Extrai nome/razao social do emitente"""
        # Dificil extrair com confianca de PDF — retorna None
        # O caller deve resolver via CNPJ no banco
        return None

    def get_todas_informacoes(self) -> Dict:
        """Extrai todas as informacoes disponiveis"""
        self.confianca = 0.0

        resultado = {
            'chave_acesso_nf': self.get_chave_acesso(),
            'numero_nf': self.get_numero_nf(),
            'serie_nf': self.get_serie(),
            'data_emissao_str': self.get_data_emissao(),
            'data_emissao': None,
            'cnpj_emitente': self.get_cnpj_emitente(),
            'nome_emitente': self.get_nome_emitente(),
            'uf_emitente': None,
            'cidade_emitente': None,
            'cnpj_destinatario': self.get_cnpj_destinatario(),
            'nome_destinatario': None,
            'uf_destinatario': None,
            'cidade_destinatario': None,
            'valor_total': self.get_valor_total(),
            'peso_bruto': self.get_peso_bruto(),
            'peso_liquido': self.get_peso_liquido(),
            'quantidade_volumes': self.get_quantidade_volumes(),
            'tipo_fonte': 'PDF_DANFE',
            'confianca': round(self.confianca, 2),
        }

        # Tentar parsear data
        if resultado['data_emissao_str']:
            resultado['data_emissao'] = self._parse_date_br(resultado['data_emissao_str'])

        return resultado

    def _parse_valor_br(self, valor_str: str) -> Optional[float]:
        """Converte valor brasileiro (1.234,56) para float"""
        if not valor_str:
            return None
        try:
            # Remove espacos
            valor_str = valor_str.strip()
            # Detectar formato brasileiro (virgula como decimal)
            if ',' in valor_str:
                # 1.234,56 -> 1234.56
                valor_str = valor_str.replace('.', '').replace(',', '.')
            return float(valor_str)
        except (ValueError, TypeError):
            return None

    def _parse_date_br(self, date_str: str):
        """Converte data brasileira (DD/MM/YYYY) para date"""
        if not date_str:
            return None
        try:
            from datetime import datetime
            # Normalizar separadores
            date_str = date_str.replace('-', '/').replace('.', '/')
            return datetime.strptime(date_str, '%d/%m/%Y').date()
        except (ValueError, TypeError):
            return None


def parsear_danfe_pdf(pdf_path: str = None, pdf_bytes: bytes = None) -> Dict:
    """Funcao helper para parsear DANFE PDF"""
    parser = DanfePDFParser(pdf_path=pdf_path, pdf_bytes=pdf_bytes)
    return parser.get_todas_informacoes()
