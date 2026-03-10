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

    # ------------------------------------------------------------------
    # Metodos adicionais para DACTE PDF
    # ------------------------------------------------------------------

    def get_serie(self) -> Optional[str]:
        """Extrai serie do CTe de <ide>/<serie>"""
        ide = self._find_tag('ide')
        return self._get_tag_text_in('serie', ide) if ide else None

    def get_cfop(self) -> Optional[str]:
        """Extrai CFOP de <ide>/<CFOP>"""
        ide = self._find_tag('ide')
        return self._get_tag_text_in('CFOP', ide) if ide else None

    def get_natureza_operacao(self) -> Optional[str]:
        """Extrai natureza da operacao de <ide>/<natOp>"""
        ide = self._find_tag('ide')
        return self._get_tag_text_in('natOp', ide) if ide else None

    def get_modal(self) -> Optional[str]:
        """Extrai modal de <ide>/<modal>. 01=Rodoviario, 02=Aereo, etc."""
        ide = self._find_tag('ide')
        codigo = self._get_tag_text_in('modal', ide) if ide else None
        modais = {
            '01': 'Rodoviario',
            '02': 'Aereo',
            '03': 'Aquaviario',
            '04': 'Ferroviario',
            '05': 'Dutoviario',
            '06': 'Multimodal',
        }
        return modais.get(codigo, codigo)

    def get_forma_pagamento(self) -> Optional[str]:
        """Extrai forma de pagamento de <ide>/<forPag>. 0=Pago, 1=A Pagar, 2=Outros"""
        ide = self._find_tag('ide')
        codigo = self._get_tag_text_in('forPag', ide) if ide else None
        formas = {'0': 'Pago', '1': 'A Pagar', '2': 'Outros'}
        return formas.get(codigo, codigo)

    def get_protocolo_autorizacao(self) -> Dict:
        """Extrai protocolo de autorizacao de <protCTe>"""
        prot = self._find_tag('protCTe')
        if prot is None:
            return {}
        return {
            'numero': self._get_tag_text_in('nProt', prot),
            'data_recebimento': self._get_tag_text_in('dhRecbto', prot),
            'codigo_status': self._get_tag_text_in('cStat', prot),
            'motivo': self._get_tag_text_in('xMotivo', prot),
        }

    def get_tomador(self) -> Dict:
        """Extrai dados do tomador do servico (<ide>/<toma3> ou <toma4>)"""
        ide = self._find_tag('ide')
        if ide is None:
            return {}

        # toma3: tomador e um dos participantes (0=Rem, 1=Exped, 2=Receb, 3=Dest)
        toma3 = self._find_tag('toma3', root=ide)
        if toma3 is not None:
            toma_code = self._get_tag_text_in('toma', toma3)
            toma_map = {
                '0': 'Remetente',
                '1': 'Expedidor',
                '2': 'Recebedor',
                '3': 'Destinatario',
            }
            return {
                'tipo': toma_map.get(toma_code, toma_code),
                'codigo': toma_code,
            }

        # toma4: tomador e terceiro (com CNPJ/CPF proprio)
        toma4 = self._find_tag('toma4', root=ide)
        if toma4 is not None:
            return {
                'tipo': 'Outros',
                'codigo': '4',
                'cnpj': self._get_tag_text_in('CNPJ', toma4),
                'cpf': self._get_tag_text_in('CPF', toma4),
                'nome': self._get_tag_text_in('xNome', toma4),
                'ie': self._get_tag_text_in('IE', toma4),
            }

        return {}

    def _extrair_endereco(self, tag_endereco: str, tag_pai: str) -> Dict:
        """Helper: extrai endereco completo de uma tag dentro de um pai"""
        pai = self._find_tag(tag_pai)
        if pai is None:
            return {}

        ender = None
        for el in pai.iter():
            local_name = el.tag.split('}')[-1] if '}' in el.tag else el.tag
            if local_name == tag_endereco:
                ender = el
                break

        if ender is None:
            return {}

        return {
            'logradouro': self._get_tag_text_in('xLgr', ender),
            'numero': self._get_tag_text_in('nro', ender),
            'complemento': self._get_tag_text_in('xCpl', ender),
            'bairro': self._get_tag_text_in('xBairro', ender),
            'codigo_municipio': self._get_tag_text_in('cMun', ender),
            'municipio': self._get_tag_text_in('xMun', ender),
            'uf': self._get_tag_text_in('UF', ender),
            'cep': self._get_tag_text_in('CEP', ender),
            'fone': self._get_tag_text_in('fone', ender),
        }

    def get_endereco_emitente(self) -> Dict:
        """Extrai endereco completo do emitente (<emit>/<enderEmit>)"""
        return self._extrair_endereco('enderEmit', 'emit')

    def get_endereco_remetente(self) -> Dict:
        """Extrai endereco completo do remetente (<rem>/<enderReme>)"""
        return self._extrair_endereco('enderReme', 'rem')

    def get_endereco_destinatario(self) -> Dict:
        """Extrai endereco completo do destinatario (<dest>/<enderDest>)"""
        return self._extrair_endereco('enderDest', 'dest')

    def get_ie_emitente(self) -> Optional[str]:
        """Extrai IE do emitente"""
        emit = self._find_tag('emit')
        return self._get_tag_text_in('IE', emit) if emit else None

    def get_ie_remetente(self) -> Optional[str]:
        """Extrai IE do remetente"""
        rem = self._find_tag('rem')
        return self._get_tag_text_in('IE', rem) if rem else None

    def get_ie_destinatario(self) -> Optional[str]:
        """Extrai IE do destinatario"""
        dest = self._find_tag('dest')
        return self._get_tag_text_in('IE', dest) if dest else None

    def get_componentes_prestacao(self) -> List[Dict]:
        """Extrai componentes da prestacao (<vPrest>/<Comp>)"""
        v_prest = self._find_tag('vPrest')
        if v_prest is None:
            return []

        componentes = []
        for element in v_prest.iter():
            local_name = element.tag.split('}')[-1] if '}' in element.tag else element.tag
            if local_name == 'Comp':
                nome = self._get_tag_text_in('xNome', element)
                valor = self._to_decimal(
                    self._get_tag_text_in('vComp', element) or ''
                )
                if nome or valor:
                    componentes.append({'nome': nome, 'valor': valor})

        return componentes

    def get_produto_predominante(self) -> Optional[str]:
        """Extrai produto predominante de <infCarga>/<proPred>"""
        inf_carga = self._find_tag('infCarga')
        return self._get_tag_text_in('proPred', inf_carga) if inf_carga else None

    def get_quantidades_carga(self) -> List[Dict]:
        """Extrai todas as quantidades de carga (<infCarga>/<infQ>)"""
        inf_carga = self._find_tag('infCarga')
        if inf_carga is None:
            return []

        quantidades = []
        unidades = {
            '00': 'M3', '01': 'KG', '02': 'TON',
            '03': 'UNID', '04': 'LITRO', '05': 'MMBTU',
        }

        for element in inf_carga.iter():
            local_name = element.tag.split('}')[-1] if '}' in element.tag else element.tag
            if local_name == 'infQ':
                c_unid = self._get_tag_text_in('cUnid', element)
                tp_med = self._get_tag_text_in('tpMed', element)
                q_carga = self._to_decimal(
                    self._get_tag_text_in('qCarga', element) or ''
                )
                quantidades.append({
                    'codigo_unidade': c_unid,
                    'unidade': unidades.get(c_unid, c_unid),
                    'tipo_medida': tp_med,
                    'quantidade': q_carga,
                })

        return quantidades

    def get_observacoes(self) -> Optional[str]:
        """Extrai observacoes complementares de <compl>/<xObs>"""
        compl = self._find_tag('compl')
        return self._get_tag_text_in('xObs', compl) if compl else None

    def get_info_adicional_fisco(self) -> Optional[str]:
        """Extrai informacoes adicionais de interesse do fisco de <compl>/<xCaracAd>"""
        compl = self._find_tag('compl')
        return self._get_tag_text_in('xCaracAd', compl) if compl else None

    def get_todas_informacoes_dacte(self) -> Dict:
        """Extrai TODAS as informacoes necessarias para gerar o DACTE PDF.

        Superset de get_todas_informacoes_carvia() com campos adicionais
        para enderecos, protocolo, componentes, quantidades e observacoes.
        """
        # Base: todas as informacoes CarVia
        dados = self.get_todas_informacoes_carvia()

        # Campos adicionais para DACTE
        dados.update({
            # Identificacao
            'serie': self.get_serie(),
            'cfop': self.get_cfop(),
            'natureza_operacao': self.get_natureza_operacao(),
            'modal': self.get_modal(),
            'forma_pagamento': self.get_forma_pagamento(),
            # Protocolo
            'protocolo': self.get_protocolo_autorizacao(),
            # Tomador
            'tomador': self.get_tomador(),
            # Enderecos completos
            'endereco_emitente': self.get_endereco_emitente(),
            'endereco_remetente': self.get_endereco_remetente(),
            'endereco_destinatario': self.get_endereco_destinatario(),
            # Inscricoes Estaduais
            'ie_emitente': self.get_ie_emitente(),
            'ie_remetente': self.get_ie_remetente(),
            'ie_destinatario': self.get_ie_destinatario(),
            # Prestacao
            'componentes_prestacao': self.get_componentes_prestacao(),
            # Carga detalhada
            'produto_predominante': self.get_produto_predominante(),
            'quantidades_carga': self.get_quantidades_carga(),
            # Observacoes
            'observacoes_complementares': self.get_observacoes(),
            'info_adicional_fisco': self.get_info_adicional_fisco(),
        })

        return dados

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
