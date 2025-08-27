"""
Script para investigar separações ABERTO que não aparecem na Carteira
e corrigir pedidos duplicados

USO:
    python fix_pedidos_duplicados.py --investigar  # Investigar separações ausentes
    python fix_pedidos_duplicados.py --dry-run     # Simular correção de duplicados
    python fix_pedidos_duplicados.py --execute     # Executar correções
"""

from app import create_app, db
from app.pedidos.models import Pedido
from app.separacao.models import Separacao
from app.carteira.models import CarteiraPrincipal, SaldoStandby
from sqlalchemy import text, func, and_, exists
import logging
import sys

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def limpar_pedidos_duplicados(dry_run=True):
    """Remove pedidos duplicados mantendo apenas o mais recente"""
    app = create_app()
    
    with app.app_context():
        try:
            if dry_run:
                logger.info("=" * 60)
                logger.info("🔍 MODO DRY RUN - NENHUMA ALTERAÇÃO SERÁ FEITA")
                logger.info("=" * 60)
            else:
                logger.info("=" * 60)
                logger.info("⚠️  MODO EXECUÇÃO - ALTERAÇÕES SERÃO APLICADAS")
                logger.info("=" * 60)
            # 1. Identificar duplicados por separacao_lote_id
            duplicados = db.session.execute(text("""
                SELECT separacao_lote_id, COUNT(*) as qtd
                FROM pedidos
                WHERE separacao_lote_id IS NOT NULL
                GROUP BY separacao_lote_id
                HAVING COUNT(*) > 1
            """)).fetchall()
            
            if duplicados:
                logger.info(f"\n📊 Encontrados {len(duplicados)} lotes com pedidos duplicados\n")
                
                total_duplicados = 0
                for lote_id, qtd in duplicados:
                    logger.info(f"Lote {lote_id} tem {qtd} pedidos")
                    
                    # Buscar todos os pedidos deste lote
                    pedidos = Pedido.query.filter_by(
                        separacao_lote_id=lote_id
                    ).order_by(Pedido.criado_em.desc()).all()
                    
                    # Manter o mais recente (primeiro da lista)
                    pedido_mantido = pedidos[0]
                    logger.info(f"  ✅ MANTER: Pedido ID {pedido_mantido.id} - Num: {pedido_mantido.num_pedido} - Criado: {pedido_mantido.criado_em}")
                    
                    # Mostrar detalhes do pedido que será mantido
                    logger.info(f"     Status: {pedido_mantido.status} | NF: {pedido_mantido.nf or 'Sem NF'}")
                    logger.info(f"     Expedição: {pedido_mantido.expedicao} | Agendamento: {pedido_mantido.agendamento}")
                    
                    # Identificar os duplicados
                    for pedido_duplicado in pedidos[1:]:
                        total_duplicados += 1
                        if dry_run:
                            logger.info(f"  ❌ REMOVER (dry-run): Pedido ID {pedido_duplicado.id} - Num: {pedido_duplicado.num_pedido}")
                            logger.info(f"     Status: {pedido_duplicado.status} | NF: {pedido_duplicado.nf or 'Sem NF'}")
                        else:
                            logger.info(f"  ❌ REMOVENDO: Pedido ID {pedido_duplicado.id}")
                            db.session.delete(pedido_duplicado)
                
                if not dry_run:
                    db.session.commit()
                    logger.info(f"\n✅ {total_duplicados} pedidos duplicados removidos com sucesso!")
                else:
                    logger.info(f"\n📊 RESUMO: {total_duplicados} pedidos seriam removidos")
            else:
                logger.info("✅ Nenhum pedido duplicado encontrado")
            
            # 2. Aplicar constraint única (se ainda não existir)
            logger.info("\n📝 Verificando constraint única...")
            
            if dry_run:
                # Verificar se constraint já existe
                constraint_exists = db.session.execute(text("""
                    SELECT COUNT(*) 
                    FROM information_schema.table_constraints 
                    WHERE constraint_name = 'uix_separacao_lote_id' 
                    AND table_name = 'pedidos'
                """)).scalar()
                
                if constraint_exists:
                    logger.info("  ℹ️  Constraint única já existe (não será criada novamente)")
                else:
                    logger.info("  🔧 Constraint única SERIA criada: uix_separacao_lote_id")
            else:
                try:
                    db.session.execute(text("""
                        ALTER TABLE pedidos 
                        ADD CONSTRAINT uix_separacao_lote_id 
                        UNIQUE (separacao_lote_id)
                    """))
                    db.session.commit()
                    logger.info("  ✅ Constraint única aplicada com sucesso!")
                except Exception as e:
                    if "already exists" in str(e):
                        logger.info("  ℹ️  Constraint única já existe")
                    else:
                        logger.error(f"  ❌ Erro ao aplicar constraint: {e}")
                        db.session.rollback()
            
            # 3. Verificar integridade final
            logger.info("\n🔍 Verificação de integridade...")
            
            resultado = db.session.execute(text("""
                SELECT separacao_lote_id, COUNT(*) as qtd
                FROM pedidos
                WHERE separacao_lote_id IS NOT NULL
                GROUP BY separacao_lote_id
                HAVING COUNT(*) > 1
            """)).fetchall()
            
            if resultado:
                if dry_run:
                    logger.warning(f"\n⚠️  APÓS SIMULAÇÃO: Ainda existiriam {len(resultado)} lotes com duplicados")
                else:
                    logger.error(f"\n❌ AINDA EXISTEM {len(resultado)} LOTES COM DUPLICADOS!")
                for lote_id, qtd in resultado:
                    logger.error(f"  Lote {lote_id}: {qtd} pedidos")
            else:
                if dry_run:
                    logger.info("\n✅ Após simulação: Nenhum duplicado restaria!")
                else:
                    logger.info("\n✅ Verificação concluída: Nenhum duplicado encontrado!")
                
            # Contar total de pedidos
            total = Pedido.query.count()
            logger.info(f"\n📊 Total de pedidos no sistema: {total}")
            
            # Estatísticas finais
            if dry_run:
                logger.info("\n" + "=" * 60)
                logger.info("🏁 FIM DO DRY RUN - Nenhuma alteração foi feita")
                logger.info("Para executar as correções, rode:")
                logger.info("  python fix_pedidos_duplicados.py")
                logger.info("=" * 60)
            else:
                logger.info("\n" + "=" * 60)
                logger.info("🏁 EXECUÇÃO CONCLUÍDA COM SUCESSO")
                logger.info("=" * 60)
            
        except Exception as e:
            logger.error(f"Erro geral: {e}")
            db.session.rollback()
            raise

