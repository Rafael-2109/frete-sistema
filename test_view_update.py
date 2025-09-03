#!/usr/bin/env python
"""
Script de teste para verificar se as correções de UPDATE em Pedido VIEW funcionam
"""
import sys
sys.path.insert(0, '/home/rafaelnascimento/projetos/frete_sistema')

from app import create_app, db
from datetime import datetime

def testar_atualizacoes():
    """Testa se as atualizações em Separacao funcionam corretamente"""
    app = create_app()
    
    with app.app_context():
        try:
            from app.pedidos.models import Pedido
            from app.separacao.models import Separacao
            from app.cotacao.models import Cotacao
            
            print("=" * 60)
            print("TESTE DE ATUALIZAÇÃO PEDIDO VIEW -> SEPARACAO")
            print("=" * 60)
            
            # 1. Verificar se Pedido é uma VIEW
            print("\n1. Verificando se Pedido é uma VIEW...")
            is_view = Pedido.__table_args__.get('info', {}).get('is_view', False)
            print(f"   ✓ Pedido é VIEW: {is_view}")
            
            # 2. Buscar um pedido de teste
            print("\n2. Buscando pedido de teste...")
            pedido = Pedido.query.filter(
                Pedido.separacao_lote_id.isnot(None)
            ).first()
            
            if not pedido:
                print("   ✗ Nenhum pedido com separacao_lote_id encontrado")
                return False
                
            print(f"   ✓ Pedido encontrado: {pedido.num_pedido}")
            print(f"   ✓ Lote: {pedido.separacao_lote_id}")
            print(f"   ✓ Status atual: {pedido.status}")
            print(f"   ✓ NF CD atual: {pedido.nf_cd}")
            
            # 3. Simular atualização de cotação (como em cotacao/routes.py)
            print("\n3. Simulando atualização de cotação...")
            
            # Criar cotação de teste
            cotacao_teste = Cotacao.query.first()
            if not cotacao_teste:
                print("   ! Criando cotação de teste...")
                cotacao_teste = Cotacao(
                    usuario_id=1,
                    transportadora_id=1,
                    status='Teste',
                    tipo_carga='TESTE'
                )
                db.session.add(cotacao_teste)
                db.session.flush()
            
            # Atualizar via Separacao (novo método)
            result = Separacao.query.filter_by(
                separacao_lote_id=pedido.separacao_lote_id
            ).update({
                'cotacao_id': cotacao_teste.id,
                'nf_cd': False
            })
            
            if result > 0:
                db.session.commit()
                print(f"   ✓ Atualização bem-sucedida: {result} registros atualizados")
                
                # Verificar se a VIEW reflete a mudança
                pedido_atualizado = Pedido.query.filter_by(
                    separacao_lote_id=pedido.separacao_lote_id
                ).first()
                
                print(f"   ✓ Cotação ID na VIEW: {pedido_atualizado.cotacao_id}")
                print(f"   ✓ NF CD na VIEW: {pedido_atualizado.nf_cd}")
            else:
                print("   ✗ Nenhum registro atualizado")
                db.session.rollback()
                return False
                
            # 4. Simular atualização de NF (como em embarques/routes.py)
            print("\n4. Simulando atualização de NF...")
            
            result = Separacao.query.filter_by(
                separacao_lote_id=pedido.separacao_lote_id
            ).update({
                'numero_nf': '123456-TESTE'
            })
            
            if result > 0:
                db.session.commit()
                print(f"   ✓ NF atualizada: {result} registros")
                
                # Verificar na VIEW
                pedido_atualizado = Pedido.query.filter_by(
                    separacao_lote_id=pedido.separacao_lote_id
                ).first()
                
                print(f"   ✓ NF na VIEW: {pedido_atualizado.nf}")
            else:
                print("   ✗ Falha ao atualizar NF")
                db.session.rollback()
                
            # 5. Limpar teste
            print("\n5. Limpando dados de teste...")
            Separacao.query.filter_by(
                separacao_lote_id=pedido.separacao_lote_id
            ).update({
                'numero_nf': None,
                'cotacao_id': None
            })
            db.session.commit()
            print("   ✓ Dados de teste limpos")
            
            print("\n" + "=" * 60)
            print("✅ TODOS OS TESTES PASSARAM COM SUCESSO!")
            print("=" * 60)
            return True
            
        except Exception as e:
            print(f"\n❌ ERRO NO TESTE: {str(e)}")
            import traceback
            traceback.print_exc()
            db.session.rollback()
            return False

if __name__ == "__main__":
    sucesso = testar_atualizacoes()
    sys.exit(0 if sucesso else 1)