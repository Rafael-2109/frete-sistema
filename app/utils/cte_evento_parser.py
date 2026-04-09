"""
Parser generico de XML de CTe — CTe original e Evento de Cancelamento
======================================================================

Suporta dois formatos:

1. **procEventoCTe** (Evento SEFAZ 110111 — Cancelamento):
   - Namespace: http://www.portalfiscal.inf.br/cte
   - Estrutura: procEventoCTe > eventoCTe > infEvento
   - Extrai: chave, tpEvento, protocolo (nProt), dhEvento, xJust
   - Considera cancelado apenas se tpEvento=='110111' AND retEventoCTe.cStat=='135' (homologado)

2. **cteProc** (CTe original completo):
   - Namespace: http://www.portalfiscal.inf.br/cte
   - Estrutura: cteProc > CTe > infCte + protCTe
   - Extrai: chave, numero, serie, emitente, valor, data_emissao

Uso basico:
-----------
    from app.utils.cte_evento_parser import CteEventoParser

    parser = CteEventoParser()
    tipo = parser.detectar_tipo(xml_bytes)  # 'procEventoCTe' | 'cteProc' | 'invalido'

    if tipo == 'procEventoCTe':
        info = parser.parse_evento(xml_bytes)
        # info = {'tipo': 'procEventoCTe', 'chave': '...', 'cancelamento': True/False,
        #         'tp_evento': '110111', 'protocolo': '...', 'data_evento': '...',
        #         'justificativa': '...', 'cstat': '135'}
    elif tipo == 'cteProc':
        info = parser.parse_cte(xml_bytes)

Referencia: Layout oficial SEFAZ MOC CT-e v3.00
Data: 2026-04-09
"""

import logging
import xml.etree.ElementTree as ET
from typing import Dict, Literal, Optional, Union

logger = logging.getLogger(__name__)

TipoXml = Literal['procEventoCTe', 'cteProc', 'invalido']

# Codigo SEFAZ do evento de cancelamento de CTe
TP_EVENTO_CANCELAMENTO = '110111'

# cStat 135 = "Evento registrado e vinculado ao CTe" (homologado)
CSTAT_EVENTO_HOMOLOGADO = '135'

NAMESPACE_CTE = 'http://www.portalfiscal.inf.br/cte'


