"""
Service de Validacao NF x PO - FASE 2
=====================================

Valida e faz match entre NF-e (DFE) e Pedidos de Compra (PO).

Fluxo de Validacao:
1. NF chega SEM vinculo com PO
2. Para cada item da NF:
   a) Buscar De-Para (codigo fornecedor -> interno)
   b) Converter quantidade e preco usando fator de conversao
   c) Buscar POs candidatos do fornecedor com saldo
3. Validar cada PO candidato:
   - Preco: 0% tolerancia (exato)
   - Data: +/- 2 dias uteis
   - Quantidade: NF <= PO + 10%
4. Verificar MATCH COMPLETO:
   - Se 100% itens OK -> APROVAR (consolidar POs)
   - Se <100% itens OK -> BLOQUEAR (nao mexer em nenhum PO)

Regras de Negocio:
- Match deve ser 100% para executar qualquer acao nos POs
- PO principal: o de MAIOR VALOR TOTAL
- QTD NF > QTD PO: tolerancia +10%
- QTD NF < QTD PO: ajustar PO + criar PO saldo
- Preco divergente: BLOQUEIA
- Data fora tolerancia: BLOQUEIA

Referencia: .claude/plans/wiggly-plotting-newt.md
"""

import logging
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Any, Optional
from datetime import datetime, date
from collections import defaultdict

from app import db
from app.recebimento.models import (
    ProdutoFornecedorDepara,
    ValidacaoNfPoDfe,
    MatchNfPoItem,
    DivergenciaNfPo
)
from app.recebimento.services.depara_service import DeparaService
from app.odoo.utils.connection import get_odoo_connection

logger = logging.getLogger(__name__)


# Tolerancias de validacao
TOLERANCIA_QTD_PERCENTUAL = Decimal('10.0')  # 10% para cima
TOLERANCIA_DATA_DIAS_UTEIS = 2               # +/- 2 dias uteis
TOLERANCIA_PRECO_PERCENTUAL = Decimal('0.0') # 0% (exato)


