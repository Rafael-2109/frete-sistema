"""
Parser de CTe XML para o modulo CarVia
=======================================

Estende CTeXMLParser existente com metodos adicionais para:
- NFs referenciadas no CTe (<infDoc>/<infNFe>)
- Dados de rota (<ide>/<cMunIni>, <cMunFim>)
- Dados de carga (<infCarga>)
- Valor da prestacao (<vPrest>)
- Emitente/Remetente/Destinatario

Base: app/odoo/utils/cte_xml_parser.py
"""

import logging
import re
from typing import Dict, List, Optional

from app.odoo.utils.cte_xml_parser import CTeXMLParser

logger = logging.getLogger(__name__)


class CTeXMLParserCarvia(CTeXMLParser):
    """Parser estendido para CTe no contexto CarVia (frete subcontratado)"""

    def get_nfs_referenciadas(self) -> List[Dict]:
        """
        Extrai NFs referenciadas no CTe.

        Estrutura:
            <infDoc>
                <infNFe>
                    <chave>44 digitos</chave>
                    <nDoc>numero NF</nDoc>  (alternativa)
                </infNFe>
            </infDoc>

        Returns:
            Lista de dicts com chave, numero_nf, cnpj_emitente
        """
        if self.root is None:
            return []

        nfs = []
        # Buscar todas as tags infNFe dentro de infDoc
        inf_doc = self._find_tag('infDoc')
        if inf_doc is None:
            return []

        # Iterar por todos os filhos de infDoc buscando infNFe
        for element in inf_doc.iter():
            local_name = element.tag.split('}')[-1] if '}' in element.tag else element.tag
            if local_name == 'infNFe':
                nf_info = self._extrair_info_nfe(element)
                if nf_info:
                    nfs.append(nf_info)

        return nfs

    def _extrair_info_nfe(self, inf_nfe_element) -> Optional[Dict]:
        """Extrai info de um elemento infNFe"""
        chave = self._get_tag_text_in('chave', inf_nfe_element)
        if not chave:
            # Tentar tag alternativa 'chNFe'
            chave = self._get_tag_text_in('chNFe', inf_nfe_element)

        numero_nf = None
        cnpj_emitente = None

        if chave and len(chave) == 44:
            # Extrair numero e CNPJ da chave
            try:
                cnpj_emitente = chave[6:20]
                numero_nf = str(int(chave[25:34]))
            except (ValueError, IndexError):
                pass
        else:
            # Sem chave — tentar nDoc
            numero_nf = self._get_tag_text_in('nDoc', inf_nfe_element)

        if not chave and not numero_nf:
            return None

        return {
            'chave': chave,
            'numero_nf': numero_nf,
            'cnpj_emitente': cnpj_emitente,
        }

    def get_dados_rota(self) -> Dict:
        """
        Extrai dados de rota do CTe.

        Tags: <ide>/<cMunIni>, <ide>/<cMunFim>, <ide>/<UFIni>, <ide>/<UFFim>

        Returns:
            Dict com uf_origem, cidade_origem, uf_destino, cidade_destino, cod_mun_ini, cod_mun_fim
        """
        ide = self._find_tag('ide')
        return {
            'uf_origem': self._get_tag_text_in('UFIni', ide) if ide else None,
            'uf_destino': self._get_tag_text_in('UFFim', ide) if ide else None,
            'cidade_origem': self._get_tag_text_in('xMunIni', ide) if ide else None,
            'cidade_destino': self._get_tag_text_in('xMunFim', ide) if ide else None,
            'cod_mun_ini': self._get_tag_text_in('cMunIni', ide) if ide else None,
            'cod_mun_fim': self._get_tag_text_in('cMunFim', ide) if ide else None,
        }

    def get_dados_carga(self) -> Dict:
        """
        Extrai dados de carga do CTe.

        Tags: <infCarga>/<vCarga>, <infCarga>/<infQ> (qCarga, cUnid, tpMed)

        Returns:
            Dict com valor_carga, peso_bruto, peso_cubado
        """
        inf_carga = self._find_tag('infCarga')
        if inf_carga is None:
            return {}

        valor_carga = self._to_decimal(
            self._get_tag_text_in('vCarga', inf_carga) or ''
        )

        peso_bruto = None
        peso_cubado = None

        # Iterar por infQ para extrair pesos
        for element in inf_carga.iter():
            local_name = element.tag.split('}')[-1] if '}' in element.tag else element.tag
            if local_name == 'infQ':
                c_unid = self._get_tag_text_in('cUnid', element)
                tp_med = self._get_tag_text_in('tpMed', element)
                q_carga = self._to_decimal(
                    self._get_tag_text_in('qCarga', element) or ''
                )

                # cUnid: 00=M3, 01=KG, 02=TON, 03=UNID, 04=LITRO, 05=MMBTU
                if c_unid == '01' or (tp_med and 'PESO' in tp_med.upper()):
                    peso_bruto = q_carga
                elif c_unid == '00' or (tp_med and 'CUBAGEM' in tp_med.upper()):
                    peso_cubado = q_carga

        return {
            'valor_carga': valor_carga,
            'peso_bruto': peso_bruto,
            'peso_cubado': peso_cubado,
        }

    def get_valor_prestacao(self) -> Optional[float]:
        """
        Extrai valor total da prestacao de servico.

        Tag: <vPrest>/<vTPrest>

        Returns:
            Valor float ou None
        """
        v_prest = self._find_tag('vPrest')
        if v_prest is None:
            return None

        vtprest = self._get_tag_text_in('vTPrest', v_prest)
        return self._to_decimal(vtprest or '')

    def get_numero_cte(self) -> Optional[str]:
        """Extrai numero do CTe de <ide>/<nCT>"""
        return self._get_tag_text('nCT')

    def get_chave_acesso(self) -> Optional[str]:
        """Extrai chave de acesso do CTe (44 digitos)"""
        # Tag <chCTe> dentro de <protCTe>
        chave = self._get_tag_text('chCTe')
        if chave and len(chave) == 44:
            return chave

        # Fallback: atributo Id de <infCte>
        inf_cte = self._find_tag('infCte')
        if inf_cte is not None:
            inf_id = inf_cte.get('Id', '')
            digits = re.sub(r'\D', '', inf_id)
            if len(digits) == 44:
                return digits

        return None

    def get_data_emissao(self) -> Optional[str]:
        """Extrai data de emissao (dhEmi) do CTe"""
        return self._get_tag_text('dhEmi')

    def get_emitente(self) -> Dict:
        """Extrai dados do emitente (emit) — quem emitiu o CTe"""
        emit = self._find_tag('emit')
        if emit is None:
            return {}

        ender = None
        for el in emit.iter():
            local_name = el.tag.split('}')[-1] if '}' in el.tag else el.tag
            if local_name == 'enderEmit':
                ender = el
                break

        return {
            'cnpj': self._get_tag_text_in('CNPJ', emit),
            'nome': self._get_tag_text_in('xNome', emit),
            'uf': self._get_tag_text_in('UF', ender) if ender else None,
            'cidade': self._get_tag_text_in('xMun', ender) if ender else None,
        }

    def get_remetente(self) -> Dict:
        """Extrai dados do remetente (rem) — quem envia a carga"""
        rem = self._find_tag('rem')
        if rem is None:
            return {}

        return {
            'cnpj': self._get_tag_text_in('CNPJ', rem),
            'nome': self._get_tag_text_in('xNome', rem),
        }

    def get_destinatario(self) -> Dict:
        """Extrai dados do destinatario (dest)"""
        dest = self._find_tag('dest')
        if dest is None:
            return {}

        return {
            'cnpj': self._get_tag_text_in('CNPJ', dest),
            'nome': self._get_tag_text_in('xNome', dest),
        }

    def get_todas_informacoes_carvia(self) -> Dict:
        """Extrai todas as informacoes relevantes para o modulo CarVia"""
        rota = self.get_dados_rota()
        carga = self.get_dados_carga()
        emit = self.get_emitente()
        rem = self.get_remetente()
        dest = self.get_destinatario()
        nfs = self.get_nfs_referenciadas()

        return {
            # CTe
            'cte_numero': self.get_numero_cte(),
            'cte_chave_acesso': self.get_chave_acesso(),
            'cte_valor': self.get_valor_prestacao(),
            'cte_data_emissao': self.get_data_emissao(),
            'tipo_cte': self.get_tipo_cte(),
            'tipo_cte_descricao': self.get_tipo_cte_descricao(),
            # Rota
            'uf_origem': rota.get('uf_origem'),
            'cidade_origem': rota.get('cidade_origem'),
            'uf_destino': rota.get('uf_destino'),
            'cidade_destino': rota.get('cidade_destino'),
            # Carga
            'valor_mercadoria': carga.get('valor_carga'),
            'peso_bruto': carga.get('peso_bruto'),
            'peso_cubado': carga.get('peso_cubado'),
            # Participantes
            'emitente': emit,
            'remetente': rem,
            'destinatario': dest,
            # NFs referenciadas
            'nfs_referenciadas': nfs,
            # Impostos
            'impostos': self.get_impostos(),
        }

    def _get_tag_text_in(self, tag_name: str, root) -> Optional[str]:
        """Helper: busca texto de tag dentro de um elemento especifico"""
        if root is None:
            return None
        element = self._find_tag(tag_name, root=root)
        if element is not None and element.text:
            return element.text.strip()
        return None


def parsear_cte_carvia(xml_content) -> Dict:
    """Funcao helper para parsear XML de CTe no contexto CarVia"""
    parser = CTeXMLParserCarvia(xml_content)
    return parser.get_todas_informacoes_carvia()
