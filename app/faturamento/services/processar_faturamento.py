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
            'erros': [],
            'detalhes_processamento': []
        }
        
        try:
            # Buscar NFs não processadas (sem movimentação)
            nfs_pendentes = self._buscar_nfs_pendentes()
            logger.info(f"📊 Total de NFs para processar: {len(nfs_pendentes)}")
            
            for nf in nfs_pendentes:
                try:
                    logger.info(f"🔄 Processando NF {nf.numero_nf} - Origem/Pedido: {nf.origem}")
                    caso = self._processar_nf(nf, usuario)
                    resultado['processadas'] += 1
                    resultado[f'caso{caso}'] += 1
                    
                    # Adicionar detalhes para debug
                    if caso == 1:
                        tipo = "DIRETO"
                    elif caso == 2:
                        tipo = "PARCIAL"
                    elif caso == 3:
                        tipo = "CANCELADO"
                    else:
                        tipo = "DESCONHECIDO"
                    
                    resultado['detalhes_processamento'].append({
                        'nf': nf.numero_nf,
                        'origem': nf.origem,
                        'caso': caso,
                        'tipo': tipo
                    })
                    
                except Exception as e:
                    import traceback
                    erro_completo = traceback.format_exc()
                    logger.error(f"❌ Erro ao processar NF {nf.numero_nf}: {str(e)}")
                    logger.error(f"Traceback completo:\n{erro_completo}")
                    resultado['erros'].append(f"NF {nf.numero_nf}: {str(e)}")
                    continue
            
            db.session.commit()
            logger.info(f"✅ Processamento concluído: {resultado['processadas']} NFs processadas")
            
        except Exception as e:
            db.session.rollback()
            resultado['erro_geral'] = str(e)
        
        return resultado
    
    def _buscar_nfs_pendentes(self) -> List[RelatorioFaturamentoImportado]:
        """
        ✅ CORRIGIDO: Busca NFs não processadas OU processadas como "Sem Separação" para reprocessamento
        """
        # Buscar NFs que têm movimentação "Sem Separação" (candidatas a reprocessamento)
        nfs_sem_separacao_query = db.session.query(MovimentacaoEstoque.observacao)\
            .filter(MovimentacaoEstoque.tipo_movimentacao == 'FATURAMENTO')\
            .filter(MovimentacaoEstoque.observacao.like('%Sem Separação%'))\
            .all()
        
        # Extrair números de NF processadas como "Sem Separação"
        nfs_sem_separacao = set()
        for (obs,) in nfs_sem_separacao_query:
            if obs and 'Baixa automática NF' in obs:
                import re
                match = re.search(r'Baixa automática NF (\d+)', obs)
                if match:
                    nfs_sem_separacao.add(match.group(1))
        
        # Buscar NFs que já foram processadas COM separação (não reprocessar)
        nfs_com_separacao_query = db.session.query(MovimentacaoEstoque.observacao)\
            .filter(MovimentacaoEstoque.tipo_movimentacao == 'FATURAMENTO')\
            .filter(MovimentacaoEstoque.observacao.like('%lote separação%'))\
            .filter(~MovimentacaoEstoque.observacao.like('%Sem Separação%'))\
            .all()
        
        # Extrair números de NF já processadas com separação
        nfs_ja_processadas_com_separacao = set()
        for (obs,) in nfs_com_separacao_query:
            if obs and 'Baixa automática NF' in obs:
                import re
                match = re.search(r'Baixa automática NF (\d+)', obs)
                if match:
                    nfs_ja_processadas_com_separacao.add(match.group(1))
        
        # Subquery para NFs que têm produtos
        nfs_com_produtos = db.session.query(FaturamentoProduto.numero_nf).distinct().subquery()
        
        # Buscar NFs ativas que:
        # 1. Nunca foram processadas OU
        # 2. Foram processadas como "Sem Separação" (candidatas a reprocessamento)
        # 3. Mas NÃO foram processadas com separação
        todas_nfs = RelatorioFaturamentoImportado.query.filter(
            RelatorioFaturamentoImportado.ativo == True,
            RelatorioFaturamentoImportado.numero_nf.in_(
                db.session.query(nfs_com_produtos.c.numero_nf)
            ),
            ~RelatorioFaturamentoImportado.numero_nf.in_(nfs_ja_processadas_com_separacao)
        ).all()
        
        logger.info(f"📊 Busca corrigida: {len(todas_nfs)} NFs pendentes (incluindo {len(nfs_sem_separacao)} 'Sem Separação' para reprocessamento)")
        
        return todas_nfs
    
    def _processar_nf(self, nf: RelatorioFaturamentoImportado, usuario: str) -> int:
        """
        Processa uma NF específica e retorna o caso (1, 2 ou 3)
        """
        # Verificar se NF já foi processada como "Sem Separação"
        movimentacao_sem_separacao = MovimentacaoEstoque.query.filter(
            MovimentacaoEstoque.observacao.like(f'%NF {nf.numero_nf}%'),
            MovimentacaoEstoque.observacao.like('%Sem Separação%')
        ).first()
        
        # Verificar status no FaturamentoProduto
        produto_cancelado = FaturamentoProduto.query.filter_by(
            numero_nf=nf.numero_nf,
            status_nf='Cancelado'
        ).first()
        
        # Caso 3: NF Cancelada
        if produto_cancelado or not nf.ativo:
            self._processar_caso3_cancelamento(nf)
            return 3
        
        # ✅ CORRIGIDO: Verificar se embarque existe antes de acessar
        embarque_item_existente = EmbarqueItem.query.filter_by(
            nota_fiscal=nf.numero_nf
        ).first()
        
        if embarque_item_existente:
            # ✅ CORREÇÃO: Verificar se embarque ainda existe
            if embarque_item_existente.embarque is None:
                # Item órfão - embarque foi deletado
                logger.warning(f"EmbarqueItem órfão detectado: NF {nf.numero_nf} sem embarque")
                embarque_item_existente.nota_fiscal = None  # Limpar NF para reprocessamento
                db.session.commit()
            else:
                # Verificar se bate CNPJ e pedido
                embarque = embarque_item_existente.embarque
                
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
            # Se já foi processada como "Sem Separação", não precisa reprocessar
            if movimentacao_sem_separacao:
                logger.info(f"ℹ️ NF {nf.numero_nf} já processada como 'Sem Separação' - mantendo")
                return 1
            # Sem separação - gravar como "Sem Separação"
            self._criar_movimentacao_sem_separacao(nf, usuario)
            return 1
        
        # Se encontrou separações e havia movimentação "Sem Separação", deletar a antiga
        if movimentacao_sem_separacao and separacoes:
            logger.info(f"♾️ Reprocessando NF {nf.numero_nf}: encontrada separação para NF anteriormente 'Sem Separação'")
            # Deletar todas as movimentações antigas "Sem Separação" desta NF
            MovimentacaoEstoque.query.filter(
                MovimentacaoEstoque.observacao.like(f'%NF {nf.numero_nf}%'),
                MovimentacaoEstoque.observacao.like('%Sem Separação%')
            ).delete()
            db.session.commit()
        
        # Verificar match com separações
        logger.info(f"🔍 Vinculando NF {nf.numero_nf} com {len(separacoes)} separações encontradas")
        lote_vinculado, divergencia = self._vincular_com_separacao(nf, separacoes)
        
        if divergencia:
            # Caso 2: Separação != NF
            logger.info(f"⚠️ NF {nf.numero_nf} - Caso 2: Divergência detectada no lote {lote_vinculado}")
            self._processar_caso2_divergencia(nf, lote_vinculado, divergencia, usuario)
            return 2
        else:
            # Caso 1: Separação = NF
            logger.info(f"✅ NF {nf.numero_nf} - Caso 1: Processamento direto no lote {lote_vinculado}")
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
        ✅ CORRIGIDO: Score por quantidade por produto (não por lote total)
        """
        # Se só tem uma separação, usa ela
        if len(separacoes) == 1:
            return self._verificar_divergencia_simples(nf, separacoes[0])
        
        # Múltiplas separações - encontrar melhor match POR PRODUTO
        melhor_score = 0
        melhor_lote = None
        tem_divergencia = False
        
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
        
        # ✅ NOVO ALGORITMO: Score por quantidade por produto
        for lote_id, seps_lote in separacoes_por_lote.items():
            score_produtos = []
            produtos_divergentes = 0
            
            # Para cada produto da NF
            for prod_nf in produtos_nf:
                # Buscar separação correspondente no lote
                sep_correspondente = next(
                    (sep for sep in seps_lote if sep.cod_produto == prod_nf.cod_produto), 
                    None
                )
                
                if sep_correspondente:
                    # Calcular score de quantidade para este produto específico
                    qtd_nf = prod_nf.qtd_produto_faturado
                    qtd_sep = sep_correspondente.qtd_saldo
                    
                    if qtd_sep > 0:
                        # Score baseado na menor quantidade / maior quantidade
                        score_produto = min(qtd_nf, qtd_sep) / max(qtd_nf, qtd_sep)
                        score_produtos.append(score_produto)
                        
                        # Detectar divergência se diferença > 5%
                        if abs(qtd_nf - qtd_sep) / max(qtd_nf, qtd_sep) > 0.05:
                            produtos_divergentes += 1
                    else:
                        score_produtos.append(0)
                        produtos_divergentes += 1
                else:
                    # Produto não encontrado na separação
                    score_produtos.append(0)
                    produtos_divergentes += 1
            
            # Score médio do lote = média dos scores dos produtos
            score_lote = sum(score_produtos) / len(score_produtos) if score_produtos else 0
            
            if score_lote > melhor_score:
                melhor_score = score_lote
                melhor_lote = lote_id
                tem_divergencia = produtos_divergentes > 0
        
        logger.info(f"NF {nf.numero_nf}: Melhor lote {melhor_lote} com score {melhor_score:.2f}")
        
        return melhor_lote or '', tem_divergencia
    
    def _verificar_divergencia_simples(self, nf: RelatorioFaturamentoImportado, 
                                     separacao: Separacao) -> Tuple[str, bool]:
        """
        ✅ CORRIGIDO: Verifica divergência por produto específico
        """
        produtos_nf = FaturamentoProduto.query.filter_by(
            numero_nf=nf.numero_nf
        ).all()
        
        # Buscar produto específico na separação
        produto_correspondente = next(
            (p for p in produtos_nf if p.cod_produto == separacao.cod_produto), 
            None
        )
        
        if produto_correspondente:
            diferenca_percentual = abs(produto_correspondente.qtd_produto_faturado - separacao.qtd_saldo) / max(produto_correspondente.qtd_produto_faturado, separacao.qtd_saldo)
            tem_divergencia = diferenca_percentual > 0.05  # 5% de tolerância
        else:
            tem_divergencia = True  # Produto não encontrado
        
        return separacao.separacao_lote_id, tem_divergencia
    
    def _processar_caso1_direto(self, nf: RelatorioFaturamentoImportado, 
                               lote_id: str, usuario: str):
        """
        ✅ CORRIGIDO: Garantir faturamento negativo e criar produtos se não existirem
        """
        try:
            produtos = FaturamentoProduto.query.filter_by(numero_nf=nf.numero_nf).all()
            logger.info(f"📦 Processando {len(produtos)} produtos da NF {nf.numero_nf} para lote {lote_id}")
            
            for produto in produtos:
                try:
                    # ✅ VERIFICAR SE PRODUTO EXISTE EM PALLETIZAÇÃO
                    self._garantir_produto_existe(produto.cod_produto, produto.nome_produto)
                    
                    movimentacao = MovimentacaoEstoque()
                    movimentacao.cod_produto = produto.cod_produto
                    movimentacao.nome_produto = produto.nome_produto
                    movimentacao.tipo_movimentacao = 'FATURAMENTO'
                    movimentacao.local_movimentacao = 'VENDA'
                    # ✅ CORRIGIDO: Data sem vínculo direto na movimentação (usar data atual)
                    movimentacao.data_movimentacao = datetime.now().date()
                    # ✅ GARANTIDO: Sempre negativo para faturamento
                    movimentacao.qtd_movimentacao = -abs(produto.qtd_produto_faturado)
                    movimentacao.observacao = f"Baixa automática NF {nf.numero_nf} - lote separação {lote_id}"
                    movimentacao.criado_por = usuario
                    db.session.add(movimentacao)
                    logger.info(f"✅ Movimentação criada: Produto {produto.cod_produto}, Qtd: {movimentacao.qtd_movimentacao}")
                except Exception as e:
                    logger.error(f"❌ Erro ao criar movimentação para produto {produto.cod_produto}: {str(e)}")
                    raise
            
            # Atualizar EmbarqueItem com a NF
            self._atualizar_embarque_item(nf.numero_nf, lote_id)
        except Exception as e:
            logger.error(f"❌ Erro em _processar_caso1_direto para NF {nf.numero_nf}: {str(e)}")
            raise
    
    def _garantir_produto_existe(self, cod_produto: str, nome_produto: str):
        """
        ✅ CORRIGIDO: Cria produto em Palletização se não existir
        """
        try:
            from app.producao.models import CadastroPalletizacao
            
            produto_existente = CadastroPalletizacao.query.filter_by(
                cod_produto=cod_produto
            ).first()
            
            if not produto_existente:
                # Criar objeto e definir campos separadamente
                novo_produto = CadastroPalletizacao()
                novo_produto.cod_produto = cod_produto
                novo_produto.nome_produto = nome_produto or f'Produto {cod_produto}'
                novo_produto.peso_bruto = 0
                novo_produto.palletizacao = 1  # Valor padrão para evitar divisão por zero
                
                db.session.add(novo_produto)
                logger.info(f"✅ Produto {cod_produto} criado em Palletização")
                
        except ImportError:
            logger.warning(f"⚠️ Módulo Palletização não disponível para criar produto {cod_produto}")
        except Exception as e:
            logger.error(f"❌ Erro ao criar produto {cod_produto} em Palletização: {e}")
    
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
            # ✅ CORREÇÃO: Encontrar produto específico que corresponde à separação
            produto_correspondente = next(
                (p for p in produtos if p.cod_produto == separacao.cod_produto), 
                None
            )
            
            if produto_correspondente:
                justificativa = FaturamentoParcialJustificativa()
                justificativa.separacao_lote_id = lote_id
                justificativa.num_pedido = nf.origem
                justificativa.cod_produto = separacao.cod_produto
                justificativa.numero_nf = nf.numero_nf
                justificativa.qtd_separada = separacao.qtd_saldo
                # ✅ CORRIGIDO: Usar apenas quantidade do produto específico
                justificativa.qtd_faturada = produto_correspondente.qtd_produto_faturado
                justificativa.qtd_saldo = abs(separacao.qtd_saldo - produto_correspondente.qtd_produto_faturado)
                justificativa.motivo_nao_faturamento = 'DIVERGENCIA_AUTOMATICA'
                justificativa.descricao_detalhada = f'Divergência detectada: Separado {separacao.qtd_saldo}, Faturado {produto_correspondente.qtd_produto_faturado}'
                justificativa.classificacao_saldo = 'NECESSITA_COMPLEMENTO'
                justificativa.criado_por = usuario
                db.session.add(justificativa)
            else:
                logger.warning(f"⚠️ Produto {separacao.cod_produto} da separação {lote_id} não encontrado na NF {nf.numero_nf}")
    
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
            # ✅ VERIFICAR SE PRODUTO EXISTE EM PALLETIZAÇÃO
            self._garantir_produto_existe(produto.cod_produto, produto.nome_produto)
            
            movimentacao = MovimentacaoEstoque()
            movimentacao.cod_produto = produto.cod_produto
            movimentacao.nome_produto = produto.nome_produto
            movimentacao.tipo_movimentacao = 'FATURAMENTO'
            movimentacao.local_movimentacao = 'VENDA'
            movimentacao.data_movimentacao = datetime.now().date()
            # ✅ GARANTIDO: Sempre negativo para faturamento
            movimentacao.qtd_movimentacao = -abs(produto.qtd_produto_faturado)
            movimentacao.observacao = f"Baixa automática NF {nf.numero_nf} - Sem Separação"
            movimentacao.criado_por = usuario
            db.session.add(movimentacao)
    
    def _atualizar_embarque_item(self, numero_nf: str, lote_id: str):
        """
        ✅ MELHORADO: Atualiza EmbarqueItem e reprocessa órfãos
        """
        # Buscar item do embarque com este lote sem NF
        item = EmbarqueItem.query.filter_by(
            separacao_lote_id=lote_id,
            nota_fiscal=None
        ).first()
        
        if item:
            item.nota_fiscal = numero_nf
            logger.info(f"✅ NF {numero_nf} vinculada ao lote {lote_id}")
    
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
        - CNPJ NF: {nf.cnpj_cliente} vs CNPJ Embarque: {embarque_item.embarque.cnpj_cliente if embarque_item.embarque else 'EMBARQUE_DELETADO'}
        - Pedido NF: {nf.origem} vs Pedido Item: {embarque_item.pedido}
        Lote separação: {embarque_item.separacao_lote_id}
        """
        inconsistencia.resolvida = False
        
        db.session.add(inconsistencia)
        
        logger.warning(f"⚠️ Inconsistência gerada: NF {nf.numero_nf} vinculada incorretamente ao embarque {embarque_item.embarque_id}") 