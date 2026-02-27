"""
Parser de NF-e XML para o modulo CarVia
========================================

Extrai dados de NF-e (Nota Fiscal Eletronica) a partir do XML.
Baseado no padrao de app/devolucao/services/nfd_xml_parser.py (namespace-agnostic).

Estrutura NF-e XML:
    <nfeProc>
        <NFe>
            <infNFe>
                <ide> (nNF, serie, dhEmi)
                <emit> (CNPJ, xNome, UF, xMun)
                <dest> (CNPJ, xNome, UF, xMun)
                <total>
                    <ICMSTot> (vNF, vProd)
                <transp>
                    <vol> (pesoB, pesoL, qVol)
            </infNFe>
        </NFe>
    </nfeProc>
"""

import logging
import re
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class NFeXMLParser:
    """Parser para extrair informacoes de XMLs de NF-e"""

    def __init__(self, xml_content):
        """
        Args:
            xml_content: String ou bytes contendo o XML completo
        """
        self.xml_content = xml_content
        self.root = None
        self._parse()

    def _parse(self):
        """Parsing do XML com tratamento de encoding"""
        try:
            if isinstance(self.xml_content, bytes):
                try:
                    xml_str = self.xml_content.decode('utf-8')
                except UnicodeDecodeError:
                    xml_str = self.xml_content.decode('iso-8859-1')
                self.xml_content = xml_str

            self.root = ET.fromstring(self.xml_content)
        except ET.ParseError as e:
            logger.error(f"Erro ao parsear XML NF-e: {e}")
            self.root = None

    def _find_tag(self, tag_name: str, root=None) -> Optional[ET.Element]:
        """Busca tag ignorando namespace (namespace-agnostic)"""
        if root is None:
            root = self.root
        if root is None:
            return None

        for element in root.iter():
            local_name = element.tag.split('}')[-1] if '}' in element.tag else element.tag
            if local_name == tag_name:
                return element
        return None

    def _find_all_tags(self, tag_name: str, root=None) -> List[ET.Element]:
        """Busca todas as tags com o nome especificado"""
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

    def _get_tag_text(self, tag_name: str, root=None, default=None) -> Optional[str]:
        """Obtem texto de uma tag"""
        element = self._find_tag(tag_name, root=root)
        if element is not None and element.text:
            return element.text.strip()
        return default

    def _to_float(self, value: str) -> Optional[float]:
        """Converte string para float"""
        if not value:
            return None
        try:
            return float(value.replace(',', '.'))
        except (ValueError, TypeError):
            return None

    def _sanitize_cnpj(self, cnpj: str) -> str:
        """Remove formatacao do CNPJ, mantendo apenas digitos"""
        if not cnpj:
            return ''
        return re.sub(r'\D', '', cnpj)

    def is_valid(self) -> bool:
        """Verifica se o XML foi parseado com sucesso"""
        return self.root is not None

    def is_nfe(self) -> bool:
        """Verifica se o XML e uma NF-e (modelo 55)"""
        if not self.is_valid():
            return False
        modelo = self._get_tag_text('mod')
        return modelo == '55'

    def get_chave_acesso(self) -> Optional[str]:
        """Extrai chave de acesso (44 digitos) do XML"""
        # Tentar tag <chNFe> dentro de <protNFe>
        chave = self._get_tag_text('chNFe')
        if chave and len(chave) == 44:
            return chave

        # Fallback: atributo Id de <infNFe>
        inf_nfe = self._find_tag('infNFe')
        if inf_nfe is not None:
            inf_id = inf_nfe.get('Id', '')
            # Formato: NFe + 44 digitos
            digits = re.sub(r'\D', '', inf_id)
            if len(digits) == 44:
                return digits

        return None

    def get_ide(self) -> Dict:
        """Extrai dados de identificacao (ide)"""
        ide = self._find_tag('ide')
        return {
            'numero_nf': self._get_tag_text('nNF', root=ide),
            'serie_nf': self._get_tag_text('serie', root=ide),
            'data_emissao': self._parse_datetime(self._get_tag_text('dhEmi', root=ide)),
            'tipo_operacao': self._get_tag_text('tpNF', root=ide),  # 0=entrada, 1=saida
            'finalidade': self._get_tag_text('finNFe', root=ide),
        }

    def get_emitente(self) -> Dict:
        """Extrai dados do emitente (emit)"""
        emit = self._find_tag('emit')
        if emit is None:
            return {}

        ender = self._find_tag('enderEmit', root=emit)
        return {
            'cnpj': self._sanitize_cnpj(self._get_tag_text('CNPJ', root=emit) or ''),
            'nome': self._get_tag_text('xNome', root=emit),
            'uf': self._get_tag_text('UF', root=ender) if ender else None,
            'cidade': self._get_tag_text('xMun', root=ender) if ender else None,
        }

    def get_destinatario(self) -> Dict:
        """Extrai dados do destinatario (dest)"""
        dest = self._find_tag('dest')
        if dest is None:
            return {}

        ender = self._find_tag('enderDest', root=dest)
        return {
            'cnpj': self._sanitize_cnpj(self._get_tag_text('CNPJ', root=dest) or ''),
            'nome': self._get_tag_text('xNome', root=dest),
            'uf': self._get_tag_text('UF', root=ender) if ender else None,
            'cidade': self._get_tag_text('xMun', root=ender) if ender else None,
        }

    def get_totais(self) -> Dict:
        """Extrai totais da NF-e (ICMSTot)"""
        icms_tot = self._find_tag('ICMSTot')
        if icms_tot is None:
            return {}

        return {
            'valor_total': self._to_float(self._get_tag_text('vNF', root=icms_tot)),
            'valor_produtos': self._to_float(self._get_tag_text('vProd', root=icms_tot)),
            'valor_frete': self._to_float(self._get_tag_text('vFrete', root=icms_tot)),
        }

    def get_transporte(self) -> Dict:
        """Extrai dados de transporte (transp/vol)"""
        vol = self._find_tag('vol')
        if vol is None:
            return {}

        return {
            'peso_bruto': self._to_float(self._get_tag_text('pesoB', root=vol)),
            'peso_liquido': self._to_float(self._get_tag_text('pesoL', root=vol)),
            'quantidade_volumes': self._to_int(self._get_tag_text('qVol', root=vol)),
        }

    def get_itens(self) -> List[Dict]:
        """Extrai itens de produto (<det><prod>)

        Estrutura XML:
            <det nItem="1">
                <prod>
                    <cProd>JET MOTO CHEFE</cProd>
                    <xProd>JET MOTO CHEFE</xProd>
                    <NCM>87116000</NCM>
                    <CFOP>5405</CFOP>
                    <uCom>UN</uCom>
                    <qCom>3.0000</qCom>
                    <vUnCom>7220.0000</vUnCom>
                    <vProd>21660.00</vProd>
                </prod>
            </det>
        """
        itens = []
        dets = self._find_all_tags('det')
        for det in dets:
            prod = self._find_tag('prod', root=det)
            if prod is None:
                continue

            itens.append({
                'codigo_produto': self._get_tag_text('cProd', root=prod),
                'descricao': self._get_tag_text('xProd', root=prod),
                'ncm': self._get_tag_text('NCM', root=prod),
                'cfop': self._get_tag_text('CFOP', root=prod),
                'unidade': self._get_tag_text('uCom', root=prod),
                'quantidade': self._to_float(self._get_tag_text('qCom', root=prod)),
                'valor_unitario': self._to_float(self._get_tag_text('vUnCom', root=prod)),
                'valor_total_item': self._to_float(self._get_tag_text('vProd', root=prod)),
            })
        return itens

    def get_todas_informacoes(self) -> Dict:
        """Extrai todas as informacoes relevantes em um unico dict"""
        ide = self.get_ide()
        emit = self.get_emitente()
        dest = self.get_destinatario()
        totais = self.get_totais()
        transp = self.get_transporte()

        return {
            'chave_acesso_nf': self.get_chave_acesso(),
            'numero_nf': ide.get('numero_nf'),
            'serie_nf': ide.get('serie_nf'),
            'data_emissao': ide.get('data_emissao'),
            'cnpj_emitente': emit.get('cnpj'),
            'nome_emitente': emit.get('nome'),
            'uf_emitente': emit.get('uf'),
            'cidade_emitente': emit.get('cidade'),
            'cnpj_destinatario': dest.get('cnpj'),
            'nome_destinatario': dest.get('nome'),
            'uf_destinatario': dest.get('uf'),
            'cidade_destinatario': dest.get('cidade'),
            'valor_total': totais.get('valor_total'),
            'peso_bruto': transp.get('peso_bruto'),
            'peso_liquido': transp.get('peso_liquido'),
            'quantidade_volumes': transp.get('quantidade_volumes'),
            'itens': self.get_itens(),
            'tipo_fonte': 'XML_NFE',
        }

    def _parse_datetime(self, dt_str: Optional[str]) -> Optional[datetime]:
        """Converte string datetime do XML para datetime"""
        if not dt_str:
            return None
        try:
            # Remove timezone offset: 2025-10-22T16:49:56-04:00
            clean = dt_str
            if '+' in clean:
                clean = clean.split('+')[0]
            elif clean.count('-') > 2:
                parts = clean.rsplit('-', 1)
                if ':' in parts[-1]:
                    clean = parts[0]
            return datetime.fromisoformat(clean)
        except (ValueError, TypeError) as e:
            logger.warning(f"Erro ao parsear datetime '{dt_str}': {e}")
            return None

    def _to_int(self, value: Optional[str]) -> Optional[int]:
        """Converte string para int"""
        if not value:
            return None
        try:
            return int(float(value))
        except (ValueError, TypeError):
            return None


def parsear_nfe_xml(xml_content) -> Dict:
    """Funcao helper para parsear XML de NF-e"""
    parser = NFeXMLParser(xml_content)
    return parser.get_todas_informacoes()
