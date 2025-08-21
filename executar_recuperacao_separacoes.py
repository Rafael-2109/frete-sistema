#!/usr/bin/env python
"""
Script de Execução - Recuperação de Separações Perdidas
========================================================

Este script recupera Separações que foram deletadas incorretamente.
Reconstrói as Separações usando dados de Pedidos FATURADOS e suas NFs.

Uso:
    python executar_recuperacao_separacoes.py [opções]

Exemplos:
    python executar_recuperacao_separacoes.py                 # Executa recuperação
    python executar_recuperacao_separacoes.py --dry-run       # Modo simulação
    python executar_recuperacao_separacoes.py --pedido P001   # Verifica pedido específico

Para agendar execução única:
    nohup python executar_recuperacao_separacoes.py > recuperacao.log 2>&1 &
"""

import sys
import argparse
import logging
from datetime import datetime

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(f'logs/recuperacao_separacoes_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
    ]
)

logger = logging.getLogger(__name__)


def main():
    """
    Função principal do script
    """
    # Parser de argumentos
    parser = argparse.ArgumentParser(
        description='Recupera Separações perdidas usando dados de NFs faturadas'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Executa em modo simulação (não salva alterações)'
    )
    parser.add_argument(
        '--pedido',
        type=str,
        help='Verifica/recupera pedido específico'
    )
    parser.add_argument(
        '--verificar',
        action='store_true',
        help='Apenas verifica quantos pedidos órfãos existem'
    )
    
    args = parser.parse_args()
    
    try:
        # Importar app e serviço
        from app import create_app, db
        from app.faturamento.services.recuperar_separacoes_perdidas import RecuperadorSeparacoesPerdidas
        
        # Criar contexto da aplicação
        app = create_app()
        
        with app.app_context():
            print("=" * 70)
            print("🔧 RECUPERAÇÃO DE SEPARAÇÕES PERDIDAS")
            print(f"📅 Data/Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print("=" * 70)
            
            if args.verificar:
                # Modo verificação - apenas conta pedidos órfãos
                logger.info("🔍 Modo verificação - contando pedidos órfãos...")
                
                from app.pedidos.models import Pedido
                
                # Contar pedidos que TÊM lote mas NÃO tem Separacao
                from app.separacao.models import Separacao
                
                pedidos_com_lote = Pedido.query.filter(
                    db.or_(
                        Pedido.status == 'FATURADO',
                        Pedido.status == 'NF no CD'
                    ),
                    Pedido.separacao_lote_id.isnot(None),
                    Pedido.separacao_lote_id != '',
                    Pedido.nf.isnot(None),
                    Pedido.nf != ''
                ).all()
                
                pedidos_orfaos = 0
                for pedido in pedidos_com_lote:
                    sep_existe = Separacao.query.filter_by(
                        separacao_lote_id=pedido.separacao_lote_id
                    ).first()
                    if not sep_existe:
                        pedidos_orfaos += 1
                
                pedidos_total = Pedido.query.filter(
                    db.or_(
                        Pedido.status == 'FATURADO',
                        Pedido.status == 'NF no CD'
                    )
                ).count()
                
                print(f"\n📊 RESULTADO DA VERIFICAÇÃO:")
                print(f"   Total de pedidos FATURADOS/NF no CD: {pedidos_total}")
                print(f"   Pedidos órfãos (sem separação): {pedidos_orfaos}")
                print(f"   Percentual órfão: {(pedidos_orfaos/pedidos_total*100):.1f}%" if pedidos_total > 0 else "0%")
                
                if pedidos_orfaos > 0:
                    print(f"\n⚠️ Existem {pedidos_orfaos} pedidos que podem ser recuperados")
                    print("   Execute sem --verificar para recuperar as separações")
                else:
                    print("\n✅ Sistema íntegro - nenhum pedido órfão encontrado")
                
                return 0
                
            elif args.pedido:
                # Verificar/recuperar pedido específico
                logger.info(f"🔍 Verificando pedido {args.pedido}...")
                
                resultado = RecuperadorSeparacoesPerdidas.verificar_pedido_especifico(args.pedido)
                
                print(f"\n📋 PEDIDO: {args.pedido}")
                print(f"   Status: {resultado['status']}")
                print(f"   Tem separação: {'SIM' if resultado['tem_separacao'] else 'NÃO'}")
                print(f"   Tem NF: {'SIM' if resultado['tem_nf'] else 'NÃO'}")
                
                if resultado['detalhes']:
                    print(f"   Cliente: {resultado['detalhes'].get('cliente', 'N/A')}")
                    print(f"   NF: {resultado['detalhes'].get('nf', 'N/A')}")
                    print(f"   Lote: {resultado['detalhes'].get('separacao_lote_id', 'N/A')}")
                    
                    if 'produtos_na_nf' in resultado['detalhes']:
                        print(f"   Produtos na NF: {resultado['detalhes']['produtos_na_nf']}")
                
                if resultado['pode_recuperar']:
                    print(f"\n✅ Este pedido PODE ser recuperado")
                    
                    if not args.dry_run:
                        resposta = input("\n🔄 Deseja recuperar este pedido agora? (s/n): ")
                        if resposta.lower() == 's':
                            from app.pedidos.models import Pedido
                            pedido = Pedido.query.filter_by(num_pedido=args.pedido).first()
                            
                            if pedido:
                                resultado_rec = RecuperadorSeparacoesPerdidas._recuperar_separacao_pedido(pedido)
                                if resultado_rec['sucesso']:
                                    db.session.commit()
                                    print(f"✅ Pedido recuperado com sucesso!")
                                    print(f"   Lote criado: {resultado_rec['lote_id']}")
                                    print(f"   Produtos: {resultado_rec['produtos_recuperados']}")
                                else:
                                    print(f"❌ Erro na recuperação: {resultado_rec.get('erro')}")
                    else:
                        print("   (Execute sem --dry-run para recuperar)")
                elif resultado['tem_separacao']:
                    print(f"\n✅ Este pedido já tem separação (lote: {resultado['detalhes'].get('separacao_lote_id')})")
                else:
                    print(f"\n❌ Este pedido NÃO pode ser recuperado")
                    if not resultado['tem_nf']:
                        print("   Motivo: Não tem NF associada")
                    elif resultado['status'] not in ['FATURADO', 'NF no CD']:
                        print(f"   Motivo: Status '{resultado['status']}' não é recuperável")
                
                return 0
                
            else:
                # Executar recuperação completa
                logger.info(f"🔄 Executando recuperação completa...")
                
                if args.dry_run:
                    print("\n⚠️ MODO SIMULAÇÃO - Nenhuma alteração será salva")
                    print("=" * 70)
                
                resultado = RecuperadorSeparacoesPerdidas.executar_recuperacao_completa(
                    modo_simulacao=args.dry_run
                )
                
                # Exibir resultados
                print("\n" + "=" * 70)
                if resultado['sucesso']:
                    if resultado['separacoes_criadas'] > 0:
                        print("✅ RECUPERAÇÃO CONCLUÍDA COM SUCESSO")
                        print(f"   📊 Pedidos analisados: {resultado['pedidos_analisados']}")
                        print(f"   🔍 Pedidos órfãos: {resultado['pedidos_orfaos']}")
                        print(f"   ✅ Separações criadas: {resultado['separacoes_criadas']}")
                        print(f"   📦 Produtos recuperados: {resultado['produtos_recuperados']}")
                        
                        if resultado['lotes_criados']:
                            print(f"\n🆔 Alguns lotes criados:")
                            for lote in resultado['lotes_criados'][:5]:
                                print(f"   - {lote}")
                        
                        if resultado['erros']:
                            print(f"\n⚠️ Erros encontrados: {len(resultado['erros'])}")
                            for erro in resultado['erros'][:3]:
                                print(f"   - {erro}")
                        
                        if args.dry_run:
                            print("\n⚠️ MODO SIMULAÇÃO - Nenhuma alteração foi salva")
                            print("   Execute sem --dry-run para aplicar as mudanças")
                    else:
                        print("✅ SISTEMA ÍNTEGRO")
                        print("   Nenhuma separação precisou ser recuperada")
                else:
                    print("❌ ERRO NA RECUPERAÇÃO")
                    print(f"   Erro: {resultado.get('erro_geral', 'Erro desconhecido')}")
                    if resultado['erros']:
                        print(f"\n   Erros detalhados:")
                        for erro in resultado['erros'][:5]:
                            print(f"   - {erro}")
                
                print("=" * 70)
                
                # Retornar código apropriado
                if resultado['sucesso']:
                    return 0
                else:
                    return 1
                
    except Exception as e:
        logger.error(f"❌ Erro fatal: {e}")
        import traceback
        logger.error(traceback.format_exc())
        print(f"\n❌ ERRO FATAL: {e}")
        print("Verifique o arquivo de log para mais detalhes")
        return 2


if __name__ == '__main__':
    sys.exit(main())