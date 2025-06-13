#!/usr/bin/env python3
"""
Script simples para resetar pedido para status "Aberto"
- Foca apenas nos campos essenciais: cotacao_id e transportadora
- Não mexe com nf_cd ou outros campos complexos
"""

import sys
import os
from datetime import datetime

# Adiciona o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.pedidos.models import Pedido

def resetar_pedido_simples(numero_pedido):
    """Reseta um pedido para status Aberto de forma simples"""
    app = create_app()
    
    with app.app_context():
        print(f"🔧 RESETAR PEDIDO {numero_pedido} - VERSÃO SIMPLES")
        print("=" * 50)
        print(f"Executado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        print()
        
        # Busca o pedido
        pedido = Pedido.query.filter_by(num_pedido=str(numero_pedido)).first()
        
        if not pedido:
            print(f"❌ Pedido {numero_pedido} não encontrado!")
            return False
        
        print(f"📋 DADOS DO PEDIDO:")
        print(f"   • Número: {pedido.num_pedido}")
        print(f"   • Cliente: {pedido.raz_social_red}")
        print(f"   • CNPJ: {pedido.cnpj_cpf}")
        print()
        
        print(f"🔍 CAMPOS ATUAIS:")
        print(f"   • cotacao_id: {pedido.cotacao_id}")
        print(f"   • transportadora: '{pedido.transportadora}'")
        print(f"   • nf: '{pedido.nf}'")
        print(f"   • data_embarque: {pedido.data_embarque}")
        print()
        
        # Verifica se já está "aberto"
        if not pedido.cotacao_id and not pedido.transportadora and not pedido.nf and not pedido.data_embarque:
            print("✅ Pedido já está com status 'Aberto' (todos os campos limpos)")
            return True
        
        # Mostra o que será alterado
        print("🔄 ALTERAÇÕES QUE SERÃO FEITAS:")
        if pedido.cotacao_id:
            print(f"   • cotacao_id: {pedido.cotacao_id} → None")
        if pedido.transportadora:
            print(f"   • transportadora: '{pedido.transportadora}' → None")
        if pedido.nf:
            print(f"   • nf: '{pedido.nf}' → None")
        if pedido.data_embarque:
            print(f"   • data_embarque: {pedido.data_embarque} → None")
        print()
        
        # Confirma a operação
        resposta = input("⚠️  Confirma o reset? (digite 'SIM'): ")
        
        if resposta.upper() != 'SIM':
            print("❌ Operação cancelada.")
            return False
        
        # Salva valores antigos para log
        cotacao_antiga = pedido.cotacao_id
        transportadora_antiga = pedido.transportadora
        nf_antiga = pedido.nf
        data_embarque_antiga = pedido.data_embarque
        
        # Executa o reset - TODOS os campos que afetam o status
        print(f"\n🔄 Executando reset...")
        pedido.cotacao_id = None
        pedido.transportadora = None
        pedido.nf = None
        pedido.data_embarque = None
        
        print(f"   ✅ cotacao_id: {cotacao_antiga} → None")
        print(f"   ✅ transportadora: '{transportadora_antiga}' → None")
        print(f"   ✅ nf: '{nf_antiga}' → None")
        print(f"   ✅ data_embarque: {data_embarque_antiga} → None")
        
        # Confirma salvamento
        confirma = input(f"\n💾 Salvar alterações? (digite 'SALVAR'): ")
        
        if confirma.upper() == 'SALVAR':
            try:
                db.session.commit()
                print(f"\n✅ SUCESSO! Pedido {numero_pedido} resetado!")
                
                # Verifica o status após o reset
                try:
                    novo_status = pedido.status_calculado
                    print(f"📊 Novo status: {novo_status}")
                except:
                    print(f"📊 Status: Campos básicos limpos (cotacao_id=None, transportadora=None)")
                
                # Log simples
                log_msg = (f"RESET COMPLETO - {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n"
                          f"Pedido: {numero_pedido}\n"
                          f"Cliente: {pedido.raz_social_red}\n"
                          f"cotacao_id: {cotacao_antiga} → None\n"
                          f"transportadora: '{transportadora_antiga}' → None\n"
                          f"nf: '{nf_antiga}' → None\n"
                          f"data_embarque: {data_embarque_antiga} → None\n\n")
                
                with open('log_reset_pedidos.txt', 'a', encoding='utf-8') as f:
                    f.write(log_msg)
                
                print("📝 Log salvo em 'log_reset_pedidos.txt'")
                return True
                
            except Exception as e:
                db.session.rollback()
                print(f"❌ ERRO ao salvar: {str(e)}")
                return False
        else:
            db.session.rollback()
            print("❌ Salvamento cancelado.")
            return False

def main():
    """Função principal"""
    print("🔧 SCRIPT DE RESET SIMPLES")
    print("=" * 50)
    
    # Verifica se foi passado número do pedido como argumento
    if len(sys.argv) > 1:
        numero_pedido = sys.argv[1]
    else:
        numero_pedido = input("📋 Digite o número do pedido: ").strip()
    
    if not numero_pedido:
        print("❌ Número do pedido não informado!")
        return
    
    numero_pedido = str(numero_pedido).strip()
    
    print(f"\n🎯 Processando pedido: {numero_pedido}")
    print()
    
    sucesso = resetar_pedido_simples(numero_pedido)
    
    if sucesso:
        print(f"\n🎉 Reset concluído!")
    else:
        print(f"\n❌ Reset não realizado.")
    
    print(f"\n🏁 Finalizado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ Interrompido pelo usuário")
    except Exception as e:
        print(f"\n❌ Erro: {str(e)}")
        import traceback
        traceback.print_exc() 