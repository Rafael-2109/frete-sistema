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

Referencia: "/home/rafaelnascimento/.claude/plans/plano-validacao-nf-po.md"
"""

import logging
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Any, Optional
from datetime import datetime, date
from collections import defaultdict

from app import db
from app.recebimento.models import (
    ValidacaoNfPoDfe,
    MatchNfPoItem,
    MatchAlocacao,
    DivergenciaNfPo
)
from app.recebimento.services.depara_service import DeparaService
from app.odoo.utils.connection import get_odoo_connection
from app.manufatura.models import PedidoCompras
from app.utils.cnpj_utils import obter_nome_empresa

logger = logging.getLogger(__name__)


# Tolerancias de validacao
TOLERANCIA_QTD_PERCENTUAL = Decimal('10.0')      # 10% para cima
TOLERANCIA_DATA_ANTECIPADO_DIAS = 5              # NF chegou ANTES do PO (dias corridos)
TOLERANCIA_DATA_ATRASADO_DIAS = 15               # NF chegou DEPOIS do PO (dias corridos)
TOLERANCIA_PRECO_PERCENTUAL = Decimal('0.0')     # 0% (exato)


class ValidacaoNfPoService:
    """
    Service para validacao de NF-e vs Pedidos de Compra.
    Identifica POs compativeis e faz match item a item.
    """

    def __init__(self):
        self.depara_service = DeparaService()
        # OTIMIZACAO: Cache local de produtos durante validacao
        # Evita N+1 queries ao Odoo (buscar mesmo produto varias vezes)
        self._product_cache: Dict[str, Optional[int]] = {}

    # =========================================================================
    # MAIN VALIDATION FLOW
    # =========================================================================

    def validar_dfe(self, odoo_dfe_id: int, usar_dados_locais: bool = True) -> Dict[str, Any]:
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
            usar_dados_locais: Se True (padrao), busca POs na tabela local
                               pedido_compras em vez de chamar Odoo (muito mais rapido)

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

            # OTIMIZACAO: Limpar cache de produtos no inicio da validacao
            self._limpar_cache_produtos()

            # Criar ou atualizar registro de validacao
            validacao = self._get_or_create_validacao(odoo_dfe_id)
            validacao.status = 'validando'
            # CORRECAO BUG: Resetar contadores antes de revalidar
            # Sem isso, ao revalidar um DFE apos criar/reativar De-Para,
            # os contadores antigos permanecem e o status fica incorreto
            validacao.itens_sem_depara = 0
            validacao.itens_sem_po = 0
            validacao.itens_preco_diverge = 0
            validacao.itens_data_diverge = 0
            validacao.itens_qtd_diverge = 0
            validacao.itens_match = 0
            validacao.total_itens = 0
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

            # =================================================================
            # VERIFICAR SITUACAO DA NF NA SEFAZ (ANTES DE QUALQUER PROCESSAMENTO)
            # Se NF CANCELADA ou INUTILIZADA -> BLOQUEAR imediatamente
            # =================================================================
            if validacao.situacao_nf_bloqueada:
                situacao = validacao.situacao_dfe_odoo
                logger.warning(
                    f"DFE {odoo_dfe_id} BLOQUEADO: NF {situacao} na SEFAZ. "
                    f"Nao pode ser lancada."
                )

                # Limpar matches/divergencias anteriores (se houver de revalidacao)
                DivergenciaNfPo.query.filter_by(validacao_id=validacao.id).delete()
                MatchNfPoItem.query.filter_by(validacao_id=validacao.id).delete()

                validacao.status = 'bloqueado'
                validacao.erro_mensagem = f'NF {situacao} na SEFAZ - Nao pode ser lancada'
                validacao.validado_em = datetime.utcnow()
                validacao.atualizado_em = datetime.utcnow()
                db.session.commit()

                return {
                    'status': 'bloqueado',
                    'mensagem': f'NF {situacao} na SEFAZ - Nao pode ser lancada',
                    'situacao_dfe_odoo': situacao,
                    'bloqueio_tipo': 'situacao_nf_sefaz'
                }

            # NOVO: Importar POs vinculados do Odoo (se houver)
            self._importar_pos_vinculados(validacao, dfe_data)

            # =================================================================
            # VERIFICAR SE DFE JA TEM PO VINCULADO NO ODOO
            # Se sim, marcar como 'finalizado_odoo' e nao processar mais
            # =================================================================
            if validacao.odoo_po_vinculado_id or validacao.odoo_po_fiscal_id:
                po_info = validacao.odoo_po_vinculado_name or validacao.odoo_po_fiscal_name
                po_id = validacao.odoo_po_vinculado_id or validacao.odoo_po_fiscal_id

                logger.info(
                    f"DFE {odoo_dfe_id} ja possui PO vinculado no Odoo: {po_info} (ID: {po_id}). "
                    f"Marcando como finalizado_odoo."
                )

                # BUGFIX: Limpar matches/divergencias anteriores ao finalizar
                # Sem isso, divergencias criadas antes do vinculo com PO permaneciam
                # como 'pendentes' mesmo apos o DFE ser finalizado no Odoo
                divergencias_limpas = DivergenciaNfPo.query.filter_by(
                    validacao_id=validacao.id
                ).delete()
                matches_limpos = MatchNfPoItem.query.filter_by(
                    validacao_id=validacao.id
                ).delete()

                if divergencias_limpas > 0 or matches_limpos > 0:
                    logger.info(
                        f"DFE {odoo_dfe_id} finalizado_odoo: limpas {divergencias_limpas} "
                        f"divergencias e {matches_limpos} matches anteriores"
                    )

                validacao.status = 'finalizado_odoo'
                validacao.validado_em = datetime.utcnow()
                validacao.atualizado_em = datetime.utcnow()
                db.session.commit()

                return {
                    'status': 'finalizado_odoo',
                    'mensagem': f'DFE ja vinculado ao PO {po_info} no Odoo. Nao requer validacao.',
                    'odoo_po_vinculado_id': validacao.odoo_po_vinculado_id,
                    'odoo_po_vinculado_name': validacao.odoo_po_vinculado_name,
                    'odoo_po_fiscal_id': validacao.odoo_po_fiscal_id,
                    'odoo_po_fiscal_name': validacao.odoo_po_fiscal_name,
                    'divergencias_limpas': divergencias_limpas,
                    'matches_limpos': matches_limpos
                }

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

            # ETAPA 1: Converter todos os itens (OTIMIZADO com batch)
            itens_convertidos, itens_sem_depara = self._converter_itens_dfe_batch(
                dfe_lines, dfe_data
            )

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

            # 🚀 OTIMIZACAO: Usar dados locais por padrao (muito mais rapido)
            if usar_dados_locais:
                pos_candidatos = self._buscar_pos_fornecedor_local(cnpj_fornecedor)
            else:
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

            # ================================================================
            # ETAPA 3: Agrupar itens por codigo interno
            # (Suporta N linhas da NF com mesmo produto - lotes diferentes)
            # ================================================================
            data_nf = self._parse_date(dfe_data.get('nfe_infnfe_ide_dhemi', ''))
            itens_agrupados = self._agrupar_itens_por_codigo(itens_convertidos)

            logger.info(
                f"DFE {odoo_dfe_id}: {len(itens_agrupados)} produtos unicos "
                f"de {len(itens_convertidos)} linhas da NF"
            )

            # ================================================================
            # ETAPA 4: Match com split para cada produto
            # (Avalia TODOS os POs antes de decidir, permite split multi-PO)
            # ================================================================
            resultados_match = []
            saldos_consumidos = {}  # {po_line_id: qtd_ja_alocada}

            for cod_interno, item_agrupado in itens_agrupados.items():
                # Filtrar candidatos validos (preco e data OK)
                # 🚀 OTIMIZACAO: Usar versao local quando usar_dados_locais=True
                if usar_dados_locais:
                    candidatos = self._filtrar_pos_candidatos_por_item_local(
                        cod_interno,
                        item_agrupado['preco_medio'],
                        data_nf,
                        pos_candidatos
                    )
                else:
                    # Versao original com odoo_product_id
                    candidatos = self._filtrar_pos_candidatos_por_item(
                        cod_interno,
                        item_agrupado['preco_medio'],
                        data_nf,
                        pos_candidatos,
                        odoo_product_id=item_agrupado.get('odoo_product_id')
                    )

                if not candidatos:
                    # Nenhum PO candidato para este produto
                    resultado = {
                        'status': 'sem_po',
                        'cod_produto_interno': cod_interno,
                        'motivo': f'Nenhum PO com preco/data validos para {cod_interno}',
                        'item_agrupado': item_agrupado,
                        'alocacoes': []
                    }
                else:
                    # Fazer match com split
                    resultado = self._fazer_match_com_split(
                        item_agrupado,
                        candidatos,
                        saldos_consumidos
                    )
                    resultado['cod_produto_interno'] = cod_interno
                    resultado['item_agrupado'] = item_agrupado

                resultados_match.append(resultado)

                # Registrar match/divergencia para CADA linha original da NF
                for linha_nf in item_agrupado['linhas_nf']:
                    self._registrar_match_item_com_alocacoes(
                        validacao,
                        linha_nf['item_original'],
                        resultado
                    )

            # ================================================================
            # ETAPA 5: Verificar match completo
            # ================================================================
            itens_ok = [r for r in resultados_match if r['status'] == 'match']
            itens_falha = [r for r in resultados_match if r['status'] != 'match']

            # Contar itens com match (produtos unicos agrupados)
            validacao.itens_match = len(itens_ok)
            validacao.total_itens = len(itens_agrupados)  # Produtos unicos

            # Contar tipos de falha
            for r in itens_falha:
                status = r.get('status', 'sem_po')
                if status == 'sem_po':
                    validacao.itens_sem_po = (validacao.itens_sem_po or 0) + 1
                elif status == 'saldo_insuficiente':
                    validacao.itens_qtd_diverge = (validacao.itens_qtd_diverge or 0) + 1
                elif status == 'preco_diverge':
                    validacao.itens_preco_diverge = (validacao.itens_preco_diverge or 0) + 1
                elif status == 'data_diverge':
                    validacao.itens_data_diverge = (validacao.itens_data_diverge or 0) + 1
                elif status == 'qtd_diverge':
                    validacao.itens_qtd_diverge = (validacao.itens_qtd_diverge or 0) + 1

            # Se NAO for 100% match, bloquear
            if len(itens_ok) < len(resultados_match):
                self._registrar_divergencias_match_agrupado(
                    validacao, itens_falha, dfe_data
                )
                validacao.status = 'bloqueado'
                validacao.atualizado_em = datetime.utcnow()
                db.session.commit()

                return {
                    'status': 'bloqueado',
                    'mensagem': f'{len(itens_falha)} produto(s) com divergencia',
                    'itens_match': len(itens_ok),
                    'itens_falha': len(itens_falha),
                    'total_itens': len(itens_agrupados),
                    'divergencias': [r.get('motivo', r.get('status')) for r in itens_falha]
                }

            # ETAPA 5: 100% match - preparar consolidacao
            validacao.status = 'aprovado'
            validacao.validado_em = datetime.utcnow()
            validacao.atualizado_em = datetime.utcnow()

            # Identificar POs envolvidos
            pos_envolvidos = self._agrupar_pos_para_consolidar(resultados_match)

            # === RASTREAMENTO PARA SKIP INTELIGENTE ===
            # Salvar quais POs foram usadas nesta validação
            # Quando essas POs mudarem, a flag po_modificada_apos_validacao será setada
            import json
            from app.recebimento.services.po_changes_detector_service import PoChangesDetectorService

            detector = PoChangesDetectorService()
            po_ids_usados = detector.extrair_pos_usadas(validacao.id)
            validacao.po_ids_usados = json.dumps(po_ids_usados) if po_ids_usados else None
            validacao.ultima_validacao_em = datetime.utcnow()
            validacao.po_modificada_apos_validacao = False  # Reset flag após validação bem-sucedida

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

        finally:
            # OTIMIZACAO: Limpar cache de produtos no final da validacao
            # Garante que nao acumula dados entre validacoes
            self._limpar_cache_produtos()

    # =========================================================================
    # DFE DATA FETCHING
    # =========================================================================

    def _buscar_dfe(self, odoo_dfe_id: int) -> Optional[Dict[str, Any]]:
        """Busca dados do DFE no Odoo, incluindo POs vinculados."""
        try:
            odoo = get_odoo_connection()

            dfes = odoo.read(
                'l10n_br_ciel_it_account.dfe',
                [odoo_dfe_id],
                [
                    'id', 'name', 'l10n_br_status',
                    'l10n_br_situacao_dfe',  # NOVO: Situacao NF na SEFAZ (AUTORIZADA/CANCELADA/INUTILIZADA)
                    'nfe_infnfe_emit_cnpj', 'nfe_infnfe_emit_xnome',
                    'nfe_infnfe_dest_cnpj',  # CNPJ empresa compradora (dest_xnome não existe no Odoo)
                    'nfe_infnfe_ide_nnf', 'nfe_infnfe_ide_serie',
                    'protnfe_infnfe_chnfe', 'nfe_infnfe_ide_dhemi',
                    'nfe_infnfe_total_icmstot_vnf',
                    'l10n_br_tipo_pedido',
                    # Campos de PO vinculado
                    'purchase_id',        # PO vinculado (many2one)
                    'purchase_fiscal_id'  # PO fiscal/escrituracao (many2one)
                ]
            )

            return dfes[0] if dfes else None

        except Exception as e:
            logger.error(f"Erro ao buscar DFE {odoo_dfe_id}: {e}")
            return None

    def _importar_pos_vinculados(
        self,
        validacao: ValidacaoNfPoDfe,
        dfe_data: Dict[str, Any]
    ) -> None:
        """
        Importa informacoes dos POs vinculados ao DFE do Odoo.

        Estrategia de busca (3 caminhos, em ordem):
        1. DFE.purchase_id (many2one direto - 14.6% dos casos)
        2. DFE.purchase_fiscal_id (many2one escrituracao - 75% dos concluidos)
        3. PO.dfe_id = DFE.id (caminho inverso - 85.4% dos casos em status=04)
        """
        try:
            # 1. purchase_id (caminho direto - excepcional)
            purchase_id_data = dfe_data.get('purchase_id')
            if purchase_id_data and isinstance(purchase_id_data, (list, tuple)):
                validacao.odoo_po_vinculado_id = purchase_id_data[0]
                validacao.odoo_po_vinculado_name = purchase_id_data[1] if len(purchase_id_data) > 1 else None
                logger.info(
                    f"DFE {validacao.odoo_dfe_id}: PO vinculado importado - "
                    f"{validacao.odoo_po_vinculado_name} (ID: {validacao.odoo_po_vinculado_id})"
                )

            # 2. purchase_fiscal_id (escrituracao)
            purchase_fiscal_data = dfe_data.get('purchase_fiscal_id')
            if purchase_fiscal_data and isinstance(purchase_fiscal_data, (list, tuple)):
                validacao.odoo_po_fiscal_id = purchase_fiscal_data[0]
                validacao.odoo_po_fiscal_name = purchase_fiscal_data[1] if len(purchase_fiscal_data) > 1 else None
                logger.info(
                    f"DFE {validacao.odoo_dfe_id}: PO fiscal importado - "
                    f"{validacao.odoo_po_fiscal_name} (ID: {validacao.odoo_po_fiscal_id})"
                )

            # 3. FALLBACK: Buscar PO via PO.dfe_id (caminho inverso)
            #    Cobre 85.4% dos DFEs em status=04 que nao tem purchase_id preenchido
            if not validacao.odoo_po_vinculado_id and not validacao.odoo_po_fiscal_id:
                self._vincular_po_via_dfe_id(validacao)

            # Marcar data de importacao se algum PO foi encontrado
            if validacao.odoo_po_vinculado_id or validacao.odoo_po_fiscal_id:
                validacao.pos_vinculados_importados_em = datetime.utcnow()

        except Exception as e:
            logger.warning(f"Erro ao importar POs vinculados do DFE {validacao.odoo_dfe_id}: {e}")

    def _vincular_po_via_dfe_id(self, validacao: ValidacaoNfPoDfe) -> None:
        """
        Fallback: busca PO que aponta dfe_id para este DFE.
        Caminho: purchase.order WHERE dfe_id = DFE.id

        Este e o caminho PRIMARIO no Odoo (85.4% dos DFEs em status=04).
        O campo PO.dfe_id (many2one) e preenchido pelo Odoo quando o usuario
        vincula o DFE ao PO na interface de compras.
        """
        try:
            odoo = get_odoo_connection()

            # Buscar PO que tem dfe_id apontando para este DFE
            pos = odoo.execute_kw(
                'purchase.order', 'search_read',
                [[['dfe_id', '=', validacao.odoo_dfe_id]]],
                {'fields': ['id', 'name'], 'limit': 1}
            )

            if pos:
                validacao.odoo_po_vinculado_id = pos[0]['id']
                validacao.odoo_po_vinculado_name = pos[0]['name']
                logger.info(
                    f"DFE {validacao.odoo_dfe_id}: PO vinculado via PO.dfe_id - "
                    f"{pos[0]['name']} (ID: {pos[0]['id']})"
                )
            else:
                logger.debug(
                    f"DFE {validacao.odoo_dfe_id}: Nenhum PO encontrado via PO.dfe_id"
                )

        except Exception as e:
            logger.warning(
                f"Erro ao vincular PO via dfe_id para DFE {validacao.odoo_dfe_id}: {e}"
            )

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

    def _converter_itens_dfe_batch(
        self,
        dfe_lines: List[Dict[str, Any]],
        dfe_data: Dict[str, Any]
    ) -> tuple:
        """
        OTIMIZACAO: Converte todos os itens do DFE em BATCH.

        Ao inves de N queries ao BD (uma por item), faz apenas 1 query
        usando converter_lote() do DeparaService.

        Args:
            dfe_lines: Lista de linhas do DFE
            dfe_data: Dados do DFE (cabecalho)

        Returns:
            Tuple (itens_convertidos, itens_sem_depara)
        """
        cnpj = self._limpar_cnpj(dfe_data.get('nfe_infnfe_emit_cnpj', ''))

        # Extrair todos os codigos de produto do fornecedor
        cod_produtos = [line.get('det_prod_cprod', '') for line in dfe_lines]
        cod_produtos = [c for c in cod_produtos if c]  # Remover vazios

        # OTIMIZACAO: Uma unica query para todos os De-Para
        deparas_cache = self.depara_service.converter_lote(cnpj, cod_produtos)

        logger.debug(
            f"De-Para batch: {len(deparas_cache)} encontrados para {len(cod_produtos)} codigos"
        )

        itens_convertidos = []
        itens_sem_depara = []

        for line in dfe_lines:
            cod_forn = line.get('det_prod_cprod', '')

            # Buscar no cache (O(1) ao inves de query ao BD)
            depara = deparas_cache.get(cod_forn)

            if not depara:
                itens_sem_depara.append({
                    'tem_depara': False,
                    'dfe_line_id': line['id'],
                    'cod_produto_fornecedor': cod_forn,
                    'nome_produto': line.get('det_prod_xprod', ''),
                    'qtd_original': Decimal(str(line.get('det_prod_qcom', 0) or 0)),
                    'um_nf': line.get('det_prod_ucom', ''),
                    'preco_original': Decimal(str(line.get('det_prod_vuncom', 0) or 0))
                })
                continue

            fator = Decimal(str(depara.get('fator_conversao', 1)))
            qtd_original = Decimal(str(line.get('det_prod_qcom', 0) or 0))
            preco_original = Decimal(str(line.get('det_prod_vuncom', 0) or 0))

            # Converter quantidade e preco
            qtd_convertida = self.depara_service.converter_quantidade(qtd_original, fator)
            preco_convertido = self.depara_service.converter_preco(preco_original, fator)

            itens_convertidos.append({
                'tem_depara': True,
                'dfe_line_id': line['id'],
                'cod_produto_fornecedor': cod_forn,
                'cod_produto_interno': depara['cod_produto_interno'],
                'odoo_product_id': depara.get('odoo_product_id'),
                'nome_produto': line.get('det_prod_xprod', ''),
                'qtd_original': qtd_original,
                'qtd_convertida': qtd_convertida,
                'um_nf': line.get('det_prod_ucom', ''),
                'um_interna': depara.get('um_interna', 'UNITS'),
                'preco_original': preco_original,
                'preco_convertido': preco_convertido,
                'fator_conversao': fator
            })

        return itens_convertidos, itens_sem_depara

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
            # EXCLUIR POs que ja possuem NF vinculada (dfe_id preenchido)
            # NOTA: order nao e suportado no search, usa-se search_read para ordenar
            po_ids = odoo.search(
                'purchase.order',
                [
                    ('partner_id', '=', partner_id),
                    ('state', 'in', ['purchase', 'done']),
                    ('dfe_id', '=', False)  # Apenas POs SEM NF vinculada
                ]
            )

            if not po_ids:
                return []

            # Ler dados dos POs (campos minimos necessarios)
            pos = odoo.read(
                'purchase.order',
                po_ids,
                [
                    'id', 'name', 'date_planned', 'order_line'
                ]
            )

            # OTIMIZACAO: Batch read de TODAS as linhas de PO em UMA UNICA chamada
            # Ao inves de N chamadas (uma por PO), faz apenas 1 chamada
            all_line_ids = []
            line_id_to_po_idx = {}  # Mapear line_id -> indice do PO

            for po_idx, po in enumerate(pos):
                po['lines'] = []  # Inicializar lista vazia
                for line_id in po.get('order_line', []):
                    all_line_ids.append(line_id)
                    line_id_to_po_idx[line_id] = po_idx

            if all_line_ids:
                # UMA UNICA chamada para TODAS as linhas (campos minimos)
                all_lines = odoo.read(
                    'purchase.order.line',
                    all_line_ids,
                    [
                        'id', 'order_id', 'product_id',
                        'product_qty', 'qty_received',
                        'price_unit', 'date_planned'
                    ]
                )

                # Distribuir linhas de volta para cada PO (em memoria)
                for line in all_lines:
                    line_id = line['id']
                    po_idx = line_id_to_po_idx.get(line_id)
                    if po_idx is not None:
                        # Filtrar apenas linhas com saldo (qty > received)
                        qtd = line.get('product_qty', 0) or 0
                        recebido = line.get('qty_received', 0) or 0
                        if qtd > recebido:
                            pos[po_idx]['lines'].append(line)

                logger.debug(
                    f"PO Lines batch: {len(all_lines)} linhas lidas em 1 chamada "
                    f"(antes: {len(pos)} chamadas)"
                )

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

    def _buscar_pos_fornecedor_local(self, cnpj_fornecedor: str) -> List[Dict[str, Any]]:
        """
        🚀 OTIMIZAÇÃO: Busca POs do fornecedor na tabela LOCAL pedido_compras.

        Substitui chamadas ao Odoo por query local, reduzindo drasticamente
        o tempo de resposta (de segundos para milissegundos).

        Criterios:
        - CNPJ igual ao fornecedor da NF
        - Status Odoo = 'purchase' ou 'done' (confirmados)
        - dfe_id vazio (sem NF vinculada)
        - Saldo disponivel > 0 (qtd_produto_pedido - qtd_recebida)

        Retorna lista de POs formatada compativel com o metodo original.
        """
        try:
            # Limpar CNPJ (remover pontuacao)
            cnpj_limpo = ''.join(c for c in cnpj_fornecedor if c.isdigit())

            # Query local - SEM chamada ao Odoo!
            pos_local = PedidoCompras.query.filter(
                # CNPJ do fornecedor (limpar pontuacao para comparacao)
                db.func.regexp_replace(PedidoCompras.cnpj_fornecedor, '[^0-9]', '', 'g') == cnpj_limpo,
                # Status confirmado
                PedidoCompras.status_odoo.in_(['purchase', 'done']),
                # Sem NF vinculada
                db.or_(
                    PedidoCompras.dfe_id.is_(None),
                    PedidoCompras.dfe_id == ''
                ),
                # Saldo disponivel > 0
                (PedidoCompras.qtd_produto_pedido - db.func.coalesce(PedidoCompras.qtd_recebida, 0)) > 0
            ).order_by(
                PedidoCompras.num_pedido,
                PedidoCompras.cod_produto
            ).all()

            if not pos_local:
                logger.info(f"Nenhum PO local com saldo para fornecedor {cnpj_fornecedor}")
                return []

            # Agrupar por numero do pedido (cada PO pode ter multiplas linhas/produtos)
            pos_agrupados = defaultdict(lambda: {
                'id': None,
                'name': None,
                'date_order': None,
                'date_planned': None,
                'lines': []
            })

            for po in pos_local:
                num_pedido = po.num_pedido

                # Atualizar dados do header (pega do primeiro registro)
                if pos_agrupados[num_pedido]['id'] is None:
                    pos_agrupados[num_pedido]['id'] = po.odoo_id  # ID da linha no Odoo
                    pos_agrupados[num_pedido]['name'] = po.num_pedido
                    pos_agrupados[num_pedido]['date_order'] = (
                        po.data_pedido_criacao.strftime('%Y-%m-%d') if po.data_pedido_criacao else None
                    )
                    pos_agrupados[num_pedido]['date_planned'] = (
                        po.data_pedido_previsao.strftime('%Y-%m-%d') if po.data_pedido_previsao else None
                    )

                # Calcular saldo
                qtd_pedido = po.qtd_produto_pedido or Decimal('0')
                qtd_recebida = po.qtd_recebida or Decimal('0')
                saldo = qtd_pedido - qtd_recebida

                # Adicionar linha do PO (formato compativel com Odoo)
                pos_agrupados[num_pedido]['lines'].append({
                    'id': int(po.odoo_id) if po.odoo_id else po.id,  # ID da linha
                    'order_id': [None, po.num_pedido],  # [id, name] - formato Odoo
                    'product_id': [None, po.cod_produto],  # [id, default_code]
                    'product_qty': float(qtd_pedido),
                    'qty_received': float(qtd_recebida),
                    'price_unit': float(po.preco_produto_pedido or 0),
                    'date_planned': (
                        po.data_pedido_previsao.strftime('%Y-%m-%d %H:%M:%S')
                        if po.data_pedido_previsao else None
                    ),
                    # Campos extras para match local
                    '_cod_produto_interno': po.cod_produto,
                    '_saldo': float(saldo),
                    '_local_id': po.id
                })

            # Converter para lista
            pos_lista = list(pos_agrupados.values())

            logger.info(
                f"🚀 [LOCAL] Encontrados {len(pos_lista)} POs com saldo para "
                f"fornecedor {cnpj_fornecedor} ({sum(len(p['lines']) for p in pos_lista)} linhas)"
            )

            return pos_lista

        except Exception as e:
            logger.error(f"Erro ao buscar POs locais do fornecedor {cnpj_fornecedor}: {e}")
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

        # OTIMIZACAO: Buscar produto usando cache local
        # Evita N+1 queries ao Odoo (mesmo produto buscado apenas 1 vez)
        product_id = self._obter_product_id(cod_interno)

        if not product_id:
            return {
                'status': 'sem_po',
                'motivo': f'Produto {cod_interno} nao encontrado no Odoo',
                'item': item
            }

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
        Valida data com tolerancia ASSIMETRICA:
        - Antecipado (NF antes do PO): 3 dias uteis (~5 dias corridos)
        - Atrasado (NF depois do PO): 7 dias uteis (~10 dias corridos)

        Logica:
        - diff_dias < 0: NF chegou ANTES do PO (antecipada)
        - diff_dias > 0: NF chegou DEPOIS do PO (atrasada)
        - diff_dias = 0: Mesmo dia (OK)
        """
        if not data_po:
            return True  # Se PO nao tem data, aceita

        # Calcular diferenca: positivo = NF depois, negativo = NF antes
        diff_dias = (data_nf - data_po).days

        if diff_dias < 0:
            # NF chegou ANTES do PO (antecipada)
            return abs(diff_dias) <= TOLERANCIA_DATA_ANTECIPADO_DIAS
        else:
            # NF chegou DEPOIS do PO (atrasada) ou na data exata
            return diff_dias <= TOLERANCIA_DATA_ATRASADO_DIAS

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
        cnpj_empresa = self._limpar_cnpj(dfe_data.get('nfe_infnfe_dest_cnpj', ''))
        # IMPORTANTE: nfe_infnfe_dest_xnome NÃO existe no Odoo, usar mapeamento centralizado
        razao_empresa = obter_nome_empresa(cnpj_empresa)

        for item in itens:
            div = DivergenciaNfPo(
                validacao_id=validacao.id,
                odoo_dfe_id=validacao.odoo_dfe_id,
                odoo_dfe_line_id=item.get('dfe_line_id'),
                cnpj_fornecedor=cnpj,
                razao_fornecedor=razao,
                cnpj_empresa_compradora=cnpj_empresa,
                razao_empresa_compradora=razao_empresa,
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
        cnpj_empresa = self._limpar_cnpj(dfe_data.get('nfe_infnfe_dest_cnpj', ''))
        # IMPORTANTE: nfe_infnfe_dest_xnome NÃO existe no Odoo, usar mapeamento centralizado
        razao_empresa = obter_nome_empresa(cnpj_empresa)

        for item in itens:
            # Criar divergência
            div = DivergenciaNfPo(
                validacao_id=validacao.id,
                odoo_dfe_id=validacao.odoo_dfe_id,
                odoo_dfe_line_id=item.get('dfe_line_id'),
                cnpj_fornecedor=cnpj,
                razao_fornecedor=razao,
                cnpj_empresa_compradora=cnpj_empresa,
                razao_empresa_compradora=razao_empresa,
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
        cnpj_empresa = self._limpar_cnpj(dfe_data.get('nfe_infnfe_dest_cnpj', ''))
        # IMPORTANTE: nfe_infnfe_dest_xnome NÃO existe no Odoo, usar mapeamento centralizado
        razao_empresa = obter_nome_empresa(cnpj_empresa)

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
                cnpj_empresa_compradora=cnpj_empresa,
                razao_empresa_compradora=razao_empresa,
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

    def _registrar_divergencias_match_agrupado(
        self,
        validacao: ValidacaoNfPoDfe,
        itens_falha: List[Dict[str, Any]],
        dfe_data: Dict[str, Any]
    ):
        """
        Registra divergencias para itens AGRUPADOS que nao fizeram match.

        DIFERENCA do metodo original:
        - Recebe resultados do novo algoritmo com 'item_agrupado'
        - Suporta estrutura de multiplas linhas da NF por produto
        - Registra divergencia uma vez por produto (nao por linha)
        """
        cnpj = self._limpar_cnpj(dfe_data.get('nfe_infnfe_emit_cnpj', ''))
        razao = dfe_data.get('nfe_infnfe_emit_xnome', '')
        cnpj_empresa = self._limpar_cnpj(dfe_data.get('nfe_infnfe_dest_cnpj', ''))
        # IMPORTANTE: nfe_infnfe_dest_xnome NÃO existe no Odoo, usar mapeamento centralizado
        razao_empresa = obter_nome_empresa(cnpj_empresa)

        for resultado in itens_falha:
            item_agrupado = resultado.get('item_agrupado', {})
            status = resultado.get('status', 'sem_po')

            # Mapear tipo de divergencia
            tipo_map = {
                'sem_po': 'sem_po',
                'saldo_insuficiente': 'quantidade',
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

            # Valores para divergencia
            valor_nf = None
            valor_po = None
            diferenca = None

            if status == 'sem_po':
                valor_nf = item_agrupado.get('cod_produto_interno')
                valor_po = 'Nenhum PO com preco/data validos'
            elif status == 'saldo_insuficiente':
                qtd_total_nf = float(item_agrupado.get('qtd_total', 0))
                alocacoes = resultado.get('alocacoes', [])
                qtd_alocada = sum(float(a.get('qtd_alocada', 0)) for a in alocacoes)
                valor_nf = f"{qtd_total_nf:.3f}"
                valor_po = f"{qtd_alocada:.3f}"
                if qtd_alocada > 0:
                    diferenca = ((qtd_total_nf - qtd_alocada) / qtd_alocada) * 100

            # Pegar primeira linha da NF para referencia
            linhas_nf = item_agrupado.get('linhas_nf', [])
            primeira_linha = linhas_nf[0] if linhas_nf else {}
            item_original = primeira_linha.get('item_original', {})

            # Pegar PO principal das alocacoes (se houver)
            alocacoes = resultado.get('alocacoes', [])
            po_principal = alocacoes[0] if alocacoes else {}

            div = DivergenciaNfPo(
                validacao_id=validacao.id,
                odoo_dfe_id=validacao.odoo_dfe_id,
                odoo_dfe_line_id=item_original.get('dfe_line_id'),
                cnpj_fornecedor=cnpj,
                razao_fornecedor=razao,
                cnpj_empresa_compradora=cnpj_empresa,
                razao_empresa_compradora=razao_empresa,
                cod_produto_fornecedor=item_original.get('cod_produto_fornecedor'),
                cod_produto_interno=item_agrupado.get('cod_produto_interno'),
                nome_produto=item_agrupado.get('nome_produto'),
                tipo_divergencia=tipo,
                campo_label=label_map.get(tipo, tipo),
                valor_nf=valor_nf,
                valor_po=valor_po,
                diferenca_percentual=diferenca,
                odoo_po_id=po_principal.get('po_id'),
                odoo_po_name=po_principal.get('po_name'),
                odoo_po_line_id=po_principal.get('po_line_id'),
                status='pendente',
                criado_em=datetime.utcnow()
            )
            db.session.add(div)

            logger.info(
                f"Divergencia registrada: {item_agrupado.get('cod_produto_interno')} - "
                f"{tipo} - {resultado.get('motivo', status)}"
            )

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
        validacao.cnpj_empresa_compradora = self._limpar_cnpj(
            dfe_data.get('nfe_infnfe_dest_cnpj', '')
        )
        # IMPORTANTE: nfe_infnfe_dest_xnome NÃO existe no Odoo, usar mapeamento centralizado
        validacao.razao_empresa_compradora = obter_nome_empresa(validacao.cnpj_empresa_compradora)
        validacao.data_nf = self._parse_date(dfe_data.get('nfe_infnfe_ide_dhemi', ''))
        validacao.valor_total_nf = dfe_data.get('nfe_infnfe_total_icmstot_vnf')

        # NOVO: Situacao da NF na SEFAZ (l10n_br_situacao_dfe)
        # Valores: AUTORIZADA, CANCELADA, INUTILIZADA (ou None/False se nao preenchido)
        situacao_dfe = dfe_data.get('l10n_br_situacao_dfe')
        # Tratar False do Odoo como None
        if situacao_dfe is False:
            situacao_dfe = None
        validacao.situacao_dfe_odoo = situacao_dfe

    def _agrupar_pos_para_consolidar(
        self,
        resultados_match: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Agrupa POs envolvidos no match para consolidacao.

        ATUALIZADO para novo algoritmo:
        - Processa 'alocacoes' de cada resultado (suporte a split)
        - Um item da NF pode ter multiplas alocacoes em POs diferentes

        Retorna lista ordenada por valor total (maior primeiro = PO principal).
        """
        pos_dict = {}

        for r in resultados_match:
            if r.get('status') != 'match':
                continue

            # NOVO: Processar TODAS as alocacoes (split multi-PO)
            alocacoes = r.get('alocacoes', [])
            item_agrupado = r.get('item_agrupado', {})

            for aloc in alocacoes:
                po_id = aloc.get('po_id')
                if not po_id:
                    continue

                if po_id not in pos_dict:
                    pos_dict[po_id] = {
                        'po_id': po_id,
                        'po_name': aloc.get('po_name'),
                        'linhas': [],
                        'valor_total': Decimal('0')
                    }

                preco = aloc.get('preco_po', Decimal('0'))
                if not isinstance(preco, Decimal):
                    preco = Decimal(str(preco or 0))

                qtd_alocada = aloc.get('qtd_alocada', Decimal('0'))
                if not isinstance(qtd_alocada, Decimal):
                    qtd_alocada = Decimal(str(qtd_alocada or 0))

                pos_dict[po_id]['linhas'].append({
                    'po_line_id': aloc.get('po_line_id'),
                    'qtd_alocada': float(qtd_alocada),
                    'preco_po': float(preco),
                    'data_po': str(aloc.get('data_po')) if aloc.get('data_po') else None,
                    'ordem': aloc.get('ordem'),
                    'cod_produto_interno': r.get('cod_produto_interno'),
                    'nome_produto': item_agrupado.get('nome_produto')
                })

                # Somar valor
                pos_dict[po_id]['valor_total'] += qtd_alocada * preco

        # Ordenar por valor total (maior primeiro)
        pos_list = sorted(
            pos_dict.values(),
            key=lambda x: x['valor_total'],
            reverse=True
        )

        # Converter Decimal para float para JSON
        for po in pos_list:
            po['valor_total'] = float(po['valor_total'])

        logger.info(
            f"POs para consolidar: {len(pos_list)} POs, "
            f"total linhas: {sum(len(p['linhas']) for p in pos_list)}"
        )

        return pos_list

    # =========================================================================
    # NOVO ALGORITMO DE MATCH COM SPLIT (Multi-Item + Multi-PO)
    # =========================================================================

    def _agrupar_itens_por_codigo(
        self,
        itens_convertidos: List[Dict[str, Any]]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Agrupa itens convertidos por codigo interno.
        Soma quantidades de linhas com mesmo produto (lotes diferentes).

        Cenario: NF com 2 linhas do mesmo produto (lotes diferentes)
        - Linha 1: Produto A, lote 1, 100 un
        - Linha 2: Produto A, lote 2, 150 un
        Resultado: Produto A = 250 un total

        Retorna:
            {
                'COD001': {
                    'cod_produto_interno': 'COD001',
                    'qtd_total': Decimal('250'),
                    'preco_medio': Decimal('10.50'),
                    'linhas_nf': [
                        {'dfe_line_id': 1, 'qtd': 100, 'preco': 10.50},
                        {'dfe_line_id': 2, 'qtd': 150, 'preco': 10.50}
                    ]
                }
            }
        """
        agrupado = {}

        for item in itens_convertidos:
            cod = item.get('cod_produto_interno')
            if not cod:
                continue

            if cod not in agrupado:
                agrupado[cod] = {
                    'cod_produto_interno': cod,
                    'odoo_product_id': item.get('odoo_product_id'),
                    'nome_produto': item.get('nome_produto'),
                    'qtd_total': Decimal('0'),
                    'valor_total': Decimal('0'),
                    'linhas_nf': []
                }

            qtd = item.get('qtd_convertida', Decimal('0'))
            if not isinstance(qtd, Decimal):
                qtd = Decimal(str(qtd or 0))

            preco = item.get('preco_convertido', Decimal('0'))
            if not isinstance(preco, Decimal):
                preco = Decimal(str(preco or 0))

            agrupado[cod]['qtd_total'] += qtd
            agrupado[cod]['valor_total'] += qtd * preco
            agrupado[cod]['linhas_nf'].append({
                'dfe_line_id': item.get('dfe_line_id'),
                'qtd': qtd,
                'preco': preco,
                'fator_conversao': item.get('fator_conversao'),
                'item_original': item
            })

        # Calcular preco medio ponderado
        for cod, dados in agrupado.items():
            if dados['qtd_total'] > 0:
                dados['preco_medio'] = dados['valor_total'] / dados['qtd_total']
            else:
                dados['preco_medio'] = Decimal('0')

        logger.info(f"Itens agrupados: {len(agrupado)} produtos unicos de {len(itens_convertidos)} linhas")

        return agrupado

    def _filtrar_pos_candidatos_por_item(
        self,
        cod_produto_interno: str,
        preco_nf: Decimal,
        data_nf: date,
        pos_fornecedor: List[Dict[str, Any]],
        odoo_product_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Filtra POs candidatos para um produto especifico.

        Validacoes aplicadas (somente linhas que passam sao candidatas):
        1. Produto: linha do PO deve ter o mesmo produto
        2. Preco: 0% tolerancia (4 casas decimais)
        3. Data: tolerancia assimetrica (3 dias antes, 7 dias depois)

        Args:
            cod_produto_interno: Codigo interno do produto
            preco_nf: Preco do item na NF
            data_nf: Data de emissao da NF
            pos_fornecedor: Lista de POs do fornecedor
            odoo_product_id: ID do produto no Odoo (opcional, evita busca se fornecido)

        Retorna lista de linhas de PO validas, ORDENADAS por data ASC (mais antigo primeiro).
        """
        candidatos = []

        # OTIMIZACAO: Se ja tem o product_id, nao busca novamente
        # Isso elimina chamadas redundantes quando o ID ja foi obtido antes
        if odoo_product_id is not None:
            product_id = odoo_product_id
        else:
            product_id = self._obter_product_id(cod_produto_interno)

        if not product_id:
            logger.warning(f"Produto {cod_produto_interno} nao encontrado no Odoo (cache)")
            return []

        for po in pos_fornecedor:
            for line in po.get('lines', []):
                line_product_id = line.get('product_id', [None])[0] if line.get('product_id') else None

                if line_product_id != product_id:
                    continue

                # Validar PRECO
                preco_po = Decimal(str(line.get('price_unit', 0) or 0))
                if not self._validar_preco(preco_nf, preco_po):
                    logger.debug(
                        f"PO {po['name']} linha {line['id']}: preco diverge "
                        f"(NF={preco_nf:.4f}, PO={preco_po:.4f})"
                    )
                    continue  # Preco diverge, nao e candidato

                # Validar DATA
                data_po = self._parse_date(
                    line.get('date_planned', '') or po.get('date_planned', '')
                )
                if not self._validar_data(data_nf, data_po):
                    logger.debug(
                        f"PO {po['name']} linha {line['id']}: data diverge "
                        f"(NF={data_nf}, PO={data_po})"
                    )
                    continue  # Data fora de tolerancia

                # Calcular saldo disponivel
                qtd_po = Decimal(str(line.get('product_qty', 0) or 0))
                qtd_recebida = Decimal(str(line.get('qty_received', 0) or 0))
                saldo = qtd_po - qtd_recebida

                if saldo <= 0:
                    continue  # Sem saldo

                candidatos.append({
                    'po_id': po['id'],
                    'po_name': po['name'],
                    'po_line_id': line['id'],
                    'saldo_disponivel': saldo,
                    'preco_po': preco_po,
                    'data_po': data_po,
                    'qtd_original': qtd_po
                })

        # Ordenar por data (mais antigo primeiro)
        candidatos.sort(key=lambda x: x['data_po'] or date.max)

        logger.info(
            f"Produto {cod_produto_interno}: {len(candidatos)} POs candidatos "
            f"com preco e data validos"
        )

        return candidatos

    def _filtrar_pos_candidatos_por_item_local(
        self,
        cod_produto_interno: str,
        preco_nf: Decimal,
        data_nf: date,
        pos_fornecedor: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        🚀 VERSÃO LOCAL: Filtra POs candidatos usando codigo interno do produto.

        Diferente da versao original que usa product_id do Odoo, esta versao
        compara diretamente pelo codigo interno (cod_produto), eliminando
        completamente a necessidade de chamadas ao Odoo.

        Validacoes aplicadas:
        1. Produto: cod_produto_interno deve ser igual ao cod_produto do PO
        2. Preco: 0% tolerancia (4 casas decimais)
        3. Data: tolerancia assimetrica (3 dias antes, 7 dias depois)

        Retorna lista de linhas de PO validas, ORDENADAS por data ASC.
        """
        candidatos = []

        for po in pos_fornecedor:
            for line in po.get('lines', []):
                # COMPARACAO LOCAL: Usar _cod_produto_interno (inserido por _buscar_pos_fornecedor_local)
                line_cod_produto = line.get('_cod_produto_interno')

                # Fallback: extrair do product_id se nao tiver campo extra
                if not line_cod_produto and line.get('product_id'):
                    # product_id pode ser [id, default_code] ou apenas id
                    product_id_val = line.get('product_id')
                    if isinstance(product_id_val, list) and len(product_id_val) > 1:
                        line_cod_produto = product_id_val[1]

                if line_cod_produto != cod_produto_interno:
                    continue

                # Validar PRECO
                preco_po = Decimal(str(line.get('price_unit', 0) or 0))
                if not self._validar_preco(preco_nf, preco_po):
                    logger.debug(
                        f"PO {po['name']} linha {line['id']}: preco diverge "
                        f"(NF={preco_nf:.4f}, PO={preco_po:.4f})"
                    )
                    continue

                # Validar DATA
                data_po = self._parse_date(
                    line.get('date_planned', '') or po.get('date_planned', '')
                )
                if not self._validar_data(data_nf, data_po):
                    logger.debug(
                        f"PO {po['name']} linha {line['id']}: data diverge "
                        f"(NF={data_nf}, PO={data_po})"
                    )
                    continue

                # Saldo (pode vir pre-calculado ou calcular)
                saldo = line.get('_saldo')
                if saldo is None:
                    qtd_po = Decimal(str(line.get('product_qty', 0) or 0))
                    qtd_recebida = Decimal(str(line.get('qty_received', 0) or 0))
                    saldo = float(qtd_po - qtd_recebida)

                if saldo <= 0:
                    continue

                candidatos.append({
                    'po_id': po['id'],
                    'po_name': po['name'],
                    'po_line_id': line['id'],
                    'saldo_disponivel': Decimal(str(saldo)),
                    'preco_po': preco_po,
                    'data_po': data_po,
                    'qtd_original': Decimal(str(line.get('product_qty', 0) or 0)),
                    '_local_id': line.get('_local_id')  # ID local para referencia
                })

        # Ordenar por data (mais antigo primeiro)
        candidatos.sort(key=lambda x: x['data_po'] or date.max)

        logger.info(
            f"🚀 [LOCAL] Produto {cod_produto_interno}: {len(candidatos)} POs candidatos"
        )

        return candidatos

    def _fazer_match_com_split(
        self,
        item_agrupado: Dict[str, Any],
        candidatos: List[Dict[str, Any]],
        saldos_consumidos: Dict[int, Decimal]
    ) -> Dict[str, Any]:
        """
        Faz match de um item (agrupado) com split entre multiplos POs.

        Algoritmo:
        1. Para cada PO candidato (ordenado por data ASC):
           - Verificar saldo real (descontando ja consumido)
           - Alocar min(qtd_pendente, saldo_real)
           - Registrar alocacao
        2. Se qtd_pendente > 0:
           - Verificar tolerancia de +10%
           - Se dentro: aceita com observacao
           - Se fora: divergencia 'saldo_insuficiente'

        Args:
            item_agrupado: Item com qtd_total e linhas_nf agrupadas
            candidatos: Lista de linhas de PO candidatas (ja filtradas)
            saldos_consumidos: Dict {po_line_id: qtd_ja_alocada} para controle

        Returns:
            {
                'status': 'match' | 'saldo_insuficiente',
                'qtd_pendente': Decimal (0 se match completo),
                'alocacoes': [
                    {'po_id': 1, 'po_line_id': 10, 'qtd_alocada': 100},
                    {'po_id': 2, 'po_line_id': 20, 'qtd_alocada': 150}
                ],
                'motivo': str (se falhou)
            }
        """
        qtd_pendente = item_agrupado['qtd_total']
        alocacoes = []
        ordem = 1

        for candidato in candidatos:
            if qtd_pendente <= 0:
                break

            po_line_id = candidato['po_line_id']

            # Calcular saldo real (descontando ja consumido por outros itens)
            ja_consumido = saldos_consumidos.get(po_line_id, Decimal('0'))
            saldo_real = candidato['saldo_disponivel'] - ja_consumido

            if saldo_real <= 0:
                continue

            # Alocar o minimo entre pendente e disponivel
            qtd_alocar = min(qtd_pendente, saldo_real)

            alocacoes.append({
                'po_id': candidato['po_id'],
                'po_name': candidato['po_name'],
                'po_line_id': po_line_id,
                'qtd_alocada': qtd_alocar,
                'preco_po': candidato['preco_po'],
                'data_po': candidato['data_po'],
                'ordem': ordem
            })

            # Atualizar controles
            qtd_pendente -= qtd_alocar
            saldos_consumidos[po_line_id] = ja_consumido + qtd_alocar
            ordem += 1

            logger.debug(
                f"Alocacao: {candidato['po_name']} linha {po_line_id} = {qtd_alocar} "
                f"(pendente: {qtd_pendente})"
            )

        if qtd_pendente > 0:
            # Aplicar tolerancia de +10%
            tolerancia = item_agrupado['qtd_total'] * Decimal('0.10')
            if qtd_pendente <= tolerancia:
                # Aceita com saldo pendente dentro da tolerancia
                logger.info(
                    f"Produto {item_agrupado['cod_produto_interno']}: match com tolerancia "
                    f"(pendente={qtd_pendente:.3f}, tolerancia={tolerancia:.3f})"
                )
                return {
                    'status': 'match',
                    'qtd_pendente': qtd_pendente,
                    'alocacoes': alocacoes,
                    'observacao': f'Saldo pendente ({qtd_pendente:.3f}) dentro da tolerancia 10%'
                }
            else:
                # Saldo insuficiente
                total_disponivel = sum(a['qtd_alocada'] for a in alocacoes)
                logger.warning(
                    f"Produto {item_agrupado['cod_produto_interno']}: saldo insuficiente "
                    f"(NF={item_agrupado['qtd_total']}, disponivel={total_disponivel})"
                )
                return {
                    'status': 'saldo_insuficiente',
                    'qtd_pendente': qtd_pendente,
                    'alocacoes': alocacoes,
                    'motivo': (
                        f"Qtd NF ({item_agrupado['qtd_total']:.3f}) excede saldo POs "
                        f"({total_disponivel:.3f}) + 10% tolerancia"
                    )
                }

        logger.info(
            f"Produto {item_agrupado['cod_produto_interno']}: match completo com "
            f"{len(alocacoes)} PO(s)"
        )

        return {
            'status': 'match',
            'qtd_pendente': Decimal('0'),
            'alocacoes': alocacoes
        }

    def _registrar_match_item_com_alocacoes(
        self,
        validacao: ValidacaoNfPoDfe,
        item: Dict[str, Any],
        resultado: Dict[str, Any]
    ) -> MatchNfPoItem:
        """
        Registra resultado do match de um item COM suporte a alocacoes multi-PO.

        Cria:
        - MatchNfPoItem: registro do match (1 por linha da NF)
        - MatchAlocacao: alocacoes em POs (N por MatchNfPoItem se split)
        """
        # Criar registro do match principal
        match_item = MatchNfPoItem(
            validacao_id=validacao.id,
            odoo_dfe_line_id=item.get('dfe_line_id'),
            cod_produto_fornecedor=item.get('cod_produto_fornecedor'),
            cod_produto_interno=item.get('cod_produto_interno'),
            nome_produto=item.get('nome_produto'),
            um_nf=item.get('um_nf'),
            fator_conversao=float(item.get('fator_conversao', 1)) if item.get('fator_conversao') else 1,
            qtd_nf=float(item.get('qtd_convertida', 0)) if item.get('qtd_convertida') else 0,
            preco_nf=float(item.get('preco_convertido', 0)) if item.get('preco_convertido') else 0,
            data_nf=self._parse_date(item.get('data_nf')) if item.get('data_nf') else None,
            status_match=resultado.get('status', 'sem_po'),
            motivo_bloqueio=resultado.get('motivo'),
            criado_em=datetime.utcnow()
        )

        # Se teve match, preencher dados do PO principal (primeiro da lista)
        alocacoes = resultado.get('alocacoes', [])
        if alocacoes:
            primeiro = alocacoes[0]
            match_item.odoo_po_id = primeiro['po_id']
            match_item.odoo_po_name = primeiro['po_name']
            match_item.odoo_po_line_id = primeiro['po_line_id']
            match_item.qtd_po = float(primeiro['qtd_alocada'])
            match_item.preco_po = float(primeiro['preco_po']) if primeiro.get('preco_po') else None
            match_item.data_po = primeiro.get('data_po')

        db.session.add(match_item)
        db.session.flush()  # Obter ID para FK

        # Criar registros de alocacao (se houver)
        for aloc in alocacoes:
            alocacao = MatchAlocacao(
                match_item_id=match_item.id,
                odoo_po_id=aloc['po_id'],
                odoo_po_name=aloc['po_name'],
                odoo_po_line_id=aloc['po_line_id'],
                qtd_alocada=float(aloc['qtd_alocada']),
                preco_po=float(aloc['preco_po']) if aloc.get('preco_po') else None,
                data_po=aloc.get('data_po'),
                ordem=aloc.get('ordem', 1),
                criado_em=datetime.utcnow()
            )
            db.session.add(alocacao)

        return match_item

    def _limpar_cnpj(self, cnpj: str) -> str:
        """Remove pontuacao do CNPJ."""
        if not cnpj:
            return ''
        return ''.join(c for c in str(cnpj) if c.isdigit())

    def _parse_date(self, date_str: str) -> Optional[date]:
        """Parse string de data para date."""
        if not date_str:
            return None

        # Se ja for um objeto date, retornar diretamente
        if isinstance(date_str, date):
            return date_str

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
            except ValueError:
                continue

        # Apenas logar se nenhum formato funcionou
        logger.warning(f"Nao foi possivel parsear data: {date_str}")
        return None

    def _obter_product_id(self, cod_interno: str) -> Optional[int]:
        """
        Busca product_id no Odoo pelo codigo interno COM CACHE.

        OTIMIZACAO: Evita N+1 queries ao Odoo.
        Se a NF tem 20 itens mas apenas 5 produtos unicos,
        faz apenas 5 chamadas ao inves de 20.

        Args:
            cod_interno: Codigo interno do produto (default_code no Odoo)

        Returns:
            ID do produto no Odoo ou None se nao encontrado
        """
        # Verificar cache primeiro
        if cod_interno in self._product_cache:
            return self._product_cache[cod_interno]

        try:
            odoo = get_odoo_connection()
            product_ids = odoo.search(
                'product.product',
                [('default_code', '=', cod_interno)],
                limit=1
            )

            result = product_ids[0] if product_ids else None
            self._product_cache[cod_interno] = result

            if result:
                logger.debug(f"Produto {cod_interno} encontrado: ID {result} (cached)")
            else:
                logger.debug(f"Produto {cod_interno} NAO encontrado no Odoo (cached)")

            return result

        except Exception as e:
            logger.error(f"Erro ao buscar produto {cod_interno} no Odoo: {e}")
            self._product_cache[cod_interno] = None
            return None

    def _limpar_cache_produtos(self):
        """Limpa o cache de produtos. Chamar no inicio/fim de cada validacao."""
        self._product_cache = {}

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
            # POs vinculados (importados do Odoo)
            'odoo_po_vinculado_id': v.odoo_po_vinculado_id,
            'odoo_po_vinculado_name': v.odoo_po_vinculado_name,
            'odoo_po_fiscal_id': v.odoo_po_fiscal_id,
            'odoo_po_fiscal_name': v.odoo_po_fiscal_name,
            'pos_vinculados_importados_em': v.pos_vinculados_importados_em.isoformat() if v.pos_vinculados_importados_em else None,
            # Resultado consolidacao
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

    # =========================================================================
    # PREVIEW DE POs CANDIDATOS (REFATORADO)
    # =========================================================================

    def buscar_preview_pos_candidatos(self, odoo_dfe_id: int) -> Dict[str, Any]:
        """
        Preview de POs candidatos - 100% LOCAL (sem Odoo).

        Usa:
        - ValidacaoNfPoDfe: cabecalho DFE (dados ja importados)
        - MatchNfPoItem: itens ja convertidos (com De-Para aplicado)
        - _buscar_pos_fornecedor_local(): POs da tabela pedido_compras
        """
        try:
            logger.info(f"[PREVIEW] Buscando POs candidatos para DFE {odoo_dfe_id} (100% local)")

            # 1. Buscar dados do DFE LOCAL (sem Odoo!)
            validacao = ValidacaoNfPoDfe.query.filter_by(odoo_dfe_id=odoo_dfe_id).first()
            if not validacao:
                return {'sucesso': False, 'erro': f'DFE {odoo_dfe_id} nao encontrado localmente'}

            cnpj_fornecedor = self._limpar_cnpj(validacao.cnpj_fornecedor or '')

            # 2. Buscar itens JA CONVERTIDOS do MatchNfPoItem (sem Odoo!)
            itens_match = MatchNfPoItem.query.filter_by(validacao_id=validacao.id).all()

            if not itens_match:
                return {
                    'sucesso': True,
                    'dfe': self._montar_dfe_local(validacao, cnpj_fornecedor),
                    'itens_nf': [],
                    'pos_candidatos': [],
                    'resumo': {'itens_nf': 0, 'itens_com_depara': 0, 'itens_sem_depara': 0,
                               'itens_com_po': 0, 'itens_sem_po': 0, 'pos_candidatos': 0, 'valor_total_pos': 0}
                }

            # 3. Separar itens com/sem De-Para (dados locais!)
            itens_convertidos = []
            itens_sem_depara = []

            for item in itens_match:
                if item.cod_produto_interno:  # Tem De-Para
                    fator = Decimal(str(item.fator_conversao or 1))
                    qtd_convertida = Decimal(str(item.qtd_nf or 0))
                    preco_convertido = Decimal(str(item.preco_nf or 0))

                    itens_convertidos.append({
                        'tem_depara': True,
                        'dfe_line_id': item.odoo_dfe_line_id,
                        'cod_produto_fornecedor': item.cod_produto_fornecedor,
                        'cod_produto_interno': item.cod_produto_interno,
                        'nome_produto': item.nome_produto,
                        'qtd_original': qtd_convertida / fator if fator else qtd_convertida,
                        'qtd_convertida': qtd_convertida,
                        'um_nf': item.um_nf or '',
                        'preco_original': preco_convertido * fator if fator else preco_convertido,
                        'preco_convertido': preco_convertido,
                        'fator_conversao': fator
                    })
                else:  # Sem De-Para
                    itens_sem_depara.append({
                        'tem_depara': False,
                        'dfe_line_id': item.odoo_dfe_line_id,
                        'cod_produto_fornecedor': item.cod_produto_fornecedor,
                        'nome_produto': item.nome_produto,
                        'qtd_original': Decimal(str(item.qtd_nf or 0)),
                        'um_nf': item.um_nf or '',
                        'preco_original': Decimal(str(item.preco_nf or 0))
                    })

            # 4. Buscar POs LOCAIS (ja e local, sem Odoo)
            pos_local = self._buscar_pos_fornecedor_local(cnpj_fornecedor)

            logger.info(
                f"[PREVIEW] DFE {odoo_dfe_id}: {len(itens_convertidos)} itens com De-Para, "
                f"{len(itens_sem_depara)} sem De-Para, {len(pos_local)} POs locais"
            )

            # 5. Data da NF para validacao de data
            data_nf = validacao.data_nf  # Ja e date, nao precisa parse

            # 6. Calcular matches
            pos_candidatos = self._calcular_preview_matches(
                itens_convertidos, itens_sem_depara, pos_local, data_nf
            )

            # 7. Montar resposta
            itens_nf = self._formatar_itens_para_preview(itens_convertidos, itens_sem_depara)
            resumo = self._calcular_resumo_preview(itens_nf, pos_candidatos)

            return {
                'sucesso': True,
                'dfe': self._montar_dfe_local(validacao, cnpj_fornecedor),
                'itens_nf': itens_nf,
                'pos_candidatos': pos_candidatos,
                'resumo': resumo
            }

        except Exception as e:
            logger.error(f"Erro ao buscar preview POs candidatos: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {'sucesso': False, 'erro': str(e)}

    # Mapeamento fixo das empresas compradoras do grupo (fallback para DFEs antigos)
    EMPRESAS_COMPRADORA_FALLBACK = {
        '61724241000330': 'NACOM GOYA - CD',
        '61724241000178': 'NACOM GOYA - FB',
        '61724241000259': 'NACOM GOYA - SC',
        '18467441000163': 'LA FAMIGLIA - LF',
    }

    def _montar_dfe_local(self, validacao: ValidacaoNfPoDfe, cnpj_fornecedor: str) -> Dict[str, Any]:
        """Monta dados do DFE a partir da tabela local ValidacaoNfPoDfe."""
        # Fallback para empresa compradora quando campo nulo (DFEs antigos)
        razao_empresa = validacao.razao_empresa_compradora
        if not razao_empresa and validacao.cnpj_empresa_compradora:
            cnpj_limpo = ''.join(c for c in validacao.cnpj_empresa_compradora if c.isdigit())
            razao_empresa = self.EMPRESAS_COMPRADORA_FALLBACK.get(cnpj_limpo)

        return {
            'id': validacao.odoo_dfe_id,
            'numero_nf': validacao.numero_nf,
            'serie': validacao.serie_nf,
            'cnpj_fornecedor': cnpj_fornecedor,
            'razao_fornecedor': validacao.razao_fornecedor,
            'cnpj_empresa_compradora': validacao.cnpj_empresa_compradora,
            'razao_empresa_compradora': razao_empresa,
            'data_emissao': validacao.data_nf.isoformat() if validacao.data_nf else None,
            'valor_total': float(validacao.valor_total_nf or 0)
        }

    def _calcular_preview_matches(
        self,
        itens_convertidos: List[Dict[str, Any]],
        itens_sem_depara: List[Dict[str, Any]],
        pos_local: List[Dict[str, Any]],
        data_nf: Optional[date] = None
    ) -> List[Dict[str, Any]]:
        """
        Calcula matches e divergências para preview.

        REGRAS:
        - Apenas linhas cujo PRODUTO existe nos itens da NF são incluídas
          (linhas sem possibilidade de match são excluídas)
        - Usa as constantes CENTRALIZADAS de tolerância:
          - TOLERANCIA_QTD_PERCENTUAL (10%)
          - TOLERANCIA_PRECO_PERCENTUAL (0%)
        - Valida DATA usando _validar_data() (mesma lógica da validação real)
        """
        # Mapear códigos internos dos itens da NF
        codigos_nf = {
            item['cod_produto_interno']: item
            for item in itens_convertidos
            if item.get('cod_produto_interno')
        }

        pos_candidatos = []

        for po in pos_local:
            po_info = {
                'po_id': po.get('id'),
                'po_name': po.get('name'),
                'data_pedido': po.get('date_order'),
                'data_prevista': po.get('date_planned'),
                'estado': 'purchase',
                'valor_total': 0.0,
                'linhas': [],
                'qtd_linhas_match': 0
            }

            for line in po.get('lines', []):
                cod_interno = line.get('_cod_produto_interno')
                saldo = Decimal(str(line.get('_saldo', 0)))
                preco_po = Decimal(str(line.get('price_unit', 0)))
                qtd_pedida = Decimal(str(line.get('product_qty', 0)))
                qtd_recebida = Decimal(str(line.get('qty_received', 0)))

                # FILTRO: Só incluir linhas cujo produto existe nos itens da NF
                match_item = codigos_nf.get(cod_interno) if cod_interno else None
                if not match_item:
                    continue  # Produto não está na NF → não é candidato

                # Calcular divergências
                qtd_nf = match_item.get('qtd_convertida', Decimal('0'))
                preco_nf = match_item.get('preco_convertido', Decimal('0'))

                # Data da linha do PO
                data_po = self._parse_date(
                    line.get('date_planned', '') or po.get('date_planned', '')
                )

                divergencias = self._calcular_divergencias_preview(
                    qtd_nf, saldo, preco_nf, preco_po, data_nf, data_po
                )
                po_info['qtd_linhas_match'] += 1

                # Nome do produto
                product_info = line.get('product_id', [None, cod_interno or 'N/A'])
                if isinstance(product_info, list) and len(product_info) > 1:
                    nome_produto = product_info[1]
                else:
                    nome_produto = cod_interno or 'N/A'

                linha_info = {
                    'line_id': line.get('id'),
                    'product_id': product_info[0] if isinstance(product_info, list) else None,
                    'cod_interno': cod_interno,
                    'nome': nome_produto[:60] + '...' if len(str(nome_produto)) > 60 else nome_produto,
                    'qtd_pedida': float(qtd_pedida),
                    'qtd_recebida': float(qtd_recebida),
                    'saldo': float(saldo),
                    'preco': float(preco_po),
                    'valor_linha': float(preco_po * saldo),
                    'data_prevista': line.get('date_planned'),
                    'tem_saldo': saldo > 0,
                    'match_item_nf': match_item.get('cod_produto_fornecedor'),
                    'divergencias': divergencias
                }

                po_info['linhas'].append(linha_info)
                po_info['valor_total'] += linha_info['valor_linha']

            # Incluir apenas POs que têm linhas candidatas (com match de produto)
            if po_info['linhas']:
                pos_candidatos.append(po_info)

        return pos_candidatos

    def _calcular_divergencias_preview(
        self,
        qtd_nf: Decimal,
        saldo_po: Decimal,
        preco_nf: Decimal,
        preco_po: Decimal,
        data_nf: Optional[date] = None,
        data_po: Optional[date] = None
    ) -> Dict[str, Any]:
        """
        Calcula divergências usando tolerâncias CENTRALIZADAS.

        IMPORTANTE: Usa as mesmas regras da validação real!
        - Quantidade: TOLERANCIA_QTD_PERCENTUAL (10% para cima)
        - Preço: TOLERANCIA_PRECO_PERCENTUAL (0% - exato)
        - Data: _validar_data() (5 dias antecipado / 10 dias atrasado)
        """
        # Divergência de quantidade (NF vs Saldo PO)
        if saldo_po > 0:
            dif_qtd = qtd_nf - saldo_po
            dif_qtd_pct = ((qtd_nf - saldo_po) / saldo_po * Decimal('100'))
        else:
            dif_qtd = qtd_nf
            dif_qtd_pct = Decimal('100')

        # Divergência de preço
        if preco_po > 0:
            dif_preco = preco_nf - preco_po
            dif_preco_pct = ((preco_nf - preco_po) / preco_po * Decimal('100'))
        else:
            dif_preco = preco_nf
            dif_preco_pct = Decimal('100') if preco_nf > 0 else Decimal('0')

        # Validação de data (mesma lógica de _validar_data)
        data_ok = self._validar_data(data_nf, data_po) if data_nf else True

        return {
            'qtd_nf': float(qtd_nf),
            'preco_nf': float(preco_nf),
            # Nomes usados pelo frontend JS (divergencias_nf_po.js)
            'qtd_nf_convertida': float(qtd_nf),
            'preco_nf_convertido': float(preco_nf),
            'dif_qtd': round(float(dif_qtd), 3),
            'dif_qtd_pct': round(float(dif_qtd_pct), 2),
            'dif_preco': round(float(dif_preco), 4),
            'dif_preco_pct': round(float(dif_preco_pct), 2),
            'data_nf': str(data_nf) if data_nf else None,
            'data_po': str(data_po) if data_po else None,
            # Usa constantes centralizadas e métodos reais
            'qtd_ok': dif_qtd_pct <= TOLERANCIA_QTD_PERCENTUAL,
            'preco_ok': abs(dif_preco_pct) <= TOLERANCIA_PRECO_PERCENTUAL,
            'data_ok': data_ok
        }

    def _formatar_itens_para_preview(
        self,
        itens_convertidos: List[Dict[str, Any]],
        itens_sem_depara: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Formata itens para resposta JSON do preview."""
        itens_nf = []

        for item in itens_convertidos:
            itens_nf.append({
                'dfe_line_id': item['dfe_line_id'],
                'nitem': item.get('nitem'),
                'cod_produto_fornecedor': item['cod_produto_fornecedor'],
                'nome_produto': item['nome_produto'],
                'qtd_nf': float(item['qtd_original']),
                'preco_nf': float(item['preco_original']),
                'um_nf': item.get('um_nf', ''),
                'tem_depara': True,
                'cod_produto_interno': item['cod_produto_interno'],
                'fator_conversao': float(item['fator_conversao']),
                'qtd_convertida': float(item['qtd_convertida']),
                'preco_convertido': float(item['preco_convertido'])
            })

        for item in itens_sem_depara:
            itens_nf.append({
                'dfe_line_id': item['dfe_line_id'],
                'nitem': item.get('nitem'),
                'cod_produto_fornecedor': item['cod_produto_fornecedor'],
                'nome_produto': item['nome_produto'],
                'qtd_nf': float(item['qtd_original']),
                'preco_nf': float(item['preco_original']),
                'um_nf': item.get('um_nf', ''),
                'tem_depara': False,
                'cod_produto_interno': None,
                'fator_conversao': 1,
                'qtd_convertida': float(item['qtd_original']),
                'preco_convertido': float(item['preco_original'])
            })

        return itens_nf

    def _calcular_resumo_preview(
        self,
        itens_nf: List[Dict[str, Any]],
        pos_candidatos: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Calcula estatísticas do preview."""
        # Contar itens com PO (que têm match em algum PO candidato)
        itens_com_po = sum(
            1 for item in itens_nf
            if item.get('cod_produto_interno') and
            any(
                any(l.get('match_item_nf') == item['cod_produto_fornecedor'] for l in po['linhas'])
                for po in pos_candidatos
            )
        )

        return {
            'itens_nf': len(itens_nf),
            'itens_com_depara': sum(1 for i in itens_nf if i.get('tem_depara')),
            'itens_sem_depara': sum(1 for i in itens_nf if not i.get('tem_depara')),
            'itens_com_po': itens_com_po,
            'itens_sem_po': len(itens_nf) - itens_com_po,
            'pos_candidatos': len(pos_candidatos),
            'valor_total_pos': sum(po.get('valor_total', 0) for po in pos_candidatos)
        }
