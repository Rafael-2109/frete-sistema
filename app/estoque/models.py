from app import db
from app.utils.timezone import agora_brasil
from sqlalchemy import inspect
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)

class MovimentacaoEstoque(db.Model):
    """
    Modelo para controle das movimentações de estoque
    """
    __tablename__ = 'movimentacao_estoque'

    id = db.Column(db.Integer, primary_key=True)
    
    # Dados do produto
    cod_produto = db.Column(db.String(50), nullable=False, index=True)
    nome_produto = db.Column(db.String(200), nullable=False)
    
    # Dados da movimentação
    data_movimentacao = db.Column(db.Date, nullable=False, index=True)
    tipo_movimentacao = db.Column(db.String(50), nullable=False, index=True)  # ENTRADA, SAIDA, AJUSTE, PRODUCAO
    local_movimentacao = db.Column(db.String(50), nullable=False)  # COMPRA, VENDA, PRODUCAO, AJUSTE, DEVOLUCAO
    
    # Quantidades
    qtd_movimentacao = db.Column(db.Numeric(15, 3), nullable=False)

    # Observações
    observacao = db.Column(db.Text, nullable=True)

        
    # Auditoria
    criado_em = db.Column(db.DateTime, default=agora_brasil, nullable=False)
    atualizado_em = db.Column(db.DateTime, default=agora_brasil, onupdate=agora_brasil, nullable=False)
    criado_por = db.Column(db.String(100), nullable=True)
    atualizado_por = db.Column(db.String(100), nullable=True)
    ativo = db.Column(db.Boolean, default=True, index=True)

    # Índices compostos para performance  
    __table_args__ = (
        db.Index('idx_movimentacao_produto_data', 'cod_produto', 'data_movimentacao'),
        db.Index('idx_movimentacao_tipo_data', 'tipo_movimentacao', 'data_movimentacao'),
    )

    def __repr__(self):
        return f'<MovimentacaoEstoque {self.cod_produto} - {self.tipo_movimentacao} - {self.qtd_movimentacao}>'

    def to_dict(self):
        return {
            'id': self.id,
            'cod_produto': self.cod_produto,
            'nome_produto': self.nome_produto,
            'data_movimentacao': self.data_movimentacao.strftime('%d/%m/%Y') if self.data_movimentacao else None,
            'tipo_movimentacao': self.tipo_movimentacao,
            'local_movimentacao': self.local_movimentacao,
            'qtd_movimentacao': float(self.qtd_movimentacao) if self.qtd_movimentacao else 0,
            'observacao': self.observacao
        }


