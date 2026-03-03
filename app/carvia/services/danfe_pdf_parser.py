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

    def _encontrar_secao_destinatario(self) -> Optional[int]:
        """Encontra a SECAO DESTINATARIO/REMETENTE (ignora 'DESTINATARIO' do canhoto).

        DANFEs reais tem 'DESTINATARIO' no canhoto (primeiras linhas) e
        'DESTINATARIO/REMETENTE' na secao formal. Usar primeira ocorrencia
        como ancora causa bugs em cnpj, nome, uf/cidade.
        """
        # Preferir "DESTINATARIO/REMETENTE" (secao formal com barra)
        idx = self._encontrar_linha('DESTINAT', 'REMETENTE')
        if idx is not None:
            return idx
        # Fallback: "DESTINATARIO" que NAO esteja no canhoto (primeiras 5 linhas)
        linhas = self._linhas()
        for i, linha in enumerate(linhas):
            if i < 5:
                continue
            if 'DESTINAT' in linha.upper():
                return i
        # Ultimo recurso: qualquer ocorrencia
        return self._encontrar_linha('DESTINAT')

    def _completar_cidade_cross_line(self, linhas: List[str], linha_idx: int, cidade: str) -> str:
        """Verifica se nome da cidade foi cortado entre linhas e completa se necessario.

        Problema: pdfplumber pode dividir "RIO DE JANEIRO" em:
          L007: "... - RIO DE 0 - ENTRADA ..."
          L008: "JANEIRO - RJ - CEP: ..."
        Strategy 1a/1b captura "JANEIRO" mas o prefixo "RIO DE" esta na linha anterior.

        Fix: busca na linha anterior por pattern "[CIDADE] D[EOA]S? <digito>" antes
        de checkbox entrada/saida, e prefixa ao nome da cidade.
        """
        if linha_idx <= 0:
            return cidade
        prev = linhas[linha_idx - 1]
        # Buscar "PALAVRA(S) DE|DO|DA|DOS|DAS" seguido de digito (checkbox entrada/saida)
        prefix_m = re.search(
            r'([A-ZÀ-Ú][A-ZÀ-Ú\s]*\s+D[EOA]S?)\s+\d',
            prev,
        )
        if prefix_m:
            prefix = prefix_m.group(1).strip()
            # Evitar falsos positivos: "CHAVE DE", "BASE DE" etc nao sao cidades
            skip_words = {'CHAVE', 'BASE', 'NOTA', 'DATA', 'INSCRIÇÃO', 'VALOR'}
            first_word = prefix.split()[0].upper() if prefix else ''
            if first_word not in skip_words:
                cidade = prefix + ' ' + cidade
        return cidade

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

        # Buscar apos SECAO DESTINATARIO/REMETENTE (ignora canhoto)
        dest_idx = self._encontrar_secao_destinatario()
        if dest_idx is not None:
            linhas = self._linhas()
            # Converter indice de linha para posicao de caractere
            offset = sum(len(l) + 1 for l in linhas[:dest_idx])
            texto_dest = self.texto_completo[offset:]
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
            # VOLUMES? REMOVIDO: "Volumes" como ESPECIE na linha de valores
            # capturava "13" de "13.176,000" (peso bruto) em vez da quantidade real.
            # Strategy 2 (tabular com guard ESPECIE) trata esse caso corretamente.
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
        """Extrai data de emissao

        Suporta ano com 2 ou 4 digitos (DD/MM/YY ou DD/MM/YYYY).
        DANFEs compactas (ex: Laiouns) usam '06/01/26' em vez de '06/01/2026'.
        """
        # Strategy 1: same-line regex (nao cruza \n)
        patterns = [
            r'(?:DATA[^\S\n]*(?:DA[^\S\n]*)?EMISS[AÃ]O|EMITIDO[^\S\n]*EM)[^\S\n]*[:.]?[^\S\n]*(\d{2}[/.-]\d{2}[/.-]\d{2,4})',
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
                date_match = re.search(r'\d{2}[/.-]\d{2}[/.-]\d{2,4}', linhas[idx + 1])
                if date_match:
                    return date_match.group(0)

        # Fallback: primeira data no formato BR (4 digitos preferencial, depois 2)
        match = re.search(r'(\d{2}/\d{2}/\d{4})', self.texto_completo)
        if match:
            return match.group(1)
        match = re.search(r'(\d{2}/\d{2}/\d{2})\b', self.texto_completo)
        if match:
            return match.group(1)
        return None

    def get_nome_emitente(self) -> Optional[str]:
        """Extrai nome/razao social do emitente

        Strategy 1: 'Recebemos de [NOME] os produtos' (canhoto)
        Strategy 2: Texto antes de 'DANFE' na mesma linha (header)
        Strategy 3: Backward search a partir do CNPJ emitente
        """
        # Headers/palavras que NAO sao nome de emitente
        _REJECT_EMITENTE = frozenset({
            'DANFE', 'MODELO', 'SERIE', 'NUMERO', 'FOLHA', 'FL', 'SAIDA',
            'ENTRADA', 'DOCUMENTO', 'AUXILIAR', 'NOTA', 'FISCAL', 'ELETRONICA',
            'PROTOCOLO', 'CHAVE', 'ACESSO', 'NATUREZA', 'OPERACAO',
        })

        def _is_valid_nome(nome: str) -> bool:
            """Valida que nome nao e header/keyword DANFE"""
            if not nome or len(nome) < 5:
                return False
            # Rejeitar se o nome inteiro e uma keyword
            if nome.upper().strip() in _REJECT_EMITENTE:
                return False
            # Rejeitar se TODAS as palavras sao keywords (ex: "NOTA FISCAL ELETRONICA")
            words = nome.upper().split()
            if all(w in _REJECT_EMITENTE for w in words):
                return False
            return True

        # Strategy 1: canhoto — "Recebemos de [NOME] os produtos"
        # Variante: "REEBEMOS" (typo em DANFEs compactas)
        match = re.search(
            r'R[E]+CEBEMOS\s+de\s+(.+?)\s+os\s+produtos',
            self.texto_completo,
            re.IGNORECASE,
        )
        if match:
            nome = match.group(1).strip()
            if _is_valid_nome(nome):
                return nome

        # Strategy 2: texto antes de 'DANFE' na mesma linha
        linhas = self._linhas()
        for linha in linhas[:15]:  # Apenas area do header
            if 'DANFE' in linha.upper():
                parts = re.split(r'\s+DANFE\b', linha, flags=re.IGNORECASE)
                if parts and parts[0].strip():
                    nome = parts[0].strip()
                    if _is_valid_nome(nome):
                        return nome

        # Strategy 3: backward search a partir do CNPJ emitente
        # DANFEs compactas: nome do emitente esta poucas linhas ACIMA do CNPJ
        # Ex: L06 "Laiouns Importacao e Exportacao Ltda", L11 "CNPJ: 09.089.839/0001-12"
        dest_idx = self._encontrar_secao_destinatario()
        limite_cnpj = dest_idx if dest_idx else min(20, len(linhas))
        cnpj_line_idx = None
        for i in range(limite_cnpj):
            if re.search(r'CNPJ[:\s]*\d{2}\.?\d{3}\.?\d{3}', linhas[i]):
                cnpj_line_idx = i
                break

        if cnpj_line_idx is not None:
            # Varrer backward: buscar linha com texto alfabetico >= 5 chars
            for i in range(cnpj_line_idx - 1, max(0, cnpj_line_idx - 8), -1):
                candidato = linhas[i].strip()
                if not candidato:
                    continue
                # Pular linhas que sao puramente numericas ou contem CNPJ/CEP
                if re.match(r'^[\d\s./-]+$', candidato):
                    continue
                if re.search(r'CEP[:\s]*\d{5}', candidato, re.IGNORECASE):
                    continue
                # Pular linhas de endereco (contem numero de rua + bairro)
                if re.search(
                    r'(?:'
                    r'RUA|R\.\s|'
                    r'AV\.?\s|AVENIDA|'
                    r'ROD\.?\s|RODOVIA|'
                    r'EST\.?\s|ESTR\.?\s|ESTRADA|'
                    r'TV\.?\s|TRAV\.?\s|TRAVESSA|'
                    r'AL\.?\s|ALAMEDA|'
                    r'PCA\.?\s|PRA[CÇ]A|'
                    r'LOTE|LT\.?\s|QUADRA|QD\.?\s|'
                    r'COND\.?\s|CONDOMINIO|'
                    r'BR\s*-?\s*\d{3}'
                    r')\b',
                    candidato, re.IGNORECASE,
                ):
                    continue
                # Pular bairro: linha imediatamente ACIMA de "Cidade - UF - CEP"
                # (bairro = palavra curta logo antes da cidade, ex: "Olaria" antes de "Rio de Janeiro - RJ - CEP")
                if i + 1 < len(linhas) and re.search(r'-\s*[A-Z]{2}\s*-\s*CEP', linhas[i + 1]):
                    continue
                # Pular linhas com padrao de endereco: "texto, NUMERO" (logradouro + numero)
                if re.search(r',\s*\d{1,5}\b', candidato):
                    continue
                # Pular "CONTROLE DO FISCO" e similares
                if re.search(r'CONTROLE|FISCO|INSCRI[ÇC]', candidato, re.IGNORECASE):
                    continue
                if _is_valid_nome(candidato):
                    return candidato

        return None

    def get_nome_destinatario(self) -> Optional[str]:
        """Extrai nome/razao social do destinatario

        Strategy 1 (merged): Apos DESTINATARIO, buscar 'NOME <dados> MUNICIPIO' na mesma linha
        Strategy 2 (tabular): Apos DESTINATARIO, localizar 'NOME' header, extrair proxima linha
        Strategy 3: 'Dest/Reme:' pattern no canhoto
        """
        dest_idx = self._encontrar_secao_destinatario()
        if dest_idx is not None:
            linhas = self._linhas()

            # Strategy 1 (merged): NOME + dados + MUNICIPIO na mesma linha
            # Ex: "NOME PABLO VASCONCELLOS LEAL MUNICIPIORIO GRANDE - RS CEP96210-080"
            # Variante: "MUNICIPIO" ou "MUNICIP" (pdfplumber pode truncar/merge)
            for i in range(dest_idx, min(dest_idx + 5, len(linhas))):
                upper = linhas[i].upper()
                if 'NOME' in upper and 'MUNIC' in upper:
                    # Extrair texto entre NOME e MUNICIPIO
                    match = re.search(
                        r'NOME\s+(.+?)\s+MUNIC',
                        linhas[i],
                        re.IGNORECASE,
                    )
                    if match:
                        nome = match.group(1).strip()
                        if len(nome) >= 3:
                            return nome

            # Strategy 2 (tabular): header 'NOME' (com ou sem 'RAZAO SOCIAL'), dados na proxima linha
            nome_idx = None
            for i in range(dest_idx, min(dest_idx + 5, len(linhas))):
                upper = linhas[i].upper()
                # Aceitar "NOME / RAZAO SOCIAL" OU apenas "NOME"
                if 'NOME' in upper:
                    # Verificar que nao e a linha merged (Strategy 1 ja tentou)
                    if 'MUNIC' not in upper:
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

        # Strategy 3: canhoto 'Dest/Reme:'
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
        dest_idx = self._encontrar_secao_destinatario()
        linhas = self._linhas()
        limite = dest_idx if dest_idx else min(20, len(linhas))

        # Strategy 0: cidade mixed-case NO INICIO da linha + " - UF - CEP"
        # Ex: "Rio de Janeiro - RJ - CEP: 21031-490" — cidade mixed-case sem "-" antes
        for i in range(limite):
            match = re.search(
                r'^([A-Za-zÀ-ÿ][A-Za-zÀ-ÿ\s]+?)\s*-\s*([A-Z]{2})\s*-\s*CEP',
                linhas[i],
            )
            if match:
                cidade = match.group(1).strip()
                uf = match.group(2)
                if uf in self._UFS_BRASIL and len(cidade) >= 2:
                    cidade = self._completar_cidade_cross_line(linhas, i, cidade)
                    return (uf, cidade)

        # Strategy 1a: 'CIDADE - UF - CEP:' (all-uppercase city)
        for i in range(limite):
            match = re.search(
                r'([A-ZÀ-Ú][A-ZÀ-Ú\s]+?)\s*-\s*([A-Z]{2})\s*-\s*CEP',
                linhas[i],
            )
            if match:
                cidade = match.group(1).strip()
                uf = match.group(2)
                if uf in self._UFS_BRASIL and len(cidade) >= 2:
                    # Cross-line fix: cidade pode ter sido cortada entre linhas
                    # Ex: L007 "... RIO DE 0 - ENTRADA" + L008 "JANEIRO - RJ - CEP:"
                    cidade = self._completar_cidade_cross_line(linhas, i, cidade)
                    return (uf, cidade)

        # Strategy 1b: '... - Cidade Mixed Case - UF - CEP:' (mixed case)
        # DANFEs podem ter enderecos em mixed case: "Santana de Parnaiba - SP - CEP"
        for i in range(limite):
            match = re.search(
                r'-\s*([^-]{2,}?)\s*-\s*([A-Z]{2})\s*-\s*CEP',
                linhas[i],
            )
            if match:
                cidade = match.group(1).strip()
                uf = match.group(2)
                if uf in self._UFS_BRASIL and len(cidade) >= 2:
                    cidade = self._completar_cidade_cross_line(linhas, i, cidade)
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

        # Strategy 3: Multi-line layout (pdfplumber split cells em linhas separadas)
        # Ex Nacom: L012 "Santana de Parnaiba 0 - Entrada ...", L014 "SP", L016 "CEP: 06530-581"
        # UF aparece sozinha numa linha, CEP em outra, cidade acima
        cep_idx = None
        for i in range(limite):
            if re.search(r'CEP[:\s]*\d{5}', linhas[i], re.IGNORECASE):
                cep_idx = i
                break

        if cep_idx is not None:
            # Buscar UF backward a partir da linha do CEP
            uf_found = None
            uf_line_idx = None
            for i in range(cep_idx - 1, max(0, cep_idx - 5), -1):
                token = linhas[i].strip()
                if len(token) == 2 and token.upper() in self._UFS_BRASIL:
                    uf_found = token.upper()
                    uf_line_idx = i
                    break

            if uf_found and uf_line_idx is not None:
                # Cidade esta acima da linha da UF
                for i in range(uf_line_idx - 1, max(0, uf_line_idx - 4), -1):
                    line = linhas[i].strip()
                    # Extrair texto antes do primeiro digito (ex: "Santana de Parnaiba 0 - Entrada")
                    m = re.match(r'([A-Za-zÀ-ÿ][A-Za-zÀ-ÿ\s]+?)(?:\s+\d|\s*-\s*(?:Entrada|Sa[ií]da)|\s*$)', line, re.IGNORECASE)
                    if m:
                        cidade = m.group(1).strip()
                        if len(cidade) >= 3:
                            return (uf_found, cidade)

        return (None, None)

    def get_uf_cidade_destinatario(self) -> tuple:
        """Extrai UF e cidade do destinatario (combinado)

        Strategy 1 (merged): MUNICIPIO + cidade + UF + CEP na mesma linha
        Strategy 2 (tabular): Header 'MUNICIPIO' + 'UF', dados na proxima linha

        Returns:
            (uf, cidade) — qualquer um pode ser None
        """
        dest_idx = self._encontrar_secao_destinatario()
        if dest_idx is None:
            return (None, None)

        linhas = self._linhas()

        # Limitar busca: parar antes de TRANSPORTADOR ou FATURA
        limite_fim = len(linhas)
        for i in range(dest_idx + 1, len(linhas)):
            upper = linhas[i].upper()
            if 'TRANSPORTAD' in upper or 'FATURA' in upper:
                limite_fim = i
                break

        # Strategy 1 (merged): MUNICIPIO + cidade + " - UF" + CEP na mesma linha
        # Ex: "NOME PABLO VASCONCELLOS LEAL MUNICIPIORIO GRANDE - RS CEP96210-080"
        # pdfplumber pode colar "MUNICIPIO" com cidade: "MUNICIPIORIO GRANDE"
        for i in range(dest_idx + 1, limite_fim):
            upper = linhas[i].upper()
            if 'MUNIC' in upper:
                # Pattern: MUNICIPIO? + cidade + " - " + UF(2) + CEP/fim
                # "MUNICIPIO?" captura "MUNICIPIO" colado ou separado
                match = re.search(
                    r'MUNIC[IÍ]PIO?\s*(.+?)\s*-\s*([A-Z]{2})\s*(?:CEP|$)',
                    linhas[i],
                    re.IGNORECASE,
                )
                if match:
                    cidade = match.group(1).strip()
                    uf = match.group(2).upper()
                    if uf in self._UFS_BRASIL and len(cidade) >= 2:
                        # Limpar cidade: remover "UF" header residual
                        cidade = re.sub(r'\bUF\b', '', cidade).strip()
                        if len(cidade) >= 2:
                            return (uf, cidade)

        # Strategy 2 (tabular): header MUNICIPIO + UF, dados na proxima linha
        mun_idx = None
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
        # Layout: "Jaboatao dos Guararapes (81) 3224-0703 PE 099769654 11:10:54"
        # Cidade = tokens ate telefone, UF = token 2-letras valido APOS telefone
        cidade_parts = []
        uf_encontrada = None
        past_phone = False
        for token in tokens:
            token_upper = token.strip().upper()
            if token_upper in self._UFS_BRASIL and not cidade_parts:
                # UF antes de qualquer texto de cidade — improvavel, skip
                continue
            if token_upper in self._UFS_BRASIL and cidade_parts:
                uf_encontrada = token_upper
                break
            # Telefone/fax — ex: '(81)', '3224-0703' — nao acumular, mas CONTINUAR buscando UF
            if token.startswith('(') or re.match(r'^\d+-\d+', token):
                past_phone = True
                continue
            if not past_phone:
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
        linhas = self._linhas()

        # Encontrar TODAS as secoes de produtos (multi-pagina: header repetido em cada pagina)
        # DANFEs usam "DADOS DOS PRODUTOS" (plural) ou "DADOS DO PRODUTO" (singular)
        # re.match exige "DADOS" no INICIO da linha — evita falso positivo tipo
        # "TRANSPORTADOR / VOLUMES TRANSPORTADOS DADOS DO PRODUTO" (pdfplumber merge)
        prod_starts = []
        for i, linha in enumerate(linhas):
            upper = linha.upper().strip()
            if re.match(r'DADOS\s+D[OE]S?\s+PRODUTO', upper):
                prod_starts.append(i)

        if not prod_starts:
            logger.debug("get_itens_produto: secao DADOS PRODUTO(S) nao encontrada")
            return itens

        # Range de busca: do primeiro header de produto ate o primeiro DADOS ADICIONAIS
        # apos o ultimo prod_start. Isso evita que "CONTINUACAO DAS INFORMACOES"
        # na pagina 2 (sem produtos) estenda o range para texto nao-produto.
        # Para multi-pagina com produtos em ambas paginas (NOTCO), section_boundary
        # PARA coleta de continuacoes ao atingir ISSQN/DADOS ADICIONAIS/header,
        # enquanto inline_metadata pula linhas de lote/pedido sem interromper.
        inicio = prod_starts[0]
        last_prod_start = prod_starts[-1]
        fim_idx = len(linhas)
        for i in range(last_prod_start + 1, len(linhas)):
            upper = linhas[i].upper().strip()
            if 'DADOS ADICIONAIS' in upper or 'INFORMAÇÕES COMPLEMENTARES' in upper:
                fim_idx = i
                break

        logger.debug(f"get_itens_produto: {len(prod_starts)} secao(oes) produto, range L{inicio}..L{fim_idx}")

        # Agrupar por produto: linha com NCM inicia produto, linhas sem NCM sao continuacao
        # NCM (8 dig) + O/CST (1-3 dig, possivelmente split: "3 00") + CFOP (4 dig, OPCIONAL)
        # DANFEs compactas (ex: Laiouns) omitem CFOP. Guard: apos NCM+CST exigir unidade
        # (1-5 chars alfa) em ate 2 tokens para evitar falsos positivos sem CFOP.
        ncm_pattern = re.compile(r'\d{8}\s+\d{1,3}(?:\s+\d{2})?(?:\s+\d{4}|\s+[A-Za-z]{1,5}\s)')

        # --- Dois niveis de filtro para linhas sem NCM ---

        # SECTION BOUNDARIES: indicam fim da area de produtos.
        # Quando encontradas, PARAR de coletar continuacoes do item atual.
        # Multi-pagina NOTCO: ISSQN + DADOS ADICIONAIS + header pag.2 aparecem
        # ENTRE o ultimo produto da pag.1 e o primeiro da pag.2.
        section_boundary = re.compile(
            r'C[AÁ]LCULO DO ISSQN|DADOS ADICIONAIS|'
            r'INFORMA[ÇC][ÕO]ES COMPLEMENTARES|RESERVADO AO FISCO|'
            r'\bDANFE\b|DOCUMENTO AUXILIAR|NOTA FISCAL ELETR|'
            r'DADOS\s+D[OE]S?\s+PRODUTO|'
            r'FOLHA\s+\d|CHAVE DE ACESSO|PROTOCOLO DE AUTORIZA|'
            r'NATUREZA DA OPERA|'
            r'INSCRIÇÃO ESTADUAL|INSCRI[ÇC][AÃ]O MUNICIPAL|'
            r'CONSULTA DE AUTENTICIDADE|'
            r'TRANSPORTADOR\s*/\s*VOLUMES|'
            r'VALOR TOTAL DOS SERVI',
            re.IGNORECASE,
        )

        # INLINE METADATA: info de lote/pedido/logistica impressa logo apos o produto.
        # Pular a linha mas CONTINUAR coletando continuacoes.
        inline_metadata = re.compile(
            r'ICMS|FCP|MVA|Base\s+.+ST|Al[ií]quota|Redu[çc][aã]o|'
            r'Lote:|Data de Validade|'
            r'No Ped:|Dep\.\s*de\s*Sa[ií]da|Venc:|Cod\s*Material|'
            r'Inf\.\s*Contribuinte|LOCAL DE SA[IÍ]DA|Material Novo:|'
            r'SITUADA\s+N[OA]\s|COD\.?\s*PROD|DESCRI[ÇC][ÃA]O DO PRODUTO|'
            r'www\.\w+\.gov\.br',
            re.IGNORECASE,
        )
        blocos = []  # [(ncm_line, [continuations])]
        ncm_line_atual = None
        continuacoes = []
        # Limite de continuacoes por produto: descricoes DANFE raramente wrappam
        # mais que 2 linhas. Excesso = lixo (ISSQN, header pag.2, etc.)
        MAX_CONTINUACOES = 3

        for i in range(inicio + 1, fim_idx):
            linha = linhas[i].strip()
            if not linha:
                continue

            has_ncm = ncm_pattern.search(linha)

            if has_ncm:
                # Nova linha de produto — salvar bloco anterior
                if ncm_line_atual:
                    blocos.append((ncm_line_atual, continuacoes))
                ncm_line_atual = linha
                continuacoes = []
            elif ncm_line_atual and len(continuacoes) < MAX_CONTINUACOES:
                # SECTION BOUNDARY: saimos da area de produtos → finalizar item atual.
                # Multi-pagina: ISSQN + DADOS ADICIONAIS + header pag.2 aparecem entre
                # o ultimo produto da pag.1 e o primeiro da pag.2. Sem esse break,
                # texto de endereco/cabecalho vira continuacao do ultimo produto.
                if section_boundary.search(linha):
                    blocos.append((ncm_line_atual, continuacoes))
                    ncm_line_atual = None
                    continuacoes = []
                    continue
                # INLINE METADATA: info lote/pedido — pular mas continuar coletando
                if inline_metadata.search(linha):
                    continue
                # Filtrar fragmentos curtos numericos (date wrapping: "26" de "01/04/2026")
                if len(linha) <= 4 and linha.isdigit():
                    continue
                # Filtrar linhas puramente numericas 5+ dig — "Cod Material Novo" orphan
                # Ex: "10000606" sozinho na linha (layout estreito NOTCO)
                if re.match(r'^\d{5,}$', linha):
                    continue
                # Filtrar datas standalone DD/MM/YYYY — "Venc:" orphan
                # Ex: "19/08/2026" sozinho na linha (layout estreito NOTCO)
                if re.match(r'^\d{1,2}/\d{2}/\d{4}$', linha):
                    continue
                # Filtrar linhas de dados fiscais: 3+ valores decimais (ISSQN/imposto)
                # Ex: "140172 0,00 0,00 0,00" ou "0,00 0,00 0,00 0,00"
                if len(re.findall(r'\d+,\d+', linha)) >= 3:
                    continue
                # Filtrar linhas com CNPJ (XX.XXX.XXX/XXXX-XX) — secao complementar
                if re.search(r'\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}', linha):
                    continue
                # Continuacao do produto atual (descricao wrapping)
                continuacoes.append(linha)
            # else: linha de cabecalho antes do primeiro produto — ignorar

        if ncm_line_atual:
            blocos.append((ncm_line_atual, continuacoes))

        logger.debug(f"get_itens_produto: {len(blocos)} blocos NCM encontrados")

        # Parsear cada bloco
        for idx, (ncm_line, conts) in enumerate(blocos):
            item = self._parsear_linha_produto(ncm_line, conts)
            if item:
                itens.append(item)
            else:
                logger.warning(f"get_itens_produto: bloco {idx} FALHOU parse: {ncm_line[:100]}")

        return itens

    def _separar_codigo_descricao(self, texto: str) -> tuple:
        """Separa codigo e descricao do texto mesclado antes do NCM

        pdfplumber extrai colunas CODIGO PRODUTO e DESCRICAO lado a lado, produzindo
        texto mesclado. 4 heuristicas em ordem de especificidade:

        H1: Codigo numerico 5+ digitos (Nacom: "421016 AZEITONA...")
        H2: Codigo com dash (Laiouns: "MT-B2 BIKE ELETRICA B2")
        H3: Repeat detection (Q.p.a: "X12 MOTO X12 MOTO CHEFE")
        H4: Codigo alfanumerico curto (letras+digitos, <=10 chars)

        Returns: (codigo, descricao)
        """
        tokens = texto.split()
        if not tokens:
            return (texto, texto)

        primeiro = tokens[0]
        resto = ' '.join(tokens[1:]) if len(tokens) > 1 else ''

        # H1: Codigo puramente numerico (5+ digitos) — ex: "421016" (Nacom)
        if re.match(r'^\d{5,}$', primeiro):
            return (primeiro, resto or primeiro)

        # H1b: Codigo numerico concatenado com descricao (sem espaco)
        # Ex: "00000000001000126NotMilk" → cod="00000000001000126", desc="NotMilk ..."
        m = re.match(r'^(\d{5,})([A-Za-z].*)$', primeiro)
        if m:
            codigo = m.group(1)
            desc_start = m.group(2)
            desc_full = desc_start + (' ' + resto if resto else '')
            return (codigo, desc_full)

        # H2: Codigo com dash — ex: "MT-B2", "X11-MINI" (Laiouns)
        if '-' in primeiro and len(primeiro) <= 15:
            return (primeiro, resto or primeiro)

        # H3: Repeat detection — pdfplumber mergeou code+desc duas vezes
        # Ex: "X12 MOTO X12 MOTO CHEFE" → code="X12 MOTO", desc="X12 MOTO CHEFE"
        primeiro_upper = primeiro.upper()
        for i in range(1, len(tokens)):
            if tokens[i].upper() == primeiro_upper:
                codigo = ' '.join(tokens[:i])
                descricao = ' '.join(tokens[i:])
                return (codigo, descricao)

        # H4: Codigo alfanumerico curto (tem letras E digitos, <=10 chars)
        if len(primeiro) <= 10 and re.search(r'\d', primeiro) and re.search(r'[A-Za-z]', primeiro):
            return (primeiro, resto or primeiro)

        # Fallback: sem separacao confiavel — ambos recebem texto completo
        return (texto, texto)

    def _parsear_linha_produto(self, ncm_line: str, continuacoes: Optional[List[str]] = None) -> Optional[Dict]:
        """Parseia uma linha de produto usando NCM como ancora

        Args:
            ncm_line: Linha principal contendo NCM + dados numericos
            continuacoes: Linhas extras (descricao wrapping para proximas linhas)

        Formato tipico ncm_line (COM CFOP):
        'JET MOTO JET MOTO CHEFE 87116000 460 5405 UN 3,00 7.220,0000 0,00 21.660,00 ...'
                                  ^NCM    ^CST^CFOP^UN^QTD ^V.UNIT    ^DESC^V.LIQ

        Formato compacto ncm_line (SEM CFOP):
        'MT-X12 10 MOTO ELETR. X12-10 87116000 110 UN 5,0000 2.786,37 13.931,85 04,00'
                                       ^NCM    ^CST^UN^QTD   ^V.UNIT  ^V.TOTAL  ^ALIQ

        Texto antes do NCM = codigo + descricao mesclados (pdfplumber merge colunas).
        Continuacoes = wrapping da coluna descricao (anexadas a desc, NAO ao codigo).
        """
        if not continuacoes:
            continuacoes = []

        # Tentar com CFOP primeiro (mais especifico, menos falsos positivos)
        # NCM (8 dig) + O/CST skip (1-3 dig, possivelmente split) + CFOP (4 dig)
        # Ex: "20057000 3 00 6101" ou "87116000 460 5405" — ambos devem funcionar
        match = re.search(
            r'(\d{8})\s+\d{1,3}(?:\s+\d{2})?\s+(\d{4})\s+(\w{1,5})\s+([\d.,]+)\s+([\d.,]+)',
            ncm_line,
        )
        if match:
            ncm = match.group(1)
            cfop = match.group(2)
            unidade = match.group(3)
            quantidade = self._parse_valor_br(match.group(4))
            valor_unitario = self._parse_valor_br(match.group(5))

            # Extrair valor total: numeros apos NCM
            texto_apos = ncm_line[match.start():]
            numeros = re.findall(r'[\d.,]+', texto_apos)
            # [NCM, CST, CFOP, QTD, V.UNIT, V.DESC, V.LIQ, BASE_ICMS, V.ICMS, V.IPI, ...]
            valor_total_item = None
            if len(numeros) >= 7:
                valor_total_item = self._parse_valor_br(numeros[6])

            texto_antes = ncm_line[:match.start()].strip()
            codigo, descricao = self._separar_codigo_descricao(texto_antes)
        else:
            # Fallback SEM CFOP: NCM (8 dig) + CST (1-3 dig) + UNIDADE (alfa) + QTD + V.UNIT
            # Ex: "87116000 110 UN 5,0000 2.786,37 13.931,85"
            match_no_cfop = re.search(
                r'(\d{8})\s+\d{1,3}(?:\s+\d{2})?\s+([A-Za-z]{1,5})\s+([\d.,]+)\s+([\d.,]+)',
                ncm_line,
            )
            if not match_no_cfop:
                return None

            ncm = match_no_cfop.group(1)
            cfop = None
            unidade = match_no_cfop.group(2)
            quantidade = self._parse_valor_br(match_no_cfop.group(3))
            valor_unitario = self._parse_valor_br(match_no_cfop.group(4))

            # Extrair valor total: numeros apos NCM
            texto_apos = ncm_line[match_no_cfop.start():]
            numeros = re.findall(r'[\d.,]+', texto_apos)
            # SEM CFOP: [NCM, CST, QTD, V.UNIT, V.TOTAL, ...]
            valor_total_item = None
            if len(numeros) >= 5:
                valor_total_item = self._parse_valor_br(numeros[4])

            texto_antes = ncm_line[:match_no_cfop.start()].strip()
            codigo, descricao = self._separar_codigo_descricao(texto_antes)

        # Continuacoes = descricao wrapping (nao codigo).
        # Em DANFEs, o codigo e curto e cabe em 1 linha. Continuacoes sao texto
        # da coluna descricao que nao coube na linha do NCM.
        # Dedup: se descricao ja termina com o texto da continuacao, pular (overlap pdfplumber).
        if continuacoes:
            desc_strip = descricao.strip()
            for cont in continuacoes:
                cont_strip = cont.strip()
                if cont_strip and not desc_strip.endswith(cont_strip):
                    desc_strip = desc_strip + ' ' + cont_strip
            descricao = desc_strip

        # Defesa em profundidade: truncar para 60 chars (limite da coluna carvia_nf_itens.codigo_produto)
        codigo_final = codigo.strip()[:60]

        return {
            'codigo_produto': codigo_final,
            'descricao': descricao.strip()[:255],  # varchar(255)
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
        """Converte data brasileira (DD/MM/YYYY ou DD/MM/YY) para date

        Suporta ano com 2 digitos: YY < 100 → 20YY (ex: 26 → 2026).
        """
        if not date_str:
            return None
        try:
            from datetime import datetime
            # Normalizar separadores
            date_str = date_str.replace('-', '/').replace('.', '/')
            parts = date_str.split('/')
            if len(parts) == 3 and len(parts[2]) == 2:
                # Ano com 2 digitos — converter para 4 digitos
                ano = int(parts[2])
                parts[2] = str(2000 + ano)
                date_str = '/'.join(parts)
            return datetime.strptime(date_str, '%d/%m/%Y').date()
        except (ValueError, TypeError):
            return None


def parsear_danfe_pdf(pdf_path: str = None, pdf_bytes: bytes = None) -> Dict:
    """Funcao helper para parsear DANFE PDF"""
    parser = DanfePDFParser(pdf_path=pdf_path, pdf_bytes=pdf_bytes)
    return parser.get_todas_informacoes()
