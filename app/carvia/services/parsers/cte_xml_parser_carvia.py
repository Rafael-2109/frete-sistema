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
        """Extrai dados do destinatario priorizando o endereco de entrega (<receb>).

        Em CTe v4.00, <receb> representa o LOCAL DE ENTREGA fisico (onde a carga
        sera efetivamente entregue), enquanto <dest> e o destinatario fiscal/comercial.
        Para fins operacionais/logisticos CarVia, usamos o recebedor como fonte primaria
        e caimos no destinatario fiscal apenas quando <receb> nao existe no XML.
        """
        receb = self._find_tag('receb')
        if receb is not None:
            cnpj = self._get_tag_text_in('CNPJ', receb)
            nome = self._get_tag_text_in('xNome', receb)
            if cnpj or nome:
                return {'cnpj': cnpj, 'nome': nome}

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

    def get_expedidor(self) -> Dict:
        """Extrai dados do expedidor (<exped>) — quem despacha a carga"""
        exped = self._find_tag('exped')
        if exped is None:
            return {}
        return {
            'cnpj': self._get_tag_text_in('CNPJ', exped),
            'nome': self._get_tag_text_in('xNome', exped),
        }

    def get_endereco_expedidor(self) -> Dict:
        """Extrai endereco completo do expedidor (<exped>/<enderExped>)"""
        return self._extrair_endereco('enderExped', 'exped')

    def get_ie_expedidor(self) -> Optional[str]:
        """Extrai IE do expedidor"""
        exped = self._find_tag('exped')
        return self._get_tag_text_in('IE', exped) if exped else None

    def get_fone_expedidor(self) -> Optional[str]:
        """Extrai telefone do expedidor"""
        exped = self._find_tag('exped')
        return self._get_tag_text_in('fone', exped) if exped else None

    def get_recebedor(self) -> Dict:
        """Extrai dados do recebedor (<receb>) — quem recebe a carga"""
        receb = self._find_tag('receb')
        if receb is None:
            return {}
        return {
            'cnpj': self._get_tag_text_in('CNPJ', receb),
            'nome': self._get_tag_text_in('xNome', receb),
        }

    def get_endereco_recebedor(self) -> Dict:
        """Extrai endereco completo do recebedor (<receb>/<enderReceb>)"""
        return self._extrair_endereco('enderReceb', 'receb')

    def get_ie_recebedor(self) -> Optional[str]:
        """Extrai IE do recebedor"""
        receb = self._find_tag('receb')
        return self._get_tag_text_in('IE', receb) if receb else None

    def get_fone_recebedor(self) -> Optional[str]:
        """Extrai telefone do recebedor"""
        receb = self._find_tag('receb')
        return self._get_tag_text_in('fone', receb) if receb else None

    def get_rntrc(self) -> Optional[str]:
        """Extrai RNTRC de <infModal>/<rodo>/<RNTRC>"""
        rodo = self._find_tag('rodo')
        return self._get_tag_text_in('RNTRC', rodo) if rodo else None

    def get_tipo_servico(self) -> Optional[str]:
        """Extrai tipo de servico de <ide>/<tpServ>.
        0=Normal, 1=Subcontratacao, 2=Redespacho, 3=Redespacho Intermediario, 4=Multimodal"""
        ide = self._find_tag('ide')
        codigo = self._get_tag_text_in('tpServ', ide) if ide else None
        tipos = {
            '0': 'NORMAL', '1': 'SUBCONTRATACAO',
            '2': 'REDESPACHO', '3': 'REDESPACHO INTERMEDIARIO',
            '4': 'MULTIMODAL',
        }
        return tipos.get(codigo, codigo)

    def get_valor_a_receber(self) -> Optional[float]:
        """Extrai valor a receber de <vPrest>/<vRec>"""
        v_prest = self._find_tag('vPrest')
        if v_prest is None:
            return None
        vrec = self._get_tag_text_in('vRec', v_prest)
        return self._to_decimal(vrec or '')

    def get_qrcode_url(self) -> Optional[str]:
        """Extrai URL do QR Code de <infCTeSupl>/<qrCodCTe>"""
        supl = self._find_tag('infCTeSupl')
        if supl is None:
            return None
        url = self._get_tag_text_in('qrCodCTe', supl)
        # URL pode conter &amp; — decodificar
        if url:
            url = url.replace('&amp;', '&')
        return url

    def get_observacoes_contribuinte(self) -> List[Dict]:
        """Extrai observacoes do contribuinte (<compl>/<ObsCont>) — multiplas entradas"""
        compl = self._find_tag('compl')
        if compl is None:
            return []

        obs_list = []
        for element in compl.iter():
            local_name = element.tag.split('}')[-1] if '}' in element.tag else element.tag
            if local_name == 'ObsCont':
                campo = element.get('xCampo', '')
                texto = self._get_tag_text_in('xTexto', element)
                if texto:
                    obs_list.append({'campo': campo, 'texto': texto})

        return obs_list

    def get_motivo(self) -> Optional[str]:
        """Extrai texto apos 'MOTIVO:' de qualquer <ObsCont>/<xTexto>.

        Usado principalmente em CTes Complementares. O <xCampo> costuma ser '2'
        mas nao e garantia — o padrao e o texto comecar com 'MOTIVO:'. Retorna
        apenas o conteudo apos 'MOTIVO:' (trimmed), preservando o texto livre
        (descarga, reentrega, pedagio, etc — nao interpretado).

        Exemplo XML:
            <ObsCont xCampo="2"><xTexto>- MOTIVO: descarga</xTexto></ObsCont>
        Retorna: 'descarga'
        """
        import re as _re
        for obs in self.get_observacoes_contribuinte():
            texto = (obs.get('texto') or '').strip()
            match = _re.search(r'MOTIVO\s*:\s*(.+)', texto, _re.IGNORECASE)
            if match:
                motivo = match.group(1).strip()
                # Remove prefixos comuns de formatacao (-, *, :)
                motivo = _re.sub(r'^[\-\*:\s]+', '', motivo).strip()
                return motivo[:500] if motivo else None
        return None

    def get_previsao_entrega(self) -> Optional[str]:
        """Extrai data de previsao de entrega de <compl>/<Entrega>/<comData>/<dProg>"""
        entrega = self._find_tag('Entrega')
        if entrega is None:
            return None
        com_data = self._find_tag('comData', root=entrega)
        if com_data is None:
            return None
        return self._get_tag_text_in('dProg', com_data)

    def get_situacao_tributaria_icms(self) -> Optional[str]:
        """Extrai CST do ICMS de <imp>/<ICMS>/<ICMSXX>/<CST>"""
        icms = self._find_tag('ICMS')
        if icms is None:
            return None
        # Procurar primeiro filho ICMSXX (ICMS00, ICMS20, ICMS45, etc.)
        for element in icms:
            local_name = element.tag.split('}')[-1] if '}' in element.tag else element.tag
            if local_name.startswith('ICMS'):
                cst = self._get_tag_text_in('CST', element)
                return cst
        return None

    def get_fone_remetente(self) -> Optional[str]:
        """Extrai telefone do remetente"""
        rem = self._find_tag('rem')
        return self._get_tag_text_in('fone', rem) if rem else None

    def get_fone_destinatario(self) -> Optional[str]:
        """Extrai telefone priorizando o recebedor (LOC ENTREGA) com fallback no destinatario fiscal."""
        receb = self._find_tag('receb')
        if receb is not None:
            fone = self._get_tag_text_in('fone', receb)
            if fone:
                return fone
        dest = self._find_tag('dest')
        return self._get_tag_text_in('fone', dest) if dest else None

    def get_cdv(self) -> Optional[str]:
        """Extrai digito verificador de <ide>/<cDV>"""
        ide = self._find_tag('ide')
        return self._get_tag_text_in('cDV', ide) if ide else None

    def get_ctrc_formatado(self) -> Optional[str]:
        """Monta CTRC no formato CAR-{nCT}-{cDV} (ex: CAR-133-2).

        O CTRC (Conhecimento de Transporte Rodoviario de Cargas) e o
        identificador oficial do CTe no SSW/SEFAZ.

        Fontes: <ide>/<nCT> + <ide>/<cDV>
        """
        nct = self.get_numero_cte()
        cdv = self.get_cdv()
        if nct is not None:
            try:
                nct = str(int(nct))  # Strip leading zeros para consistencia com backfill
            except ValueError:
                pass
            return f"CAR-{nct}-{cdv}" if cdv else f"CAR-{nct}"
        return None

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
        """Extrai endereco priorizando o LOCAL DE ENTREGA (<receb>/<enderReceb>).

        Em CTe v4.00, o endereco de entrega fisica (LOC ENTREGA) vem de <enderReceb>.
        O <enderDest> e o endereco fiscal do destinatario (pode ser diferente).
        Para CarVia, priorizamos o endereco de entrega e caimos no destinatario fiscal
        apenas como fallback quando o recebedor nao esta presente no XML.
        """
        endereco_entrega = self._extrair_endereco('enderReceb', 'receb')
        if endereco_entrega:
            return endereco_entrega
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
        """Extrai IE priorizando o recebedor (LOC ENTREGA) com fallback no destinatario fiscal."""
        receb = self._find_tag('receb')
        if receb is not None:
            ie = self._get_tag_text_in('IE', receb)
            if ie:
                return ie
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
        para enderecos, protocolo, componentes, quantidades, observacoes,
        expedidor, recebedor, RNTRC, QR code, IBS/CBS e previsao entrega.
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
            'endereco_expedidor': self.get_endereco_expedidor(),
            'endereco_recebedor': self.get_endereco_recebedor(),
            # Inscricoes Estaduais
            'ie_emitente': self.get_ie_emitente(),
            'ie_remetente': self.get_ie_remetente(),
            'ie_destinatario': self.get_ie_destinatario(),
            'ie_expedidor': self.get_ie_expedidor(),
            'ie_recebedor': self.get_ie_recebedor(),
            # Participantes extras
            'expedidor': self.get_expedidor(),
            'recebedor': self.get_recebedor(),
            # Telefones
            'fone_remetente': self.get_fone_remetente(),
            'fone_destinatario': self.get_fone_destinatario(),
            'fone_expedidor': self.get_fone_expedidor(),
            'fone_recebedor': self.get_fone_recebedor(),
            # Prestacao
            'componentes_prestacao': self.get_componentes_prestacao(),
            'valor_a_receber': self.get_valor_a_receber(),
            # Carga detalhada
            'produto_predominante': self.get_produto_predominante(),
            'quantidades_carga': self.get_quantidades_carga(),
            # Observacoes
            'observacoes_complementares': self.get_observacoes(),
            'observacoes_contribuinte': self.get_observacoes_contribuinte(),
            'info_adicional_fisco': self.get_info_adicional_fisco(),
            # Campos SSW adicionais
            'rntrc': self.get_rntrc(),
            'tipo_servico': self.get_tipo_servico(),
            'situacao_tributaria_icms': self.get_situacao_tributaria_icms(),
            'previsao_entrega': self.get_previsao_entrega(),
            'qrcode_url': self.get_qrcode_url(),
            # IBS/CBS (Reforma Tributaria)
            'ibscbs': self.get_ibscbs(),
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
        # A4.1 (2026-04-18): enderecos textuais (logradouro, CEP, bairro,
        # numero) para suportar correcao via CC-e (Bug #4). Antes so
        # cidade/UF eram persistidos.
        end_rem = self.get_endereco_remetente() or {}
        end_dest = self.get_endereco_destinatario() or {}

        return {
            # CTe
            'cte_numero': self.get_numero_cte(),
            'cte_chave_acesso': self.get_chave_acesso(),
            'ctrc_numero': self.get_ctrc_formatado(),
            'cte_valor': self.get_valor_prestacao(),
            'cte_data_emissao': self.get_data_emissao(),
            'tipo_cte': self.get_tipo_cte(),
            'tipo_cte_descricao': self.get_tipo_cte_descricao(),
            'info_complementar': self.get_info_complementar(),
            # Rota
            'uf_origem': rota.get('uf_origem'),
            'cidade_origem': rota.get('cidade_origem'),
            'uf_destino': rota.get('uf_destino'),
            'cidade_destino': rota.get('cidade_destino'),
            # A4.1: enderecos textuais persistiveis
            'remetente_logradouro': end_rem.get('logradouro'),
            'remetente_numero': end_rem.get('numero'),
            'remetente_bairro': end_rem.get('bairro'),
            'remetente_cep': end_rem.get('cep'),
            'destinatario_logradouro': end_dest.get('logradouro'),
            'destinatario_numero': end_dest.get('numero'),
            'destinatario_bairro': end_dest.get('bairro'),
            'destinatario_cep': end_dest.get('cep'),
            # Carga
            'valor_mercadoria': carga.get('valor_carga'),
            'peso_bruto': carga.get('peso_bruto'),
            'peso_cubado': carga.get('peso_cubado'),
            # Participantes
            'emitente': emit,
            'remetente': rem,
            'destinatario': dest,
            # Enderecos completos (incluindo logradouro/cep/bairro/numero)
            'endereco_remetente': end_rem,
            'endereco_destinatario': end_dest,
            # NFs referenciadas
            'nfs_referenciadas': nfs,
            # Impostos
            'impostos': self.get_impostos(),
            # Tomador do servico (<ide>/<toma3> ou <toma4>)
            'tomador': self.get_tomador(),
            # Motivo extraido de <compl>/<ObsCont>/<xTexto> "MOTIVO: ..."
            # (principalmente para CTes Complementares)
            'motivo': self.get_motivo(),
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