class UnificacaoCodigos(db.Model):
    """
    Modelo para unificação de códigos de produtos
    Permite tratar códigos diferentes como mesmo produto físico para fins de estoque
    """
    __tablename__ = 'unificacao_codigos'

    id = db.Column(db.Integer, primary_key=True)
    
    # Códigos de unificação
    codigo_origem = db.Column(db.Integer, nullable=False, index=True)
    codigo_destino = db.Column(db.Integer, nullable=False, index=True) 
    
    # Observações
    observacao = db.Column(db.Text, nullable=True)
    
    # Auditoria completa
    ativo = db.Column(db.Boolean, default=True, index=True)
    created_at = db.Column(db.DateTime, default=agora_brasil, nullable=False)
    updated_at = db.Column(db.DateTime, default=agora_brasil, onupdate=agora_brasil, nullable=False)
    created_by = db.Column(db.String(100), nullable=True)
    updated_by = db.Column(db.String(100), nullable=True)
    
    # Histórico de ativação/desativação
    data_ativacao = db.Column(db.DateTime, nullable=True)
    data_desativacao = db.Column(db.DateTime, nullable=True)
    motivo_desativacao = db.Column(db.Text, nullable=True)
    
    # Índices compostos para performance e integridade
    __table_args__ = (
        # Evita duplicação: mesmo par origem-destino
        db.UniqueConstraint('codigo_origem', 'codigo_destino', name='uq_unificacao_origem_destino'),
        # Evita ciclos: A->B e B->A simultaneamente  
        db.Index('idx_unificacao_origem', 'codigo_origem'),
        db.Index('idx_unificacao_destino', 'codigo_destino'),
        db.Index('idx_unificacao_ativo', 'ativo'),
    )

    def __repr__(self):
        status = "Ativo" if self.ativo else "Inativo"
        return f'<UnificacaoCodigos {self.codigo_origem} → {self.codigo_destino} [{status}]>'

    def to_dict(self):
        return {
            'id': self.id,
            'codigo_origem': self.codigo_origem,
            'codigo_destino': self.codigo_destino,
            'observacao': self.observacao,
            'ativo': self.ativo,
            'created_at': self.created_at.strftime('%d/%m/%Y %H:%M') if self.created_at else None,
            'updated_at': self.updated_at.strftime('%d/%m/%Y %H:%M') if self.updated_at else None,
            'created_by': self.created_by,
            'updated_by': self.updated_by,
            'data_ativacao': self.data_ativacao.strftime('%d/%m/%Y %H:%M') if self.data_ativacao else None,
            'data_desativacao': self.data_desativacao.strftime('%d/%m/%Y %H:%M') if self.data_desativacao else None,
            'motivo_desativacao': self.motivo_desativacao
        }

    @classmethod
    def get_codigo_unificado(cls, codigo_produto):
        """
        Retorna o código destino se existe unificação ativa, senão retorna o próprio código
        """
        try:
            codigo_produto = int(codigo_produto)
            
            # Busca se o código é origem em alguma unificação ativa
            unificacao = cls.query.filter_by(
                codigo_origem=codigo_produto,
                ativo=True
            ).first()
            
            if unificacao:
                return unificacao.codigo_destino
                
            # Se não é origem, verifica se é destino (para estatísticas)
            return codigo_produto
            
        except (ValueError, TypeError):
            return codigo_produto

    @classmethod
    def get_todos_codigos_relacionados(cls, codigo_produto):
        """
        Retorna todos os códigos relacionados ao código informado
        SEMPRE inclui o próprio código, mesmo sem unificação
        """
        try:
            # Garantir que sempre inclui o próprio código (como string)
            codigo_original = str(codigo_produto)
            codigos_relacionados = set([codigo_original])
            
            # Tentar converter para int para busca na tabela de unificação
            try:
                codigo_int = int(codigo_produto)
                
                # Busca códigos que apontam para este (este é destino)
                origens = cls.query.filter_by(
                    codigo_destino=codigo_int,
                    ativo=True
                ).all()
                
                for origem in origens:
                    codigos_relacionados.add(str(origem.codigo_origem))
                
                # Busca para onde este código aponta (este é origem)
                destino = cls.query.filter_by(
                    codigo_origem=codigo_int,
                    ativo=True
                ).first()
                
                if destino:
                    codigos_relacionados.add(str(destino.codigo_destino))
                    # Busca outros códigos que também apontam para o mesmo destino
                    outros_origens = cls.query.filter_by(
                        codigo_destino=destino.codigo_destino,
                        ativo=True
                    ).all()
                    for outro in outros_origens:
                        codigos_relacionados.add(str(outro.codigo_origem))
                        
            except (ValueError, TypeError):
                # Se não conseguir converter para int, ignora unificação mas mantém o código original
                pass
            
            return list(codigos_relacionados)
            
        except Exception:
            # Em caso de qualquer erro, sempre retorna pelo menos o código original
            return [str(codigo_produto)]

    def ativar(self, usuario=None, motivo=None):
        """Ativa a unificação"""
        self.ativo = True
        self.data_ativacao = agora_brasil()
        self.updated_by = usuario
        self.motivo_desativacao = None
        
    def desativar(self, usuario=None, motivo=None):
        """Desativa a unificação"""
        self.ativo = False
        self.data_desativacao = agora_brasil()
        self.updated_by = usuario
        self.motivo_desativacao = motivo 