class CteEventoParser:
    """
    Parser resiliente de XMLs de CTe.

    - Ignora namespace ao fazer buscas (match pelo nome local da tag).
    - Suporta bytes ou str como entrada.
    - Tenta UTF-8 primeiro, depois ISO-8859-1 como fallback.
    - Nao levanta excecao em casos normais: retorna None/invalido.
    """

    def _parse_xml(self, xml_input: Union[bytes, str]) -> Optional[ET.Element]:
        """
        Parse XML em um elemento root. Resiliente a encoding.

        Returns:
            Element root ou None se falhou.
        """
        try:
            if isinstance(xml_input, bytes):
                try:
                    xml_str = xml_input.decode('utf-8')
                except UnicodeDecodeError:
                    xml_str = xml_input.decode('iso-8859-1', errors='replace')
            else:
                xml_str = xml_input

            # Remover BOM se presente
            if xml_str.startswith('\ufeff'):
                xml_str = xml_str[1:]

            return ET.fromstring(xml_str)
        except ET.ParseError as e:
            logger.warning(f"XML invalido: {e}")
            return None
        except Exception as e:
            logger.error(f"Erro inesperado ao parsear XML: {e}")
            return None

    @staticmethod
    def _local_name(element: ET.Element) -> str:
        """Nome da tag sem namespace. Ex: '{ns}tpEvento' -> 'tpEvento'."""
        tag = element.tag
        return tag.split('}')[-1] if '}' in tag else tag

    def _find_local(self, element: ET.Element, tag_name: str) -> Optional[ET.Element]:
        """
        Busca recursivamente por tag (ignorando namespace).
        Retorna primeiro match.
        """
        for child in element.iter():
            if self._local_name(child) == tag_name:
                return child
        return None

    def _find_all_local(self, element: ET.Element, tag_name: str) -> list:
        """Busca TODAS as ocorrencias de uma tag (ignorando namespace)."""
        return [
            child for child in element.iter()
            if self._local_name(child) == tag_name
        ]

    def _text_of(self, element: ET.Element, tag_name: str) -> Optional[str]:
        """
        Retorna o texto da primeira tag encontrada, ou None.
        """
        found = self._find_local(element, tag_name)
        if found is None or found.text is None:
            return None
        return found.text.strip() or None

    def detectar_tipo(self, xml_input: Union[bytes, str]) -> TipoXml:
        """
        Detecta o tipo do XML pelo root tag.

        Returns:
            'procEventoCTe' | 'cteProc' | 'invalido'
        """
        root = self._parse_xml(xml_input)
        if root is None:
            return 'invalido'

        root_name = self._local_name(root)

        if root_name == 'procEventoCTe':
            return 'procEventoCTe'
        if root_name == 'cteProc':
            return 'cteProc'

        # Alguns emissores entregam o XML sem o envelope proc* — aceitar:
        if root_name == 'eventoCTe':
            return 'procEventoCTe'
        if root_name in ('CTe', 'infCte'):
            return 'cteProc'

        return 'invalido'

    def parse_evento(self, xml_input: Union[bytes, str]) -> Optional[Dict]:
        """
        Parse de procEventoCTe (ou eventoCTe raw).

        Returns:
            Dict com chaves:
                - tipo: 'procEventoCTe'
                - chave: chave de acesso do CTe afetado (44 digitos) ou None
                - tp_evento: codigo do evento (ex: '110111')
                - cancelamento: bool — True se tp_evento == '110111' AND homologado
                - protocolo: nProt do retEvento (ou None se nao homologado)
                - data_evento: dhEvento do infEvento (ISO string) ou None
                - data_registro: dhRegEvento do retEvento (ISO string) ou None
                - justificativa: xJust do detEvento (ou None)
                - cstat: cStat do retEventoCTe (ex: '135')
                - cstat_descricao: xMotivo do retEventoCTe
                - n_seq_evento: numero sequencial do evento
            ou None se falhou parsear.
        """
        root = self._parse_xml(xml_input)
        if root is None:
            return None

        root_name = self._local_name(root)
        if root_name not in ('procEventoCTe', 'eventoCTe'):
            logger.warning(f"parse_evento: root tag inesperada: {root_name}")
            return None

        # Chave do CTe afetado (dentro de infEvento/chCTe)
        chave = self._text_of(root, 'chCTe')
        if chave:
            chave = chave.strip()

        tp_evento = self._text_of(root, 'tpEvento')
        dh_evento = self._text_of(root, 'dhEvento')
        n_seq_evento = self._text_of(root, 'nSeqEvento')

        # xJust esta dentro de detEvento/evCancCTe para cancelamento
        justificativa = self._text_of(root, 'xJust')

        # retEventoCTe: status + protocolo do evento
        ret_evento = self._find_local(root, 'retEventoCTe')
        cstat = None
        cstat_descricao = None
        protocolo = None
        dh_reg_evento = None
        if ret_evento is not None:
            cstat = self._text_of(ret_evento, 'cStat')
            cstat_descricao = self._text_of(ret_evento, 'xMotivo')
            protocolo = self._text_of(ret_evento, 'nProt')
            dh_reg_evento = self._text_of(ret_evento, 'dhRegEvento')

        cancelamento_efetivo = (
            tp_evento == TP_EVENTO_CANCELAMENTO
            and (cstat == CSTAT_EVENTO_HOMOLOGADO or cstat is None)
        )
        # Obs: se nao houver retEventoCTe (apenas eventoCTe sem retorno), aceitamos
        # mesmo assim se tp_evento == 110111 — alguns emissores entregam so o evento.

        return {
            'tipo': 'procEventoCTe',
            'chave': chave,
            'tp_evento': tp_evento,
            'cancelamento': cancelamento_efetivo,
            'protocolo': protocolo,
            'data_evento': dh_evento,
            'data_registro': dh_reg_evento,
            'justificativa': justificativa,
            'cstat': cstat,
            'cstat_descricao': cstat_descricao,
            'n_seq_evento': n_seq_evento,
        }

    def parse_cte(self, xml_input: Union[bytes, str]) -> Optional[Dict]:
        """
        Parse de cteProc (CTe original completo).

        ATENCAO: este metodo NAO detecta cancelamento — um CTe original em si
        nao traz informacao de cancelamento, so o evento (procEventoCTe) traz.
        Retorna sempre cancelamento=False.

        Returns:
            Dict com chaves:
                - tipo: 'cteProc'
                - chave: chave de acesso (44 digitos) ou None
                - cancelamento: False (sempre)
                - numero: nCT
                - serie: serie
                - modelo: mod (ex: '57')
                - data_emissao: dhEmi (ISO string) ou None
                - emitente_cnpj: CNPJ do emit
                - emitente_nome: xNome do emit
                - valor_total: vTPrest (string decimal) ou None
                - protocolo: nProt do protCTe (autorizacao)
            ou None se falhou.
        """
        root = self._parse_xml(xml_input)
        if root is None:
            return None

        root_name = self._local_name(root)
        if root_name not in ('cteProc', 'CTe', 'infCte'):
            logger.warning(f"parse_cte: root tag inesperada: {root_name}")
            return None

        # Chave: pode vir em protCTe/infProt/chCTe ou em infCte/@Id (prefixo CTe)
        chave = self._text_of(root, 'chCTe')
        if not chave:
            # Fallback: atributo Id de infCte
            inf_cte = self._find_local(root, 'infCte')
            if inf_cte is not None:
                cte_id = inf_cte.get('Id') or ''
                if cte_id.startswith('CTe') and len(cte_id) >= 47:
                    chave = cte_id[3:47]

        numero = self._text_of(root, 'nCT')
        serie = self._text_of(root, 'serie')
        modelo = self._text_of(root, 'mod')
        dh_emi = self._text_of(root, 'dhEmi')

        # Emitente
        emit = self._find_local(root, 'emit')
        emitente_cnpj = None
        emitente_nome = None
        if emit is not None:
            emitente_cnpj = self._text_of(emit, 'CNPJ')
            emitente_nome = self._text_of(emit, 'xNome')

        # Valor total do servico
        valor_total = self._text_of(root, 'vTPrest')

        # Protocolo de autorizacao (nao e cancelamento)
        prot_cte = self._find_local(root, 'protCTe')
        protocolo = None
        if prot_cte is not None:
            protocolo = self._text_of(prot_cte, 'nProt')

        return {
            'tipo': 'cteProc',
            'chave': chave,
            'cancelamento': False,  # CTe original nunca traz cancelamento
            'numero': numero,
            'serie': serie,
            'modelo': modelo,
            'data_emissao': dh_emi,
            'emitente_cnpj': emitente_cnpj,
            'emitente_nome': emitente_nome,
            'valor_total': valor_total,
            'protocolo': protocolo,
        }

    def parse(self, xml_input: Union[bytes, str]) -> Optional[Dict]:
        """
        Helper: detecta o tipo e roteia para o parser correto.

        Returns:
            Dict resultado (de parse_evento ou parse_cte) ou None.
            Sempre inclui chave 'tipo'.
        """
        tipo = self.detectar_tipo(xml_input)
        if tipo == 'procEventoCTe':
            return self.parse_evento(xml_input)
        if tipo == 'cteProc':
            return self.parse_cte(xml_input)
        return None

    def extrair_chave_acesso(self, xml_input: Union[bytes, str]) -> Optional[str]:
        """
        Extrai apenas a chave de acesso de qualquer XML suportado.
        Util quando so precisamos identificar o CTe.

        Returns:
            String de 44 digitos ou None.
        """
        info = self.parse(xml_input)
        if info is None:
            return None
        chave = info.get('chave')
        if chave and len(chave) == 44 and chave.isdigit():
            return chave
        return None
