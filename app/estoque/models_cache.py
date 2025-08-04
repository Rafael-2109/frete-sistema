"""
Modelos de cache para otimização do saldo de estoque
Objetivo: Performance < 1 segundo para consultas
"""
from app import db
from app.utils.timezone import agora_brasil
import logging


logger = logging.getLogger(__name__)


class SaldoEstoqueCache(db.Model):
    """
    Tabela materializada de saldo de estoque
    Atualizada incrementalmente a cada movimentação
    """
    __tablename__ = 'saldo_estoque_cache'
    
    id = db.Column(db.Integer, primary_key=True)
    cod_produto = db.Column(db.String(50), nullable=False, unique=True, index=True)
    nome_produto = db.Column(db.String(200), nullable=False)
    
    # Saldo atual (soma de todas as movimentações)
    saldo_atual = db.Column(db.Numeric(15, 3), nullable=False, default=0)
    
    # Quantidades em carteira/separação (para cálculo rápido)
    qtd_carteira = db.Column(db.Numeric(15, 3), nullable=False, default=0)
    qtd_pre_separacao = db.Column(db.Numeric(15, 3), nullable=False, default=0)
    qtd_separacao = db.Column(db.Numeric(15, 3), nullable=False, default=0)
    
    # Estatísticas pré-calculadas
    previsao_ruptura_7d = db.Column(db.Numeric(15, 3), nullable=True)
    status_ruptura = db.Column(db.String(20), nullable=True, index=True)
    
    # Controle de atualização
    ultima_atualizacao_saldo = db.Column(db.DateTime, nullable=True)
    ultima_atualizacao_carteira = db.Column(db.DateTime, nullable=True)
    ultima_atualizacao_projecao = db.Column(db.DateTime, nullable=True)
    
    # Auditoria
    criado_em = db.Column(db.DateTime, default=agora_brasil, nullable=False)
    atualizado_em = db.Column(db.DateTime, default=agora_brasil, onupdate=agora_brasil, nullable=False)
    
    def __repr__(self):
        return f'<SaldoEstoqueCache {self.cod_produto} - Saldo: {self.saldo_atual}>'
    
    @property
    def saldo_disponivel(self):
        """Retorna o saldo disponível (descontando carteira, pré-separação e separação)"""
        return float(self.saldo_atual or 0) - float(self.qtd_carteira or 0) - float(self.qtd_pre_separacao or 0) - float(self.qtd_separacao or 0)
    
    @classmethod
    def atualizar_saldo_incremental(cls, cod_produto, nome_produto, delta_quantidade):
        """
        Atualiza saldo de forma incremental (chamado ao inserir MovimentacaoEstoque)
        delta_quantidade: positivo para entrada, negativo para saída
        """
        try:
            cache = cls.query.filter_by(cod_produto=str(cod_produto)).first()
            
            if not cache:
                # Criar novo registro de cache
                cache = cls(
                    cod_produto=str(cod_produto),
                    nome_produto=nome_produto,
                    saldo_atual=delta_quantidade,
                    ultima_atualizacao_saldo=agora_brasil()
                )
                db.session.add(cache)
            else:
                # Atualizar saldo existente
                cache.saldo_atual += delta_quantidade
                cache.ultima_atualizacao_saldo = agora_brasil()
                
                # Recalcular status de ruptura
                if cache.saldo_atual <= 0:
                    cache.status_ruptura = 'CRÍTICO'
                elif cache.saldo_atual < 10:
                    cache.status_ruptura = 'ATENÇÃO'
                else:
                    cache.status_ruptura = 'OK'
            
            db.session.commit()
            logger.info(f"✅ Saldo cache atualizado para {cod_produto}: {cache.saldo_atual}")
            return True
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"❌ Erro ao atualizar saldo cache: {str(e)}")
            return False
    
    @classmethod
    def atualizar_carteira(cls, cod_produto):
        """
        Atualiza quantidades de carteira/separação (chamado ao modificar carteira)
        """
        try:
            from app.carteira.models import CarteiraPrincipal, PreSeparacaoItem
            from app.separacao.models import Separacao
            from app.pedidos.models import Pedido
            from app.estoque.models import UnificacaoCodigos
            
            # Obter códigos relacionados
            try:
                codigos_relacionados = UnificacaoCodigos.get_todos_codigos_relacionados(int(cod_produto))
            except (ValueError, TypeError):
                codigos_relacionados = [str(cod_produto)]
            
            cache = cls.query.filter_by(cod_produto=str(cod_produto)).first()
            if not cache:
                return False
            
            # Calcular qtd_carteira
            qtd_carteira = 0
            for codigo in codigos_relacionados:
                itens = CarteiraPrincipal.query.filter(
                    CarteiraPrincipal.cod_produto == str(codigo),
                    CarteiraPrincipal.separacao_lote_id.is_(None),
                    CarteiraPrincipal.ativo == True
                ).all()
                for item in itens:
                    if item.qtd_saldo_produto_pedido:
                        qtd_carteira += float(item.qtd_saldo_produto_pedido)
            
            # Calcular qtd_pre_separacao
            qtd_pre_separacao = 0
            for codigo in codigos_relacionados:
                pre_seps = PreSeparacaoItem.query.filter(
                    PreSeparacaoItem.cod_produto == str(codigo),
                    PreSeparacaoItem.status.in_(['CRIADO', 'RECOMPOSTO'])
                ).all()
                for pre_sep in pre_seps:
                    if pre_sep.qtd_selecionada_usuario:
                        qtd_pre_separacao += float(pre_sep.qtd_selecionada_usuario)
            
            # Calcular qtd_separacao
            qtd_separacao = 0
            for codigo in codigos_relacionados:
                separacoes = Separacao.query.join(
                    Pedido, Separacao.separacao_lote_id == Pedido.separacao_lote_id
                ).filter(
                    Separacao.cod_produto == str(codigo),
                    Pedido.status.in_(['ABERTO', 'COTADO'])
                ).all()
                for sep in separacoes:
                    if sep.qtd_saldo and sep.qtd_saldo > 0:
                        qtd_separacao += float(sep.qtd_saldo)
            
            # Atualizar cache
            cache.qtd_carteira = qtd_carteira
            cache.qtd_pre_separacao = qtd_pre_separacao
            cache.qtd_separacao = qtd_separacao
            cache.ultima_atualizacao_carteira = agora_brasil()
            
            db.session.commit()
            return True
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"❌ Erro ao atualizar carteira cache: {str(e)}")
            return False
    
    @classmethod
    def inicializar_cache_completo(cls):
        """
        Inicializa o cache com todos os produtos existentes
        Executar apenas uma vez ou para reconstruir o cache
        CONSIDERA CÓDIGOS UNIFICADOS!
        """
        try:
            from app.estoque.models import MovimentacaoEstoque, UnificacaoCodigos
            
            logger.info("🔄 Iniciando reconstrução do cache de saldo...")
            
            # Usar no_autoflush para evitar flush prematuro
            with db.session.no_autoflush:
                # Limpar cache existente
                cls.query.delete()
                db.session.commit()
                
                # Obter todos os produtos únicos
                produtos = db.session.query(
                    MovimentacaoEstoque.cod_produto,
                    MovimentacaoEstoque.nome_produto
                ).filter(
                    MovimentacaoEstoque.ativo == True
                ).distinct().all()
                
                total = len(produtos)
                processados = 0
                produtos_unificados = {}  # Mapear códigos unificados
                
                # Primeiro, mapear todos os códigos unificados
                logger.info("📦 Mapeando códigos unificados...")
                for produto in produtos:
                    try:
                        # Buscar todos os códigos relacionados (incluindo o próprio)
                        codigos_relacionados = UnificacaoCodigos.get_todos_codigos_relacionados(produto.cod_produto)
                        
                        # Usar o menor código como principal (ou o próprio se não houver relacionados)
                        if codigos_relacionados and len(codigos_relacionados) > 1:
                            # Converter para int para ordenar e pegar o menor
                            codigos_int = []
                            for cod in codigos_relacionados:
                                try:
                                    codigos_int.append(int(cod))
                                except (ValueError, TypeError):
                                    pass
                            
                            if codigos_int:
                                codigo_principal = str(min(codigos_int))
                            else:
                                codigo_principal = produto.cod_produto
                        else:
                            codigo_principal = produto.cod_produto
                        
                        # Adicionar ao mapeamento
                        if codigo_principal not in produtos_unificados:
                            produtos_unificados[codigo_principal] = {
                                'codigos': set(),
                                'nome': produto.nome_produto
                            }
                        
                        # Adicionar todos os códigos relacionados
                        produtos_unificados[codigo_principal]['codigos'].update(codigos_relacionados)
                        
                    except Exception as e:
                        # Em caso de erro, tratar como individual
                        logger.debug(f"Erro ao processar unificação para {produto.cod_produto}: {e}")
                        produtos_unificados[produto.cod_produto] = {
                            'codigos': {produto.cod_produto},
                            'nome': produto.nome_produto
                        }
                
                logger.info(f"📊 {len(produtos_unificados)} grupos de produtos após unificação")
                
                # Agora processar por código principal
                for codigo_principal, info in produtos_unificados.items():
                    # Calcular saldo total considerando todos os códigos relacionados
                    saldo_total = 0
                    for codigo in info['codigos']:
                        movimentacoes = MovimentacaoEstoque.query.filter_by(
                            cod_produto=codigo,
                            ativo=True
                        ).all()
                        saldo_total += sum(float(m.qtd_movimentacao) for m in movimentacoes)
                    
                    # Verificar se já existe no cache (por segurança)
                    cache_existente = cls.query.filter_by(cod_produto=codigo_principal).first()
                    
                    if cache_existente:
                        # Atualizar existente
                        cache_existente.nome_produto = info['nome']
                        cache_existente.saldo_atual = saldo_total
                        cache_existente.status_ruptura = 'CRÍTICO' if saldo_total <= 0 else 'ATENÇÃO' if saldo_total < 10 else 'OK'
                        cache_existente.ultima_atualizacao_saldo = agora_brasil()
                        cache_existente.atualizado_em = agora_brasil()
                    else:
                        # Criar novo registro
                        cache = cls(
                            cod_produto=codigo_principal,
                            nome_produto=info['nome'],
                            saldo_atual=saldo_total,
                            status_ruptura='CRÍTICO' if saldo_total <= 0 else 'ATENÇÃO' if saldo_total < 10 else 'OK',
                            ultima_atualizacao_saldo=agora_brasil()
                        )
                        db.session.add(cache)
                    
                    processados += 1
                    if processados % 100 == 0:
                        db.session.commit()
                        logger.info(f"  Processados {processados}/{total} produtos...")
                
                db.session.commit()
            
            # Atualizar quantidades de carteira para todos
            logger.info("🔄 Atualizando quantidades de carteira...")
            produtos_para_atualizar = cls.query.all()
            for i, cache_produto in enumerate(produtos_para_atualizar, 1):
                cls.atualizar_carteira(cache_produto.cod_produto)
                if i % 100 == 0:
                    logger.info(f"  Atualizadas carteiras de {i}/{len(produtos_para_atualizar)} produtos...")
            
            logger.info(f"✅ Cache inicializado com {processados} produtos")
            return True
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"❌ Erro ao inicializar cache: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return False


