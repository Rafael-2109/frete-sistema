"""
Utilitário para Parsing de XML de NFD (Nota Fiscal de Devolução)
================================================================

OBJETIVO:
    Extrair informações específicas de NFDs a partir do XML,
    incluindo NFs de venda referenciadas (tag <refNFe>)

ESTRUTURA DA NFD (SEFAZ):
    <nfeProc>
        <NFe>
            <infNFe>
                <ide>
                    <finnfe>4</finnfe>  <!-- Finalidade = Devolução -->
                    <NFref>
                        <refNFe>CHAVE_44_DIGITOS</refNFe>  <!-- NF de venda referenciada -->
                    </NFref>
                </ide>
                <emit>...</emit>  <!-- Emitente (cliente que devolveu) -->
                <dest>...</dest>  <!-- Destinatário (nós - Nacom) -->
                <det>...</det>    <!-- Itens da NFD -->
            </infNFe>
        </NFe>
    </nfeProc>

AUTOR: Sistema de Fretes - Módulo Devoluções
DATA: 30/12/2024
"""

import logging
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional
import unicodedata

logger = logging.getLogger(__name__)


class NFDXMLParser:
    """Parser para extrair informações de XMLs de NFD"""

    # Namespaces comuns em XMLs de NF-e/NFD
    NAMESPACES = {
        'nfe': 'http://www.portalfiscal.inf.br/nfe'
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
            tag_name: Nome da tag a buscar (ex: 'refNFe', 'emit')
            root: Elemento raiz para busca (se None, usa self.root)

        Returns:
            Elemento encontrado ou None
        """
        if root is None:
            root = self.root

        if root is None:
            return None

        # Buscar ignorando namespace - método robusto
        for element in root.iter():
            local_name = element.tag.split('}')[-1] if '}' in element.tag else element.tag
            if local_name == tag_name:
                return element

        return None

    def _find_all_tags(self, tag_name: str, root=None) -> List[ET.Element]:
        """
        Busca todas as tags com o nome especificado

        Args:
            tag_name: Nome da tag
            root: Elemento raiz para busca

        Returns:
            Lista de elementos encontrados
        """
        if root is None:
            root = self.root

        if root is None:
            return []

        encontrados = []
        for element in root.iter():
            local_name = element.tag.split('}')[-1] if '}' in element.tag else element.tag
            if local_name == tag_name:
                encontrados.append(element)

        return encontrados

    def _get_tag_text(self, tag_name: str, default: str = None, root=None) -> Optional[str]:
        """
        Obtém o texto de uma tag

        Args:
            tag_name: Nome da tag
            default: Valor padrão se não encontrar
            root: Elemento raiz para busca

        Returns:
            Texto da tag ou default
        """
        element = self._find_tag(tag_name, root=root)
        if element is not None and element.text:
            text = element.text.strip()
            return text
        return default

    def _limpar_texto(self, texto: str) -> str:
        """
        Limpa texto removendo acentos e caracteres especiais

        Args:
            texto: Texto a limpar

        Returns:
            Texto limpo
        """
        if not texto:
            return texto

        # Remover acentos
        texto = unicodedata.normalize('NFD', texto)
        texto = ''.join(char for char in texto if unicodedata.category(char) != 'Mn')

        return texto.strip()

    def get_finalidade(self) -> str:
        """
        Extrai a finalidade da NF-e

        Returns:
            '1' = Normal
            '2' = Complementar
            '3' = Ajuste
            '4' = Devolução de mercadoria
        """
        finalidade = self._get_tag_text('finNFe', default='1')
        return finalidade #type: ignore

    def is_devolucao(self) -> bool:
        """Verifica se a NF é de devolução (finalidade = 4)"""
        return self.get_finalidade() == '4'

    def get_data_emissao(self):
        """
        Extrai data de emissão (dhEmi) do XML

        Formato esperado: 2025-10-22T16:49:56-04:00

        Returns:
            Datetime da emissão ou None
        """
        from datetime import datetime

        dhEmi = self._get_tag_text('dhEmi')
        if dhEmi:
            try:
                # Remove timezone offset para parsing
                # Ex: 2025-10-22T16:49:56-04:00 -> 2025-10-22T16:49:56
                dhEmi_limpo = dhEmi
                if '+' in dhEmi:
                    dhEmi_limpo = dhEmi.split('+')[0]
                elif dhEmi.count('-') > 2:
                    # Formato com offset negativo: 2025-10-22T16:49:56-04:00
                    partes = dhEmi.rsplit('-', 1)
                    if ':' in partes[-1]:  # É timezone, não parte da data
                        dhEmi_limpo = partes[0]

                return datetime.fromisoformat(dhEmi_limpo)
            except Exception as e:
                logger.warning(f"⚠️ Erro ao parsear dhEmi '{dhEmi}': {e}")
                return None
        return None

    def get_nfs_referenciadas(self) -> List[Dict]:
        """
        Extrai todas as NFs de venda referenciadas na NFD

        A NFD pode referenciar múltiplas NFs através da tag <NFref>
        dentro de <ide>

        Returns:
            Lista de dicts com:
                - chave: Chave de 44 dígitos da NF referenciada
                - numero: Número extraído da chave
                - serie: Série extraída da chave
        """
        referencias = []

        # Buscar todas as tags <refNFe> (chaves de NF referenciadas)
        ref_elements = self._find_all_tags('refNFe')

        for ref_element in ref_elements:
            chave = ref_element.text.strip() if ref_element.text else None

            if chave and len(chave) == 44:
                # Extrair número e série da chave
                # Estrutura da chave NF-e:
                # Posições 0-1: UF (2)
                # Posições 2-5: AAMM (4)
                # Posições 6-19: CNPJ (14)
                # Posições 20-21: Modelo (2) - 55=NF-e
                # Posições 22-24: Série (3)
                # Posições 25-33: Número (9)
                # Posições 34-34: tpEmis (1)
                # Posições 35-42: Código numérico (8)
                # Posição 43: Dígito verificador (1)

                try:
                    serie = str(int(chave[22:25]))  # Remove zeros à esquerda
                    numero = str(int(chave[25:34]))  # Remove zeros à esquerda

                    referencias.append({
                        'chave': chave,
                        'numero': numero,
                        'serie': serie
                    })

                    logger.info(f"   📄 NF referenciada encontrada: {numero} série {serie}")

                except (ValueError, IndexError) as e:
                    logger.warning(f"   ⚠️ Erro ao extrair número/série da chave {chave}: {e}")
                    # Ainda adiciona com chave apenas
                    referencias.append({
                        'chave': chave,
                        'numero': None,
                        'serie': None
                    })

        logger.info(f"   📊 Total de NFs referenciadas: {len(referencias)}")
        return referencias

    def get_dados_emitente(self) -> Dict:
        """
        Extrai dados do emitente (cliente que emitiu a NFD)

        Returns:
            Dict com CNPJ, nome, IE, etc.
        """
        emit = self._find_tag('emit')

        if emit is None:
            return {}

        return {
            'cnpj': self._get_tag_text('CNPJ', root=emit),
            'cpf': self._get_tag_text('CPF', root=emit),
            'nome': self._limpar_texto(self._get_tag_text('xNome', root=emit)),
            'nome_fantasia': self._limpar_texto(self._get_tag_text('xFant', root=emit)),
            'ie': self._get_tag_text('IE', root=emit),
            'uf': self._get_tag_text('UF', root=emit),
            'municipio': self._limpar_texto(self._get_tag_text('xMun', root=emit)),
        }

    def get_dados_destinatario(self) -> Dict:
        """
        Extrai dados do destinatário (nós - Nacom)

        Returns:
            Dict com CNPJ, nome, etc.
        """
        dest = self._find_tag('dest')

        if dest is None:
            return {}

        return {
            'cnpj': self._get_tag_text('CNPJ', root=dest),
            'cpf': self._get_tag_text('CPF', root=dest),
            'nome': self._limpar_texto(self._get_tag_text('xNome', root=dest)),
            'ie': self._get_tag_text('IE', root=dest),
            'uf': self._get_tag_text('UF', root=dest),
            'municipio': self._limpar_texto(self._get_tag_text('xMun', root=dest)),
        }

    def get_itens(self) -> List[Dict]:
        """
        Extrai todos os itens (linhas de produto) da NFD

        Returns:
            Lista de dicts com dados de cada item
        """
        itens = []

        # Buscar todas as tags <det> (detalhes/itens)
        det_elements = self._find_all_tags('det')

        for det in det_elements:
            # Número do item (atributo nItem)
            numero_item = det.get('nItem')

            # Buscar tag <prod> dentro do <det>
            prod = self._find_tag('prod', root=det)

            if prod is None:
                continue

            item = {
                'numero_item': int(numero_item) if numero_item else None,
                'codigo_produto': self._get_tag_text('cProd', root=prod),
                'ean': self._get_tag_text('cEAN', root=prod),
                'descricao': self._limpar_texto(self._get_tag_text('xProd', root=prod)),
                'ncm': self._get_tag_text('NCM', root=prod),
                'cfop': self._get_tag_text('CFOP', root=prod),
                'unidade_medida': self._get_tag_text('uCom', root=prod),
                'quantidade': self._parse_decimal(self._get_tag_text('qCom', root=prod)),
                'valor_unitario': self._parse_decimal(self._get_tag_text('vUnCom', root=prod)),
                'valor_total': self._parse_decimal(self._get_tag_text('vProd', root=prod)),
                'peso_bruto': self._parse_decimal(self._get_tag_text('pesoB', root=prod)),
                'peso_liquido': self._parse_decimal(self._get_tag_text('pesoL', root=prod)),
            }

            itens.append(item)

        logger.info(f"   📦 Total de itens extraídos: {len(itens)}")
        return itens

    def get_info_complementar(self) -> Optional[str]:
        """
        Extrai informações complementares da NFD (tag infCpl)

        Este campo contém texto livre do cliente que pode incluir:
        - Referência à NF de venda original
        - Motivo da devolução
        - Observações gerais

        Returns:
            String com informações complementares ou None
        """
        # A tag infCpl fica dentro de infAdic
        inf_adic = self._find_tag('infAdic')
        if inf_adic is None:
            # Tentar buscar diretamente
            info = self._get_tag_text('infCpl')
            return self._limpar_texto(info) if info else None

        info = self._get_tag_text('infCpl', root=inf_adic)
        return self._limpar_texto(info) if info else None

    def get_totais(self) -> Dict:
        """
        Extrai valores totais da NFD

        Returns:
            Dict com valores totais
        """
        total = self._find_tag('total')

        if total is None:
            return {}

        icms_tot = self._find_tag('ICMSTot', root=total)

        if icms_tot is None:
            return {}

        return {
            'valor_produtos': self._parse_decimal(self._get_tag_text('vProd', root=icms_tot)),
            'valor_frete': self._parse_decimal(self._get_tag_text('vFrete', root=icms_tot)),
            'valor_seguro': self._parse_decimal(self._get_tag_text('vSeg', root=icms_tot)),
            'valor_desconto': self._parse_decimal(self._get_tag_text('vDesc', root=icms_tot)),
            'valor_icms': self._parse_decimal(self._get_tag_text('vICMS', root=icms_tot)),
            'valor_ipi': self._parse_decimal(self._get_tag_text('vIPI', root=icms_tot)),
            'valor_pis': self._parse_decimal(self._get_tag_text('vPIS', root=icms_tot)),
            'valor_cofins': self._parse_decimal(self._get_tag_text('vCOFINS', root=icms_tot)),
            'valor_total': self._parse_decimal(self._get_tag_text('vNF', root=icms_tot)),
        }

    def get_todas_informacoes(self) -> Dict:
        """
        Extrai todas as informações relevantes do XML

        Returns:
            Dict com todas as informações
        """
        return {
            'finalidade': self.get_finalidade(),
            'is_devolucao': self.is_devolucao(),
            'emitente': self.get_dados_emitente(),
            'destinatario': self.get_dados_destinatario(),
            'nfs_referenciadas': self.get_nfs_referenciadas(),
            'itens': self.get_itens(),
            'totais': self.get_totais(),
        }

    @staticmethod
    def _parse_decimal(valor: str) -> Optional[float]:
        """Converte string para decimal"""
        if not valor:
            return None
        try:
            return float(valor.replace(',', '.'))
        except (ValueError, AttributeError):
            return None


def extrair_nfs_referenciadas(xml_content: str) -> List[Dict]:
    """
    Função helper para extrair NFs referenciadas de um XML de NFD

    Args:
        xml_content: Conteúdo XML como string

    Returns:
        Lista de dicts com dados das NFs referenciadas
    """
    parser = NFDXMLParser(xml_content)
    return parser.get_nfs_referenciadas()


def extrair_itens_nfd(xml_content: str) -> List[Dict]:
    """
    Função helper para extrair itens de um XML de NFD

    Args:
        xml_content: Conteúdo XML como string

    Returns:
        Lista de dicts com dados dos itens
    """
    parser = NFDXMLParser(xml_content)
    return parser.get_itens()


def parsear_nfd_completo(xml_content: str) -> Dict:
    """
    Função helper para extrair todas as informações de um XML de NFD

    Args:
        xml_content: Conteúdo XML como string

    Returns:
        Dict com todas as informações
    """
    parser = NFDXMLParser(xml_content)
    return parser.get_todas_informacoes()