def investigar_separacoes_ausentes():
    """Investiga separações com status ABERTO que não aparecem na Carteira"""
    app = create_app()
    
    with app.app_context():
        logger.info("\n=== INVESTIGAÇÃO DE SEPARAÇÕES AUSENTES NA CARTEIRA ===\n")
        
        # 1. Buscar todas as separações com pedidos ABERTO
        separacoes_aberto = db.session.query(
            Separacao.num_pedido,
            Separacao.separacao_lote_id,
            Pedido.status,
            func.count(Separacao.id).label('qtd_itens')
        ).join(
            Pedido, and_(
                Separacao.separacao_lote_id == Pedido.separacao_lote_id,
                Separacao.num_pedido == Pedido.num_pedido
            )
        ).filter(
            Pedido.status == 'ABERTO'
        ).group_by(
            Separacao.num_pedido,
            Separacao.separacao_lote_id,
            Pedido.status
        ).all()
        
        logger.info(f"Total de separações com status ABERTO: {len(separacoes_aberto)}")
        logger.info("\nDetalhes das separações ABERTO:")
        for sep in separacoes_aberto:
            logger.info(f"  - Pedido: {sep.num_pedido}, Lote: {sep.separacao_lote_id}, Itens: {sep.qtd_itens}")
        
        # 2. Verificar quais desses pedidos estão na CarteiraPrincipal
        logger.info("\n--- VERIFICANDO PRESENÇA NA CARTEIRA ---")
        
        pedidos_ausentes = []
        pedidos_presentes = []
        pedidos_standby = []
        
        for sep in separacoes_aberto:
            # Verificar se existe na CarteiraPrincipal
            carteira_count = CarteiraPrincipal.query.filter_by(
                num_pedido=sep.num_pedido,
                ativo=True
            ).count()
            
            # Verificar se está em StandBy
            standby = SaldoStandby.query.filter(
                SaldoStandby.num_pedido == sep.num_pedido,
                SaldoStandby.status_standby.in_(['ATIVO', 'BLOQ. COML.', 'SALDO'])
            ).first()
            
            if carteira_count == 0:
                pedidos_ausentes.append(sep.num_pedido)
                logger.warning(f"\n❌ PEDIDO AUSENTE NA CARTEIRA: {sep.num_pedido}")
                logger.warning(f"   Lote: {sep.separacao_lote_id}")
                
                # Verificar se existiu mas foi inativado
                carteira_inativo = CarteiraPrincipal.query.filter_by(
                    num_pedido=sep.num_pedido,
                    ativo=False
                ).first()
                
                if carteira_inativo:
                    logger.warning(f"   ⚠️  Pedido existe mas está INATIVO na CarteiraPrincipal")
                else:
                    logger.warning(f"   ⚠️  Pedido NÃO EXISTE na CarteiraPrincipal")
                    
            elif standby:
                pedidos_standby.append(sep.num_pedido)
                logger.info(f"\n⏸️  PEDIDO EM STANDBY: {sep.num_pedido}")
                logger.info(f"   Status StandBy: {standby.status_standby}")
                logger.info(f"   Lote: {sep.separacao_lote_id}")
            else:
                pedidos_presentes.append(sep.num_pedido)
                logger.info(f"✅ Pedido {sep.num_pedido} está presente e ativo na Carteira")
        
        # 3. Resumo
        logger.info("\n=== RESUMO DA INVESTIGAÇÃO ===")
        logger.info(f"Total de separações ABERTO: {len(separacoes_aberto)}")
        logger.info(f"Presentes na Carteira: {len(pedidos_presentes)}")
        logger.info(f"Em StandBy: {len(pedidos_standby)}")
        logger.info(f"AUSENTES NA CARTEIRA: {len(pedidos_ausentes)}")
        
        if pedidos_ausentes:
            logger.warning(f"\n🔴 PEDIDOS QUE PRECISAM SER CORRIGIDOS:")
            for pedido in pedidos_ausentes:
                logger.warning(f"   - {pedido}")
                
            # Propor correção
            logger.info("\n--- PROPOSTA DE CORREÇÃO ---")
            logger.info("Para cada pedido ausente, verificar:")
            logger.info("1. Se foi removido da CarteiraPrincipal por algum motivo")
            logger.info("2. Se precisa ser reativado (ativo=True)")
            logger.info("3. Se precisa ser recriado na CarteiraPrincipal")
            
            resposta = input("\nDeseja tentar reativar pedidos inativos? (s/n): ")
            
            if resposta.lower() == 's':
                for pedido in pedidos_ausentes:
                    # Tentar reativar
                    carteira_items = CarteiraPrincipal.query.filter_by(
                        num_pedido=pedido,
                        ativo=False
                    ).all()
                    
                    if carteira_items:
                        logger.info(f"\n🔧 Reativando {len(carteira_items)} itens do pedido {pedido}...")
                        for item in carteira_items:
                            item.ativo = True
                        db.session.commit()
                        logger.info(f"   ✅ Pedido {pedido} reativado!")
                    else:
                        logger.warning(f"\n⚠️  Pedido {pedido} não encontrado para reativar")
                        logger.warning(f"   Este pedido precisa ser recriado ou importado novamente")

