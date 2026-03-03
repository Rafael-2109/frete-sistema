"""
Parser de DACTE PDF para o modulo CarVia
=========================================

Extrai dados de DACTE (Documento Auxiliar de CTe) a partir de PDF.
Utiliza pdfplumber (primario) + pypdf (fallback).

Layout SSW: Todos DACTEs processados por SSW (ssw.inf.br) seguem layout
padronizado com secoes REMETENTE, DESTINATARIO, EXPEDIDOR, RECEBEDOR, TOMADOR.

IMPORTANTE: A extracao de PDF e inerentemente menos confiavel que XML.
O campo 'confianca' indica o nivel de confianca dos dados extraidos.

Separacao de chaves CT-E vs NF-E:
- Modelo na posicao 20-21 da chave de 44 digitos:
  - 57 -> CTe (excluir de nfs_referenciadas, usar como chave do CTe)
  - 55 -> NF-e (incluir em nfs_referenciadas)

Formato de saida: identico ao CTeXMLParserCarvia.get_todas_informacoes_carvia()
para que o fluxo de classificacao CNPJ e criacao de operacao/subcontrato
funcione sem alteracao.
"""

import logging
import re
from datetime import datetime
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class DactePDFParser:
    """Parser para extrair informacoes de DACTE (CTe PDF) no formato SSW"""

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
            if texto_fallback and len(texto_fallback.strip()) > len((texto or '').strip()):
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
            logger.warning(f"pdfplumber falhou (DACTE): {e}")
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
            logger.warning(f"pypdf falhou (DACTE): {e}")
            return ''

    def is_valid(self) -> bool:
        """Verifica se o texto foi extraido com sucesso"""
        return len(self.texto_completo.strip()) > 50

    def is_dacte(self) -> bool:
        """Verifica se o PDF e um DACTE (nao DANFE).

        Criterios (qualquer um):
        1. Texto "D A C T E" ou "DACTE" presente
        2. "Conhecimento de Transporte" no conteudo
        3. Chave com modelo 57 (posicao 20-21)
        """
        upper = self.texto_completo.upper()

        # Criterio 1: texto DACTE
        if 'D A C T E' in upper or 'DACTE' in upper:
            return True

        # Criterio 2: Conhecimento de Transporte
        if 'CONHECIMENTO DE TRANSPORTE' in upper:
            return True

        # Criterio 3: chave com modelo 57
        chaves = re.findall(r'\d{44}', self.texto_completo)
        for chave in chaves:
            if chave[20:22] == '57':
                return True

        return False

    # --- Helpers ---

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

    def _encontrar_secao(self, nome_secao: str) -> Optional[int]:
        """Encontra indice da linha que marca inicio de uma secao"""
        return self._encontrar_linha(nome_secao)

    def _extrair_cnpj(self, texto: str) -> Optional[str]:
        """Extrai CNPJ (apenas digitos) de um texto"""
        # CNPJ formatado: XX.XXX.XXX/XXXX-XX
        m = re.search(r'(\d{2}[.\s]?\d{3}[.\s]?\d{3}[/\s]?\d{4}[-\s]?\d{2})', texto)
        if m:
            return re.sub(r'\D', '', m.group(1))
        # CNPJ sem formatacao (14 digitos consecutivos)
        m = re.search(r'(\d{14})', texto)
        if m:
            return m.group(1)
        return None

    def _extrair_cpf(self, texto: str) -> Optional[str]:
        """Extrai CPF (apenas digitos) de um texto"""
        # CPF formatado: XXX.XXX.XXX-XX
        m = re.search(r'(\d{3}[.\s]?\d{3}[.\s]?\d{3}[-\s]?\d{2})', texto)
        if m:
            digits = re.sub(r'\D', '', m.group(1))
            if len(digits) == 11:
                return digits
        return None

    def _extrair_valor(self, texto: str) -> Optional[float]:
        """Extrai valor monetario de um texto (formato brasileiro: 1.234,56)"""
        # Formato com separador de milhar e decimal
        m = re.search(r'(\d[\d.]*,\d{2,4})', texto)
        if m:
            val_str = m.group(1).replace('.', '').replace(',', '.')
            try:
                return float(val_str)
            except ValueError:
                pass
        # Formato sem milhar: 319.92 (americano)
        m = re.search(r'(\d+\.\d{2})', texto)
        if m:
            try:
                return float(m.group(1))
            except ValueError:
                pass
        return None

    def _extrair_peso(self, texto: str) -> Optional[float]:
        """Extrai peso de um texto (formato brasileiro: 1.234,567)"""
        m = re.search(r'(\d[\d.]*,\d{1,4})', texto)
        if m:
            val_str = m.group(1).replace('.', '').replace(',', '.')
            try:
                return float(val_str)
            except ValueError:
                pass
        # Formato americano
        m = re.search(r'(\d+\.\d{1,4})', texto)
        if m:
            try:
                return float(m.group(1))
            except ValueError:
                pass
        return None

    # --- Metodos de extracao ---

    def get_chave_acesso_cte(self) -> Optional[str]:
        """Extrai chave de acesso do CTe (44 digitos com modelo=57).

        Busca TODAS as chaves de 44 digitos e retorna a que tem modelo 57
        na posicao 20-21.
        """
        # Primeiro tentar chave formatada (com pontos/barras/hifens): remover separadores
        # Formato SSW: "35.2602.32.767.123/0002-20-57-002-000.190.063-100.128.346-9"
        texto_limpo = re.sub(r'[.\-/\s]', '', self.texto_completo)
        chaves = re.findall(r'\d{44}', texto_limpo)

        for chave in chaves:
            if chave[20:22] == '57':
                return chave

        # Fallback: buscar no texto original (sem limpeza global)
        chaves_orig = re.findall(r'\d{44}', self.texto_completo)
        for chave in chaves_orig:
            if chave[20:22] == '57':
                return chave

        return None

    def get_numero_cte(self) -> Optional[str]:
        """Extrai numero do CTe.

        Strategies:
        1. Procura "NUMERO" no header, pega numero grande na mesma regiao
        2. Strip zeros da chave (posicoes 25-33)
        """
        linhas = self._linhas()

        # Strategy 1: Procurar "NUMERO" (header DACTE)
        for i, linha in enumerate(linhas):
            upper = linha.upper()
            if 'NÚMERO' in upper or 'NUMERO' in upper:
                # Buscar numeros na proxima linha
                if i + 1 < len(linhas):
                    nums = re.findall(r'\d+', linhas[i + 1])
                    # Pegar o maior numero (mais digitos) — provavelmente o CTe
                    if nums:
                        nums_filtrados = [n for n in nums if len(n) >= 4]
                        if nums_filtrados:
                            return str(int(nums_filtrados[0]))
                # Tentar na mesma linha (apos "NUMERO")
                m = re.search(r'N[ÚU]MERO[^0-9]*(\d{3,})', upper)
                if m:
                    return str(int(m.group(1)))

        # Strategy 2: Extrair da chave de acesso (posicoes 25-33)
        chave = self.get_chave_acesso_cte()
        if chave and len(chave) == 44:
            try:
                return str(int(chave[25:34]))
            except ValueError:
                pass

        return None

    def get_serie(self) -> Optional[str]:
        """Extrai serie do CTe"""
        linhas = self._linhas()

        for i, linha in enumerate(linhas):
            upper = linha.upper()
            if 'SÉRIE' in upper or 'SERIE' in upper:
                # Na mesma linha
                m = re.search(r'S[ÉE]RIE[^0-9]*(\d{1,3})', upper)
                if m:
                    return m.group(1)
                # Na proxima linha
                if i + 1 < len(linhas):
                    m = re.search(r'(\d{1,3})', linhas[i + 1])
                    if m:
                        return m.group(1)

        return None

    def get_emitente(self) -> Dict:
        """Extrai dados do emitente (quem emitiu o CTe).

        No DACTE SSW, o emitente aparece no topo com CNPJ e nome da empresa.
        """
        upper = self.texto_completo.upper()
        linhas = self._linhas()

        # CNPJ: buscar nas primeiras 15 linhas (header)
        cnpj = None
        nome = None
        uf = None
        cidade = None

        for i, linha in enumerate(linhas[:20]):
            if cnpj is None:
                cnpj_found = self._extrair_cnpj(linha)
                if cnpj_found:
                    cnpj = cnpj_found

            # Nome do emitente: primeira linha com texto substantivo
            # (nao "DACTE", nao "MODAL", nao numeros puros)
            if nome is None and i > 0:
                texto_limpo = re.sub(r'[^A-ZÀ-Ú\s]', '', linha.upper()).strip()
                if (len(texto_limpo) > 10
                        and 'D A C T E' not in texto_limpo
                        and 'DACTE' not in texto_limpo
                        and 'MODAL' not in texto_limpo
                        and 'MODELO' not in texto_limpo
                        and 'SERIE' not in texto_limpo
                        and 'NÚMERO' not in linha.upper()
                        and 'NUMERO' not in linha.upper()):
                    nome = texto_limpo.strip()

        # UF/Cidade: buscar perto da "INSCRICAO ESTADUAL" ou CNPJ
        for i, linha in enumerate(linhas[:20]):
            upper_l = linha.upper()
            # Padrao "CIDADE/UF" ou "CIDADE - UF"
            m = re.search(r'([A-ZÀ-Ú][A-ZÀ-Ú\s]+?)\s*[/-]\s*([A-Z]{2})\b', upper_l)
            if m and m.group(2) in self._UFS_BRASIL:
                if cidade is None:
                    cidade = m.group(1).strip()
                    uf = m.group(2)

        return {
            'cnpj': cnpj,
            'nome': nome,
            'uf': uf,
            'cidade': cidade,
        }

    def get_tipo_servico(self) -> Optional[str]:
        """Extrai tipo do servico (ex: SUBCONTRATACAO, NORMAL)"""
        m = re.search(
            r'TIPO\s+D[OE]\s+SERVI[CÇ]O[^A-Z]*([A-ZÀ-Ú][A-ZÀ-Ú ]*)',
            self.texto_completo.upper()
        )
        if m:
            return m.group(1).strip()

        # Fallback: buscar palavras-chave
        upper = self.texto_completo.upper()
        if 'SUBCONTRATA' in upper:
            return 'SUBCONTRATACAO'
        if 'REDESPACHO' in upper:
            return 'REDESPACHO'

        return None

    def get_origem_destino(self) -> Dict:
        """Extrai origem e destino da prestacao.

        Busca "ORIGEM DA PRESTACAO" e "DESTINO DA PRESTACAO" seguidos de
        "CIDADE/UF" no formato DACTE SSW.
        """
        result = {
            'uf_origem': None,
            'cidade_origem': None,
            'uf_destino': None,
            'cidade_destino': None,
        }

        linhas = self._linhas()

        for i, linha in enumerate(linhas):
            upper = linha.upper()

            if 'ORIGEM' in upper and 'PRESTA' in upper:
                # Buscar cidade/UF nas proximas 3 linhas
                for j in range(i, min(i + 4, len(linhas))):
                    m = re.search(
                        r'([A-ZÀ-Ú][A-ZÀ-Ú\s]+?)\s*[/-]\s*([A-Z]{2})\b',
                        linhas[j].upper()
                    )
                    if m and m.group(2) in self._UFS_BRASIL:
                        result['cidade_origem'] = m.group(1).strip()
                        result['uf_origem'] = m.group(2)
                        break

            if 'DESTINO' in upper and 'PRESTA' in upper:
                for j in range(i, min(i + 4, len(linhas))):
                    m = re.search(
                        r'([A-ZÀ-Ú][A-ZÀ-Ú\s]+?)\s*[/-]\s*([A-Z]{2})\b',
                        linhas[j].upper()
                    )
                    if m and m.group(2) in self._UFS_BRASIL:
                        result['cidade_destino'] = m.group(1).strip()
                        result['uf_destino'] = m.group(2)
                        break

        return result

    _SECOES_DACTE = frozenset({
        'REMETENTE', 'DESTINAT', 'EXPEDIDOR', 'RECEBEDOR', 'TOMADOR',
        'PRODUTO PREDOMINANTE', 'INFORM', 'COMPONENTES', 'FRETE TOTAL',
        'CHAVES NF', 'ORIGEM DA', 'DESTINO DA',
    })

    def _extrair_participante(self, nome_secao: str) -> Dict:
        """Extrai dados de um participante (REMETENTE, DESTINATARIO, TOMADOR, etc.)

        Busca a secao pelo nome, depois extrai CNPJ/CPF e nome na regiao.
        Para ao encontrar inicio de outra secao.
        """
        result = {'cnpj': None, 'nome': None}
        linhas = self._linhas()
        idx = self._encontrar_secao(nome_secao)
        if idx is None:
            return result

        # Buscar nas proximas linhas, parando em outra secao
        for j in range(idx + 1, min(idx + 7, len(linhas))):
            linha = linhas[j]
            upper_l = linha.upper().strip()

            # Parar se encontramos inicio de outra secao
            if any(sec in upper_l for sec in self._SECOES_DACTE
                   if sec != nome_secao.upper()):
                break

            # CNPJ (14 digitos)
            if result['cnpj'] is None:
                cnpj = self._extrair_cnpj(linha)
                if cnpj:
                    result['cnpj'] = cnpj
                    continue

            # CPF (11 digitos) — se nao achou CNPJ
            if result['cnpj'] is None:
                cpf = self._extrair_cpf(linha)
                if cpf:
                    result['cnpj'] = cpf  # campo generico para doc
                    continue

            # Nome: linha com texto substantivo
            if result['nome'] is None:
                texto_limpo = re.sub(r'[^A-ZÀ-Úa-zà-ú\s]', '', linha).strip()
                if len(texto_limpo) > 5:
                    if not any(label in texto_limpo.upper() for label in [
                        'CNPJ', 'CPF', 'INSCRI', 'ESTADUAL', 'MUNIC',
                        'ENDERECO', 'CEP', 'TELEFONE', 'PAIS',
                    ]):
                        result['nome'] = texto_limpo.upper()

        return result

    def get_remetente(self) -> Dict:
        """Extrai dados do remetente"""
        return self._extrair_participante('REMETENTE')

    def get_destinatario(self) -> Dict:
        """Extrai dados do destinatario.

        DACTE pode ter CPF em vez de CNPJ para pessoa fisica.
        _extrair_participante ja tenta CPF como fallback.
        """
        return self._extrair_participante('DESTINAT')

    def get_tomador(self) -> Dict:
        """Extrai dados do tomador do servico"""
        return self._extrair_participante('TOMADOR')

    def get_frete_total(self) -> Optional[float]:
        """Extrai valor do frete total.

        Busca "FRETE TOTAL" ou "VALOR TOTAL DA PRESTACAO" seguido de valor.
        """
        linhas = self._linhas()

        for i, linha in enumerate(linhas):
            linha_upper = linha.upper()
            if 'FRETE TOTAL' in linha_upper or ('VALOR TOTAL' in linha_upper and 'PRESTA' in linha_upper):
                # Buscar valor na mesma linha
                valor = self._extrair_valor(linha)
                if valor:
                    return valor
                # Buscar na proxima linha
                if i + 1 < len(linhas):
                    valor = self._extrair_valor(linhas[i + 1])
                    if valor:
                        return valor

        # Fallback: buscar "VALOR DA PRESTACAO" generico
        for i, linha in enumerate(linhas):
            if 'VALOR DA PRESTA' in linha.upper():
                valor = self._extrair_valor(linha)
                if valor:
                    return valor
                if i + 1 < len(linhas):
                    valor = self._extrair_valor(linhas[i + 1])
                    if valor:
                        return valor

        return None

    def get_peso_calculo(self) -> Optional[float]:
        """Extrai peso de calculo (kg)"""
        linhas = self._linhas()

        for i, linha in enumerate(linhas):
            upper = linha.upper()
            if 'PESO' in upper and ('LCULO' in upper or 'CALCULO' in upper):
                peso = self._extrair_peso(linha)
                if peso:
                    return peso
                if i + 1 < len(linhas):
                    peso = self._extrair_peso(linhas[i + 1])
                    if peso:
                        return peso

        # Fallback: PESO BRUTO
        for i, linha in enumerate(linhas):
            if 'PESO BRUTO' in linha.upper():
                peso = self._extrair_peso(linha)
                if peso:
                    return peso
                if i + 1 < len(linhas):
                    peso = self._extrair_peso(linhas[i + 1])
                    if peso:
                        return peso

        return None

    def get_valor_mercadoria(self) -> Optional[float]:
        """Extrai valor da mercadoria"""
        linhas = self._linhas()

        for i, linha in enumerate(linhas):
            upper = linha.upper()
            if 'VALOR' in upper and 'MERCADORIA' in upper:
                valor = self._extrair_valor(linha)
                if valor:
                    return valor
                if i + 1 < len(linhas):
                    valor = self._extrair_valor(linhas[i + 1])
                    if valor:
                        return valor

        return None

    def get_nfs_referenciadas(self) -> List[Dict]:
        """Extrai NFs referenciadas no DACTE.

        Busca secao "CHAVES NF-E/CT-E" ou similar e extrai chaves de 44
        digitos com modelo=55 (NF-e). Chaves com modelo=57 (CTe) sao ignoradas.
        """
        nfs = []
        texto_limpo = re.sub(r'[.\-/\s]', '', self.texto_completo)
        chaves = re.findall(r'\d{44}', texto_limpo)

        seen = set()
        for chave in chaves:
            modelo = chave[20:22]
            if modelo == '55' and chave not in seen:
                seen.add(chave)
                # Extrair numero e CNPJ emitente da chave
                numero_nf = None
                cnpj_emitente = None
                try:
                    cnpj_emitente = chave[6:20]
                    numero_nf = str(int(chave[25:34]))
                except (ValueError, IndexError):
                    pass

                nfs.append({
                    'chave': chave,
                    'numero_nf': numero_nf,
                    'cnpj_emitente': cnpj_emitente,
                })

        return nfs

    def get_data_emissao(self) -> Optional[str]:
        """Extrai data de emissao do CTe.

        Busca padroes DD/MM/YYYY ou DD/MM/YY perto de "AUTORIZA" ou "EMISS".
        Retorna no formato DD/MM/YYYY.
        """
        linhas = self._linhas()

        for i, linha in enumerate(linhas):
            upper = linha.upper()
            if 'AUTORIZA' in upper or 'EMISS' in upper:
                # Buscar data na mesma linha e proxima
                for j in range(i, min(i + 3, len(linhas))):
                    # DD/MM/YYYY HH:MM ou DD/MM/YYYY
                    m = re.search(r'(\d{2}/\d{2}/\d{4})', linhas[j])
                    if m:
                        return m.group(1)
                    # DD/MM/YY HH:MM
                    m = re.search(r'(\d{2}/\d{2}/(\d{2}))\s', linhas[j])
                    if m:
                        dd_mm_yy = m.group(1)
                        try:
                            dt = datetime.strptime(dd_mm_yy, '%d/%m/%y')
                            return dt.strftime('%d/%m/%Y')
                        except ValueError:
                            pass

        # Fallback: qualquer data nas primeiras 15 linhas
        for i, linha in enumerate(linhas[:15]):
            m = re.search(r'(\d{2}/\d{2}/\d{4})', linha)
            if m:
                return m.group(1)

        return None

    def get_todas_informacoes(self) -> Dict:
        """Extrai todas as informacoes do DACTE.

        Formato de saida IDENTICO ao CTeXMLParserCarvia.get_todas_informacoes_carvia()
        para compatibilidade com o fluxo de importacao.
        """
        rota = self.get_origem_destino()
        emit = self.get_emitente()
        rem = self.get_remetente()
        dest = self.get_destinatario()
        nfs = self.get_nfs_referenciadas()
        chave = self.get_chave_acesso_cte()

        # Calcular confianca
        campos_encontrados = 0
        campos_total = 6  # chave, numero, valor, emitente_cnpj, origem, destino

        if chave:
            campos_encontrados += 1
        if self.get_numero_cte():
            campos_encontrados += 1
        if self.get_frete_total():
            campos_encontrados += 1
        if emit.get('cnpj'):
            campos_encontrados += 1
        if rota.get('uf_origem'):
            campos_encontrados += 1
        if rota.get('uf_destino'):
            campos_encontrados += 1

        self.confianca = campos_encontrados / campos_total

        return {
            # CTe
            'cte_numero': self.get_numero_cte(),
            'cte_chave_acesso': chave,
            'cte_valor': self.get_frete_total(),
            'cte_data_emissao': self.get_data_emissao(),
            # Rota
            'uf_origem': rota.get('uf_origem'),
            'cidade_origem': rota.get('cidade_origem'),
            'uf_destino': rota.get('uf_destino'),
            'cidade_destino': rota.get('cidade_destino'),
            # Carga
            'valor_mercadoria': self.get_valor_mercadoria(),
            'peso_bruto': self.get_peso_calculo(),
            'peso_cubado': None,  # DACTE nao tem peso cubado
            # Participantes
            'emitente': emit,
            'remetente': rem,
            'destinatario': dest,
            # NFs referenciadas
            'nfs_referenciadas': nfs,
            # Impostos (DACTE PDF nao tem detalhe de impostos)
            'impostos': {},
        }
