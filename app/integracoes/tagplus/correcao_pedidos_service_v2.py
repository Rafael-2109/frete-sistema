"""
Serviço para correção de pedidos em NFs pendentes do TagPlus
Versão 2 - Usando a nova tabela NFPendenteTagPlus
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from app import db
from app.integracoes.tagplus.models import NFPendenteTagPlus
from app.faturamento.models import FaturamentoProduto, RelatorioFaturamentoImportado
from app.carteira.models import CadastroCliente
from app.estoque.models import MovimentacaoEstoque
from app.separacao.models import Separacao
from app.embarques.models import EmbarqueItem
from app.utils.sincronizar_entregas import sincronizar_entrega_por_nf
from sqlalchemy import func

logger = logging.getLogger(__name__)


class CorrecaoPedidosServiceV2:
    """
    Serviço para correção de pedidos em NFs pendentes (nova tabela)
    """

    def listar_nfs_pendentes(self, limite: int = 100) -> List[Dict[str, Any]]:
        """
        Lista NFs pendentes de preenchimento de pedido
        """
        try:
            # Buscar NFs agrupadas
            nfs_agrupadas = db.session.query(
                NFPendenteTagPlus.numero_nf,
                NFPendenteTagPlus.cnpj_cliente,
                NFPendenteTagPlus.nome_cliente,
                NFPendenteTagPlus.nome_cidade,
                NFPendenteTagPlus.cod_uf,
                NFPendenteTagPlus.data_fatura,
                func.max(NFPendenteTagPlus.origem).label('origem_nf'),
                func.count(NFPendenteTagPlus.id).label('qtd_itens'),
                func.sum(NFPendenteTagPlus.valor_produto_faturado).label('valor_total'),
                func.sum(NFPendenteTagPlus.qtd_produto_faturado).label('qtd_total'),
                func.bool_or(NFPendenteTagPlus.importado).label('algum_importado'),
                func.bool_or(NFPendenteTagPlus.origem.isnot(None)).label('pedido_preenchido')
            ).filter(
                NFPendenteTagPlus.resolvido == False
            ).group_by(
                NFPendenteTagPlus.numero_nf,
                NFPendenteTagPlus.cnpj_cliente,
                NFPendenteTagPlus.nome_cliente,
                NFPendenteTagPlus.nome_cidade,
                NFPendenteTagPlus.cod_uf,
                NFPendenteTagPlus.data_fatura
            ).order_by(
                NFPendenteTagPlus.data_fatura.desc()
            ).limit(limite).all()

            resultado = []
            for nf in nfs_agrupadas:
                # Buscar produtos desta NF
                produtos = NFPendenteTagPlus.query.filter_by(
                    numero_nf=nf.numero_nf
                ).all()

                status_logistico = self._avaliar_status_logistico(nf.numero_nf)

                resultado.append({
                    'numero_nf': nf.numero_nf,
                    'data_fatura': nf.data_fatura.strftime('%d/%m/%Y') if nf.data_fatura else '',
                    'cnpj_cliente': nf.cnpj_cliente,
                    'nome_cliente': nf.nome_cliente,
                    'nome_cidade': nf.nome_cidade,
                    'cod_uf': nf.cod_uf,
                    'valor_total': float(nf.valor_total or 0),
                    'qtd_total': float(nf.qtd_total or 0),
                    'qtd_produtos': nf.qtd_itens,
                    'origem': nf.origem_nf,
                    'importada': bool(nf.algum_importado),
                    'pedido_preenchido': bool(nf.pedido_preenchido),
                    'status_logistico': status_logistico,
                    'produtos': [
                        {
                            'cod_produto': p.cod_produto,
                            'nome_produto': p.nome_produto,
                            'quantidade': float(p.qtd_produto_faturado or 0),
                            'valor': float(p.valor_produto_faturado or 0)
                        } for p in produtos[:5]  # Limitar a 5 produtos para preview
                    ]
                })

            logger.info(f"📊 Encontradas {len(resultado)} NFs pendentes")
            return resultado

        except Exception as e:
            logger.error(f"❌ Erro ao listar NFs pendentes: {e}")
            return []

    def atualizar_pedido_nf(
        self,
        numero_nf: str,
        numero_pedido: str,
        importar: bool = True,
        usuario: str = 'Correção Manual'
    ) -> Dict[str, Any]:
        """
        Atualiza o número do pedido em uma NF pendente
        """
        try:
            logger.info(f"🔧 Atualizando NF {numero_nf} com pedido {numero_pedido}")

            # Atualizar todos os itens da NF
            itens_atualizados = NFPendenteTagPlus.query.filter_by(
                numero_nf=numero_nf
            ).update({
                'origem': numero_pedido,
                'pedido_preenchido_em': datetime.now(),
                'pedido_preenchido_por': usuario,
                'resolvido': False,
                'resolvido_em': None,
                'resolvido_por': None
            })

            if itens_atualizados == 0:
                return {
                    'success': False,
                    'erro': f'NF {numero_nf} não encontrada em pendências'
                }

            db.session.commit()
            logger.info(f"  ✅ {itens_atualizados} itens atualizados com pedido {numero_pedido}")

            # Sincronizar pedido nas estruturas relacionadas
            self._sincronizar_pedido_relacionados(numero_nf, numero_pedido, usuario)

            # Se solicitado, importar a NF
            resultado_importacao = None
            if importar:
                resultado_importacao = self.importar_nf_resolvida(numero_nf, usuario)
            else:
                # Atualizar status logístico mesmo sem importação
                status = self._atualizar_status_resolucao(numero_nf, usuario)
                resultado_importacao = {
                    'success': True,
                    'itens_criados': 0,
                    'itens_atualizados': 0,
                    'status_logistico': status
                }

            return {
                'success': True,
                'mensagem': f'NF {numero_nf} atualizada com pedido {numero_pedido}',
                'itens_atualizados': itens_atualizados,
                'importacao': resultado_importacao
            }

        except Exception as e:
            logger.error(f"❌ Erro ao atualizar pedido da NF {numero_nf}: {e}")
            db.session.rollback()
            return {
                'success': False,
                'erro': str(e)
            }

    def importar_nf_resolvida(self, numero_nf: str, usuario: str = 'Sistema') -> Dict[str, Any]:
        """
        Importa uma NF que teve o pedido preenchido
        """
        try:
            logger.info(f"📥 Importando NF resolvida {numero_nf}")

            # Buscar itens da NF pendente
            itens_pendentes = NFPendenteTagPlus.query.filter_by(
                numero_nf=numero_nf
            ).all()

            if not itens_pendentes:
                return {
                    'success': False,
                    'erro': 'NF não encontrada em pendências'
                }

            if any(not item.origem for item in itens_pendentes):
                return {
                    'success': False,
                    'erro': 'Existem itens sem pedido preenchido. Atualize o pedido antes de importar.'
                }

            dados_cliente = self._obter_dados_cliente(itens_pendentes[0].cnpj_cliente)
            numero_pedido_corrigido = itens_pendentes[0].origem

            itens_criados = 0
            itens_atualizados = 0
            erros = []

            agora = datetime.now()

            # Criar/atualizar FaturamentoProduto para cada item
            for item in itens_pendentes:
                try:
                    municipio = item.nome_cidade or dados_cliente.get('municipio')
                    estado = item.cod_uf or dados_cliente.get('estado')

                    existe = FaturamentoProduto.query.filter_by(
                        numero_nf=item.numero_nf,
                        cod_produto=item.cod_produto
                    ).first()

                    if not existe:
                        faturamento = FaturamentoProduto(
                            numero_nf=item.numero_nf,
                            data_fatura=item.data_fatura,
                            cnpj_cliente=item.cnpj_cliente,
                            nome_cliente=item.nome_cliente,
                            municipio=municipio,
                            estado=estado,
                            vendedor=dados_cliente.get('vendedor'),
                            equipe_vendas=dados_cliente.get('equipe_vendas'),
                            cod_produto=item.cod_produto,
                            nome_produto=item.nome_produto,
                            qtd_produto_faturado=item.qtd_produto_faturado,
                            preco_produto_faturado=item.preco_produto_faturado,
                            valor_produto_faturado=item.valor_produto_faturado,
                            origem=item.origem,
                            status_nf='Lançado',
                            created_by='ImportTagPlus-Corrigido',
                            updated_by=usuario
                        )
                        db.session.add(faturamento)
                        itens_criados += 1
                    else:
                        campos_atualizados = False
                        if not existe.municipio and municipio:
                            existe.municipio = municipio
                            campos_atualizados = True
                        if not existe.estado and estado:
                            existe.estado = estado
                            campos_atualizados = True
                        if not existe.vendedor and dados_cliente.get('vendedor'):
                            existe.vendedor = dados_cliente.get('vendedor')
                            campos_atualizados = True
                        if not existe.equipe_vendas and dados_cliente.get('equipe_vendas'):
                            existe.equipe_vendas = dados_cliente.get('equipe_vendas')
                            campos_atualizados = True
                        if not existe.origem and item.origem:
                            existe.origem = item.origem
                            campos_atualizados = True
                        if campos_atualizados:
                            itens_atualizados += 1

                    # Marcar como importado
                    item.importado = True
                    item.importado_em = agora
                    item.resolvido = False  # Será recalculado após processamento

                except Exception as e:
                    erros.append(f"Erro no item {item.cod_produto}: {str(e)}")

            # Criar/atualizar RelatorioFaturamentoImportado
            self._consolidar_relatorio_faturamento(numero_nf, itens_pendentes[0], dados_cliente)

            db.session.commit()

            # Sincronizar pedido em movimentações existentes
            if numero_pedido_corrigido:
                self._sincronizar_pedido_relacionados(numero_nf, numero_pedido_corrigido, usuario)

            # Processar faturamento
            from app.faturamento.services.processar_faturamento import ProcessadorFaturamento
            processador = ProcessadorFaturamento()
            resultado_processamento = processador.processar_nfs_importadas(
                usuario=usuario,
                limpar_inconsistencias=False,
                nfs_especificas=[numero_nf]
            )

            # Sincronizar entrega monitorada
            try:
                sincronizar_entrega_por_nf(numero_nf)
            except Exception as sync_err:
                logger.warning(f"⚠️ Falha ao sincronizar EntregaMonitorada da NF {numero_nf}: {sync_err}")

            status_logistico = self._atualizar_status_resolucao(numero_nf, usuario)

            return {
                'success': True,
                'itens_criados': itens_criados,
                'itens_atualizados': itens_atualizados,
                'processamento': resultado_processamento,
                'status_logistico': status_logistico,
                'erros': erros
            }

        except Exception as e:
            logger.error(f"❌ Erro ao importar NF {numero_nf}: {e}")
            db.session.rollback()
            return {
                'success': False,
                'erro': str(e)
            }

    def _consolidar_relatorio_faturamento(
        self,
        numero_nf: str,
        item_exemplo: NFPendenteTagPlus,
        dados_cliente: Dict[str, Any]
    ) -> None:
        """Cria/atualiza ``RelatorioFaturamentoImportado`` com dados completos."""
        try:
            relatorio = RelatorioFaturamentoImportado.query.filter_by(
                numero_nf=numero_nf
            ).first()

            totais = db.session.query(
                func.sum(NFPendenteTagPlus.valor_produto_faturado),
                func.sum(NFPendenteTagPlus.qtd_produto_faturado)
            ).filter_by(numero_nf=numero_nf).first()

            municipio = item_exemplo.nome_cidade or dados_cliente.get('municipio')
            estado = item_exemplo.cod_uf or dados_cliente.get('estado')
            vendedor = dados_cliente.get('vendedor')
            equipe_vendas = dados_cliente.get('equipe_vendas')

            if not relatorio:
                relatorio = RelatorioFaturamentoImportado(
                    numero_nf=numero_nf,
                    cnpj_cliente=item_exemplo.cnpj_cliente,
                    nome_cliente=item_exemplo.nome_cliente,
                    data_fatura=item_exemplo.data_fatura,
                    municipio=municipio,
                    estado=estado,
                    vendedor=vendedor,
                    equipe_vendas=equipe_vendas,
                    origem=item_exemplo.origem,
                    valor_total=float(totais[0] or 0), #type: ignore
                    peso_bruto=0,
                    ativo=True,
                    criado_em=datetime.now()
                )
                db.session.add(relatorio)
                logger.info(f"RelatorioFaturamentoImportado criado para NF {numero_nf}")
            else:
                relatorio.cnpj_cliente = item_exemplo.cnpj_cliente or relatorio.cnpj_cliente
                relatorio.nome_cliente = item_exemplo.nome_cliente or relatorio.nome_cliente
                relatorio.data_fatura = item_exemplo.data_fatura or relatorio.data_fatura
                relatorio.valor_total = float(totais[0] or 0) #type: ignore
                relatorio.peso_bruto = 0
                if municipio:
                    relatorio.municipio = municipio
                if estado:
                    relatorio.estado = estado
                if vendedor:
                    relatorio.vendedor = vendedor
                if equipe_vendas:
                    relatorio.equipe_vendas = equipe_vendas
                if item_exemplo.origem:
                    relatorio.origem = item_exemplo.origem
                logger.debug(f"RelatorioFaturamentoImportado atualizado para NF {numero_nf}")

            db.session.flush()

        except Exception as e:
            logger.error(f"Erro ao consolidar relatório: {e}")
            raise

    def _sincronizar_pedido_relacionados(self, numero_nf: str, numero_pedido: str, usuario: str) -> None:
        """Atualiza pedido corrigido em FaturamentoProduto, Relatorio e MovimentacaoEstoque."""
        try:
            if not numero_pedido:
                return

            agora = datetime.now()

            # Atualizar FaturamentoProduto
            FaturamentoProduto.query.filter_by(numero_nf=numero_nf).update({
                'origem': numero_pedido,
                'updated_by': usuario
            })

            # Atualizar RelatorioFaturamentoImportado
            RelatorioFaturamentoImportado.query.filter_by(numero_nf=numero_nf).update({
                'origem': numero_pedido
            })

            # Atualizar MovimentacaoEstoque existente
            MovimentacaoEstoque.query.filter_by(numero_nf=numero_nf).update({
                'num_pedido': numero_pedido,
                'atualizado_por': usuario,
                'atualizado_em': agora
            })

            db.session.commit()

        except Exception as e:
            logger.error(f"Erro ao sincronizar pedido em estruturas relacionadas: {e}")
            db.session.rollback()

    def _obter_dados_cliente(self, cnpj_cliente: str) -> Dict[str, Any]:
        cliente = CadastroCliente.query.filter_by(cnpj_cpf=cnpj_cliente).first()
        return {
            'municipio': cliente.municipio if cliente else None,
            'estado': cliente.estado if cliente else None,
            'vendedor': cliente.vendedor if cliente else None,
            'equipe_vendas': cliente.equipe_vendas if cliente else None
        }

    def _avaliar_status_logistico(self, numero_nf: str) -> Dict[str, bool]:
        tem_movimentacao = (
            db.session.query(MovimentacaoEstoque.id)
            .filter(
                MovimentacaoEstoque.numero_nf == numero_nf,
                MovimentacaoEstoque.status_nf == 'FATURADO'
            )
            .first()
            is not None
        )

        tem_movimentacao_com_lote = (
            db.session.query(MovimentacaoEstoque.id)
            .filter(
                MovimentacaoEstoque.numero_nf == numero_nf,
                MovimentacaoEstoque.status_nf == 'FATURADO',
                MovimentacaoEstoque.separacao_lote_id.isnot(None)
            )
            .first()
            is not None
        )

        tem_embarque = (
            db.session.query(EmbarqueItem.id)
            .filter(EmbarqueItem.nota_fiscal == numero_nf)
            .first()
            is not None
        )

        separacoes_sincronizadas = (
            db.session.query(Separacao.id)
            .filter(
                Separacao.numero_nf == numero_nf,
                Separacao.sincronizado_nf == True
            )
            .first()
            is not None
        )

        return {
            'tem_movimentacao': tem_movimentacao,
            'tem_movimentacao_com_lote': tem_movimentacao_com_lote,
            'tem_embarque': tem_embarque,
            'separacoes_sincronizadas': separacoes_sincronizadas,
            'resolvido': tem_movimentacao_com_lote and tem_embarque and separacoes_sincronizadas
        }

    def _atualizar_status_resolucao(self, numero_nf: str, usuario: str) -> Dict[str, bool]:
        status = self._avaliar_status_logistico(numero_nf)
        pendentes = NFPendenteTagPlus.query.filter_by(numero_nf=numero_nf).all()

        if not pendentes:
            return status

        alterou = False
        agora = datetime.now()

        if status['resolvido']:
            for item in pendentes:
                if not item.resolvido or not item.resolvido_em or not item.resolvido_por:
                    alterou = True
                item.resolvido = True
                item.resolvido_em = agora
                item.resolvido_por = usuario
        else:
            for item in pendentes:
                if item.resolvido or item.resolvido_em or item.resolvido_por:
                    alterou = True
                item.resolvido = False
                item.resolvido_em = None
                item.resolvido_por = None

        if alterou:
            db.session.commit()

        return status

    def sincronizar_status_nf(self, numero_nf: str, usuario: str = 'Sistema') -> Dict[str, bool]:
        """Permite atualizar o status de resolução para uma NF específica."""
        return self._atualizar_status_resolucao(numero_nf, usuario)

    def estatisticas_pendentes(self) -> Dict[str, Any]:
        """
        Retorna estatísticas das NFs pendentes
        """
        try:
            # Revalidar status logístico das NFs ainda abertas
            nfs_para_validar = [
                nf.numero_nf
                for nf in db.session.query(NFPendenteTagPlus.numero_nf).filter(
                    NFPendenteTagPlus.resolvido == False
                ).distinct()
            ]

            for nf_numero in nfs_para_validar:
                try:
                    self._atualizar_status_resolucao(nf_numero, 'Sistema Estatisticas')
                except Exception as e:
                    logger.warning(f"⚠️ Falha ao atualizar status da NF {nf_numero} nas estatísticas: {e}")

            total_pendentes = db.session.query(
                func.count(func.distinct(NFPendenteTagPlus.numero_nf))
            ).filter(
                NFPendenteTagPlus.resolvido == False
            ).scalar() or 0

            nfs_sem_pedido = db.session.query(
                func.count(func.distinct(NFPendenteTagPlus.numero_nf))
            ).filter(
                NFPendenteTagPlus.resolvido == False,
                NFPendenteTagPlus.origem.is_(None)
            ).scalar() or 0

            nfs_importadas = db.session.query(
                func.count(func.distinct(NFPendenteTagPlus.numero_nf))
            ).filter(
                NFPendenteTagPlus.resolvido == False,
                NFPendenteTagPlus.importado == True
            ).scalar() or 0

            valor_total = db.session.query(
                func.sum(NFPendenteTagPlus.valor_produto_faturado)
            ).filter(
                NFPendenteTagPlus.resolvido == False
            ).scalar() or 0

            return {
                'total_nfs_pendentes': total_pendentes,
                'total_nfs_sem_pedido': nfs_sem_pedido,
                'nfs_com_movimentacao': nfs_importadas,
                'nfs_sem_movimentacao': max(total_pendentes - nfs_importadas, 0),
                'valor_total': float(valor_total)
            }

        except Exception as e:
            logger.error(f"Erro ao calcular estatísticas: {e}")
            return {
                'total_nfs_pendentes': 0,
                'nfs_resolvidas_nao_importadas': 0,
                'nfs_aguardando_pedido': 0,
                'valor_total': 0
            }

    def atualizar_pedidos_em_lote(
        self,
        atualizacoes: List[Dict[str, str]],
        importar: bool = True,
        usuario: str = 'Sistema'
    ) -> Dict[str, Any]:
        """
        Atualiza múltiplos pedidos em lote

        Args:
            atualizacoes: Lista de dicts com 'numero_nf' e 'numero_pedido'
        """
        try:
            resultados = {
                'sucesso': [],
                'erros': []
            }

            for item in atualizacoes:
                numero_nf = item.get('numero_nf')
                numero_pedido = item.get('numero_pedido')

                if not numero_nf or not numero_pedido:
                    resultados['erros'].append(f"Dados inválidos: {item}")
                    continue

                resultado = self.atualizar_pedido_nf(
                    numero_nf=numero_nf,
                    numero_pedido=numero_pedido,
                    importar=importar,
                    usuario=usuario
                )

                if resultado['success']:
                    resultados['sucesso'].append(numero_nf)
                else:
                    resultados['erros'].append(f"{numero_nf}: {resultado.get('erro', 'Erro desconhecido')}")

            return {
                'success': True,
                'processados': len(resultados['sucesso']),
                'erros': len(resultados['erros']),
                'detalhes': resultados
            }

        except Exception as e:
            logger.error(f"Erro no processamento em lote: {e}")
            return {
                'success': False,
                'erro': str(e)
            }

    def buscar_pedido_sugerido(self, numero_nf: str) -> Optional[str]:
        """
        Tenta sugerir um número de pedido baseado em padrões conhecidos

        Args:
            numero_nf: Número da NF

        Returns:
            Número do pedido sugerido ou None
        """
        try:
            # Buscar itens pendentes da NF
            itens_pendentes = NFPendenteTagPlus.query.filter_by(
                numero_nf=numero_nf
            ).all()

            if not itens_pendentes:
                return None

            # Estratégia 1: Buscar na CarteiraPrincipal por produto e cliente
            from app.carteira.models import CarteiraPrincipal

            primeiro_item = itens_pendentes[0]

            # Buscar pedidos do mesmo cliente e produto
            pedidos_candidatos = CarteiraPrincipal.query.filter_by(
                cnpj_cpf=primeiro_item.cnpj_cliente,
                cod_produto=primeiro_item.cod_produto
            ).filter(
                CarteiraPrincipal.qtd_saldo_produto_pedido > 0
            ).order_by(
                CarteiraPrincipal.expedicao.desc()
            ).limit(5).all()

            # Verificar qual pedido tem quantidades mais próximas
            for pedido in pedidos_candidatos:
                # Comparar quantidades
                qtd_pedido = float(pedido.qtd_produto_pedido or 0)
                qtd_faturada = float(primeiro_item.qtd_produto_faturado or 0)

                # Se a quantidade faturada está dentro da quantidade do pedido
                if qtd_faturada <= qtd_pedido:
                    logger.info(f"  💡 Sugestão encontrada: Pedido {pedido.num_pedido}")
                    return pedido.num_pedido

            return None

        except Exception as e:
            logger.error(f"Erro ao buscar sugestão de pedido: {e}")
            return None
