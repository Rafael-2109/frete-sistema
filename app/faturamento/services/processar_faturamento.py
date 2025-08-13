"""
Processamento de Faturamento Simplificado
========================================

Implementação simplificada e otimizada do processamento de NFs
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from decimal import Decimal
from app.estoque.services.estoque_tempo_real import ServicoEstoqueTempoReal
from app import db
from app.faturamento.models import FaturamentoProduto, RelatorioFaturamentoImportado
from app.estoque.models import MovimentacaoEstoque
from app.separacao.models import Separacao
from app.embarques.models import Embarque, EmbarqueItem
from app.carteira.models import FaturamentoParcialJustificativa, InconsistenciaFaturamento

logger = logging.getLogger(__name__)


class ProcessadorFaturamento:
    """
    Processador simplificado de faturamento
    """

    def processar_nfs_importadas(
        self, usuario: str = "Importação Odoo", limpar_inconsistencias: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Processa todas as NFs importadas seguindo lógica simplificada
        COM MELHORIAS: Commits incrementais e tratamento de erros isolados
        """
        resultado = {
            "processadas": 0,
            "ja_processadas": 0,
            "canceladas": 0,
            "com_embarque": 0,
            "sem_separacao": 0,
            "erros": [],
            "detalhes": [],
            "movimentacoes_criadas": 0,
            "embarque_items_atualizados": 0
        }

        try:
            # 0. Limpar inconsistências anteriores se solicitado
            if limpar_inconsistencias:
                logger.info("🧹 Limpando inconsistências anteriores...")
                try:
                    # Limpar todas as inconsistências não resolvidas
                    # Mantém as resolvidas como histórico
                    deletadas = InconsistenciaFaturamento.query.filter_by(resolvida=False).delete()
                    db.session.commit()
                    logger.info(f"✅ {deletadas} inconsistências não resolvidas removidas antes do processamento")
                except Exception as e:
                    logger.warning(f"⚠️ Erro ao limpar inconsistências: {e}")
                    db.session.rollback()

            # 1. Buscar TODAS as NFs ativas
            nfs_pendentes = self._buscar_nfs_pendentes()
            logger.info(f"📊 Total de NFs para processar: {len(nfs_pendentes)}")

            for idx, nf in enumerate(nfs_pendentes):
                try:
                    logger.info(
                        f"🔄 [{idx+1}/{len(nfs_pendentes)}] Processando NF {nf.numero_nf} - Pedido: {nf.origem}"
                    )

                    # 1.A - Já tem movimentação com separacao_lote_id?
                    if self._tem_movimentacao_com_lote(nf.numero_nf):
                        logger.info(f"✅ NF {nf.numero_nf} já processada com lote - pulando")
                        resultado["ja_processadas"] += 1
                        continue

                    # 1.B - NF Cancelada?
                    if self._nf_cancelada(nf):
                        self._processar_cancelamento(nf)
                        resultado["canceladas"] += 1
                        logger.info(f"🚫 NF {nf.numero_nf} cancelada - movimentações removidas")
                        # MELHORIA: Commit incremental para cancelamentos
                        try:
                            db.session.commit()
                        except:
                            db.session.rollback()
                        continue

                    # 1.C - Processar NF (com ou sem movimentação "Sem Separação")
                    processou, mov_criadas, emb_atualizados = self._processar_nf(nf, usuario)
                    if processou:
                        resultado["processadas"] += 1
                        resultado["movimentacoes_criadas"] += mov_criadas
                        resultado["embarque_items_atualizados"] += emb_atualizados
                        
                        # MELHORIA: Commit incremental após cada NF processada com sucesso
                        try:
                            db.session.commit()
                            logger.debug(f"✅ NF {nf.numero_nf} commitada com sucesso")
                        except Exception as commit_error:
                            logger.error(f"❌ Erro no commit da NF {nf.numero_nf}: {commit_error}")
                            db.session.rollback()
                            resultado["erros"].append(f"NF {nf.numero_nf}: Erro no commit")

                except Exception as e:
                    logger.error(f"❌ Erro ao processar NF {nf.numero_nf}: {str(e)}")
                    resultado["erros"].append(f"NF {nf.numero_nf}: {str(e)}")
                    # MELHORIA: Rollback apenas desta NF específica
                    db.session.rollback()
                    continue

            # Estatísticas finais
            logger.info(f"✅ Processamento completo: {resultado['processadas']} NFs processadas")
            if resultado.get('movimentacoes_criadas', 0) > 0:
                logger.info(f"📊 Movimentações criadas: {resultado['movimentacoes_criadas']}")
            if resultado.get('embarque_items_atualizados', 0) > 0:
                logger.info(f"📦 EmbarqueItems atualizados: {resultado['embarque_items_atualizados']}")

        except Exception as e:
            db.session.rollback()
            logger.error(f"❌ Erro geral no processamento: {str(e)}")
            resultado["erro_geral"] = str(e)

        return resultado

    def _buscar_nfs_pendentes(self) -> List[RelatorioFaturamentoImportado]:
        """
        Busca TODAS as NFs ativas que têm produtos
        """
        # Subquery para NFs que têm produtos
        nfs_com_produtos = db.session.query(FaturamentoProduto.numero_nf).distinct().subquery()

        # Buscar todas as NFs ativas com produtos
        return (
            RelatorioFaturamentoImportado.query.filter(
                RelatorioFaturamentoImportado.ativo == True,
                RelatorioFaturamentoImportado.numero_nf.in_(db.session.query(nfs_com_produtos.c.numero_nf)),
            )
            .order_by(RelatorioFaturamentoImportado.numero_nf.desc())
            .all()
        )

    def _tem_movimentacao_com_lote(self, numero_nf: str) -> bool:
        """
        Verifica se NF já tem movimentação COM separacao_lote_id
        """
        return (
            MovimentacaoEstoque.query.filter(
                MovimentacaoEstoque.observacao.like(f"%NF {numero_nf}%"),
                MovimentacaoEstoque.observacao.like("%lote separação%"),
                ~MovimentacaoEstoque.observacao.like("%Sem Separação%"),
            ).first()
            is not None
        )

    def _nf_cancelada(self, nf: RelatorioFaturamentoImportado) -> bool:
        """
        Verifica se NF está cancelada
        """
        produto_cancelado = FaturamentoProduto.query.filter_by(numero_nf=nf.numero_nf, status_nf="Cancelado").first()

        return produto_cancelado is not None or not nf.ativo

    def _processar_cancelamento(self, nf: RelatorioFaturamentoImportado):
        """
        Remove movimentações de NF cancelada
        """
        MovimentacaoEstoque.query.filter(MovimentacaoEstoque.observacao.like(f"%NF {nf.numero_nf}%")).delete()

    def _processar_nf(self, nf: RelatorioFaturamentoImportado, usuario: str) -> tuple:
        """
        Processa uma NF seguindo a lógica simplificada
        Retorna: (processou, movimentacoes_criadas, embarque_items_atualizados)
        """
        movimentacoes_criadas = 0
        embarque_items_atualizados = 0
        
        # 2. NF consta em EmbarqueItem?
        embarque_item = EmbarqueItem.query.filter_by(nota_fiscal=nf.numero_nf).first()

        if embarque_item and embarque_item.pedido == nf.origem:
            # Caso 1: NF vinculada e pedido bate
            logger.info(f"📦 NF {nf.numero_nf} em EmbarqueItem com mesmo pedido")
            self._apagar_movimentacao_anterior(nf.numero_nf)

            # Gravar movimentação com o lote do EmbarqueItem
            if embarque_item.separacao_lote_id:
                mov_criadas = self._criar_movimentacao_com_lote(nf, embarque_item.separacao_lote_id, usuario)
                movimentacoes_criadas += mov_criadas
                # Avaliar score para verificar se há divergência
                self._avaliar_score_e_gerar_inconsistencia(nf, embarque_item.separacao_lote_id, usuario)
                return True, movimentacoes_criadas, embarque_items_atualizados
            else:
                logger.error(f"❌ EmbarqueItem sem separacao_lote_id para NF {nf.numero_nf}")
                return False, 0, 0

        elif embarque_item:
            # NF vinculada mas pedido não bate
            logger.warning(f"⚠️ NF {nf.numero_nf} em EmbarqueItem mas pedido divergente")
            mov_criadas = self._criar_movimentacao_sem_separacao(nf, usuario)
            movimentacoes_criadas += mov_criadas
            self._gerar_inconsistencia_divergencia_embarque(nf, embarque_item, usuario)
            return True, movimentacoes_criadas, embarque_items_atualizados

        # 3. Origem da NF consta em algum embarque ativo?
        embarque_ativo = self._buscar_embarque_ativo_por_pedido(nf.origem)

        if embarque_ativo:
            # Caso 2: Pedido encontrado em embarque ativo
            logger.info(f"🚢 NF {nf.numero_nf} tem embarque ativo - avaliando score")
            self._apagar_movimentacao_anterior(nf.numero_nf)
            processou, mov_criadas, emb_atualizados = self._avaliar_score_completo(nf, usuario)
            return processou, mov_criadas, emb_atualizados
        else:
            # Não - Registra "Sem Separação" + inconsistência
            logger.info(f"❌ NF {nf.numero_nf} sem embarque ativo - registrando 'Sem Separação'")
            mov_criadas = self._criar_movimentacao_sem_separacao(nf, usuario)
            movimentacoes_criadas += mov_criadas
            self._gerar_inconsistencia_sem_separacao(nf, usuario)
            return True, movimentacoes_criadas, embarque_items_atualizados

    def _buscar_embarque_ativo_por_pedido(self, num_pedido: str) -> Optional[EmbarqueItem]:
        """
        Busca embarque ativo por número do pedido que precisa de processamento
        
        Processa SE:
        1. NF vazia (ainda não preenchida) OU  
        2. erro_validacao != None (tem erro para resolver)
        
        NÃO processa SE:
        NF preenchida E erro_validacao = None (já está tudo OK!)
        """
        from sqlalchemy import or_
        
        return (
            EmbarqueItem.query.join(Embarque, EmbarqueItem.embarque_id == Embarque.id)
            .filter(
                EmbarqueItem.pedido == num_pedido,
                Embarque.status == "ativo",
                EmbarqueItem.status == "ativo",
                or_(
                    # Caso 1: NF vazia (ainda não preenchida)
                    EmbarqueItem.nota_fiscal.is_(None),
                    EmbarqueItem.nota_fiscal == '',
                    # Caso 2: Tem erro de validação para resolver
                    EmbarqueItem.erro_validacao.isnot(None)
                )
            )
            .first()
        )

    def _apagar_movimentacao_anterior(self, numero_nf: str):
        """
        Apaga movimentações anteriores da NF (exceto as com lote)
        """
        MovimentacaoEstoque.query.filter(
            MovimentacaoEstoque.observacao.like(f"%NF {numero_nf}%"),
            MovimentacaoEstoque.observacao.like("%Sem Separação%"),
        ).delete()

    def _avaliar_score_e_gerar_inconsistencia(self, nf: RelatorioFaturamentoImportado, lote_id: str, usuario: str):
        """
        Avalia score para gerar inconsistência se houver divergência (Caso 1)
        """
        # Buscar separações do lote
        separacoes = Separacao.query.filter_by(separacao_lote_id=lote_id).all()

        if separacoes:
            tem_divergencia = self._calcular_divergencia_lote(nf, separacoes)
            if tem_divergencia:
                self._criar_justificativa_divergencia(nf, lote_id, usuario)

    def _avaliar_score_completo(self, nf: RelatorioFaturamentoImportado, usuario: str) -> tuple:
        """
        Avalia score completo para encontrar melhor lote (Caso 2)
        Retorna: (processou, movimentacoes_criadas, embarque_items_atualizados)
        """
        movimentacoes_criadas = 0
        embarque_items_atualizados = 0
        
        # Verificar se há apenas 1 EmbarqueItem com o pedido
        embarques_pedido = EmbarqueItem.query.filter_by(pedido=nf.origem).all()

        if len(embarques_pedido) == 1:
            # Apenas 1 EmbarqueItem - usar seu lote
            lote_id = embarques_pedido[0].separacao_lote_id
            if lote_id:
                logger.info(f"✅ Único EmbarqueItem encontrado para pedido {nf.origem} - lote {lote_id}")
                mov_criadas = self._criar_movimentacao_com_lote(nf, lote_id, usuario)
                movimentacoes_criadas += mov_criadas
                if self._atualizar_embarque_item(nf.numero_nf, lote_id):
                    embarque_items_atualizados += 1
                # Avaliar divergência
                self._avaliar_score_e_gerar_inconsistencia(nf, lote_id, usuario)
                return True, movimentacoes_criadas, embarque_items_atualizados

        # Múltiplos embarques ou nenhum - avaliar por score
        return self._avaliar_melhor_lote_por_score(nf, embarques_pedido, usuario)

    def _calcular_divergencia_lote(self, nf: RelatorioFaturamentoImportado, separacoes: List[Separacao]) -> bool:
        """
        Calcula se há divergência entre NF e separações de um lote
        """
        produtos_nf = FaturamentoProduto.query.filter_by(numero_nf=nf.numero_nf).all()

        tem_divergencia = False

        for prod_nf in produtos_nf:
            sep_correspondente = next(
                (sep for sep in separacoes if str(sep.cod_produto).strip() == str(prod_nf.cod_produto).strip()), None
            )

            if sep_correspondente and sep_correspondente.qtd_saldo > 0:
                qtd_nf = Decimal(str(prod_nf.qtd_produto_faturado))
                qtd_sep = Decimal(str(sep_correspondente.qtd_saldo))

                max_qtd = max(qtd_nf, qtd_sep)
                if max_qtd > 0:
                    # Divergência se diferença > 5%
                    if abs(qtd_nf - qtd_sep) / max_qtd > 0.05:
                        tem_divergencia = True
                        break
            else:
                # Produto não encontrado ou sem saldo
                tem_divergencia = True
                break

        return tem_divergencia

    def _avaliar_melhor_lote_por_score(
        self, nf: RelatorioFaturamentoImportado, embarques_pedido: List[EmbarqueItem], usuario: str
    ) -> tuple:
        """
        Avalia múltiplos lotes e escolhe o melhor por score
        Retorna: (processou, movimentacoes_criadas, embarque_items_atualizados)
        """
        movimentacoes_criadas = 0
        embarque_items_atualizados = 0
        
        # Coletar todos os lotes únicos
        lotes_unicos = set()
        for item in embarques_pedido:
            if item.separacao_lote_id:
                lotes_unicos.add(item.separacao_lote_id)

        if not lotes_unicos:
            logger.warning(f"⚠️ Nenhum lote encontrado para pedido {nf.origem}")
            mov_criadas = self._criar_movimentacao_sem_separacao(nf, usuario)
            movimentacoes_criadas += mov_criadas
            self._gerar_inconsistencia_sem_separacao(nf, usuario)
            return True, movimentacoes_criadas, embarque_items_atualizados

        # Buscar produtos da NF
        produtos_nf = FaturamentoProduto.query.filter_by(numero_nf=nf.numero_nf).all()

        melhor_score = 0
        melhor_lote = None

        # Avaliar cada lote
        for lote_id in lotes_unicos:
            # Buscar separações do lote
            separacoes_lote = Separacao.query.filter_by(separacao_lote_id=lote_id).all()

            if not separacoes_lote:
                continue

            # Calcular score do lote
            score_produtos = []

            for prod_nf in produtos_nf:
                sep_correspondente = next(
                    (
                        sep
                        for sep in separacoes_lote
                        if str(sep.cod_produto).strip() == str(prod_nf.cod_produto).strip()
                    ),
                    None,
                )

                if sep_correspondente and sep_correspondente.qtd_saldo > 0:
                    qtd_nf = Decimal(str(prod_nf.qtd_produto_faturado))
                    qtd_sep = Decimal(str(sep_correspondente.qtd_saldo))

                    max_qtd = max(qtd_nf, qtd_sep)
                    if max_qtd > 0:
                        score_produto = float(min(qtd_nf, qtd_sep) / max_qtd)
                        score_produtos.append(score_produto)
                else:
                    score_produtos.append(0)

            # Score médio do lote
            score_lote = sum(score_produtos) / len(score_produtos) if score_produtos else 0

            logger.info(f"  Lote {lote_id}: score {score_lote:.2f}")

            if score_lote > melhor_score:
                melhor_score = score_lote
                melhor_lote = lote_id

        if melhor_lote:
            logger.info(f"✅ Melhor lote para NF {nf.numero_nf}: {melhor_lote} (score: {melhor_score:.2f})")
            mov_criadas = self._criar_movimentacao_com_lote(nf, melhor_lote, usuario)
            movimentacoes_criadas += mov_criadas
            if self._atualizar_embarque_item(nf.numero_nf, melhor_lote):
                embarque_items_atualizados += 1
            self._avaliar_score_e_gerar_inconsistencia(nf, melhor_lote, usuario)
            return True, movimentacoes_criadas, embarque_items_atualizados
        else:
            logger.warning(f"⚠️ Nenhum lote adequado encontrado para NF {nf.numero_nf}")
            mov_criadas = self._criar_movimentacao_sem_separacao(nf, usuario)
            movimentacoes_criadas += mov_criadas
            self._gerar_inconsistencia_sem_separacao(nf, usuario)
            return True, movimentacoes_criadas, embarque_items_atualizados

    def _criar_movimentacao_sem_separacao(self, nf: RelatorioFaturamentoImportado, usuario: str) -> int:
        """
        Cria movimentação 'Sem Separação'
        Retorna: quantidade de movimentações criadas
        """
        movimentacoes_criadas = 0
        
        # Verificar se já existe
        existe = MovimentacaoEstoque.query.filter(
            MovimentacaoEstoque.observacao.like(f"%NF {nf.numero_nf}%"),
            MovimentacaoEstoque.observacao.like("%Sem Separação%"),
        ).first()

        if existe:
            return 0

        produtos = FaturamentoProduto.query.filter_by(numero_nf=nf.numero_nf).all()

        for produto in produtos:
            mov = MovimentacaoEstoque()
            mov.cod_produto = produto.cod_produto
            mov.nome_produto = produto.nome_produto
            mov.tipo_movimentacao = "FATURAMENTO"
            mov.local_movimentacao = "VENDA"
            mov.data_movimentacao = datetime.now().date()
            mov.qtd_movimentacao = -abs(produto.qtd_produto_faturado)
            mov.observacao = f"Baixa automática NF {nf.numero_nf} - Sem Separação"
            mov.criado_por = usuario
            db.session.add(mov)
            movimentacoes_criadas += 1
            
        return movimentacoes_criadas

    def _criar_movimentacao_com_lote(self, nf: RelatorioFaturamentoImportado, lote_id: str, usuario: str) -> int:
        """
        Cria movimentação com lote de separação
        Retorna: quantidade de movimentações criadas
        """
        movimentacoes_criadas = 0
        produtos = FaturamentoProduto.query.filter_by(numero_nf=nf.numero_nf).all()

        for produto in produtos:
            mov = MovimentacaoEstoque()
            mov.cod_produto = produto.cod_produto
            mov.nome_produto = produto.nome_produto
            mov.tipo_movimentacao = "FATURAMENTO"
            mov.local_movimentacao = "VENDA"
            mov.data_movimentacao = datetime.now().date()
            mov.qtd_movimentacao = -abs(produto.qtd_produto_faturado)
            mov.observacao = f"Baixa automática NF {nf.numero_nf} - lote separação {lote_id}"
            mov.criado_por = usuario
            db.session.add(mov)
            movimentacoes_criadas += 1

            # Abater MovimentacaoPrevista SEM fallback de data
            try:
                sep = Separacao.query.filter_by(separacao_lote_id=lote_id, cod_produto=produto.cod_produto).first()
                if sep and sep.expedicao:
                    ServicoEstoqueTempoReal.atualizar_movimentacao_prevista(
                        cod_produto=produto.cod_produto,
                        data=sep.expedicao,
                        qtd_entrada=Decimal("0"),
                        qtd_saida=Decimal(str(-abs(produto.qtd_produto_faturado))),
                    )
            except Exception as e:
                logger.debug(f"Falha ao abater previsão NF {nf.numero_nf}/{produto.cod_produto}: {e}")
                
        return movimentacoes_criadas

    def _criar_justificativa_divergencia(self, nf: RelatorioFaturamentoImportado, lote_id: str, usuario: str):
        """
        Cria justificativa para divergência
        """
        produtos = FaturamentoProduto.query.filter_by(numero_nf=nf.numero_nf).all()
        separacoes = Separacao.query.filter_by(separacao_lote_id=lote_id).all()

        for sep in separacoes:
            prod_corresp = next(
                (p for p in produtos if str(p.cod_produto).strip() == str(sep.cod_produto).strip()), None
            )

            if prod_corresp:
                qtd_fat = Decimal(str(prod_corresp.qtd_produto_faturado))
                qtd_sep = Decimal(str(sep.qtd_saldo))

                if abs(qtd_fat - qtd_sep) > 0:
                    just = FaturamentoParcialJustificativa()
                    just.separacao_lote_id = lote_id
                    just.num_pedido = nf.origem
                    just.cod_produto = sep.cod_produto
                    just.numero_nf = nf.numero_nf
                    just.qtd_separada = float(qtd_sep)
                    just.qtd_faturada = float(qtd_fat)
                    just.qtd_saldo = float(abs(qtd_sep - qtd_fat))
                    just.motivo_nao_faturamento = "DIVERGENCIA_AUTO"
                    just.descricao_detalhada = f"Divergência: Separado {qtd_sep}, Faturado {qtd_fat}"
                    just.classificacao_saldo = "NECESSITA_COMP"  # Max 20 chars
                    just.criado_por = usuario
                    db.session.add(just)

    def _atualizar_embarque_item(self, numero_nf: str, lote_id: str) -> bool:
        """
        Atualiza EmbarqueItem com a NF
        Retorna: True se atualizou, False caso contrário
        """
        item = EmbarqueItem.query.filter_by(separacao_lote_id=lote_id, nota_fiscal=None).first()

        if item:
            item.nota_fiscal = numero_nf
            logger.info(f"✅ NF {numero_nf} vinculada ao EmbarqueItem do lote {lote_id}")
            return True
        return False

    def _gerar_inconsistencia_divergencia_embarque(
        self, nf: RelatorioFaturamentoImportado, embarque_item: EmbarqueItem, usuario: str
    ):
        """
        Gera inconsistência para divergência NF x Embarque
        """
        # Verificar se já existe inconsistência para esta NF
        inc_existente = InconsistenciaFaturamento.query.filter_by(
            numero_nf=nf.numero_nf, tipo="DIVERGENCIA_NF_EMBARQUE"
        ).first()

        produtos = FaturamentoProduto.query.filter_by(numero_nf=nf.numero_nf).all()
        qtd_total = sum(float(p.qtd_produto_faturado) for p in produtos)

        if inc_existente:
            # Atualizar existente
            inc_existente.num_pedido = nf.origem
            inc_existente.cod_produto = produtos[0].cod_produto if produtos else "MULTIPLOS"
            inc_existente.qtd_faturada = qtd_total
            inc_existente.observacao_resolucao = f"""
            NF {nf.numero_nf} vinculada ao embarque mas com pedido divergente:
            - Pedido NF: {nf.origem}
            - Pedido EmbarqueItem: {embarque_item.pedido}
            - Embarque ID: {embarque_item.embarque_id}
            """
            inc_existente.resolvida = False
            inc_existente.atualizado_por = usuario
            inc_existente.atualizado_em = datetime.now()
        else:
            # Criar nova
            inc = InconsistenciaFaturamento()
            inc.tipo = "DIVERGENCIA_NF_EMBARQUE"
            inc.numero_nf = nf.numero_nf
            inc.num_pedido = nf.origem
            inc.cod_produto = produtos[0].cod_produto if produtos else "MULTIPLOS"
            inc.qtd_faturada = qtd_total
            inc.observacao_resolucao = f"""
            NF {nf.numero_nf} vinculada ao embarque mas com pedido divergente:
            - Pedido NF: {nf.origem}
            - Pedido EmbarqueItem: {embarque_item.pedido}
            - Embarque ID: {embarque_item.embarque_id}
            """
            inc.resolvida = False
            inc.criado_por = usuario
            db.session.add(inc)

    def _gerar_inconsistencia_sem_separacao(self, nf: RelatorioFaturamentoImportado, usuario: str):
        """
        Gera inconsistência para NF sem separação
        """
        # Verificar se já existe inconsistência para esta NF
        inc_existente = InconsistenciaFaturamento.query.filter_by(
            numero_nf=nf.numero_nf, tipo="NF_SEM_SEPARACAO"
        ).first()

        produtos = FaturamentoProduto.query.filter_by(numero_nf=nf.numero_nf).all()
        qtd_total = sum(float(p.qtd_produto_faturado) for p in produtos)

        if inc_existente:
            # Atualizar existente
            inc_existente.num_pedido = nf.origem
            inc_existente.cod_produto = produtos[0].cod_produto if produtos else "MULTIPLOS"
            inc_existente.qtd_faturada = qtd_total
            inc_existente.observacao_resolucao = f"NF {nf.numero_nf} processada sem separação - Pedido {nf.origem}"
            inc_existente.resolvida = False
            inc_existente.atualizado_por = usuario
            inc_existente.atualizado_em = datetime.now()
        else:
            # Criar nova
            inc = InconsistenciaFaturamento()
            inc.tipo = "NF_SEM_SEPARACAO"
            inc.numero_nf = nf.numero_nf
            inc.num_pedido = nf.origem
            inc.cod_produto = produtos[0].cod_produto if produtos else "MULTIPLOS"
            inc.qtd_faturada = qtd_total
            inc.observacao_resolucao = f"NF {nf.numero_nf} processada sem separação - Pedido {nf.origem}"
            inc.resolvida = False
            inc.criado_por = usuario
            db.session.add(inc)
