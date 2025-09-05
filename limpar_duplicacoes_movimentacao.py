#!/usr/bin/env python3
"""
Script para limpar duplicações em MovimentacaoEstoque
Mantém apenas o registro mais antigo para cada combinação numero_nf + cod_produto
Apenas para tipo_movimentacao = 'FATURAMENTO'
"""

import logging
from datetime import datetime
from app import create_app, db
from app.estoque.models import MovimentacaoEstoque
from sqlalchemy import func, and_

app = create_app()

logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def identificar_duplicacoes():
    """
    Identifica movimentações duplicadas
    Retorna lista de (numero_nf, cod_produto, count)
    """
    duplicados = db.session.query(
        MovimentacaoEstoque.numero_nf,
        MovimentacaoEstoque.cod_produto,
        func.count(MovimentacaoEstoque.id).label('count')
    ).filter(
        MovimentacaoEstoque.numero_nf.isnot(None),
        MovimentacaoEstoque.tipo_movimentacao == 'FATURAMENTO',  # Apenas FATURAMENTO
        MovimentacaoEstoque.status_nf == 'FATURADO'
    ).group_by(
        MovimentacaoEstoque.numero_nf,
        MovimentacaoEstoque.cod_produto
    ).having(
        func.count(MovimentacaoEstoque.id) > 1
    ).all()
    
    return duplicados

def limpar_duplicacoes_por_nf_produto():
    """
    Remove duplicações mantendo apenas o registro mais antigo
    para cada combinação numero_nf + cod_produto
    """
    
    with app.app_context():
        logger.info("=" * 80)
        logger.info("🧹 INICIANDO LIMPEZA DE DUPLICAÇÕES EM MOVIMENTACAOESTOQUE")
        logger.info("=" * 80)
        
        # 1. Identificar duplicações
        logger.info("🔍 Identificando duplicações...")
        duplicados = identificar_duplicacoes()
        
        if not duplicados:
            logger.info("✅ Nenhuma duplicação encontrada!")
            return
        
        logger.info(f"⚠️ Encontradas {len(duplicados)} combinações duplicadas")
        
        # Estatísticas
        total_registros_duplicados = sum(count for _, _, count in duplicados)
        total_registros_deletar = total_registros_duplicados - len(duplicados)  # Mantém 1 de cada
        
        print("\n📊 RESUMO DAS DUPLICAÇÕES:")
        print(f"  • Combinações únicas duplicadas: {len(duplicados)}")
        print(f"  • Total de registros duplicados: {total_registros_duplicados}")
        print(f"  • Registros a deletar: {total_registros_deletar}")
        print(f"  • Registros a manter: {len(duplicados)}")
        
        # Mostrar exemplos
        print("\n📋 EXEMPLOS (primeiras 5):")
        for nf, produto, count in duplicados[:5]:
            print(f"  NF: {nf} | Produto: {produto} | Ocorrências: {count}")
        
        # 2. Confirmar com usuário
        print("\n" + "=" * 80)
        resposta = input("⚠️ CONFIRMAR LIMPEZA? (Digite 'SIM' para continuar): ")
        
        if resposta.upper() != 'SIM':
            logger.info("❌ Operação cancelada pelo usuário")
            return
        
        # 3. Processar limpeza
        logger.info("\n🔧 Iniciando limpeza...")
        registros_deletados = 0
        erros = []
        
        for idx, (nf, produto, count) in enumerate(duplicados):
            try:
                # Buscar todos os registros desta combinação
                registros = MovimentacaoEstoque.query.filter_by(
                    numero_nf=nf,
                    cod_produto=produto,
                    tipo_movimentacao='FATURAMENTO',
                    status_nf='FATURADO'
                ).order_by(
                    MovimentacaoEstoque.criado_em.asc()  # Mais antigo primeiro
                ).all()
                
                if len(registros) <= 1:
                    continue
                
                # Manter o mais antigo (primeiro da lista)
                registro_manter = registros[0]
                registros_deletar = registros[1:]
                
                logger.debug(f"[{idx+1}/{len(duplicados)}] NF {nf}, Produto {produto}:")
                logger.debug(f"  Mantendo: ID {registro_manter.id} (criado em {registro_manter.criado_em})")
                
                # Antes de deletar, consolidar informações importantes
                for reg in registros_deletar:
                    # Se o registro a manter não tem lote mas algum dos outros tem
                    if (not registro_manter.separacao_lote_id or registro_manter.separacao_lote_id == 'LOTE') \
                       and reg.separacao_lote_id and reg.separacao_lote_id != 'LOTE':
                        registro_manter.separacao_lote_id = reg.separacao_lote_id
                        logger.debug(f"    → Lote atualizado para: {reg.separacao_lote_id}")
                    
                    # Se falta pedido
                    if not registro_manter.num_pedido and reg.num_pedido:
                        registro_manter.num_pedido = reg.num_pedido
                        logger.debug(f"    → Pedido atualizado para: {reg.num_pedido}")
                    
                    # Se falta código embarque
                    if not registro_manter.codigo_embarque and reg.codigo_embarque:
                        registro_manter.codigo_embarque = reg.codigo_embarque
                        logger.debug(f"    → Código embarque atualizado para: {reg.codigo_embarque}")
                
                # Atualizar registro mantido
                registro_manter.atualizado_em = datetime.now()
                registro_manter.atualizado_por = 'Script Limpeza Duplicações - Consolidado'
                
                # Deletar duplicados
                for reg in registros_deletar:
                    logger.debug(f"  Deletando: ID {reg.id} (criado em {reg.criado_em})")
                    db.session.delete(reg)
                    registros_deletados += 1
                
                # Commit a cada 100 registros para não sobrecarregar
                if (idx + 1) % 100 == 0:
                    db.session.commit()
                    logger.info(f"  ✓ Processadas {idx + 1}/{len(duplicados)} combinações...")
                
            except Exception as e:
                logger.error(f"❌ Erro ao processar NF {nf}, Produto {produto}: {e}")
                erros.append(f"NF {nf}, Produto {produto}: {str(e)}")
                db.session.rollback()
                continue
        
        # Commit final
        try:
            db.session.commit()
            logger.info("✅ Commit final realizado")
        except Exception as e:
            logger.error(f"❌ Erro no commit final: {e}")
            db.session.rollback()
            return
        
        # 4. Relatório final
        print("\n" + "=" * 80)
        print("📊 RELATÓRIO FINAL:")
        print("=" * 80)
        print(f"✅ Registros deletados: {registros_deletados}")
        print(f"✅ Combinações processadas: {len(duplicados)}")
        
        if erros:
            print(f"\n⚠️ Erros encontrados: {len(erros)}")
            for erro in erros[:10]:  # Mostrar até 10 erros
                print(f"  • {erro}")
        
        # 5. Verificação pós-limpeza
        logger.info("\n🔍 Verificando resultado...")
        duplicados_restantes = identificar_duplicacoes()
        
        if duplicados_restantes:
            logger.warning(f"⚠️ Ainda restam {len(duplicados_restantes)} duplicações")
            print("\nDuplicações restantes:")
            for nf, produto, count in duplicados_restantes[:5]:
                print(f"  NF: {nf} | Produto: {produto} | Ocorrências: {count}")
        else:
            logger.info("✅ TODAS AS DUPLICAÇÕES FORAM REMOVIDAS COM SUCESSO!")
            print("\n🎉 LIMPEZA CONCLUÍDA COM SUCESSO!")
        
        print("=" * 80)

