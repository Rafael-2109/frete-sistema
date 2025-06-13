#!/usr/bin/env python3
"""
Script para resetar um pedido específico para status "Aberto"
- Remove vinculação com cotação
- Remove transportadora
- Permite especificar o número do pedido
"""

import sys
import os
from datetime import datetime

# Adiciona o diretório raiz ao path para importar os módulos da aplicação
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.pedidos.models import Pedido

def resetar_pedido(numero_pedido):
    """Reseta um pedido específico para status Aberto"""
    app = create_app()
    
    with app.app_context():
        print(f"🔧 RESETAR PEDIDO {numero_pedido} PARA STATUS 'ABERTO'")
        print("=" * 60)
        print(f"Iniciado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        print()
        
        # Busca o pedido (converte para string pois num_pedido é VARCHAR)
        pedido = Pedido.query.filter_by(num_pedido=str(numero_pedido)).first()
        
        if not pedido:
            print(f"❌ Pedido {numero_pedido} não encontrado!")
            return False
        
        print(f"📋 Pedido encontrado:")
        print(f"   • Número: {pedido.num_pedido}")
        print(f"   • Cliente: {pedido.raz_social_red}")
        print(f"   • CNPJ: {pedido.cnpj_cpf}")
        print(f"   • Valor: R$ {pedido.valor_saldo_total:,.2f}")
        print(f"   • Peso: {pedido.peso_total} kg")
        print(f"   • Lote Separação: {pedido.separacao_lote_id}")
        
        # Verifica status atual
        status_atual = []
        if pedido.cotacao_id:
            status_atual.append(f"Cotação ID: {pedido.cotacao_id}")
        if pedido.transportadora:
            status_atual.append(f"Transportadora: {pedido.transportadora}")
        
        if not status_atual:
            print(f"✅ Pedido {numero_pedido} já está com status 'Aberto'")
            return True
        
        print(f"   • Status atual: {', '.join(status_atual)}")
        print()
        
        # Confirma a operação
        resposta = input(f"⚠️  Confirma o reset do pedido {numero_pedido} para status 'Aberto'?\n"
                        f"   - Remove cotacao_id: {pedido.cotacao_id}\n"
                        f"   - Remove transportadora: {pedido.transportadora}\n"
                        f"   - Pedido voltará ao status 'Aberto'\n\n"
                        f"Digite 'SIM' para confirmar: ")
        
        if resposta.upper() != 'SIM':
            print("❌ Operação cancelada pelo usuário.")
            return False
        
        # Executa o reset
        print(f"\n🔄 Resetando pedido {numero_pedido}...")
        
        # Salva valores antigos para log
        cotacao_antiga = pedido.cotacao_id
        transportadora_antiga = pedido.transportadora
        
        # Remove vinculações
        pedido.cotacao_id = None
        pedido.transportadora = None
        
        print(f"   ✅ cotacao_id: {cotacao_antiga} → None")
        print(f"   ✅ transportadora: {transportadora_antiga} → None")
        
        # Confirma salvamento
        confirma_salvar = input(f"\n💾 Confirma o salvamento das alterações? (digite 'CONFIRMAR'): ")
        
        if confirma_salvar.upper() == 'CONFIRMAR':
            try:
                db.session.commit()
                print(f"✅ Pedido {numero_pedido} resetado com sucesso para status 'Aberto'!")
                
                # Log da operação
                log_msg = (f"RESET PEDIDO {numero_pedido} - {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n"
                          f"Cliente: {pedido.raz_social_red}\n"
                          f"CNPJ: {pedido.cnpj_cpf}\n"
                          f"Cotação removida: {cotacao_antiga}\n"
                          f"Transportadora removida: {transportadora_antiga}\n"
                          f"Status: ABERTO\n")
                
                with open('log_reset_pedidos.txt', 'a', encoding='utf-8') as f:
                    f.write(log_msg + "\n" + "="*50 + "\n")
                
                print("📝 Log da operação salvo em 'log_reset_pedidos.txt'")
                return True
                
            except Exception as e:
                db.session.rollback()
                print(f"❌ Erro ao salvar alterações: {str(e)}")
                print("🔄 Alterações revertidas.")
                return False
        else:
            db.session.rollback()
            print("❌ Operação cancelada. Nenhuma alteração foi salva.")
            return False

def main():
    """Função principal do script"""
    print("🔧 SCRIPT DE RESET DE PEDIDO ESPECÍFICO")
    print("=" * 60)
    
    # Verifica se foi passado número do pedido como argumento
    if len(sys.argv) > 1:
        numero_pedido = sys.argv[1]
    else:
        # Solicita o número do pedido
        numero_pedido = input("📋 Digite o número do pedido para resetar: ").strip()
    
    if not numero_pedido:
        print("❌ Número do pedido não informado!")
        return
    
    # Garante que o número do pedido seja tratado como string
    # pois o campo num_pedido no banco é VARCHAR
    numero_pedido = str(numero_pedido).strip()
    
    print(f"\n🎯 Processando pedido: {numero_pedido}")
    print()
    
    sucesso = resetar_pedido(numero_pedido)
    
    if sucesso:
        print(f"\n🎉 Operação concluída com sucesso!")
    else:
        print(f"\n❌ Operação não realizada.")
    
    print(f"\n🏁 Script finalizado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ Script interrompido pelo usuário (Ctrl+C)")
    except Exception as e:
        print(f"\n❌ Erro inesperado: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        print("\n👋 Encerrando script...") 