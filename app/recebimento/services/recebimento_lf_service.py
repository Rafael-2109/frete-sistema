"""
Service para Recebimento LF (La Famiglia -> Nacom Goya)
========================================================

Responsabilidades:
- Buscar DFes da LF disponiveis no Odoo (NFs de retorno de industrializacao)
- Buscar detalhes de um DFe: linhas separadas por CFOP (manual vs auto)
- Copiar lotes do faturamento da LF para produtos CFOP=1902
- Salvar recebimento local + enqueue job RQ (fire-and-forget)
- Listar recebimentos com status
- Retry de recebimentos com erro

Contexto:
- LF (company_id=5) envia insumos para FB (company_id=1) industrializar
- FB recebe NF de retorno da LF (DFe aparece na company_id=1)
- CFOP=1902: retorno de insumos/embalagens (lotes copiados automaticamente)
- CFOP!=1902: produto acabado (lotes preenchidos pelo usuario)
"""

import logging
from datetime import datetime, timedelta
from decimal import Decimal

from app import db
from app.utils.timezone import agora_utc_naive, agora_utc
from app.utils.database_retry import commit_with_retry
from app.recebimento.models import RecebimentoLf, RecebimentoLfLote
from app.odoo.utils.connection import get_odoo_connection
from app.odoo.utils.dfe_utils import situacao_nf_valida

logger = logging.getLogger(__name__)


