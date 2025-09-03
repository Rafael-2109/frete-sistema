"""
Processamento de Faturamento Simplificado
========================================

Implementação simplificada e otimizada do processamento de NFs
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from decimal import Decimal
# MIGRADO: ServicoEstoqueTempoReal -> ServicoEstoqueSimples (02/09/2025)
from app.estoque.services.estoque_simples import ServicoEstoqueSimples as ServicoEstoqueTempoReal
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
        self, usuario: str = "Importação Odoo", 
        limpar_inconsistencias: bool = True,
        nfs_especificas: List[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Processa NFs importadas seguindo lógica simplificada
        COM MELHORIAS: Commits em lotes e tratamento de erros isolados
        
        Args:
            usuario: Usuário responsável pelo processamento
            limpar_inconsistencias: Se deve limpar inconsistências anteriores
            nfs_especificas: Lista de NFs específicas para processar (otimização)
                           Se None, busca NFs não processadas
                           
        Cenários de Processamento/Reprocessamento:
            1. NF nova importada → Cria MovimentacaoEstoque
            2. NF sem EmbarqueItem → Cria como "Sem Separação", reprocessa quando tiver
            3. NF sem Separacao → Cria sem lote, reprocessa quando encontrar
            4. NF com erro em EmbarqueItem → Reprocessa após correção
            5. NF reativada (des-cancelada) → Reprocessa para recriar movimentações
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

            # 1. Buscar NFs para processar
            if nfs_especificas:
                # 🚀 OTIMIZAÇÃO: Processar apenas NFs específicas (novas ou atualizadas)
                logger.info(f"🎯 Processando {len(nfs_especificas)} NFs específicas...")
                nfs_pendentes = self._buscar_nfs_especificas(nfs_especificas)
            else:
                # Fallback: buscar NFs não processadas (método otimizado)
                logger.info("🔍 Buscando NFs não processadas...")
                nfs_pendentes = self._buscar_nfs_nao_processadas()
            
            logger.info(f"📊 Total de NFs para processar: {len(nfs_pendentes)}")
            
            # Cache de separações por lote para evitar queries repetidas
            cache_separacoes = {}
            
            for idx, nf in enumerate(nfs_pendentes):
                try:
                    logger.debug(f"[{idx+1}/{len(nfs_pendentes)}] NF {nf.numero_nf}")

                    # Processar NF (verificação redundante removida)
                    processou, mov_criadas, emb_atualizados = self._processar_nf_simplificado(
                        nf, usuario, cache_separacoes
                    )
                    
                    if processou:
                        resultado["processadas"] += 1
                        resultado["movimentacoes_criadas"] += mov_criadas
                        resultado["embarque_items_atualizados"] += emb_atualizados

                except Exception as e:
                    logger.error(f"❌ Erro NF {nf.numero_nf}: {str(e)}")
                    resultado["erros"].append(f"NF {nf.numero_nf}: {str(e)}")
                    db.session.rollback()  # Rollback específico do erro
                    continue

            # Commit único no final (mais simples e seguro)
            try:
                db.session.commit()
                logger.debug(f"✅ Commit final de {resultado['processadas']} NFs processadas")
            except Exception as e:
                logger.error(f"❌ Erro no commit final: {e}")
                db.session.rollback()
            
            # NOVO: Atualizar status das separações para FATURADO
            logger.info("🔄 Atualizando status das separações para FATURADO...")
            separacoes_atualizadas = self._atualizar_status_separacoes_faturadas()
            if separacoes_atualizadas > 0:
                logger.info(f"✅ {separacoes_atualizadas} separações atualizadas para status FATURADO")
                resultado["separacoes_atualizadas_status"] = separacoes_atualizadas
            
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

    def _buscar_nfs_especificas(self, nfs_lista: List[str]) -> List[RelatorioFaturamentoImportado]:
        """
        Busca NFs específicas da lista fornecida
        
        Args:
            nfs_lista: Lista de números de NF para buscar
        """
        if not nfs_lista:
            return []
        
        # Remover duplicatas
        nfs_unicas = list(set(nfs_lista))
        
        return (
            RelatorioFaturamentoImportado.query.filter(
                RelatorioFaturamentoImportado.ativo == True,
                RelatorioFaturamentoImportado.numero_nf.in_(nfs_unicas)
            )
            .order_by(RelatorioFaturamentoImportado.numero_nf.desc())
            .all()
        )
    
    def _buscar_nfs_nao_processadas(self) -> List[RelatorioFaturamentoImportado]:
        """
        FLUXO ÚNICO: Busca NFs que precisam ser processadas ou REprocessadas
        Inclui:
        - NFs sem MovimentacaoEstoque
        - NFs com MovimentacaoEstoque mas sem separacao_lote_id (processamento incompleto)
        - NFs em EmbarqueItem com erro_validacao pendente
        
        GARANTE: Não duplicação - _tem_movimentacao_com_lote() verifica antes de criar
        """
        # Subquery para NFs que já têm movimentação COMPLETA (com lote)
        nfs_processadas_completas = db.session.query(MovimentacaoEstoque.numero_nf).filter(
            MovimentacaoEstoque.numero_nf.isnot(None),
            MovimentacaoEstoque.separacao_lote_id.isnot(None),  # Tem lote = processamento completo
            MovimentacaoEstoque.status_nf == 'FATURADO'
        ).distinct().subquery()
        
        # Subquery para NFs que precisam reprocessamento (sem lote ou com erro)
        nfs_reprocessar = db.session.query(MovimentacaoEstoque.numero_nf).filter(
            MovimentacaoEstoque.numero_nf.isnot(None),
            MovimentacaoEstoque.separacao_lote_id.is_(None),  # Sem lote = precisa reprocessar
            MovimentacaoEstoque.status_nf == 'FATURADO'
        ).distinct().subquery()
        
        # Subquery para NFs em EmbarqueItem com erro
        nfs_com_erro_embarque = db.session.query(EmbarqueItem.nota_fiscal).filter(
            EmbarqueItem.nota_fiscal.isnot(None),
            EmbarqueItem.erro_validacao.isnot(None)  # Com erro = precisa reprocessar
        ).distinct().subquery()
        
        # Subquery para NFs que têm produtos ativos
        nfs_com_produtos = db.session.query(FaturamentoProduto.numero_nf).filter(
            FaturamentoProduto.status_nf != 'Cancelado'  # Ignorar canceladas
        ).distinct().subquery()
        
        # Buscar NFs que:
        # 1. Não estão processadas completamente OU
        # 2. Estão marcadas para reprocessamento OU  
        # 3. Têm erro em EmbarqueItem
        return (
            RelatorioFaturamentoImportado.query.filter(
                RelatorioFaturamentoImportado.ativo == True,
                RelatorioFaturamentoImportado.numero_nf.in_(db.session.query(nfs_com_produtos.c.numero_nf)),
                db.or_(
                    # NFs não processadas completamente
                    ~RelatorioFaturamentoImportado.numero_nf.in_(db.session.query(nfs_processadas_completas.c.numero_nf)),
                    # NFs que precisam reprocessamento (sem lote)
                    RelatorioFaturamentoImportado.numero_nf.in_(db.session.query(nfs_reprocessar.c.numero_nf)),
                    # NFs com erro em EmbarqueItem
                    RelatorioFaturamentoImportado.numero_nf.in_(db.session.query(nfs_com_erro_embarque.c.numero_nf))
                )
            )
            .order_by(RelatorioFaturamentoImportado.numero_nf.desc())
            .all()  # Sem limite - máximo 50 NFs/dia na prática
        )
        
    def processar_fluxo_completo(self) -> Dict[str, Any]:
        """
        FLUXO ÚNICO COMPLETO: Processa todas as NFs que precisam (novas + incompletas)
        
        Garante:
        - Não duplica movimentações (verifica antes de criar)
        - Processa NFs novas
        - Reprocessa NFs incompletas
        - Tenta vincular separações que apareceram depois
        
        Returns:
            Dicionário com estatísticas completas
        """
        logger.info("🚀 FLUXO ÚNICO: Processando todas as NFs pendentes...")
        
        # Usar o método já otimizado que pega TUDO que precisa
        resultado = self.processar_nfs_importadas(
            usuario="Sincronização Completa",
            limpar_inconsistencias=True,
            nfs_especificas=None  # None = busca automática de todas pendentes
        )
        
        if resultado:
            logger.info(f"✅ FLUXO COMPLETO CONCLUÍDO:")
            logger.info(f"   - {resultado.get('processadas', 0)} NFs processadas")
            logger.info(f"   - {resultado.get('movimentacoes_criadas', 0)} movimentações criadas")
            logger.info(f"   - {resultado.get('embarque_items_atualizados', 0)} embarques atualizados")
            logger.info(f"   - {resultado.get('sem_separacao', 0)} sem separação (tentarão novamente depois)")
            
        return resultado or {"sucesso": False, "erro": "Processamento retornou None"}

    def _tem_movimentacao_com_lote(self, numero_nf: str) -> bool:
        """
        Verifica se NF já tem movimentação COM separacao_lote_id
        Sem fallback - todos os registros já foram migrados
        """
        resultado = MovimentacaoEstoque.query.filter(
            MovimentacaoEstoque.numero_nf == numero_nf,
            MovimentacaoEstoque.separacao_lote_id.isnot(None),
            MovimentacaoEstoque.status_nf == 'FATURADO'
        ).first()
        
        return resultado is not None

    def _processar_nf_simplificado(self, nf: RelatorioFaturamentoImportado, usuario: str, cache_separacoes: dict = None) -> tuple:
        """
        Processa NF seguindo ESPECIFICACAO_SINCRONIZACAO_ODOO.md
        
        Lógica:
        1. tipo_envio="total" ou 1 EmbarqueItem ativo → processar direto
        2. tipo_envio="parcial" com múltiplos EmbarqueItems → avaliar score
        3. Sem pedido encontrado → criar sem lote
        
        Usa cache de separações para evitar queries repetidas
        
        Retorna: (processou, movimentacoes_criadas, embarque_items_atualizados)
        """
        movimentacoes_criadas = 0
        embarque_items_atualizados = 0
        separacao_lote_id = None
        
        # Inicializar cache se não fornecido
        if cache_separacoes is None:
            cache_separacoes = {}
        
        logger.info(f"📋 Processando NF {nf.numero_nf} - Pedido {nf.origem}")
        
        # Buscar EmbarqueItems ativos para o pedido
        embarque_items = EmbarqueItem.query.join(
            Embarque, EmbarqueItem.embarque_id == Embarque.id
        ).filter(
            EmbarqueItem.pedido == nf.origem,
            EmbarqueItem.status == 'ativo',
            Embarque.status == 'ativo'
        ).all()
        
        # NOVO: Se não encontrou com o pedido correto, verificar se há items com divergência
        if not embarque_items:
            # Buscar EmbarqueItems que têm a NF mas com pedido divergente
            embarque_items_divergentes = EmbarqueItem.query.join(
                Embarque, EmbarqueItem.embarque_id == Embarque.id
            ).filter(
                EmbarqueItem.nota_fiscal == nf.numero_nf,
                EmbarqueItem.pedido != nf.origem,  # Pedido diferente
                EmbarqueItem.status == 'ativo',
                Embarque.status == 'ativo'
            ).all()
            
            if embarque_items_divergentes:
                logger.warning(f"⚠️ Encontrados {len(embarque_items_divergentes)} EmbarqueItems com divergência para NF {nf.numero_nf}")
                # Criar inconsistências para cada item divergente
                for item_div in embarque_items_divergentes:
                    self._gerar_inconsistencia_divergencia_embarque(nf, item_div, usuario)
                    # Marcar erro de validação no EmbarqueItem
                    if not item_div.erro_validacao:
                        item_div.erro_validacao = f"NF_DIVERGENTE: Pedido NF ({nf.origem}) != Pedido Item ({item_div.pedido})"
            
            # 4.4 da especificação - Pedido não encontrado
            logger.warning(f"⚠️ NF {nf.numero_nf} sem embarque ativo - criando sem lote")
            mov_criadas = self._criar_movimentacao_sem_separacao(nf, usuario)
            return True, mov_criadas, 0
        
        # Se apenas 1 EmbarqueItem, usar direto
        if len(embarque_items) == 1:
            separacao_lote_id = embarque_items[0].separacao_lote_id
            if separacao_lote_id:
                logger.info(f"✅ Único EmbarqueItem encontrado - usando lote {separacao_lote_id}")
            else:
                logger.warning(f"⚠️ EmbarqueItem sem lote - criando sem separação")
                mov_criadas = self._criar_movimentacao_sem_separacao(nf, usuario)
                return True, mov_criadas, 0
        else:
            # Múltiplos EmbarqueItems - verificar tipo_envio das Separações
            logger.info(f"🔍 {len(embarque_items)} EmbarqueItems encontrados - analisando tipo_envio")
            
            # Coletar lotes e verificar tipo_envio
            lotes_parciais = []
            lote_total = None
            
            for item in embarque_items:
                if not item.separacao_lote_id:
                    continue
                    
                # Usar cache ou buscar Separações do lote
                cache_key = f"{item.separacao_lote_id}_{nf.origem}"
                if cache_key not in cache_separacoes:
                    # Buscar apenas não sincronizadas
                    cache_separacoes[cache_key] = Separacao.query.filter_by(
                        separacao_lote_id=item.separacao_lote_id,
                        num_pedido=nf.origem,
                        sincronizado_nf=False  # IMPORTANTE: apenas não sincronizadas
                    ).all()
                
                separacoes_lote = cache_separacoes[cache_key]
                
                # Verificar tipo_envio da primeira Separação
                separacao = separacoes_lote[0] if separacoes_lote else None
                
                if separacao:
                    if separacao.tipo_envio == 'total':
                        lote_total = item.separacao_lote_id
                        logger.info(f"  • Lote {item.separacao_lote_id}: tipo_envio=TOTAL")
                        break  # Se encontrou total, usar este
                    else:
                        lotes_parciais.append(item.separacao_lote_id)
                        logger.info(f"  • Lote {item.separacao_lote_id}: tipo_envio=PARCIAL")
            
            # Decisão baseada no tipo_envio
            if lote_total:
                # 4.1 da especificação - Separação completa
                separacao_lote_id = lote_total
                logger.info(f"✅ Usando lote TOTAL {separacao_lote_id}")
            elif len(lotes_parciais) == 1:
                # 4.2 da especificação - Parcial único
                separacao_lote_id = lotes_parciais[0]
                logger.info(f"✅ Único lote PARCIAL {separacao_lote_id}")
            elif len(lotes_parciais) > 1:
                # 4.3 da especificação - Múltiplos parciais, calcular score
                logger.info(f"📊 Calculando score para {len(lotes_parciais)} lotes parciais")
                separacao_lote_id = self._calcular_melhor_lote_por_score_simples(nf, lotes_parciais, cache_separacoes, usuario)
            else:
                # Nenhum lote válido encontrado
                logger.warning(f"⚠️ Nenhum lote válido encontrado - criando sem separação")
                mov_criadas = self._criar_movimentacao_sem_separacao(nf, usuario)
                return True, mov_criadas, 0
        
        # PROCESSAR COM O LOTE ENCONTRADO
        if separacao_lote_id:
            logger.info(f"📦 Processando NF {nf.numero_nf} com lote {separacao_lote_id}")
            
            # 1. Atualizar EmbarqueItem
            embarque_item = EmbarqueItem.query.filter_by(
                separacao_lote_id=separacao_lote_id,
                pedido=nf.origem,
                status='ativo'
            ).first()
            
            if embarque_item:
                if not embarque_item.nota_fiscal:
                    embarque_item.nota_fiscal = nf.numero_nf
                    embarque_item.erro_validacao = None
                    embarque_items_atualizados += 1
                    logger.info(f"✅ EmbarqueItem atualizado com NF {nf.numero_nf}")
            
            # 2. Atualizar Separações do lote
            separacoes_atualizadas = Separacao.query.filter_by(
                separacao_lote_id=separacao_lote_id,
                num_pedido=nf.origem,
                sincronizado_nf=False
            ).update({
                'numero_nf': nf.numero_nf,
                'sincronizado_nf': True,
                'data_sincronizacao': datetime.now()
            })
            
            if separacoes_atualizadas > 0:
                logger.info(f"✅ {separacoes_atualizadas} Separações marcadas como sincronizadas")
            
            # 3. Criar MovimentacaoEstoque
            mov_criadas = self._criar_movimentacao_com_lote(nf, separacao_lote_id, usuario, cache_separacoes)
            movimentacoes_criadas += mov_criadas
            
            # 4. Atualizar status das Separações para FATURADO
            separacoes_status = Separacao.query.filter_by(
                separacao_lote_id=separacao_lote_id,
                num_pedido=nf.origem
            ).filter(
                Separacao.status != 'FATURADO'
            ).update({
                'status': 'FATURADO'
            })
            
            if separacoes_status > 0:
                logger.info(f"✅ {separacoes_status} Separações atualizadas para status FATURADO")
        
        return True, movimentacoes_criadas, embarque_items_atualizados
    
    def _calcular_melhor_lote_por_score_simples(self, nf: RelatorioFaturamentoImportado, lotes_candidatos: list, cache_separacoes: dict = None, usuario: str = 'sistema') -> Optional[str]:
        """
        Calcula score simples para múltiplos lotes parciais
        Score baseado em match de produtos e quantidades
        NOVO: Cria FaturamentoParcialJustificativa quando score < 0.99
        
        Returns:
            separacao_lote_id do melhor match
        """
        # Buscar produtos da NF
        produtos_nf = FaturamentoProduto.query.filter_by(numero_nf=nf.numero_nf).all()
        
        # Criar dict para fácil acesso
        nf_produtos_dict = {}
        for prod in produtos_nf:
            nf_produtos_dict[prod.cod_produto] = float(prod.qtd_produto_faturado)
        
        melhor_score = 0
        melhor_lote = None
        detalhes_melhor_lote = {}  # Para guardar informações do melhor match
        
        for lote_id in lotes_candidatos:
            # Usar cache se disponível
            cache_key = f"{lote_id}_{nf.origem}"
            if cache_separacoes and cache_key in cache_separacoes:
                separacoes = cache_separacoes[cache_key]
            else:
                # Buscar separações do lote
                separacoes = Separacao.query.filter_by(
                    separacao_lote_id=lote_id,
                    num_pedido=nf.origem,
                    sincronizado_nf=False
                ).all()
                # Adicionar ao cache se fornecido
                if cache_separacoes is not None:
                    cache_separacoes[cache_key] = separacoes
            
            if not separacoes:
                continue
            
            # Calcular score e guardar detalhes
            score_total = 0
            produtos_matched = 0
            detalhes_produtos = {}
            
            for sep in separacoes:
                if sep.cod_produto in nf_produtos_dict:
                    qtd_nf = nf_produtos_dict[sep.cod_produto]
                    qtd_sep = float(sep.qtd_saldo or 0)
                    
                    if qtd_sep > 0 and qtd_nf > 0:
                        # Score baseado na proximidade das quantidades
                        # 1.0 = quantidades idênticas, 0.0 = completamente diferentes
                        ratio = min(qtd_nf, qtd_sep) / max(qtd_nf, qtd_sep)
                        score_total += ratio
                        produtos_matched += 1
                        
                        # Guardar detalhes para possível justificativa
                        detalhes_produtos[sep.cod_produto] = {
                            'qtd_separada': qtd_sep,
                            'qtd_faturada': qtd_nf,
                            'qtd_saldo': qtd_sep - qtd_nf if qtd_sep > qtd_nf else 0,
                            'ratio': ratio
                        }
            
            # Score médio do lote
            if produtos_matched > 0:
                score_lote = score_total / len(nf_produtos_dict)  # Normalizar pelo total de produtos na NF
                logger.info(f"  Lote {lote_id}: score {score_lote:.2%} ({produtos_matched}/{len(nf_produtos_dict)} produtos)")
                
                if score_lote > melhor_score:
                    melhor_score = score_lote
                    melhor_lote = lote_id
                    detalhes_melhor_lote = detalhes_produtos
        
        # NOVO: Criar FaturamentoParcialJustificativa se score < 0.99 (divergência > 1%)
        if melhor_lote and melhor_score < 0.99:
            logger.warning(f"⚠️ Score {melhor_score:.2%} < 99% para lote {melhor_lote} - criando justificativas")
            
            for cod_produto, detalhes in detalhes_melhor_lote.items():
                # Verificar se há divergência significativa
                if detalhes['ratio'] < 0.99:
                    # Verificar se já existe justificativa
                    just_existente = FaturamentoParcialJustificativa.query.filter_by(
                        separacao_lote_id=melhor_lote,
                        num_pedido=nf.origem if hasattr(nf, 'origem') else None,
                        cod_produto=cod_produto,
                        numero_nf=nf.numero_nf
                    ).first()
                    
                    if not just_existente:
                        # Criar nova justificativa
                        just = FaturamentoParcialJustificativa()
                        just.separacao_lote_id = melhor_lote
                        just.num_pedido = nf.origem if hasattr(nf, 'origem') else None
                        just.cod_produto = cod_produto
                        just.numero_nf = nf.numero_nf
                        just.qtd_separada = detalhes['qtd_separada']
                        just.qtd_faturada = detalhes['qtd_faturada']
                        just.qtd_saldo = detalhes['qtd_saldo']
                        
                        # Deixar campos vazios como solicitado
                        just.motivo_nao_faturamento = ''  # Para preenchimento posterior
                        just.classificacao_saldo = ''  # Para preenchimento posterior
                        just.descricao_detalhada = f"Divergência detectada: Score {detalhes['ratio']:.2%}"
                        just.criado_por = usuario
                        # criado_em tem default
                        
                        db.session.add(just)
                        logger.info(f"  📝 Justificativa criada para produto {cod_produto}: Sep {detalhes['qtd_separada']} x Fat {detalhes['qtd_faturada']}")
        
        if melhor_lote:
            logger.info(f"✅ Melhor lote selecionado: {melhor_lote} (score: {melhor_score:.2%})")
        else:
            # Se nenhum lote teve score > 0, pegar o primeiro
            melhor_lote = lotes_candidatos[0] if lotes_candidatos else None
            logger.warning(f"⚠️ Nenhum lote com score positivo, usando primeiro: {melhor_lote}")
        
        return melhor_lote

    def _criar_movimentacao_sem_separacao(self, nf: RelatorioFaturamentoImportado, usuario: str) -> int:
        """
        Cria movimentação 'Sem Separação'
        Verifica por campos estruturados para evitar duplicação
        NOVO: Cria inconsistência tipo NF_SEM_SEPARACAO
        Retorna: quantidade de movimentações criadas
        """
        movimentacoes_criadas = 0
        
        # Verificar se já existe usando campos estruturados
        existe = MovimentacaoEstoque.query.filter(
            MovimentacaoEstoque.numero_nf == nf.numero_nf,
            MovimentacaoEstoque.separacao_lote_id.is_(None),  # Sem lote
            MovimentacaoEstoque.status_nf == 'FATURADO'
        ).first()

        if existe:
            logger.debug(f"Movimentação 'Sem Separação' já existe para NF {nf.numero_nf}")
            return 0

        produtos = FaturamentoProduto.query.filter_by(numero_nf=nf.numero_nf).all()
        logger.info(f"📦 Criando {len(produtos)} movimentações 'Sem Separação' para NF {nf.numero_nf}")
        
        # NOVO: Criar inconsistência NF_SEM_SEPARACAO
        self._criar_inconsistencia_nf_sem_separacao(nf, produtos, usuario)
        

        for produto in produtos:
            try:
                mov = MovimentacaoEstoque()
                mov.cod_produto = produto.cod_produto
                mov.nome_produto = produto.nome_produto
                mov.tipo_movimentacao = "FATURAMENTO"
                mov.local_movimentacao = "VENDA"
                mov.data_movimentacao = datetime.now().date()
                mov.qtd_movimentacao = -abs(produto.qtd_produto_faturado)
                
                # NOVO: Campos estruturados
                mov.numero_nf = nf.numero_nf
                mov.num_pedido = nf.origem if hasattr(nf, 'origem') else None
                mov.tipo_origem = 'ODOO'  # ProcessadorFaturamento processa dados do Odoo
                mov.status_nf = 'FATURADO'
                mov.separacao_lote_id = None  # Sem separação
                
                # Manter observação para compatibilidade
                mov.observacao = f"Baixa automática NF {nf.numero_nf} - Sem Separação"
                mov.criado_por = usuario
                db.session.add(mov)
                movimentacoes_criadas += 1
                logger.debug(f"  ✓ Movimentação criada: {produto.cod_produto} - Qtd: {mov.qtd_movimentacao}")
            except Exception as e:
                logger.error(f"  ✗ Erro ao criar movimentação para produto {produto.cod_produto}: {e}")
        
        logger.info(f"✅ {movimentacoes_criadas} movimentações 'Sem Separação' preparadas para NF {nf.numero_nf}")
        return movimentacoes_criadas

    def _criar_movimentacao_com_lote(self, nf: RelatorioFaturamentoImportado, lote_id: str, usuario: str, cache_separacoes: dict = None) -> int:
        """
        Cria movimentação com lote de separação
        Se já existir movimentação sem lote, apenas preenche o lote
        Retorna: quantidade de movimentações criadas/atualizadas
        """
        # Verificar se já existe movimentação sem lote para esta NF
        movs_sem_lote = MovimentacaoEstoque.query.filter(
            MovimentacaoEstoque.numero_nf == nf.numero_nf,
            MovimentacaoEstoque.separacao_lote_id.is_(None),
            MovimentacaoEstoque.status_nf == 'FATURADO'
        ).all()
        
        if movs_sem_lote:
            # Apenas preencher o lote nas movimentações existentes
            logger.info(f"🔄 Atualizando {len(movs_sem_lote)} movimentações existentes com lote {lote_id}")
            for mov in movs_sem_lote:
                mov.separacao_lote_id = lote_id
                mov.atualizado_em = datetime.now()
                mov.atualizado_por = 'ProcessadorFaturamento - Lote preenchido'
            return len(movs_sem_lote)
        
        # Criar novas movimentações se não existirem
        movimentacoes_criadas = 0
        produtos = FaturamentoProduto.query.filter_by(numero_nf=nf.numero_nf).all()
        logger.info(f"📦 Criando {len(produtos)} movimentações com lote {lote_id} para NF {nf.numero_nf}")

        for produto in produtos:
            try:
                mov = MovimentacaoEstoque()
                mov.cod_produto = produto.cod_produto
                mov.nome_produto = produto.nome_produto
                mov.tipo_movimentacao = "FATURAMENTO"
                mov.local_movimentacao = "VENDA"
                mov.data_movimentacao = datetime.now().date()
                mov.qtd_movimentacao = -abs(produto.qtd_produto_faturado)
                
                # NOVO: Campos estruturados
                mov.separacao_lote_id = lote_id
                mov.numero_nf = nf.numero_nf
                mov.num_pedido = nf.origem if hasattr(nf, 'origem') else None
                mov.tipo_origem = 'ODOO'  # ProcessadorFaturamento processa dados do Odoo
                mov.status_nf = 'FATURADO'
                
                # Buscar código do embarque se existir
                embarque_item = EmbarqueItem.query.filter_by(
                    separacao_lote_id=lote_id,
                    pedido=nf.origem
                ).first()
                if embarque_item:
                    mov.codigo_embarque = embarque_item.embarque_id
                
                # Manter observação para compatibilidade
                mov.observacao = f"Baixa automática NF {nf.numero_nf} - lote separação {lote_id}"
                mov.criado_por = usuario
                db.session.add(mov)
                movimentacoes_criadas += 1
                logger.debug(f"  ✓ Movimentação criada: {produto.cod_produto} - Qtd: {mov.qtd_movimentacao}")

                # Abater MovimentacaoPrevista SEM fallback de data
                try:
                    # Buscar separação no cache ou no banco
                    sep = None
                    if cache_separacoes:
                        # Procurar em todas as chaves do cache que contém o lote_id
                        for cache_key, separacoes in cache_separacoes.items():
                            if cache_key.startswith(f"{lote_id}_"):
                                sep = next((s for s in separacoes if s.cod_produto == produto.cod_produto), None)
                                if sep:
                                    break
                    
                    # Se não encontrou no cache, buscar no banco
                    if not sep:
                        sep = Separacao.query.filter_by(separacao_lote_id=lote_id, cod_produto=produto.cod_produto).first()
                    
                    if sep and sep.expedicao:
                        ServicoEstoqueTempoReal.atualizar_movimentacao_prevista(
                            cod_produto=produto.cod_produto,
                            data=sep.expedicao,
                            qtd_entrada=Decimal("0"),
                            qtd_saida=Decimal(str(-abs(produto.qtd_produto_faturado))),
                        )
                        logger.debug(f"  ✓ Previsão abatida para {produto.cod_produto}")
                except Exception as e:
                    logger.debug(f"  ⚠️ Falha ao abater previsão {produto.cod_produto}: {e}")
                    
            except Exception as e:
                logger.error(f"  ✗ Erro ao criar movimentação para produto {produto.cod_produto}: {e}")
        
        logger.info(f"✅ {movimentacoes_criadas} movimentações com lote preparadas para NF {nf.numero_nf}")        
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
        Atualiza EmbarqueItem com a NF e marca o Pedido como FATURADO
        Retorna: True se atualizou, False caso contrário
        """
        try:
            # Primeiro verificar se existe item para atualizar
            item = EmbarqueItem.query.filter_by(separacao_lote_id=lote_id, nota_fiscal=None).first()
            
            if not item:
                # Verificar se já foi atualizado anteriormente
                item_ja_atualizado = EmbarqueItem.query.filter_by(
                    separacao_lote_id=lote_id, 
                    nota_fiscal=numero_nf
                ).first()
                
                if item_ja_atualizado:
                    logger.debug(f"EmbarqueItem do lote {lote_id} já possui NF {numero_nf}")
                    return False
                else:
                    logger.warning(f"⚠️ Nenhum EmbarqueItem encontrado para lote {lote_id} sem NF")
                    return False
            
            # Atualizar o item
            item.nota_fiscal = numero_nf
            
            # Também limpar erro de validação se existir
            if item.erro_validacao in ['NF_PENDENTE_FATURAMENTO', 'NF_DIVERGENTE']:
                item.erro_validacao = None
                logger.info(f"✅ Erro de validação limpo para EmbarqueItem do lote {lote_id}")
            
            # IMPORTANTE: Atualizar status das Separações para FATURADO
            # Como Pedido é VIEW, atualizamos direto na Separação
            separacoes_atualizadas = Separacao.query.filter_by(
                separacao_lote_id=lote_id
            ).filter(
                Separacao.status != 'FATURADO'
            ).update({
                'status': 'FATURADO'
            })
            
            if separacoes_atualizadas > 0:
                logger.info(f"✅ {separacoes_atualizadas} Separações marcadas como FATURADO (lote {lote_id})")
            
            logger.info(f"✅ NF {numero_nf} vinculada ao EmbarqueItem do lote {lote_id} (ID: {item.id})")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro ao atualizar EmbarqueItem do lote {lote_id} com NF {numero_nf}: {e}")
            return False

    def _gerar_inconsistencia_divergencia_embarque(
        self, nf: RelatorioFaturamentoImportado, embarque_item: EmbarqueItem, usuario: str
    ):
        """
        Gera inconsistência para divergência NF x Embarque
        IMPORTANTE: Uma linha por produto para facilitar análise
        """
        produtos = FaturamentoProduto.query.filter_by(numero_nf=nf.numero_nf).all()
        inconsistencias_criadas = 0
        
        # Criar uma inconsistência por produto
        for produto in produtos:
            # Verificar se já existe inconsistência não resolvida para este produto
            inc_existente = InconsistenciaFaturamento.query.filter_by(
                numero_nf=nf.numero_nf,
                cod_produto=produto.cod_produto,
                tipo="DIVERGENCIA_NF_EMBARQUE",
                resolvida=False
            ).first()
            
            if inc_existente:
                # Atualizar observação com informações mais recentes
                inc_existente.observacao_resolucao = (
                    f"NF {nf.numero_nf} produto {produto.cod_produto} com divergência: "
                    f"Pedido NF: {nf.origem if hasattr(nf, 'origem') else 'N/A'}, "
                    f"Pedido EmbarqueItem: {embarque_item.pedido}, "
                    f"Embarque ID: {embarque_item.embarque_id}, "
                    f"Lote: {embarque_item.separacao_lote_id}"
                )
                logger.debug(f"Inconsistência DIVERGENCIA_NF_EMBARQUE atualizada para produto {produto.cod_produto}")
            else:
                # Criar nova inconsistência
                inc = InconsistenciaFaturamento()
                inc.tipo = "DIVERGENCIA_NF_EMBARQUE"
                inc.numero_nf = nf.numero_nf
                inc.num_pedido = nf.origem if hasattr(nf, 'origem') else None
                inc.cod_produto = produto.cod_produto
                inc.qtd_faturada = float(produto.qtd_produto_faturado)
                inc.saldo_disponivel = None  # Não aplicável neste caso
                inc.qtd_excesso = None  # Não aplicável
                inc.resolvida = False
                inc.acao_tomada = None  # Para usuário definir
                inc.observacao_resolucao = (
                    f"NF {nf.numero_nf} produto {produto.cod_produto} com divergência: "
                    f"Pedido NF: {nf.origem if hasattr(nf, 'origem') else 'N/A'}, "
                    f"Pedido EmbarqueItem: {embarque_item.pedido}, "
                    f"Embarque ID: {embarque_item.embarque_id}, "
                    f"Lote: {embarque_item.separacao_lote_id}"
                )
                # detectada_em tem default
                inc.resolvida_em = None
                inc.resolvida_por = None
                
                db.session.add(inc)
                inconsistencias_criadas += 1
        
        if inconsistencias_criadas > 0:
            logger.info(f"⚠️ {inconsistencias_criadas} inconsistências DIVERGENCIA_NF_EMBARQUE criadas para NF {nf.numero_nf}")

    def _criar_inconsistencia_nf_sem_separacao(self, nf: RelatorioFaturamentoImportado, produtos: list, usuario: str):
        """
        Cria inconsistência para NF sem separação
        IMPORTANTE: Uma linha por produto para facilitar análise
        """
        inconsistencias_criadas = 0
        
        # Criar uma inconsistência por produto
        for produto in produtos:
            # Verificar se já existe inconsistência não resolvida para este produto
            inc_existente = InconsistenciaFaturamento.query.filter_by(
                numero_nf=nf.numero_nf,
                cod_produto=produto.cod_produto,
                tipo="NF_SEM_SEPARACAO",
                resolvida=False
            ).first()
            
            if inc_existente:
                logger.debug(f"Inconsistência já existe para NF {nf.numero_nf} produto {produto.cod_produto}")
                continue
            
            # Criar nova inconsistência
            inc = InconsistenciaFaturamento()
            inc.tipo = "NF_SEM_SEPARACAO"
            inc.numero_nf = nf.numero_nf
            inc.num_pedido = nf.origem if hasattr(nf, 'origem') else None
            inc.cod_produto = produto.cod_produto
            inc.qtd_faturada = float(produto.qtd_produto_faturado)
            inc.saldo_disponivel = None  # Não há separação
            inc.qtd_excesso = None  # Não aplicável
            inc.resolvida = False
            inc.acao_tomada = None  # Para usuário definir
            inc.observacao_resolucao = (
                f"Produto {produto.cod_produto} - {produto.nome_produto[:50]}... "
                f"faturado sem separação. Qtd: {produto.qtd_produto_faturado}. "
                f"Verificar pedido {nf.origem if hasattr(nf, 'origem') else 'N/A'}"
            )
            # detectada_em tem default
            inc.resolvida_em = None
            inc.resolvida_por = None
            
            db.session.add(inc)
            inconsistencias_criadas += 1
        
        if inconsistencias_criadas > 0:
            logger.info(f"⚠️ {inconsistencias_criadas} inconsistências NF_SEM_SEPARACAO criadas para NF {nf.numero_nf}")
    
    def _atualizar_status_separacoes_faturadas(self) -> int:
        """
        Atualiza o status das Separações para FATURADO quando têm NF preenchida
        e existe faturamento correspondente.
        
        Como Pedido agora é uma VIEW, trabalhamos diretamente com Separação
        
        Returns:
            Número de separações atualizadas
        """
        contador = 0
        
        try:
            # Buscar separações com NF mas sem status FATURADO
            separacoes_com_nf = Separacao.query.filter(
                Separacao.numero_nf.isnot(None),
                Separacao.numero_nf != "",
                Separacao.sincronizado_nf == True,
                Separacao.status != 'FATURADO'
            ).all()
            
            logger.info(f"📊 Encontradas {len(separacoes_com_nf)} separações com NF mas sem status FATURADO")
            
            for sep in separacoes_com_nf:
                # Verificar se existe faturamento para esta NF
                faturamento_existe = FaturamentoProduto.query.filter_by(
                    numero_nf=sep.numero_nf
                ).first()
                
                if faturamento_existe:
                    status_antigo = sep.status
                    sep.status = 'FATURADO'
                    contador += 1
                    logger.debug(f"  • Separação {sep.separacao_lote_id}/{sep.num_pedido}: '{status_antigo}' → 'FATURADO' (NF: {sep.numero_nf})")
            
            # Também verificar EmbarqueItems com NF para garantir Separações FATURADAS
            logger.info("🔍 Verificando EmbarqueItems com NF para garantir Separações FATURADAS...")
            
            embarque_items_com_nf = EmbarqueItem.query.filter(
                EmbarqueItem.nota_fiscal.isnot(None),
                EmbarqueItem.nota_fiscal != "",
                EmbarqueItem.separacao_lote_id.isnot(None)
            ).all()
            
            for item in embarque_items_com_nf:
                # Atualizar todas as separações deste lote
                sep_atualizadas = Separacao.query.filter_by(
                    separacao_lote_id=item.separacao_lote_id
                ).filter(
                    Separacao.status != 'FATURADO'
                ).update({
                    'status': 'FATURADO',
                    'numero_nf': item.nota_fiscal,
                    'sincronizado_nf': True,
                    'data_sincronizacao': datetime.now()
                })
                
                if sep_atualizadas > 0:
                    contador += sep_atualizadas
                    logger.debug(f"  • {sep_atualizadas} separações do lote {item.separacao_lote_id} atualizadas para FATURADO")
            
            if contador > 0:
                db.session.commit()
                logger.info(f"✅ Total: {contador} separações atualizadas para FATURADO")
            
        except Exception as e:
            logger.error(f"❌ Erro ao atualizar status das separações: {e}")
            db.session.rollback()
        
        return contador
