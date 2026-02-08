#!/usr/bin/env python3
"""
Script para Recompor Separações Perdidas
Data: 2025-01-29

Objetivo: Recriar registros de Separacao usando dados de:
- Pedido (dados gerais)
- FaturamentoProduto (produtos e quantidades pela NF)
- CadastroPalletizacao (peso e pallet por produto)

EXECUTAR ANTES de transformar Pedido em VIEW!
"""

import os
import sys
from decimal import Decimal
import logging

# Adicionar path do projeto
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.pedidos.models import Pedido
from app.separacao.models import Separacao
from app.faturamento.models import FaturamentoProduto
from app.producao.models import CadastroPalletizacao
from sqlalchemy import and_, or_, func
from app.utils.timezone import agora_utc_naive
# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def calcular_peso_pallet_produto(cod_produto, quantidade):
    """
    Calcula peso e pallet baseado em CadastroPalletizacao
    """
    try:
        # Buscar dados de palletização
        pallet_info = CadastroPalletizacao.query.filter_by(
            cod_produto=cod_produto
        ).first()
        
        if pallet_info:
            # Calcular peso
            peso_unitario = float(pallet_info.peso_produto or 0)
            peso_total = peso_unitario * float(quantidade)
            
            # Calcular pallet
            if pallet_info.qtde_produto and pallet_info.qtde_produto > 0:
                pallet = float(quantidade) / float(pallet_info.qtde_produto)
            else:
                # Fallback: assumir 500kg por pallet
                pallet = peso_total / 500 if peso_total > 0 else 0
            
            return peso_total, pallet
        else:
            # Se não encontrar, usar valores padrão
            logger.warning(f"CadastroPalletizacao não encontrado para produto {cod_produto}")
            peso_estimado = float(quantidade) * 0.5  # Estimar 0.5kg por unidade
            pallet_estimado = peso_estimado / 500  # 500kg por pallet
            return peso_estimado, pallet_estimado
            
    except Exception as e:
        logger.error(f"Erro ao calcular peso/pallet para {cod_produto}: {e}")
        return 0, 0

