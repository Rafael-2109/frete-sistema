"""
Utilitário para Parsing de XML de CTe
=====================================

OBJETIVO:
    Extrair informações específicas de CTes a partir do XML,
    incluindo identificação de CTes complementares e suas referências

ESTRUTURA DE CTe COMPLEMENTAR (SEFAZ):
    <tpCTe>1</tpCTe>  <!-- Tipo: 0=Normal, 1=Complementar, 2=Anulação, 3=Substituto -->
    <infCteComp>
        <chCTe>chave_do_cte_original</chCTe>
    </infCteComp>
    <xObs>Motivo do complemento</xObs>

AUTOR: Sistema de Fretes
DATA: 15/11/2025
"""

import logging
import xml.etree.ElementTree as ET
from typing import Dict, Optional
import re
import unicodedata

logger = logging.getLogger(__name__)


class CTeXMLParser:
    """Parser para extrair informações de XMLs de CTe"""

    # Namespaces comuns em XMLs de CTe
    NAMESPACES = {
        'cte': 'http://www.portalfiscal.inf.br/cte'
    }

    def __init__(self, xml_content: str):
        """
        Inicializa o parser com o conteúdo XML

        Args:
            xml_content: String contendo o XML completo
        """
        self.xml_content = xml_content
        self.root = None
        self._parse()

    def _parse(self):
        """Faz o parsing do XML com tratamento de encoding"""
        try:
            # Garantir que o XML está em UTF-8
            if isinstance(self.xml_content, bytes):
                # Se vier como bytes, tentar decodificar
                try:
                    xml_str = self.xml_content.decode('utf-8')
                except UnicodeDecodeError:
                    # Fallback para ISO-8859-1 (Latin-1)
                    xml_str = self.xml_content.decode('iso-8859-1')
                self.xml_content = xml_str

            self.root = ET.fromstring(self.xml_content)
        except ET.ParseError as e:
            logger.error(f"❌ Erro ao fazer parsing do XML: {e}")
            self.root = None

    def _find_tag(self, tag_name: str, root=None) -> Optional[ET.Element]:
        """
        Busca uma tag no XML, ignorando namespace completamente

        Args:
            tag_name: Nome da tag a buscar (ex: 'tpCTe', 'infCteComp')
            root: Elemento raiz para busca (se None, usa self.root)

        Returns:
            Elemento encontrado ou None
        """
        if root is None:
            root = self.root

        if root is None:
            return None

        # Buscar ignorando namespace - método robusto
        # Itera por todos os elementos e compara apenas o nome local da tag
        for element in root.iter():
            # Extrai o nome da tag sem namespace
            # Ex: {http://www.portalfiscal.inf.br/cte}tpCTe -> tpCTe
            local_name = element.tag.split('}')[-1] if '}' in element.tag else element.tag

            if local_name == tag_name:
                return element

        return None

    def _get_tag_text(self, tag_name: str, default: str = None) -> Optional[str]:
        """
        Obtém o texto de uma tag

        Args:
            tag_name: Nome da tag
            default: Valor padrão se não encontrar

        Returns:
            Texto da tag ou default (com correções de formatação e sem acentos)
        """
        element = self._find_tag(tag_name)
        if element is not None and element.text:
            text = element.text.strip()

            # Corrigir \delimiter para vírgula
            text = text.replace('\\delimiter', ',')

            # Remover acentos para evitar problemas de encoding
            # NFD = Forma de Decomposição Canônica (separa caracteres base de acentos)
            # Depois remove apenas os caracteres de marca (acentos)
            text = unicodedata.normalize('NFD', text)
            text = ''.join(char for char in text if unicodedata.category(char) != 'Mn')

            return text
        return default

    def get_tipo_cte(self) -> str:
        """
        Extrai o tipo do CTe

        Returns:
            '0' = Normal
            '1' = Complementar
            '2' = Anulação
            '3' = Substituto
        """
        tipo = self._get_tag_text('tpCTe', default='0')
        return tipo

    def get_info_complementar(self) -> Optional[Dict]:
        """
        Extrai informações de CTe complementar se houver

        Returns:
            Dict com:
                - chave_cte_original: Chave do CTe que está sendo complementado
                - motivo: Motivo do complemento (extraído de xObs)
            ou None se não for complementar
        """
        tipo = self.get_tipo_cte()

        if tipo != '1':  # Não é complementar
            return None

        # Buscar tag infCteComp
        info_comp = self._find_tag('infCteComp')

        if info_comp is None:
            logger.warning("⚠️ CTe marcado como complementar mas sem tag <infCteComp>")
            return None

        # Extrair chave do CTe original
        chave_element = self._find_tag('chCTe', root=info_comp)
        chave_original = chave_element.text.strip() if chave_element is not None and chave_element.text else None

        if not chave_original:
            logger.warning("⚠️ Tag <infCteComp> encontrada mas sem <chCTe>")
            return None

        # Tentar extrair motivo (priorizar xCaracAd sobre xObs)
        # xCaracAd geralmente contém o motivo real do complemento (ex: "Compl. Frete")
        # xObs geralmente contém informações genéricas (impostos, seguros, etc)
        motivo = self._get_tag_text('xCaracAd')

        if not motivo:
            # Fallback: usar xObs apenas se xCaracAd estiver vazio
            motivo = self._get_tag_text('xObs')

        resultado = {
            'chave_cte_original': chave_original,
            'motivo': motivo
        }

        logger.info(f"✅ CTe Complementar detectado: {chave_original}")
        if motivo:
            logger.info(f"   Motivo: {motivo}")

        return resultado

    def extrair_numero_de_chave(self, chave: str) -> Optional[str]:
        """
        Extrai o número do CTe a partir da chave de acesso

        Estrutura da chave CTe (44 dígitos):
        - Posições 26-33: Número do documento (8 dígitos)

        Args:
            chave: Chave de acesso de 44 dígitos

        Returns:
            Número do CTe ou None
        """
        if not chave or len(chave) != 44:
            return None

        try:
            numero = chave[25:33]  # Posições 26-33 (índice 25-32)
            return numero.lstrip('0')  # Remove zeros à esquerda
        except Exception as e:
            logger.error(f"❌ Erro ao extrair número da chave {chave}: {e}")
            return None

    def get_todas_informacoes(self) -> Dict:
        """
        Extrai todas as informações relevantes do XML

        Returns:
            Dict com todas as informações extraídas
        """
        resultado = {
            'tipo_cte': self.get_tipo_cte(),
            'tipo_cte_descricao': self.get_tipo_cte_descricao(),
            'info_complementar': self.get_info_complementar(),
        }

        return resultado

    def get_tipo_cte_descricao(self) -> str:
        """Retorna descrição do tipo de CTe"""
        tipos = {
            '0': 'Normal',
            '1': 'Complementar',
            '2': 'Anulação',
            '3': 'Substituto'
        }
        return tipos.get(self.get_tipo_cte(), 'Normal')

    def get_ibscbs(self) -> Optional[Dict]:
        """
        Extrai informações de IBS/CBS do XML (Reforma Tributária 2026)

        Estrutura esperada no XML:
        <IBSCBS>
            <CST>200</CST>
            <cClassTrib>200034</cClassTrib>
            <gIBSCBS>
                <vBC>427.34</vBC>
                <gIBSUF>
                    <pIBSUF>0.10</pIBSUF>
                    <gRed>
                        <pRedAliq>60.00</pRedAliq>
                        <pAliqEfet>0.04</pAliqEfet>
                    </gRed>
                    <vIBSUF>0.17</vIBSUF>
                </gIBSUF>
                <gIBSMun>
                    <pIBSMun>0.00</pIBSMun>
                    <gRed>
                        <pRedAliq>60.00</pRedAliq>
                        <pAliqEfet>0.00</pAliqEfet>
                    </gRed>
                    <vIBSMun>0.00</vIBSMun>
                </gIBSMun>
                <vIBS>0.17</vIBS>
                <gCBS>
                    <pCBS>0.90</pCBS>
                    <gRed>
                        <pRedAliq>60.00</pRedAliq>
                        <pAliqEfet>0.36</pAliqEfet>
                    </gRed>
                    <vCBS>1.54</vCBS>
                </gCBS>
            </gIBSCBS>
        </IBSCBS>

        Returns:
            Dict com dados IBS/CBS ou None se não encontrar
        """
        if self.root is None:
            return None

        # Buscar tag IBSCBS
        ibscbs_element = self._find_tag('IBSCBS')

        if ibscbs_element is None:
            logger.debug("Tag <IBSCBS> não encontrada no XML")
            return None

        resultado = {
            'encontrado': True,
            'cst': None,
            'class_trib': None,
            'base_calculo': None,
            # IBS UF
            'ibs_uf_aliquota': None,
            'ibs_uf_reducao': None,
            'ibs_uf_aliq_efetiva': None,
            'ibs_uf_valor': None,
            # IBS Municipio
            'ibs_mun_aliquota': None,
            'ibs_mun_reducao': None,
            'ibs_mun_aliq_efetiva': None,
            'ibs_mun_valor': None,
            # IBS Total
            'ibs_total': None,
            # CBS
            'cbs_aliquota': None,
            'cbs_reducao': None,
            'cbs_aliq_efetiva': None,
            'cbs_valor': None
        }

        # Extrair CST
        cst_element = self._find_tag('CST', root=ibscbs_element)
        if cst_element is not None and cst_element.text:
            resultado['cst'] = cst_element.text.strip()

        # Extrair Classificação Tributária
        class_trib_element = self._find_tag('cClassTrib', root=ibscbs_element)
        if class_trib_element is not None and class_trib_element.text:
            resultado['class_trib'] = class_trib_element.text.strip()

        # Buscar grupo gIBSCBS
        gibscbs = self._find_tag('gIBSCBS', root=ibscbs_element)
        if gibscbs is None:
            # Tenta buscar diretamente os valores
            gibscbs = ibscbs_element

        # Base de Cálculo
        vbc = self._find_tag('vBC', root=gibscbs)
        if vbc is not None and vbc.text:
            resultado['base_calculo'] = self._to_decimal(vbc.text.strip())

        # IBS UF
        gibsuf = self._find_tag('gIBSUF', root=gibscbs)
        if gibsuf is not None:
            pibsuf = self._find_tag('pIBSUF', root=gibsuf)
            if pibsuf is not None and pibsuf.text:
                resultado['ibs_uf_aliquota'] = self._to_decimal(pibsuf.text.strip())

            # Redução dentro de gIBSUF
            gred_uf = self._find_tag('gRed', root=gibsuf)
            if gred_uf is not None:
                pred = self._find_tag('pRedAliq', root=gred_uf)
                if pred is not None and pred.text:
                    resultado['ibs_uf_reducao'] = self._to_decimal(pred.text.strip())
                paliqefet = self._find_tag('pAliqEfet', root=gred_uf)
                if paliqefet is not None and paliqefet.text:
                    resultado['ibs_uf_aliq_efetiva'] = self._to_decimal(paliqefet.text.strip())

            vibsuf = self._find_tag('vIBSUF', root=gibsuf)
            if vibsuf is not None and vibsuf.text:
                resultado['ibs_uf_valor'] = self._to_decimal(vibsuf.text.strip())

        # IBS Município
        gibsmun = self._find_tag('gIBSMun', root=gibscbs)
        if gibsmun is not None:
            pibsmun = self._find_tag('pIBSMun', root=gibsmun)
            if pibsmun is not None and pibsmun.text:
                resultado['ibs_mun_aliquota'] = self._to_decimal(pibsmun.text.strip())

            # Redução dentro de gIBSMun
            gred_mun = self._find_tag('gRed', root=gibsmun)
            if gred_mun is not None:
                pred = self._find_tag('pRedAliq', root=gred_mun)
                if pred is not None and pred.text:
                    resultado['ibs_mun_reducao'] = self._to_decimal(pred.text.strip())
                paliqefet = self._find_tag('pAliqEfet', root=gred_mun)
                if paliqefet is not None and paliqefet.text:
                    resultado['ibs_mun_aliq_efetiva'] = self._to_decimal(paliqefet.text.strip())

            vibsmun = self._find_tag('vIBSMun', root=gibsmun)
            if vibsmun is not None and vibsmun.text:
                resultado['ibs_mun_valor'] = self._to_decimal(vibsmun.text.strip())

        # IBS Total
        vibs = self._find_tag('vIBS', root=gibscbs)
        if vibs is not None and vibs.text:
            resultado['ibs_total'] = self._to_decimal(vibs.text.strip())

        # CBS
        gcbs = self._find_tag('gCBS', root=gibscbs)
        if gcbs is not None:
            pcbs = self._find_tag('pCBS', root=gcbs)
            if pcbs is not None and pcbs.text:
                resultado['cbs_aliquota'] = self._to_decimal(pcbs.text.strip())

            # Redução dentro de gCBS
            gred_cbs = self._find_tag('gRed', root=gcbs)
            if gred_cbs is not None:
                pred = self._find_tag('pRedAliq', root=gred_cbs)
                if pred is not None and pred.text:
                    resultado['cbs_reducao'] = self._to_decimal(pred.text.strip())
                paliqefet = self._find_tag('pAliqEfet', root=gred_cbs)
                if paliqefet is not None and paliqefet.text:
                    resultado['cbs_aliq_efetiva'] = self._to_decimal(paliqefet.text.strip())

            vcbs = self._find_tag('vCBS', root=gcbs)
            if vcbs is not None and vcbs.text:
                resultado['cbs_valor'] = self._to_decimal(vcbs.text.strip())

        logger.info(f"✅ IBS/CBS extraído do XML: CST={resultado['cst']}, vIBS={resultado['ibs_total']}, vCBS={resultado['cbs_valor']}")

        return resultado

    def _to_decimal(self, valor: str) -> Optional[float]:
        """Converte string para float/decimal"""
        if not valor:
            return None
        try:
            return float(valor.replace(',', '.'))
        except (ValueError, TypeError):
            return None

    def tem_ibscbs(self) -> bool:
        """
        Verifica se o XML contém a tag IBSCBS

        Returns:
            True se a tag IBSCBS existir
        """
        if self.root is None:
            return False

        ibscbs_element = self._find_tag('IBSCBS')
        return ibscbs_element is not None

    def ibscbs_tem_valores(self) -> bool:
        """
        Verifica se o XML tem IBSCBS com valores > 0

        Returns:
            True se IBSCBS existir e tiver valores
        """
        dados = self.get_ibscbs()
        if not dados:
            return False

        # Verificar se tem algum valor > 0
        valores = [
            dados.get('ibs_uf_valor'),
            dados.get('ibs_mun_valor'),
            dados.get('ibs_total'),
            dados.get('cbs_valor')
        ]

        for v in valores:
            if v and v > 0:
                return True

        return False


def parsear_cte_xml(xml_content: str) -> Dict:
    """
    Função helper para parsear XML de CTe

    Args:
        xml_content: Conteúdo XML como string

    Returns:
        Dict com informações extraídas
    """
    parser = CTeXMLParser(xml_content)
    return parser.get_todas_informacoes()


def extrair_info_complementar(xml_content: str) -> Optional[Dict]:
    """
    Função helper para extrair apenas info de CTe complementar

    Args:
        xml_content: Conteúdo XML como string

    Returns:
        Dict com info complementar ou None
    """
    parser = CTeXMLParser(xml_content)
    return parser.get_info_complementar()


def extrair_ibscbs(xml_content: str) -> Optional[Dict]:
    """
    Função helper para extrair dados de IBS/CBS do XML

    Args:
        xml_content: Conteúdo XML como string

    Returns:
        Dict com dados IBS/CBS ou None
    """
    parser = CTeXMLParser(xml_content)
    return parser.get_ibscbs()
