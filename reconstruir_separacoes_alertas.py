#!/usr/bin/env python3
"""
Script para reconstruir Separações deletadas usando dados dos Alertas e Pedidos.

Este script:
1. Busca alertas de separações que foram alteradas/removidas
2. Usa os dados do Pedido (que permaneceram intactos) para preencher campos gerais
3. Usa os dados do alerta (produtos e quantidades) para reconstruir os itens
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.pedidos.models import Pedido
from app.separacao.models import Separacao
from app.carteira.models_alertas import AlertaSeparacaoCotada
from app.producao.models import CadastroPalletizacao
from datetime import datetime
from sqlalchemy import and_, or_
from decimal import Decimal

def reconstruir_separacoes():
    """Reconstrói separações usando alertas e dados do pedido."""
    app = create_app()
    
    with app.app_context():
        print("\n" + "="*60)
        print("🔧 RECONSTRUÇÃO DE SEPARAÇÕES VIA ALERTAS")
        print("="*60)
        
        # 1. Buscar alertas únicos por lote (separações que foram alteradas)
        print("\n📋 Buscando alertas de separações alteradas...")
        
        # Buscar lotes únicos dos alertas
        lotes_alertas = db.session.query(
            AlertaSeparacaoCotada.separacao_lote_id,
            AlertaSeparacaoCotada.num_pedido
        ).filter(
            AlertaSeparacaoCotada.separacao_lote_id.isnot(None)
        ).distinct().all()
        
        print(f"✅ Encontrados {len(lotes_alertas)} lotes com alertas")
        
        if not lotes_alertas:
            print("⚠️ Nenhum alerta encontrado para processar")
            return
        
        lotes_reconstruidos = 0
        lotes_ja_existentes = 0
        lotes_sem_pedido = 0
        
        for lote_id, num_pedido in lotes_alertas:
            print(f"\n📦 Processando lote {lote_id} (pedido {num_pedido})...")
            
            # Verificar se já existe Separacao para este lote
            separacao_existe = Separacao.query.filter_by(
                separacao_lote_id=lote_id
            ).first()
            
            if separacao_existe:
                print(f"  ⚠️ Lote {lote_id} já tem Separação - pulando")
                lotes_ja_existentes += 1
                continue
            
            # Buscar dados do Pedido pelo separacao_lote_id (vínculo principal)
            pedido = Pedido.query.filter_by(
                separacao_lote_id=lote_id
            ).first()
            
            if not pedido:
                print(f"  ❌ Pedido não encontrado para lote {lote_id}")
                print(f"     (Tentou buscar Pedido com separacao_lote_id = '{lote_id}')")
                lotes_sem_pedido += 1
                continue
            
            print(f"  📋 Pedido encontrado: {pedido.num_pedido} (status: {pedido.status})")
            
            # Buscar todos os alertas deste lote para reconstruir produtos
            # O vínculo é pelo separacao_lote_id
            alertas_produtos = AlertaSeparacaoCotada.query.filter_by(
                separacao_lote_id=lote_id
            ).all()
            
            if not alertas_produtos:
                print(f"  ⚠️ Nenhum produto nos alertas para lote {lote_id}")
                continue
            
            # Agrupar produtos únicos (pode ter múltiplos alertas do mesmo produto)
            produtos_map = {}
            for alerta in alertas_produtos:
                if alerta.cod_produto and alerta.cod_produto != 'TODOS':
                    # Usar qtd_anterior (quantidade original antes da alteração)
                    if alerta.cod_produto not in produtos_map:
                        produtos_map[alerta.cod_produto] = {
                            'nome': alerta.nome_produto or f'Produto {alerta.cod_produto}',
                            'qtd': float(alerta.qtd_anterior or 0),
                            'tipo_alteracao': alerta.tipo_alteracao
                        }
                    else:
                        # Se já existe, pegar a maior quantidade (mais conservador)
                        qtd_atual = produtos_map[alerta.cod_produto]['qtd']
                        qtd_alerta = float(alerta.qtd_anterior or 0)
                        if qtd_alerta > qtd_atual:
                            produtos_map[alerta.cod_produto]['qtd'] = qtd_alerta
            
            if not produtos_map:
                print(f"  ⚠️ Nenhum produto válido para reconstruir no lote {lote_id}")
                continue
            
            print(f"  📦 Reconstruindo {len(produtos_map)} produtos...")
            
            # Criar Separações para cada produto
            itens_criados = 0
            for cod_produto, info in produtos_map.items():
                if info['qtd'] <= 0:
                    continue
                
                # Buscar palletização do produto
                palletizacao = CadastroPalletizacao.query.filter_by(
                    cod_produto=cod_produto
                ).first()
                
                # Calcular pallets
                qtd_pallets = 0
                if palletizacao and palletizacao.palletizacao and palletizacao.palletizacao > 0:
                    qtd_pallets = info['qtd'] / float(palletizacao.palletizacao)
                
                # Criar nova Separacao com dados do Pedido + produto do alerta
                nova_separacao = Separacao(
                    # Identificação
                    separacao_lote_id=lote_id,
                    num_pedido=pedido.num_pedido,
                    
                    # Produto (do alerta)
                    cod_produto=cod_produto,
                    nome_produto=info['nome'],
                    qtd_saldo=info['qtd'],
                    
                    # Cliente (do pedido)
                    cnpj_cpf=pedido.cnpj_cpf,
                    raz_social_red=pedido.raz_social_red,
                    nome_cidade=pedido.nome_cidade or pedido.cidade_normalizada,
                    cod_uf=pedido.cod_uf or pedido.uf_normalizada,
                    
                    # Datas (do pedido)
                    data_pedido=pedido.data_pedido,
                    expedicao=pedido.expedicao,
                    agendamento=pedido.agendamento,
                    protocolo=pedido.protocolo,
                    
                    # Valores estimados (baseado em quantidade)
                    valor_saldo=info['qtd'] * 10,  # Valor estimado
                    peso=info['qtd'] * 1,  # Peso estimado
                    pallet=qtd_pallets,
                    
                    # Operacional
                    tipo_envio='total',
                    observ_ped_1=f'Reconstruído via alerta - {info["tipo_alteracao"]}',
                    
                    # Transportadora (do pedido se houver)
                    roteirizacao=pedido.transportadora,
                    
                    # Timestamps
                    criado_em=datetime.utcnow()
                )
                
                db.session.add(nova_separacao)
                itens_criados += 1
                print(f"    ✅ {cod_produto}: {info['qtd']:.2f} unidades")
            
            if itens_criados > 0:
                print(f"  ✅ Lote {lote_id} reconstruído com {itens_criados} itens")
                lotes_reconstruidos += 1
            else:
                print(f"  ⚠️ Nenhum item criado para lote {lote_id}")
        
        # Commit das alterações
        if lotes_reconstruidos > 0:
            print("\n💾 Salvando alterações...")
            db.session.commit()
            print("✅ Alterações salvas com sucesso!")
        
        # Resumo final
        print("\n" + "="*60)
        print("📊 RESUMO DA RECONSTRUÇÃO:")
        print("="*60)
        print(f"✅ Lotes reconstruídos: {lotes_reconstruidos}")
        print(f"⚠️ Lotes já existentes: {lotes_ja_existentes}")
        print(f"❌ Lotes sem pedido: {lotes_sem_pedido}")
        print(f"📋 Total de lotes processados: {len(lotes_alertas)}")
        
        # Verificar resultado
        if lotes_reconstruidos > 0:
            print("\n✅ SUCESSO: Separações reconstruídas!")
            print("   Verifique no sistema se os dados estão corretos")
        else:
            print("\n⚠️ Nenhuma separação foi reconstruída")
            if lotes_ja_existentes > 0:
                print("   A maioria dos lotes já tinha separação")

def listar_alertas_disponiveis():
    """Lista os alertas disponíveis para análise."""
    app = create_app()
    
    with app.app_context():
        print("\n📋 ALERTAS DISPONÍVEIS PARA RECONSTRUÇÃO:")
        print("-" * 60)
        
        # Buscar alertas agrupados por lote
        alertas = db.session.query(
            AlertaSeparacaoCotada.separacao_lote_id,
            AlertaSeparacaoCotada.num_pedido,
            db.func.count(AlertaSeparacaoCotada.id).label('total_alertas'),
            db.func.min(AlertaSeparacaoCotada.data_alerta).label('primeira_alteracao'),
            db.func.max(AlertaSeparacaoCotada.data_alerta).label('ultima_alteracao')
        ).group_by(
            AlertaSeparacaoCotada.separacao_lote_id,
            AlertaSeparacaoCotada.num_pedido
        ).all()
        
        for lote, pedido, total, primeira, ultima in alertas:
            # Verificar se tem Separacao
            tem_separacao = Separacao.query.filter_by(
                separacao_lote_id=lote
            ).first() is not None
            
            status_sep = "✅ Tem Separação" if tem_separacao else "❌ SEM Separação"
            
            print(f"\nLote: {lote}")
            print(f"  Pedido: {pedido}")
            print(f"  Status: {status_sep}")
            print(f"  Total alertas: {total}")
            print(f"  Primeira alteração: {primeira}")
            print(f"  Última alteração: {ultima}")

def main():
    """Função principal."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Reconstruir separações usando alertas')
    parser.add_argument('--listar', action='store_true', 
                       help='Apenas listar alertas disponíveis')
    parser.add_argument('--confirmar', action='store_true',
                       help='Confirmar reconstrução (sem isso, apenas simula)')
    
    args = parser.parse_args()
    
    try:
        if args.listar:
            listar_alertas_disponiveis()
        else:
            if not args.confirmar:
                print("\n⚠️ MODO SIMULAÇÃO - Use --confirmar para executar de verdade")
                print("   As alterações NÃO serão salvas no banco\n")
            
            reconstruir_separacoes()
            
        print("\n✅ Script executado com sucesso")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Erro durante execução: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()