def recompor_separacoes():
    """
    Função principal para recompor separações perdidas
    """
    
    app = create_app()
    
    with app.app_context():
        try:
            logger.info("=" * 60)
            logger.info("INICIANDO RECOMPOSIÇÃO DE SEPARAÇÕES")
            logger.info("=" * 60)
            
            # 1. Identificar Pedidos que precisam de recomposição
            logger.info("\n📊 Analisando pedidos...")
            
            # Buscar pedidos com NF preenchida
            pedidos_com_nf = Pedido.query.filter(
                Pedido.nf.isnot(None),
                Pedido.nf != '',
                Pedido.separacao_lote_id.isnot(None)
            ).all()
            
            logger.info(f"   Total de pedidos com NF: {len(pedidos_com_nf)}")
            
            estatisticas = {
                'pedidos_analisados': 0,
                'separacoes_criadas': 0,
                'separacoes_atualizadas': 0,
                'produtos_processados': 0,
                'erros': 0
            }
            
            for pedido in pedidos_com_nf:
                estatisticas['pedidos_analisados'] += 1
                
                try:
                    logger.info(f"\n🔄 Processando Pedido {pedido.num_pedido} (NF: {pedido.nf})")
                    
                    # Verificar se já existem separações para este lote
                    separacoes_existentes = Separacao.query.filter_by(
                        separacao_lote_id=pedido.separacao_lote_id
                    ).all()
                    
                    # Se não existem ou estão incompletas, recompor
                    if len(separacoes_existentes) == 0:
                        logger.info(f"   ⚠️ Nenhuma separação encontrada para lote {pedido.separacao_lote_id}")
                        
                        # Buscar produtos do faturamento pela NF
                        produtos_faturados = FaturamentoProduto.query.filter_by(
                            numero_nf=pedido.nf
                        ).all()
                        
                        if not produtos_faturados:
                            logger.warning(f"   ❌ Nenhum produto encontrado para NF {pedido.nf}")
                            continue
                        
                        logger.info(f"   📦 Encontrados {len(produtos_faturados)} produtos na NF")
                        
                        # Criar separação para cada produto
                        for produto_fat in produtos_faturados:
                            estatisticas['produtos_processados'] += 1
                            
                            # Calcular peso e pallet
                            peso, pallet = calcular_peso_pallet_produto(
                                produto_fat.cod_produto,
                                produto_fat.qtd_produto_faturado
                            )
                            
                            # Criar registro de Separacao
                            nova_separacao = Separacao(
                                # Identificação
                                separacao_lote_id=pedido.separacao_lote_id,
                                num_pedido=pedido.num_pedido,
                                data_pedido=pedido.data_pedido,
                                
                                # Cliente
                                cnpj_cpf=produto_fat.cnpj_cliente or pedido.cnpj_cpf,
                                raz_social_red=produto_fat.nome_cliente or pedido.raz_social_red,
                                nome_cidade=pedido.nome_cidade,
                                cod_uf=pedido.cod_uf,
                                
                                # Produto
                                cod_produto=produto_fat.cod_produto,
                                nome_produto=produto_fat.nome_produto,
                                qtd_saldo=float(produto_fat.qtd_produto_faturado),
                                valor_saldo=float(produto_fat.valor_produto_faturado),
                                peso=peso,
                                pallet=pallet,
                                
                                # Logística
                                rota=pedido.rota,
                                sub_rota=pedido.sub_rota,
                                observ_ped_1=pedido.observ_ped_1,
                                roteirizacao=pedido.roteirizacao,
                                expedicao=pedido.expedicao,
                                agendamento=pedido.agendamento,
                                agendamento_confirmado=pedido.agendamento_confirmado,
                                protocolo=pedido.protocolo,
                                
                                # Novos campos
                                status=pedido.status or 'FATURADO',
                                nf_cd=pedido.nf_cd if hasattr(pedido, 'nf_cd') else False,
                                data_embarque=pedido.data_embarque,
                                cidade_normalizada=pedido.cidade_normalizada,
                                uf_normalizada=pedido.uf_normalizada,
                                codigo_ibge=pedido.codigo_ibge,
                                cotacao_id=pedido.cotacao_id,
                                pedido_cliente=pedido.pedido_cliente if hasattr(pedido, 'pedido_cliente') else None,
                                
                                # Controle
                                numero_nf=pedido.nf,
                                sincronizado_nf=True,  # Já está faturado
                                data_sincronizacao=agora_utc_naive(),
                                tipo_envio='total',
                                criado_em=agora_utc_naive()
                            )
                            
                            db.session.add(nova_separacao)
                            logger.info(f"      ✅ Criada separação para {produto_fat.cod_produto} - Qtd: {produto_fat.qtd_produto_faturado}")
                        
                        estatisticas['separacoes_criadas'] += len(produtos_faturados)
                        
                    else:
                        # Atualizar campos faltantes nas separações existentes
                        logger.info(f"   📝 Atualizando {len(separacoes_existentes)} separações existentes")
                        
                        for sep in separacoes_existentes:
                            # Atualizar campos que podem estar faltando
                            if not sep.status:
                                sep.status = pedido.status or 'ABERTO'
                            if not sep.cotacao_id:
                                sep.cotacao_id = pedido.cotacao_id
                            if not sep.cidade_normalizada:
                                sep.cidade_normalizada = pedido.cidade_normalizada
                            if not sep.uf_normalizada:
                                sep.uf_normalizada = pedido.uf_normalizada
                            if not sep.codigo_ibge:
                                sep.codigo_ibge = pedido.codigo_ibge
                            if hasattr(pedido, 'nf_cd'):
                                sep.nf_cd = pedido.nf_cd
                            if hasattr(pedido, 'pedido_cliente'):
                                sep.pedido_cliente = pedido.pedido_cliente
                            
                            # Se tem NF mas não está marcado como sincronizado
                            if pedido.nf and not sep.sincronizado_nf:
                                sep.numero_nf = pedido.nf
                                sep.sincronizado_nf = True
                                sep.data_sincronizacao = agora_utc_naive()
                        
                        estatisticas['separacoes_atualizadas'] += len(separacoes_existentes)
                    
                    # Commit a cada pedido processado
                    db.session.commit()
                    
                except Exception as e:
                    logger.error(f"   ❌ Erro ao processar pedido {pedido.num_pedido}: {e}")
                    estatisticas['erros'] += 1
                    db.session.rollback()
                    continue
            
            # Estatísticas finais
            logger.info("\n" + "=" * 60)
            logger.info("📊 RESUMO DA RECOMPOSIÇÃO:")
            logger.info("=" * 60)
            logger.info(f"✅ Pedidos analisados: {estatisticas['pedidos_analisados']}")
            logger.info(f"✅ Separações criadas: {estatisticas['separacoes_criadas']}")
            logger.info(f"✅ Separações atualizadas: {estatisticas['separacoes_atualizadas']}")
            logger.info(f"✅ Produtos processados: {estatisticas['produtos_processados']}")
            if estatisticas['erros'] > 0:
                logger.info(f"⚠️ Erros encontrados: {estatisticas['erros']}")
            
            # Verificação final
            logger.info("\n📊 VERIFICAÇÃO FINAL:")
            
            # Total de pedidos vs separações
            total_pedidos = Pedido.query.filter(
                Pedido.separacao_lote_id.isnot(None)
            ).count()
            
            total_lotes_separacao = db.session.query(
                func.count(func.distinct(Separacao.separacao_lote_id))
            ).scalar()
            
            logger.info(f"   Total de pedidos com lote: {total_pedidos}")
            logger.info(f"   Total de lotes em Separacao: {total_lotes_separacao}")
            
            if total_pedidos == total_lotes_separacao:
                logger.info("   ✅ Todos os pedidos têm separação correspondente!")
            else:
                logger.warning(f"   ⚠️ Diferença de {total_pedidos - total_lotes_separacao} lotes")
            
            logger.info("\n✅ RECOMPOSIÇÃO CONCLUÍDA!")
            logger.info("Agora você pode executar a migração para VIEW com segurança.")
            
        except Exception as e:
            logger.error(f"❌ Erro fatal durante recomposição: {e}")
            db.session.rollback()
            raise
        finally:
            db.session.close()

if __name__ == "__main__":
    recompor_separacoes()