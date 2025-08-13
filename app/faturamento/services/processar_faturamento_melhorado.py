"""
Processador de Faturamento Melhorado
====================================

Versão corrigida que resolve os problemas identificados:
1. Commit incremental para não perder dados
2. Tratamento de erros sem afetar outras NFs
3. Busca correta de EmbarqueItems
4. Garantia de criação de MovimentacaoEstoque

Autor: Sistema de Fretes
Data: 2025-08-13
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
from sqlalchemy import or_, and_

logger = logging.getLogger(__name__)


class ProcessadorFaturamentoMelhorado:
    """
    Processador melhorado com correções dos problemas identificados
    """

    def processar_nfs_importadas(
        self, usuario: str = "Importação Odoo", limpar_inconsistencias: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Processa todas as NFs importadas com commits incrementais
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
                    deletadas = InconsistenciaFaturamento.query.filter_by(resolvida=False).delete()
                    db.session.commit()
                    logger.info(f"✅ {deletadas} inconsistências não resolvidas removidas")
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
                        # Commit incremental para cancelamentos
                        try:
                            db.session.commit()
                        except:
                            db.session.rollback()
                        continue

                    # 1.C - Processar NF (com ou sem movimentação "Sem Separação")
                    processou, mov_criadas, embarque_atualizado = self._processar_nf_melhorado(nf, usuario)
                    
                    if processou:
                        resultado["processadas"] += 1
                        resultado["movimentacoes_criadas"] += mov_criadas
                        if embarque_atualizado:
                            resultado["embarque_items_atualizados"] += 1
                        
                        # COMMIT INCREMENTAL APÓS CADA NF PROCESSADA COM SUCESSO
                        try:
                            db.session.commit()
                            logger.info(f"✅ NF {nf.numero_nf} processada e commitada")
                        except Exception as commit_error:
                            logger.error(f"❌ Erro no commit da NF {nf.numero_nf}: {commit_error}")
                            db.session.rollback()
                            resultado["erros"].append(f"NF {nf.numero_nf}: Erro no commit - {str(commit_error)}")

                except Exception as e:
                    logger.error(f"❌ Erro ao processar NF {nf.numero_nf}: {str(e)}")
                    resultado["erros"].append(f"NF {nf.numero_nf}: {str(e)}")
                    # Rollback apenas desta NF específica
                    db.session.rollback()
                    continue

            logger.info(f"✅ Processamento completo: {resultado['processadas']} NFs processadas")
            logger.info(f"📊 Movimentações criadas: {resultado['movimentacoes_criadas']}")
            logger.info(f"📦 EmbarqueItems atualizados: {resultado['embarque_items_atualizados']}")

        except Exception as e:
            logger.error(f"❌ Erro geral no processamento: {str(e)}")
            resultado["erro_geral"] = str(e)

        return resultado

    def _processar_nf_melhorado(self, nf: RelatorioFaturamentoImportado, usuario: str) -> tuple:
        """
        Processa uma NF retornando (sucesso, movimentacoes_criadas, embarque_atualizado)
        """
        movimentacoes_criadas = 0
        embarque_atualizado = False
        
        try:
            # Buscar EmbarqueItem de forma mais abrangente
            embarque_item = self._buscar_embarque_item_melhorado(nf)
            
            if embarque_item:
                logger.info(f"📦 Encontrado EmbarqueItem para NF {nf.numero_nf}")
                
                # Verificar se precisa atualizar a NF no EmbarqueItem
                if not embarque_item.nota_fiscal or embarque_item.nota_fiscal != nf.numero_nf:
                    embarque_item.nota_fiscal = nf.numero_nf
                    embarque_item.erro_validacao = None
                    embarque_atualizado = True
                    logger.info(f"✅ EmbarqueItem atualizado com NF {nf.numero_nf}")
                
                # Criar movimentação com lote se tiver
                if embarque_item.separacao_lote_id:
                    mov_criadas = self._criar_movimentacao_com_lote_seguro(
                        nf, embarque_item.separacao_lote_id, usuario
                    )
                    movimentacoes_criadas += mov_criadas
                    return True, movimentacoes_criadas, embarque_atualizado
                else:
                    # Embarque sem lote - criar "Sem Separação"
                    mov_criadas = self._criar_movimentacao_sem_separacao_seguro(nf, usuario)
                    movimentacoes_criadas += mov_criadas
                    return True, movimentacoes_criadas, embarque_atualizado
            
            # Não encontrou embarque - criar "Sem Separação"
            logger.info(f"❌ NF {nf.numero_nf} sem embarque - criando 'Sem Separação'")
            mov_criadas = self._criar_movimentacao_sem_separacao_seguro(nf, usuario)
            movimentacoes_criadas += mov_criadas
            return True, movimentacoes_criadas, False
            
        except Exception as e:
            logger.error(f"❌ Erro ao processar NF {nf.numero_nf}: {e}")
            return False, 0, False

    def _buscar_embarque_item_melhorado(self, nf: RelatorioFaturamentoImportado) -> Optional[EmbarqueItem]:
        """
        Busca EmbarqueItem de forma mais abrangente
        """
        if not nf.origem:
            return None
        
        # Buscar por pedido, priorizando os que precisam de processamento
        embarque_item = (
            EmbarqueItem.query.join(Embarque, EmbarqueItem.embarque_id == Embarque.id)
            .filter(
                EmbarqueItem.pedido == nf.origem,
                Embarque.status == "ativo",
                EmbarqueItem.status == "ativo"
            )
            .order_by(
                # Priorizar: 1º sem NF, 2º com erro, 3º com NF (para verificar)
                EmbarqueItem.nota_fiscal.is_(None).desc(),
                EmbarqueItem.erro_validacao.isnot(None).desc()
            )
            .first()
        )
        
        return embarque_item

    def _criar_movimentacao_com_lote_seguro(
        self, nf: RelatorioFaturamentoImportado, lote_id: str, usuario: str
    ) -> int:
        """
        Cria movimentação com lote de forma segura, retorna quantidade criada
        """
        movimentacoes_criadas = 0
        
        # Verificar se já existe para evitar duplicação
        existe = MovimentacaoEstoque.query.filter(
            MovimentacaoEstoque.observacao.like(f"%NF {nf.numero_nf}%lote separação {lote_id}%")
        ).first()
        
        if existe:
            logger.info(f"✅ Movimentação já existe para NF {nf.numero_nf} com lote {lote_id}")
            return 0
        
        produtos = FaturamentoProduto.query.filter_by(numero_nf=nf.numero_nf).all()
        
        for produto in produtos:
            try:
                mov = MovimentacaoEstoque()
                mov.cod_produto = produto.cod_produto
                mov.nome_produto = produto.nome_produto
                mov.tipo_movimentacao = "FATURAMENTO"
                mov.local_movimentacao = "VENDA"
                mov.data_movimentacao = nf.data_fatura or datetime.now().date()
                mov.qtd_movimentacao = -abs(produto.qtd_produto_faturado)
                mov.observacao = f"Baixa automática NF {nf.numero_nf} - lote separação {lote_id}"
                mov.criado_por = usuario
                
                db.session.add(mov)
                movimentacoes_criadas += 1
                
                # Tentar abater MovimentacaoPrevista
                try:
                    sep = Separacao.query.filter_by(
                        separacao_lote_id=lote_id, 
                        cod_produto=produto.cod_produto
                    ).first()
                    
                    if sep and sep.expedicao:
                        ServicoEstoqueTempoReal.atualizar_movimentacao_prevista(
                            cod_produto=produto.cod_produto,
                            data=sep.expedicao,
                            qtd_entrada=Decimal("0"),
                            qtd_saida=Decimal(str(-abs(produto.qtd_produto_faturado))),
                        )
                except Exception as e:
                    logger.debug(f"Falha ao abater previsão: {e}")
                    
            except Exception as e:
                logger.error(f"❌ Erro ao criar movimentação para produto {produto.cod_produto}: {e}")
                continue
        
        return movimentacoes_criadas

    def _criar_movimentacao_sem_separacao_seguro(
        self, nf: RelatorioFaturamentoImportado, usuario: str
    ) -> int:
        """
        Cria movimentação 'Sem Separação' de forma segura, retorna quantidade criada
        """
        movimentacoes_criadas = 0
        
        # Verificar se já existe
        existe = MovimentacaoEstoque.query.filter(
            and_(
                MovimentacaoEstoque.observacao.like(f"%NF {nf.numero_nf}%"),
                MovimentacaoEstoque.observacao.like("%Sem Separação%")
            )
        ).first()
        
        if existe:
            logger.info(f"✅ Movimentação 'Sem Separação' já existe para NF {nf.numero_nf}")
            return 0
        
        produtos = FaturamentoProduto.query.filter_by(numero_nf=nf.numero_nf).all()
        
        for produto in produtos:
            try:
                mov = MovimentacaoEstoque()
                mov.cod_produto = produto.cod_produto
                mov.nome_produto = produto.nome_produto
                mov.tipo_movimentacao = "FATURAMENTO"
                mov.local_movimentacao = "VENDA"
                mov.data_movimentacao = nf.data_fatura or datetime.now().date()
                mov.qtd_movimentacao = -abs(produto.qtd_produto_faturado)
                mov.observacao = f"Baixa automática NF {nf.numero_nf} - Sem Separação"
                mov.criado_por = usuario
                
                db.session.add(mov)
                movimentacoes_criadas += 1
                
            except Exception as e:
                logger.error(f"❌ Erro ao criar movimentação para produto {produto.cod_produto}: {e}")
                continue
        
        return movimentacoes_criadas

    # Herdar outros métodos necessários do ProcessadorFaturamento original
    def _buscar_nfs_pendentes(self):
        """Busca TODAS as NFs ativas que têm produtos"""
        return (
            RelatorioFaturamentoImportado.query.filter_by(ativo=True)
            .filter(RelatorioFaturamentoImportado.origem.isnot(None))
            .order_by(RelatorioFaturamentoImportado.data_fatura.desc())
            .all()
        )

    def _tem_movimentacao_com_lote(self, numero_nf: str) -> bool:
        """Verifica se já existe movimentação com lote"""
        existe = MovimentacaoEstoque.query.filter(
            and_(
                MovimentacaoEstoque.observacao.like(f"%NF {numero_nf}%"),
                ~MovimentacaoEstoque.observacao.like("%Sem Separação%"),
                MovimentacaoEstoque.observacao.like("%lote separação%"),
            )
        ).first()
        return existe is not None

    def _nf_cancelada(self, nf: RelatorioFaturamentoImportado) -> bool:
        """Verifica se NF está cancelada"""
        produtos = FaturamentoProduto.query.filter_by(numero_nf=nf.numero_nf).all()
        if not produtos:
            return False
        return all(p.status_nf == "Cancelado" for p in produtos)

    def _processar_cancelamento(self, nf: RelatorioFaturamentoImportado):
        """Remove movimentações de NF cancelada"""
        MovimentacaoEstoque.query.filter(
            MovimentacaoEstoque.observacao.like(f"%NF {nf.numero_nf}%")
        ).delete()