"""
Processador de Faturamento para integração TagPlus
Integra com ProcessadorFaturamento existente para usar score e movimentações
Inclui todas as sincronizações do FaturamentoService
"""

import logging
from datetime import datetime
from app import db
from app.faturamento.models import FaturamentoProduto, RelatorioFaturamentoImportado
from app.faturamento.services.processar_faturamento import ProcessadorFaturamento
from app.embarques.models import EmbarqueItem
from app.carteira.models import CarteiraCopia
from app.estoque.models import MovimentacaoEstoque
from app.estoque.services.estoque_tempo_real import ServicoEstoqueTempoReal
from sqlalchemy import and_

logger = logging.getLogger(__name__)


class ProcessadorFaturamentoTagPlus:
    """Processa faturamento do TagPlus usando lógica existente do sistema"""

    def __init__(self):
        # Usa o processador existente para aproveitar a lógica de score
        self.processador_base = ProcessadorFaturamento()
        self.nfs_processadas = []
        self.movimentacoes_criadas = []
        self.inconsistencias = []

    def processar_nf_tagplus(self, faturamento_produto):
        """Processa uma NF do TagPlus aplicando todas as regras do sistema"""
        erros_etapa = []
        try:
            logger.info(f"Processando NF TagPlus {faturamento_produto.numero_nf}")

            # 1. Encontrar separação usando CNPJ + Produto + Qtd (score)
            embarque_item_match = None
            separacao_lote_id = None
            num_pedido = None

            try:
                embarque_item_match = self._encontrar_separacao_por_score(faturamento_produto)
                separacao_lote_id = embarque_item_match.separacao_lote_id if embarque_item_match else None
                num_pedido = embarque_item_match.pedido if embarque_item_match else None
            except Exception as e:
                logger.error(f"Erro ao buscar separação: {e}")
                erros_etapa.append(f"Busca separação: {str(e)}")

            # 2. Criar movimentação de estoque (SEMPRE EXECUTAR)
            try:
                self._criar_movimentacao_estoque(faturamento_produto, separacao_lote_id)
            except Exception as e:
                logger.error(f"Erro ao criar movimentação: {e}")
                erros_etapa.append(f"Movimentação estoque: {str(e)}")

            # 3. Atualizar EmbarqueItem se encontrado (SEMPRE TENTAR)
            if embarque_item_match:
                try:
                    self._atualizar_embarque_item(faturamento_produto, embarque_item_match)
                except Exception as e:
                    logger.error(f"Erro ao atualizar EmbarqueItem: {e}")
                    erros_etapa.append(f"Atualizar EmbarqueItem: {str(e)}")

                # Caso 1 ou 3: Abater MovimentacaoPrevista usando data da Separacao (sem fallback)
                try:
                    from app.separacao.models import Separacao

                    sep = Separacao.query.filter_by(
                        separacao_lote_id=embarque_item_match.separacao_lote_id,
                        cod_produto=faturamento_produto.cod_produto,
                    ).first()
                    if sep and sep.expedicao:
                        ServicoEstoqueTempoReal.atualizar_movimentacao_prevista(
                            cod_produto=faturamento_produto.cod_produto,
                            data=sep.expedicao,
                            qtd_entrada=0,
                            qtd_saida=-abs(faturamento_produto.qtd_produto_faturado),
                        )
                except Exception as e:
                    logger.debug(
                        f"Falha ao abater previsão TagPlus NF {faturamento_produto.numero_nf}/{faturamento_produto.cod_produto}: {e}"
                    )

            # 4. Atualizar origem no FaturamentoProduto (SEMPRE TENTAR)
            if num_pedido:
                try:
                    faturamento_produto.origem = num_pedido
                    # NOTA: baixa_produto_pedido agora é calculada dinamicamente via hybrid_property
                except Exception as e:
                    logger.error(f"Erro ao atualizar origem: {e}")
                    erros_etapa.append(f"Atualizar origem: {str(e)}")

            # 5. Consolidar em RelatorioFaturamentoImportado (SEMPRE EXECUTAR)
            try:
                self._consolidar_relatorio(faturamento_produto, num_pedido)
            except Exception as e:
                logger.error(f"Erro ao consolidar relatório: {e}")
                erros_etapa.append(f"Consolidar relatório: {str(e)}")

            # 6. Sincronizar CarteiraPrincipal se houver pedido
            if num_pedido:
                try:
                    self._sincronizar_carteira_principal(num_pedido, faturamento_produto.cod_produto)
                except Exception as e:
                    logger.error(f"Erro ao sincronizar CarteiraPrincipal: {e}")
                    erros_etapa.append(f"Sincronizar CarteiraPrincipal: {str(e)}")

            # Registra como processada mesmo com erros parciais
            self.nfs_processadas.append(faturamento_produto.numero_nf)

            # Se houve erros, registra inconsistência
            if erros_etapa:
                self.inconsistencias.append(
                    {"nf": faturamento_produto.numero_nf, "erros_parciais": erros_etapa, "processada": True}
                )

        except Exception as e:
            logger.error(f"Erro geral ao processar NF {faturamento_produto.numero_nf}: {e}")
            self.inconsistencias.append({"nf": faturamento_produto.numero_nf, "erro": str(e), "processada": False})

    def _encontrar_separacao_por_score(self, faturamento):
        """Encontra separação usando lógica de score (CNPJ + Produto + Qtd)"""
        try:
            # Importa modelos necessários
            from app.embarques.models import Embarque
            from app.utils.cnpj_utils import normalizar_cnpj
            from app.separacao.models import Separacao

            # Normaliza CNPJ do faturamento para busca
            cnpj_normalizado = normalizar_cnpj(faturamento.cnpj_cliente)
            
            # Busca EmbarqueItens do mesmo CNPJ com critérios específicos
            # Não fazemos JOIN com CarteiraCopia aqui pois EmbarqueItem não tem cod_produto
            embarque_items_candidatos = (
                EmbarqueItem.query.join(Embarque, EmbarqueItem.embarque_id == Embarque.id)
                .filter(
                    EmbarqueItem.numero_nf.is_(None),  # Ainda não faturado
                    Embarque.status == "ativo",  # Embarque ativo
                    EmbarqueItem.status == "ativo",  # Item ativo
                    EmbarqueItem.erro_validacao.isnot(None),  # Tem erro de validação (candidato a faturamento)
                )
                .all()
            )
            
            # Filtra manualmente pelo CNPJ normalizado e busca informações da Separacao
            embarque_items = []
            items_com_separacao = []  # Lista para armazenar (item, separacao_info)
            
            for item in embarque_items_candidatos:
                # Busca a CarteiraCopia para pegar o CNPJ
                carteira = CarteiraCopia.query.filter_by(
                    num_pedido=item.pedido
                ).first()
                
                if carteira and normalizar_cnpj(carteira.cnpj_cpf) == cnpj_normalizado:
                    # Busca informações da Separacao para este item
                    separacoes = Separacao.query.filter_by(
                        separacao_lote_id=item.separacao_lote_id,
                        cod_produto=faturamento.cod_produto  # Filtra pelo produto do faturamento
                    ).all()
                    
                    # Se encontrou separações do produto, adiciona à lista
                    for sep in separacoes:
                        items_com_separacao.append({
                            'embarque_item': item,
                            'cod_produto': sep.cod_produto,
                            'qtd_separada': sep.qtd_saldo or 0
                        })

            if not items_com_separacao:
                logger.info(
                    f"Nenhum EmbarqueItem ativo com erro_validacao encontrado para CNPJ {faturamento.cnpj_cliente} e produto {faturamento.cod_produto}"
                )
                return None

            logger.info(
                f"Encontrados {len(items_com_separacao)} EmbarqueItems candidatos para CNPJ {faturamento.cnpj_cliente}"
            )

            # Calcula score para cada item
            melhor_match = None
            melhor_score = 0

            for item_info in items_com_separacao:
                item = item_info['embarque_item']
                cod_produto = item_info['cod_produto']
                qtd_separada = item_info['qtd_separada']
                score = 0

                # Score por produto (peso maior) - agora sempre será igual pois já filtramos
                if cod_produto == faturamento.cod_produto:
                    score += 50

                # Score por quantidade (exata ou próxima)
                if qtd_separada == faturamento.qtd_produto_faturado:
                    score += 40  # Quantidade exata
                elif qtd_separada > 0:
                    # Tolerância de 10%
                    diff_percent = abs(qtd_separada - faturamento.qtd_produto_faturado) / qtd_separada
                    if diff_percent <= 0.1:
                        score += 30
                    elif diff_percent <= 0.2:
                        score += 20

                # Score por data (embarques mais recentes)
                if hasattr(item, "criado_em"):
                    dias_diff = (datetime.now() - item.criado_em).days
                    if dias_diff <= 7:
                        score += 10

                if score > melhor_score:
                    melhor_score = score
                    melhor_match = item

            # Retorna separacao_lote_id se score for maior que 0 (igual ProcessadorFaturamento)
            if melhor_score > 0 and melhor_match:
                logger.info(
                    f"Melhor match encontrado: separacao_lote_id={melhor_match.separacao_lote_id}, score={melhor_score}"
                )
                return melhor_match
            else:
                logger.info(f"Nenhum match encontrado. Melhor score: {melhor_score}")
                return None

        except Exception as e:
            logger.error(f"Erro ao buscar separação por score: {e}")
            return None

    def _criar_movimentacao_estoque(self, faturamento, separacao_lote_id):
        """Cria movimentação de estoque igual ao Odoo"""
        try:
            # Define observação igual ao Odoo
            if separacao_lote_id:
                observacao = f"Baixa automática NF {faturamento.numero_nf} - Lote {separacao_lote_id}"
            else:
                observacao = f"Baixa automática NF {faturamento.numero_nf} - Sem Separação"

            # Verifica se já existe para evitar duplicação
            existe = MovimentacaoEstoque.query.filter(
                MovimentacaoEstoque.cod_produto == faturamento.cod_produto,
                MovimentacaoEstoque.observacao.contains(f"NF {faturamento.numero_nf}"),
            ).first()

            if existe:
                logger.info(f"Movimentação já existe para NF {faturamento.numero_nf}")
                return

            # Cria movimentação igual ao Odoo
            mov = MovimentacaoEstoque()
            mov.cod_produto = faturamento.cod_produto
            mov.nome_produto = faturamento.nome_produto
            mov.tipo_movimentacao = "FATURAMENTO TAGPLUS"
            mov.local_movimentacao = "VENDA"
            mov.data_movimentacao = faturamento.data_fatura
            mov.qtd_movimentacao = -abs(faturamento.qtd_produto_faturado)  # Negativo para saída
            mov.observacao = observacao
            mov.criado_por = "Sistema"  # Igual ao Odoo

            db.session.add(mov)
            self.movimentacoes_criadas.append(mov)

            logger.info(f"Movimentação criada: {observacao}")

        except Exception as e:
            logger.error(f"Erro ao criar movimentação: {e}")
            raise

    def _atualizar_embarque_item(self, faturamento, embarque_item):
        """Atualiza EmbarqueItem com número da NF"""
        try:
            if not embarque_item:
                return None

            # Atualiza apenas o número da NF
            embarque_item.numero_nf = faturamento.numero_nf

            logger.info(f"EmbarqueItem atualizado com NF {faturamento.numero_nf}")
            return embarque_item

        except Exception as e:
            logger.error(f"Erro ao atualizar EmbarqueItem: {e}")
            return None

    # REMOVIDO: _atualizar_baixa_carteira não é mais necessário
    # A baixa_produto_pedido agora é calculada dinamicamente via hybrid_property em CarteiraCopia
    # que soma automaticamente todos os FaturamentoProduto onde origem = num_pedido

    def _sincronizar_carteira_principal(self, num_pedido, cod_produto):
        """Sincroniza qtd_saldo_produto_pedido da CarteiraPrincipal com CarteiraCopia"""
        try:
            # Busca CarteiraCopia
            carteira_copia = CarteiraCopia.query.filter_by(num_pedido=num_pedido, cod_produto=cod_produto).first()

            if carteira_copia:
                # Recalcula saldo com a baixa dinâmica
                carteira_copia.recalcular_saldo()

                # Sincroniza com CarteiraPrincipal
                carteira_copia.sincronizar_com_principal()

                logger.info(f"CarteiraPrincipal sincronizada para {num_pedido}/{cod_produto}")
            else:
                logger.warning(f"CarteiraCopia não encontrada: {num_pedido}/{cod_produto}")

        except Exception as e:
            logger.error(f"Erro ao sincronizar CarteiraPrincipal: {e}")
            raise

    def _consolidar_relatorio(self, faturamento, num_pedido=None):
        """Consolida NF em RelatorioFaturamentoImportado"""
        try:
            # Verifica se já existe
            existe = RelatorioFaturamentoImportado.query.filter_by(numero_nf=faturamento.numero_nf).first()

            if existe:
                logger.info(f"NF {faturamento.numero_nf} já consolidada")
                return


            # Calcula totais da NF
            itens_nf = FaturamentoProduto.query.filter_by(numero_nf=faturamento.numero_nf).all()

            valor_total = sum(item.valor_produto_faturado for item in itens_nf)
            peso_total = sum(item.peso_total or 0 for item in itens_nf)

            # Cria registro consolidado
            relatorio = RelatorioFaturamentoImportado(
                numero_nf=faturamento.numero_nf,
                data_fatura=faturamento.data_fatura,
                cnpj_cliente=faturamento.cnpj_cliente,
                nome_cliente=faturamento.nome_cliente,
                valor_total=valor_total,
                peso_bruto=peso_total,
                cnpj_transportadora="",  # TagPlus não envia
                nome_transportadora="",  # TagPlus não envia
                municipio=faturamento.municipio,
                estado=faturamento.estado,
                codigo_ibge="",  # Buscar depois se necessário
                origem=num_pedido or "TagPlus",  # Inclui número do pedido se encontrado
                incoterm=faturamento.incoterm or "CIF",
                vendedor=faturamento.vendedor,
                equipe_vendas=faturamento.equipe_vendas,
                ativo=True,
                criado_em=datetime.utcnow(),
            )

            db.session.add(relatorio)
            logger.info(f"NF {faturamento.numero_nf} consolidada em RelatorioFaturamentoImportado")

        except Exception as e:
            logger.error(f"Erro ao consolidar relatório: {e}")

    def processar_lote_nfs(self):
        """Processa todas as NFs TagPlus pendentes"""
        try:
            # Busca NFs TagPlus não processadas
            nfs_pendentes = (
                FaturamentoProduto.query.filter(
                    FaturamentoProduto.created_by == "ImportTagPlus", FaturamentoProduto.status_nf == "Lançado"
                )
                .filter(~FaturamentoProduto.numero_nf.in_(db.session.query(RelatorioFaturamentoImportado.numero_nf)))
                .all()
            )

            logger.info(f"Encontradas {len(nfs_pendentes)} itens de NFs TagPlus para processar")

            # CORREÇÃO: Processa TODOS os itens, não apenas um por NF
            itens_processados = 0
            for nf_item in nfs_pendentes:
                self.processar_nf_tagplus(nf_item)
                itens_processados += 1

            # Commit final
            db.session.commit()

            return {
                "success": True,
                "nfs_processadas": len(set(self.nfs_processadas)),  # NFs únicas
                "itens_processados": itens_processados,
                "movimentacoes_criadas": len(self.movimentacoes_criadas),
                "inconsistencias": len(self.inconsistencias),
                "detalhes": {
                    "nfs": list(set(self.nfs_processadas))[:10],  # Primeiras 10 NFs únicas
                    "inconsistencias": self.inconsistencias,
                },
            }

        except Exception as e:
            logger.error(f"Erro no processamento em lote: {e}")
            db.session.rollback()
            return {"success": False, "erro": str(e)}

    def processar_nf_completo(self, faturamento_produto):
        """
        Processa um ITEM de NF do TagPlus com TODAS as sincronizações
        Equivalente ao sincronizar_faturamento_incremental do Odoo
        """
        try:
            logger.info(
                f"🚀 Processamento completo item TagPlus: NF {faturamento_produto.numero_nf} - Produto {faturamento_produto.cod_produto}"
            )

            # 1. Processamento base (score, movimentações, carteira) - POR ITEM
            self.processar_nf_tagplus(faturamento_produto)

            # NOTA: As etapas 2-5 são por NF, não por item
            # Então vamos executá-las apenas uma vez por NF para evitar duplicação
            # Usando um controle de NFs já processadas para estas etapas

            if not hasattr(self, "_nfs_sincronizacoes_completas"):
                self._nfs_sincronizacoes_completas = set()

            if faturamento_produto.numero_nf not in self._nfs_sincronizacoes_completas:
                self._nfs_sincronizacoes_completas.add(faturamento_produto.numero_nf)

                # 2. Sincronizar entrega monitorada (UMA VEZ POR NF)
                try:
                    from app.utils.sincronizar_entregas import sincronizar_entrega_por_nf

                    sincronizar_entrega_por_nf(faturamento_produto.numero_nf)
                    logger.info(f"✅ Entrega sincronizada para NF {faturamento_produto.numero_nf}")
                except Exception as e:
                    logger.error(f"❌ Erro ao sincronizar entrega: {e}")

                # 3. Re-validar embarques pendentes (UMA VEZ POR NF)
                try:
                    from app.faturamento.routes import revalidar_embarques_pendentes

                    resultado_revalidacao = revalidar_embarques_pendentes([faturamento_produto.numero_nf])
                    if resultado_revalidacao:
                        logger.info(f"✅ Embarques revalidados para NF {faturamento_produto.numero_nf}")
                except Exception as e:
                    logger.error(f"❌ Erro ao revalidar embarques: {e}")

                # 4. Sincronizar NFs pendentes em embarques (UMA VEZ POR NF)
                try:
                    from app.faturamento.routes import sincronizar_nfs_pendentes_embarques

                    nfs_sync = sincronizar_nfs_pendentes_embarques([faturamento_produto.numero_nf])
                    if nfs_sync:
                        logger.info(f"✅ NFs de embarques sincronizadas: {nfs_sync}")
                except Exception as e:
                    logger.error(f"❌ Erro ao sincronizar NFs de embarques: {e}")

                # 5. Lançamento automático de fretes (UMA VEZ POR CNPJ)
                try:
                    from app.fretes.routes import processar_lancamento_automatico_fretes

                    sucesso, resultado = processar_lancamento_automatico_fretes(
                        cnpj_cliente=faturamento_produto.cnpj_cliente, usuario="ImportTagPlus"
                    )
                    if sucesso:
                        logger.info(f"✅ Frete processado para CNPJ {faturamento_produto.cnpj_cliente}: {resultado}")
                except Exception as e:
                    logger.error(f"❌ Erro ao processar frete: {e}")

        except Exception as e:
            logger.error(f"❌ Erro no processamento completo: {e}")
            raise

    def processar_lote_completo(self, nfs_produtos=None):
        """
        Processa lote de NFs com todas as sincronizações
        Se nfs_produtos não for fornecido, busca NFs pendentes
        """
        try:
            import time

            start_time = time.time()

            # Se não passou lista específica, busca pendentes
            if nfs_produtos is None:
                nfs_produtos = (
                    FaturamentoProduto.query.filter(
                        FaturamentoProduto.created_by == "ImportTagPlus", FaturamentoProduto.status_nf == "Lançado"
                    )
                    .filter(
                        ~FaturamentoProduto.numero_nf.in_(db.session.query(RelatorioFaturamentoImportado.numero_nf))
                    )
                    .all()
                )

            logger.info(f"📊 Processando {len(nfs_produtos)} itens de NFs TagPlus com sincronização completa...")

            # Estatísticas
            stats = {
                "nfs_processadas": 0,
                "itens_processados": 0,
                "movimentacoes_criadas": 0,
                "entregas_sincronizadas": 0,
                "embarques_revalidados": 0,
                "nfs_embarques_sync": 0,
                "fretes_lancados": 0,
                "erros": [],
            }

            # CORREÇÃO: Agrupa por NF mas mantém TODOS os produtos
            nfs_agrupadas = {}
            for nf_produto in nfs_produtos:
                if nf_produto.numero_nf not in nfs_agrupadas:
                    nfs_agrupadas[nf_produto.numero_nf] = []
                nfs_agrupadas[nf_produto.numero_nf].append(nf_produto)

            # Processa cada NF com TODOS seus produtos
            for numero_nf, produtos_nf in nfs_agrupadas.items():
                try:
                    logger.info(f"Processando NF {numero_nf} com {len(produtos_nf)} itens")

                    # Processa CADA produto da NF
                    for produto in produtos_nf:
                        self.processar_nf_completo(produto)
                        stats["itens_processados"] += 1

                    stats["nfs_processadas"] += 1
                except Exception as e:
                    stats["erros"].append(f"NF {numero_nf}: {str(e)}")

            # Commit final
            db.session.commit()

            # Estatísticas finais
            tempo_execucao = time.time() - start_time
            stats["movimentacoes_criadas"] = len(self.movimentacoes_criadas)
            stats["tempo_execucao"] = f"{tempo_execucao:.2f}s"

            logger.info(f"✅ PROCESSAMENTO COMPLETO TAGPLUS FINALIZADO:")
            logger.info(f"   📄 {stats['nfs_processadas']} NFs processadas")
            logger.info(f"   📦 {stats['itens_processados']} itens processados")
            logger.info(f"   🏭 {stats['movimentacoes_criadas']} movimentações criadas")
            logger.info(f"   ⏱️ Tempo execução: {stats['tempo_execucao']}")
            logger.info(f"   ❌ {len(stats['erros'])} erros")

            return {
                "success": True,
                "estatisticas": stats,
                "nfs_processadas": self.nfs_processadas,
                "inconsistencias": self.inconsistencias,
            }

        except Exception as e:
            logger.error(f"❌ Erro no processamento em lote completo: {e}")
            db.session.rollback()
            return {"success": False, "erro": str(e)}
