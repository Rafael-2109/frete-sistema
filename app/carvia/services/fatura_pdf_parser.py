"""
Parser de Faturas PDF para o modulo CarVia
============================================

Extrai dados de faturas PDF (cliente ou transportadora) com 3 camadas:
1. Regex — patterns genericos + calibrados SSW (confianca alta)
2. Haiku — LLM rapido para campos faltantes (confianca media)
3. Sonnet — LLM avancado para reextracao completa (confianca baixa)

Suporte multi-pagina: formato SSW tem 1 fatura por pagina.
parse_multi() retorna List[Dict] (1 dict por pagina/fatura).
parse() retorna apenas 1 dict (backwards compatible, 1a fatura).

Campos extraidos (base):
- numero_fatura (obrigatorio)
- cnpj_emissor (beneficiario = CarVia)
- nome_emissor (beneficiario = CarVia)
- cnpj_pagador (obrigatorio — cliente que paga)
- nome_pagador (cliente)
- data_emissao (obrigatorio)
- valor_total (obrigatorio)
- vencimento (opcional)
- ctes_referenciados (opcional)

Campos SSW adicionais:
- tipo_frete (CIF/FOB)
- quantidade_documentos
- valor_mercadoria, valor_icms, aliquota_icms, valor_pedagio
- vencimento_original
- cancelada (bool)
- pagador_endereco, pagador_cep, pagador_cidade, pagador_uf
- pagador_ie, pagador_telefone
- itens_detalhe (lista de dicts com dados por CTe)

Reutiliza padrao de DanfePDFParser para extracao de texto:
pdfplumber (primario) + pypdf (fallback).
"""

