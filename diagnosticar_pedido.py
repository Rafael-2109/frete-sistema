#!/usr/bin/env python3
"""
Script para diagnosticar o status de um pedido específico
- Mostra todos os campos relevantes para o status
- Identifica por que o pedido não está com status "Aberto"
- Permite resetar corretamente
"""

import sys
import os
from datetime import datetime

# Adiciona o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.pedidos.models import Pedido

def diagnosticar_pedido(numero_pedido):
    """Diagnostica completamente o status de um pedido"""
    app = create_app()
    
    with app.app_context():
        print(f"🔍 DIAGNÓSTICO COMPLETO DO PEDIDO {numero_pedido}")
        print("=" * 60)
        print(f"Executado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        print()
        
        # Busca o pedido
        pedido = Pedido.query.filter_by(num_pedido=str(numero_pedido)).first()
        
        if not pedido:
            print(f"❌ Pedido {numero_pedido} não encontrado!")
            return False
        
        print(f"📋 DADOS BÁSICOS:")
        print(f"   • ID: {pedido.id}")
        print(f"   • Número: {pedido.num_pedido}")
        print(f"   • Cliente: {pedido.raz_social_red}")
        print(f"   • CNPJ: {pedido.cnpj_cpf}")
        print(f"   • Valor: R$ {pedido.valor_saldo_total:,.2f}")
        print(f"   • Peso: {pedido.peso_total} kg")
        print(f"   • Lote Separação: {pedido.separacao_lote_id}")
        print()
        
        print(f"🔍 CAMPOS QUE AFETAM O STATUS:")
        print(f"   • cotacao_id: {pedido.cotacao_id}")
        print(f"   • transportadora: {pedido.transportadora}")
        print(f"   • nf: '{pedido.nf}'")
        print(f"   • data_embarque: {pedido.data_embarque}")
        
        # Verifica se o campo nf_cd existe
        try:
            nf_cd = getattr(pedido, 'nf_cd', None)
            print(f"   • nf_cd: {nf_cd}")
        except:
            print(f"   • nf_cd: Campo não existe no modelo")
        
        print(f"   • status (campo): {getattr(pedido, 'status', 'Campo não existe')}")
        print()
        
        print(f"📊 STATUS CALCULADO:")
        try:
            status_calc = pedido.status_calculado
            print(f"   • Status atual: {status_calc}")
            
            # Explica por que tem esse status
            if hasattr(pedido, 'nf_cd') and getattr(pedido, 'nf_cd', False):
                print(f"   • Motivo: NF está marcada como 'no CD' (nf_cd = True)")
            elif pedido.nf and pedido.nf.strip():
                print(f"   • Motivo: Tem NF preenchida ('{pedido.nf}')")
            elif pedido.data_embarque:
                print(f"   • Motivo: Tem data de embarque ({pedido.data_embarque})")
            elif pedido.cotacao_id:
                print(f"   • Motivo: Tem cotação vinculada (ID: {pedido.cotacao_id})")
            else:
                print(f"   • Motivo: Não tem cotação, embarque ou NF - deveria estar ABERTO")
                
        except Exception as e:
            print(f"   • Erro ao calcular status: {str(e)}")
        
        print()
        
        # Verifica se precisa de reset
        precisa_reset = False
        campos_para_limpar = []
        
        if pedido.cotacao_id:
            precisa_reset = True
            campos_para_limpar.append(f"cotacao_id: {pedido.cotacao_id} → None")
            
        if pedido.transportadora:
            precisa_reset = True
            campos_para_limpar.append(f"transportadora: '{pedido.transportadora}' → None")
            
        if pedido.nf and pedido.nf.strip():
            precisa_reset = True
            campos_para_limpar.append(f"nf: '{pedido.nf}' → None")
            
        if pedido.data_embarque:
            precisa_reset = True
            campos_para_limpar.append(f"data_embarque: {pedido.data_embarque} → None")
            
        if hasattr(pedido, 'nf_cd') and getattr(pedido, 'nf_cd', False):
            precisa_reset = True
            campos_para_limpar.append(f"nf_cd: True → False")
        
        if not precisa_reset:
            print("✅ PEDIDO JÁ ESTÁ COM STATUS 'ABERTO'!")
            print("   Não há campos que impeçam o status 'Aberto'.")
            return True
        
        print("🔧 AÇÕES NECESSÁRIAS PARA STATUS 'ABERTO':")
        for campo in campos_para_limpar:
            print(f"   • {campo}")
        print()
        
        # Pergunta se quer executar o reset
        resposta = input("⚠️  Deseja executar o reset para status 'Aberto'? (digite 'SIM'): ")
        
        if resposta.upper() != 'SIM':
            print("❌ Reset cancelado pelo usuário.")
            return False
        
        # Executa o reset
        print(f"\n🔄 Executando reset do pedido {numero_pedido}...")
        
        # Salva valores antigos para log
        valores_antigos = {
            'cotacao_id': pedido.cotacao_id,
            'transportadora': pedido.transportadora,
            'nf': pedido.nf,
            'data_embarque': pedido.data_embarque,
            'nf_cd': getattr(pedido, 'nf_cd', None)
        }
        
        # Limpa os campos
        pedido.cotacao_id = None
        pedido.transportadora = None
        pedido.nf = None
        pedido.data_embarque = None
        
        if hasattr(pedido, 'nf_cd'):
            pedido.nf_cd = False
        
        print("   ✅ Campos limpos:")
        for campo in campos_para_limpar:
            print(f"      • {campo}")
        
        # Confirma salvamento
        confirma = input(f"\n💾 Confirma o salvamento? (digite 'CONFIRMAR'): ")
        
        if confirma.upper() == 'CONFIRMAR':
            try:
                db.session.commit()
                print(f"\n✅ SUCESSO! Pedido {numero_pedido} resetado para status 'Aberto'!")
                
                # Verifica o novo status
                novo_status = pedido.status_calculado
                print(f"📊 Novo status: {novo_status}")
                
                # Log da operação
                log_msg = (f"RESET PEDIDO {numero_pedido} - {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n"
                          f"Cliente: {pedido.raz_social_red}\n"
                          f"CNPJ: {pedido.cnpj_cpf}\n")
                
                for campo, valor in valores_antigos.items():
                    if valor is not None and valor != '' and valor != False:
                        log_msg += f"{campo}: {valor} → None/False\n"
                
                log_msg += f"Novo status: {novo_status}\n"
                
                with open('log_reset_pedidos.txt', 'a', encoding='utf-8') as f:
                    f.write(log_msg + "\n" + "="*50 + "\n")
                
                print("📝 Log salvo em 'log_reset_pedidos.txt'")
                return True
                
            except Exception as e:
                db.session.rollback()
                print(f"❌ ERRO ao salvar: {str(e)}")
                print("🔄 Alterações revertidas.")
                return False
        else:
            db.session.rollback()
            print("❌ Salvamento cancelado. Alterações revertidas.")
            return False

def main():
    """Função principal do script"""
    print("🔍 SCRIPT DE DIAGNÓSTICO DE PEDIDO")
    print("=" * 60)
    
    # Verifica se foi passado número do pedido como argumento
    if len(sys.argv) > 1:
        numero_pedido = sys.argv[1]
    else:
        # Solicita o número do pedido
        numero_pedido = input("📋 Digite o número do pedido para diagnosticar: ").strip()
    
    if not numero_pedido:
        print("❌ Número do pedido não informado!")
        return
    
    # Garante que o número do pedido seja tratado como string
    numero_pedido = str(numero_pedido).strip()
    
    print(f"\n🎯 Diagnosticando pedido: {numero_pedido}")
    print()
    
    sucesso = diagnosticar_pedido(numero_pedido)
    
    if sucesso:
        print(f"\n🎉 Diagnóstico/Reset concluído com sucesso!")
    else:
        print(f"\n❌ Operação não realizada ou pedido já estava correto.")
    
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