"""
Sistema Otimizado de Recálculo de Movimentação Prevista
========================================================
Substitui sistema de soma/subtração por recálculo total
Mais confiável e evita acumulação de erros
"""

from sqlalchemy import text
import logging

logger = logging.getLogger(__name__)


class RecalculoMovimentacaoPrevista:
    """
    Sistema de recálculo total de movimentações previstas
    Ao invés de somar/subtrair, recalcula do zero
    """
    
    @staticmethod
    def recalcular_saida_prevista_produto(connection, cod_produto, data_prevista=None):
        """
        Recalcula saida_prevista para um produto específico
        
        REGRA DE NEGÓCIO:
        saida_prevista = 
            Separacao.qtd_saldo (onde NF não existe em FaturamentoProduto) +
            PreSeparacaoItem.qtd_selecionada_usuario (status CRIADO ou RECOMPOSTO)
        
        Args:
            connection: Conexão SQLAlchemy
            cod_produto: Código do produto
            data_prevista: Data específica ou None para todas
        """
        try:
            # Se data específica, recalcular só essa data
            if data_prevista:
                return RecalculoMovimentacaoPrevista._recalcular_data_especifica(
                    connection, cod_produto, data_prevista
                )
            
            # Senão, recalcular todas as datas do produto
            return RecalculoMovimentacaoPrevista._recalcular_todas_datas_produto(
                connection, cod_produto
            )
            
        except Exception as e:
            logger.error(f"Erro ao recalcular saida_prevista para {cod_produto}: {e}")
            return False
    
    @staticmethod
    def _recalcular_data_especifica(connection, cod_produto, data_prevista):
        """
        Recalcula saida_prevista para produto e data específicos
        """
        try:
            # 1. Calcular total de Separacao (sem NF faturada)
            # Verificação: NF do Pedido NÃO existe em FaturamentoProduto
            sql_separacao = """
            SELECT COALESCE(SUM(s.qtd_saldo), 0) as total_separacao
            FROM separacao s
            LEFT JOIN pedidos p ON s.separacao_lote_id = p.separacao_lote_id
            WHERE s.cod_produto = :cod_produto
              AND s.expedicao = :data_prevista
              AND s.qtd_saldo > 0
              AND (
                  p.nf IS NULL 
                  OR NOT EXISTS (
                      SELECT 1 FROM faturamento_produto fp
                      WHERE fp.numero_nf = p.nf
                        AND fp.cod_produto = s.cod_produto
                        AND fp.status_nf != 'Cancelado'
                  )
              )
            """
            
            result = connection.execute(text(sql_separacao), {
                'cod_produto': cod_produto,
                'data_prevista': data_prevista
            })
            total_separacao = float(result.scalar() or 0)
            
            # 2. Calcular total de PreSeparacaoItem (CRIADO ou RECOMPOSTO)
            sql_pre_separacao = """
            SELECT COALESCE(SUM(psi.qtd_selecionada_usuario), 0) as total_pre_separacao
            FROM pre_separacao_item psi
            WHERE psi.cod_produto = :cod_produto
              AND psi.data_expedicao_editada = :data_prevista
              AND psi.status IN ('CRIADO', 'RECOMPOSTO')
            """
            
            result = connection.execute(text(sql_pre_separacao), {
                'cod_produto': cod_produto,
                'data_prevista': data_prevista
            })
            total_pre_separacao = float(result.scalar() or 0)
            
            # 3. Total de saída prevista
            total_saida = total_separacao + total_pre_separacao
            
            # 4. Buscar entrada_prevista atual (não alteramos)
            sql_entrada = """
            SELECT COALESCE(entrada_prevista, 0) as entrada
            FROM movimentacao_prevista
            WHERE cod_produto = :cod_produto
              AND data_prevista = :data_prevista
            """
            
            result = connection.execute(text(sql_entrada), {
                'cod_produto': cod_produto,
                'data_prevista': data_prevista
            })
            entrada_prevista = float(result.scalar() or 0)
            
            # 5. Atualizar ou inserir MovimentacaoPrevista
            if total_saida > 0 or entrada_prevista > 0:
                # UPSERT com valores absolutos (não soma)
                sql_upsert = """
                INSERT INTO movimentacao_prevista (
                    cod_produto, data_prevista, entrada_prevista, saida_prevista
                ) VALUES (
                    :cod_produto, :data_prevista, :entrada_prevista, :saida_prevista
                )
                ON CONFLICT (cod_produto, data_prevista) DO UPDATE SET
                    saida_prevista = :saida_prevista,  -- SUBSTITUI ao invés de somar
                    entrada_prevista = EXCLUDED.entrada_prevista  -- Mantém entrada
                """
                
                connection.execute(text(sql_upsert), {
                    'cod_produto': cod_produto,
                    'data_prevista': data_prevista,
                    'entrada_prevista': entrada_prevista,
                    'saida_prevista': total_saida
                })
            else:
                # Se zerou tudo, deletar registro
                sql_delete = """
                DELETE FROM movimentacao_prevista 
                WHERE cod_produto = :cod_produto 
                  AND data_prevista = :data_prevista
                """
                
                connection.execute(text(sql_delete), {
                    'cod_produto': cod_produto,
                    'data_prevista': data_prevista
                })
            
            logger.debug(f"Recalculado {cod_produto}/{data_prevista}: Separação={total_separacao}, PreSep={total_pre_separacao}, Total={total_saida}")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao recalcular {cod_produto}/{data_prevista}: {e}")
            return False
    
    @staticmethod
    def _recalcular_todas_datas_produto(connection, cod_produto):
        """
        Recalcula todas as datas de um produto
        """
        try:
            # 1. Buscar todas as datas relevantes para o produto
            sql_datas = """
            SELECT DISTINCT data FROM (
                -- Datas de Separacao
                SELECT s.expedicao as data
                FROM separacao s
                WHERE s.cod_produto = :cod_produto
                  AND s.expedicao IS NOT NULL
                
                UNION
                
                -- Datas de PreSeparacaoItem
                SELECT psi.data_expedicao_editada as data
                FROM pre_separacao_item psi
                WHERE psi.cod_produto = :cod_produto
                  AND psi.data_expedicao_editada IS NOT NULL
                  AND psi.status IN ('CRIADO', 'RECOMPOSTO')
                
                UNION
                
                -- Datas existentes em MovimentacaoPrevista
                SELECT mp.data_prevista as data
                FROM movimentacao_prevista mp
                WHERE mp.cod_produto = :cod_produto
            ) as todas_datas
            WHERE data IS NOT NULL
            """
            
            result = connection.execute(text(sql_datas), {'cod_produto': cod_produto})
            datas = [row[0] for row in result]
            
            # 2. Recalcular cada data
            for data in datas:
                RecalculoMovimentacaoPrevista._recalcular_data_especifica(
                    connection, cod_produto, data
                )
            
            logger.info(f"Recalculado {len(datas)} datas para produto {cod_produto}")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao recalcular todas as datas de {cod_produto}: {e}")
            return False
    
    @staticmethod
    def recalcular_lote_completo(connection, separacao_lote_id):
        """
        Recalcula todos os produtos de um lote de separação
        Útil após criar/editar separações
        """
        try:
            # Buscar todos produtos/datas do lote
            sql_itens = """
            SELECT DISTINCT cod_produto, expedicao
            FROM separacao
            WHERE separacao_lote_id = :lote_id
              AND expedicao IS NOT NULL
            
            UNION
            
            SELECT DISTINCT cod_produto, data_expedicao_editada
            FROM pre_separacao_item
            WHERE separacao_lote_id = :lote_id
              AND data_expedicao_editada IS NOT NULL
            """
            
            result = connection.execute(text(sql_itens), {'lote_id': separacao_lote_id})
            
            for row in result:
                cod_produto, data_prevista = row
                RecalculoMovimentacaoPrevista._recalcular_data_especifica(
                    connection, cod_produto, data_prevista
                )
            
            return True
            
        except Exception as e:
            logger.error(f"Erro ao recalcular lote {separacao_lote_id}: {e}")
            return False
    
    @staticmethod
    def recalcular_apos_sincronizacao(connection):
        """
        Recalcula TUDO após sincronização com Odoo
        Método mais pesado, usar com cautela
        """
        try:
            logger.info("Iniciando recálculo completo pós-sincronização...")
            
            # Limpar todas as saidas_previstas primeiro
            sql_limpar = """
            UPDATE movimentacao_prevista 
            SET saida_prevista = 0
            """
            connection.execute(text(sql_limpar))
            
            # Recalcular baseado em Separacao + PreSeparacaoItem
            sql_recalculo = """
            WITH saidas_calculadas AS (
                -- Separações sem NF faturada (verificando NF em Pedido)
                SELECT 
                    s.cod_produto,
                    s.expedicao as data_prevista,
                    SUM(s.qtd_saldo) as qtd_saida
                FROM separacao s
                LEFT JOIN pedidos p ON s.separacao_lote_id = p.separacao_lote_id
                WHERE s.expedicao IS NOT NULL
                  AND s.qtd_saldo > 0
                  AND (
                      p.nf IS NULL 
                      OR NOT EXISTS (
                          SELECT 1 FROM faturamento_produto fp
                          WHERE fp.numero_nf = p.nf
                            AND fp.cod_produto = s.cod_produto
                            AND fp.status_nf != 'Cancelado'
                      )
                  )
                GROUP BY s.cod_produto, s.expedicao
                
                UNION ALL
                
                -- Pré-separações ativas
                SELECT 
                    psi.cod_produto,
                    psi.data_expedicao_editada as data_prevista,
                    SUM(psi.qtd_selecionada_usuario) as qtd_saida
                FROM pre_separacao_item psi
                WHERE psi.data_expedicao_editada IS NOT NULL
                  AND psi.status IN ('CRIADO', 'RECOMPOSTO')
                GROUP BY psi.cod_produto, psi.data_expedicao_editada
            )
            INSERT INTO movimentacao_prevista (cod_produto, data_prevista, entrada_prevista, saida_prevista)
            SELECT 
                cod_produto,
                data_prevista,
                0,  -- entrada será preenchida pelos triggers de ProgramacaoProducao
                SUM(qtd_saida)
            FROM saidas_calculadas
            GROUP BY cod_produto, data_prevista
            ON CONFLICT (cod_produto, data_prevista) DO UPDATE SET
                saida_prevista = EXCLUDED.saida_prevista
            """
            
            connection.execute(text(sql_recalculo))
            
            # Limpar registros zerados
            sql_cleanup = """
            DELETE FROM movimentacao_prevista
            WHERE entrada_prevista <= 0 AND saida_prevista <= 0
            """
            connection.execute(text(sql_cleanup))
            
            logger.info("Recálculo completo concluído com sucesso")
            return True
            
        except Exception as e:
            logger.error(f"Erro no recálculo completo: {e}")
            return False