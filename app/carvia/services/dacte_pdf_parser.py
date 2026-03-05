"""
Parser de DACTE PDF para o modulo CarVia — Multi-Formato
=========================================================

Extrai dados de DACTE (Documento Auxiliar de CTe) a partir de PDF.
Utiliza pdfplumber (primario) + pypdf (fallback).

Suporta 5 formatos de layout:
  - SSW (ssw.inf.br): Tocantins, Velocargas, Dago
  - Bsoft (Bsoft Internetworks): Transmenezes
  - ESL (ESL Informatica): Transperola
  - Lonngren (Lonngren Sistemas): CD Uni Brasil
  - Montenegro (Impresso por :): Montenegro

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
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# CNPJ da CarVia para detectar CTe referenciado em observacoes de subcontrato
_CARVIA_CNPJ_RAIZ = '62312605'


class DactePDFParser:
    """Parser para extrair informacoes de DACTE (CTe PDF) multi-formato"""

    _UFS_BRASIL = frozenset({
        'AC', 'AL', 'AP', 'AM', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA',
        'MG', 'MS', 'MT', 'PA', 'PB', 'PE', 'PI', 'PR', 'RJ', 'RN',
        'RO', 'RR', 'RS', 'SC', 'SE', 'SP', 'TO',
    })

    # Formatos detectaveis pelo footer/marca d'agua do PDF
    FORMATO_SSW = 'SSW'
    FORMATO_BSOFT = 'BSOFT'
    FORMATO_ESL = 'ESL'
    FORMATO_LONNGREN = 'LONNGREN'
    FORMATO_MONTENEGRO = 'MONTENEGRO'
    FORMATO_GENERICO = 'GENERICO'

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
        self.formato = self.FORMATO_GENERICO
        self._extrair_texto()
        self._detectar_formato()

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

    def _detectar_formato(self):
        """Detecta o formato/sistema gerador do DACTE pelo footer/marca d'agua.

        Ordem de verificacao:
        1. SSW: "SSW.INF.BR" ou "ssw.inf.br"
        2. ESL: "ESLSISTEMAS" ou "ESL INFORM" ou "ESL Informatica"
        3. Lonngren: "LONNGREN"
        4. Bsoft: "BSOFT"
        5. Montenegro: "Impresso por" (marca generica, por ultimo)
        6. GENERICO: fallback
        """
        upper = self.texto_completo.upper()
        if 'SSW.INF.BR' in upper or 'SSW INF BR' in upper:
            self.formato = self.FORMATO_SSW
        elif 'ESLSISTEMAS' in upper or 'ESL INFORM' in upper:
            self.formato = self.FORMATO_ESL
        elif 'LONNGREN' in upper:
            self.formato = self.FORMATO_LONNGREN
        elif 'BSOFT' in upper:
            self.formato = self.FORMATO_BSOFT
        elif 'IMPRESSO POR' in upper:
            self.formato = self.FORMATO_MONTENEGRO
        else:
            self.formato = self.FORMATO_GENERICO

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

        # Criterio 3: chave com modelo 57 — usa metodo robusto
        chave = self.get_chave_acesso_cte()
        if chave:
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
        """Extrai peso de um texto (formato brasileiro: 1.234,567 ou americano: 1234.567)"""
        # Formato brasileiro: virgula decimal
        m = re.search(r'(\d[\d.]*,\d{1,4})', texto)
        if m:
            val_str = m.group(1).replace('.', '').replace(',', '.')
            try:
                return float(val_str)
            except ValueError:
                pass
        # Formato americano: ponto decimal
        m = re.search(r'(\d+\.\d{1,4})', texto)
        if m:
            try:
                return float(m.group(1))
            except ValueError:
                pass
        # Formato Bsoft: "1799,105/KG" — numero com barra antes de unidade
        m = re.search(r'(\d[\d.]*,\d{1,4})\s*/?\s*KG', texto, re.IGNORECASE)
        if m:
            val_str = m.group(1).replace('.', '').replace(',', '.')
            try:
                return float(val_str)
            except ValueError:
                pass
        return None

    def _extrair_cidade_uf(self, texto: str) -> Optional[Tuple[str, str]]:
        """Extrai PRIMEIRO par (cidade, uf) de um texto. Wrapper de _extrair_todas_cidade_uf."""
        matches = self._extrair_todas_cidade_uf(texto)
        return matches[0] if matches else None

    def _extrair_todas_cidade_uf(self, texto: str) -> List[Tuple[str, str]]:
        """Extrai TODOS os pares (cidade, uf) de um texto.

        Suporta 2 formatos:
        - Pattern 1: "CIDADE - UF" ou "CIDADE/UF" (SSW, Bsoft, Lonngren, Montenegro)
        - Pattern 2: "UF - Cidade" (ESL: "SP - Santana de Parnaiba RO - Colorado do Oeste")

        Retorna lista de tuplas (cidade, uf) na ordem de aparicao.
        """
        upper = texto.upper()
        results = []

        # Pattern 1: CIDADE - UF ou CIDADE/UF (mais comum)
        for m in re.finditer(r'([A-ZÀ-Ú][A-ZÀ-Ú\s]+?)\s*[/\-]\s*([A-Z]{2})\b', upper):
            if m.group(2) in self._UFS_BRASIL:
                cidade = m.group(1).strip()
                # Ignorar matches espurios como "R - SP" (rua), "CEP - PE" etc.
                if len(cidade) >= 3 and not any(kw in cidade for kw in ['CEP', 'RUA', 'ENDERECO']):
                    results.append((cidade, m.group(2)))

        if results:
            return results

        # Pattern 2: UF - Cidade (ESL) — split pela posicao das UFs
        # Ex: "SP - Santana de Parnaiba RO - Colorado do Oeste"
        uf_positions = []
        for m in re.finditer(r'\b([A-Z]{2})\s*-\s*', upper):
            if m.group(1) in self._UFS_BRASIL:
                uf_positions.append((m.group(1), m.start(), m.end()))

        for idx, (uf, _, end) in enumerate(uf_positions):
            # Cidade: do fim do match ate o inicio da proxima UF (ou fim do texto)
            if idx + 1 < len(uf_positions):
                next_start = uf_positions[idx + 1][1]
                trecho = upper[end:next_start].strip()
            else:
                trecho = upper[end:].strip()

            # Limpar: remover numeros, pontuacao no final
            cidade = re.sub(r'[\d:;\-/]+$', '', trecho).strip()
            if len(cidade) >= 3:
                results.append((cidade, uf))

        return results


    # --- Metodos de extracao ---

    def get_chave_acesso_cte(self) -> Optional[str]:
        """Extrai chave de acesso do CTe (44 digitos com modelo=57).

        3 niveis de busca para suportar todos os formatos:
        1. Chave com 44 digitos consecutivos no texto original
        2. Blocos de digitos com separadores (formatado) — limpa por match
        3. Secao "Chave de acesso" — busca localizada

        IMPORTANTE: NAO faz strip global de separadores (bug Montenegro onde
        CEP contamina a chave quando espacos sao removidos globalmente).

        Quando multiplas chaves modelo=57 sao encontradas, prioriza:
        - Chave cujo CNPJ (pos 6-19) bate com o emitente do header
        - Se nao bate, retorna a primeira encontrada
        """
        # Detectar CNPJ do emitente no header para priorizar chave correta
        cnpj_emitente = None
        linhas = self._linhas()
        for linha in linhas[:10]:
            cnpj = self._extrair_cnpj(linha)
            if cnpj and len(cnpj) == 14:
                cnpj_emitente = cnpj
                break

        todas_chaves = []

        # Nivel 1: 44 digitos consecutivos no texto original
        for m in re.finditer(r'\d{44}', self.texto_completo):
            chave = m.group(0)
            if chave[20:22] == '57' and chave not in [c for c, _ in todas_chaves]:
                todas_chaves.append((chave, m.start()))

        # Nivel 2: Blocos formatados com separadores (pontos, espacos, hifens, barras)
        pattern_formatado = re.compile(
            r'(\d{2,4}[\s.\-/]+(?:\d{2,4}[\s.\-/]+){8,}\d{1,4})'
        )
        for match in pattern_formatado.finditer(self.texto_completo):
            candidato = re.sub(r'[.\-/\s]', '', match.group(0))
            if len(candidato) >= 44:
                for start_pos in range(len(candidato) - 43):
                    sub = candidato[start_pos:start_pos + 44]
                    if (sub.isdigit() and sub[20:22] == '57'
                            and sub not in [c for c, _ in todas_chaves]):
                        todas_chaves.append((sub, match.start()))

        # Nivel 3: Busca localizada na secao "Chave de acesso"
        for i, linha in enumerate(linhas):
            upper = linha.upper()
            if 'CHAVE' in upper and ('ACESSO' in upper or 'CT-E' in upper):
                for j in range(i, min(i + 4, len(linhas))):
                    for m in re.finditer(r'\d{44}', linhas[j]):
                        chave = m.group(0)
                        if (chave[20:22] == '57'
                                and chave not in [c for c, _ in todas_chaves]):
                            todas_chaves.append((chave, 0))
                    # Digitos com separadores
                    candidato = re.sub(r'[.\-/\s]', '', linhas[j])
                    if len(candidato) >= 44:
                        for start_pos in range(len(candidato) - 43):
                            sub = candidato[start_pos:start_pos + 44]
                            if (sub.isdigit() and sub[20:22] == '57'
                                    and sub not in [c for c, _ in todas_chaves]):
                                todas_chaves.append((sub, 0))

        if not todas_chaves:
            return None

        # Se ha apenas 1 chave, retorna
        if len(todas_chaves) == 1:
            return todas_chaves[0][0]

        # Priorizar: chave cujo CNPJ (pos 6-19) bate com emitente do header
        if cnpj_emitente:
            for chave, _ in todas_chaves:
                if chave[6:20] == cnpj_emitente:
                    return chave

        # Fallback: retornar a primeira chave encontrada
        return todas_chaves[0][0]


    def get_numero_cte(self) -> Optional[str]:
        """Extrai numero do CTe.

        Strategies (ordem de confiabilidade):
        1. Texto: Procura "NUMERO" no header, pega numero na proxima linha
           (filtra CEPs — 8 digitos iniciando com 0)
        2. Chave: Extrai das posicoes 25-33 da chave de acesso

        Prefere texto primeiro porque:
        - SSW: chave pode estar garbled (overlay de URL sobre digitos)
        - Montenegro: chave OK, mas texto precisa filtrar CEP

        Se ambos encontram valores diferentes, prefere texto (mais confiavel
        como numero de EXIBICAO do DACTE).
        """
        linhas = self._linhas()

        # Strategy 1: Procurar "NUMERO" (header DACTE)
        numero_texto = None
        for i, linha in enumerate(linhas):
            upper = linha.upper()
            if 'NÚMERO' in upper or 'NUMERO' in upper:
                # Buscar numeros na proxima linha
                if i + 1 < len(linhas):
                    nums = re.findall(r'\d+', linhas[i + 1])
                    if nums:
                        # Filtrar CEPs (8 digitos, tipicamente comecam com 0)
                        # e numeros muito grandes (CNPJ parcial, etc.)
                        nums_filtrados = [
                            n for n in nums
                            if 4 <= len(n) <= 9
                            and not (len(n) == 8 and n[0] == '0')  # CEP
                        ]
                        if nums_filtrados:
                            numero_texto = str(int(nums_filtrados[0]))
                            break
                # Tentar na mesma linha (apos "NUMERO")
                m = re.search(r'N[ÚU]MERO[^0-9]*(\d{3,9})', upper)
                if m:
                    numero_texto = str(int(m.group(1)))
                    break

        if numero_texto and numero_texto != '0':
            return numero_texto

        # Strategy 2: Extrair da chave de acesso (posicoes 25-33)
        chave = self.get_chave_acesso_cte()
        if chave and len(chave) == 44:
            try:
                numero_chave = str(int(chave[25:34]))
                if numero_chave != '0':
                    return numero_chave
            except ValueError:
                pass

        # Ultimo fallback: retornar texto mesmo se 0
        return numero_texto


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
            resultado = self._extrair_cidade_uf(linha)
            if resultado and cidade is None:
                cidade, uf = resultado

        return {
            'cnpj': cnpj,
            'nome': nome,
            'uf': uf,
            'cidade': cidade,
        }

    def get_tipo_servico(self) -> Optional[str]:
        """Extrai tipo do servico (ex: SUBCONTRATACAO, NORMAL, REDESPACHO)"""
        m = re.search(
            r'TIPO\s+D[OE]\s+SERVI[CÇ]O[^A-Z]*([A-ZÀ-Ú][A-ZÀ-Ú ]*)',
            self.texto_completo.upper()
        )
        if m:
            tipo = m.group(1).strip()
            # Montenegro usa "OUTROS" como tipo — normalizar
            if tipo == 'OUTROS':
                # Verificar se ha indicacao de redespacho/subcontratacao no texto
                upper = self.texto_completo.upper()
                if 'SUBCONTRATA' in upper:
                    return 'SUBCONTRATACAO'
                if 'REDESPACHO' in upper:
                    return 'REDESPACHO'
            return tipo

        # Fallback: buscar palavras-chave
        upper = self.texto_completo.upper()
        if 'SUBCONTRATA' in upper:
            return 'SUBCONTRATACAO'
        if 'REDESPACHO' in upper:
            return 'REDESPACHO'

        return None

    def get_origem_destino(self) -> Dict:
        """Extrai origem e destino da prestacao.

        Suporta multiplos formatos de label:
        - SSW/Bsoft/Lonngren: "ORIGEM DA PRESTACAO" / "DESTINO DA PRESTACAO"
        - ESL: "INICIO DA PRESTACAO" / "TERMINO DA PRESTACAO"
        - Montenegro: ambos labels na mesma linha, cidades na proxima linha

        Suporta multiplos formatos de cidade/UF via _extrair_todas_cidade_uf().
        """
        result = {
            'uf_origem': None,
            'cidade_origem': None,
            'uf_destino': None,
            'cidade_destino': None,
        }

        linhas = self._linhas()

        # Patterns para labels de origem
        origin_labels = [
            lambda u: 'ORIGEM' in u and 'PRESTA' in u,
            lambda u: ('INÍCIO' in u or 'INICIO' in u) and 'PRESTA' in u,
        ]
        # Patterns para labels de destino
        dest_labels = [
            lambda u: 'DESTINO' in u and 'PRESTA' in u,
            lambda u: ('TÉRMINO' in u or 'TERMINO' in u) and 'PRESTA' in u,
        ]

        # Detectar se ORIGEM e DESTINO estao na MESMA linha (Montenegro/ESL)
        for i, linha in enumerate(linhas):
            upper = linha.upper()
            has_origin = any(fn(upper) for fn in origin_labels)
            has_dest = any(fn(upper) for fn in dest_labels)

            if has_origin and has_dest:
                # Ambos labels na mesma linha — buscar 2 cidades nas proximas linhas
                for j in range(i, min(i + 5, len(linhas))):
                    matches = self._extrair_todas_cidade_uf(linhas[j])
                    if len(matches) >= 2:
                        result['cidade_origem'] = matches[0][0]
                        result['uf_origem'] = matches[0][1]
                        result['cidade_destino'] = matches[1][0]
                        result['uf_destino'] = matches[1][1]
                        return result
                    elif len(matches) == 1 and result['uf_origem'] is None:
                        result['cidade_origem'] = matches[0][0]
                        result['uf_origem'] = matches[0][1]
                # Se so encontrou 1 cidade, continua para buscar destino separado
                break

        # Busca separada (labels em linhas diferentes)
        for i, linha in enumerate(linhas):
            upper = linha.upper()

            # Origem
            if result['uf_origem'] is None:
                for label_fn in origin_labels:
                    if label_fn(upper):
                        for j in range(i, min(i + 5, len(linhas))):
                            matches = self._extrair_todas_cidade_uf(linhas[j])
                            if matches:
                                result['cidade_origem'] = matches[0][0]
                                result['uf_origem'] = matches[0][1]
                                break
                        break

            # Destino
            if result['uf_destino'] is None:
                for label_fn in dest_labels:
                    if label_fn(upper):
                        for j in range(i, min(i + 5, len(linhas))):
                            matches = self._extrair_todas_cidade_uf(linhas[j])
                            for cidade, uf in matches:
                                # Evitar reusar a mesma cidade da origem
                                if (cidade == result.get('cidade_origem')
                                        and uf == result.get('uf_origem')):
                                    continue
                                result['cidade_destino'] = cidade
                                result['uf_destino'] = uf
                                break
                            if result['uf_destino']:
                                break
                        break

        return result


    _SECOES_DACTE = frozenset({
        'REMETENTE', 'DESTINAT', 'EXPEDIDOR', 'RECEBEDOR', 'TOMADOR',
        'PRODUTO PREDOMINANTE', 'INFORM', 'COMPONENTES', 'FRETE TOTAL',
        'CHAVES NF', 'ORIGEM DA', 'DESTINO DA', 'INICIO DA', 'TERMINO DA',
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

        Busca por ordem de prioridade:
        1. "FRETE TOTAL" (SSW)
        2. "VALOR TOTAL" + "PRESTA" (SSW/Montenegro)
        3. "VALOR TOTAL" + "SERVI" (Bsoft/Lonngren: "VALOR TOTAL DO SERVICO")
        4. "VALOR TOTAL:" seguido de valor (ESL: "VALOR TOTAL: 330,18")
        5. "A RECEBER" / "À RECEBER" (fallback universal)
        6. "VALOR DA PRESTA" generico (cuidado: extracao restrita ao trecho APOS o label)
        """
        linhas = self._linhas()

        # Prioridade 1: "FRETE TOTAL" ou "VALOR TOTAL" + "PRESTA"
        for i, linha in enumerate(linhas):
            linha_upper = linha.upper()
            if 'FRETE TOTAL' in linha_upper or ('VALOR TOTAL' in linha_upper and 'PRESTA' in linha_upper):
                valor = self._extrair_valor(linha)
                if valor:
                    return valor
                if i + 1 < len(linhas):
                    valor = self._extrair_valor(linhas[i + 1])
                    if valor:
                        return valor

        # Prioridade 2: "VALOR TOTAL" + "SERVI" (Bsoft/Lonngren)
        for i, linha in enumerate(linhas):
            linha_upper = linha.upper()
            if 'VALOR TOTAL' in linha_upper and 'SERVI' in linha_upper:
                valor = self._extrair_valor(linha)
                if valor:
                    return valor
                if i + 1 < len(linhas):
                    valor = self._extrair_valor(linhas[i + 1])
                    if valor:
                        return valor

        # Prioridade 3: "VALOR TOTAL:" ou "VALOR TOTAL :" (ESL — ex: "VALOR TOTAL: 330,18")
        for i, linha in enumerate(linhas):
            linha_upper = linha.upper()
            if 'VALOR TOTAL' in linha_upper:
                # Extrair valor APOS "VALOR TOTAL"
                m = re.search(r'VALOR\s+TOTAL\s*:?\s*(\d[\d.,]*)', linha_upper)
                if m:
                    valor = self._extrair_valor(m.group(1))
                    if valor:
                        return valor
                # Valor pode estar apos ":" na mesma linha
                idx_vt = linha_upper.find('VALOR TOTAL')
                if idx_vt >= 0:
                    trecho = linha[idx_vt:]
                    valor = self._extrair_valor(trecho)
                    if valor:
                        return valor
                if i + 1 < len(linhas):
                    valor = self._extrair_valor(linhas[i + 1])
                    if valor:
                        return valor

        # Prioridade 4: "A RECEBER" ou "À RECEBER" (fallback universal)
        for i, linha in enumerate(linhas):
            linha_upper = linha.upper()
            if 'A RECEBER' in linha_upper or 'À RECEBER' in linha_upper:
                # Buscar valor APOS "RECEBER" na mesma linha
                idx_rec = max(linha_upper.find('A RECEBER'), linha_upper.find('À RECEBER'))
                if idx_rec >= 0:
                    trecho = linha[idx_rec:]
                    valor = self._extrair_valor(trecho)
                    if valor:
                        return valor
                # Valor na proxima linha
                if i + 1 < len(linhas):
                    valor = self._extrair_valor(linhas[i + 1])
                    if valor:
                        return valor

        # Prioridade 5: "VALOR DA PRESTA" generico
        # CUIDADO: extrair SOMENTE do trecho APOS o label (evitar CEP que precede)
        for i, linha in enumerate(linhas):
            linha_upper = linha.upper()
            if 'VALOR DA PRESTA' in linha_upper:
                idx_vp = linha_upper.find('VALOR DA PRESTA')
                trecho = linha[idx_vp:]
                valor = self._extrair_valor(trecho)
                if valor:
                    return valor
                if i + 1 < len(linhas):
                    valor = self._extrair_valor(linhas[i + 1])
                    if valor:
                        return valor

        return None


    def get_peso_calculo(self) -> Optional[float]:
        """Extrai peso de calculo (kg).

        Busca por ordem de prioridade:
        1. "PESO" + "CALCULO" (SSW)
        2. "PESO BRUTO" (SSW fallback)
        3. "PESO TAXADO" (ESL — peso de calculo efetivo)
        4. "PESO REAL" (ESL — peso fisico)
        5. "PESO" seguido de valor numerico + "KG" (Bsoft: "PESO 1799,105/KG")
        """
        linhas = self._linhas()

        # Prioridade 1: PESO DE CALCULO
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

        # Prioridade 2: PESO BRUTO
        for i, linha in enumerate(linhas):
            if 'PESO BRUTO' in linha.upper():
                peso = self._extrair_peso(linha)
                if peso:
                    return peso
                if i + 1 < len(linhas):
                    peso = self._extrair_peso(linhas[i + 1])
                    if peso:
                        return peso

        # Prioridade 3: PESO TAXADO (ESL — peso de calculo efetivo)
        for i, linha in enumerate(linhas):
            if 'PESO TAXADO' in linha.upper():
                peso = self._extrair_peso(linha)
                if peso:
                    return peso
                if i + 1 < len(linhas):
                    peso = self._extrair_peso(linhas[i + 1])
                    if peso:
                        return peso

        # Prioridade 4: PESO REAL (ESL)
        for i, linha in enumerate(linhas):
            if 'PESO REAL' in linha.upper():
                peso = self._extrair_peso(linha)
                if peso:
                    return peso
                if i + 1 < len(linhas):
                    peso = self._extrair_peso(linhas[i + 1])
                    if peso:
                        return peso

        # Prioridade 5: "PESO" seguido de valor+KG (Bsoft: "PESO 1799,105/KG")
        for i, linha in enumerate(linhas):
            upper = linha.upper()
            if 'PESO' in upper and 'KG' in upper:
                # Evitar linhas que ja foram capturadas acima (PESO CALCULO, etc.)
                if not any(kw in upper for kw in ['CALCULO', 'LCULO', 'BRUTO', 'TAXADO', 'REAL', 'CUBADO']):
                    peso = self._extrair_peso(linha)
                    if peso:
                        return peso

        return None

    def get_peso_cubado_pdf(self) -> Optional[float]:
        """Extrai peso cubado (kg).

        Busca "PESO CUBADO" seguido de valor. Presente em ESL e alguns outros formatos.
        """
        linhas = self._linhas()

        for i, linha in enumerate(linhas):
            if 'PESO CUBADO' in linha.upper():
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

        IMPORTANTE: Usa mesma logica robusta de get_chave_acesso_cte() para
        encontrar chaves formatadas com separadores.
        """
        nfs = []
        seen = set()

        # Nivel 1: 44 digitos consecutivos no texto original
        chaves_orig = re.findall(r'\d{44}', self.texto_completo)
        for chave in chaves_orig:
            modelo = chave[20:22]
            if modelo == '55' and chave not in seen:
                seen.add(chave)
                self._adicionar_nf(nfs, chave)

        # Nivel 2: Blocos formatados com separadores
        pattern_formatado = re.compile(
            r'(\d{2,4}[\s.\-/]+(?:\d{2,4}[\s.\-/]+){8,}\d{1,4})'
        )
        for match in pattern_formatado.finditer(self.texto_completo):
            candidato = re.sub(r'[.\-/\s]', '', match.group(0))
            if len(candidato) >= 44:
                for start in range(len(candidato) - 43):
                    sub = candidato[start:start + 44]
                    if sub.isdigit() and sub[20:22] == '55' and sub not in seen:
                        seen.add(sub)
                        self._adicionar_nf(nfs, sub)

        return nfs

    def _adicionar_nf(self, nfs: List[Dict], chave: str):
        """Adiciona NF ao resultado, extraindo numero e CNPJ da chave"""
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

    def get_cte_carvia_referenciado(self) -> Optional[str]:
        """Extrai referencia ao CTe CarVia das observacoes de subcontrato.

        Todos os formatos de subcontrato mencionam o CTe original da CarVia:
        "Transporte subcontratado por CARVIA LOGISTICA, CNPJ 62.312.605/0001-75,
         CT-e: 001-000000031"

        Tambem presente em:
        - "Documentos Anteriores" (Lonngren)
        - "CHAVES NF-E/CT-E" com prefixo CT-E: (SSW)

        Returns:
            String no formato "serie-numero" (ex: "001-000000031") ou chave 44 digitos
            do CTe CarVia referenciado. None se nao encontrado.
        """
        # Verificar se CNPJ CarVia esta presente (indica subcontrato)
        cnpj_carvia_patterns = [
            '62.312.605', '62312605',
        ]
        tem_ref_carvia = any(p in self.texto_completo for p in cnpj_carvia_patterns)

        if not tem_ref_carvia:
            return None

        # Pattern 1: "CT-e: 001-000000031" ou "CTe: 001-000000031"
        m = re.search(r'CT-?[Ee]:\s*(\d{3}[-/]\d+)', self.texto_completo)
        if m:
            return m.group(1)

        # Pattern 2: Chave 44 digitos com CNPJ raiz CarVia (62312605) e modelo=57
        # O CNPJ aparece nas posicoes 6-20 da chave
        chaves = re.findall(r'\d{44}', self.texto_completo)
        for chave in chaves:
            if chave[20:22] == '57' and _CARVIA_CNPJ_RAIZ in chave[6:20]:
                return chave

        # Pattern 3: Buscar em blocos formatados
        pattern_formatado = re.compile(
            r'(\d{2,4}[\s.\-/]+(?:\d{2,4}[\s.\-/]+){8,}\d{1,4})'
        )
        for match in pattern_formatado.finditer(self.texto_completo):
            candidato = re.sub(r'[.\-/\s]', '', match.group(0))
            if len(candidato) >= 44:
                for start in range(len(candidato) - 43):
                    sub = candidato[start:start + 44]
                    if (sub.isdigit() and sub[20:22] == '57'
                            and _CARVIA_CNPJ_RAIZ in sub[6:20]):
                        return sub

        return None

    def get_componentes_frete(self) -> Dict[str, float]:
        """Extrai componentes individuais do frete.

        Busca padroes como:
        - "FRETE PESO 481,81"
        - "DESPACHO 24,51"
        - "GRIS 22,70"
        - "PEDAGIO 37,52"

        Returns:
            Dict {nome_componente: valor} (ex: {"FRETE PESO": 481.81, "GRIS": 22.70})
        """
        componentes = {}
        linhas = self._linhas()

        # Localizar secao de componentes do frete
        secao_inicio = None
        secao_fim = None
        for i, linha in enumerate(linhas):
            upper = linha.upper()
            if 'COMPONENTES' in upper and ('FRETE' in upper or 'VALOR' in upper):
                secao_inicio = i
            elif secao_inicio is not None and secao_fim is None:
                # Parar em outra secao
                if any(sec in upper for sec in [
                    'INFORMAÇ', 'INFORMAC', 'OBSERV', 'CHAVES NF',
                    'ORIGEM DA', 'DESTINO DA', 'INICIO DA', 'TERMINO DA',
                ]):
                    secao_fim = i
                    break

        if secao_inicio is None:
            return componentes

        if secao_fim is None:
            secao_fim = min(secao_inicio + 15, len(linhas))

        # Extrair componentes: NOME + VALOR na mesma linha
        componente_pattern = re.compile(
            r'([A-ZÀ-Ú][A-ZÀ-Ú\s]{2,30}?)\s+'
            r'(\d[\d.]*[,.]?\d{0,4})\s*$'
        )
        for i in range(secao_inicio + 1, secao_fim):
            linha = linhas[i].strip()
            if not linha:
                continue
            m = componente_pattern.search(linha.upper())
            if m:
                nome = m.group(1).strip()
                valor_str = m.group(2)
                valor = self._extrair_valor(valor_str)
                if valor is None:
                    # Tentar como peso (menos restritivo)
                    valor = self._extrair_peso(valor_str)
                if valor is not None and valor > 0:
                    componentes[nome] = valor

        return componentes

    def get_volumes(self) -> Optional[int]:
        """Extrai quantidade de volumes/unidades.

        Busca padroes como "QUANTIDADE 5" ou "QTD 5" ou "VOLUMES 5".
        """
        linhas = self._linhas()

        for linha in linhas:
            upper = linha.upper()
            # "QUANTIDADE" perto de contexto de carga (nao de documentos/NFs)
            if ('QUANTIDADE' in upper or 'QTD' in upper) and 'DOCUMENTO' not in upper:
                m = re.search(r'(?:QUANTIDADE|QTD)\s*[:\s]*(\d+)', upper)
                if m:
                    try:
                        vol = int(m.group(1))
                        if 0 < vol < 100000:  # sanity check
                            return vol
                    except ValueError:
                        pass

            if 'VOLUME' in upper:
                m = re.search(r'VOLUME[S]?\s*[:\s]*(\d+)', upper)
                if m:
                    try:
                        vol = int(m.group(1))
                        if 0 < vol < 100000:
                            return vol
                    except ValueError:
                        pass

        return None

    def get_todas_informacoes(self) -> Dict:
        """Extrai todas as informacoes do DACTE.

        Formato de saida IDENTICO ao CTeXMLParserCarvia.get_todas_informacoes_carvia()
        para compatibilidade com o fluxo de importacao.
        Campos novos (formato, cte_carvia_ref, etc.) sao ADICIONAIS e nao quebram
        consumidores existentes.
        """
        rota = self.get_origem_destino()
        emit = self.get_emitente()
        rem = self.get_remetente()
        dest = self.get_destinatario()
        nfs = self.get_nfs_referenciadas()
        chave = self.get_chave_acesso_cte()
        numero = self.get_numero_cte()
        frete = self.get_frete_total()
        peso = self.get_peso_calculo()
        peso_cubado = self.get_peso_cubado_pdf()

        # Calcular confianca ponderada
        # Campos criticos (peso 2x): chave, frete
        # Campos importantes (peso 1.5x): rota (origem+destino)
        # Campos normais (peso 1x): numero, emitente_cnpj, peso
        pesos_campos = {
            'chave': (2.0, bool(chave)),
            'frete': (2.0, bool(frete)),
            'numero': (1.0, bool(numero)),
            'emitente_cnpj': (1.0, bool(emit.get('cnpj'))),
            'origem': (1.5, bool(rota.get('uf_origem'))),
            'destino': (1.5, bool(rota.get('uf_destino'))),
            'peso': (1.0, bool(peso)),
        }

        peso_total = sum(p for p, _ in pesos_campos.values())
        peso_encontrado = sum(p for p, encontrado in pesos_campos.values() if encontrado)
        self.confianca = peso_encontrado / peso_total if peso_total > 0 else 0.0

        return {
            # CTe
            'cte_numero': numero,
            'cte_chave_acesso': chave,
            'cte_valor': frete,
            'cte_data_emissao': self.get_data_emissao(),
            # Rota
            'uf_origem': rota.get('uf_origem'),
            'cidade_origem': rota.get('cidade_origem'),
            'uf_destino': rota.get('uf_destino'),
            'cidade_destino': rota.get('cidade_destino'),
            # Carga
            'valor_mercadoria': self.get_valor_mercadoria(),
            'peso_bruto': peso,
            'peso_cubado': peso_cubado,
            # Participantes
            'emitente': emit,
            'remetente': rem,
            'destinatario': dest,
            # NFs referenciadas
            'nfs_referenciadas': nfs,
            # Impostos (DACTE PDF nao tem detalhe de impostos)
            'impostos': {},
            # Campos novos (multi-formato)
            'formato': self.formato,
            'tipo_servico': self.get_tipo_servico(),
            'cte_carvia_ref': self.get_cte_carvia_referenciado(),
            'componentes_frete': self.get_componentes_frete(),
            'volumes': self.get_volumes(),
        }
