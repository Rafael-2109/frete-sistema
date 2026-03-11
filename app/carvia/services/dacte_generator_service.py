"""
DACTE Generator Service — Gera PDF de DACTE no layout SSW
==========================================================

Fluxo: XML bytes -> CTeXMLParserCarvia -> formatacao SSW -> template HTML -> WeasyPrint -> PDF bytes

Layout: 2 vias por pagina (portrait A4), 2 colunas por via, 5 participantes,
QR code, barcode Code128, formatacao brasileira completa.

Fallback: Se nao tem XML, gera representacao simplificada com dados do banco.
"""

import base64
import logging
from io import BytesIO
from typing import Optional

from flask import render_template

logger = logging.getLogger(__name__)


class DacteGeneratorService:
    """Gera DACTE PDF para operacoes e subcontratos CarVia — layout SSW"""

    def gerar_dacte_pdf(self, tipo: str, entity_id: int) -> bytes:
        """Gera PDF do DACTE para uma entidade CarVia.

        Args:
            tipo: 'operacao' ou 'subcontrato'
            entity_id: ID da entidade

        Returns:
            bytes do PDF gerado

        Raises:
            ValueError: se entidade nao encontrada
        """
        from weasyprint import HTML

        # Tentar extrair dados do XML primeiro
        dados_raw = self._extrair_dados_xml(tipo, entity_id)
        simplificado = False

        if dados_raw is None:
            # Fallback: dados do banco
            dados_raw = self._extrair_dados_banco(tipo, entity_id)
            simplificado = True

        # Preparar dados formatados para o template
        d = self._preparar_dados_formatados(dados_raw)

        # Renderizar HTML
        html_content = render_template(
            'carvia/dacte_pdf.html',
            d=d,
            simplificado=simplificado,
        )

        # Gerar PDF
        pdf_buffer = BytesIO()
        HTML(string=html_content).write_pdf(pdf_buffer)
        pdf_buffer.seek(0)

        return pdf_buffer.getvalue()

    # ------------------------------------------------------------------
    # Extracao de dados
    # ------------------------------------------------------------------

    def _extrair_dados_xml(self, tipo: str, entity_id: int) -> Optional[dict]:
        """Extrai dados do XML armazenado no storage.

        Returns:
            dict com dados DACTE ou None se XML indisponivel
        """
        entity = self._buscar_entidade(tipo, entity_id)
        xml_path = getattr(entity, 'cte_xml_path', None)

        if not xml_path:
            return None

        try:
            from app.utils.file_storage import get_file_storage
            storage = get_file_storage()
            xml_bytes = storage.download_file(xml_path)

            if not xml_bytes:
                logger.warning(
                    f"XML nao encontrado no storage para {tipo} {entity_id}: {xml_path}"
                )
                return None

            from app.carvia.services.cte_xml_parser_carvia import CTeXMLParserCarvia
            parser = CTeXMLParserCarvia(xml_bytes)
            dados = parser.get_todas_informacoes_dacte()

            # Garantir que temos a chave de acesso
            if not dados.get('cte_chave_acesso') and hasattr(entity, 'cte_chave_acesso'):
                dados['cte_chave_acesso'] = entity.cte_chave_acesso

            return dados

        except Exception as e:
            logger.error(f"Erro ao parsear XML do {tipo} {entity_id}: {e}")
            return None

    def _extrair_dados_banco(self, tipo: str, entity_id: int) -> dict:
        """Extrai dados disponiveis no banco para DACTE simplificado."""
        entity = self._buscar_entidade(tipo, entity_id)

        dados = {
            'cte_numero': getattr(entity, 'cte_numero', None),
            'cte_chave_acesso': getattr(entity, 'cte_chave_acesso', None),
            'cte_valor': getattr(entity, 'cte_valor', None),
            'cte_data_emissao': (
                entity.cte_data_emissao.strftime('%Y-%m-%dT%H:%M:%S')
                if getattr(entity, 'cte_data_emissao', None)
                else None
            ),
            'tipo_cte': None,
            'tipo_cte_descricao': 'Normal',
            # Participantes
            'emitente': {}, 'remetente': {}, 'destinatario': {},
            'expedidor': {}, 'recebedor': {},
            # Enderecos
            'endereco_emitente': {}, 'endereco_remetente': {},
            'endereco_destinatario': {}, 'endereco_expedidor': {},
            'endereco_recebedor': {},
            # IEs e fones
            'ie_emitente': None, 'ie_remetente': None,
            'ie_destinatario': None, 'ie_expedidor': None, 'ie_recebedor': None,
            'fone_remetente': None, 'fone_destinatario': None,
            'fone_expedidor': None, 'fone_recebedor': None,
            # NFs e impostos
            'nfs_referenciadas': [],
            'impostos': {},
            'ibscbs': None,
            # Campos extras
            'serie': None, 'cfop': None, 'natureza_operacao': None,
            'modal': None, 'forma_pagamento': None,
            'protocolo': {}, 'tomador': {},
            'componentes_prestacao': [], 'valor_a_receber': None,
            'produto_predominante': None, 'quantidades_carga': [],
            'observacoes_complementares': None, 'observacoes_contribuinte': [],
            'info_adicional_fisco': None,
            'rntrc': None, 'tipo_servico': None,
            'situacao_tributaria_icms': None, 'previsao_entrega': None,
            'qrcode_url': None,
            # Rota e carga
            'uf_origem': None, 'cidade_origem': None,
            'uf_destino': None, 'cidade_destino': None,
            'valor_mercadoria': None, 'peso_bruto': None, 'peso_cubado': None,
        }

        if tipo == 'operacao':
            dados.update({
                'uf_origem': entity.uf_origem,
                'cidade_origem': entity.cidade_origem,
                'uf_destino': entity.uf_destino,
                'cidade_destino': entity.cidade_destino,
                'valor_mercadoria': float(entity.valor_mercadoria) if entity.valor_mercadoria else None,
                'peso_bruto': float(entity.peso_bruto) if entity.peso_bruto else None,
                'peso_cubado': float(entity.peso_cubado) if entity.peso_cubado else None,
            })
            dados['remetente'] = {
                'cnpj': entity.cnpj_cliente,
                'nome': entity.nome_cliente,
            }
        elif tipo == 'subcontrato':
            operacao = entity.operacao if hasattr(entity, 'operacao') else None
            if operacao:
                dados.update({
                    'uf_origem': operacao.uf_origem,
                    'cidade_origem': operacao.cidade_origem,
                    'uf_destino': operacao.uf_destino,
                    'cidade_destino': operacao.cidade_destino,
                    'valor_mercadoria': float(operacao.valor_mercadoria) if operacao.valor_mercadoria else None,
                    'peso_bruto': float(operacao.peso_bruto) if operacao.peso_bruto else None,
                    'peso_cubado': float(operacao.peso_cubado) if operacao.peso_cubado else None,
                })
            if entity.transportadora:
                dados['emitente'] = {
                    'cnpj': entity.transportadora.cnpj,
                    'nome': entity.transportadora.razao_social,
                }

        return dados

    def _buscar_entidade(self, tipo: str, entity_id: int):
        """Busca entidade no banco por tipo e ID."""
        from app import db

        if tipo == 'operacao':
            from app.carvia.models import CarviaOperacao
            entity = db.session.get(CarviaOperacao, entity_id)
            if not entity:
                raise ValueError(f'Operacao {entity_id} nao encontrada')
        elif tipo == 'subcontrato':
            from app.carvia.models import CarviaSubcontrato
            entity = db.session.get(CarviaSubcontrato, entity_id)
            if not entity:
                raise ValueError(f'Subcontrato {entity_id} nao encontrada')
        else:
            raise ValueError(f'Tipo invalido: {tipo}. Use "operacao" ou "subcontrato"')

        return entity

    # ------------------------------------------------------------------
    # Pipeline de formatacao SSW
    # ------------------------------------------------------------------

    def _preparar_dados_formatados(self, dados: dict) -> dict:
        """Prepara dict com todos os dados ja formatados para o template.

        Aplica formatacao brasileira SSW em CNPJs, CEPs, fones, valores,
        pesos, chave de acesso. Gera QR code e barcode.
        """
        chave = dados.get('cte_chave_acesso') or ''
        prot = dados.get('protocolo') or {}
        impostos = dados.get('impostos') or {}
        ibscbs = dados.get('ibscbs') or {}
        tomador = dados.get('tomador') or {}

        # Enderecos
        end_emit = dados.get('endereco_emitente') or {}
        end_rem = dados.get('endereco_remetente') or {}
        end_dest = dados.get('endereco_destinatario') or {}
        end_exp = dados.get('endereco_expedidor') or {}
        end_rec = dados.get('endereco_recebedor') or {}

        # Resolver tomador: codigo -> abreviacao SSW
        toma_code = tomador.get('codigo')
        toma_abrev_map = {'0': 'REM', '1': 'EXP', '2': 'REC', '3': 'DEST', '4': 'OUTROS'}
        toma_abrev = toma_abrev_map.get(toma_code, 'DEST')

        # Montar observacoes concatenadas
        obs_parts = []
        for obs in (dados.get('observacoes_contribuinte') or []):
            if obs.get('texto'):
                obs_parts.append(obs['texto'])
        obs_texto = ' - '.join(obs_parts) if obs_parts else (dados.get('observacoes_complementares') or '')

        # Formato autorizacao: DD/MM/AA HH:MM
        auth_dt = prot.get('data_recebimento') or ''
        auth_formatada = ''
        if auth_dt and len(auth_dt) >= 16:
            try:
                # '2026-03-11T15:13:57-03:00' -> '11/03/26 15:13'
                dt_part = auth_dt[:10]  # 2026-03-11
                tm_part = auth_dt[11:16]  # 15:13
                partes = dt_part.split('-')
                auth_formatada = f'{partes[2]}/{partes[1]}/{partes[0][2:]} {tm_part}'
            except (IndexError, ValueError):
                auth_formatada = auth_dt[:16]

        # Data emissao formatada
        data_emissao = dados.get('cte_data_emissao') or ''
        data_emissao_fmt = ''
        if data_emissao and len(data_emissao) >= 10:
            try:
                partes = data_emissao[:10].split('-')
                data_emissao_fmt = f'{partes[2]}/{partes[1]}/{partes[0]}'
            except (IndexError, ValueError):
                data_emissao_fmt = data_emissao[:10]

        # Previsao entrega formatada (DD/MM/AA)
        prev_entrega = dados.get('previsao_entrega') or ''
        prev_fmt = ''
        if prev_entrega and len(prev_entrega) >= 10:
            try:
                partes = prev_entrega.split('-')
                prev_fmt = f'{partes[2]}/{partes[1]}/{partes[0][2:]}'
            except (IndexError, ValueError):
                prev_fmt = prev_entrega

        # Quantidades carga — extrair especificas para SSW
        qtds = dados.get('quantidades_carga') or []
        qtd_pares = 0
        qtd_volumes = 0
        peso_real = 0.0
        peso_cubado = 0.0
        peso_calculo = 0.0
        for q in qtds:
            tp = (q.get('tipo_medida') or '').upper()
            cu = q.get('codigo_unidade') or ''
            val = q.get('quantidade') or 0
            if cu == '03' or 'UNID' in tp:
                qtd_volumes = val
            elif 'PARES' in tp or 'PAR' in tp:
                qtd_pares = val
            elif cu == '00' or 'M3' in tp:
                peso_cubado = val
            elif 'PESO REAL' in tp or 'PESO BRUTO' in tp:
                peso_real = val
            elif 'PESO BASE' in tp or 'CALCULO' in tp:
                peso_calculo = val
            elif cu == '01':
                # KG generico — usar como peso real se nao preenchido
                if not peso_real:
                    peso_real = val

        # Se peso_calculo nao veio, usar peso_real
        if not peso_calculo:
            peso_calculo = peso_real

        # Componentes frete
        componentes = dados.get('componentes_prestacao') or []
        comps_fmt = []
        for c in componentes:
            comps_fmt.append({
                'nome': c.get('nome') or '-',
                'valor': self._formatar_valor_br(c.get('valor')),
            })

        # NFs referenciadas formatadas
        nfs = dados.get('nfs_referenciadas') or []
        nfs_fmt = []
        for nf in nfs:
            ch = nf.get('chave') or ''
            num_nf = nf.get('numero_nf') or ''
            # Pad numero NF para 9 digitos
            try:
                num_nf_fmt = str(int(num_nf)).zfill(9) if num_nf else ''
            except (ValueError, TypeError):
                num_nf_fmt = num_nf
            nfs_fmt.append({
                'chave': ch,
                'numero_nf': num_nf_fmt,
                'cnpj_emitente': nf.get('cnpj_emitente') or '',
            })

        # Cobrar: forma pagamento
        forma_pgto = dados.get('forma_pagamento') or ''
        cobrar = 'A PRAZO' if forma_pgto == 'A Pagar' else ('PAGO' if forma_pgto == 'Pago' else 'A PRAZO')

        d = {
            # Emitente
            'emit_nome': (dados.get('emitente') or {}).get('nome') or '',
            'emit_cnpj': self._formatar_cnpj((dados.get('emitente') or {}).get('cnpj')),
            'emit_ie': dados.get('ie_emitente') or '',
            'emit_end': self._montar_endereco_inline(end_emit),
            'emit_bairro': end_emit.get('bairro') or '',
            'emit_mun': end_emit.get('municipio') or '',
            'emit_uf': end_emit.get('uf') or '',
            'emit_cep': self._formatar_cep(end_emit.get('cep')),
            'emit_fone': self._formatar_telefone(end_emit.get('fone')),

            # Identificacao CTe
            'serie': dados.get('serie') or '',
            'numero': self._formatar_numero_cte(dados.get('cte_numero')),
            'modal': (dados.get('modal') or 'RODOVIARIO').upper(),
            'modelo': '57',
            'protocolo_numero': prot.get('numero') or '',
            'autorizacao': auth_formatada,
            'folha': '1/1',
            'rntrc': dados.get('rntrc') or '',

            # Tipos
            'tipo_cte': (dados.get('tipo_cte_descricao') or 'Normal').upper(),
            'tipo_servico': (dados.get('tipo_servico') or 'NORMAL').upper(),
            'cfop_natureza': f"{dados.get('cfop') or ''} {dados.get('natureza_operacao') or ''}".strip(),

            # Rota
            'origem': f"{dados.get('cidade_origem') or ''}/{dados.get('uf_origem') or ''}",
            'destino': f"{dados.get('cidade_destino') or ''}/{dados.get('uf_destino') or ''}",
            'emitido_por': '',  # Campo SSW especifico

            # Chave de acesso
            'chave_raw': chave,
            'chave_ssw': self._formatar_chave_ssw(chave),
            'barcode_svg': self._gerar_barcode_svg(chave) if len(chave) == 44 else '',
            'qrcode_base64': self._gerar_qrcode_base64(
                dados.get('qrcode_url') or '', chave
            ),

            # Remetente
            'rem_nome': (dados.get('remetente') or {}).get('nome') or '',
            'rem_cnpj': self._formatar_cnpj((dados.get('remetente') or {}).get('cnpj')),
            'rem_ie': dados.get('ie_remetente') or '',
            'rem_end': self._montar_endereco_inline(end_rem),
            'rem_mun_uf': f"{end_rem.get('municipio') or ''} - {end_rem.get('uf') or ''}",
            'rem_cep': self._formatar_cep(end_rem.get('cep')),
            'rem_fone': self._formatar_telefone(dados.get('fone_remetente') or end_rem.get('fone')),

            # Destinatario
            'dest_nome': (dados.get('destinatario') or {}).get('nome') or '',
            'dest_cnpj': self._formatar_cnpj((dados.get('destinatario') or {}).get('cnpj')),
            'dest_ie': dados.get('ie_destinatario') or '',
            'dest_end': self._montar_endereco_inline(end_dest),
            'dest_mun_uf': f"{end_dest.get('municipio') or ''} - {end_dest.get('uf') or ''}",
            'dest_cep': self._formatar_cep(end_dest.get('cep')),
            'dest_fone': self._formatar_telefone(dados.get('fone_destinatario') or end_dest.get('fone')),
            'dest_suframa': '0',

            # Expedidor
            'exp_nome': (dados.get('expedidor') or {}).get('nome') or '',
            'exp_cnpj': self._formatar_cnpj((dados.get('expedidor') or {}).get('cnpj')),
            'exp_ie': dados.get('ie_expedidor') or '',
            'exp_end': self._montar_endereco_inline(end_exp),
            'exp_mun_uf': f"{end_exp.get('municipio') or ''} - {end_exp.get('uf') or ''}",
            'exp_cep': self._formatar_cep(end_exp.get('cep')),
            'exp_fone': self._formatar_telefone(dados.get('fone_expedidor') or end_exp.get('fone')),

            # Recebedor
            'rec_nome': (dados.get('recebedor') or {}).get('nome') or '',
            'rec_cnpj': self._formatar_cnpj((dados.get('recebedor') or {}).get('cnpj')),
            'rec_ie': dados.get('ie_recebedor') or '',
            'rec_end': self._montar_endereco_inline(end_rec),
            'rec_mun_uf': f"{end_rec.get('municipio') or ''} - {end_rec.get('uf') or ''}",
            'rec_cep': self._formatar_cep(end_rec.get('cep')),
            'rec_fone': self._formatar_telefone(dados.get('fone_recebedor') or end_rec.get('fone')),

            # Tomador
            'toma_abrev': toma_abrev,
            'toma_nome': tomador.get('nome') or '',
            'toma_cnpj': self._formatar_cnpj(tomador.get('cnpj')),
            'toma_ie': tomador.get('ie') or '',

            # Observacoes
            'observacoes': obs_texto,

            # Footer
            'cobrar': cobrar,
            'prev_entrega': prev_fmt,
            'placa': '',  # Nao disponivel no XML
            'nr_placa': '',

            # Componentes frete
            'componentes': comps_fmt,
            'frete_total': self._formatar_valor_br(dados.get('cte_valor')),
            'valor_a_receber': self._formatar_valor_br(dados.get('valor_a_receber') or dados.get('cte_valor')),

            # Mercadoria
            'prod_predominante': (dados.get('produto_predominante') or '')[:15],
            'especie': 'DIVERSOS',
            'valor_mercadoria': self._formatar_valor_br(dados.get('valor_mercadoria')),
            'qtd_pares': str(int(qtd_pares)) if qtd_pares else '0',
            'qtd_volumes': str(int(qtd_volumes)) if qtd_volumes else '0',
            'peso_cubado': self._formatar_peso_br(peso_cubado),
            'peso_real': self._formatar_peso_br(peso_real),
            'peso_calculo': self._formatar_peso_br(peso_calculo),

            # ICMS
            'icms_sit_trib': (dados.get('situacao_tributaria_icms') or '').upper() or 'NORMAL',
            'icms_base': self._formatar_valor_br(impostos.get('base_icms')),
            'icms_aliq_difal': '0,00',
            'icms_aliq': self._formatar_valor_br_2(impostos.get('aliquota_icms')),
            'icms_valor': self._formatar_valor_br(impostos.get('valor_icms')),
            'icms_difal_orig_dest': '0,00',
            'icms_cred_pres': '0,00',

            # IBS/CBS
            'ibs_uf_aliq': self._formatar_valor_br_2(ibscbs.get('ibs_uf_aliquota') if ibscbs else None),
            'ibs_uf_valor': self._formatar_valor_br(ibscbs.get('ibs_uf_valor') if ibscbs else None),
            'ibs_mun_aliq': self._formatar_valor_br_2(ibscbs.get('ibs_mun_aliquota') if ibscbs else None),
            'ibs_mun_valor': self._formatar_valor_br(ibscbs.get('ibs_mun_valor') if ibscbs else None),
            'cbs_aliq': self._formatar_valor_br_2(ibscbs.get('cbs_aliquota') if ibscbs else None),
            'cbs_valor': self._formatar_valor_br(ibscbs.get('cbs_valor') if ibscbs else None),

            # Tributos Lei 12.741
            'trib_icms': self._formatar_valor_br(impostos.get('valor_icms')),
            'trib_pis': self._formatar_valor_br(None),
            'trib_cofins': self._formatar_valor_br(None),
            'trib_total': self._formatar_valor_br(impostos.get('total_tributos')),

            # NFs
            'nfs': nfs_fmt,

            # Data emissao
            'data_emissao': data_emissao_fmt,
        }

        return d

    # ------------------------------------------------------------------
    # Formatadores SSW
    # ------------------------------------------------------------------

    @staticmethod
    def _formatar_chave_ssw(chave: str) -> str:
        """Formata chave de 44 digitos no padrao SSW:
        UF.AAMM.CNPJ(formatado)-MOD-SER-NUM(formatado)-TIPO-COD.NUM-DV

        Ex: 35.2603.62.312.605/0001-75-57-001-000.000.049-1-00.000.050-9
        """
        if not chave or len(chave) != 44:
            return chave or ''

        uf = chave[0:2]         # 35
        aamm = chave[2:6]       # 2603
        cnpj = chave[6:20]      # 62312605000175
        mod = chave[20:22]      # 57
        serie = chave[22:25]    # 001
        numero = chave[25:34]   # 000000049
        tipo = chave[34:35]     # 1
        codigo = chave[35:43]   # 00000050
        dv = chave[43:44]       # 9

        # Formatar CNPJ dentro da chave: XX.XXX.XXX/XXXX-XX
        cnpj_fmt = (
            f'{cnpj[:2]}.{cnpj[2:5]}.{cnpj[5:8]}'
            f'/{cnpj[8:12]}-{cnpj[12:]}'
        )

        # Formatar numero: 000.000.049
        num_fmt = f'{numero[:3]}.{numero[3:6]}.{numero[6:]}'

        # Formatar codigo: 00.000.050
        cod_fmt = f'{codigo[:2]}.{codigo[2:5]}.{codigo[5:]}'

        return f'{uf}.{aamm}.{cnpj_fmt}-{mod}-{serie}-{num_fmt}-{tipo}-{cod_fmt}-{dv}'

    @staticmethod
    def _formatar_cnpj(cnpj: str) -> str:
        """Formata CNPJ: XX.XXX.XXX/XXXX-XX"""
        if not cnpj:
            return ''
        digits = ''.join(c for c in cnpj if c.isdigit())
        if len(digits) == 14:
            return (
                f'{digits[:2]}.{digits[2:5]}.{digits[5:8]}'
                f'/{digits[8:12]}-{digits[12:]}'
            )
        return cnpj

    @staticmethod
    def _formatar_cep(cep: str) -> str:
        """Formata CEP: XXXXX-XXX"""
        if not cep:
            return ''
        digits = ''.join(c for c in cep if c.isdigit())
        if len(digits) == 8:
            return f'{digits[:5]}-{digits[5:]}'
        return cep

    @staticmethod
    def _formatar_telefone(fone: str) -> str:
        """Formata telefone: (XX)XXXX-XXXX ou (XX)XXXXX-XXXX"""
        if not fone:
            return '0'
        digits = ''.join(c for c in fone if c.isdigit())
        if len(digits) == 11:
            return f'({digits[:2]}){digits[2:7]}-{digits[7:]}'
        elif len(digits) == 10:
            return f'({digits[:2]}){digits[2:6]}-{digits[6:]}'
        return fone

    @staticmethod
    def _formatar_numero_cte(numero) -> str:
        """Formata numero CTe com zero-pad 9 digitos: 000000049"""
        if numero is None:
            return ''
        try:
            return str(int(str(numero))).zfill(9)
        except (ValueError, TypeError):
            return str(numero)

    @staticmethod
    def _formatar_valor_br(valor) -> str:
        """Formata valor monetario brasileiro: 1.650,00"""
        if valor is None:
            return '0,00'
        try:
            valor_f = float(valor)
            # Usar locale-independente
            formatado = f'{valor_f:,.2f}'
            # Trocar: 1,650.00 -> 1.650,00
            formatado = formatado.replace(',', 'X').replace('.', ',').replace('X', '.')
            return formatado
        except (ValueError, TypeError):
            return '0,00'

    @staticmethod
    def _formatar_valor_br_2(valor) -> str:
        """Formata valor com 2 decimais: 12,00"""
        if valor is None:
            return '0,00'
        try:
            return f'{float(valor):.2f}'.replace('.', ',')
        except (ValueError, TypeError):
            return '0,00'

    @staticmethod
    def _formatar_peso_br(peso) -> str:
        """Formata peso com 3 decimais brasileiro: 704,000"""
        if not peso:
            return '0,000'
        try:
            formatado = f'{float(peso):,.3f}'
            formatado = formatado.replace(',', 'X').replace('.', ',').replace('X', '.')
            return formatado
        except (ValueError, TypeError):
            return '0,000'

    @staticmethod
    def _montar_endereco_inline(ender: dict) -> str:
        """Monta endereco em linha: RUA X 123 BAIRRO"""
        if not ender:
            return ''
        partes = []
        if ender.get('logradouro'):
            partes.append(ender['logradouro'])
        if ender.get('numero'):
            partes.append(ender['numero'])
        if ender.get('bairro'):
            partes.append(ender['bairro'])
        return ' '.join(partes)

    # ------------------------------------------------------------------
    # Geracao de codigos visuais
    # ------------------------------------------------------------------

    def _gerar_barcode_svg(self, chave_acesso: str) -> str:
        """Gera barcode Code128 como SVG inline."""
        try:
            import barcode
            from barcode.writer import SVGWriter

            code128 = barcode.get('code128', chave_acesso, writer=SVGWriter())
            svg_buffer = BytesIO()
            code128.write(svg_buffer, options={
                'module_width': 0.2,
                'module_height': 8,
                'write_text': False,
                'quiet_zone': 1,
            })
            svg_buffer.seek(0)
            return svg_buffer.read().decode('utf-8')

        except Exception as e:
            logger.warning(f"Erro ao gerar barcode: {e}")
            return ''

    @staticmethod
    def _gerar_qrcode_base64(qrcode_url: str, chave: str) -> str:
        """Gera QR code como base64 PNG para embed no HTML.

        Args:
            qrcode_url: URL do QR code extraida do XML (preferencial)
            chave: Chave de acesso 44 digitos (fallback para gerar URL)

        Returns:
            String 'data:image/png;base64,...' ou '' se erro
        """
        if not qrcode_url and not chave:
            return ''

        url = qrcode_url
        if not url and len(chave) == 44:
            # Gerar URL padrao SEFAZ
            url = (
                f'https://nfe.fazenda.sp.gov.br/CTeConsulta/qrCode'
                f'?chCTe={chave}&tpAmb=1'
            )

        if not url:
            return ''

        try:
            import qrcode

            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_M,
                box_size=3,
                border=1,
            )
            qr.add_data(url)
            qr.make(fit=True)

            img = qr.make_image(fill_color='black', back_color='white')
            buf = BytesIO()
            img.save(buf, format='PNG')
            buf.seek(0)
            b64 = base64.b64encode(buf.getvalue()).decode('utf-8')
            return f'data:image/png;base64,{b64}'

        except Exception as e:
            logger.warning(f"Erro ao gerar QR code: {e}")
            return ''
