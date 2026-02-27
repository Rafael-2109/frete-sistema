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

    _UFS_BRASIL = frozenset({
        'AC', 'AL', 'AP', 'AM', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA',
        'MG', 'MS', 'MT', 'PA', 'PB', 'PE', 'PI', 'PR', 'RJ', 'RN',
        'RO', 'RR', 'RS', 'SC', 'SE', 'SP', 'TO',
    })

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
        """Extrai nome/razao social do emitente

        Strategy 1: 'Recebemos de [NOME] os produtos' (canhoto)
        Strategy 2: Texto antes de 'DANFE' na mesma linha (header)
        """
        # Strategy 1: canhoto
        match = re.search(
            r'Recebemos\s+de\s+(.+?)\s+os\s+produtos',
            self.texto_completo,
            re.IGNORECASE,
        )
        if match:
            nome = match.group(1).strip()
            if len(nome) >= 3:
                return nome

        # Strategy 2: texto antes de 'DANFE' na mesma linha
        linhas = self._linhas()
        for linha in linhas[:15]:  # Apenas area do header
            if 'DANFE' in linha.upper():
                parts = re.split(r'\s+DANFE\b', linha, flags=re.IGNORECASE)
                if parts and parts[0].strip():
                    nome = parts[0].strip()
                    if len(nome) >= 3:
                        return nome

        return None

    def get_nome_destinatario(self) -> Optional[str]:
        """Extrai nome/razao social do destinatario

        Strategy 1: Apos DESTINATARIO, localizar 'NOME / RAZAO SOCIAL' header,
                    extrair texto da proxima linha antes do CNPJ
        Strategy 2: 'Dest/Reme:' pattern no canhoto
        """
        # Strategy 1: secao DESTINATARIO tabular
        dest_idx = self._encontrar_linha('DESTINAT')
        if dest_idx is not None:
            linhas = self._linhas()
            nome_idx = None
            for i in range(dest_idx, min(dest_idx + 5, len(linhas))):
                upper = linhas[i].upper()
                if 'NOME' in upper and ('RAZ' in upper or 'SOCIAL' in upper):
                    nome_idx = i
                    break

            if nome_idx is not None and nome_idx + 1 < len(linhas):
                prox_linha = linhas[nome_idx + 1]
                # Extrair texto antes do padrao CNPJ
                cnpj_match = re.search(r'\d{2}\.?\d{3}\.?\d{3}/\d{4}', prox_linha)
                if cnpj_match:
                    nome = prox_linha[:cnpj_match.start()].strip()
                    if len(nome) >= 3:
                        return nome
                else:
                    nome = prox_linha.strip()
                    if len(nome) >= 3:
                        return nome

        # Strategy 2: canhoto 'Dest/Reme:'
        match = re.search(
            r'Dest/Reme:\s*(.+?)(?:\s+Valor\s+Total|\s*$)',
            self.texto_completo,
            re.IGNORECASE,
        )
        if match:
            nome = match.group(1).strip().rstrip('.')
            if len(nome) >= 3:
                return nome

        return None

    def get_uf_cidade_emitente(self) -> tuple:
        """Extrai UF e cidade do emitente (combinado para evitar busca duplicada)

        Strategy 1: Pattern 'CIDADE - UF - CEP:' na area do header (antes de DESTINATARIO)
        Strategy 2: Pattern 'CIDADE/UF' ou 'CIDADE - UF' com CEP proximo

        Returns:
            (uf, cidade) — qualquer um pode ser None
        """
        dest_idx = self._encontrar_linha('DESTINAT')
        linhas = self._linhas()
        limite = dest_idx if dest_idx else min(20, len(linhas))

        # Strategy 1: 'CIDADE - UF - CEP:'
        for i in range(limite):
            match = re.search(
                r'([A-ZÀ-Ú][A-ZÀ-Ú\s]+?)\s*-\s*([A-Z]{2})\s*-\s*CEP',
                linhas[i],
            )
            if match:
                cidade = match.group(1).strip()
                uf = match.group(2)
                if uf in self._UFS_BRASIL and len(cidade) >= 2:
                    return (uf, cidade)

        # Strategy 2: 'CIDADE/UF' pattern (sem hifen)
        for i in range(limite):
            match = re.search(
                r'([A-ZÀ-Ú][A-ZÀ-Ú\s]+?)\s*/\s*([A-Z]{2})\b',
                linhas[i],
            )
            if match:
                cidade = match.group(1).strip()
                uf = match.group(2)
                if uf in self._UFS_BRASIL and len(cidade) >= 2:
                    return (uf, cidade)

        return (None, None)

    def get_uf_cidade_destinatario(self) -> tuple:
        """Extrai UF e cidade do destinatario (combinado)

        Strategy 1: Apos DESTINATARIO, localizar 'MUNICIPIO' + 'UF' header,
                    extrair cidade e UF da proxima linha
        Strategy 2: Tokens com UF valida na proxima linha apos MUNICIPIO

        Returns:
            (uf, cidade) — qualquer um pode ser None
        """
        dest_idx = self._encontrar_linha('DESTINAT')
        if dest_idx is None:
            return (None, None)

        linhas = self._linhas()

        # Encontrar header MUNICIPIO + UF apos DESTINATARIO
        mun_idx = None
        # Limitar busca: parar antes de TRANSPORTADOR ou FATURA
        limite_fim = len(linhas)
        for i in range(dest_idx + 1, len(linhas)):
            upper = linhas[i].upper()
            if 'TRANSPORTAD' in upper or 'FATURA' in upper:
                limite_fim = i
                break

        for i in range(dest_idx + 1, limite_fim):
            upper = linhas[i].upper()
            if 'MUNIC' in upper and 'UF' in upper:
                mun_idx = i
                break

        if mun_idx is None or mun_idx + 1 >= len(linhas):
            return (None, None)

        prox_linha = linhas[mun_idx + 1]
        tokens = prox_linha.split()

        # Encontrar primeiro token que e UF valida
        cidade_parts = []
        uf_encontrada = None
        for token in tokens:
            token_upper = token.strip().upper()
            if token_upper in self._UFS_BRASIL and not cidade_parts:
                # UF antes de qualquer texto de cidade — improvavel, skip
                continue
            if token_upper in self._UFS_BRASIL and cidade_parts:
                uf_encontrada = token_upper
                break
            cidade_parts.append(token)

        cidade = ' '.join(cidade_parts).strip() if cidade_parts else None
        if cidade and len(cidade) < 2:
            cidade = None

        return (uf_encontrada, cidade)

    def get_itens_produto(self) -> List[Dict]:
        """Extrai itens de produto da secao DADOS DOS PRODUTOS / SERVICOS

        Layout tabular tipico (pdfplumber extrai colunas lado a lado):
            CODIGO PRODUTO | DESCRICAO | NCM | CST | CFOP | UNID | QTDE | V.UNIT | ...
            JET MOTO CHEFE | JET MOTO CHEFE | 87116000 | 460 | 5405 | UN | 3,00 | 7.220,0000 | ...

        Ancora: NCM (8 digitos) + CST (2-3 digitos) + CFOP (4 digitos).
        Linhas com NCM = inicio de produto. Linhas sem NCM = continuacao
        (codigo do produto wrapping na coluna estreita).

        Returns:
            Lista de dicts com: codigo_produto, descricao, ncm, cfop, unidade,
                                quantidade, valor_unitario, valor_total_item
        """
        itens = []

        # Encontrar inicio e fim da secao de produtos
        prod_idx = self._encontrar_linha('DADOS', 'PRODUTOS')
        if prod_idx is None:
            return itens

        linhas = self._linhas()

        fim_idx = len(linhas)
        for i in range(prod_idx + 1, len(linhas)):
            upper = linhas[i].upper()
            if 'DADOS ADICIONAIS' in upper or 'INFORMAÇÕES COMPLEMENTARES' in upper:
                fim_idx = i
                break

        # Agrupar por produto: linha com NCM inicia produto, linhas sem NCM sao continuacao
        ncm_pattern = re.compile(r'\d{8}\s+\d{2,3}\s+\d{4}')
        blocos = []  # [(ncm_line, [continuations])]
        ncm_line_atual = None
        continuacoes = []

        for i in range(prod_idx + 1, fim_idx):
            linha = linhas[i].strip()
            if not linha:
                continue

            if ncm_pattern.search(linha):
                # Nova linha de produto — salvar bloco anterior
                if ncm_line_atual:
                    blocos.append((ncm_line_atual, continuacoes))
                ncm_line_atual = linha
                continuacoes = []
            elif ncm_line_atual:
                # Continuacao do produto atual (codigo wrapping)
                continuacoes.append(linha)
            # else: linha de cabecalho antes do primeiro produto — ignorar

        if ncm_line_atual:
            blocos.append((ncm_line_atual, continuacoes))

        # Parsear cada bloco
        for ncm_line, conts in blocos:
            item = self._parsear_linha_produto(ncm_line, conts)
            if item:
                itens.append(item)

        return itens

    def _separar_codigo_descricao(self, texto: str) -> tuple:
        """Separa codigo e descricao do texto mesclado antes do NCM

        pdfplumber extrai colunas lado a lado: 'COD DESC' vira 'COD DESC' ou
        'COD1 COD2 DESC1 DESC2' quando codigo e descricao compartilham palavras.
        Heuristica: encontrar onde o primeiro token se repete — marca inicio da descricao.

        Ex: 'JET MOTO JET MOTO CHEFE' → codigo='JET MOTO', descricao='JET MOTO CHEFE'

        Returns: (codigo, descricao)
        """
        tokens = texto.split()
        if not tokens:
            return (texto, texto)

        primeiro = tokens[0].upper()
        for i in range(1, len(tokens)):
            if tokens[i].upper() == primeiro:
                codigo = ' '.join(tokens[:i])
                descricao = ' '.join(tokens[i:])
                return (codigo, descricao)

        # Sem repeticao — codigo e descricao sao o mesmo texto
        return (texto, texto)

    def _parsear_linha_produto(self, ncm_line: str, continuacoes: Optional[List[str]] = None) -> Optional[Dict]:
        """Parseia uma linha de produto usando NCM como ancora

        Args:
            ncm_line: Linha principal contendo NCM + dados numericos
            continuacoes: Linhas extras (codigo do produto wrapping)

        Formato tipico ncm_line:
        'JET MOTO JET MOTO CHEFE 87116000 460 5405 UN 3,00 7.220,0000 0,00 21.660,00 ...'
                                  ^NCM    ^CST^CFOP^UN^QTD ^V.UNIT    ^DESC^V.LIQ
        """
        if not continuacoes:
            continuacoes = []

        # Encontrar NCM (8 digitos) + CST (2-3 digitos) + CFOP (4 digitos)
        match = re.search(
            r'(\d{8})\s+(\d{2,3})\s+(\d{4})\s+(\w{1,5})\s+([\d.,]+)\s+([\d.,]+)',
            ncm_line,
        )
        if not match:
            return None

        ncm = match.group(1)
        cfop = match.group(3)
        unidade = match.group(4)
        quantidade = self._parse_valor_br(match.group(5))
        valor_unitario = self._parse_valor_br(match.group(6))

        # Extrair valor total: numeros apos NCM
        texto_apos = ncm_line[match.start():]
        numeros = re.findall(r'[\d.,]+', texto_apos)
        # [NCM, CST, CFOP, QTD, V.UNIT, V.DESC, V.LIQ, BASE_ICMS, V.ICMS, V.IPI, ...]
        valor_total_item = None
        if len(numeros) >= 7:
            valor_total_item = self._parse_valor_br(numeros[6])

        # Texto antes do NCM = codigo + descricao mesclados
        texto_antes = ncm_line[:match.start()].strip()
        codigo, descricao = self._separar_codigo_descricao(texto_antes)

        # Continuacoes = codigo wrapping — anexar ao codigo
        if continuacoes:
            codigo = codigo + ' ' + ' '.join(continuacoes)

        return {
            'codigo_produto': codigo.strip(),
            'descricao': descricao.strip(),
            'ncm': ncm,
            'cfop': cfop,
            'unidade': unidade,
            'quantidade': quantidade,
            'valor_unitario': valor_unitario,
            'valor_total_item': valor_total_item,
        }

    def get_todas_informacoes(self) -> Dict:
        """Extrai todas as informacoes disponiveis"""
        self.confianca = 0.0

        uf_emit, cidade_emit = self.get_uf_cidade_emitente()
        uf_dest, cidade_dest = self.get_uf_cidade_destinatario()

        resultado = {
            'chave_acesso_nf': self.get_chave_acesso(),
            'numero_nf': self.get_numero_nf(),
            'serie_nf': self.get_serie(),
            'data_emissao_str': self.get_data_emissao(),
            'data_emissao': None,
            'cnpj_emitente': self.get_cnpj_emitente(),
            'nome_emitente': self.get_nome_emitente(),
            'uf_emitente': uf_emit,
            'cidade_emitente': cidade_emit,
            'cnpj_destinatario': self.get_cnpj_destinatario(),
            'nome_destinatario': self.get_nome_destinatario(),
            'uf_destinatario': uf_dest,
            'cidade_destinatario': cidade_dest,
            'valor_total': self.get_valor_total(),
            'peso_bruto': self.get_peso_bruto(),
            'peso_liquido': self.get_peso_liquido(),
            'quantidade_volumes': self.get_quantidade_volumes(),
            'itens': self.get_itens_produto(),
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
