"""
Job de Validacao de Recebimento - FASE 1 + FASE 2
=================================================

Executado pelo scheduler a cada 30 minutos.
Executa AMBAS as validacoes:
- Fase 1: Validacao Fiscal
- Fase 2: Validacao NF x PO

Tambem executa sincronizacoes:
- De-Para: Odoo -> Sistema (product.supplierinfo)
- POs Vinculados: Atualiza DFEs que receberam PO no Odoo

OTIMIZAÇÃO: Skip Inteligente (v2.0)
===================================
Para reduzir tempo de execução de ~90s para ~5-15s:
- Detecta POs modificadas após última validação
- Marca DFEs afetados com flag po_modificada_apos_validacao=True
- Skip DFEs aprovados se PO não foi modificada
- Skip DFEs finalizados no Odoo
- Reprocessa apenas quando algo REALMENTE mudou

Fluxo:
1. Sync De-Para do Odoo (product.supplierinfo)
2. Sync POs vinculados (DFEs sem PO -> verifica se Odoo agora tem)
3. Buscar DFEs de compra com SKIP INTELIGENTE
4. Para cada DFE que PRECISA processar:
   a) Executar validacao fiscal (Fase 1)
   b) Executar validacao NF x PO (Fase 2)
   c) Ambas devem aprovar para DFE ser liberado

Referencia:
- .claude/references/RECEBIMENTO_MATERIAIS.md
- .claude/plans/hashed-noodling-zebra.md (otimização inteligente)
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any

from flask import current_app
from app import db
from app.recebimento.models import ValidacaoFiscalDfe, ValidacaoNfPoDfe
from app.recebimento.services.validacao_fiscal_service import ValidacaoFiscalService
from app.recebimento.services.validacao_nf_po_service import ValidacaoNfPoService
from app.recebimento.services.depara_service import DeparaService
from app.odoo.utils.connection import get_odoo_connection

logger = logging.getLogger(__name__)

# Configuracoes
JANELA_MINUTOS = 2880  # Buscar DFEs das ultimas 48 horas
SYNC_DEPARA_LIMIT = 200  # Limite de registros para sync De-Para

# CNPJs do grupo a serem ignorados (empresas proprias - Nacom, Goya)
CNPJS_IGNORAR = [
    '61724241',  # Nacom
    '18467441',  # Goya
]


class ValidacaoRecebimentoJob:
    """
    Job unificado para validacao de recebimento.

    Executa Fase 1 (Fiscal) e Fase 2 (NF x PO) em paralelo.
    Tambem sincroniza De-Para do Odoo.
    """

    def __init__(self):
        self.odoo = None
        self.service_fiscal = ValidacaoFiscalService()
        self.service_nf_po = ValidacaoNfPoService()
        self.service_depara = DeparaService()

    def _get_odoo(self):
        """Obtem conexao Odoo lazy"""
        if self.odoo is None:
            self.odoo = get_odoo_connection()
            if not self.odoo.authenticate():
                raise Exception("Falha na autenticacao com Odoo")
        return self.odoo

    def executar(self, minutos_janela: int = None) -> Dict[str, Any]:
        """
        Executa job completo de validacao de recebimento.

        Args:
            minutos_janela: Janela de tempo em minutos (default: JANELA_MINUTOS)

        Returns:
            Dict com resultados de todas as etapas
        """
        janela = minutos_janela or JANELA_MINUTOS

        resultado = {
            'sucesso': True,
            'sync_depara': {},
            'sync_pos_vinculados': {},
            'fase1_fiscal': {},
            'fase2_nf_po': {},
            'dfes_processados': 0,
            'erro': None
        }

        try:
            logger.info(f"=== INICIANDO JOB DE VALIDACAO DE RECEBIMENTO ===")
            logger.info(f"Janela: {janela} minutos")

            # 1. SYNC DE-PARA (Odoo -> Sistema)
            logger.info("[1/4] Sincronizando De-Para do Odoo...")
            resultado['sync_depara'] = self._sync_depara_odoo()

            # 2. SYNC POs VINCULADOS (DFEs sem PO -> verifica se Odoo agora tem)
            logger.info("[2/4] Sincronizando POs vinculados do Odoo...")
            resultado['sync_pos_vinculados'] = self._sync_pos_vinculados()

            # 3. BUSCAR DFEs PENDENTES
            logger.info("[3/4] Buscando DFEs de compra pendentes...")
            dfes = self._buscar_dfes_pendentes(janela)

            if not dfes:
                logger.info("Nenhum DFE de compra pendente encontrado")
                return resultado

            logger.info(f"Encontrados {len(dfes)} DFEs para processar")

            # 4. PROCESSAR CADA DFE (Fase 1 + Fase 2)
            logger.info("[4/4] Processando validacoes...")

            resultado['fase1_fiscal'] = {
                'dfes_validados': 0,
                'dfes_aprovados': 0,
                'dfes_bloqueados': 0,
                'dfes_primeira_compra': 0,
                'dfes_erro': 0
            }

            resultado['fase2_nf_po'] = {
                'dfes_validados': 0,
                'dfes_aprovados': 0,
                'dfes_bloqueados': 0,
                'dfes_erro': 0
            }

            # Processamento sequencial (skip inteligente reduz volume)
            for dfe in dfes:
                try:
                    res = self._processar_dfe_completo(dfe)
                    resultado['dfes_processados'] += 1

                    # Contabilizar Fase 1
                    if res.get('fase1'):
                        resultado['fase1_fiscal']['dfes_validados'] += 1
                        status1 = res['fase1'].get('status')
                        if status1 == 'aprovado':
                            resultado['fase1_fiscal']['dfes_aprovados'] += 1
                        elif status1 == 'bloqueado':
                            resultado['fase1_fiscal']['dfes_bloqueados'] += 1
                        elif status1 == 'primeira_compra':
                            resultado['fase1_fiscal']['dfes_primeira_compra'] += 1
                        elif status1 == 'erro':
                            resultado['fase1_fiscal']['dfes_erro'] += 1

                    # Contabilizar Fase 2
                    if res.get('fase2'):
                        resultado['fase2_nf_po']['dfes_validados'] += 1
                        status2 = res['fase2'].get('status')
                        if status2 == 'aprovado':
                            resultado['fase2_nf_po']['dfes_aprovados'] += 1
                        elif status2 == 'bloqueado':
                            resultado['fase2_nf_po']['dfes_bloqueados'] += 1
                        elif status2 == 'erro':
                            resultado['fase2_nf_po']['dfes_erro'] += 1

                except Exception as e:
                    logger.error(f"Erro ao processar DFE {dfe.get('id')}: {e}")
                    resultado['fase1_fiscal']['dfes_erro'] += 1
                    resultado['fase2_nf_po']['dfes_erro'] += 1

            logger.info("=== JOB DE VALIDACAO CONCLUIDO ===")
            logger.info(
                f"Resultados: "
                f"DFEs={resultado['dfes_processados']}, "
                f"Fase1.aprovados={resultado['fase1_fiscal']['dfes_aprovados']}, "
                f"Fase2.aprovados={resultado['fase2_nf_po']['dfes_aprovados']}"
            )

        except Exception as e:
            logger.error(f"Erro no job de validacao: {e}")
            resultado['sucesso'] = False
            resultado['erro'] = str(e)

        return resultado

    def _sync_depara_odoo(self) -> Dict[str, Any]:
        """
        Sincroniza De-Para do Odoo para o Sistema.
        Importa product.supplierinfo que tenham product_code preenchido.
        """
        try:
            resultado = self.service_depara.importar_do_odoo(limit=SYNC_DEPARA_LIMIT)

            logger.info(
                f"Sync De-Para: importados={resultado.get('importados', 0)}, "
                f"atualizados={resultado.get('atualizados', 0)}, "
                f"erros={resultado.get('erros', 0)}"
            )

            return resultado

        except Exception as e:
            logger.error(f"Erro no sync De-Para: {e}")
            return {'erro': str(e)}

    def _sync_pos_vinculados(self) -> Dict[str, Any]:
        """
        Sincroniza POs vinculados do Odoo para DFEs que nao tinham PO.

        Busca 3 caminhos (em ordem):
        1. DFE.purchase_id (many2one direto - 14.6% dos casos)
        2. DFE.purchase_fiscal_id (many2one escrituracao)
        3. PO.dfe_id = DFE.id (caminho inverso - 85.4% dos casos em status=04)

        Isso cobre cenarios:
        - DFE chegou sem PO vinculado
        - Usuario vinculou PO manualmente no Odoo
        - PO.dfe_id preenchido mas DFE.purchase_id nao (caminho principal)
        """
        resultado = {
            'dfes_verificados': 0,
            'dfes_atualizados': 0,
            'dfes_sem_po': 0,
            'erros': 0
        }

        try:
            # Buscar validacoes sem PO vinculado
            validacoes_sem_po = ValidacaoNfPoDfe.query.filter(
                ValidacaoNfPoDfe.odoo_po_vinculado_id.is_(None),
                ValidacaoNfPoDfe.odoo_po_fiscal_id.is_(None)
            ).all()

            if not validacoes_sem_po:
                logger.info("Sync POs: Nenhum DFE sem PO vinculado")
                return resultado

            logger.info(f"Sync POs: Verificando {len(validacoes_sem_po)} DFEs sem PO")
            resultado['dfes_verificados'] = len(validacoes_sem_po)

            # Coletar IDs para consulta em batch no Odoo
            dfe_ids = [v.odoo_dfe_id for v in validacoes_sem_po]

            odoo = self._get_odoo()

            # CAMINHO 1+2: Consultar DFEs no Odoo (purchase_id, purchase_fiscal_id)
            dfes_odoo = odoo.search_read(
                'l10n_br_ciel_it_account.dfe',
                [['id', 'in', dfe_ids]],
                fields=['id', 'purchase_id', 'purchase_fiscal_id']
            )

            dfe_map = {d['id']: d for d in dfes_odoo} if dfes_odoo else {}

            # CAMINHO 3: Buscar POs que apontam dfe_id para esses DFEs (batch)
            pos_por_dfe = {}
            if dfe_ids:
                pos_com_dfe = odoo.search_read(
                    'purchase.order',
                    [['dfe_id', 'in', dfe_ids]],
                    fields=['id', 'name', 'dfe_id', 'invoice_status']
                )
                if pos_com_dfe:
                    for po in pos_com_dfe:
                        dfe_id_vinculado = po['dfe_id'][0] if po.get('dfe_id') else None
                        if dfe_id_vinculado:
                            pos_por_dfe[dfe_id_vinculado] = po

            logger.info(
                f"Sync POs: {len(dfe_map)} DFEs no Odoo, "
                f"{len(pos_por_dfe)} POs via dfe_id"
            )

            # Processar validacoes
            for validacao in validacoes_sem_po:
                try:
                    tem_po = False
                    dfe_data = dfe_map.get(validacao.odoo_dfe_id, {})

                    # Caminho 1: purchase_id (vínculo direto no DFE)
                    purchase_id_data = dfe_data.get('purchase_id')
                    if purchase_id_data and isinstance(purchase_id_data, (list, tuple)):
                        validacao.odoo_po_vinculado_id = purchase_id_data[0]
                        validacao.odoo_po_vinculado_name = (
                            purchase_id_data[1] if len(purchase_id_data) > 1 else None
                        )
                        tem_po = True
                        logger.info(
                            f"DFE {validacao.odoo_dfe_id}: PO vinculado encontrado - "
                            f"{validacao.odoo_po_vinculado_name}"
                        )

                        # NOVO: Atualizar PedidoCompras com dfe_id
                        self._atualizar_pedido_compras_dfe(
                            po_name=validacao.odoo_po_vinculado_name,
                            dfe_id=validacao.odoo_dfe_id,
                            numero_nf=validacao.numero_nf,
                            chave_nfe=validacao.chave_nfe
                        )

                        # NOVO: Vínculo direto significa fatura gerada - marcar como finalizado
                        validacao.status = 'finalizado_odoo'
                        logger.info(
                            f"DFE {validacao.odoo_dfe_id}: Status alterado para finalizado_odoo "
                            f"(PO {validacao.odoo_po_vinculado_name} via purchase_id direto)"
                        )

                    # Caminho 2: purchase_fiscal_id (vínculo fiscal no DFE)
                    if not tem_po:
                        purchase_fiscal_data = dfe_data.get('purchase_fiscal_id')
                        if purchase_fiscal_data and isinstance(purchase_fiscal_data, (list, tuple)):
                            validacao.odoo_po_fiscal_id = purchase_fiscal_data[0]
                            validacao.odoo_po_fiscal_name = (
                                purchase_fiscal_data[1] if len(purchase_fiscal_data) > 1 else None
                            )
                            tem_po = True
                            logger.info(
                                f"DFE {validacao.odoo_dfe_id}: PO fiscal encontrado - "
                                f"{validacao.odoo_po_fiscal_name}"
                            )

                            # NOVO: Atualizar PedidoCompras com dfe_id
                            self._atualizar_pedido_compras_dfe(
                                po_name=validacao.odoo_po_fiscal_name,
                                dfe_id=validacao.odoo_dfe_id,
                                numero_nf=validacao.numero_nf,
                                chave_nfe=validacao.chave_nfe
                            )

                            # NOVO: Vínculo fiscal direto significa fatura gerada - marcar como finalizado
                            validacao.status = 'finalizado_odoo'
                            logger.info(
                                f"DFE {validacao.odoo_dfe_id}: Status alterado para finalizado_odoo "
                                f"(PO {validacao.odoo_po_fiscal_name} via purchase_fiscal_id direto)"
                            )

                    # Caminho 3: PO.dfe_id (inverso)
                    if not tem_po:
                        po_inverso = pos_por_dfe.get(validacao.odoo_dfe_id)
                        if po_inverso:
                            validacao.odoo_po_vinculado_id = po_inverso['id']
                            validacao.odoo_po_vinculado_name = po_inverso['name']
                            tem_po = True
                            logger.info(
                                f"DFE {validacao.odoo_dfe_id}: PO vinculado via PO.dfe_id - "
                                f"{po_inverso['name']}"
                            )

                            # NOVO: Atualizar PedidoCompras com dfe_id para manter compatibilidade
                            self._atualizar_pedido_compras_dfe(
                                po_name=po_inverso['name'],
                                dfe_id=validacao.odoo_dfe_id,
                                numero_nf=validacao.numero_nf,
                                chave_nfe=validacao.chave_nfe
                            )

                            # NOVO: Se PO já está faturado, marcar como finalizado_odoo
                            if po_inverso.get('invoice_status') == 'invoiced':
                                validacao.status = 'finalizado_odoo'
                                logger.info(
                                    f"DFE {validacao.odoo_dfe_id}: Status alterado para finalizado_odoo "
                                    f"(PO {po_inverso['name']} já faturado via invoice_status)"
                                )

                    if tem_po:
                        validacao.pos_vinculados_importados_em = datetime.utcnow()
                        resultado['dfes_atualizados'] += 1

                        # Gap 3 FIX: Marcar para revalidação se DFE já tinha sido processado
                        # Quando PO é vinculado pela primeira vez a um DFE que já foi validado,
                        # precisamos reprocessar para considerar a nova PO
                        if validacao.status in ('bloqueado', 'aprovado'):
                            validacao.po_modificada_apos_validacao = True
                            logger.info(
                                f"⚠️ DFE {validacao.odoo_dfe_id} marcado para revalidação "
                                f"(PO vinculado via sync)"
                            )
                    else:
                        resultado['dfes_sem_po'] += 1

                except Exception as e:
                    logger.error(
                        f"Erro ao processar DFE {validacao.odoo_dfe_id}: {e}"
                    )
                    resultado['erros'] += 1

            # Commit das alteracoes
            db.session.commit()

            logger.info(
                f"Sync POs: atualizados={resultado['dfes_atualizados']}, "
                f"sem_po={resultado['dfes_sem_po']}, "
                f"erros={resultado['erros']}"
            )

            return resultado

        except Exception as e:
            logger.error(f"Erro no sync POs vinculados: {e}")
            db.session.rollback()
            return {'erro': str(e)}

    def _atualizar_pedido_compras_dfe(
        self,
        po_name: str,
        dfe_id: int,
        numero_nf: str = None,
        chave_nfe: str = None
    ) -> int:
        """
        Atualiza PedidoCompras com dfe_id para manter compatibilidade entre tabelas.

        Quando um vínculo PO ↔ DFE é detectado no Odoo (via PO.dfe_id),
        atualizamos também a tabela pedido_compras para manter os dados sincronizados.

        Args:
            po_name: Nome do PO (ex: 'C2512302')
            dfe_id: ID do DFE no Odoo
            numero_nf: Número da NF (opcional)
            chave_nfe: Chave de acesso da NF-e (opcional)

        Returns:
            Número de registros atualizados
        """
        try:
            from app.manufatura.models import PedidoCompras

            pedidos_compra = PedidoCompras.query.filter_by(
                num_pedido=po_name
            ).all()

            if not pedidos_compra:
                return 0

            dfe_id_str = str(dfe_id)
            atualizados = 0

            for pc in pedidos_compra:
                if pc.dfe_id != dfe_id_str:
                    pc.dfe_id = dfe_id_str
                    if numero_nf:
                        pc.nf_numero = numero_nf
                    if chave_nfe:
                        pc.nf_chave_acesso = chave_nfe
                    atualizados += 1

            if atualizados > 0:
                logger.info(
                    f"PedidoCompras {po_name}: Atualizado dfe_id={dfe_id_str} "
                    f"({atualizados} linhas)"
                )

            return atualizados

        except Exception as e:
            logger.warning(
                f"Erro ao atualizar PedidoCompras para PO {po_name}: {e}"
            )
            return 0

    def _deve_reprocessar_dfe(self, dfe: Dict, validacao: ValidacaoNfPoDfe) -> bool:
        """
        Decide INTELIGENTEMENTE se um DFE deve ser reprocessado na Fase 2.

        Regras de Skip:
        - finalizado_odoo → SKIP (PO já vinculado no Odoo)
        - aprovado + po_modificada=False → SKIP (nada mudou)

        Regras de Reprocessamento:
        - po_modificada_apos_validacao=True → REPROCESSAR (PO usada foi modificada)
        - status pendente/erro/validando → REPROCESSAR (não concluiu)
        - bloqueado + divergências resolvidas → REPROCESSAR (pode aprovar agora)

        Args:
            dfe: Dict com dados do DFE do Odoo
            validacao: Instância de ValidacaoNfPoDfe

        Returns:
            True se deve reprocessar, False se pode skip
        """
        from app.recebimento.models import DivergenciaNfPo

        dfe_id = dfe.get('id')

        # 1. SKIP se finalizado no Odoo (tem PO vinculado diretamente)
        if validacao.status == 'finalizado_odoo':
            logger.debug(f"DFE {dfe_id}: SKIP (finalizado_odoo)")
            return False

        # 2. REPROCESSAR se PO foi modificada após validação
        if validacao.po_modificada_apos_validacao:
            logger.info(f"DFE {dfe_id}: REPROCESSAR (PO modificada após validação)")
            return True

        # 3. SKIP se aprovado e PO não modificada
        if validacao.status == 'aprovado':
            logger.debug(f"DFE {dfe_id}: SKIP (aprovado, PO não modificada)")
            return False

        # 4. Status que sempre precisam reprocessar
        if validacao.status in ('pendente', 'erro', 'validando'):
            logger.debug(f"DFE {dfe_id}: REPROCESSAR (status={validacao.status})")
            return True

        # 5. BLOQUEADO - verificar se divergências foram resolvidas
        if validacao.status == 'bloqueado':
            divergencias_pendentes = DivergenciaNfPo.query.filter(
                DivergenciaNfPo.validacao_id == validacao.id,
                DivergenciaNfPo.status == 'pendente'
            ).count()

            if divergencias_pendentes == 0:
                logger.info(f"DFE {dfe_id}: REPROCESSAR (divergências resolvidas)")
                return True
            else:
                logger.debug(f"DFE {dfe_id}: SKIP ({divergencias_pendentes} divergências pendentes)")
                return False

        # 6. Consolidado - não reprocessar
        if validacao.status == 'consolidado':
            logger.debug(f"DFE {dfe_id}: SKIP (consolidado)")
            return False

        # DEFAULT: Skip por segurança (status desconhecido)
        logger.debug(f"DFE {dfe_id}: SKIP (status={validacao.status} - default)")
        return False

    def _buscar_dfes_pendentes(self, minutos_janela: int) -> List[Dict]:
        """
        Busca DFEs de compra que ainda nao foram validados.

        Criterios:
        - Tipo: compra
        - Estado: processado (04)
        - Data de modificacao: dentro da janela
        - Nao e devolucao nem CTe
        - Nao pertence ao grupo (Nacom/Goya)
        """
        odoo = self._get_odoo()

        # Calcular data limite
        data_limite = datetime.utcnow() - timedelta(minutes=minutos_janela)
        data_limite_str = data_limite.strftime('%Y-%m-%d %H:%M:%S')

        filtro = [
            ['l10n_br_tipo_pedido', '=', 'compra'],
            ['l10n_br_status', '=', '04'],
            ['nfe_infnfe_ide_finnfe', '!=', '4'],  # Excluir devolucoes
            ['is_cte', '=', False],  # Apenas NF-e
            ['write_date', '>=', data_limite_str]
        ]

        dfes_odoo = odoo.search_read(
            'l10n_br_ciel_it_account.dfe',
            filtro,
            fields=[
                'id', 'name', 'nfe_infnfe_ide_nnf', 'nfe_infnfe_ide_serie',
                'protnfe_infnfe_chnfe',
                'nfe_infnfe_emit_cnpj', 'nfe_infnfe_emit_xnome',
                'nfe_infnfe_ide_dhemi',
                'nfe_infnfe_total_icmstot_vnf',
                'write_date'
            ],
            limit=100
        )

        if not dfes_odoo:
            return []

        # Ordenar por write_date desc
        dfes_odoo.sort(key=lambda x: x.get('write_date', ''), reverse=True)

        # Filtrar CNPJs do grupo
        dfes_filtrados = []
        for dfe in dfes_odoo:
            cnpj = dfe.get('nfe_infnfe_emit_cnpj', '')
            cnpj_limpo = ''.join(c for c in cnpj if c.isdigit())

            ignorar = any(cnpj_limpo.startswith(p) for p in CNPJS_IGNORAR)
            if not ignorar:
                dfes_filtrados.append(dfe)

        # Filtrar DFEs ja processados em AMBAS as fases
        dfe_ids = [d['id'] for d in dfes_filtrados]

        # Fase 1: ja validados (status != pendente/erro)
        fase1_processados = set(
            r.odoo_dfe_id for r in ValidacaoFiscalDfe.query.filter(
                ValidacaoFiscalDfe.odoo_dfe_id.in_(dfe_ids),
                ValidacaoFiscalDfe.status.notin_(['pendente', 'erro'])
            ).all()
        )

        # === SKIP INTELIGENTE (Fase 2) ===
        # Buscar todas as validações de Fase 2 para esses DFEs
        validacoes_fase2 = {
            v.odoo_dfe_id: v
            for v in ValidacaoNfPoDfe.query.filter(
                ValidacaoNfPoDfe.odoo_dfe_id.in_(dfe_ids)
            ).all()
        }

        dfes_para_processar = []
        dfes_skipped = 0

        for dfe in dfes_filtrados:
            dfe_id = dfe['id']
            validacao = validacoes_fase2.get(dfe_id)

            # Fase 1 ainda não foi feita -> processar
            if dfe_id not in fase1_processados:
                dfes_para_processar.append(dfe)
                continue

            # Fase 2: nunca validado -> processar
            if validacao is None:
                dfes_para_processar.append(dfe)
                continue

            # Fase 2: verificar se precisa reprocessar (skip inteligente)
            if self._deve_reprocessar_dfe(dfe, validacao):
                dfes_para_processar.append(dfe)
            else:
                dfes_skipped += 1

        logger.info(
            f"⚡ Skip inteligente: {dfes_skipped} DFEs skipped, "
            f"{len(dfes_para_processar)} DFEs para processar"
        )

        return dfes_para_processar

    def _processar_dfe_completo(self, dfe: Dict) -> Dict[str, Any]:
        """
        Processa um DFE executando AMBAS as validacoes.

        Fase 1 e Fase 2 sao executadas independentemente.
        O DFE so esta "liberado" se AMBAS aprovarem.
        """
        dfe_id = dfe.get('id')
        numero_nf = dfe.get('nfe_infnfe_ide_nnf')
        razao = dfe.get('nfe_infnfe_emit_xnome', '')

        logger.info(f"Processando DFE {dfe_id} - NF {numero_nf} ({razao})")

        resultado = {
            'dfe_id': dfe_id,
            'fase1': None,
            'fase2': None
        }

        # FASE 1: Validacao Fiscal
        try:
            resultado['fase1'] = self._executar_fase1(dfe)
        except Exception as e:
            logger.error(f"Erro Fase 1 DFE {dfe_id}: {e}")
            resultado['fase1'] = {'status': 'erro', 'erro': str(e)}

        # FASE 2: Validacao NF x PO
        try:
            resultado['fase2'] = self._executar_fase2(dfe)
        except Exception as e:
            logger.error(f"Erro Fase 2 DFE {dfe_id}: {e}")
            resultado['fase2'] = {'status': 'erro', 'erro': str(e)}

        # Log resultado combinado
        status1 = resultado['fase1'].get('status', 'erro') if resultado['fase1'] else 'erro'
        status2 = resultado['fase2'].get('status', 'erro') if resultado['fase2'] else 'erro'

        logger.info(
            f"DFE {dfe_id} processado: "
            f"Fase1={status1}, Fase2={status2}"
        )

        return resultado

    def _executar_fase1(self, dfe: Dict) -> Dict[str, Any]:
        """Executa validacao fiscal (Fase 1)"""
        dfe_id = dfe.get('id')
        numero_nf = dfe.get('nfe_infnfe_ide_nnf')
        chave_nfe = dfe.get('protnfe_infnfe_chnfe')
        cnpj = dfe.get('nfe_infnfe_emit_cnpj', '')
        razao = dfe.get('nfe_infnfe_emit_xnome', '')

        cnpj_limpo = ''.join(c for c in cnpj if c.isdigit())

        # Criar/atualizar registro de controle
        registro = ValidacaoFiscalDfe.query.filter_by(odoo_dfe_id=dfe_id).first()
        if not registro:
            registro = ValidacaoFiscalDfe(
                odoo_dfe_id=dfe_id,
                numero_nf=numero_nf,
                chave_nfe=chave_nfe,
                cnpj_fornecedor=cnpj_limpo,
                razao_fornecedor=razao,
                status='validando'
            )
            db.session.add(registro)
        else:
            registro.status = 'validando'

        db.session.commit()

        # Executar validacao
        resultado = self.service_fiscal.validar_nf(dfe_id)

        # Atualizar status
        status = resultado.get('status', 'erro')
        registro.status = status
        registro.total_linhas = resultado.get('linhas_validadas', 0)
        registro.linhas_divergentes = len(resultado.get('divergencias', []))
        registro.linhas_primeira_compra = len(resultado.get('primeira_compra', []))
        registro.linhas_aprovadas = (
            registro.total_linhas -
            registro.linhas_divergentes -
            registro.linhas_primeira_compra
        )
        registro.validado_em = datetime.utcnow()
        registro.atualizado_em = datetime.utcnow()

        if resultado.get('erro'):
            registro.erro_mensagem = resultado['erro']

        db.session.commit()

        return {'status': status, 'detalhes': resultado}

    def _executar_fase2(self, dfe: Dict) -> Dict[str, Any]:
        """Executa validacao NF x PO (Fase 2)"""
        dfe_id = dfe.get('id')

        # Executar validacao
        resultado = self.service_nf_po.validar_dfe(dfe_id)

        return resultado


# Funcao de conveniencia para uso no scheduler
def executar_validacao_recebimento(minutos_janela: int = None) -> Dict[str, Any]:
    """
    Funcao de conveniencia para executar o job de validacao de recebimento.
    Usada pelo scheduler.

    Args:
        minutos_janela: Janela de tempo em minutos

    Returns:
        Resultado da execucao
    """
    job = ValidacaoRecebimentoJob()
    return job.executar(minutos_janela)


# Manter compatibilidade com job antigo
def executar_validacao_fiscal(minutos_janela: int = None) -> Dict[str, Any]:
    """
    Wrapper de compatibilidade.
    Chama o novo job unificado.
    """
    return executar_validacao_recebimento(minutos_janela)