import json
import logging
import os
import re
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class FaturaPDFParser:
    """Parser de faturas PDF com regex + LLM escalonado"""

    HAIKU_MODEL = "claude-haiku-4-5-20251001"
    SONNET_MODEL = "claude-sonnet-4-6"

    # Campos obrigatorios para considerar extracao valida
    # cnpj_pagador substitui cnpj_emissor (beneficiario = sempre CarVia)
    CAMPOS_OBRIGATORIOS = {'numero_fatura', 'cnpj_pagador', 'data_emissao', 'valor_total'}

    def __init__(self, pdf_bytes: bytes):
        """
        Args:
            pdf_bytes: Bytes do PDF da fatura
        """
        self.pdf_bytes = pdf_bytes
        self.texto_completo = ''
        self.paginas: List[str] = []
        self.confianca = 0.0
        self._client = None
        self._extrair_texto()

    # ------------------------------------------------------------------
    # Extracao de texto do PDF
    # ------------------------------------------------------------------

    def _extrair_texto(self):
        """Extrai texto do PDF usando pdfplumber (primario) + pypdf (fallback)"""
        texto = self._extrair_com_pdfplumber()
        if not texto or len(texto.strip()) < 30:
            texto_fallback = self._extrair_com_pypdf()
            if texto_fallback and len(texto_fallback.strip()) > len((texto or '').strip()):
                texto = texto_fallback

        self.texto_completo = texto or ''

    def _extrair_com_pdfplumber(self) -> str:
        """Extrai texto usando pdfplumber"""
        try:
            import pdfplumber
            import io

            pdf = pdfplumber.open(io.BytesIO(self.pdf_bytes))
            textos = []
            for page in pdf.pages:
                texto = page.extract_text()
                if texto:
                    textos.append(texto)
                    self.paginas.append(texto)
            pdf.close()
            return '\n'.join(textos)
        except Exception as e:
            logger.warning(f"pdfplumber falhou na fatura: {e}")
            return ''

    def _extrair_com_pypdf(self) -> str:
        """Extrai texto usando pypdf (fallback)"""
        try:
            import pypdf
            import io

            reader = pypdf.PdfReader(io.BytesIO(self.pdf_bytes))
            textos = []
            for page in reader.pages:
                texto = page.extract_text()
                if texto:
                    textos.append(texto)
            return '\n'.join(textos)
        except Exception as e:
            logger.warning(f"pypdf falhou na fatura: {e}")
            return ''

    # ------------------------------------------------------------------
    # Validacao
    # ------------------------------------------------------------------

    def is_valid(self) -> bool:
        """Verifica se o texto foi extraido com sucesso"""
        return len(self.texto_completo.strip()) > 30

    # ------------------------------------------------------------------
    # Pipeline principal
    # ------------------------------------------------------------------

    def parse(self) -> Dict:
        """Pipeline completo: regex -> haiku -> sonnet (backwards compatible)

        Para PDFs multi-pagina, retorna apenas a 1a fatura.
        Use parse_multi() para obter todas.

        Returns:
            Dict com campos extraidos + confianca + metodo_extracao.
            Dict vazio se nao foi possivel extrair dados minimos.
        """
        resultados = self.parse_multi()
        if resultados:
            return resultados[0]
        return {}

    def parse_multi(self) -> List[Dict]:
        """Pipeline multi-pagina: parseia cada pagina como fatura separada.

        Se o PDF tem N paginas (formato SSW), retorna N dicts.
        Se o PDF tem 1 pagina, retorna lista com 1 dict.

        Returns:
            List[Dict] — cada dict com campos extraidos + confianca + metodo_extracao.
            Lista vazia se nenhuma fatura foi extraida.
        """
        if not self.is_valid():
            return []

        # Multi-pagina: parsear cada pagina individualmente
        if len(self.paginas) > 1:
            resultados = []
            for idx, texto_pagina in enumerate(self.paginas):
                resultado = self._parsear_pagina(texto_pagina, idx + 1)
                if resultado:
                    resultados.append(resultado)

            if resultados:
                return resultados

        # Fallback: tratar como pagina unica (texto_completo)
        resultado = self._parsear_pagina(self.texto_completo, 1)
        if resultado:
            return [resultado]
        return []

    def _parsear_pagina(self, texto: str, pagina_num: int) -> Optional[Dict]:
        """Parseia texto de uma unica pagina/fatura.

        Pipeline: regex -> haiku -> sonnet

        Args:
            texto: Texto extraido da pagina
            pagina_num: Numero da pagina (para logging)

        Returns:
            Dict com campos extraidos ou None se insuficiente
        """
        self.confianca = 0.0

        # Log primeiras linhas para diagnostico de formato
        linhas_preview = texto.strip().split('\n')[:15]
        logger.info(
            f"Fatura pag {pagina_num} — preview texto ({len(texto)} chars):\n"
            + '\n'.join(f"  [{i+1}] {l}" for i, l in enumerate(linhas_preview))
        )

        # Camada 1: Regex
        resultado = self._extract_by_regex(texto)
        campos_faltantes = self._campos_faltantes(resultado)

        if not campos_faltantes:
            resultado['confianca'] = round(self.confianca, 2)
            resultado['metodo_extracao'] = 'REGEX'
            resultado['pagina'] = pagina_num
            return resultado

        # Camada 2: Haiku para campos faltantes
        resultado_llm = self._extract_by_llm(self.HAIKU_MODEL, campos_faltantes, texto)
        if resultado_llm:
            resultado = self._merge_results(resultado, resultado_llm)

            campos_faltantes_pos_haiku = self._campos_faltantes(resultado)
            if not campos_faltantes_pos_haiku and self._validar_formato(resultado_llm):
                resultado['confianca'] = round(self.confianca, 2)
                resultado['metodo_extracao'] = 'HAIKU'
                resultado['pagina'] = pagina_num
                return resultado

        # Camada 3: Sonnet para reextracao completa (campos ainda faltantes)
        campos_faltantes_final = self._campos_faltantes(resultado)
        if campos_faltantes_final:
            resultado_sonnet = self._extract_by_llm(
                self.SONNET_MODEL, campos_faltantes_final, texto
            )
            if resultado_sonnet:
                resultado = self._merge_results(resultado, resultado_sonnet)

        resultado['confianca'] = round(self.confianca, 2)
        resultado['metodo_extracao'] = 'SONNET'
        resultado['pagina'] = pagina_num
        return resultado

    # ------------------------------------------------------------------
    # Camada 1: Regex
    # ------------------------------------------------------------------

    def _extract_by_regex(self, texto: str) -> Dict:
        """Extrai campos via regex patterns

        Cada campo extraido com sucesso incrementa self.confianca.

        Args:
            texto: Texto da pagina a parsear
        """
        resultado: Dict = {
            'numero_fatura': None,
            'cnpj_emissor': None,
            'nome_emissor': None,
            'cnpj_pagador': None,
            'nome_pagador': None,
            'data_emissao': None,
            'valor_total': None,
            'vencimento': None,
            'ctes_referenciados': [],
            # Campos SSW adicionais
            'tipo_frete': None,
            'quantidade_documentos': None,
            'valor_mercadoria': None,
            'valor_icms': None,
            'aliquota_icms': None,
            'valor_pedagio': None,
            'vencimento_original': None,
            'cancelada': False,
            'pagador_endereco': None,
            'pagador_cep': None,
            'pagador_cidade': None,
            'pagador_uf': None,
            'pagador_ie': None,
            'pagador_telefone': None,
            'itens_detalhe': [],
            'fonte_campos': {},
        }

        # numero_fatura
        numero = self._regex_numero_fatura(texto)
        if numero:
            resultado['numero_fatura'] = numero
            resultado['fonte_campos']['numero_fatura'] = 'REGEX'
            self.confianca += 0.15

        # cnpj_emissor (beneficiario = CarVia, 1o CNPJ)
        cnpj = self._regex_cnpj_emissor(texto)
        if cnpj:
            resultado['cnpj_emissor'] = cnpj
            resultado['fonte_campos']['cnpj_emissor'] = 'REGEX'
            self.confianca += 0.05

        # nome_emissor (beneficiario)
        nome = self._regex_nome_emissor(texto)
        if nome:
            resultado['nome_emissor'] = nome
            resultado['fonte_campos']['nome_emissor'] = 'REGEX'
            self.confianca += 0.03

        # cnpj_pagador + nome_pagador (cliente)
        pagador = self._regex_pagador(texto)
        logger.info(f"Pagador extraido: {pagador}")
        if pagador:
            if pagador.get('cnpj'):
                resultado['cnpj_pagador'] = pagador['cnpj']
                resultado['fonte_campos']['cnpj_pagador'] = 'REGEX'
                self.confianca += 0.15
            if pagador.get('nome'):
                resultado['nome_pagador'] = pagador['nome']
                resultado['fonte_campos']['nome_pagador'] = 'REGEX'
                self.confianca += 0.03
            # IE e telefone extraidos do topo pelo _regex_pagador
            if pagador.get('ie'):
                resultado['pagador_ie'] = pagador['ie']
                resultado['fonte_campos']['pagador_ie'] = 'REGEX'
            if pagador.get('telefone'):
                resultado['pagador_telefone'] = pagador['telefone']
                resultado['fonte_campos']['pagador_telefone'] = 'REGEX'

        # Dados do pagador (endereco, CEP, cidade, UF)
        pagador_dados = self._regex_pagador_endereco(texto)
        if pagador_dados:
            for key in ('pagador_endereco', 'pagador_cep', 'pagador_cidade', 'pagador_uf'):
                if pagador_dados.get(key):
                    resultado[key] = pagador_dados[key]
                    resultado['fonte_campos'][key] = 'REGEX'

        # IE e telefone via metodos dedicados (se nao extraidos acima)
        if not resultado.get('pagador_ie'):
            ie = self._regex_pagador_ie(texto)
            if ie:
                resultado['pagador_ie'] = ie
                resultado['fonte_campos']['pagador_ie'] = 'REGEX'

        if not resultado.get('pagador_telefone'):
            telefone = self._regex_pagador_telefone(texto)
            if telefone:
                resultado['pagador_telefone'] = telefone
                resultado['fonte_campos']['pagador_telefone'] = 'REGEX'

        # data_emissao
        data = self._regex_data_emissao(texto)
        if data:
            resultado['data_emissao'] = data
            resultado['fonte_campos']['data_emissao'] = 'REGEX'
            self.confianca += 0.15

        # valor_total
        valor = self._regex_valor_total(texto)
        if valor is not None:
            resultado['valor_total'] = valor
            resultado['fonte_campos']['valor_total'] = 'REGEX'
            self.confianca += 0.15

        # vencimento
        venc = self._regex_vencimento(texto)
        if venc:
            resultado['vencimento'] = venc
            resultado['fonte_campos']['vencimento'] = 'REGEX'
            self.confianca += 0.05

        # ctes_referenciados
        ctes = self._regex_ctes_referenciados(texto)
        if ctes:
            resultado['ctes_referenciados'] = ctes
            resultado['fonte_campos']['ctes_referenciados'] = 'REGEX'
            self.confianca += 0.05

        # Campos SSW adicionais
        tipo = self._regex_tipo_frete(texto)
        if tipo:
            resultado['tipo_frete'] = tipo
            resultado['fonte_campos']['tipo_frete'] = 'REGEX'

        qtd = self._regex_quantidade_documentos(texto)
        if qtd is not None:
            resultado['quantidade_documentos'] = qtd
            resultado['fonte_campos']['quantidade_documentos'] = 'REGEX'

        vm = self._regex_valor_mercadoria(texto)
        if vm is not None:
            resultado['valor_mercadoria'] = vm
            resultado['fonte_campos']['valor_mercadoria'] = 'REGEX'

        pedagio = self._regex_valor_pedagio(texto)
        if pedagio is not None:
            resultado['valor_pedagio'] = pedagio
            resultado['fonte_campos']['valor_pedagio'] = 'REGEX'

        icms = self._regex_icms_resumo(texto)
        if icms:
            if icms.get('aliquota'):
                resultado['aliquota_icms'] = icms['aliquota']
                resultado['fonte_campos']['aliquota_icms'] = 'REGEX'
            if icms.get('valor') is not None:
                resultado['valor_icms'] = icms['valor']
                resultado['fonte_campos']['valor_icms'] = 'REGEX'

        venc_orig = self._regex_vencimento_original(texto)
        if venc_orig:
            resultado['vencimento_original'] = venc_orig
            resultado['fonte_campos']['vencimento_original'] = 'REGEX'

        if self._regex_cancelada(texto):
            resultado['cancelada'] = True
            resultado['fonte_campos']['cancelada'] = 'REGEX'

        itens = self._regex_detalhe_ctes(texto)
        if itens:
            resultado['itens_detalhe'] = itens
            resultado['fonte_campos']['itens_detalhe'] = 'REGEX'

        return resultado

    # ------------------------------------------------------------------
    # Regex: Campos base
    # ------------------------------------------------------------------

    def _regex_numero_fatura(self, texto: str) -> Optional[str]:
        """Extrai numero da fatura via regex"""
        patterns = [
            # SSW: "FATURA Nº: 0001234-5" ou "FATURA Nº 0001234-5"
            r'FATURA\s*N[°ºo.]?\s*:?\s*(\d[\d.\-/]*\d)',
            r'(?:Fatura|Fat\.?|Nota|NF|N[°ºo.])\s*(?:de\s+Servi[cç]o\s*)?[:\s]*[Nn][°ºo.]?\s*[:.]?\s*(\d[\d./\-]*\d)',
            r'(?:Fatura|Fat\.?)\s*[:.]?\s*[Nn]?[°ºo.]?\s*[:.]?\s*(\d[\d./\-]*\d)',
            r'(?:N[°ºo.]\s*(?:da\s+)?(?:Fatura|Fat))\s*[:.]?\s*(\d[\d./\-]*\d)',
            r'(?:FATURA|NOTA\s+FISCAL)\s*(?:DE\s+SERVI[CÇ]O)?\s*(?:N[°ºo.]?\s*)?[:.]?\s*(\d[\d./\-]*\d)',
        ]
        for pattern in patterns:
            match = re.search(pattern, texto, re.IGNORECASE)
            if match:
                numero = match.group(1).strip().lstrip('0') or '0'
                return numero
        return None

    def _regex_cnpj_emissor(self, texto: str) -> Optional[str]:
        """Extrai CNPJ do emissor/beneficiario (CarVia).

        No formato SSW boleto, o layout e:
          "Pagador CNPJ: XX.XXX.XXX/XXXX-XX" ← PAGADOR (1o CNPJ no texto)
          ...
          "CNPJ/CPF: 62.312.605/0001-75"      ← BENEFICIARIO/CarVia

        Portanto NAO usar 1o CNPJ — usar label "CNPJ/CPF:" que identifica CarVia.
        """
        # SSW: "CNPJ/CPF: XX.XXX.XXX/XXXX-XX" (beneficiario = CarVia)
        match_cnpj_cpf = re.search(
            r'CNPJ/CPF\s*:\s*(\d{2}[.\d]+/\d{4}-?\d{2})',
            texto,
        )
        if match_cnpj_cpf:
            cnpj = re.sub(r'\D', '', match_cnpj_cpf.group(1))
            if len(cnpj) == 14:
                return cnpj

        # Fallback: "Razao Social" ou "Empresa" seguido de CNPJ
        match_rs = re.search(
            r'(?:Raz[aã]o\s+Social|Empresa|Emissor)\s*[:.]?\s*.*?'
            r'(\d{2}\.?\d{3}\.?\d{3}/\d{4}-?\d{2})',
            texto,
            re.IGNORECASE | re.DOTALL,
        )
        if match_rs:
            cnpj = re.sub(r'\D', '', match_rs.group(1))
            if len(cnpj) == 14:
                return cnpj

        return None

    def _regex_nome_emissor(self, texto: str) -> Optional[str]:
        """Extrai nome/razao social do emissor (beneficiario = CarVia).

        No formato SSW boleto:
          "Beneficiário Agência/Código do Beneficiário"
          "CARVIA LOGISTICA E TRANSPORTE LTDA 077 0001-0 / 047977495-1 PIX"

        O nome esta na linha APOS "Beneficiário".
        """
        linhas = texto.split('\n')

        # SSW: encontrar linha com "Beneficiário" e pegar proxima linha
        for i, linha in enumerate(linhas):
            if re.search(r'Benefici[aá]rio', linha, re.IGNORECASE):
                # Proxima linha tem o nome da empresa
                if i + 1 < len(linhas):
                    nome_linha = linhas[i + 1].strip()
                    if nome_linha and len(nome_linha) >= 5:
                        # Remover dados bancarios (077 0001-0 / ...) e PIX
                        nome = re.split(r'\s+\d{3}\s+\d{4}', nome_linha)[0].strip()
                        nome = re.sub(r'\s+PIX\s*$', '', nome).strip()
                        if len(nome) >= 5:
                            return nome

        # Fallback: "Razão Social" ou "Empresa" seguido de nome
        match = re.search(
            r'(?:Raz[aã]o\s+Social|Empresa|Emissor)\s*[:.]?\s*(.+?)(?:\n|CNPJ)',
            texto,
            re.IGNORECASE,
        )
        if match:
            nome = match.group(1).strip()
            if len(nome) >= 3:
                return nome

        return None

    def _regex_data_emissao(self, texto: str) -> Optional[str]:
        """Extrai data de emissao no formato DD/MM/YYYY.

        No formato SSW boleto:
          "FATURA Nº:0000001-9 Emissão: 09/01/2026"
        O label e "Emissão:" (sem "Data" antes).
        """
        patterns = [
            # SSW: "Emissão: DD/MM/YYYY" (sem "Data" antes)
            r'Emiss[aã]o\s*:\s*(\d{2}[/.\-]\d{2}[/.\-]\d{4})',
            r'(?:Data\s*(?:de\s+)?Emiss[aã]o|Emitido\s*(?:em)?)\s*[:.]?\s*(\d{2}[/.\-]\d{2}[/.\-]\d{4})',
            r'(?:DT\.?\s*EMISS[AÃ]O)\s*[:.]?\s*(\d{2}[/.\-]\d{2}[/.\-]\d{4})',
        ]
        for pattern in patterns:
            match = re.search(pattern, texto, re.IGNORECASE)
            if match:
                return self._normalizar_data(match.group(1))

        return None

    def _regex_valor_total(self, texto: str) -> Optional[float]:
        """Extrai valor total da fatura.

        No SSW: "VALOR TOTAL 1.250,00" (no bloco RESUMO).
        Aceita valor 0.00 (faturas canceladas).
        """
        patterns = [
            # SSW: "VALOR TOTAL" (case-sensitive, mais especifico)
            r'VALOR\s+TOTAL\s+([\d.,]+)',
            r'(?:Valor\s*Total|Total\s*(?:da\s+)?(?:Fatura|Nota|NF))\s*[:.]?\s*R?\$?\s*([\d.,]+)',
            r'(?:Total\s*(?:Geral|a\s*Pagar))\s*[:.]?\s*R?\$?\s*([\d.,]+)',
            r'(?:Valor\s*(?:Cobrado|Liquido|L[ií]quido))\s*[:.]?\s*R?\$?\s*([\d.,]+)',
            r'(?:Total\s+dos\s+CTRCs?)\s*[:.]?\s*R?\$?\s*([\d.,]+)',
        ]
        for pattern in patterns:
            match = re.search(pattern, texto, re.IGNORECASE)
            if match:
                valor = self._parse_valor_br(match.group(1))
                if valor is not None and valor >= 0:
                    return valor
        return None

    def _regex_vencimento(self, texto: str) -> Optional[str]:
        """Extrai data de vencimento.

        No formato SSW boleto:
          "Vencimento Nº do Documento Espécie Valor do Documento"
          "28/02/2026 0000001-9 1.250,00"
        O vencimento esta na PROXIMA LINHA apos o label (nao inline).

        Tambem: "Vencimento Valor a pagar"
                "28/02/2026 1.250,00"
        """
        # Pattern 1: "Vencimento" seguido de data na mesma linha
        patterns = [
            r'(?:Venc(?:imento)?|Data\s*Venc(?:imento)?|Venc\.?)\s*[:.]?\s*(\d{2}[/.\-]\d{2}[/.\-]\d{4})',
            r'(?:DT\.?\s*VENC(?:IMENTO)?)\s*[:.]?\s*(\d{2}[/.\-]\d{2}[/.\-]\d{4})',
        ]
        for pattern in patterns:
            match = re.search(pattern, texto, re.IGNORECASE)
            if match:
                return self._normalizar_data(match.group(1))

        # SSW: "Vencimento" label na linha, data na proxima linha
        linhas = texto.split('\n')
        for i, linha in enumerate(linhas):
            if re.search(r'Vencimento', linha, re.IGNORECASE) and i + 1 < len(linhas):
                # Proxima linha comeca com data DD/MM/YYYY
                prox = linhas[i + 1].strip()
                match_data = re.match(r'(\d{2}/\d{2}/\d{4})', prox)
                if match_data:
                    return match_data.group(1)

        return None

    def _regex_ctes_referenciados(self, texto: str) -> List[str]:
        """Extrai lista de numeros de CTe referenciados"""
        ctes = set()

        # Pattern: CTe + numero
        for match in re.finditer(
            r'(?:CT-?e|CTe|CTRC|Conhecimento)\s*(?:N[°ºo.]?\s*)?[:.]?\s*(\d{3,15})',
            texto,
            re.IGNORECASE,
        ):
            ctes.add(match.group(1).lstrip('0') or '0')

        # Pattern: chave de acesso de CTe (44 digitos comecando com UF+ano)
        for match in re.finditer(r'\b(\d{44})\b', texto):
            digitos = match.group(1)
            # Modelo CTe = posicoes 20-21 == '57'
            if digitos[20:22] == '57':
                ctes.add(digitos)

        return sorted(ctes)

    # ------------------------------------------------------------------
    # Regex: Pagador (cliente) — SSW
    # ------------------------------------------------------------------

    def _regex_pagador(self, texto: str) -> Optional[Dict]:
        """Extrai CNPJ/CPF e nome do pagador (cliente).

        No formato SSW boleto, ha 3 ocorrencias de "Pagador" por pagina:

        1) TOPO: "Pagador CNPJ: 24.727.443/0001-47 - IE: ... - FONE: ..."
                 "PABLO VASCONCELLOS LEAL"  ← nome na proxima linha

        2) MEIO: "Pagador: PABLO VASCONCELLOS LEAL Banco/Ag/CC ..."
                 "CNPJ: 24.727.443/0001-47 - IE: ..."

        3) RODAPE: "Pagador"  (sozinho na linha)
                   "PABLO VASCONCELLOS LEAL"
                   "AVENIDA ..., 032 - CASSINO - FONE(00) -"
                   "96210-080 RIO GRANDE RS"

        Estrategia: usar (1) para CNPJ + nome (mais confiavel, no topo).
        Fallback com (2) e (3) se (1) falhar.
        """
        result = {}

        linhas = texto.split('\n')

        # ---------------------------------------------------------------
        # Estrategia 1: "Pagador CNPJ: XX.XXX.XXX/XXXX-XX" no topo
        # ---------------------------------------------------------------
        for i, linha in enumerate(linhas):
            match_top = re.match(
                r'Pagador\s+CNPJ\s*:\s*(\d{2}\.\d{3}\.\d{3}/\d{4}-?\d{2})',
                linha,
            )
            if match_top:
                cnpj = re.sub(r'\D', '', match_top.group(1))
                if len(cnpj) == 14:
                    result['cnpj'] = cnpj

                # IE do pagador na mesma linha
                ie_match = re.search(r'IE\s*:\s*([\d.]+)', linha)
                if ie_match:
                    result['ie'] = ie_match.group(1).strip()

                # Telefone do pagador na mesma linha
                fone_match = re.search(r'FONE\s*:\s*\((\d+)\)\s*([\d\- ]*)', linha)
                if fone_match:
                    ddd = fone_match.group(1)
                    num = fone_match.group(2).strip().rstrip('-').strip()
                    if ddd != '00' and num:
                        result['telefone'] = f"({ddd}) {num}"

                # Nome na proxima linha (limpa, sem metadata)
                if i + 1 < len(linhas):
                    nome_linha = linhas[i + 1].strip()
                    if nome_linha and len(nome_linha) >= 3:
                        # Verificar que nao e outra label
                        if not re.match(r'(?:Vencimento|Recibo|CARVIA)', nome_linha, re.IGNORECASE):
                            result['nome'] = nome_linha

                break  # Encontrou no topo, nao precisa mais

        # ---------------------------------------------------------------
        # Fallback CPF (pessoa fisica): "Pagador CPF: XXX.XXX.XXX-XX"
        # ---------------------------------------------------------------
        if not result.get('cnpj'):
            for i, linha in enumerate(linhas):
                match_cpf = re.match(
                    r'Pagador\s+CPF\s*:\s*(\d{3}\.?\d{3}\.?\d{3}-?\d{2})',
                    linha,
                )
                if match_cpf:
                    cpf = re.sub(r'\D', '', match_cpf.group(1))
                    if len(cpf) == 11:
                        result['cnpj'] = cpf
                    if i + 1 < len(linhas):
                        nome_linha = linhas[i + 1].strip()
                        if nome_linha and len(nome_linha) >= 3:
                            if not re.match(r'(?:Vencimento|Recibo)', nome_linha, re.IGNORECASE):
                                result['nome'] = nome_linha
                    break

        # ---------------------------------------------------------------
        # Estrategia 2: "Pagador: NOME Banco/Ag/CC ..."
        #               "CNPJ: XX.XXX.XXX/XXXX-XX - IE: ..."
        # ---------------------------------------------------------------
        if not result.get('cnpj'):
            for i, linha in enumerate(linhas):
                match_meio = re.match(
                    r'Pagador\s*:\s*(.+)',
                    linha,
                )
                if match_meio:
                    nome_raw = match_meio.group(1).strip()
                    nome_limpo = self._limpar_nome_pagador(nome_raw)
                    if nome_limpo and len(nome_limpo) >= 3:
                        result['nome'] = nome_limpo

                    # CNPJ na proxima linha: "CNPJ: XX.XXX..."
                    if i + 1 < len(linhas):
                        prox = linhas[i + 1]
                        cnpj_match = re.search(
                            r'CNPJ\s*:\s*(\d{2}\.\d{3}\.\d{3}/\d{4}-?\d{2})', prox
                        )
                        if cnpj_match:
                            cnpj = re.sub(r'\D', '', cnpj_match.group(1))
                            if len(cnpj) == 14:
                                result['cnpj'] = cnpj
                        else:
                            # CPF na proxima linha
                            cpf_match = re.search(
                                r'CPF\s*:\s*(\d{3}\.?\d{3}\.?\d{3}-?\d{2})', prox
                            )
                            if cpf_match:
                                cpf = re.sub(r'\D', '', cpf_match.group(1))
                                if len(cpf) == 11:
                                    result['cnpj'] = cpf
                    break

        # ---------------------------------------------------------------
        # Estrategia 3: "Pagador" sozinho + nome na proxima linha (rodape)
        # ---------------------------------------------------------------
        if not result.get('nome'):
            for i in range(len(linhas) - 1, -1, -1):
                if linhas[i].strip() == 'Pagador' and i + 1 < len(linhas):
                    nome_rodape = linhas[i + 1].strip()
                    if nome_rodape and len(nome_rodape) >= 3:
                        # Desduplicar caracteres (pag 14 cancelada: "PPaaggaaddoorr")
                        if not re.match(r'[A-Z]{2}[a-z]{2}', nome_rodape):
                            result['nome'] = nome_rodape
                    break

        return result if result else None

    def _limpar_nome_pagador(self, nome: str) -> str:
        """Remove dados bancarios e lixo do nome do pagador.

        Boletos frequentemente misturam nome com dados bancarios:
        'PABLO VASCONCELLOS LEAL Banco/Ag/CC beneficiário: 077 0001-0 / 047977495-1'
        -> 'PABLO VASCONCELLOS LEAL'
        """
        if not nome:
            return nome
        # Cortar em marcadores de dados bancarios
        marcadores = [
            r'\s+Banco\s*/\s*Ag',      # "Banco/Ag/CC"
            r'\s+Ag[êe]ncia',           # "Agência"
            r'\s+Conta\s',              # "Conta Corrente"
            r'\s+C/?C\s',               # "CC" ou "C/C"
            r'\s+benefici[aá]rio',       # "beneficiário"
            r'\s+CPF\s*[:./]',          # "CPF:"
            r'\s+CNPJ\s*[:./]',         # "CNPJ:"
            r'\s+CEP\s*[:.]',           # "CEP:"
            r'\s+Nosso\s+n[uú]mero',    # "Nosso número"
        ]
        for marcador in marcadores:
            match = re.search(marcador, nome, re.IGNORECASE)
            if match:
                nome = nome[:match.start()].strip()
        # Remover CNPJ residual
        nome = re.sub(r'\d{2}\.?\d{3}\.?\d{3}/\d{4}-?\d{2}', '', nome).strip()
        nome = nome.rstrip('-').rstrip('/').strip()
        return nome

    def _regex_pagador_endereco(self, texto: str) -> Optional[Dict]:
        """Extrai endereco, CEP, cidade e UF do pagador.

        No formato SSW boleto, o rodape tem:
          "Pagador"                              ← label sozinho
          "PABLO VASCONCELLOS LEAL"              ← nome
          "AVENIDA QUERENCIA,032 - CASSINO - FONE(00) -"  ← endereco
          "96210-080 RIO GRANDE RS"              ← CEP CIDADE UF

        Ultima linha: CEP + CIDADE + UF (UF sao os 2 ultimos chars maiusculos).
        """
        result = {}
        linhas = texto.split('\n')

        # Encontrar bloco "Pagador" no rodape (de tras pra frente)
        idx_pagador_rodape = None
        for i in range(len(linhas) - 1, -1, -1):
            if linhas[i].strip() == 'Pagador':
                idx_pagador_rodape = i
                break

        if idx_pagador_rodape is not None:
            # Linhas apos "Pagador" no rodape
            bloco = linhas[idx_pagador_rodape + 1:]

            # Linha de endereco (2a linha apos "Pagador", apos o nome)
            if len(bloco) >= 2:
                endereco_linha = bloco[1].strip()
                if endereco_linha and len(endereco_linha) >= 5:
                    # Limpar FONE do final
                    endereco_limpo = re.sub(r'\s*-?\s*FONE\s*\(.+$', '', endereco_linha).strip()
                    endereco_limpo = endereco_limpo.rstrip('-').strip()
                    if len(endereco_limpo) >= 5:
                        result['pagador_endereco'] = endereco_limpo

            # Ultima linha nao-vazia do bloco: "96210-080 RIO GRANDE RS"
            if len(bloco) >= 3:
                cep_cidade_uf = bloco[2].strip()
            elif len(bloco) >= 2:
                cep_cidade_uf = bloco[1].strip()
            else:
                cep_cidade_uf = ''

            if cep_cidade_uf:
                # Pattern: CEP CIDADE UF (UF = 2 letras maiusculas no final)
                match_ccu = re.match(
                    r'(\d{5}-?\d{3})\s+(.+?)\s+([A-Z]{2})\s*$',
                    cep_cidade_uf,
                )
                if match_ccu:
                    result['pagador_cep'] = match_ccu.group(1)
                    result['pagador_cidade'] = match_ccu.group(2).strip()
                    result['pagador_uf'] = match_ccu.group(3)
                else:
                    # Fallback: apenas CEP
                    cep_m = re.search(r'(\d{5}-\d{3})', cep_cidade_uf)
                    if cep_m:
                        result['pagador_cep'] = cep_m.group(1)

        # Se nao encontrou no rodape, fallback generico
        if not result:
            # Buscar CEP em qualquer lugar
            cep_match = re.search(r'(\d{5}-\d{3})', texto)
            if cep_match:
                result['pagador_cep'] = cep_match.group(1)

        return result if result else None

    def _regex_pagador_ie(self, texto: str) -> Optional[str]:
        """Extrai Inscricao Estadual do pagador.

        No formato SSW boleto, a IE do pagador aparece em:
          "Pagador CNPJ: XX - IE: 1000308887 - FONE: (00) ..."
        A IE da CarVia aparece em:
          "CNPJ/CPF: 62.312.605/0001-75 - IE: 623371998113"

        Estrategia: buscar IE na linha "Pagador CNPJ:" (topo, pagador).
        """
        # SSW: IE na linha "Pagador CNPJ:"
        match_pagador = re.search(
            r'Pagador\s+CNPJ\s*:.+?IE\s*:\s*([\d.]+)',
            texto,
        )
        if match_pagador:
            ie = match_pagador.group(1).strip()
            if len(ie) >= 5:
                return ie

        # Fallback: IE na linha "CNPJ:" apos "Pagador:" (secao do meio)
        match_meio = re.search(
            r'Pagador\s*:.+?\n\s*CNPJ\s*:.+?IE\s*:\s*([\d.]+)',
            texto,
        )
        if match_meio:
            ie = match_meio.group(1).strip()
            if len(ie) >= 5:
                return ie

        return None

    def _regex_pagador_telefone(self, texto: str) -> Optional[str]:
        """Extrai telefone do pagador.

        No formato SSW boleto, telefone do pagador aparece em:
          "Pagador CNPJ: XX - IE: YY - FONE: (17) 3423-5241 Nosso..."
        Quando "(00)" = telefone nao informado.

        Tambem no rodape:
          "AVENIDA...,032 - CENTRO - FONE(17) 3423-5241"

        Estrategia: buscar FONE na linha "Pagador CNPJ:" ou na
        linha "CNPJ:" do meio. Rejeitar "(00)".
        """
        # SSW: FONE na linha "Pagador CNPJ:"
        match_pagador = re.search(
            r'Pagador\s+CNPJ\s*:.+?FONE\s*:\s*\((\d+)\)\s*([\d\- ]*)',
            texto,
        )
        if match_pagador:
            ddd = match_pagador.group(1)
            num = match_pagador.group(2).strip().rstrip('-').strip()
            if ddd != '00' and num:
                fone = f"({ddd}) {num}"
                return fone[:30]

        # Fallback: FONE na linha "CNPJ:" do meio (apos "Pagador:")
        match_meio = re.search(
            r'Pagador\s*:.+?\n\s*CNPJ\s*:.+?FONE\s*:\s*\((\d+)\)\s*([\d\- ]*)',
            texto,
        )
        if match_meio:
            ddd = match_meio.group(1)
            num = match_meio.group(2).strip().rstrip('-').strip()
            if ddd != '00' and num:
                fone = f"({ddd}) {num}"
                return fone[:30]

        # Fallback: FONE no rodape (endereco)
        match_rodape = re.search(
            r'FONE\s*\((\d+)\)\s*([\d\- ]+)',
            texto,
        )
        if match_rodape:
            ddd = match_rodape.group(1)
            num = match_rodape.group(2).strip().rstrip('-').strip()
            if ddd != '00' and num:
                fone = f"({ddd}) {num}"
                return fone[:30]

        return None

    # ------------------------------------------------------------------
    # Regex: Campos SSW adicionais
    # ------------------------------------------------------------------

    def _regex_tipo_frete(self, texto: str) -> Optional[str]:
        """Extrai tipo de frete: CIF ou FOB"""
        match = re.search(r'FRETE\s+(CIF|FOB)', texto, re.IGNORECASE)
        if match:
            return match.group(1).upper()
        # Fallback: "Tipo Frete: CIF"
        match2 = re.search(r'(?:Tipo\s+(?:de\s+)?Frete)\s*[:.]?\s*(CIF|FOB)', texto, re.IGNORECASE)
        if match2:
            return match2.group(1).upper()
        return None

    def _regex_quantidade_documentos(self, texto: str) -> Optional[int]:
        """Extrai quantidade de documentos (CTes)"""
        match = re.search(
            r'(?:Quantidade\s+de\s+documentos?|Qtd\.?\s+documentos?)\s*[:.]?\s*(\d+)',
            texto,
            re.IGNORECASE,
        )
        if match:
            try:
                return int(match.group(1))
            except ValueError:
                pass
        return None

    def _regex_valor_mercadoria(self, texto: str) -> Optional[float]:
        """Extrai valor total de mercadoria dos CTRCs"""
        match = re.search(
            r'(?:Valor\s+mercadoria\s+dos\s+CTRCs?|Valor\s+mercadoria)\s*[:.]?\s*R?\$?\s*([\d.,]+)',
            texto,
            re.IGNORECASE,
        )
        if match:
            return self._parse_valor_br(match.group(1))
        return None

    def _regex_valor_pedagio(self, texto: str) -> Optional[float]:
        """Extrai valor total de pedagio dos CTRCs"""
        match = re.search(
            r'(?:Valor\s+ped[aá]gio\s+dos\s+CTRCs?|Valor\s+ped[aá]gio)\s*[:.]?\s*R?\$?\s*([\d.,]+)',
            texto,
            re.IGNORECASE,
        )
        if match:
            return self._parse_valor_br(match.group(1))
        return None

    def _regex_icms_resumo(self, texto: str) -> Optional[Dict]:
        """Extrai aliquota e valor de ICMS do resumo"""
        result = {}

        # "ICMS (Aliq 12.00%)" + valor
        match = re.search(
            r'ICMS\s*\(?(?:Aliq\.?\s*)?([\d.,]+)\s*%\s*\)?\s*[:.]?\s*R?\$?\s*([\d.,]+)?',
            texto,
            re.IGNORECASE,
        )
        if match:
            result['aliquota'] = f"{match.group(1)}%"
            if match.group(2):
                valor = self._parse_valor_br(match.group(2))
                if valor is not None:
                    result['valor'] = valor

        # Fallback separado: "ICMS R$ 123,45"
        if 'valor' not in result:
            match_valor = re.search(
                r'ICMS\s*[:.]?\s*R?\$?\s*([\d.,]+)',
                texto,
                re.IGNORECASE,
            )
            if match_valor:
                valor = self._parse_valor_br(match_valor.group(1))
                if valor is not None:
                    result['valor'] = valor

        return result if result else None

    def _regex_vencimento_original(self, texto: str) -> Optional[str]:
        """Extrai data de vencimento original (antes de reprogramacao)"""
        match = re.search(
            r'(?:Data\s+de\s+vencimento\s+original|Venc(?:imento)?\s+original)\s*[:.]?\s*(\d{2}[/.\-]\d{2}[/.\-]\d{4})',
            texto,
            re.IGNORECASE,
        )
        if match:
            return self._normalizar_data(match.group(1))
        return None

    def _regex_cancelada(self, texto: str) -> bool:
        """Detecta se a fatura esta marcada como cancelada"""
        return bool(re.search(r'FATURA\s+CANCELADA', texto, re.IGNORECASE))

    def _regex_detalhe_ctes(self, texto: str) -> List[Dict]:
        """Parseia tabela de linhas de detalhe CTe.

        No formato SSW boleto, cada linha de item tem:
          SEQ CTe_NUM DD/MM/YY CNPJ14raw NOME NF_FLAG NF_NUM VAL_MERC PESO B_CALC ICMS ISS ST FRETE

        Exemplo real:
          "1 00000001 09/01/26 09089839000112 LAIOUNS IMP. E EXPORTACAO 0 000033268 23.206,00 514 1.250,00 150,00 0,00 0,00 1.250,00"

        Diferencas do formato esperado anteriormente:
        - SEQ (1 digito) ANTES do CTe numero
        - Data no formato DD/MM/YY (2 digitos no ano, nao 4)
        - CNPJ sem formatacao (14 digitos crus, sem pontos/barras)
        - CPF sem formatacao (11 digitos crus) — para pessoa fisica
        - NF tem flag (0 ou 1) + numero
        """
        itens = []
        linhas = texto.split('\n')

        for linha in linhas:
            # Pattern SSW: SEQ + CTe + DD/MM/YY + CNPJ14/CPF11 + NOME + NF_FLAG + NF_NUM + valores
            match = re.match(
                r'\s*\d+\s+'                           # SEQ (descartado)
                r'(\d{5,10})\s+'                       # CTe numero (5-10 digitos)
                r'(\d{2}/\d{2}/\d{2,4})\s+'            # Data DD/MM/YY ou DD/MM/YYYY
                r'(\d{11,14})\s+'                      # CNPJ (14) ou CPF (11), sem formatacao
                r'(.+?)\s+'                            # Nome contraparte
                r'(\d+)\s+'                            # NF flag (0 ou 1)
                r'(\d{6,12})\s+'                       # NF numero
                r'([\d.,]+)\s+'                        # Valor mercadoria
                r'(\d+)\s+'                            # Peso (inteiro)
                r'([\d.,]+)\s+'                        # Base calculo
                r'([\d.,]+)\s+'                        # ICMS
                r'([\d.,]+)\s+'                        # ISS
                r'([\d.,]+)\s+'                        # ST
                r'([\d.,]+)',                          # Frete
                linha,
            )
            if match:
                data_str = match.group(2)
                # Converter DD/MM/YY para DD/MM/YYYY
                if len(data_str) == 8:  # DD/MM/YY
                    partes = data_str.split('/')
                    ano = int(partes[2])
                    ano_full = 2000 + ano if ano < 100 else ano
                    data_str = f"{partes[0]}/{partes[1]}/{ano_full}"

                item = {
                    'cte_numero': match.group(1).lstrip('0') or '0',
                    'cte_data_emissao': data_str,
                    'contraparte_cnpj': match.group(3),
                    'contraparte_nome': match.group(4).strip(),
                    'nf_numero': match.group(6).lstrip('0') or '0',
                    'valor_mercadoria': self._parse_valor_br(match.group(7)),
                    'peso_kg': float(match.group(8)),
                    'base_calculo': self._parse_valor_br(match.group(9)),
                    'icms': self._parse_valor_br(match.group(10)),
                    'iss': self._parse_valor_br(match.group(11)),
                    'st': self._parse_valor_br(match.group(12)),
                    'frete': self._parse_valor_br(match.group(13)),
                }
                itens.append(item)
                continue

            # Fallback: formato com CNPJ formatado (XX.XXX.XXX/XXXX-XX)
            match_fmt = re.match(
                r'\s*(\d{3,10})\s+'                    # CTe numero
                r'(\d{2}/\d{2}/\d{4})\s+'              # Data DD/MM/YYYY
                r'(\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2})\s+'  # CNPJ formatado
                r'(.+?)\s+'                            # Nome contraparte
                r'(\d+)\s+'                            # NF numero
                r'([\d.,]+)',                          # Valor (pelo menos 1)
                linha,
            )
            if match_fmt:
                pos = match_fmt.end()
                resto = linha[pos:]
                valores = re.findall(r'[\d.,]+', resto)

                item = {
                    'cte_numero': match_fmt.group(1),
                    'cte_data_emissao': match_fmt.group(2),
                    'contraparte_cnpj': re.sub(r'\D', '', match_fmt.group(3)),
                    'contraparte_nome': match_fmt.group(4).strip(),
                    'nf_numero': match_fmt.group(5),
                    'valor_mercadoria': self._parse_valor_br(match_fmt.group(6)),
                    'peso_kg': self._parse_valor_br(valores[0]) if valores else None,
                    'base_calculo': self._parse_valor_br(valores[1]) if len(valores) > 1 else None,
                    'icms': self._parse_valor_br(valores[2]) if len(valores) > 2 else None,
                    'iss': self._parse_valor_br(valores[3]) if len(valores) > 3 else None,
                    'st': self._parse_valor_br(valores[4]) if len(valores) > 4 else None,
                    'frete': self._parse_valor_br(valores[5]) if len(valores) > 5 else None,
                }
                itens.append(item)

        return itens

    # ------------------------------------------------------------------
    # Camada 2/3: LLM (Haiku / Sonnet)
    # ------------------------------------------------------------------

    def _extract_by_llm(self, model: str, campos_faltantes: List[str],
                        texto: str) -> Optional[Dict]:
        """Extrai campos faltantes via LLM

        Args:
            model: Model ID (Haiku ou Sonnet)
            campos_faltantes: Lista de nomes de campos a extrair
            texto: Texto da pagina a parsear

        Returns:
            Dict com campos extraidos ou None se falhar
        """
        client = self._get_client()
        if not client:
            logger.warning("Anthropic client nao disponivel — skipping LLM extraction")
            return None

        # Limitar texto para nao estourar contexto
        texto_truncado = texto[:8000]

        campos_desc = {
            'numero_fatura': 'Numero da fatura (apenas digitos e separadores)',
            'cnpj_emissor': 'CNPJ do emissor/beneficiario no formato 14 digitos',
            'nome_emissor': 'Nome ou razao social do emissor/beneficiario',
            'cnpj_pagador': 'CNPJ do pagador/sacado (quem paga) no formato 14 digitos',
            'nome_pagador': 'Nome ou razao social do pagador/sacado',
            'data_emissao': 'Data de emissao no formato DD/MM/YYYY',
            'valor_total': 'Valor total da fatura como numero decimal (ex: 1234.56)',
            'vencimento': 'Data de vencimento no formato DD/MM/YYYY',
            'ctes_referenciados': 'Lista de numeros de CTe referenciados (array de strings)',
        }

        campos_pedidos = {c: campos_desc.get(c, c) for c in campos_faltantes}

        prompt = (
            "Extraia os seguintes campos desta fatura brasileira.\n"
            "IMPORTANTE: Distinguir BENEFICIARIO (quem emite/recebe) do PAGADOR (quem paga).\n"
            "Retorne APENAS um JSON valido com os campos solicitados.\n"
            "Use null para campos nao encontrados.\n\n"
            "Campos:\n"
        )
        for campo, desc in campos_pedidos.items():
            prompt += f"- {campo}: {desc}\n"
        prompt += (
            "\nFormatos obrigatorios:\n"
            "- CNPJ: 14 digitos puros (sem pontuacao)\n"
            "- Datas: DD/MM/YYYY\n"
            "- Valores monetarios: numero decimal (1234.56, sem R$)\n"
            "- ctes_referenciados: array de strings\n\n"
            "Texto da fatura:\n---\n"
            f"{texto_truncado}\n---"
        )

        try:
            response = client.messages.create(
                model=model,
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}],
            )

            texto_resposta = response.content[0].text.strip()
            resultado = self._extrair_json(texto_resposta)

            if resultado:
                # Normalizar campos
                resultado_normalizado = {}
                for campo in campos_faltantes:
                    valor = resultado.get(campo)
                    if valor is not None:
                        resultado_normalizado[campo] = valor

                # Ajustar confianca com base no modelo
                bonus = 0.10 if model == self.HAIKU_MODEL else 0.08
                campos_encontrados = [
                    c for c in campos_faltantes
                    if resultado_normalizado.get(c) is not None
                ]
                self.confianca += bonus * len(campos_encontrados)

                return resultado_normalizado

        except Exception as e:
            logger.error(f"Erro na extracao LLM ({model}): {e}")

        return None

    def _extrair_json(self, texto: str) -> Optional[Dict]:
        """Extrai JSON de texto que pode conter markdown fences"""
        # Remover markdown code fences
        texto = re.sub(r'^```(?:json)?\s*', '', texto, flags=re.MULTILINE)
        texto = re.sub(r'```\s*$', '', texto, flags=re.MULTILINE)
        texto = texto.strip()

        try:
            return json.loads(texto)
        except json.JSONDecodeError:
            # Tentar encontrar JSON dentro do texto
            match = re.search(r'\{[^{}]*\}', texto, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(0))
                except json.JSONDecodeError:
                    pass
        return None

    def _get_client(self):
        """Lazy init do Anthropic client"""
        if self._client is not None:
            return self._client

        api_key = os.getenv('ANTHROPIC_API_KEY')
        if not api_key:
            logger.warning("ANTHROPIC_API_KEY nao configurada — LLM extraction desabilitada")
            return None

        try:
            import anthropic
            self._client = anthropic.Anthropic(api_key=api_key)
            return self._client
        except ImportError:
            logger.warning("anthropic package nao instalado — LLM extraction desabilitada")
            return None

    # ------------------------------------------------------------------
    # Validacao e merge
    # ------------------------------------------------------------------

    def _campos_faltantes(self, resultado: Dict) -> List[str]:
        """Retorna lista de campos obrigatorios ainda faltantes"""
        faltantes = []
        for campo in self.CAMPOS_OBRIGATORIOS:
            valor = resultado.get(campo)
            if valor is None or (isinstance(valor, str) and not valor.strip()):
                faltantes.append(campo)
        return faltantes

    def _validar_formato(self, resultado_llm: Dict) -> bool:
        """Valida formato dos campos extraidos por LLM"""
        valido = True

        # Validar CNPJ: 14 digitos
        for campo_cnpj in ('cnpj_emissor', 'cnpj_pagador'):
            cnpj = resultado_llm.get(campo_cnpj)
            if cnpj:
                digitos = re.sub(r'\D', '', str(cnpj))
                if len(digitos) != 14:
                    valido = False

        # Validar datas: DD/MM/YYYY
        for campo_data in ('data_emissao', 'vencimento'):
            data = resultado_llm.get(campo_data)
            if data and not re.match(r'^\d{2}/\d{2}/\d{4}$', str(data)):
                valido = False

        # Validar valor: numerico positivo
        valor = resultado_llm.get('valor_total')
        if valor is not None:
            try:
                v = float(valor)
                if v <= 0:
                    valido = False
            except (ValueError, TypeError):
                valido = False

        return valido

    def _merge_results(self, base: Dict, novo: Dict) -> Dict:
        """Preenche campos faltantes do base com valores do novo.

        Nao sobrescreve valores ja preenchidos por regex.
        """
        merged = dict(base)
        fonte_campos = merged.get('fonte_campos', {})

        for campo, valor in novo.items():
            if campo in ('fonte_campos', 'confianca', 'metodo_extracao'):
                continue
            # Preencher apenas campos vazios/None
            if valor is not None:
                valor_atual = merged.get(campo)
                if valor_atual is None or (isinstance(valor_atual, str) and not valor_atual.strip()):
                    merged[campo] = valor
                    if campo not in fonte_campos:
                        fonte_campos[campo] = 'LLM'
                elif isinstance(valor_atual, list) and not valor_atual:
                    merged[campo] = valor
                    if campo not in fonte_campos:
                        fonte_campos[campo] = 'LLM'

        merged['fonte_campos'] = fonte_campos
        return merged

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _parse_valor_br(self, valor_str: str) -> Optional[float]:
        """Converte valor brasileiro (1.234,56) para float"""
        if not valor_str:
            return None
        try:
            valor_str = valor_str.strip()
            if ',' in valor_str:
                valor_str = valor_str.replace('.', '').replace(',', '.')
            return float(valor_str)
        except (ValueError, TypeError):
            return None

    def _normalizar_data(self, data_str: str) -> str:
        """Normaliza separadores de data para DD/MM/YYYY"""
        return data_str.replace('-', '/').replace('.', '/')

    def _parse_date_br(self, date_str: str):
        """Converte data brasileira (DD/MM/YYYY) para date"""
        if not date_str:
            return None
        try:
            from datetime import datetime
            date_str = self._normalizar_data(date_str)
            return datetime.strptime(date_str, '%d/%m/%Y').date()
        except (ValueError, TypeError):
            return None
