"""
Serviço de Atualização de Separações após Sincronização Odoo
==============================================================

Implementa as regras corretas para atualização de separações TOTAIS e PARCIAIS
após alterações vindas do Odoo, incluindo geração de alertas para COTADAS.
"""

import logging
from decimal import Decimal
from app import db
from app.carteira.models import CarteiraPrincipal, PreSeparacaoItem
from app.carteira.models_alertas import AlertaSeparacaoCotada
from app.separacao.models import Separacao
from app.pedidos.models import Pedido
from sqlalchemy import and_

logger = logging.getLogger(__name__)


class SeparacaoUpdateService:
    """
    Serviço para atualizar separações conforme regras de negócio:
    - TOTAL: Espelho exato do pedido
    - PARCIAL: Segue hierarquia de impacto
    """
    
    @classmethod
    def detectar_tipo_separacao(cls, separacao_lote_id):
        """
        Detecta se uma separação é TOTAL ou PARCIAL baseado no CONTEÚDO
        
        TOTAL = Separação contém TODOS os itens e quantidades totais do pedido
        PARCIAL = Separação contém PARTE dos itens ou quantidades parciais
        """
        try:
            # Buscar todos os itens da separação
            itens_separacao = Separacao.query.filter_by(
                separacao_lote_id=separacao_lote_id
            ).all()
            
            if not itens_separacao:
                return None
            
            # Agrupar por pedido
            pedidos_na_separacao = {}
            for item in itens_separacao:
                if item.num_pedido not in pedidos_na_separacao:
                    pedidos_na_separacao[item.num_pedido] = []
                pedidos_na_separacao[item.num_pedido].append(item)
            
            # Verificar cada pedido
            for num_pedido, itens_sep_pedido in pedidos_na_separacao.items():
                # Buscar todos os itens do pedido na carteira
                itens_carteira = CarteiraPrincipal.query.filter_by(
                    num_pedido=num_pedido
                ).all()
                
                if not itens_carteira:
                    continue
                
                # Verificar se tem TODOS os produtos
                produtos_carteira = {item.cod_produto for item in itens_carteira}
                produtos_separacao = {item.cod_produto for item in itens_sep_pedido}
                
                # Se não tem todos os produtos, é PARCIAL
                if produtos_carteira != produtos_separacao:
                    logger.info(f"Separação {separacao_lote_id} é PARCIAL - faltam produtos")
                    return 'PARCIAL'
                
                # Verificar se as quantidades são totais
                for cod_produto in produtos_carteira:
                    # Somar quantidade total do produto na carteira
                    qtd_carteira = sum(
                        float(item.qtd_saldo_produto_pedido or 0) 
                        for item in itens_carteira 
                        if item.cod_produto == cod_produto
                    )
                    
                    # Somar quantidade na separação
                    qtd_separacao = sum(
                        float(item.qtd_saldo or 0) 
                        for item in itens_sep_pedido 
                        if item.cod_produto == cod_produto
                    )
                    
                    # Se quantidade na separação é menor, é PARCIAL
                    if qtd_separacao < qtd_carteira:
                        logger.info(f"Separação {separacao_lote_id} é PARCIAL - qtd parcial do produto {cod_produto}")
                        return 'PARCIAL'
            
            # Se chegou aqui, tem todos os produtos com quantidades totais
            logger.info(f"Separação {separacao_lote_id} é TOTAL")
            return 'TOTAL'
            
        except Exception as e:
            logger.error(f"Erro ao detectar tipo de separação: {e}")
            return None
    
    @classmethod
    def verificar_status_separacao(cls, separacao_lote_id):
        """
        Verifica o status da separação através do JOIN com Pedido
        """
        try:
            pedido = Pedido.query.filter_by(
                separacao_lote_id=separacao_lote_id
            ).first()
            
            if pedido:
                return pedido.status
            return None
            
        except Exception as e:
            logger.error(f"Erro ao verificar status: {e}")
            return None
    
    @classmethod
    def processar_alteracao_pedido(cls, num_pedido, cod_produto, alteracao_tipo, 
                                   qtd_anterior, qtd_nova, motivo="SYNC_ODOO"):
        """
        Processa alteração em um item do pedido conforme as regras de negócio
        
        Args:
            num_pedido: Número do pedido
            cod_produto: Código do produto
            alteracao_tipo: 'REDUCAO', 'AUMENTO', 'REMOCAO', 'ADICAO'
            qtd_anterior: Quantidade anterior
            qtd_nova: Quantidade nova
            motivo: Motivo da alteração
        """
        try:
            logger.info(f"Processando {alteracao_tipo} para {num_pedido}/{cod_produto}: {qtd_anterior} -> {qtd_nova}")
            
            # Buscar todas as separações do pedido/produto
            separacoes = Separacao.query.filter_by(
                num_pedido=num_pedido,
                cod_produto=cod_produto
            ).all()
            
            resultado = {
                'sucesso': True,
                'alertas_gerados': [],
                'separacoes_atualizadas': [],
                'operacoes': []
            }
            
            # Processar cada separação
            for separacao in separacoes:
                tipo_sep = cls.detectar_tipo_separacao(separacao.separacao_lote_id)
                status_sep = cls.verificar_status_separacao(separacao.separacao_lote_id)
                
                logger.info(f"Separação {separacao.separacao_lote_id}: tipo={tipo_sep}, status={status_sep}")
                
                if tipo_sep == 'TOTAL':
                    # SEPARAÇÃO TOTAL: Deve espelhar o pedido
                    resultado_total = cls._atualizar_separacao_total(
                        separacao, alteracao_tipo, qtd_anterior, qtd_nova, status_sep
                    )
                    resultado['separacoes_atualizadas'].append(resultado_total)
                    
                elif tipo_sep == 'PARCIAL':
                    # SEPARAÇÃO PARCIAL: Segue hierarquia
                    if alteracao_tipo in ['REDUCAO', 'REMOCAO']:
                        resultado_parcial = cls._processar_reducao_parcial(
                            num_pedido, cod_produto, qtd_anterior - qtd_nova, status_sep, separacao
                        )
                        resultado['separacoes_atualizadas'].append(resultado_parcial)
                    
                    elif alteracao_tipo == 'AUMENTO':
                        # Aumento em PARCIAL vai para saldo livre (não altera separação)
                        resultado['operacoes'].append(f"Aumento em PARCIAL - criado saldo livre")
                    
                    elif alteracao_tipo == 'ADICAO':
                        # Novo item em PARCIAL vai para saldo livre
                        resultado['operacoes'].append(f"Novo item em PARCIAL - criado saldo livre")
                
                # Gerar alerta se separação COTADA foi alterada
                if status_sep == 'COTADO' and alteracao_tipo in ['REDUCAO', 'AUMENTO', 'REMOCAO']:
                    alerta = AlertaSeparacaoCotada.criar_alerta(
                        separacao_lote_id=separacao.separacao_lote_id,
                        num_pedido=num_pedido,
                        cod_produto=cod_produto,
                        tipo_alteracao=alteracao_tipo,
                        qtd_anterior=qtd_anterior,
                        qtd_nova=qtd_nova,
                        tipo_separacao=tipo_sep
                    )
                    resultado['alertas_gerados'].append(alerta.id)
                    logger.warning(f"🚨 ALERTA CRIADO: Separação COTADA {separacao.separacao_lote_id} alterada!")
            
            db.session.commit()
            return resultado
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao processar alteração: {e}")
            return {'sucesso': False, 'erro': str(e)}
    
    @classmethod
    def _atualizar_separacao_total(cls, separacao, alteracao_tipo, qtd_anterior, qtd_nova, status):
        """
        Atualiza separação TOTAL para espelhar exatamente o pedido
        """
        try:
            operacoes = []
            
            if alteracao_tipo == 'REMOCAO':
                # Remover item da separação
                db.session.delete(separacao)
                operacoes.append(f"Item removido da separação TOTAL")
                
            elif alteracao_tipo == 'REDUCAO':
                # Reduzir quantidade
                separacao.qtd_saldo = Decimal(str(qtd_nova))
                operacoes.append(f"Quantidade reduzida de {qtd_anterior} para {qtd_nova}")
                
            elif alteracao_tipo == 'AUMENTO':
                # Aumentar quantidade
                separacao.qtd_saldo = Decimal(str(qtd_nova))
                operacoes.append(f"Quantidade aumentada de {qtd_anterior} para {qtd_nova}")
                
            elif alteracao_tipo == 'ADICAO':
                # Este caso seria para adicionar novo item (tratado em outro lugar)
                operacoes.append(f"Novo item adicionado à separação TOTAL")
            
            return {
                'separacao_lote_id': separacao.separacao_lote_id,
                'tipo': 'TOTAL',
                'status': status,
                'alteracao': alteracao_tipo,
                'operacoes': operacoes
            }
            
        except Exception as e:
            logger.error(f"Erro ao atualizar separação TOTAL: {e}")
            raise
    
    @classmethod
    def _processar_reducao_parcial(cls, num_pedido, cod_produto, qtd_reduzir, status, separacao):
        """
        Processa redução em separação PARCIAL seguindo hierarquia
        """
        try:
            qtd_restante = float(qtd_reduzir)
            operacoes = []
            
            # 1º - Consumir do saldo livre
            carteira_item = CarteiraPrincipal.query.filter(
                CarteiraPrincipal.num_pedido == num_pedido,
                CarteiraPrincipal.cod_produto == cod_produto,
                CarteiraPrincipal.separacao_lote_id.is_(None)
            ).first()
            
            if carteira_item and carteira_item.qtd_saldo_produto_pedido and qtd_restante > 0:
                qtd_consumida = min(float(carteira_item.qtd_saldo_produto_pedido), qtd_restante)
                carteira_item.qtd_saldo_produto_pedido = Decimal(
                    str(float(carteira_item.qtd_saldo_produto_pedido) - qtd_consumida)
                )
                qtd_restante -= qtd_consumida
                operacoes.append(f"Saldo livre reduzido em {qtd_consumida}")
            
            # 2º - Consumir de pré-separações
            if qtd_restante > 0:
                pre_separacoes = PreSeparacaoItem.query.filter(
                    PreSeparacaoItem.num_pedido == num_pedido,
                    PreSeparacaoItem.cod_produto == cod_produto,
                    PreSeparacaoItem.status.in_(['CRIADO', 'RECOMPOSTO'])
                ).order_by(PreSeparacaoItem.data_criacao.desc()).all()
                
                for pre_sep in pre_separacoes:
                    if qtd_restante <= 0:
                        break
                    
                    qtd_consumida = min(float(pre_sep.qtd_selecionada_usuario), qtd_restante)
                    pre_sep.qtd_selecionada_usuario = Decimal(
                        str(float(pre_sep.qtd_selecionada_usuario) - qtd_consumida)
                    )
                    qtd_restante -= qtd_consumida
                    operacoes.append(f"Pré-separação {pre_sep.id} reduzida em {qtd_consumida}")
                    
                    if pre_sep.qtd_selecionada_usuario <= 0:
                        db.session.delete(pre_sep)
                        operacoes.append(f"Pré-separação {pre_sep.id} removida")
            
            # 3º - Separação em ABERTO
            if qtd_restante > 0 and status == 'ABERTO':
                qtd_consumida = min(float(separacao.qtd_saldo or 0), qtd_restante)
                separacao.qtd_saldo = Decimal(str(float(separacao.qtd_saldo or 0) - qtd_consumida))
                qtd_restante -= qtd_consumida
                operacoes.append(f"Separação ABERTO reduzida em {qtd_consumida}")
            
            # 4º - Separação COTADA (último recurso)
            if qtd_restante > 0 and status == 'COTADO':
                qtd_consumida = min(float(separacao.qtd_saldo or 0), qtd_restante)
                separacao.qtd_saldo = Decimal(str(float(separacao.qtd_saldo or 0) - qtd_consumida))
                qtd_restante -= qtd_consumida
                operacoes.append(f"🚨 Separação COTADA reduzida em {qtd_consumida}")
            
            return {
                'separacao_lote_id': separacao.separacao_lote_id,
                'tipo': 'PARCIAL',
                'status': status,
                'qtd_reduzida': qtd_reduzir - qtd_restante,
                'qtd_nao_aplicada': qtd_restante,
                'operacoes': operacoes
            }
            
        except Exception as e:
            logger.error(f"Erro ao processar redução parcial: {e}")
            raise
    
    @classmethod
    def adicionar_item_separacao_total(cls, separacao_lote_id, num_pedido, cod_produto, dados_item):
        """
        Adiciona novo item em separação TOTAL para manter espelho do pedido
        """
        try:
            # Verificar se é realmente TOTAL
            tipo_sep = cls.detectar_tipo_separacao(separacao_lote_id)
            if tipo_sep != 'TOTAL':
                logger.warning(f"Tentativa de adicionar item em separação não-TOTAL: {separacao_lote_id}")
                return False
            
            # Criar novo item na separação
            nova_separacao = Separacao(
                separacao_lote_id=separacao_lote_id,
                num_pedido=num_pedido,
                cod_produto=cod_produto,
                qtd_saldo=dados_item.get('qtd_saldo', 0),
                valor_saldo=dados_item.get('valor_saldo', 0),
                peso=dados_item.get('peso', 0),
                pallet=dados_item.get('pallet', 0),
                # Copiar outros campos necessários
                cnpj_cpf=dados_item.get('cnpj_cpf'),
                raz_social_red=dados_item.get('raz_social_red'),
                nome_cidade=dados_item.get('nome_cidade'),
                cod_uf=dados_item.get('cod_uf'),
                nome_produto=dados_item.get('nome_produto'),
                data_pedido=dados_item.get('data_pedido'),
                expedicao=dados_item.get('expedicao'),
                agendamento=dados_item.get('agendamento'),
                protocolo=dados_item.get('protocolo'),
                observ_ped_1=dados_item.get('observ_ped_1')
            )
            
            db.session.add(nova_separacao)
            
            # Verificar status para gerar alerta se COTADO
            status = cls.verificar_status_separacao(separacao_lote_id)
            if status == 'COTADO':
                AlertaSeparacaoCotada.criar_alerta(
                    separacao_lote_id=separacao_lote_id,
                    num_pedido=num_pedido,
                    cod_produto=cod_produto,
                    tipo_alteracao='ADICAO',
                    qtd_anterior=0,
                    qtd_nova=float(dados_item.get('qtd_saldo', 0)),
                    tipo_separacao='TOTAL'
                )
                logger.warning(f"🚨 ALERTA: Item adicionado em separação TOTAL COTADA {separacao_lote_id}")
            
            db.session.commit()
            return True
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao adicionar item em separação TOTAL: {e}")
            return False