class ValidacaoNfPoService:
    """
    Service para validacao de NF-e vs Pedidos de Compra.
    Identifica POs compativeis e faz match item a item.
    """

    def __init__(self):
        self.depara_service = DeparaService()

    # =========================================================================
    # MAIN VALIDATION FLOW
    # =========================================================================

    def validar_dfe(self, odoo_dfe_id: int) -> Dict[str, Any]:
        """
        Executa validacao completa de um DFE (NF-e) contra POs.

        FLUXO:
        1. Buscar dados do DFE e suas linhas
        2. Para cada linha, converter codigo/UM usando De-Para
        3. Buscar POs candidatos para cada item
        4. Validar match (preco, data, quantidade)
        5. Se 100% match -> retornar para consolidacao
        6. Se <100% match -> registrar divergencias

        Args:
            odoo_dfe_id: ID do DFE no Odoo

        Returns:
            Dict com resultado da validacao:
            - status: 'aprovado', 'bloqueado', 'erro'
            - itens_match: quantidade de itens com match
            - itens_total: total de itens
            - divergencias: lista de divergencias
            - pos_para_consolidar: lista de POs se aprovado
        """
        try:
            logger.info(f"Iniciando validacao NF x PO do DFE {odoo_dfe_id}")

            # Criar ou atualizar registro de validacao
            validacao = self._get_or_create_validacao(odoo_dfe_id)
            validacao.status = 'validando'
            db.session.commit()

            # Buscar dados do DFE
            dfe_data = self._buscar_dfe(odoo_dfe_id)
            if not dfe_data:
                validacao.status = 'erro'
                validacao.erro_mensagem = f'DFE {odoo_dfe_id} nao encontrado no Odoo'
                db.session.commit()
                return {'status': 'erro', 'mensagem': validacao.erro_mensagem}

            # Atualizar dados basicos da validacao
            self._atualizar_validacao_com_dfe(validacao, dfe_data)

            # Buscar linhas do DFE
            dfe_lines = self._buscar_dfe_lines(odoo_dfe_id)
            if not dfe_lines:
                validacao.status = 'erro'
                validacao.erro_mensagem = f'DFE {odoo_dfe_id} nao tem linhas'
                db.session.commit()
                return {'status': 'erro', 'mensagem': validacao.erro_mensagem}

            validacao.total_itens = len(dfe_lines)

            # Limpar matches/divergencias anteriores
            MatchNfPoItem.query.filter_by(validacao_id=validacao.id).delete()
            DivergenciaNfPo.query.filter_by(validacao_id=validacao.id).delete()

            # ETAPA 1: Converter todos os itens
            itens_convertidos = []
            itens_sem_depara = []

            for line in dfe_lines:
                conversao = self._converter_item_dfe(line, dfe_data)
                if conversao['tem_depara']:
                    itens_convertidos.append(conversao)
                else:
                    itens_sem_depara.append(conversao)

            # Se algum item nao tem De-Para, ja bloqueia
            if itens_sem_depara:
                self._registrar_divergencias_sem_depara(
                    validacao, itens_sem_depara, dfe_data
                )
                validacao.status = 'bloqueado'
                validacao.itens_sem_depara = len(itens_sem_depara)
                validacao.atualizado_em = datetime.utcnow()
                db.session.commit()

                return {
                    'status': 'bloqueado',
                    'mensagem': f'{len(itens_sem_depara)} item(ns) sem De-Para',
                    'itens_sem_depara': len(itens_sem_depara),
                    'total_itens': len(dfe_lines)
                }

            # ETAPA 2: Buscar POs candidatos para cada item
            cnpj_fornecedor = self._limpar_cnpj(dfe_data.get('nfe_infnfe_emit_cnpj', ''))
            pos_candidatos = self._buscar_pos_fornecedor(cnpj_fornecedor)

            if not pos_candidatos:
                # Nenhum PO do fornecedor
                self._registrar_divergencias_sem_po(
                    validacao, itens_convertidos, dfe_data
                )
                validacao.status = 'bloqueado'
                validacao.itens_sem_po = len(itens_convertidos)
                validacao.atualizado_em = datetime.utcnow()
                db.session.commit()

                return {
                    'status': 'bloqueado',
                    'mensagem': f'Nenhum PO encontrado para fornecedor {cnpj_fornecedor}',
                    'itens_sem_po': len(itens_convertidos),
                    'total_itens': len(dfe_lines)
                }

            # ETAPA 3: Match item a item
            data_nf = self._parse_date(dfe_data.get('nfe_infnfe_ide_dhemi', ''))
            resultados_match = []

            for item in itens_convertidos:
                resultado = self._fazer_match_item(
                    item, pos_candidatos, data_nf
                )
                resultados_match.append(resultado)

                # Registrar match
                self._registrar_match_item(validacao, item, resultado)

            # ETAPA 4: Verificar match completo
            itens_ok = [r for r in resultados_match if r['status'] == 'match']
            itens_falha = [r for r in resultados_match if r['status'] != 'match']

            validacao.itens_match = len(itens_ok)

            # Contar tipos de falha
            for r in itens_falha:
                if r['status'] == 'sem_po':
                    validacao.itens_sem_po = (validacao.itens_sem_po or 0) + 1
                elif r['status'] == 'preco_diverge':
                    validacao.itens_preco_diverge = (validacao.itens_preco_diverge or 0) + 1
                elif r['status'] == 'data_diverge':
                    validacao.itens_data_diverge = (validacao.itens_data_diverge or 0) + 1
                elif r['status'] == 'qtd_diverge':
                    validacao.itens_qtd_diverge = (validacao.itens_qtd_diverge or 0) + 1

            # Se NAO for 100% match, bloquear
            if len(itens_ok) < len(resultados_match):
                self._registrar_divergencias_match(
                    validacao, itens_falha, dfe_data
                )
                validacao.status = 'bloqueado'
                validacao.atualizado_em = datetime.utcnow()
                db.session.commit()

                return {
                    'status': 'bloqueado',
                    'mensagem': f'{len(itens_falha)} item(ns) com divergencia',
                    'itens_match': len(itens_ok),
                    'itens_falha': len(itens_falha),
                    'total_itens': len(dfe_lines),
                    'divergencias': [r['motivo'] for r in itens_falha]
                }

            # ETAPA 5: 100% match - preparar consolidacao
            validacao.status = 'aprovado'
            validacao.validado_em = datetime.utcnow()
            validacao.atualizado_em = datetime.utcnow()

            # Identificar POs envolvidos
            pos_envolvidos = self._agrupar_pos_para_consolidar(resultados_match)

            db.session.commit()

            logger.info(
                f"DFE {odoo_dfe_id} APROVADO: {len(itens_ok)} itens, "
                f"{len(pos_envolvidos)} POs para consolidar"
            )

            return {
                'status': 'aprovado',
                'mensagem': f'Todos os {len(itens_ok)} itens com match',
                'itens_match': len(itens_ok),
                'total_itens': len(dfe_lines),
                'pos_para_consolidar': pos_envolvidos,
                'validacao_id': validacao.id
            }

        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao validar DFE {odoo_dfe_id}: {e}")

            # Tentar atualizar status de erro
            try:
                validacao = ValidacaoNfPoDfe.query.filter_by(
                    odoo_dfe_id=odoo_dfe_id
                ).first()
                if validacao:
                    validacao.status = 'erro'
                    validacao.erro_mensagem = str(e)
                    db.session.commit()
            except Exception as e:
                pass

            return {
                'status': 'erro',
                'mensagem': str(e)
            }

    # =========================================================================
    # DFE DATA FETCHING
    # =========================================================================

    def _buscar_dfe(self, odoo_dfe_id: int) -> Optional[Dict[str, Any]]:
        """Busca dados do DFE no Odoo."""
        try:
            odoo = get_odoo_connection()

            dfes = odoo.read(
                'l10n_br_ciel_it_account.dfe',
                [odoo_dfe_id],
                [
                    'id', 'name', 'l10n_br_status',
                    'nfe_infnfe_emit_cnpj', 'nfe_infnfe_emit_xnome',
                    'nfe_infnfe_ide_nnf', 'nfe_infnfe_ide_serie',
                    'protnfe_infnfe_chnfe', 'nfe_infnfe_ide_dhemi',
                    'nfe_infnfe_total_icmstot_vnf',
                    'l10n_br_tipo_pedido'
                ]
            )

            return dfes[0] if dfes else None

        except Exception as e:
            logger.error(f"Erro ao buscar DFE {odoo_dfe_id}: {e}")
            return None

    def _buscar_dfe_lines(self, odoo_dfe_id: int) -> List[Dict[str, Any]]:
        """Busca linhas do DFE no Odoo."""
        try:
            odoo = get_odoo_connection()

            line_ids = odoo.search(
                'l10n_br_ciel_it_account.dfe.line',
                [('dfe_id', '=', odoo_dfe_id)]
            )

            if not line_ids:
                return []

            lines = odoo.read(
                'l10n_br_ciel_it_account.dfe.line',
                line_ids,
                [
                    'id', 'dfe_id', 'product_id',
                    'det_prod_cprod', 'det_prod_xprod',
                    'det_prod_qcom', 'det_prod_ucom', 'det_prod_vuncom',
                    'det_prod_vprod'
                ]
            )

            return lines

        except Exception as e:
            logger.error(f"Erro ao buscar linhas do DFE {odoo_dfe_id}: {e}")
            return []

    # =========================================================================
    # CONVERSION
    # =========================================================================

    def _converter_item_dfe(
        self,
        dfe_line: Dict[str, Any],
        dfe_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Converte item do DFE usando De-Para.

        Retorna dict com:
        - tem_depara: bool
        - cod_produto_fornecedor
        - cod_produto_interno
        - qtd_original
        - qtd_convertida
        - preco_original
        - preco_convertido
        - fator_conversao
        """
        cnpj = self._limpar_cnpj(dfe_data.get('nfe_infnfe_emit_cnpj', ''))
        cod_forn = dfe_line.get('det_prod_cprod', '')

        # Buscar De-Para
        depara = self.depara_service.converter(cnpj, cod_forn)

        if not depara:
            return {
                'tem_depara': False,
                'dfe_line_id': dfe_line['id'],
                'cod_produto_fornecedor': cod_forn,
                'nome_produto': dfe_line.get('det_prod_xprod', ''),
                'qtd_original': Decimal(str(dfe_line.get('det_prod_qcom', 0) or 0)),
                'um_nf': dfe_line.get('det_prod_ucom', ''),
                'preco_original': Decimal(str(dfe_line.get('det_prod_vuncom', 0) or 0))
            }

        fator = Decimal(str(depara.get('fator_conversao', 1)))
        qtd_original = Decimal(str(dfe_line.get('det_prod_qcom', 0) or 0))
        preco_original = Decimal(str(dfe_line.get('det_prod_vuncom', 0) or 0))

        # Converter quantidade: qtd * fator (ex: 60 ML * 1000 = 60000 units)
        qtd_convertida = self.depara_service.converter_quantidade(qtd_original, fator)

        # Converter preco: preco / fator (ex: R$ 41 por ML / 1000 = R$ 0.041 por unit)
        preco_convertido = self.depara_service.converter_preco(preco_original, fator)

        return {
            'tem_depara': True,
            'dfe_line_id': dfe_line['id'],
            'cod_produto_fornecedor': cod_forn,
            'cod_produto_interno': depara['cod_produto_interno'],
            'odoo_product_id': depara.get('odoo_product_id'),
            'nome_produto': dfe_line.get('det_prod_xprod', ''),
            'qtd_original': qtd_original,
            'qtd_convertida': qtd_convertida,
            'um_nf': dfe_line.get('det_prod_ucom', ''),
            'um_interna': depara.get('um_interna', 'UNITS'),
            'preco_original': preco_original,
            'preco_convertido': preco_convertido,
            'fator_conversao': fator
        }

    # =========================================================================
    # PO SEARCH
    # =========================================================================

    def _buscar_pos_fornecedor(self, cnpj_fornecedor: str) -> List[Dict[str, Any]]:
        """
        Busca todos os POs do fornecedor com saldo disponivel.

        Retorna lista de POs com suas linhas.
        """
        try:
            odoo = get_odoo_connection()

            # Buscar partner pelo CNPJ
            partner_ids = odoo.search(
                'res.partner',
                [('l10n_br_cnpj', 'ilike', cnpj_fornecedor)],
                limit=1
            )

            if not partner_ids:
                logger.warning(f"Fornecedor {cnpj_fornecedor} nao encontrado no Odoo")
                return []

            partner_id = partner_ids[0]

            # Buscar POs com status purchase ou done (nao cancelados)
            po_ids = odoo.search(
                'purchase.order',
                [
                    ('partner_id', '=', partner_id),
                    ('state', 'in', ['purchase', 'done'])
                ],
                order='amount_total desc'  # Ordenar por maior valor
            )

            if not po_ids:
                return []

            # Ler dados dos POs
            pos = odoo.read(
                'purchase.order',
                po_ids,
                [
                    'id', 'name', 'partner_id', 'date_order', 'date_planned',
                    'state', 'amount_total', 'order_line'
                ]
            )

            # Para cada PO, buscar linhas com saldo
            for po in pos:
                line_ids = po.get('order_line', [])
                if line_ids:
                    lines = odoo.read(
                        'purchase.order.line',
                        line_ids,
                        [
                            'id', 'order_id', 'product_id', 'name',
                            'product_qty', 'qty_received', 'qty_invoiced',
                            'product_uom', 'price_unit', 'price_subtotal',
                            'date_planned'
                        ]
                    )
                    # Filtrar linhas com saldo (qty > received)
                    po['lines'] = [
                        line for line in lines
                        if (line.get('product_qty', 0) or 0) > (line.get('qty_received', 0) or 0)
                    ]
                else:
                    po['lines'] = []

            # Filtrar POs que tem pelo menos uma linha com saldo
            pos_com_saldo = [p for p in pos if p.get('lines')]

            logger.info(
                f"Encontrados {len(pos_com_saldo)} POs com saldo para "
                f"fornecedor {cnpj_fornecedor}"
            )

            return pos_com_saldo

        except Exception as e:
            logger.error(f"Erro ao buscar POs do fornecedor {cnpj_fornecedor}: {e}")
            return []

    # =========================================================================
    # MATCH LOGIC
    # =========================================================================

    def _fazer_match_item(
        self,
        item: Dict[str, Any],
        pos_candidatos: List[Dict[str, Any]],
        data_nf: date
    ) -> Dict[str, Any]:
        """
        Tenta fazer match de um item da NF com uma linha de PO.

        Validacoes:
        1. Produto: codigo interno deve ser igual
        2. Preco: 0% tolerancia
        3. Data: +/- 2 dias uteis
        4. Quantidade: NF <= PO + 10%

        Retorna:
        - status: 'match', 'sem_po', 'preco_diverge', 'data_diverge', 'qtd_diverge'
        - po_id, po_name, po_line_id se encontrou
        - motivo se bloqueou
        """
        cod_interno = item.get('cod_produto_interno')
        qtd_nf = item.get('qtd_convertida', Decimal('0'))
        preco_nf = item.get('preco_convertido', Decimal('0'))

        if not cod_interno:
            return {
                'status': 'sem_depara',
                'motivo': 'Item sem De-Para cadastrado',
                'item': item
            }

        # Buscar produto no Odoo pelo codigo interno
        odoo = get_odoo_connection()
        product_ids = odoo.search(
            'product.product',
            [('default_code', '=', cod_interno)],
            limit=1
        )

        if not product_ids:
            return {
                'status': 'sem_po',
                'motivo': f'Produto {cod_interno} nao encontrado no Odoo',
                'item': item
            }

        product_id = product_ids[0]

        # Procurar linha de PO com este produto
        melhor_match = None
        melhor_motivo = None

        for po in pos_candidatos:
            for line in po.get('lines', []):
                line_product_id = line.get('product_id', [None])[0]

                if line_product_id != product_id:
                    continue

                # Encontrou linha com o produto - validar
                preco_po = Decimal(str(line.get('price_unit', 0) or 0))
                qtd_po = Decimal(str(line.get('product_qty', 0) or 0))
                qtd_recebida = Decimal(str(line.get('qty_received', 0) or 0))
                saldo_po = qtd_po - qtd_recebida
                data_po = self._parse_date(line.get('date_planned', '') or po.get('date_planned', ''))

                # Validar PRECO (0% tolerancia)
                if not self._validar_preco(preco_nf, preco_po):
                    if melhor_motivo is None or melhor_motivo != 'preco_diverge':
                        melhor_motivo = 'preco_diverge'
                        melhor_match = {
                            'status': 'preco_diverge',
                            'motivo': f'Preco NF ({preco_nf:.4f}) != PO ({preco_po:.4f})',
                            'item': item,
                            'po_id': po['id'],
                            'po_name': po['name'],
                            'po_line_id': line['id'],
                            'preco_nf': float(preco_nf),
                            'preco_po': float(preco_po)
                        }
                    continue

                # Validar DATA (+/- 2 dias uteis)
                if not self._validar_data(data_nf, data_po):
                    if melhor_motivo is None:
                        melhor_motivo = 'data_diverge'
                        melhor_match = {
                            'status': 'data_diverge',
                            'motivo': f'Data NF ({data_nf}) fora da tolerancia do PO ({data_po})',
                            'item': item,
                            'po_id': po['id'],
                            'po_name': po['name'],
                            'po_line_id': line['id'],
                            'data_nf': str(data_nf),
                            'data_po': str(data_po)
                        }
                    continue

                # Validar QUANTIDADE (NF <= saldo_PO + 10%)
                if not self._validar_quantidade(qtd_nf, saldo_po):
                    if melhor_motivo is None:
                        melhor_motivo = 'qtd_diverge'
                        melhor_match = {
                            'status': 'qtd_diverge',
                            'motivo': f'Qtd NF ({qtd_nf}) excede 10% do saldo PO ({saldo_po})',
                            'item': item,
                            'po_id': po['id'],
                            'po_name': po['name'],
                            'po_line_id': line['id'],
                            'qtd_nf': float(qtd_nf),
                            'qtd_po': float(saldo_po)
                        }
                    continue

                # MATCH COMPLETO!
                return {
                    'status': 'match',
                    'item': item,
                    'po_id': po['id'],
                    'po_name': po['name'],
                    'po_line_id': line['id'],
                    'qtd_nf': float(qtd_nf),
                    'qtd_po': float(saldo_po),
                    'preco_nf': float(preco_nf),
                    'preco_po': float(preco_po),
                    'data_nf': str(data_nf),
                    'data_po': str(data_po) if data_po else None
                }

        # Nao encontrou nenhum PO com o produto
        if melhor_match:
            return melhor_match

        return {
            'status': 'sem_po',
            'motivo': f'Nenhum PO com saldo para produto {cod_interno}',
            'item': item
        }

    def _validar_preco(self, preco_nf: Decimal, preco_po: Decimal) -> bool:
        """
        Valida preco: 0% tolerancia.
        Compara com 4 casas decimais.
        """
        preco_nf_arred = preco_nf.quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP)
        preco_po_arred = preco_po.quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP)

        return preco_nf_arred == preco_po_arred

    def _validar_data(self, data_nf: date, data_po: Optional[date]) -> bool:
        """
        Valida data: +/- 2 dias uteis.
        """
        if not data_po:
            return True  # Se PO nao tem data, aceita

        # Calcular diferenca em dias
        diff = abs((data_nf - data_po).days)

        # TODO: Implementar calculo real de dias uteis (excluindo feriados)
        # Por enquanto, usa dias corridos como aproximacao
        # Considerando que ~30% dos dias sao fim de semana:
        # 2 dias uteis ~= 3 dias corridos
        return diff <= 3

    def _validar_quantidade(self, qtd_nf: Decimal, saldo_po: Decimal) -> bool:
        """
        Valida quantidade:
        - NF <= PO: sempre OK (cria saldo)
        - NF > PO: tolerancia de 10%
        """
        if qtd_nf <= saldo_po:
            return True

        # Calcular 10% de tolerancia
        limite = saldo_po * (Decimal('1') + TOLERANCIA_QTD_PERCENTUAL / Decimal('100'))

        return qtd_nf <= limite

    # =========================================================================
    # DIVERGENCE REGISTRATION
    # =========================================================================

    def _registrar_divergencias_sem_depara(
        self,
        validacao: ValidacaoNfPoDfe,
        itens: List[Dict[str, Any]],
        dfe_data: Dict[str, Any]
    ):
        """Registra divergencias para itens sem De-Para."""
        cnpj = self._limpar_cnpj(dfe_data.get('nfe_infnfe_emit_cnpj', ''))
        razao = dfe_data.get('nfe_infnfe_emit_xnome', '')

        for item in itens:
            div = DivergenciaNfPo(
                validacao_id=validacao.id,
                odoo_dfe_id=validacao.odoo_dfe_id,
                odoo_dfe_line_id=item.get('dfe_line_id'),
                cnpj_fornecedor=cnpj,
                razao_fornecedor=razao,
                cod_produto_fornecedor=item.get('cod_produto_fornecedor'),
                nome_produto=item.get('nome_produto'),
                tipo_divergencia='sem_depara',
                campo_label='De-Para',
                valor_nf=item.get('cod_produto_fornecedor'),
                valor_po='N/A',
                status='pendente',
                criado_em=datetime.utcnow()
            )
            db.session.add(div)

    def _registrar_divergencias_sem_po(
        self,
        validacao: ValidacaoNfPoDfe,
        itens: List[Dict[str, Any]],
        dfe_data: Dict[str, Any]
    ):
        """Registra divergencias para itens sem PO correspondente."""
        cnpj = self._limpar_cnpj(dfe_data.get('nfe_infnfe_emit_cnpj', ''))
        razao = dfe_data.get('nfe_infnfe_emit_xnome', '')

        for item in itens:
            # Criar divergência
            div = DivergenciaNfPo(
                validacao_id=validacao.id,
                odoo_dfe_id=validacao.odoo_dfe_id,
                odoo_dfe_line_id=item.get('dfe_line_id'),
                cnpj_fornecedor=cnpj,
                razao_fornecedor=razao,
                cod_produto_fornecedor=item.get('cod_produto_fornecedor'),
                cod_produto_interno=item.get('cod_produto_interno'),
                nome_produto=item.get('nome_produto'),
                tipo_divergencia='sem_po',
                campo_label='Pedido de Compra',
                valor_nf=item.get('cod_produto_interno'),
                valor_po='Nenhum PO encontrado',
                status='pendente',
                criado_em=datetime.utcnow()
            )
            db.session.add(div)

            # TAMBÉM criar MatchNfPoItem para preservar dados de qtd/preco/fator
            # (necessário para exibição correta na tela de divergências)
            match = MatchNfPoItem(
                validacao_id=validacao.id,
                odoo_dfe_line_id=item.get('dfe_line_id'),
                cod_produto_fornecedor=item.get('cod_produto_fornecedor'),
                cod_produto_interno=item.get('cod_produto_interno'),
                nome_produto=item.get('nome_produto'),
                qtd_nf=float(item.get('qtd_convertida', 0)) if item.get('qtd_convertida') else None,
                preco_nf=float(item.get('preco_convertido', 0)) if item.get('preco_convertido') else None,
                um_nf=item.get('um_nf'),
                fator_conversao=float(item.get('fator_conversao', 1)),
                status_match='sem_po',
                motivo_bloqueio='Nenhum PO encontrado para o produto',
                criado_em=datetime.utcnow()
            )
            db.session.add(match)

    def _registrar_divergencias_match(
        self,
        validacao: ValidacaoNfPoDfe,
        itens_falha: List[Dict[str, Any]],
        dfe_data: Dict[str, Any]
    ):
        """Registra divergencias para itens que nao fizeram match."""
        cnpj = self._limpar_cnpj(dfe_data.get('nfe_infnfe_emit_cnpj', ''))
        razao = dfe_data.get('nfe_infnfe_emit_xnome', '')

        for resultado in itens_falha:
            item = resultado.get('item', {})
            status = resultado.get('status', 'sem_po')

            # Mapear tipo de divergencia
            tipo_map = {
                'sem_po': 'sem_po',
                'preco_diverge': 'preco',
                'data_diverge': 'data_entrega',
                'qtd_diverge': 'quantidade'
            }

            tipo = tipo_map.get(status, status)

            # Mapear label
            label_map = {
                'sem_po': 'Pedido de Compra',
                'preco': 'Preco Unitario',
                'data_entrega': 'Data de Entrega',
                'quantidade': 'Quantidade'
            }

            # Valores
            valor_nf = None
            valor_po = None
            diferenca = None

            if status == 'preco_diverge':
                valor_nf = str(resultado.get('preco_nf'))
                valor_po = str(resultado.get('preco_po'))
            elif status == 'data_diverge':
                valor_nf = resultado.get('data_nf')
                valor_po = resultado.get('data_po')
            elif status == 'qtd_diverge':
                valor_nf = str(resultado.get('qtd_nf'))
                valor_po = str(resultado.get('qtd_po'))
                if resultado.get('qtd_po') and float(resultado.get('qtd_po')) > 0:
                    diferenca = (
                        (float(resultado.get('qtd_nf', 0)) - float(resultado.get('qtd_po', 0))) /
                        float(resultado.get('qtd_po', 1)) * 100
                    )

            div = DivergenciaNfPo(
                validacao_id=validacao.id,
                odoo_dfe_id=validacao.odoo_dfe_id,
                odoo_dfe_line_id=item.get('dfe_line_id'),
                cnpj_fornecedor=cnpj,
                razao_fornecedor=razao,
                cod_produto_fornecedor=item.get('cod_produto_fornecedor'),
                cod_produto_interno=item.get('cod_produto_interno'),
                nome_produto=item.get('nome_produto'),
                tipo_divergencia=tipo,
                campo_label=label_map.get(tipo, tipo),
                valor_nf=valor_nf,
                valor_po=valor_po,
                diferenca_percentual=diferenca,
                odoo_po_id=resultado.get('po_id'),
                odoo_po_name=resultado.get('po_name'),
                odoo_po_line_id=resultado.get('po_line_id'),
                status='pendente',
                criado_em=datetime.utcnow()
            )
            db.session.add(div)

    def _registrar_match_item(
        self,
        validacao: ValidacaoNfPoDfe,
        item: Dict[str, Any],
        resultado: Dict[str, Any]
    ):
        """Registra resultado do match de um item."""
        match = MatchNfPoItem(
            validacao_id=validacao.id,
            odoo_dfe_line_id=item.get('dfe_line_id'),
            cod_produto_fornecedor=item.get('cod_produto_fornecedor'),
            cod_produto_interno=item.get('cod_produto_interno'),
            nome_produto=item.get('nome_produto'),
            qtd_nf=float(item.get('qtd_convertida', 0)),
            preco_nf=float(item.get('preco_convertido', 0)),
            um_nf=item.get('um_nf'),
            fator_conversao=float(item.get('fator_conversao', 1)),
            odoo_po_id=resultado.get('po_id'),
            odoo_po_name=resultado.get('po_name'),
            odoo_po_line_id=resultado.get('po_line_id'),
            qtd_po=resultado.get('qtd_po'),
            preco_po=resultado.get('preco_po'),
            status_match=resultado.get('status', 'sem_po'),
            motivo_bloqueio=resultado.get('motivo'),
            criado_em=datetime.utcnow()
        )
        db.session.add(match)

    # =========================================================================
    # HELPERS
    # =========================================================================

    def _get_or_create_validacao(self, odoo_dfe_id: int) -> ValidacaoNfPoDfe:
        """Busca ou cria registro de validacao."""
        validacao = ValidacaoNfPoDfe.query.filter_by(
            odoo_dfe_id=odoo_dfe_id
        ).first()

        if not validacao:
            validacao = ValidacaoNfPoDfe(
                odoo_dfe_id=odoo_dfe_id,
                status='pendente',
                criado_em=datetime.utcnow()
            )
            db.session.add(validacao)
            db.session.flush()

        return validacao

    def _atualizar_validacao_com_dfe(
        self,
        validacao: ValidacaoNfPoDfe,
        dfe_data: Dict[str, Any]
    ):
        """Atualiza dados basicos da validacao com dados do DFE."""
        validacao.numero_nf = dfe_data.get('nfe_infnfe_ide_nnf')
        validacao.serie_nf = dfe_data.get('nfe_infnfe_ide_serie')
        validacao.chave_nfe = dfe_data.get('protnfe_infnfe_chnfe')
        validacao.cnpj_fornecedor = self._limpar_cnpj(
            dfe_data.get('nfe_infnfe_emit_cnpj', '')
        )
        validacao.razao_fornecedor = dfe_data.get('nfe_infnfe_emit_xnome')
        validacao.data_nf = self._parse_date(dfe_data.get('nfe_infnfe_ide_dhemi', ''))
        validacao.valor_total_nf = dfe_data.get('nfe_infnfe_total_icmstot_vnf')

    def _agrupar_pos_para_consolidar(
        self,
        resultados_match: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Agrupa POs envolvidos no match para consolidacao.

        Retorna lista ordenada por valor total (maior primeiro = PO principal).
        """
        pos_dict = {}

        for r in resultados_match:
            if r.get('status') != 'match':
                continue

            po_id = r.get('po_id')
            if not po_id:
                continue

            if po_id not in pos_dict:
                pos_dict[po_id] = {
                    'po_id': po_id,
                    'po_name': r.get('po_name'),
                    'linhas': [],
                    'valor_total': Decimal('0')
                }

            pos_dict[po_id]['linhas'].append({
                'po_line_id': r.get('po_line_id'),
                'qtd_nf': r.get('qtd_nf'),
                'qtd_po': r.get('qtd_po'),
                'preco': r.get('preco_nf'),
                'item': r.get('item')
            })

            # Somar valor
            pos_dict[po_id]['valor_total'] += Decimal(str(r.get('qtd_nf', 0))) * Decimal(str(r.get('preco_nf', 0)))

        # Ordenar por valor total (maior primeiro)
        pos_list = sorted(
            pos_dict.values(),
            key=lambda x: x['valor_total'],
            reverse=True
        )

        # Converter Decimal para float para JSON
        for po in pos_list:
            po['valor_total'] = float(po['valor_total'])

        return pos_list

    def _limpar_cnpj(self, cnpj: str) -> str:
        """Remove pontuacao do CNPJ."""
        if not cnpj:
            return ''
        return ''.join(c for c in str(cnpj) if c.isdigit())

    def _parse_date(self, date_str: str) -> Optional[date]:
        """Parse string de data para date."""
        if not date_str:
            return None

        # Tentar varios formatos
        formatos = [
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%d',
            '%d/%m/%Y',
            '%Y-%m-%dT%H:%M:%S'
        ]

        for fmt in formatos:
            try:
                return datetime.strptime(str(date_str)[:19], fmt).date()
            except Exception as e:
                logger.error(f"Erro ao parsear data {date_str}: {e}")
                continue

        return None

    # =========================================================================
    # QUERY METHODS
    # =========================================================================

    def listar_validacoes(
        self,
        status: Optional[str] = None,
        cnpj_fornecedor: Optional[str] = None,
        page: int = 1,
        per_page: int = 50
    ) -> Dict[str, Any]:
        """Lista validacoes com filtros."""
        try:
            query = ValidacaoNfPoDfe.query

            if status:
                query = query.filter(ValidacaoNfPoDfe.status == status)

            if cnpj_fornecedor:
                cnpj_limpo = self._limpar_cnpj(cnpj_fornecedor)
                query = query.filter(
                    ValidacaoNfPoDfe.cnpj_fornecedor.ilike(f'%{cnpj_limpo}%')
                )

            query = query.order_by(ValidacaoNfPoDfe.criado_em.desc())

            pagination = query.paginate(page=page, per_page=per_page, error_out=False)

            return {
                'items': [self._validacao_to_dict(v) for v in pagination.items],
                'total': pagination.total,
                'pages': pagination.pages,
                'page': page
            }

        except Exception as e:
            logger.error(f"Erro ao listar validacoes: {e}")
            raise

    def listar_divergencias(
        self,
        validacao_id: Optional[int] = None,
        status: Optional[str] = None,
        tipo_divergencia: Optional[str] = None,
        page: int = 1,
        per_page: int = 50
    ) -> Dict[str, Any]:
        """Lista divergencias com filtros."""
        try:
            query = DivergenciaNfPo.query

            if validacao_id:
                query = query.filter(DivergenciaNfPo.validacao_id == validacao_id)

            if status:
                query = query.filter(DivergenciaNfPo.status == status)

            if tipo_divergencia:
                query = query.filter(DivergenciaNfPo.tipo_divergencia == tipo_divergencia)

            query = query.order_by(DivergenciaNfPo.criado_em.desc())

            pagination = query.paginate(page=page, per_page=per_page, error_out=False)

            return {
                'items': [self._divergencia_to_dict(d) for d in pagination.items],
                'total': pagination.total,
                'pages': pagination.pages,
                'page': page
            }

        except Exception as e:
            logger.error(f"Erro ao listar divergencias: {e}")
            raise

    def _validacao_to_dict(self, v: ValidacaoNfPoDfe) -> Dict[str, Any]:
        """Converte validacao para dict."""
        return {
            'id': v.id,
            'odoo_dfe_id': v.odoo_dfe_id,
            'numero_nf': v.numero_nf,
            'serie_nf': v.serie_nf,
            'chave_nfe': v.chave_nfe,
            'cnpj_fornecedor': v.cnpj_fornecedor,
            'razao_fornecedor': v.razao_fornecedor,
            'data_nf': str(v.data_nf) if v.data_nf else None,
            'valor_total_nf': float(v.valor_total_nf) if v.valor_total_nf else None,
            'status': v.status,
            'total_itens': v.total_itens,
            'itens_match': v.itens_match,
            'itens_sem_depara': v.itens_sem_depara,
            'itens_sem_po': v.itens_sem_po,
            'itens_preco_diverge': v.itens_preco_diverge,
            'itens_data_diverge': v.itens_data_diverge,
            'itens_qtd_diverge': v.itens_qtd_diverge,
            'po_consolidado_id': v.po_consolidado_id,
            'po_consolidado_name': v.po_consolidado_name,
            'criado_em': v.criado_em.isoformat() if v.criado_em else None,
            'validado_em': v.validado_em.isoformat() if v.validado_em else None
        }

    def _divergencia_to_dict(self, d: DivergenciaNfPo) -> Dict[str, Any]:
        """Converte divergencia para dict."""
        return {
            'id': d.id,
            'validacao_id': d.validacao_id,
            'odoo_dfe_id': d.odoo_dfe_id,
            'odoo_dfe_line_id': d.odoo_dfe_line_id,
            'cnpj_fornecedor': d.cnpj_fornecedor,
            'razao_fornecedor': d.razao_fornecedor,
            'cod_produto_fornecedor': d.cod_produto_fornecedor,
            'cod_produto_interno': d.cod_produto_interno,
            'nome_produto': d.nome_produto,
            'tipo_divergencia': d.tipo_divergencia,
            'campo_label': d.campo_label,
            'valor_nf': d.valor_nf,
            'valor_po': d.valor_po,
            'diferenca_percentual': float(d.diferenca_percentual) if d.diferenca_percentual else None,
            'odoo_po_id': d.odoo_po_id,
            'odoo_po_name': d.odoo_po_name,
            'odoo_po_line_id': d.odoo_po_line_id,
            'status': d.status,
            'resolucao': d.resolucao,
            'justificativa': d.justificativa,
            'resolvido_por': d.resolvido_por,
            'resolvido_em': d.resolvido_em.isoformat() if d.resolvido_em else None,
            'criado_em': d.criado_em.isoformat() if d.criado_em else None
        }
