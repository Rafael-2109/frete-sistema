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