if __name__ == "__main__":
    # Verificar argumentos da linha de comando
    if len(sys.argv) > 1:
        if sys.argv[1] == '--investigar':
            investigar_separacoes_ausentes()
        elif sys.argv[1] == '--dry-run':
            limpar_pedidos_duplicados(dry_run=True)
        elif sys.argv[1] == '--execute':
            # Confirmar execução
            print("\n" + "⚠️ " * 20)
            print("⚠️  ATENÇÃO: Este script IRÁ MODIFICAR O BANCO DE DADOS!")
            print("⚠️  Pedidos duplicados serão REMOVIDOS permanentemente!")
            print("⚠️ " * 20)
            confirmacao = input("\nDigite 'CONFIRMAR' para prosseguir: ")
            if confirmacao != 'CONFIRMAR':
                print("❌ Execução cancelada pelo usuário")
                sys.exit(0)
            limpar_pedidos_duplicados(dry_run=False)
        else:
            print("Uso:")
            print("  python fix_pedidos_duplicados.py --investigar  # Investigar separações ausentes")
            print("  python fix_pedidos_duplicados.py --dry-run     # Simular correção")
            print("  python fix_pedidos_duplicados.py --execute     # Executar correções")
            sys.exit(1)
    else:
        # Por padrão, mostrar ajuda
        print("Uso:")
        print("  python fix_pedidos_duplicados.py --investigar  # Investigar separações ausentes")
        print("  python fix_pedidos_duplicados.py --dry-run     # Simular correção") 
        print("  python fix_pedidos_duplicados.py --execute     # Executar correções")