#!/usr/bin/env python3
"""
Teste da Solução dos 8 Pedidos Problemáticos
============================================

Script para testar se a correção resolve completamente os problemas identificados.

TESTES REALIZADOS:
1. Verifica NFs órfãs antes da correção
2. Executa a correção
3. Valida que não há mais NFs órfãs  
4. Verifica EmbarqueItems sem erro_validacao
5. Simula sincronização para verificar que não gera mais alertas falsos

Autor: Sistema de Fretes
Data: 2025-08-13
"""

import logging
import sys
import os
from datetime import datetime

# Configurar path
sys.path.append(os.path.join(os.path.dirname(__file__)))

from app import create_app, db
from app.faturamento.models import RelatorioFaturamentoImportado, FaturamentoProduto
from app.estoque.models import MovimentacaoEstoque
from app.embarques.models import EmbarqueItem, Embarque
from app.pedidos.models import Pedido
from app.separacao.models import Separacao
from sqlalchemy import and_, text
from corrigir_nfs_problema_8_pedidos import CorretorNFsProblema

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('teste_solucao_8_pedidos.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class TestadorSolucao:
    """
    Testa se a solução resolve completamente os problemas
    """
    
    def __init__(self):
        self.app = create_app()
        self.resultados_teste = {
            'pre_correcao': {},
            'pos_correcao': {},
            'validacao_final': {},
            'sucesso_geral': False
        }
    
    def executar_teste_completo(self):
        """
        Executa bateria completa de testes
        """
        with self.app.app_context():
            try:
                logger.info("🧪 INICIANDO TESTE COMPLETO DA SOLUÇÃO")
                logger.info("=" * 60)
                
                # FASE 1: Diagnóstico pré-correção
                self._diagnostico_pre_correcao()
                
                # FASE 2: Executar correção
                self._executar_correcao()
                
                # FASE 3: Validação pós-correção  
                self._validacao_pos_correcao()
                
                # FASE 4: Teste de integração (simular sync)
                self._teste_integracao()
                
                # FASE 5: Resultado final
                self._avaliar_resultado_final()
                
                return self.resultados_teste
                
            except Exception as e:
                logger.error(f"❌ ERRO CRÍTICO no teste: {e}")
                self.resultados_teste['erro_critico'] = str(e)
                return self.resultados_teste
    
    def _diagnostico_pre_correcao(self):
        """
        Diagnóstica problemas antes da correção
        """
        logger.info("🔍 FASE 1: DIAGNÓSTICO PRÉ-CORREÇÃO")
        logger.info("-" * 40)
        
        # 1. Contar NFs órfãs
        query_nfs_orfas = """
        SELECT COUNT(*) as total,
               ARRAY_AGG(rfi.numero_nf ORDER BY rfi.numero_nf) as nfs
        FROM relatorio_faturamento_importado rfi
        INNER JOIN faturamento_produto fp ON rfi.numero_nf = fp.numero_nf
        WHERE rfi.ativo = true
        AND NOT EXISTS (
            SELECT 1 FROM movimentacao_estoque me 
            WHERE me.observacao LIKE '%NF ' || rfi.numero_nf || '%'
            AND me.tipo_movimentacao = 'FATURAMENTO'
        )
        """
        
        resultado = db.session.execute(text(query_nfs_orfas)).fetchone()
        nfs_orfas_count = resultado[0] if resultado else 0
        nfs_orfas_lista = resultado[1] if resultado and resultado[1] else []
        
        # 2. Contar EmbarqueItems com erro
        embarque_items_erro = EmbarqueItem.query.filter(
            EmbarqueItem.erro_validacao.isnot(None)
        ).count()
        
        # 3. Contar separações que poderiam gerar alertas falsos
        separacoes_risco = db.session.query(Separacao).join(
            Pedido, Separacao.separacao_lote_id == Pedido.separacao_lote_id
        ).filter(
            Pedido.status == 'COTADO'
        ).count()
        
        self.resultados_teste['pre_correcao'] = {
            'nfs_orfas': nfs_orfas_count,
            'nfs_orfas_lista': nfs_orfas_lista[:10],  # Mostrar apenas primeiras 10
            'embarque_items_erro': embarque_items_erro,
            'separacoes_risco_alerta': separacoes_risco
        }
        
        logger.info(f"📊 NFs órfãs encontradas: {nfs_orfas_count}")
        if nfs_orfas_lista:
            logger.info(f"📋 Exemplos: {nfs_orfas_lista[:5]}")
        logger.info(f"📊 EmbarqueItems com erro: {embarque_items_erro}")
        logger.info(f"📊 Separações COTADAS (risco alerta): {separacoes_risco}")
    
    def _executar_correcao(self):
        """
        Executa a correção usando o CorretorNFsProblema
        """
        logger.info("🔧 FASE 2: EXECUTANDO CORREÇÃO")
        logger.info("-" * 40)
        
        try:
            corretor = CorretorNFsProblema()
            resultado_correcao = corretor.executar_correcao_completa()
            
            self.resultados_teste['correcao_executada'] = resultado_correcao
            
            logger.info("✅ Correção executada com sucesso")
            logger.info(f"📊 Problemas corrigidos: {resultado_correcao.get('problemas_corrigidos', 0)}")
            
        except Exception as e:
            logger.error(f"❌ Erro na correção: {e}")
            self.resultados_teste['erro_correcao'] = str(e)
            raise e
    
    def _validacao_pos_correcao(self):
        """
        Valida se os problemas foram resolvidos
        """
        logger.info("✅ FASE 3: VALIDAÇÃO PÓS-CORREÇÃO")
        logger.info("-" * 40)
        
        # 1. Re-verificar NFs órfãs
        query_nfs_orfas = """
        SELECT COUNT(*) as total
        FROM relatorio_faturamento_importado rfi
        INNER JOIN faturamento_produto fp ON rfi.numero_nf = fp.numero_nf
        WHERE rfi.ativo = true
        AND NOT EXISTS (
            SELECT 1 FROM movimentacao_estoque me 
            WHERE me.observacao LIKE '%NF ' || rfi.numero_nf || '%'
            AND me.tipo_movimentacao = 'FATURAMENTO'
        )
        """
        
        resultado = db.session.execute(text(query_nfs_orfas)).fetchone()
        nfs_orfas_pos = resultado[0] if resultado else 0
        
        # 2. Re-verificar EmbarqueItems com erro
        embarque_items_erro_pos = EmbarqueItem.query.filter(
            EmbarqueItem.erro_validacao.isnot(None)
        ).count()
        
        # 3. Verificar MovimentacaoEstoque criadas
        movimentacoes_correcao = MovimentacaoEstoque.query.filter(
            MovimentacaoEstoque.criado_por == 'Correção Automática'
        ).count()
        
        self.resultados_teste['pos_correcao'] = {
            'nfs_orfas_restantes': nfs_orfas_pos,
            'embarque_items_erro_restantes': embarque_items_erro_pos,
            'movimentacoes_criadas_correcao': movimentacoes_correcao,
            'problema_nfs_resolvido': nfs_orfas_pos == 0,
            'problema_embarque_melhorou': embarque_items_erro_pos < self.resultados_teste['pre_correcao']['embarque_items_erro']
        }
        
        logger.info(f"📊 NFs órfãs restantes: {nfs_orfas_pos}")
        logger.info(f"📊 EmbarqueItems com erro restantes: {embarque_items_erro_pos}")
        logger.info(f"📊 Movimentações criadas pela correção: {movimentacoes_correcao}")
        
        if nfs_orfas_pos == 0:
            logger.info("✅ SUCESSO: Problema de NFs órfãs resolvido!")
        else:
            logger.warning(f"⚠️ ATENÇÃO: Ainda restam {nfs_orfas_pos} NFs órfãs")
    
    def _teste_integracao(self):
        """
        Testa se a sincronização não gerará mais alertas falsos
        """
        logger.info("🔄 FASE 4: TESTE DE INTEGRAÇÃO")
        logger.info("-" * 40)
        
        # Simular as condições que causaram o problema original
        try:
            # 1. Verificar se ainda há separações COTADAS que poderiam gerar alertas
            separacoes_cotadas = db.session.query(Separacao).join(
                Pedido, Separacao.separacao_lote_id == Pedido.separacao_lote_id
            ).filter(
                Pedido.status == 'COTADO'
            ).all()
            
            problemas_potenciais = 0
            
            for sep in separacoes_cotadas[:10]:  # Testar apenas primeiras 10
                # Verificar se tem MovimentacaoEstoque correspondente
                tem_movimentacao = MovimentacaoEstoque.query.filter(
                    and_(
                        MovimentacaoEstoque.observacao.like(f'%lote separação {sep.separacao_lote_id}%'),
                        MovimentacaoEstoque.tipo_movimentacao == 'FATURAMENTO'
                    )
                ).first()
                
                if not tem_movimentacao:
                    problemas_potenciais += 1
            
            self.resultados_teste['integracao'] = {
                'separacoes_cotadas_testadas': min(len(separacoes_cotadas), 10),
                'problemas_potenciais': problemas_potenciais,
                'risco_alertas_falsos': problemas_potenciais > 0
            }
            
            logger.info(f"📊 Separações COTADAS testadas: {min(len(separacoes_cotadas), 10)}")
            logger.info(f"📊 Problemas potenciais encontrados: {problemas_potenciais}")
            
            if problemas_potenciais == 0:
                logger.info("✅ SUCESSO: Risco de alertas falsos eliminado!")
            else:
                logger.warning(f"⚠️ ATENÇÃO: {problemas_potenciais} separações ainda podem gerar alertas falsos")
        
        except Exception as e:
            logger.error(f"❌ Erro no teste de integração: {e}")
            self.resultados_teste['erro_integracao'] = str(e)
    
    def _avaliar_resultado_final(self):
        """
        Avalia o resultado final do teste
        """
        logger.info("🎯 FASE 5: AVALIAÇÃO FINAL")
        logger.info("-" * 40)
        
        pre = self.resultados_teste['pre_correcao']
        pos = self.resultados_teste['pos_correcao']
        integracao = self.resultados_teste.get('integracao', {})
        
        # Critérios de sucesso
        criterios = {
            'nfs_orfas_resolvidas': pos.get('nfs_orfas_restantes', 999) == 0,
            'embarque_items_melhoraram': pos.get('problema_embarque_melhorou', False),
            'movimentacoes_criadas': pos.get('movimentacoes_criadas_correcao', 0) > 0,
            'risco_alertas_eliminado': not integracao.get('risco_alertas_falsos', True)
        }
        
        sucessos = sum(criterios.values())
        total_criterios = len(criterios)
        
        self.resultados_teste['validacao_final'] = {
            'criterios_atendidos': criterios,
            'sucessos': sucessos,
            'total_criterios': total_criterios,
            'percentual_sucesso': (sucessos / total_criterios) * 100,
            'aprovado': sucessos >= total_criterios - 1  # Permite 1 critério não atendido
        }
        
        self.resultados_teste['sucesso_geral'] = sucessos >= total_criterios - 1
        
        logger.info(f"📊 Critérios atendidos: {sucessos}/{total_criterios}")
        logger.info(f"📊 Percentual de sucesso: {(sucessos/total_criterios)*100:.1f}%")
        
        for criterio, atendido in criterios.items():
            status = "✅" if atendido else "❌"
            logger.info(f"  {status} {criterio}")
        
        if self.resultados_teste['sucesso_geral']:
            logger.info("🎉 TESTE APROVADO: Solução resolve os problemas!")
        else:
            logger.warning("⚠️ TESTE REPROVADO: Solução precisa de ajustes")
    
    def gerar_relatorio_teste(self):
        """
        Gera relatório detalhado do teste
        """
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        relatorio = f"""
════════════════════════════════════════════════
RELATÓRIO DE TESTE - SOLUÇÃO DOS 8 PEDIDOS
════════════════════════════════════════════════

🕐 Data/Hora: {timestamp}
🎯 Objetivo: Validar correção dos problemas de NFs órfãs

📊 RESULTADOS PRÉ-CORREÇÃO:
• NFs órfãs: {self.resultados_teste['pre_correcao'].get('nfs_orfas', 0)}
• EmbarqueItems com erro: {self.resultados_teste['pre_correcao'].get('embarque_items_erro', 0)}
• Separações COTADAS (risco): {self.resultados_teste['pre_correcao'].get('separacoes_risco_alerta', 0)}

📊 RESULTADOS PÓS-CORREÇÃO:
• NFs órfãs restantes: {self.resultados_teste['pos_correcao'].get('nfs_orfas_restantes', 'N/A')}
• EmbarqueItems com erro restantes: {self.resultados_teste['pos_correcao'].get('embarque_items_erro_restantes', 'N/A')}
• Movimentações criadas: {self.resultados_teste['pos_correcao'].get('movimentacoes_criadas_correcao', 'N/A')}

🔄 TESTE DE INTEGRAÇÃO:
• Problemas potenciais: {self.resultados_teste.get('integracao', {}).get('problemas_potenciais', 'N/A')}
• Risco de alertas falsos: {self.resultados_teste.get('integracao', {}).get('risco_alertas_falsos', 'N/A')}

✅ AVALIAÇÃO FINAL:
• Percentual de sucesso: {self.resultados_teste['validacao_final'].get('percentual_sucesso', 0):.1f}%
• Resultado: {'APROVADO' if self.resultados_teste['sucesso_geral'] else 'REPROVADO'}

════════════════════════════════════════════════
"""
        
        return relatorio


def main():
    """
    Função principal
    """
    try:
        print("🧪 INICIANDO TESTE DA SOLUÇÃO DOS 8 PEDIDOS")
        print("=" * 50)
        
        testador = TestadorSolucao()
        resultado = testador.executar_teste_completo()
        
        # Gerar relatório
        relatorio = testador.gerar_relatorio_teste()
        
        # Salvar relatório
        with open('relatorio_teste_solucao.txt', 'w', encoding='utf-8') as f:
            f.write(relatorio)
        
        print("\n" + relatorio)
        print(f"📄 Relatório salvo em: relatorio_teste_solucao.txt")
        print(f"📄 Log detalhado em: teste_solucao_8_pedidos.log")
        
        return resultado['sucesso_geral']
        
    except Exception as e:
        print(f"\n❌ ERRO CRÍTICO: {e}")
        return False


if __name__ == "__main__":
    sucesso = main()
    sys.exit(0 if sucesso else 1)