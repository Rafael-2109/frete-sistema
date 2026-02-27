"""
Parser de DANFE PDF para o modulo CarVia
=========================================

Extrai dados de DANFE (Documento Auxiliar de NF-e) a partir de PDF.
Utiliza pdfplumber (primario) + pypdf (fallback).

Reutiliza utilitarios de app/pedidos/leitura/base.py:
- sanitize_cnpj, sanitize_decimal, parse_date

IMPORTANTE: A extracao de PDF e inerentemente menos confiavel que XML.
O campo 'confianca' indica o nivel de confianca dos dados extraidos.

Layout Tabular: DANFEs reais usam layout tabular — cabecalhos numa
linha e valores na seguinte. Cada metodo usa Strategy 1 (same-line regex
com [^\\S\\n]* para nao cruzar newline) + Strategy 2 (split por \\n, localizar
linha do cabecalho, extrair token por posicao na linha seguinte).
"""

import logging
import re
from typing import Dict, List, Optional

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

    # --- Helpers para layout tabular ---

    def _linhas(self) -> List[str]:
        """Retorna linhas do texto completo"""
        return self.texto_completo.split('\n')

    def _encontrar_linha(self, *termos: str) -> Optional[int]:
        """Encontra indice da primeira linha que contem TODOS os termos (case-insensitive)"""
        linhas = self._linhas()
        for i, linha in enumerate(linhas):
            upper = linha.upper()
            if all(t.upper() in upper for t in termos):
                return i
        return None

    def _tokens_numericos(self, linha: str) -> List[str]:
        """Extrai todos os tokens que parecem numeros (ex: '7.360,87', '64,000', '1')"""
        return re.findall(r'\d[\d.,]*\d|\d', linha)

    # --- Metodos de extracao ---

    def get_chave_acesso(self) -> Optional[str]:
        """Extrai chave de acesso (44 digitos) do DANFE

        P1 fix: DANFEs reais imprimem chave com espacos: '3526 0253 7805...'
        Strategy 1: buscar 44 digitos contiguos (caso simples)
        Strategy 2: localizar 'CHAVE DE ACESSO', concatenar digitos da proxima linha
        Strategy 3: buscar padrao de grupos de 4 digitos separados por espaco
        """
        # Strategy 1: 44 digitos contiguos
        matches = re.findall(r'\d{44}', self.texto_completo)
        if matches:
            self.confianca += 0.3
            return matches[0]

        # Strategy 2: perto de "CHAVE DE ACESSO", concatenar digitos da proxima linha
        idx = self._encontrar_linha('CHAVE', 'ACESSO')
        if idx is not None:
            linhas = self._linhas()
            # Tentar a propria linha + proximas 2 linhas
            for offset in range(0, 3):
                if idx + offset < len(linhas):
                    digitos = re.sub(r'\D', '', linhas[idx + offset])
                    if len(digitos) == 44:
                        self.confianca += 0.25
                        return digitos
            # Concatenar digitos de 2 linhas seguintes
            digitos_concat = ''
            for offset in range(1, 3):
                if idx + offset < len(linhas):
                    digitos_concat += re.sub(r'\D', '', linhas[idx + offset])
            if len(digitos_concat) == 44:
                self.confianca += 0.2
                return digitos_concat

        # Strategy 3: padrao com espacos entre grupos de 4 digitos (nao cruza \n)
        match = re.search(r'\d{4}(?:[^\S\n]+\d{4}){8,}', self.texto_completo)
        if match:
            digitos = re.sub(r'\D', '', match.group(0))
            if len(digitos) == 44:
                self.confianca += 0.2
                return digitos

        return None

    def get_numero_nf(self) -> Optional[str]:
        """Extrai numero da NF

        P2 fix: 'N. 000.001.363' — regex deve capturar numero com separadores
        de milhar e depois remover pontos e zeros a esquerda.
        """
        # Strategy 1: numero formatado com separador de milhar (ex: 000.001.363)
        match = re.search(
            r'N[°ºo.]\s*[:.]?\s*(\d{1,3}(?:\.\d{3})+)',
            self.texto_completo,
            re.IGNORECASE,
        )
        if match:
            numero = match.group(1).replace('.', '').lstrip('0') or '0'
            self.confianca += 0.1
            return numero

        # Strategy 2: regexes same-line (numeros simples sem separador de milhar)
        patterns = [
            r'N[°ºo.][^\S\n]*[:.]?[^\S\n]*(\d{1,9})',
            r'N[UÚ]MERO[^\S\n]*[:.]?[^\S\n]*(\d{1,9})',
            r'NF-?e?\s*[Nn][°ºo.][^\S\n]*[:.]?[^\S\n]*(\d{1,9})',
            r'(?:NOTA\s*FISCAL|NF)\s*(?:ELETR[OÔ]NICA)?\s*[Nn]?\s*[°ºo.]?[^\S\n]*[:.]?[^\S\n]*(\d{1,9})',
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
            r'S[EÉ]RIE[^\S\n]*[:.]?[^\S\n]*(\d{1,3})',
            r'SER\.[^\S\n]*[:.]?[^\S\n]*(\d{1,3})',
        ]
        for pattern in patterns:
            match = re.search(pattern, self.texto_completo, re.IGNORECASE)
            if match:
                return match.group(1)
        return None

    def get_cnpj_emitente(self) -> Optional[str]:
        """Extrai CNPJ do emitente

        P3 fix: Exigir '/' no CNPJ para diferenciar de protocolo de autorizacao
        e IE que tambem tem 14 digitos. Buscar primeiro CNPJ antes de DESTINATARIO.
        """
        # Padrao CNPJ com '/' obrigatorio — elimina protocolos e IEs
        cnpj_pattern = r'\d{2}\.?\d{3}\.?\d{3}/\d{4}-?\d{2}'

        # Tentar antes de DESTINATARIO
        dest_match = re.search(r'DESTINAT[AÁ]RIO', self.texto_completo, re.IGNORECASE)
        texto_emitente = (
            self.texto_completo[:dest_match.start()] if dest_match else self.texto_completo
        )

        matches = re.findall(cnpj_pattern, texto_emitente)
        if matches:
            cnpj = re.sub(r'\D', '', matches[0])
            if len(cnpj) == 14:
                self.confianca += 0.1
                return cnpj

        # Fallback: primeiro CNPJ com '/' no texto completo
        matches = re.findall(cnpj_pattern, self.texto_completo)
        if matches:
            cnpj = re.sub(r'\D', '', matches[0])
            if len(cnpj) == 14:
                self.confianca += 0.1
                return cnpj

        return None

    def get_cnpj_destinatario(self) -> Optional[str]:
        """Extrai CNPJ do destinatario

        P3 fix: Exigir '/' no CNPJ. Buscar primeiro CNPJ apos DESTINATARIO.
        """
        cnpj_pattern = r'\d{2}\.?\d{3}\.?\d{3}/\d{4}-?\d{2}'

        # Buscar apos marcador de destinatario
        dest_match = re.search(r'DESTINAT[AÁ]RIO', self.texto_completo, re.IGNORECASE)
        if dest_match:
            texto_dest = self.texto_completo[dest_match.start():]
            matches = re.findall(cnpj_pattern, texto_dest)
            if matches:
                cnpj = re.sub(r'\D', '', matches[0])
                if len(cnpj) == 14:
                    return cnpj

        # Fallback: segundo CNPJ com '/' no texto completo
        matches = re.findall(cnpj_pattern, self.texto_completo)
        if len(matches) >= 2:
            cnpj = re.sub(r'\D', '', matches[1])
            if len(cnpj) == 14:
                return cnpj

        return None

    def get_valor_total(self) -> Optional[float]:
        """Extrai valor total da NF

        P4 fix: Layout tabular — 'VALOR TOTAL DA NOTA' e cabecalho, valor na proxima linha.
        Strategy 1: regex same-line com [^\\S\\n]* (nao cruzar newline)
        Strategy 2: localizar cabecalho, pegar ultimo token numerico da proxima linha
        Strategy 3: fallback na secao FATURA
        """
        # Strategy 1: same-line regex (nao cruza \n)
        patterns_sameline = [
            r'VALOR[^\S\n]*TOTAL[^\S\n]*DA[^\S\n]*NOTA[^\S\n]*[:.]?[^\S\n]*R?\$?[^\S\n]*([\d.,]+)',
            r'V\.[^\S\n]*TOTAL[^\S\n]*(?:DA[^\S\n]*)?NF[^\S\n]*[:.]?[^\S\n]*R?\$?[^\S\n]*([\d.,]+)',
            r'TOTAL[^\S\n]*GERAL[^\S\n]*[:.]?[^\S\n]*R?\$?[^\S\n]*([\d.,]+)',
        ]
        for pattern in patterns_sameline:
            match = re.search(pattern, self.texto_completo, re.IGNORECASE)
            if match:
                valor = self._parse_valor_br(match.group(1))
                if valor and valor > 0:
                    self.confianca += 0.1
                    return valor

        # Strategy 2: layout tabular — cabecalho + valor na proxima linha
        idx = self._encontrar_linha('VALOR', 'TOTAL', 'NOTA')
        if idx is None:
            idx = self._encontrar_linha('V.', 'TOTAL', 'NF')
        if idx is not None:
            linhas = self._linhas()
            if idx + 1 < len(linhas):
                tokens = self._tokens_numericos(linhas[idx + 1])
                if tokens:
                    # Ultimo token numerico da proxima linha (valor total e o ultimo campo)
                    valor = self._parse_valor_br(tokens[-1])
                    if valor and valor > 0:
                        self.confianca += 0.1
                        return valor

        # Strategy 3: secao FATURA (ex: 'Valor Original: R$ 7.360,87')
        match = re.search(
            r'(?:Valor\s*Original|Valor\s*Cobrado)[^\S\n]*:?[^\S\n]*R?\$?[^\S\n]*([\d.,]+)',
            self.texto_completo,
            re.IGNORECASE,
        )
        if match:
            valor = self._parse_valor_br(match.group(1))
            if valor and valor > 0:
                self.confianca += 0.05
                return valor

        return None

    def get_peso_bruto(self) -> Optional[float]:
        """Extrai peso bruto

        P5 fix: Layout tabular — 'PESO BRUTO PESO LIQUIDO' como cabecalhos na mesma linha.
        Valores na proxima linha: 'QTD ESP PESO_BRUTO PESO_LIQUIDO'.
        Strategy 1: same-line regex com [^\\S\\n]*
        Strategy 2: localizar linha com ambos cabecalhos, penultimo token numerico da proxima
        """
        # Strategy 1: same-line regex (nao cruza \n)
        patterns_sameline = [
            r'PESO[^\S\n]*BRUTO[^\S\n]*[:.]?[^\S\n]*([\d.,]+)',
            r'P\.[^\S\n]*BRUTO[^\S\n]*[:.]?[^\S\n]*([\d.,]+)',
        ]
        for pattern in patterns_sameline:
            match = re.search(pattern, self.texto_completo, re.IGNORECASE)
            if match:
                valor = self._parse_valor_br(match.group(1))
                if valor and valor > 0:
                    return valor

        # Strategy 2: layout tabular
        idx = self._encontrar_linha('PESO', 'BRUTO')
        if idx is not None:
            linhas = self._linhas()
            linha_cab = linhas[idx].upper()
            if 'QUIDO' in linha_cab and idx + 1 < len(linhas):
                # Cabecalho: PESO BRUTO  PESO LIQUIDO
                # Valores:   ... PESO_B  PESO_L
                tokens = self._tokens_numericos(linhas[idx + 1])
                if len(tokens) >= 2:
                    # Penultimo token = peso bruto, ultimo = peso liquido
                    valor = self._parse_valor_br(tokens[-2])
                    if valor and valor > 0:
                        return valor
            elif idx + 1 < len(linhas):
                # Peso bruto sozinho na linha
                tokens = self._tokens_numericos(linhas[idx + 1])
                if tokens:
                    valor = self._parse_valor_br(tokens[0])
                    if valor and valor > 0:
                        return valor

        return None

    def get_peso_liquido(self) -> Optional[float]:
        """Extrai peso liquido

        P6 fix: \\s* cruzava \\n e capturava QUANTIDADE em vez de peso.
        Strategy 1: same-line regex com [^\\S\\n]*
        Strategy 2: localizar 'PESO LIQUIDO', ultimo token numerico da proxima linha
        """
        # Strategy 1: same-line regex (nao cruza \n)
        patterns_sameline = [
            r'PESO[^\S\n]*L[IÍ]QUIDO[^\S\n]*[:.]?[^\S\n]*([\d.,]+)',
            r'P\.[^\S\n]*L[IÍ]QUIDO[^\S\n]*[:.]?[^\S\n]*([\d.,]+)',
        ]
        for pattern in patterns_sameline:
            match = re.search(pattern, self.texto_completo, re.IGNORECASE)
            if match:
                valor = self._parse_valor_br(match.group(1))
                if valor and valor > 0:
                    return valor

        # Strategy 2: layout tabular
        idx = self._encontrar_linha('PESO', 'QUIDO')
        if idx is not None:
            linhas = self._linhas()
            linha_cab = linhas[idx].upper()
            if 'BRUTO' in linha_cab and idx + 1 < len(linhas):
                # Cabecalho: PESO BRUTO  PESO LIQUIDO
                # Ultimo token = peso liquido
                tokens = self._tokens_numericos(linhas[idx + 1])
                if tokens:
                    valor = self._parse_valor_br(tokens[-1])
                    if valor and valor > 0:
                        return valor
            elif idx + 1 < len(linhas):
                # Peso liquido sozinho
                tokens = self._tokens_numericos(linhas[idx + 1])
                if tokens:
                    valor = self._parse_valor_br(tokens[-1])
                    if valor and valor > 0:
                        return valor

        return None

    def get_quantidade_volumes(self) -> Optional[int]:
        """Extrai quantidade de volumes

        P7 fix: Layout tabular — QUANTIDADE e cabecalho de coluna, valor na proxima linha.
        Strategy 1: same-line regex com [^\\S\\n]*
        Strategy 2: localizar 'QUANTIDADE' + 'ESPECIE' (guard), primeiro token numerico
        """
        # Strategy 1: same-line regex (nao cruza \n)
        patterns_sameline = [
            r'QUANTIDADE[^\S\n]*[:.]?[^\S\n]*(\d+)',
            r'QTD[^\S\n]*[:.]?[^\S\n]*(\d+)',
            r'VOLUMES?[^\S\n]*[:.]?[^\S\n]*(\d+)',
        ]
        for pattern in patterns_sameline:
            match = re.search(pattern, self.texto_completo, re.IGNORECASE)
            if match:
                try:
                    return int(match.group(1))
                except ValueError:
                    pass

        # Strategy 2: layout tabular com guard 'ESPECIE' (tipico de DANFE)
        idx = self._encontrar_linha('QUANTIDADE', 'ESP')
        if idx is None:
            idx = self._encontrar_linha('QUANTIDADE')
        if idx is not None:
            linhas = self._linhas()
            if idx + 1 < len(linhas):
                tokens = self._tokens_numericos(linhas[idx + 1])
                if tokens:
                    try:
                        valor = int(tokens[0].replace('.', '').replace(',', ''))
                        if valor > 0:
                            return valor
                    except ValueError:
                        pass

        return None

    def get_data_emissao(self) -> Optional[str]:
        """Extrai data de emissao"""
        # Strategy 1: same-line regex (nao cruza \n)
        patterns = [
            r'(?:DATA[^\S\n]*(?:DA[^\S\n]*)?EMISS[AÃ]O|EMITIDO[^\S\n]*EM)[^\S\n]*[:.]?[^\S\n]*(\d{2}[/.-]\d{2}[/.-]\d{4})',
        ]
        for pattern in patterns:
            match = re.search(pattern, self.texto_completo, re.IGNORECASE)
            if match:
                return match.group(1)

        # Strategy 2: layout tabular — cabecalho DATA EMISSAO, valor na proxima linha
        idx = self._encontrar_linha('DATA', 'EMISS')
        if idx is not None:
            linhas = self._linhas()
            if idx + 1 < len(linhas):
                date_match = re.search(r'\d{2}[/.-]\d{2}[/.-]\d{4}', linhas[idx + 1])
                if date_match:
                    return date_match.group(0)

        # Fallback: primeira data no formato BR
        match = re.search(r'(\d{2}/\d{2}/\d{4})', self.texto_completo)
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