class ProjecaoEstoqueCache(db.Model):
    """
    Tabela de projeção de estoque pré-calculada (29 dias)
    """
    __tablename__ = 'projecao_estoque_cache'
    
    id = db.Column(db.Integer, primary_key=True)
    cod_produto = db.Column(db.String(50), nullable=False, index=True)
    data_projecao = db.Column(db.Date, nullable=False, index=True)
    dia_offset = db.Column(db.Integer, nullable=False)  # 0 = D0, 1 = D+1, etc
    
    # Valores da projeção
    estoque_inicial = db.Column(db.Numeric(15, 3), nullable=False, default=0)
    saida_prevista = db.Column(db.Numeric(15, 3), nullable=False, default=0)
    producao_programada = db.Column(db.Numeric(15, 3), nullable=False, default=0)
    estoque_final = db.Column(db.Numeric(15, 3), nullable=False, default=0)
    
    # Controle
    atualizado_em = db.Column(db.DateTime, default=agora_brasil, onupdate=agora_brasil, nullable=False)
    
    # Índice único composto
    __table_args__ = (
        db.UniqueConstraint('cod_produto', 'data_projecao', name='uq_projecao_produto_data'),
    )
    
    @classmethod
    def atualizar_projecao(cls, cod_produto):
        """
        Atualiza projeção de 29 dias para um produto
        """
        from datetime import timedelta
        from app.producao.models import ProgramacaoProducao
        from app.carteira.models import PreSeparacaoItem
        from app.separacao.models import Separacao
        from app.pedidos.models import Pedido
        
        try:
            # Obter saldo atual do cache
            saldo_cache = SaldoEstoqueCache.query.filter_by(cod_produto=str(cod_produto)).first()
            if not saldo_cache:
                return False
            
            # Limpar projeção antiga
            cls.query.filter_by(cod_produto=str(cod_produto)).delete()
            
            data_hoje = agora_brasil().date()
            estoque_atual = float(saldo_cache.saldo_atual)
            
            # Calcular para cada dia
            for dia in range(29):
                data_calculo = data_hoje + timedelta(days=dia)
                
                # Calcular saídas do dia (pré-separações + separações)
                saida_dia = 0
                
                # Pré-separações
                pre_seps = PreSeparacaoItem.query.filter(
                    PreSeparacaoItem.cod_produto == str(cod_produto),
                    PreSeparacaoItem.data_expedicao_editada == data_calculo,
                    PreSeparacaoItem.status.in_(['CRIADO', 'RECOMPOSTO'])
                ).all()
                for ps in pre_seps:
                    if ps.qtd_selecionada_usuario:
                        saida_dia += float(ps.qtd_selecionada_usuario)
                
                # Separações
                seps = Separacao.query.join(
                    Pedido, Separacao.separacao_lote_id == Pedido.separacao_lote_id
                ).filter(
                    Separacao.cod_produto == str(cod_produto),
                    Pedido.expedicao == data_calculo,
                    Pedido.status.in_(['ABERTO', 'COTADO'])
                ).all()
                for s in seps:
                    if s.qtd_saldo:
                        saida_dia += float(s.qtd_saldo)
                
                # Calcular produção do dia
                producao_dia = 0
                prods = ProgramacaoProducao.query.filter(
                    ProgramacaoProducao.cod_produto == str(cod_produto),
                    ProgramacaoProducao.data_programacao == data_calculo
                ).all()
                for p in prods:
                    if p.qtd_programada:
                        producao_dia += float(p.qtd_programada)
                
                # Calcular estoques
                if dia == 0:
                    estoque_inicial_dia = estoque_atual
                    estoque_final_dia = estoque_inicial_dia - saida_dia + producao_dia
                    estoque_final_anterior = estoque_final_dia
                else:
                    # Estoque inicial = estoque final do dia anterior
                    estoque_inicial_dia = estoque_final_anterior
                    estoque_final_dia = estoque_inicial_dia - saida_dia + producao_dia
                    estoque_final_anterior = estoque_final_dia
                
                # Salvar projeção
                projecao = cls(
                    cod_produto=str(cod_produto),
                    data_projecao=data_calculo,
                    dia_offset=dia,
                    estoque_inicial=estoque_inicial_dia,
                    saida_prevista=saida_dia,
                    producao_programada=producao_dia,
                    estoque_final=estoque_final_dia
                )
                db.session.add(projecao)
            
            # Calcular previsão de ruptura (menor estoque em 7 dias)
            projecoes_7d = cls.query.filter(
                cls.cod_produto == str(cod_produto),
                cls.dia_offset <= 7
            ).all()
            
            if projecoes_7d:
                menor_estoque = min(float(p.estoque_final) for p in projecoes_7d)
                saldo_cache.previsao_ruptura_7d = menor_estoque
                saldo_cache.ultima_atualizacao_projecao = agora_brasil()
            
            db.session.commit()
            return True
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"❌ Erro ao atualizar projeção: {str(e)}")
            return False


class CacheUpdateLog(db.Model):
    """
    Log de atualizações pendentes no cache
    """
    __tablename__ = 'cache_update_log'
    
    id = db.Column(db.Integer, primary_key=True)
    tabela_origem = db.Column(db.String(50), nullable=False)
    operacao = db.Column(db.String(20), nullable=False)  # INSERT, UPDATE, DELETE
    cod_produto = db.Column(db.String(50), nullable=True, index=True)
    processado = db.Column(db.Boolean, default=False, index=True)
    criado_em = db.Column(db.DateTime, default=agora_brasil, nullable=False)
    processado_em = db.Column(db.DateTime, nullable=True)
    
    @classmethod
    def registrar_mudanca(cls, tabela, operacao, cod_produto=None):
        """Registra uma mudança que precisa ser processada no cache"""
        try:
            log = cls(
                tabela_origem=tabela,
                operacao=operacao,
                cod_produto=str(cod_produto) if cod_produto else None
            )
            db.session.add(log)
            db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao registrar mudança: {str(e)}")
            return False