class RecebimentoLfService:
    """Service para operacoes de Recebimento LF."""

    # IDs fixos (conforme IDS_FIXOS.md)
    CNPJ_LF = '18.467.441/0001-63'  # Formato Odoo (com pontuacao)
    CNPJ_FB = '61.724.241/0001-78'  # Nacom Goya FB (formato Odoo)
    COMPANY_FB = 1
    COMPANY_LF = 5

    # CFOPs de retorno (insumos/embalagens — auto-fill lote com numero NF)
    CFOPS_RETORNO = ('5902', '1902')

    # Campos do DFe para busca
    CAMPOS_DFE = [
        'id', 'l10n_br_status', 'l10n_br_situacao_dfe',
        'nfe_infnfe_ide_nnf', 'nfe_infnfe_ide_serie',
        'nfe_infnfe_ide_dhemi', 'nfe_infnfe_emit_cnpj',
        'nfe_infnfe_emit_xnome', 'nfe_infnfe_dest_cnpj',
        'nfe_infnfe_total_icmstot_vnf',
        'protnfe_infnfe_chnfe', 'l10n_br_tipo_pedido',
        'l10n_br_data_entrada', 'purchase_id',
    ]

    # Campos das linhas do DFe
    CAMPOS_DFE_LINE = [
        'id', 'dfe_id', 'det_prod_cfop', 'det_prod_cprod',
        'det_prod_xprod', 'det_prod_qcom', 'det_prod_ucom',
        'det_prod_vuncom', 'det_prod_vprod', 'product_id',
    ]

    def buscar_dfes_lf_disponiveis(self, minutos=60, data_inicio=None, data_fim=None):
        """
        Busca DFes + NFs da LF disponiveis para recebimento.

        Combina duas fontes:
        1. DFes na FB (fluxo tradicional — NF ja apareceu na SEFAZ)
        2. NFs emitidas pela LF (fluxo antecipado — NF ainda sem DFe na FB)

        Merge por chave_nfe: NFs da LF que ja tem DFe sao ignoradas (evita duplicata).

        Args:
            minutos: Janela temporal em minutos (default 60). Ignorado se data_inicio/data_fim.
            data_inicio: Data inicio do range (string ISO YYYY-MM-DD). Opcional.
            data_fim: Data fim do range (string ISO YYYY-MM-DD). Opcional.

        Returns:
            Dict com lista de DFes e total
        """
        try:
            odoo = get_odoo_connection()

            # Query UNICA de recebimentos existentes (reusada por _buscar_dfes_fb e merge)
            recebimentos_existentes = RecebimentoLf.query.filter(
                RecebimentoLf.status.in_(['pendente', 'processando', 'processado'])
            ).all()

            # === BUSCA 1: DFes na FB (fluxo tradicional, inalterado) ===
            dfes_fb = self._buscar_dfes_fb(odoo, minutos, data_inicio, data_fim,
                                           recebimentos_existentes=recebimentos_existentes)

            # === BUSCA 2: NFs emitidas pela LF (fluxo antecipado) ===
            nfs_lf = self._buscar_nfs_emitidas_lf(odoo, minutos, data_inicio, data_fim)

            # === MERGE: cross-reference por chave_nfe ===
            chaves_com_dfe = {d['chave_nfe'] for d in dfes_fb if d.get('chave_nfe')}

            # Sets de IDs ja processados (DFe + LF invoice)
            chaves_processadas = {r.chave_nfe for r in recebimentos_existentes if r.chave_nfe}
            lf_invoice_ids_processados = {
                r.odoo_lf_invoice_id for r in recebimentos_existentes
                if r.odoo_lf_invoice_id
            }

            for nf in nfs_lf:
                chave = str(nf.get('l10n_br_chave_nf', '') or '')
                lf_inv_id = nf['id']

                # Pular se DFe ja existe (fluxo normal cobre)
                if chave and chave in chaves_com_dfe:
                    continue

                # Pular se ja processado localmente (por chave ou lf_invoice_id)
                if chave and chave in chaves_processadas:
                    continue
                if lf_inv_id in lf_invoice_ids_processados:
                    continue

                dfes_fb.append({
                    'id': None,  # sem dfe_id
                    'lf_invoice_id': lf_inv_id,
                    'numero_nf': str(nf.get('l10n_br_numero_nota_fiscal', '') or ''),
                    'serie': '',
                    'data_emissao': str(nf.get('invoice_date', '') or ''),
                    'emitente_cnpj': self.CNPJ_LF,
                    'emitente_nome': 'LA FAMIGLIA',
                    'valor_total': nf.get('amount_total', 0),
                    'chave_nfe': chave,
                    'status_dfe': '',
                    'tipo_pedido': '',
                    'tem_po': False,
                    'origem': 'lf_invoice',  # FLAG: NF direto da LF
                })

            return {
                'dfes': dfes_fb,
                'total': len(dfes_fb),
            }

        except Exception as e:
            logger.error(f"Erro ao buscar DFes LF: {e}")
            raise

    def _buscar_dfes_fb(self, odoo, minutos=60, data_inicio=None, data_fim=None,
                        recebimentos_existentes=None):
        """
        Busca DFes na FB emitidos pela LF (fluxo tradicional).

        Extraido de buscar_dfes_lf_disponiveis() para permitir merge com NFs da LF.

        Args:
            odoo: Conexao Odoo ativa
            minutos: Janela temporal em minutos
            data_inicio: Data inicio do range (YYYY-MM-DD)
            data_fim: Data fim do range (YYYY-MM-DD)
            recebimentos_existentes: Lista de RecebimentoLf ja carregados (evita query duplicada).
                Se None, executa query localmente (backward compat).

        Returns:
            Lista de dicts normalizados com DFes disponiveis
        """
        filtro = [
            ['nfe_infnfe_emit_cnpj', '=', self.CNPJ_LF],
            ['company_id', '=', self.COMPANY_FB],
            # NAO filtrar l10n_br_situacao_dfe no domain Odoo:
            # - Campo vazio em ~99% dos DFes (ref: dfe_utils.py:31)
            # - Odoo 'not in' exclui registros NULL → zero resultados
            # - Filtragem feita em Python abaixo via situacao_nf_valida()
        ]

        # Filtro temporal: range de datas OU ultimos N minutos
        if data_inicio and data_fim:
            filtro.append(['nfe_infnfe_ide_dhemi', '>=', f'{data_inicio} 00:00:00'])
            filtro.append(['nfe_infnfe_ide_dhemi', '<=', f'{data_fim} 23:59:59'])
            logger.info(f"Buscando DFes LF no range {data_inicio} a {data_fim}")
        else:
            # CORREÇÃO TIMEZONE: Odoo write_date é UTC → usar agora_utc()
            data_limite = (agora_utc() - timedelta(minutes=minutos)).strftime('%Y-%m-%d %H:%M:%S')
            filtro.append(['write_date', '>=', data_limite])
            logger.info(f"Buscando DFes LF dos ultimos {minutos} minutos (desde {data_limite})")

        dfes_odoo = odoo.execute_kw(
            'l10n_br_ciel_it_account.dfe', 'search_read',
            [filtro],
            {
                'fields': self.CAMPOS_DFE,
                'order': 'nfe_infnfe_ide_dhemi desc',
                'limit': 100,
            }
        )

        if not dfes_odoo:
            return []

        # Filtrar situacao invalida em Python (CANCELADA/INUTILIZADA)
        dfes_odoo = [d for d in dfes_odoo if situacao_nf_valida(d.get('l10n_br_situacao_dfe'))]

        if not dfes_odoo:
            return []

        # Filtrar DFes ja processados localmente
        if recebimentos_existentes is None:
            recebimentos_existentes = RecebimentoLf.query.filter(
                RecebimentoLf.status.in_(['pendente', 'processando', 'processado'])
            ).all()
        dfe_ids_processados = {
            r.odoo_dfe_id for r in recebimentos_existentes if r.odoo_dfe_id
        }

        # Filtrar DFes que ja tem PO vinculado (purchase_id preenchido E status >= 06)
        dfes_disponiveis = []
        for dfe in dfes_odoo:
            dfe_id = dfe['id']

            if dfe_id in dfe_ids_processados:
                continue

            if dfe.get('purchase_id') and dfe.get('l10n_br_status') in ('06', '07'):
                continue

            dfes_disponiveis.append({
                'id': dfe['id'],
                'numero_nf': dfe.get('nfe_infnfe_ide_nnf', ''),
                'serie': dfe.get('nfe_infnfe_ide_serie', ''),
                'data_emissao': dfe.get('nfe_infnfe_ide_dhemi', ''),
                'emitente_cnpj': dfe.get('nfe_infnfe_emit_cnpj', ''),
                'emitente_nome': dfe.get('nfe_infnfe_emit_xnome', ''),
                'valor_total': dfe.get('nfe_infnfe_total_icmstot_vnf', 0),
                'chave_nfe': dfe.get('protnfe_infnfe_chnfe', ''),
                'status_dfe': dfe.get('l10n_br_status', ''),
                'tipo_pedido': dfe.get('l10n_br_tipo_pedido', ''),
                'tem_po': bool(dfe.get('purchase_id')),
                'origem': 'dfe',  # DFe tradicional
            })

        return dfes_disponiveis

    def _buscar_nfs_emitidas_lf(self, odoo, minutos=60, data_inicio=None, data_fim=None):
        """
        Busca NFs emitidas pela LF (account.move) autorizadas pela SEFAZ.

        Complementa _buscar_dfes_fb() para NFs que ainda nao apareceram
        no DFe da FB (atraso SEFAZ de ate 2h).

        Busca account.move na company LF onde partner_id = Nacom Goya FB.

        Args:
            odoo: Conexao Odoo ativa
            minutos: Janela temporal em minutos
            data_inicio: Data inicio do range (YYYY-MM-DD)
            data_fim: Data fim do range (YYYY-MM-DD)

        Returns:
            Lista de dicts do account.move da LF
        """
        try:
            # 1. Descobrir partner_id do Nacom Goya FB no Odoo da LF
            fb_partners = odoo.execute_kw('res.partner', 'search', [[
                ['company_id', 'in', [self.COMPANY_LF, False]],
                ['l10n_br_cnpj_cpf', '=', self.CNPJ_FB],
            ]], {'limit': 1})

            if not fb_partners:
                # Fallback: tentar campo vat
                fb_partners = odoo.execute_kw('res.partner', 'search', [[
                    ['company_id', 'in', [self.COMPANY_LF, False]],
                    ['vat', 'ilike', '61724241'],
                ]], {'limit': 1})

            if not fb_partners:
                logger.warning("Partner Nacom Goya FB nao encontrado na LF (partner search)")
                return []

            fb_partner_id = fb_partners[0]

            # 2. Filtro base: NFs da LF -> FB autorizadas
            filtro = [
                ['company_id', '=', self.COMPANY_LF],
                ['partner_id', '=', fb_partner_id],
                ['move_type', 'in', ['out_invoice', 'out_refund']],
                ['l10n_br_situacao_nf', '=', 'autorizado'],
                ['l10n_br_chave_nf', '!=', False],
            ]

            # Filtro temporal
            if data_inicio and data_fim:
                filtro.append(['invoice_date', '>=', data_inicio])
                filtro.append(['invoice_date', '<=', data_fim])
            else:
                # CORREÇÃO TIMEZONE: Odoo write_date é UTC → usar agora_utc()
                data_limite = (agora_utc() - timedelta(minutes=minutos)).strftime('%Y-%m-%d %H:%M:%S')
                filtro.append(['write_date', '>=', data_limite])

            # 3. Campos a buscar
            campos = [
                'id', 'name', 'l10n_br_numero_nota_fiscal',
                'l10n_br_chave_nf', 'invoice_date', 'amount_total',
                'l10n_br_situacao_nf', 'partner_id',
            ]

            nfs = odoo.execute_kw(
                'account.move', 'search_read',
                [filtro],
                {'fields': campos, 'order': 'invoice_date desc', 'limit': 100}
            )

            logger.info(f"NFs emitidas pela LF encontradas: {len(nfs)}")
            return nfs

        except Exception as e:
            logger.warning(f"Erro ao buscar NFs emitidas pela LF: {e}")
            return []

    def buscar_detalhes_dfe(self, dfe_id):
        """
        Busca detalhes de um DFe + suas linhas, separando por CFOP.

        Para CFOP=1902: busca lotes do faturamento da LF no Odoo.
        Para CFOP!=1902: retorna para preenchimento manual pelo usuario.

        Args:
            dfe_id: ID do DFe no Odoo

        Returns:
            Dict com info_dfe, linhas_manuais (CFOP!=1902), linhas_auto (CFOP=1902)
        """
        try:
            odoo = get_odoo_connection()

            # 1. Buscar DFe
            dfe = odoo.execute_kw(
                'l10n_br_ciel_it_account.dfe', 'search_read',
                [[['id', '=', dfe_id]]],
                {'fields': self.CAMPOS_DFE, 'limit': 1}
            )

            if not dfe:
                raise ValueError(f"DFe {dfe_id} nao encontrado no Odoo")

            dfe = dfe[0]

            # 2. Buscar linhas do DFe (GOTCHA: lines_ids NAO existe no dfe,
            #    buscar via l10n_br_ciel_it_account.dfe.line com filtro dfe_id)
            linhas = odoo.execute_kw(
                'l10n_br_ciel_it_account.dfe.line', 'search_read',
                [[['dfe_id', '=', dfe_id]]],
                {'fields': self.CAMPOS_DFE_LINE}
            )

            # 3. Separar por CFOP
            # CFOP 5902 (emissor) = 1902 (receptor): retorno de insumos/embalagens
            # O DFe contem o CFOP do emissor (LF), por isso checamos 5902
            CFOPS_RETORNO = ('5902', '1902')
            linhas_manuais = []  # CFOP != 5902/1902 (produto acabado)
            linhas_auto = []     # CFOP = 5902/1902 (insumos — lotes auto)

            for linha in linhas:
                cfop = str(linha.get('det_prod_cfop', '')).strip()
                product_id = linha['product_id'][0] if linha.get('product_id') else None

                item = {
                    'dfe_line_id': linha['id'],
                    'cfop': cfop,
                    'cod_produto': linha.get('det_prod_cprod', ''),
                    'nome_produto': linha.get('det_prod_xprod', ''),
                    'quantidade': Decimal(str(linha.get('det_prod_qcom', 0) or 0)),
                    'unidade': linha.get('det_prod_ucom', ''),
                    'valor_unitario': Decimal(str(linha.get('det_prod_vuncom', 0) or 0)),
                    'valor_total': Decimal(str(linha.get('det_prod_vprod', 0) or 0)),
                    'product_id': product_id,
                }

                if cfop in CFOPS_RETORNO:
                    linhas_auto.append(item)
                else:
                    linhas_manuais.append(item)

            # 4. Para linhas_auto (CFOP 5902/1902): lote = numero da NF
            # Componentes/insumos nao tem lote proprio no picking da LF;
            # convencao: usar numero da NF como identificador de lote
            numero_nf = dfe.get('nfe_infnfe_ide_nnf', '')
            for item in linhas_auto:
                item['lote_nome'] = numero_nf
                item['data_validade'] = None
                item['lote_origem'] = 'numero_nf'

            # 5. Montar retorno
            info_dfe = {
                'id': dfe['id'],
                'numero_nf': dfe.get('nfe_infnfe_ide_nnf', ''),
                'serie': dfe.get('nfe_infnfe_ide_serie', ''),
                'data_emissao': dfe.get('nfe_infnfe_ide_dhemi', ''),
                'emitente_cnpj': dfe.get('nfe_infnfe_emit_cnpj', ''),
                'emitente_nome': dfe.get('nfe_infnfe_emit_xnome', ''),
                'valor_total': dfe.get('nfe_infnfe_total_icmstot_vnf', 0),
                'chave_nfe': dfe.get('protnfe_infnfe_chnfe', ''),
                'status_dfe': dfe.get('l10n_br_status', ''),
                'origem': 'dfe',
            }

            return {
                'info_dfe': info_dfe,
                'linhas_manuais': linhas_manuais,
                'linhas_auto': linhas_auto,
                'total_linhas': len(linhas),
                'total_manuais': len(linhas_manuais),
                'total_auto': len(linhas_auto),
            }

        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Erro ao buscar detalhes DFe {dfe_id}: {e}")
            raise

    def buscar_detalhes_lf_invoice(self, lf_invoice_id):
        """
        Busca detalhes de uma NF emitida pela LF via parsing do XML autorizado.

        Usado quando o usuario clica numa NF de origem LF (sem DFe na FB).
        Retorna no MESMO formato que buscar_detalhes_dfe() para compatibilidade.

        Args:
            lf_invoice_id: ID do account.move na LF (company_id=5)

        Returns:
            Dict com info_dfe, linhas_manuais, linhas_auto
        """
        try:
            odoo = get_odoo_connection()

            # 1. Buscar invoice da LF com XML
            inv = odoo.execute_kw(
                'account.move', 'read',
                [[lf_invoice_id]],
                {'fields': [
                    'id', 'name', 'l10n_br_numero_nota_fiscal',
                    'l10n_br_chave_nf', 'invoice_date', 'amount_total',
                    'l10n_br_xml_aut_nfe', 'l10n_br_situacao_nf',
                    'partner_id',
                ]}
            )
            if not inv:
                raise ValueError(f"Invoice LF {lf_invoice_id} nao encontrada")
            inv = inv[0]

            xml_b64 = inv.get('l10n_br_xml_aut_nfe')
            if not xml_b64:
                raise ValueError(f"Invoice LF {lf_invoice_id} sem XML autorizado")

            # 2. Parse XML NF-e -> extrair linhas
            linhas = self._parse_nfe_xml_lines(xml_b64)

            # 3. Mapear cProd -> product_id no Odoo
            linhas = self._mapear_produtos_xml(odoo, linhas)

            # 4. Separar por CFOP (1902/5902 = auto, resto = manual)
            linhas_auto = []
            linhas_manuais = []
            for linha in linhas:
                cfop = str(linha.get('cfop', ''))
                item = {
                    'dfe_line_id': None,  # sem dfe_line_id (vem do XML)
                    'cfop': cfop,
                    'cod_produto': linha.get('cProd', ''),
                    'nome_produto': linha.get('product_name', linha.get('xProd', '')),
                    'quantidade': linha.get('qCom', 0),
                    'unidade': linha.get('uCom', ''),
                    'valor_unitario': linha.get('vUnCom', 0),
                    'valor_total': linha.get('vProd', 0),
                    'product_id': linha.get('product_id'),
                }

                if cfop in self.CFOPS_RETORNO:
                    linhas_auto.append(item)
                else:
                    linhas_manuais.append(item)

            # 5. Para linhas auto: lote = numero da NF
            numero_nf = str(inv.get('l10n_br_numero_nota_fiscal', '') or '')
            for item in linhas_auto:
                item['lote_nome'] = numero_nf
                item['data_validade'] = None
                item['lote_origem'] = 'numero_nf'

            # 6. Tentar buscar lotes do faturamento LF (pode ter dados melhores)
            if linhas_auto and numero_nf:
                lotes_lf = self._buscar_lotes_faturamento_lf(odoo, numero_nf)
                for item in linhas_auto:
                    pid = item.get('product_id')
                    if pid and pid in lotes_lf:
                        lote_info = lotes_lf[pid]
                        item['lote_nome'] = lote_info.get('lote_nome', numero_nf)
                        item['data_validade'] = lote_info.get('data_validade')
                        item['lote_origem'] = 'faturamento_lf'

            # 7. Retornar no MESMO formato que buscar_detalhes_dfe()
            info_dfe = {
                'id': None,  # sem dfe_id
                'lf_invoice_id': lf_invoice_id,
                'numero_nf': numero_nf,
                'serie': '',
                'data_emissao': str(inv.get('invoice_date', '') or ''),
                'emitente_cnpj': self.CNPJ_LF,
                'emitente_nome': 'LA FAMIGLIA',
                'valor_total': inv.get('amount_total', 0),
                'chave_nfe': str(inv.get('l10n_br_chave_nf', '') or ''),
                'status_dfe': '',
                'origem': 'lf_invoice',
            }

            return {
                'info_dfe': info_dfe,
                'linhas_manuais': linhas_manuais,
                'linhas_auto': linhas_auto,
                'total_linhas': len(linhas),
                'total_manuais': len(linhas_manuais),
                'total_auto': len(linhas_auto),
            }

        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Erro ao buscar detalhes LF invoice {lf_invoice_id}: {e}")
            raise

    def _parse_nfe_xml_lines(self, xml_b64):
        """
        Parse XML NF-e autorizado -> lista de linhas com CFOP, produto, qtd.

        Args:
            xml_b64: XML em base64 (campo l10n_br_xml_aut_nfe do Odoo)

        Returns:
            Lista de dicts com nItem, cProd, xProd, cfop, uCom, qCom, vUnCom, vProd
        """
        import base64
        import xml.etree.ElementTree as ET

        xml_bytes = base64.b64decode(xml_b64)
        root = ET.fromstring(xml_bytes)

        # Namespace NF-e
        ns = {'nfe': 'http://www.portalfiscal.inf.br/nfe'}
        linhas = []

        for det in root.findall('.//nfe:det', ns):
            prod = det.find('nfe:prod', ns)
            if prod is None:
                continue
            linhas.append({
                'nItem': det.get('nItem'),
                'cProd': prod.findtext('nfe:cProd', '', ns),
                'xProd': prod.findtext('nfe:xProd', '', ns),
                'cfop': prod.findtext('nfe:CFOP', '', ns),
                'uCom': prod.findtext('nfe:uCom', '', ns),
                'qCom': float(prod.findtext('nfe:qCom', '0', ns)),
                'vUnCom': float(prod.findtext('nfe:vUnCom', '0', ns)),
                'vProd': float(prod.findtext('nfe:vProd', '0', ns)),
                'product_id': None,  # preenchido em _mapear_produtos_xml
            })

        return linhas

    def _mapear_produtos_xml(self, odoo, linhas):
        """
        Mapeia cProd (codigo interno LF) -> product_id no Odoo.

        Busca product.product por default_code (batch) nas companies LF e FB.

        Args:
            odoo: Conexao Odoo ativa
            linhas: Lista de linhas do XML (retorno de _parse_nfe_xml_lines)

        Returns:
            Lista de linhas com product_id e product_name preenchidos
        """
        codigos = list({l['cProd'] for l in linhas if l.get('cProd')})
        if not codigos:
            return linhas

        # Buscar produtos por default_code (batch)
        produtos = odoo.execute_kw('product.product', 'search_read', [[
            ['default_code', 'in', codigos],
            ['company_id', 'in', [self.COMPANY_LF, self.COMPANY_FB, False]],
        ]], {'fields': ['id', 'default_code', 'name']})

        mapa = {}
        for p in produtos:
            code = p.get('default_code')
            if code and code not in mapa:
                mapa[code] = {'id': p['id'], 'name': p.get('name', '')}

        for linha in linhas:
            prod = mapa.get(linha.get('cProd'))
            if prod:
                linha['product_id'] = prod['id']
                linha['product_name'] = prod['name']
            else:
                linha['product_name'] = linha.get('xProd', '')

        return linhas

    def _buscar_lotes_faturamento_lf(self, odoo, numero_nf):
        """
        Busca lotes do faturamento da LF no Odoo.

        A NF emitida pela LF (company_id=5) contem as move lines com lote
        no picking de saida. Buscamos via account.move (fatura de venda da LF)
        e depois stock.move.line (picking de saida associado).

        Args:
            odoo: Conexao Odoo ativa
            numero_nf: Numero da NF emitida pela LF

        Returns:
            Dict[product_id] -> {lote_nome, quantidade, data_validade}
        """
        try:
            # 1. Buscar account.move da LF pelo numero da NF
            invoices = odoo.execute_kw(
                'account.move', 'search_read',
                [[
                    ['company_id', '=', self.COMPANY_LF],
                    ['l10n_br_numero_nota_fiscal', '=', numero_nf],
                    ['move_type', 'in', ['out_invoice', 'out_refund']],
                ]],
                {
                    'fields': ['id', 'name', 'invoice_line_ids', 'stock_move_id'],
                    'limit': 5,
                }
            )

            if not invoices:
                logger.warning(f"Nenhuma fatura da LF encontrada para NF {numero_nf}")
                return {}

            # 2. Para cada invoice, buscar as move lines do picking de saida
            #    (stock.picking ligado ao sale.order da LF)
            lotes_por_produto = {}

            for invoice in invoices:
                # Buscar stock.picking associado (via origin da invoice ou sale_id)
                # Alternativa: buscar stock.move.line com reference ao invoice
                invoice_id = invoice['id']

                # Buscar delivery (stock.picking) via invoice -> sale.order -> picking
                # Ou buscar diretamente as move lines com lot_id
                pickings = odoo.execute_kw(
                    'stock.picking', 'search_read',
                    [[
                        ['company_id', '=', self.COMPANY_LF],
                        ['picking_type_code', '=', 'outgoing'],
                        ['state', '=', 'done'],
                        ['origin', 'ilike', numero_nf],
                    ]],
                    {
                        'fields': ['id', 'name', 'move_line_ids'],
                        'limit': 5,
                    }
                )

                if not pickings:
                    # Fallback: buscar pickings recentes (ultimos 30 dias)
                    # CORREÇÃO TIMEZONE: Odoo date_done é UTC → usar agora_utc()
                    data_limite = (agora_utc() - timedelta(days=30)).strftime('%Y-%m-%d')
                    pickings = odoo.execute_kw(
                        'stock.picking', 'search_read',
                        [[
                            ['company_id', '=', self.COMPANY_LF],
                            ['picking_type_code', '=', 'outgoing'],
                            ['state', '=', 'done'],
                            ['date_done', '>=', data_limite],
                        ]],
                        {
                            'fields': ['id', 'name', 'move_line_ids'],
                            'limit': 5,
                            'order': 'date_done desc',
                        }
                    )

                for picking in pickings:
                    if not picking.get('move_line_ids'):
                        continue

                    # Buscar move lines com lot_id
                    move_lines = odoo.execute_kw(
                        'stock.move.line', 'search_read',
                        [[
                            ['picking_id', '=', picking['id']],
                            ['lot_id', '!=', False],
                        ]],
                        {
                            'fields': ['id', 'product_id', 'lot_id', 'quantity',
                                       'lot_name'],
                        }
                    )

                    # Coletar move_lines com lot_id para batch
                    lot_ids_to_fetch = []
                    for ml in move_lines:
                        if ml.get('lot_id'):
                            lid = ml['lot_id'][0] if isinstance(ml['lot_id'], (list, tuple)) else ml['lot_id']
                            lot_ids_to_fetch.append(lid)

                    # Batch read de stock.lot
                    lots_data = {}
                    if lot_ids_to_fetch:
                        try:
                            lots = odoo.execute_kw(
                                'stock.lot', 'read',
                                [list(set(lot_ids_to_fetch))],
                                {'fields': ['id', 'name', 'expiration_date']}
                            )
                            lots_data = {l['id']: l for l in lots}
                        except Exception as e_lot:
                            logger.warning(f"Erro ao buscar lotes batch: {e_lot}")

                    for ml in move_lines:
                        pid = ml['product_id'][0] if ml.get('product_id') else None
                        if not pid:
                            continue

                        lot_name = ''
                        data_validade = None
                        if ml.get('lot_id'):
                            lot_id = ml['lot_id'][0] if isinstance(ml['lot_id'], (list, tuple)) else ml['lot_id']
                            lot_name = ml['lot_id'][1] if isinstance(ml['lot_id'], (list, tuple)) else ''

                            # Usar dados do batch
                            if lot_id in lots_data:
                                lot_name = lots_data[lot_id].get('name', lot_name)
                                data_validade = lots_data[lot_id].get('expiration_date')

                        if pid not in lotes_por_produto:
                            lotes_por_produto[pid] = {
                                'lote_nome': lot_name,
                                'quantidade': float(ml.get('quantity', 0)),
                                'data_validade': data_validade,
                            }
                        else:
                            existing = lotes_por_produto[pid]
                            existing['quantidade'] += float(ml.get('quantity', 0))

            return lotes_por_produto

        except Exception as e:
            logger.error(f"Erro ao buscar lotes do faturamento LF (NF {numero_nf}): {e}")
            return {}

    def salvar_recebimento(self, dados, usuario='sistema'):
        """
        Salva RecebimentoLf + lotes localmente e enfileira job RQ.

        Aceita dois fluxos:
        - Fluxo DFe: dfe_id obrigatorio (NF ja tem DFe na FB)
        - Fluxo antecipado: lf_invoice_id obrigatorio, dfe_id=None (NF sem DFe)

        Args:
            dados: Dict com:
                - dfe_id (ou None), lf_invoice_id (ou None)
                - numero_nf, chave_nfe, cnpj_emitente
                - lotes_manuais: [{product_id, product_name, dfe_line_id,
                                  cfop, lote_nome, quantidade, data_validade}]
                - lotes_auto: [{product_id, product_name, dfe_line_id,
                               cfop, lote_nome, quantidade, data_validade}]
            usuario: Nome do usuario

        Returns:
            RecebimentoLf salvo com job_id
        """
        try:
            dfe_id = dados.get('dfe_id')
            lf_invoice_id = dados.get('lf_invoice_id')

            if not dfe_id and not lf_invoice_id:
                raise ValueError('dfe_id ou lf_invoice_id obrigatorio')

            # Check duplicata por DFe
            if dfe_id:
                existente = RecebimentoLf.query.filter(
                    RecebimentoLf.odoo_dfe_id == dfe_id,
                    RecebimentoLf.status.in_(['pendente', 'processando'])
                ).first()
                if existente:
                    raise ValueError(
                        f"DFe {dfe_id} ja possui recebimento em andamento "
                        f"(ID={existente.id}, status={existente.status})"
                    )

            # Check duplicata por LF invoice
            if lf_invoice_id:
                existente = RecebimentoLf.query.filter(
                    RecebimentoLf.odoo_lf_invoice_id == lf_invoice_id,
                    RecebimentoLf.status.in_(['pendente', 'processando'])
                ).first()
                if existente:
                    raise ValueError(
                        f"NF LF {lf_invoice_id} ja em processamento "
                        f"(ID={existente.id}, status={existente.status})"
                    )

            # Check duplicata por chave_nfe (abrange ambos os cenarios)
            chave = dados.get('chave_nfe')
            if chave:
                existente = RecebimentoLf.query.filter(
                    RecebimentoLf.chave_nfe == chave,
                    RecebimentoLf.status.in_(['pendente', 'processando'])
                ).first()
                if existente:
                    raise ValueError(
                        f"NF com chave {chave[:20]}... ja em processamento "
                        f"(ID={existente.id}, status={existente.status})"
                    )

            # Criar RecebimentoLf
            recebimento = RecebimentoLf(
                odoo_dfe_id=dfe_id,                    # None para fluxo antecipado
                odoo_lf_invoice_id=lf_invoice_id,      # NOVO: invoice da LF
                numero_nf=dados.get('numero_nf'),
                chave_nfe=chave,
                cnpj_emitente=dados.get('cnpj_emitente', self.CNPJ_LF),
                company_id=self.COMPANY_FB,
                status='pendente',
                usuario=usuario,
            )
            db.session.add(recebimento)
            db.session.flush()  # Obter ID

            # Salvar lotes manuais (CFOP!=1902)
            for lote_data in dados.get('lotes_manuais', []):
                lote = RecebimentoLfLote(
                    recebimento_lf_id=recebimento.id,
                    odoo_product_id=lote_data['product_id'],
                    odoo_product_name=lote_data.get('product_name', ''),
                    odoo_dfe_line_id=lote_data.get('dfe_line_id'),
                    cfop=lote_data.get('cfop', ''),
                    tipo='manual',
                    lote_nome=lote_data.get('lote_nome', ''),
                    quantidade=lote_data['quantidade'],
                    data_validade=self._parse_data(lote_data.get('data_validade')),
                    produto_tracking=lote_data.get('produto_tracking', 'lot'),
                )
                db.session.add(lote)

            # Salvar lotes auto (CFOP=1902)
            for lote_data in dados.get('lotes_auto', []):
                lote = RecebimentoLfLote(
                    recebimento_lf_id=recebimento.id,
                    odoo_product_id=lote_data['product_id'],
                    odoo_product_name=lote_data.get('product_name', ''),
                    odoo_dfe_line_id=lote_data.get('dfe_line_id'),
                    cfop=lote_data.get('cfop', '5902'),
                    tipo='auto',
                    lote_nome=lote_data.get('lote_nome', ''),
                    quantidade=lote_data['quantidade'],
                    data_validade=self._parse_data(lote_data.get('data_validade')),
                    produto_tracking=lote_data.get('produto_tracking', 'lot'),
                )
                db.session.add(lote)

            commit_with_retry(db.session)

            # Enfileirar job RQ (fire-and-forget) com retry automatico
            try:
                from app.recebimento.workers.recebimento_lf_jobs import processar_recebimento_lf_job
                from app.portal.workers import enqueue_job
                from rq import Retry

                retry_config = Retry(max=3, interval=[30, 120, 480])

                job = enqueue_job(
                    processar_recebimento_lf_job,
                    recebimento.id,
                    usuario,
                    queue_name='recebimento',
                    timeout='45m',
                    retry=retry_config,
                )
                recebimento.job_id = job.id
                commit_with_retry(db.session)
                logger.info(f"Job RQ enfileirado: {job.id} para recebimento LF {recebimento.id}")
            except Exception as e_job:
                logger.warning(
                    f"Nao foi possivel enfileirar job RQ: {e_job}. "
                    f"Recebimento LF {recebimento.id} fica 'pendente' para retry manual."
                )

            origem = f"DFe {recebimento.odoo_dfe_id}" if recebimento.odoo_dfe_id else f"LF Invoice {recebimento.odoo_lf_invoice_id}"
            logger.info(
                f"Recebimento LF {recebimento.id} salvo para {origem} "
                f"(NF {recebimento.numero_nf})"
            )

            return recebimento

        except ValueError:
            raise
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao salvar recebimento LF: {e}")
            raise

    def listar_recebimentos(self, status=None, limit=50):
        """
        Lista recebimentos LF com filtros.

        Args:
            status: Filtrar por status (pendente, processando, processado, erro)
            limit: Limite de resultados

        Returns:
            Lista de dicts serializados
        """
        try:
            query = RecebimentoLf.query

            if status:
                query = query.filter(RecebimentoLf.status == status)

            query = query.order_by(RecebimentoLf.criado_em.desc())
            query = query.limit(limit)

            recebimentos = query.all()
            return [r.to_dict() for r in recebimentos]

        except Exception as e:
            logger.error(f"Erro ao listar recebimentos LF: {e}")
            raise

    def retry_recebimento(self, recebimento_id):
        """
        Retry de recebimento LF com erro.

        Args:
            recebimento_id: ID do RecebimentoLf

        Returns:
            RecebimentoLf re-enfileirado
        """
        try:
            recebimento = RecebimentoLf.query.get(recebimento_id)
            if not recebimento:
                raise ValueError(f"Recebimento LF {recebimento_id} nao encontrado")

            if recebimento.status != 'erro':
                raise ValueError(
                    f"Recebimento LF {recebimento_id} nao esta com erro "
                    f"(status={recebimento.status})"
                )

            if recebimento.tentativas >= recebimento.max_tentativas:
                raise ValueError(
                    f"Recebimento LF {recebimento_id} atingiu maximo de tentativas "
                    f"({recebimento.max_tentativas})"
                )

            # Re-enfileirar
            recebimento.status = 'pendente'
            recebimento.erro_mensagem = None
            commit_with_retry(db.session)

            from app.recebimento.workers.recebimento_lf_jobs import processar_recebimento_lf_job
            from app.portal.workers import enqueue_job
            from rq import Retry

            retry_config = Retry(max=3, interval=[30, 120, 480])

            job = enqueue_job(
                processar_recebimento_lf_job,
                recebimento.id,
                recebimento.usuario,
                queue_name='recebimento',
                timeout='45m',
                retry=retry_config,
            )
            recebimento.job_id = job.id
            commit_with_retry(db.session)

            logger.info(f"Retry: Job RQ {job.id} para recebimento LF {recebimento.id}")
            return recebimento

        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Erro ao retry recebimento LF {recebimento_id}: {e}")
            raise

    def retry_transfer(self, recebimento_id):
        """
        Retry apenas da fase de transferencia FB -> CD (etapas 19-26).

        Requisitos:
        - Recebimento deve estar com status='processado' (FB OK)
        - transfer_status deve ser 'erro'

        Args:
            recebimento_id: ID do RecebimentoLf

        Returns:
            RecebimentoLf re-enfileirado
        """
        try:
            recebimento = RecebimentoLf.query.get(recebimento_id)
            if not recebimento:
                raise ValueError(f"Recebimento LF {recebimento_id} nao encontrado")

            if recebimento.status != 'processado':
                raise ValueError(
                    f"Recebimento LF {recebimento_id} nao esta processado "
                    f"(status={recebimento.status}). "
                    "Retry transfer so e possivel apos FB concluir."
                )

            if recebimento.transfer_status not in ('erro', None, 'pendente'):
                raise ValueError(
                    f"Transfer status atual: {recebimento.transfer_status}. "
                    "Retry so e possivel quando transfer_status='erro'."
                )

            # Reset transfer
            recebimento.transfer_status = 'pendente'
            recebimento.transfer_erro_mensagem = None
            # Reset etapa para 18 (antes da fase 6)
            if recebimento.etapa_atual >= 19:
                recebimento.etapa_atual = 18
            commit_with_retry(db.session)

            from app.recebimento.workers.recebimento_lf_jobs import processar_transfer_fb_cd_job
            from app.portal.workers import enqueue_job
            from rq import Retry

            retry_config = Retry(max=2, interval=[30, 120])

            job = enqueue_job(
                processar_transfer_fb_cd_job,
                recebimento.id,
                queue_name='recebimento',
                timeout='45m',
                retry=retry_config,
            )
            recebimento.job_id = job.id
            commit_with_retry(db.session)

            logger.info(
                f"Retry transfer: Job RQ {job.id} para recebimento LF {recebimento.id}"
            )
            return recebimento

        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Erro ao retry transfer {recebimento_id}: {e}")
            raise

    def _parse_data(self, data_str):
        """
        Parse de data no formato DD/MM/YYYY ou YYYY-MM-DD para date.

        Args:
            data_str: String de data ou None

        Returns:
            date ou None
        """
        if not data_str:
            return None

        from datetime import date

        if isinstance(data_str, date):
            return data_str

        for fmt in ('%d/%m/%Y', '%Y-%m-%d'):
            try:
                return datetime.strptime(str(data_str), fmt).date()
            except ValueError:
                continue

        logger.warning(f"Formato de data nao reconhecido: {data_str}")
        return None
