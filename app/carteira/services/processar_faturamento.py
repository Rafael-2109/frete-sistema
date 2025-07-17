"""
Processamento de Faturamento - Conforme processo_atual.md
========================================================

Implementação SIMPLES e DIRETA dos 3 casos de faturamento
"""

import logging
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Any
from sqlalchemy import and_, or_
from app import db
from app.faturamento.models import FaturamentoProduto, RelatorioFaturamentoImportado
from app.estoque.models import MovimentacaoEstoque
from app.separacao.models import Separacao
from app.embarques.models import EmbarqueItem
from app.carteira.models import FaturamentoParcialJustificativa

logger = logging.getLogger(__name__)

class ProcessadorFaturamento:
    """
    Processa faturamento conforme regras do processo_atual.md
    """
    
    def processar_nfs_importadas(self, usuario: str = 'Importação Odoo') -> Optional[Dict[str, Any]]:
        """
        Processa todas as NFs importadas que ainda não foram processadas
        """
        resultado = {
            'processadas': 0,
            'caso1_direto': 0,
            'caso2_parcial': 0,
            'caso3_cancelado': 0,
            'erros': []
        }
        
        try:
            # Buscar NFs não processadas (sem movimentação)
            nfs_pendentes = self._buscar_nfs_pendentes()
            
            for nf in nfs_pendentes:
                try:
                    caso = self._processar_nf(nf, usuario)
                    resultado['processadas'] += 1
                    resultado[f'caso{caso}'] += 1
                except Exception as e:
                    resultado['erros'].append(f"NF {nf.numero_nf}: {str(e)}")
                    continue
            
            db.session.commit()
            
        except Exception as e:
            db.session.rollback()
            resultado['erro_geral'] = str(e)
        
        return resultado
    
    def _buscar_nfs_pendentes(self) -> List[RelatorioFaturamentoImportado]:
        """
        Busca NFs que ainda não foram processadas OU que mudaram de status
        """
        # NFs já processadas e seus status
        nfs_processadas = db.session.query(
            MovimentacaoEstoque.observacao,
            MovimentacaoEstoque.tipo_movimentacao
        ).filter(
            MovimentacaoEstoque.observacao.like('%Baixa automática NF%')
        ).all()
        
        nfs_com_movimentacao = {}
        for obs, tipo in nfs_processadas:
            if obs and 'NF' in obs:
                parts = obs.split('NF')
                if len(parts) > 1:
                    numero = parts[1].split('-')[0].strip()
                    nfs_com_movimentacao[numero] = tipo
        
        # Buscar todas as NFs ativas
        todas_nfs = RelatorioFaturamentoImportado.query.filter(
            RelatorioFaturamentoImportado.ativo == True
        ).all()
        
        nfs_pendentes = []
        
        for nf in todas_nfs:
            # 1. NF nova (não processada)
            if nf.numero_nf not in nfs_com_movimentacao:
                nfs_pendentes.append(nf)
                continue
            
            # 2. Verificar se mudou status no FaturamentoProduto
            produto_cancelado = FaturamentoProduto.query.filter_by(
                numero_nf=nf.numero_nf,
                status_nf='Cancelado'
            ).first()
            
            if produto_cancelado and nfs_com_movimentacao.get(nf.numero_nf) == 'FATURAMENTO':
                # Status mudou para cancelado mas ainda tem movimentação ativa
                nfs_pendentes.append(nf)
        
        return nfs_pendentes
    
    def _processar_nf(self, nf: RelatorioFaturamentoImportado, usuario: str) -> int:
        """
        Processa uma NF específica e retorna o caso (1, 2 ou 3)
        """
        # Verificar status no FaturamentoProduto
        produto_cancelado = FaturamentoProduto.query.filter_by(
            numero_nf=nf.numero_nf,
            status_nf='Cancelado'
        ).first()
        
        # Caso 3: NF Cancelada
        if produto_cancelado or not nf.ativo:
            self._processar_caso3_cancelamento(nf)
            return 3
        
        # Verificar se NF já está preenchida em EmbarqueItem
        embarque_item_existente = EmbarqueItem.query.filter_by(
            nota_fiscal=nf.numero_nf
        ).first()
        
        if embarque_item_existente:
            # Verificar se bate CNPJ e pedido
            if embarque_item_existente.embarque:
                embarque = embarque_item_existente.embarque
                
                # Validar CNPJ e pedido
                if (embarque.cnpj_cliente == nf.cnpj_cliente and 
                    embarque_item_existente.num_pedido == nf.origem):
                    # Vinculação já está correta - apenas criar movimentação
                    lote_id = embarque_item_existente.separacao_lote_id or 'EMBARQUE_DIRETO'
                    self._processar_caso1_direto(nf, lote_id, usuario)
                    return 1
                else:
                    # Gerar inconsistência - NF preenchida mas não bate
                    self._gerar_inconsistencia_vinculacao(nf, embarque_item_existente, usuario)
                    return 2
        
        # Buscar separações do pedido
        separacoes = self._buscar_separacoes_pedido(nf.origem)  # origem = num_pedido
        
        if not separacoes:
            # Sem separação - gravar como "Sem Separação"
            self._criar_movimentacao_sem_separacao(nf, usuario)
            return 1
        
        # Verificar match com separações
        lote_vinculado, divergencia = self._vincular_com_separacao(nf, separacoes)
        
        if divergencia:
            # Caso 2: Separação != NF
            self._processar_caso2_divergencia(nf, lote_vinculado, divergencia, usuario)
            return 2
        else:
            # Caso 1: Separação = NF
            self._processar_caso1_direto(nf, lote_vinculado, usuario)
            return 1
    
    def _buscar_separacoes_pedido(self, num_pedido: str) -> List[Separacao]:
        """
        Busca todas as separações de um pedido
        """
        return Separacao.query.filter_by(
            num_pedido=num_pedido
        ).all()
    
    def _vincular_com_separacao(self, nf: RelatorioFaturamentoImportado, 
                                separacoes: List[Separacao]) -> Tuple[str, bool]:
        """
        Vincula NF com separação mais adequada usando score percentual
        Retorna (lote_id, tem_divergencia)
        """
        # Se só tem uma separação, usa ela
        if len(separacoes) == 1:
            return self._verificar_divergencia_simples(nf, separacoes[0])
        
        # Múltiplas separações - encontrar melhor match
        melhor_score = 0
        melhor_lote = None
        tem_divergencia = False
        melhor_detalhes = {}
        
        # Buscar produtos da NF
        produtos_nf = FaturamentoProduto.query.filter_by(
            numero_nf=nf.numero_nf
        ).all()
        
        # Agrupar separações por lote
        separacoes_por_lote = {}
        for sep in separacoes:
            if sep.separacao_lote_id not in separacoes_por_lote:
                separacoes_por_lote[sep.separacao_lote_id] = []
            separacoes_por_lote[sep.separacao_lote_id].append(sep)
        
        # Calcular score por lote de separação
        for lote_id, seps_lote in separacoes_por_lote.items():
            score_lote = 0
            produtos_matched = 0
            divergencia_local = False
            
            # Para cada produto da NF
            for prod_nf in produtos_nf:
                # Buscar separação correspondente no lote
                sep_correspondente = None
                for sep in seps_lote:
                    if sep.cod_produto == prod_nf.cod_produto:
                        sep_correspondente = sep
                        break
                
                if sep_correspondente:
                    produtos_matched += 1
                    
                    # Calcular percentual de match de quantidade
                    if sep_correspondente.qtd_saldo > 0:
                        percentual = min(
                            prod_nf.qtd_produto_faturado / sep_correspondente.qtd_saldo,
                            sep_correspondente.qtd_saldo / prod_nf.qtd_produto_faturado
                        )
                        
                        if percentual >= 0.95:  # 95% ou mais = match perfeito
                            score_lote += 1.0
                        elif percentual >= 0.80:  # 80-94% = match bom
                            score_lote += 0.8
                            divergencia_local = True
                        elif percentual >= 0.50:  # 50-79% = match parcial
                            score_lote += 0.5
                            divergencia_local = True
                        else:
                            score_lote += 0.2  # Menos de 50% = match fraco
                            divergencia_local = True
            
            # Calcular score final do lote (média ponderada)
            if len(produtos_nf) > 0:
                score_final_lote = (score_lote / len(produtos_nf)) * (produtos_matched / len(produtos_nf))
                
                if score_final_lote > melhor_score:
                    melhor_score = score_final_lote
                    melhor_lote = lote_id
                    tem_divergencia = divergencia_local
                    melhor_detalhes = {
                        'produtos_matched': produtos_matched,
                        'total_produtos_nf': len(produtos_nf),
                        'score_percentual': score_final_lote * 100
                    }
        
        # Log do melhor match encontrado
        if melhor_lote:
            logger.info(f"NF {nf.numero_nf} vinculada ao lote {melhor_lote} com score {melhor_detalhes.get('score_percentual', 0):.1f}%")
        
        return melhor_lote or '', tem_divergencia
    
    def _verificar_divergencia_simples(self, nf: RelatorioFaturamentoImportado, 
                                     separacao: Separacao) -> Tuple[str, bool]:
        """
        Verifica se há divergência entre NF e separação única
        """
        produtos_nf = FaturamentoProduto.query.filter_by(
            numero_nf=nf.numero_nf
        ).all()
        
        # Comparar totais
        total_nf = sum(p.qtd_produto_faturado for p in produtos_nf)
        total_sep = separacao.qtd_saldo
        
        tem_divergencia = abs(total_nf - total_sep) > 0.01
        
        return separacao.separacao_lote_id, tem_divergencia
    
    def _processar_caso1_direto(self, nf: RelatorioFaturamentoImportado, 
                               lote_id: str, usuario: str):
        """
        Caso 1: Separação = NF - Grava movimentação direta
        """
        produtos = FaturamentoProduto.query.filter_by(numero_nf=nf.numero_nf).all()
        
        for produto in produtos:
            movimentacao = MovimentacaoEstoque()
            movimentacao.cod_produto = produto.cod_produto
            movimentacao.nome_produto = produto.nome_produto
            movimentacao.tipo_movimentacao = 'FATURAMENTO'
            movimentacao.local_movimentacao = 'VENDA'
            movimentacao.data_movimentacao = produto.data_fatura.date() if produto.data_fatura else nf.data_fatura
            movimentacao.qtd_movimentacao = -produto.qtd_produto_faturado  # Negativo = saída
            movimentacao.observacao = f"Baixa automática NF {nf.numero_nf} - lote separação {lote_id}"
            movimentacao.criado_por = usuario
            db.session.add(movimentacao)
        
        # Atualizar EmbarqueItem com a NF
        self._atualizar_embarque_item(nf.numero_nf, lote_id)
    
    def _processar_caso2_divergencia(self, nf: RelatorioFaturamentoImportado,
                                    lote_id: str, divergencia: bool, usuario: str):
        """
        Caso 2: Separação != NF - Grava movimentação e justificativa
        """
        # Primeiro grava a movimentação normal
        self._processar_caso1_direto(nf, lote_id, usuario)
        
        # Depois cria justificativa para divergência
        produtos = FaturamentoProduto.query.filter_by(numero_nf=nf.numero_nf).all()
        separacao = Separacao.query.filter_by(separacao_lote_id=lote_id).first()
        
        if separacao:
            justificativa = FaturamentoParcialJustificativa()
            justificativa.separacao_lote_id = lote_id
            justificativa.num_pedido = nf.origem
            justificativa.cod_produto = separacao.cod_produto
            justificativa.numero_nf = nf.numero_nf
            justificativa.qtd_separada = separacao.qtd_saldo
            justificativa.qtd_faturada = sum(p.qtd_produto_faturado for p in produtos)
            justificativa.qtd_saldo = abs(separacao.qtd_saldo - sum(p.qtd_produto_faturado for p in produtos))
            justificativa.motivo_nao_faturamento = 'DIVERGENCIA_AUTOMATICA'
            justificativa.descricao_detalhada = 'Divergência detectada automaticamente na importação'
            justificativa.classificacao_saldo = 'NECESSITA_COMPLEMENTO'
            justificativa.criado_por = usuario
            db.session.add(justificativa)
    
    def _processar_caso3_cancelamento(self, nf: RelatorioFaturamentoImportado):
        """
        Caso 3: NF Cancelada - Remove movimentação de estoque
        """
        # Buscar movimentações desta NF
        movimentacoes = MovimentacaoEstoque.query.filter(
            MovimentacaoEstoque.observacao.like(f'%NF {nf.numero_nf}%')
        ).all()
        
        # Apagar todas as movimentações desta NF
        for mov in movimentacoes:
            db.session.delete(mov)
    
    def _criar_movimentacao_sem_separacao(self, nf: RelatorioFaturamentoImportado, usuario: str):
        """
        Cria movimentação para NF sem separação vinculada
        """
        produtos = FaturamentoProduto.query.filter_by(numero_nf=nf.numero_nf).all()
        
        for produto in produtos:
            movimentacao = MovimentacaoEstoque()
            movimentacao.cod_produto = produto.cod_produto
            movimentacao.nome_produto = produto.nome_produto
            movimentacao.tipo_movimentacao = 'FATURAMENTO'
            movimentacao.local_movimentacao = 'VENDA'
            movimentacao.data_movimentacao = produto.data_fatura.date() if produto.data_fatura else nf.data_fatura
            movimentacao.qtd_movimentacao = -produto.qtd_produto_faturado
            movimentacao.observacao = f"Baixa automática NF {nf.numero_nf} - Sem Separação"
            movimentacao.criado_por = usuario
            db.session.add(movimentacao)
    
    def _atualizar_embarque_item(self, numero_nf: str, lote_id: str):
        """
        Atualiza EmbarqueItem com o número da NF
        """
        # Buscar item do embarque com este lote sem NF
        item = EmbarqueItem.query.filter_by(
            separacao_lote_id=lote_id,
            nota_fiscal=None
        ).first()
        
        if item:
            item.nota_fiscal = numero_nf
    
    def _gerar_inconsistencia_vinculacao(self, nf: RelatorioFaturamentoImportado, 
                                       embarque_item: EmbarqueItem, usuario: str):
        """
        Gera inconsistência quando NF está preenchida mas não bate CNPJ/pedido
        """
        from app.carteira.models import InconsistenciaFaturamento
        
        # Buscar produtos da NF para somar quantidade
        produtos_nf = FaturamentoProduto.query.filter_by(numero_nf=nf.numero_nf).all()
        qtd_total = sum(p.qtd_produto_faturado for p in produtos_nf)
        
        inconsistencia = InconsistenciaFaturamento()
        inconsistencia.tipo = 'NF_VINCULADA_INCORRETAMENTE'
        inconsistencia.numero_nf = nf.numero_nf
        inconsistencia.num_pedido = nf.origem
        inconsistencia.cod_produto = produtos_nf[0].cod_produto if produtos_nf else 'MULTIPLOS'
        inconsistencia.qtd_faturada = qtd_total
        inconsistencia.observacao_resolucao = f"""
        NF {nf.numero_nf} está vinculada ao embarque {embarque_item.embarque_id} mas:
        - CNPJ NF: {nf.cnpj_cliente} vs CNPJ Embarque: {embarque_item.embarque.cnpj_cliente}
        - Pedido NF: {nf.origem} vs Pedido Item: {embarque_item.num_pedido}
        Lote separação: {embarque_item.separacao_lote_id}
        """
        inconsistencia.resolvida = False
        
        db.session.add(inconsistencia)
        
        logger.warning(f"⚠️ Inconsistência gerada: NF {nf.numero_nf} vinculada incorretamente ao embarque {embarque_item.embarque_id}") 