def verificar_registros_lote():
    """
    Verifica e reporta registros com separacao_lote_id = 'LOTE'
    """
    with app.app_context():
        registros_lote = MovimentacaoEstoque.query.filter_by(
            separacao_lote_id='LOTE',
            tipo_movimentacao='FATURAMENTO'
        ).count()
        
        if registros_lote > 0:
            print(f"\n📌 INFORMAÇÃO ADICIONAL:")
            print(f"  • {registros_lote} registros com separacao_lote_id='LOTE' (serão atualizados pelo processador)")
            
            # Mostrar exemplos
            exemplos = MovimentacaoEstoque.query.filter_by(
                separacao_lote_id='LOTE',
                tipo_movimentacao='FATURAMENTO'
            ).limit(3).all()
            
            print("  Exemplos:")
            for ex in exemplos:
                print(f"    - ID: {ex.id} | NF: {ex.numero_nf} | Produto: {ex.cod_produto}")

if __name__ == "__main__":
    print("""
╔════════════════════════════════════════════════════════════════╗
║     SCRIPT DE LIMPEZA DE DUPLICAÇÕES - MOVIMENTACAOESTOQUE    ║
╠════════════════════════════════════════════════════════════════╣
║  Este script irá:                                              ║
║  • Identificar movimentações duplicadas (NF + Produto)        ║
║  • Manter apenas o registro mais ANTIGO                       ║
║  • Consolidar informações importantes antes de deletar        ║
║  • Apenas para tipo_movimentacao = 'FATURAMENTO'             ║
╚════════════════════════════════════════════════════════════════╝
""")
    
    try:
        limpar_duplicacoes_por_nf_produto()
        verificar_registros_lote()
    except Exception as e:
        logger.error(f"❌ Erro fatal: {e}")
        import traceback
        traceback.print_exc()