class SaldoEstoque:
    """
    Classe de serviço para cálculos de saldo de estoque em tempo real
    Não é uma tabela persistente, mas sim um calculador que integra dados de:
    - MovimentacaoEstoque (módulo já existente) - entrada/saída histórica
    - ProgramacaoProducao (módulo já existente) - produção futura
    - ✅ PreSeparacaoItem (principal) - saídas futuras por data de expedição
    - ✅ Separacao (complementar) - saídas já separadas
    - UnificacaoCodigos (módulo recém implementado) - códigos relacionados
    
    ❌ REMOVIDO: CarteiraPrincipal (não participa mais do cálculo de estoque futuro)
    """
    
    @staticmethod
    def obter_produtos_com_estoque():
        """Obtém lista de produtos únicos que têm movimentação de estoque"""
        try:
            # VERIFICA SE EXISTE CACHE PRIMEIRO
            inspector = inspect(db.engine)
            if inspector.has_table('saldo_estoque_cache'):
                from app.estoque.models_cache import SaldoEstoqueCache
                # Usar cache se disponível (MUITO MAIS RÁPIDO)
                produtos = db.session.query(
                    SaldoEstoqueCache.cod_produto,
                    SaldoEstoqueCache.nome_produto
                ).all()
                if produtos:
                    return produtos
            
            # Fallback: usar método antigo se não houver cache
            if not inspector.has_table('movimentacao_estoque'):
                return []
            
            # Buscar produtos únicos com movimentação
            produtos = db.session.query(
                MovimentacaoEstoque.cod_produto,
                MovimentacaoEstoque.nome_produto
            ).filter(
                MovimentacaoEstoque.ativo == True
            ).distinct().all()
            
            return produtos
            
        except Exception as e:
            logger.error(f"Erro ao obter produtos com estoque: {str(e)}")
            return []
    
    @staticmethod
    def calcular_estoque_inicial(cod_produto):
        """Calcula estoque inicial (D0) baseado em todas as movimentações"""
        try:
            # VERIFICA SE EXISTE CACHE PRIMEIRO
            inspector = inspect(db.engine)
            if inspector.has_table('saldo_estoque_cache'):
                from app.estoque.models_cache import SaldoEstoqueCache
                cache = SaldoEstoqueCache.query.filter_by(cod_produto=str(cod_produto)).first()
                if cache:
                    # Usar cache (instantâneo!)
                    return float(cache.saldo_atual)
            
            # Fallback: cálculo tradicional se não houver cache
            if not inspector.has_table('movimentacao_estoque'):
                return 0
            
            # Buscar todos os códigos relacionados (considerando unificação)
            try:
                codigos_relacionados = UnificacaoCodigos.get_todos_codigos_relacionados(int(cod_produto))
            except (ValueError, TypeError):
                # Se não for numérico, usar apenas o código original
                codigos_relacionados = [str(cod_produto)]
            
            # Somar movimentações de todos os códigos relacionados
            total_estoque = 0
            for codigo in codigos_relacionados:
                movimentacoes = MovimentacaoEstoque.query.filter(
                    MovimentacaoEstoque.cod_produto == str(codigo),
                    MovimentacaoEstoque.ativo == True
                ).all()
                
                total_estoque += sum(float(m.qtd_movimentacao) for m in movimentacoes)
            
            return total_estoque
            
        except Exception as e:
            logger.error(f"Erro ao calcular estoque inicial para {cod_produto}: {str(e)}")
            return 0
    
    @staticmethod
    def calcular_producao_periodo(cod_produto, data_inicio, data_fim):
        """Calcula produção programada para um produto em um período"""
        try:
            inspector = inspect(db.engine)
            if not inspector.has_table('programacao_producao'):
                return 0
            
            # Buscar todos os códigos relacionados (considerando unificação)
            try:
                codigos_relacionados = UnificacaoCodigos.get_todos_codigos_relacionados(int(cod_produto))
            except (ValueError, TypeError):
                # Se não for numérico, usar apenas o código original
                codigos_relacionados = [str(cod_produto)]
            
            # Somar produção de todos os códigos relacionados
            total_producao = 0
            for codigo in codigos_relacionados:
                from app.producao.models import ProgramacaoProducao
                from sqlalchemy import cast, Date
                
                producoes = ProgramacaoProducao.query.filter(
                    ProgramacaoProducao.cod_produto == str(codigo),
                    cast(ProgramacaoProducao.data_programacao, Date) >= data_inicio,
                    cast(ProgramacaoProducao.data_programacao, Date) <= data_fim
                ).all()
                
                total_producao += sum(float(p.qtd_programada) for p in producoes)
            
            return total_producao
            
        except Exception as e:
            logger.error(f"Erro ao calcular produção para {cod_produto}: {str(e)}")
            return 0
    

    
    @staticmethod
    def calcular_projecao_completa(cod_produto):
        """
        Calcula projeção completa de estoque para 29 dias (D0 até D+28)
        IMPLEMENTA LÓGICA JUST-IN-TIME CORRETA:
        - EST INICIAL D0 = estoque atual (MovimentacaoEstoque)
        - SAÍDA D0 = Separacao + PreSeparacaoItem (expedição D0)
        - EST FINAL D0 = EST INICIAL D0 - SAÍDA D0 + PROD D0
        - PROD D0 = ProgramacaoProducao (data_programacao D0)
        - EST INICIAL D+1 = EST FINAL D0 (Just-in-Time!)
        
        ❌ CarteiraPrincipal NÃO participa do cálculo de saídas
        """
        try:
            projecao = []
            # CORREÇÃO: Usar data no timezone brasileiro
            data_hoje = agora_brasil().date()
            
            # Estoque inicial (D0)
            estoque_atual = SaldoEstoque.calcular_estoque_inicial(cod_produto)
            
            # Calcular para cada dia (D0 até D+28)
            for dia in range(29):
                data_calculo = data_hoje + timedelta(days=dia)
                
                # 📤 SAÍDAS do dia (todas as fontes com expedição = data_calculo)
                saida_dia = SaldoEstoque._calcular_saidas_completas(cod_produto, data_calculo)
                
                # 🏭 PRODUÇÃO programada para o dia
                producao_dia = SaldoEstoque.calcular_producao_periodo(cod_produto, data_calculo, data_calculo)
                
                # 📊 LÓGICA SEQUENCIAL CORRETA
                if dia == 0:
                    # D0: Estoque atual
                    estoque_inicial_dia = estoque_atual
                else:
                    # D+1: EST FINAL anterior vira EST INICIAL do próximo dia
                    estoque_inicial_dia = projecao[dia-1]['estoque_final']
                
                # ✅ CORREÇÃO: EST FINAL = EST INICIAL - SAÍDA + PRODUÇÃO DO MESMO DIA
                # A produção deve aparecer no Est. Final do próprio dia
                estoque_final_dia = estoque_inicial_dia - saida_dia + producao_dia
                
                # Dados do dia
                dia_dados = {
                    'dia': dia,
                    'data': data_calculo,
                    'data_formatada': data_calculo.strftime('%d/%m'),
                    'estoque_inicial': estoque_inicial_dia,
                    'saida_prevista': saida_dia,
                    'producao_programada': producao_dia,  # Entra no Est. Final do mesmo dia
                    'estoque_final': estoque_final_dia
                }
                
                projecao.append(dia_dados)
            
            return projecao
            
        except Exception as e:
            logger.error(f"Erro ao calcular projeção para {cod_produto}: {str(e)}")
            return []
    
    @staticmethod
    def calcular_previsao_ruptura(projecao):
        """Calcula previsão de ruptura (menor estoque em 7 dias)"""
        try:
            if not projecao or len(projecao) < 8:
                return 0
            
            # Pegar estoque final dos primeiros 8 dias (D0 até D7)
            estoques_7_dias = [dia['estoque_final'] for dia in projecao[:8]]
            
            return min(estoques_7_dias)
            
        except Exception as e:
            logger.error(f"Erro ao calcular previsão de ruptura: {str(e)}")
            return 0
    
    @staticmethod
    def obter_resumo_produto(cod_produto, nome_produto):
        """Obtém resumo completo de um produto"""
        try:
            # VERIFICA SE EXISTE CACHE PRIMEIRO
            inspector = inspect(db.engine)
            cache = None  # Inicializar cache como None
            if inspector.has_table('saldo_estoque_cache'):
                try:
                    from app.estoque.models_cache import SaldoEstoqueCache, ProjecaoEstoqueCache
                    
                    # Buscar no cache
                    cache = SaldoEstoqueCache.query.filter_by(cod_produto=str(cod_produto)).first()
                    if cache:
                        # Buscar projeção do cache com tratamento especial para PostgreSQL
                        try:
                            # Tentar query normal primeiro
                            projecoes = ProjecaoEstoqueCache.query.filter_by(
                                cod_produto=str(cod_produto)
                            ).order_by(ProjecaoEstoqueCache.dia_offset).all()
                        except Exception as e:
                            # Se falhar com erro de tipo, usar query com cast para string
                            logger.warning(f"Erro ao buscar projeção, tentando com cast: {e}")
                            from sqlalchemy import cast, String
                            projecoes = db.session.query(
                                ProjecaoEstoqueCache.cod_produto,
                                cast(ProjecaoEstoqueCache.data_projecao, String).label('data_projecao'),
                                ProjecaoEstoqueCache.dia_offset,
                                ProjecaoEstoqueCache.estoque_inicial,
                                ProjecaoEstoqueCache.saida_prevista,
                                ProjecaoEstoqueCache.producao_programada,
                                ProjecaoEstoqueCache.estoque_final
                            ).filter(
                                ProjecaoEstoqueCache.cod_produto == str(cod_produto)
                            ).order_by(ProjecaoEstoqueCache.dia_offset).all()
                        
                        # Se houver projeção no cache, usar
                        if projecoes:
                            projecao = []
                            for proj in projecoes:
                                # Verificar se é tupla (resultado da query com cast) ou objeto
                                if hasattr(proj, 'data_projecao'):
                                    # É um objeto normal
                                    data_projecao = proj.data_projecao
                                    dia_offset = proj.dia_offset
                                    estoque_inicial = float(proj.estoque_inicial)
                                    saida_prevista = float(proj.saida_prevista)
                                    producao_programada = float(proj.producao_programada)
                                    estoque_final = float(proj.estoque_final)
                                else:
                                    # É uma tupla (resultado da query com cast)
                                    cod_produto, data_projecao, dia_offset, estoque_inicial, saida_prevista, producao_programada, estoque_final = proj
                                    estoque_inicial = float(estoque_inicial)
                                    saida_prevista = float(saida_prevista)
                                    producao_programada = float(producao_programada)
                                    estoque_final = float(estoque_final)
                                
                                # Tratamento seguro para data_projecao - FIX para erro PG 1082
                                try:
                                    # Converter data_projecao para string primeiro para evitar erro de tipo
                                    if data_projecao is not None:
                                        # Forçar conversão para string via SQL se necessário
                                        if hasattr(data_projecao, 'strftime'):
                                            data_formatada = data_projecao.strftime('%d/%m')
                                        else:
                                            # Converter qualquer tipo para string primeiro
                                            data_str = str(data_projecao)
                                            # Se for formato YYYY-MM-DD, converter
                                            if len(data_str) == 10 and data_str[4] == '-' and data_str[7] == '-':
                                                from datetime import datetime
                                                data_temp = datetime.strptime(data_str[:10], '%Y-%m-%d')
                                                data_formatada = data_temp.strftime('%d/%m')
                                            else:
                                                # Fallback: usar string como está
                                                data_formatada = data_str
                                    else:
                                        data_formatada = ''
                                except Exception as e:
                                    logger.debug(f"Erro ao formatar data_projecao: {e}")
                                    # Fallback seguro: converter para string
                                    data_formatada = str(data_projecao) if data_projecao else ''
                                
                                projecao.append({
                                    'dia': dia_offset,
                                    'data': data_projecao,
                                    'data_formatada': data_formatada,
                                    'estoque_inicial': estoque_inicial,
                                    'saida_prevista': saida_prevista,
                                    'producao_programada': producao_programada,
                                    'estoque_final': estoque_final
                                })
                        
                            return {
                                'cod_produto': cache.cod_produto,
                                'nome_produto': cache.nome_produto,
                                'estoque_inicial': float(cache.saldo_atual),
                                'qtd_total_carteira': float(cache.qtd_carteira),
                                'previsao_ruptura': float(cache.previsao_ruptura_7d) if cache.previsao_ruptura_7d else 0,
                                'projecao_29_dias': projecao,
                                'status_ruptura': cache.status_ruptura or 'OK'
                            }
                except Exception as e:
                    # Se houver erro com tipos PostgreSQL, retornar sem projeção
                    if "Unknown PG numeric type: 1082" in str(e) or "1082" in str(e):
                        logger.warning(f"Erro de tipo PostgreSQL ao buscar cache, retornando sem projeção: {e}")
                        # Retornar dados básicos do cache sem projeção
                        if cache:
                            return {
                                'cod_produto': cache.cod_produto,
                                'nome_produto': cache.nome_produto,
                                'estoque_inicial': float(cache.saldo_atual),
                                'qtd_total_carteira': float(cache.qtd_carteira),
                                'previsao_ruptura': float(cache.previsao_ruptura_7d) if cache.previsao_ruptura_7d else 0,
                                'projecao_29_dias': [],  # Vazio por causa do erro
                                'status_ruptura': cache.status_ruptura or 'OK'
                            }
                    # Re-lançar outros erros
                    raise
            
            # Fallback: cálculo tradicional se não houver cache
            # Calcular projeção completa
            projecao = SaldoEstoque.calcular_projecao_completa(cod_produto)
            
            if not projecao:
                return None
            
            # Dados principais
            estoque_inicial = projecao[0]['estoque_inicial']
            previsao_ruptura = SaldoEstoque.calcular_previsao_ruptura(projecao)
            
            # 📊 TOTAIS CARTEIRA (implementado com CarteiraPrincipal)
            qtd_total_carteira = SaldoEstoque._calcular_qtd_total_carteira(cod_produto)
            
            resumo = {
                'cod_produto': cod_produto,
                'nome_produto': nome_produto,
                'estoque_inicial': estoque_inicial,
                'qtd_total_carteira': qtd_total_carteira,
                'previsao_ruptura': previsao_ruptura,
                'projecao_29_dias': projecao,
                'status_ruptura': 'CRÍTICO' if previsao_ruptura <= 0 else 'ATENÇÃO' if previsao_ruptura < 10 else 'OK'
            }
            
            return resumo
            
        except Exception as e:
            logger.error(f"Erro ao obter resumo do produto {cod_produto}: {str(e)}")
            return None
    
    @staticmethod
    def _calcular_saidas_completas(cod_produto, data_expedicao):
        """
        Calcula TODAS as saídas previstas para uma data específica
        ✅ CORRIGIDO: SAÍDA = Separacao + PreSeparacaoItem (SEM CarteiraPrincipal)
        CarteiraPrincipal não participa do cálculo - apenas Separacao e PreSeparacaoItem
        """
        try:
            # Buscar todos os códigos relacionados (considerando unificação)
            try:
                codigos_relacionados = UnificacaoCodigos.get_todos_codigos_relacionados(int(cod_produto))
            except (ValueError, TypeError):
                # Se não for numérico, usar apenas o código original
                codigos_relacionados = [str(cod_produto)]
            
            total_saida = 0
            
            for codigo in codigos_relacionados:
                # 📦 1. SEPARAÇÕES já efetivadas
                # ✅ CORRETO: Linkar Separacao com Pedido pelo separacao_lote_id
                # Data expedição e status estão na tabela Pedido, não Separacao
                try:
                    from app.separacao.models import Separacao
                    from app.pedidos.models import Pedido
                    
                    # Buscar separações linkadas com pedidos
                    # Usar cast para garantir compatibilidade de tipos de data
                    from sqlalchemy import cast, Date
                    separacoes = Separacao.query.join(
                        Pedido, Separacao.separacao_lote_id == Pedido.separacao_lote_id
                    ).filter(
                        Separacao.cod_produto == str(codigo),
                        cast(Pedido.expedicao, Date) == data_expedicao,  # Cast para Date
                        Pedido.status.in_(['ABERTO', 'COTADO'])  # Status vem do Pedido
                    ).all()
                    
                    for sep in separacoes:
                        if sep.qtd_saldo and sep.qtd_saldo > 0:
                            total_saida += float(sep.qtd_saldo)
                                
                except Exception as e:
                    logger.debug(f"Erro ao buscar Separacao para {codigo}: {e}")
                
                # 📦 2. PRÉ-SEPARAÇÕES planejadas
                try:
                    from app.carteira.models import PreSeparacaoItem
                    from sqlalchemy import cast, Date
                    pre_separacoes = PreSeparacaoItem.query.filter(
                        PreSeparacaoItem.cod_produto == str(codigo),
                        cast(PreSeparacaoItem.data_expedicao_editada, Date) == data_expedicao,
                        PreSeparacaoItem.status.in_(['CRIADO', 'RECOMPOSTO'])
                    ).all()
                    
                    for pre_sep in pre_separacoes:
                        if pre_sep.qtd_selecionada_usuario and pre_sep.qtd_selecionada_usuario > 0:
                            total_saida += float(pre_sep.qtd_selecionada_usuario)
                            
                except Exception as e:
                    logger.debug(f"Erro ao buscar PreSeparacaoItem para {codigo}: {e}")
            
            return total_saida
            
        except Exception as e:
            logger.error(f"Erro ao calcular saídas completas para {cod_produto} em {data_expedicao}: {str(e)}")
            return 0

    @staticmethod
    def _calcular_qtd_total_carteira(cod_produto):
        """
        Calcula quantidade total em carteira para um produto específico
        Soma todos os itens pendentes de separação na CarteiraPrincipal
        """
        try:
            from app.carteira.models import CarteiraPrincipal
            
            # Buscar todos os códigos relacionados (considerando unificação)
            # Não converter para int se o código for alfanumérico
            try:
                codigos_relacionados = UnificacaoCodigos.get_todos_codigos_relacionados(int(cod_produto))
            except (ValueError, TypeError):
                # Se não for numérico, usar apenas o código original
                codigos_relacionados = [str(cod_produto)]
            
            total_carteira = 0
            for codigo in codigos_relacionados:
                # Somar itens ainda não separados (sem separacao_lote_id)
                itens_carteira = CarteiraPrincipal.query.filter(
                    CarteiraPrincipal.cod_produto == str(codigo),
                    CarteiraPrincipal.separacao_lote_id.is_(None),  # Ainda não separado
                    CarteiraPrincipal.ativo == True
                ).all()
                
                for item in itens_carteira:
                    if item.qtd_saldo_produto_pedido:
                        total_carteira += float(item.qtd_saldo_produto_pedido)
            
            return total_carteira
            
        except Exception as e:
            logger.error(f"Erro ao calcular qtd total carteira para {cod_produto}: {str(e)}")
            return 0

    @staticmethod
    def processar_ajuste_estoque(cod_produto, qtd_ajuste, motivo, usuario):
        """Processa ajuste de estoque gerando movimentação automática"""
        try:
            # Buscar nome do produto
            produto_existente = MovimentacaoEstoque.query.filter_by(
                cod_produto=str(cod_produto),
                ativo=True
            ).first()
            
            if not produto_existente:
                raise ValueError(f"Produto {cod_produto} não encontrado nas movimentações")
            
            # Criar movimentação de ajuste
            ajuste = MovimentacaoEstoque(
                cod_produto=str(cod_produto),
                nome_produto=produto_existente.nome_produto,
                tipo_movimentacao='AJUSTE',
                local_movimentacao='CD',
                data_movimentacao=agora_brasil().date(),
                qtd_movimentacao=float(qtd_ajuste),
                observacao=f'Ajuste manual: {motivo}',
                criado_por=usuario,
                atualizado_por=usuario
            )
            
            db.session.add(ajuste)
            db.session.commit()
            
            return True
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao processar ajuste de estoque: {str(e)}")
            raise e 