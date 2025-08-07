"""
Serviço Principal do Sistema de Estoque em Tempo Real
Centraliza toda lógica de negócio e cálculos
"""

from datetime import date, timedelta
from decimal import Decimal
from typing import Optional, Dict, Any
import logging
from app import db
from app.utils.timezone import agora_brasil
from app.estoque.models import MovimentacaoEstoque, UnificacaoCodigos
from app.estoque.models_tempo_real import EstoqueTempoReal, MovimentacaoPrevista

logger = logging.getLogger(__name__)


class ServicoEstoqueTempoReal:
    """
    Serviço responsável por manter EstoqueTempoReal e MovimentacaoPrevista
    sempre atualizados e calcular projeções.
    """
    
    @staticmethod
    def processar_movimentacao_estoque(
        movimentacao: MovimentacaoEstoque, 
        operacao: str = 'insert', 
        qtd_anterior: Optional[Decimal] = None
    ) -> None:
        """
        Chamado por trigger quando MovimentacaoEstoque muda.
        
        Args:
            movimentacao: Objeto MovimentacaoEstoque
            operacao: 'insert', 'update' ou 'delete'
            qtd_anterior: Quantidade anterior (para update)
        """
        # Obter códigos unificados
        codigos = UnificacaoCodigos.get_todos_codigos_relacionados(
            movimentacao.cod_produto
        )
        
        for codigo in codigos:
            # Buscar ou criar registro de estoque
            estoque = EstoqueTempoReal.query.filter_by(
                cod_produto=codigo
            ).first()
            
            if not estoque:
                estoque = EstoqueTempoReal(
                    cod_produto=codigo,
                    nome_produto=movimentacao.nome_produto or f"Produto {codigo}"
                )
            
            # Calcular delta baseado na operação
            # IMPORTANTE: qtd_movimentacao já vem com sinal correto (negativo para saídas)
            if operacao == 'insert':
                # Nova movimentação - usar valor direto
                delta = movimentacao.qtd_movimentacao
                
            elif operacao == 'update':
                # Atualização: calcular diferença entre novo e anterior
                delta_novo = movimentacao.qtd_movimentacao
                delta_anterior = qtd_anterior if qtd_anterior else 0
                delta = delta_novo - delta_anterior
                
            else:  # delete
                # Reverter movimentação - inverter o sinal
                delta = -movimentacao.qtd_movimentacao
            
            # Atualizar saldo
            estoque.saldo_atual = Decimal(str(estoque.saldo_atual)) + Decimal(str(delta))
            estoque.atualizado_em = agora_brasil()
            
            # Usar merge ao invés de add para evitar warning durante flush
            db.session.merge(estoque)
            
            # Commit parcial para garantir consistência
            try:
                db.session.flush()
            except Exception as e:
                db.session.rollback()
                raise e
    
    @staticmethod
    def atualizar_movimentacao_prevista(
        cod_produto: str, 
        data: date,
        qtd_entrada: Decimal = Decimal('0'),
        qtd_saida: Decimal = Decimal('0')
    ) -> None:
        """
        Atualiza ou cria registro em MovimentacaoPrevista.
        Sempre SOMA às quantidades existentes (cumulativo).
        
        Args:
            cod_produto: Código do produto
            data: Data prevista
            qtd_entrada: Quantidade de entrada a adicionar
            qtd_saida: Quantidade de saída a adicionar
        """
        # Considerar unificação
        codigos = UnificacaoCodigos.get_todos_codigos_relacionados(cod_produto)
        
        for codigo in codigos:
            # Buscar registro existente
            mov = MovimentacaoPrevista.query.filter_by(
                cod_produto=codigo,
                data_prevista=data
            ).first()
            
            if not mov:
                # Criar novo registro
                mov = MovimentacaoPrevista(
                    cod_produto=codigo,
                    data_prevista=data,
                    entrada_prevista=Decimal('0'),
                    saida_prevista=Decimal('0')
                )
            
            # Atualizar quantidades (sempre soma)
            mov.entrada_prevista = Decimal(str(mov.entrada_prevista)) + Decimal(str(qtd_entrada))
            mov.saida_prevista = Decimal(str(mov.saida_prevista)) + Decimal(str(qtd_saida))
            
            # Se zerou, deletar registro para economizar espaço
            if mov.entrada_prevista <= 0 and mov.saida_prevista <= 0:
                db.session.delete(mov)
            else:
                # Garantir que não fique negativo
                mov.entrada_prevista = max(Decimal('0'), mov.entrada_prevista)
                mov.saida_prevista = max(Decimal('0'), mov.saida_prevista)
                db.session.add(mov)
            
            # Não fazer flush aqui - deixar para o processo pai
            # Isso evita o erro "Session is already flushing"
            # O flush será feito quando o trigger ou script principal fizer commit
        
        # Não recalcular ruptura aqui para evitar loops
        # A ruptura será recalculada:
        # 1. Sob demanda quando get_projecao_completa é chamado
        # 2. Pelo job scheduled que roda a cada 60 segundos
    
    @staticmethod
    def calcular_ruptura_d7(cod_produto: str) -> None:
        """
        Calcula menor estoque dos próximos 7 dias.
        Chamado após QUALQUER alteração em MovimentacaoPrevista ou EstoqueTempoReal.
        
        Args:
            cod_produto: Código do produto para calcular
        """
        # Considerar unificação
        codigos = UnificacaoCodigos.get_todos_codigos_relacionados(cod_produto)
        
        for codigo in codigos:
            # Buscar estoque atual
            estoque = EstoqueTempoReal.query.filter_by(
                cod_produto=codigo
            ).first()
            
            if not estoque:
                continue
            
            saldo = float(estoque.saldo_atual)
            menor_saldo = saldo  # Inicializa com saldo atual
            dia_ruptura = None
            hoje = date.today()
            
            # Buscar movimentações dos próximos 7 dias
            movimentacoes = MovimentacaoPrevista.query.filter(
                MovimentacaoPrevista.cod_produto == codigo,
                MovimentacaoPrevista.data_prevista >= hoje,
                MovimentacaoPrevista.data_prevista <= hoje + timedelta(days=7)
            ).order_by(MovimentacaoPrevista.data_prevista).all()
            
            # Simular saldo dia a dia
            for i in range(8):  # D0 até D7 (8 dias)
                data_atual = hoje + timedelta(days=i)
                
                # Buscar movimentação do dia
                mov_dia = next((m for m in movimentacoes if m.data_prevista == data_atual), None)
                
                if mov_dia:
                    saldo = saldo + float(mov_dia.entrada_prevista) - float(mov_dia.saida_prevista)
                
                # Atualizar menor saldo considerando todos os dias
                if saldo < menor_saldo:
                    menor_saldo = saldo
                
                # Marcar primeiro dia de ruptura
                if saldo < 0 and not dia_ruptura:
                    dia_ruptura = data_atual
            
            # Atualizar projeção
            estoque.menor_estoque_d7 = Decimal(str(menor_saldo))
            estoque.dia_ruptura = dia_ruptura
            
            # Adicionar ao session (sem flush para evitar recursão)
            db.session.add(estoque)
            # O flush será feito pelo processo pai ou quando necessário
    
    @staticmethod
    def processar_fallback() -> Dict[str, Any]:
        """
        Job que roda a cada 60 segundos.
        Pega 10 produtos com atualizado_em mais antigo e recalcula do zero.
        
        Returns:
            Dict com estatísticas do processamento
        """
        # Buscar 10 produtos mais antigos
        produtos = EstoqueTempoReal.query.order_by(
            EstoqueTempoReal.atualizado_em.asc()
        ).limit(10).all()
        
        processados = 0
        erros = []
        
        for produto in produtos:
            try:
                # Recalcular saldo do zero baseado em MovimentacaoEstoque
                saldo = Decimal('0')
                
                # Considerar unificação
                codigos = UnificacaoCodigos.get_todos_codigos_relacionados(
                    produto.cod_produto
                )
                
                for codigo in codigos:
                    movs = MovimentacaoEstoque.query.filter_by(
                        cod_produto=codigo,
                        ativo=True
                    ).all()
                    
                    for mov in movs:
                        # qtd_movimentacao já vem com sinal correto
                        saldo += Decimal(str(mov.qtd_movimentacao))
                
                # Atualizar produto
                produto.saldo_atual = saldo
                produto.atualizado_em = agora_brasil()
                db.session.add(produto)
                
                # Recalcular projeção
                ServicoEstoqueTempoReal.calcular_ruptura_d7(produto.cod_produto)
                
                processados += 1
                
            except Exception as e:
                erros.append({
                    'produto': produto.cod_produto,
                    'erro': str(e)
                })
        
        # Commit final
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            erros.append({'geral': str(e)})
        
        return {
            'processados': processados,
            'erros': erros,
            'timestamp': agora_brasil().isoformat()
        }
    
    @staticmethod
    def inicializar_produto(cod_produto: str, nome_produto: str = None) -> EstoqueTempoReal:
        """
        Inicializa EstoqueTempoReal para um produto se não existir.
        
        Args:
            cod_produto: Código do produto
            nome_produto: Nome do produto (opcional)
            
        Returns:
            Objeto EstoqueTempoReal
        """
        estoque = EstoqueTempoReal.query.filter_by(
            cod_produto=cod_produto
        ).first()
        
        if not estoque:
            estoque = EstoqueTempoReal(
                cod_produto=cod_produto,
                nome_produto=nome_produto or f"Produto {cod_produto}",
                saldo_atual=Decimal('0')
            )
            db.session.add(estoque)
            
            try:
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                raise e 
        
        return estoque
    
    @staticmethod
    def get_projecao_completa(cod_produto: str, dias: int = 28) -> Optional[Dict[str, Any]]:
        """
        Retorna projeção completa de estoque para N dias.
        
        Args:
            cod_produto: Código do produto
            dias: Número de dias para projetar
            
        Returns:
            Dict com projeção dia a dia
        """
        # Buscar estoque atual
        estoque = EstoqueTempoReal.query.filter_by(
            cod_produto=cod_produto
        ).first()
        
        if not estoque:
            return None
        
        hoje = date.today()
        projecao = []
        saldo_atual = float(estoque.saldo_atual)
        menor_saldo_d7 = saldo_atual  # Para recalcular o menor estoque D0-D7
        data_disponivel = None
        qtd_disponivel = None
        
        # Para cada dia
        for i in range(dias + 1):
            data_proj = hoje + timedelta(days=i)
            
            # Buscar movimentação prevista
            # IMPORTANTE: Considerar UnificacaoCodigos
            codigos_relacionados = UnificacaoCodigos.get_todos_codigos_relacionados(cod_produto)
            
            # Buscar movimentações de todos os códigos relacionados
            movs = MovimentacaoPrevista.query.filter(
                MovimentacaoPrevista.cod_produto.in_(codigos_relacionados),
                MovimentacaoPrevista.data_prevista == data_proj
            ).all()
            
            # Somar entradas e saídas de todos os códigos
            entrada = sum(float(m.entrada_prevista) for m in movs) if movs else 0
            saida = sum(float(m.saida_prevista) for m in movs) if movs else 0
            
            # Calcular saldo final do dia
            saldo_final = saldo_atual + entrada - saida
            
            # Atualizar menor_saldo_d7 para os primeiros 7 dias
            if i <= 7 and saldo_final < menor_saldo_d7:
                menor_saldo_d7 = saldo_final
            
            # Identificar primeira data com estoque positivo
            # IMPORTANTE: Usar saldo_final (Saldo) e não o estoque_final
            if data_disponivel is None and saldo_final > 0:
                data_disponivel = data_proj
                qtd_disponivel = saldo_final
            
            projecao.append({
                'dia': i,
                'data': data_proj.isoformat(),
                'saldo_inicial': saldo_atual,
                'entrada': entrada,
                'saida': saida,
                'saldo_final': saldo_final
            })
            
            # Atualizar saldo para próximo dia
            saldo_atual = saldo_final
        
        return {
            'cod_produto': cod_produto,
            'nome_produto': estoque.nome_produto,
            'estoque_atual': float(estoque.saldo_atual),
            'menor_estoque_d7': menor_saldo_d7,  # Recalculado aqui
            'dia_ruptura': estoque.dia_ruptura.isoformat() if estoque.dia_ruptura else None,
            'data_disponivel': data_disponivel.isoformat() if data_disponivel else None,
            'qtd_disponivel': qtd_disponivel,
            'projecao': projecao
        }