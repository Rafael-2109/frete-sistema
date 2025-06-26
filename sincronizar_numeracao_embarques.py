#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔧 SINCRONIZADOR DE NUMERAÇÃO DE EMBARQUES
Resolve dessincronização entre campo 'numero' e 'id' dos embarques

PROBLEMA IDENTIFICADO: Embarque #254 tem ID 278 (diferença de 24)

SOLUÇÕES DISPONÍVEIS:
1. AVANÇAR NÚMEROS: Próximos embarques terão números = IDs
2. REBOBINAR IDs: Resetar sequência de IDs para casar com números
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def analisar_situacao_atual():
    """Analisa a situação atual da numeração em produção"""
    print("🔍 ANÁLISE DA SITUAÇÃO ATUAL DOS EMBARQUES")
    print("=" * 60)
    
    try:
        from app import db, create_app
        from app.embarques.models import Embarque
        
        app = create_app()
        with app.app_context():
            # Estatísticas gerais
            total_embarques = Embarque.query.count()
            ultimo_id = db.session.query(db.func.max(Embarque.id)).scalar() or 0
            ultimo_numero = db.session.query(db.func.max(Embarque.numero)).scalar() or 0
            embarques_sem_numero = Embarque.query.filter(Embarque.numero.is_(None)).count()
            
            # Embarques com maior ID e número
            embarque_maior_id = Embarque.query.order_by(Embarque.id.desc()).first()
            embarque_maior_numero = Embarque.query.order_by(Embarque.numero.desc()).first()
            
            # Diferença atual
            diferenca = ultimo_id - ultimo_numero
            
            print(f"📊 ESTATÍSTICAS GERAIS:")
            print(f"   Total de embarques: {total_embarques}")
            print(f"   Maior ID: {ultimo_id}")
            print(f"   Maior número: {ultimo_numero}")
            print(f"   Diferença (ID - Número): {diferenca}")
            print(f"   Embarques sem número: {embarques_sem_numero}")
            print()
            
            if embarque_maior_id:
                print(f"🆔 EMBARQUE COM MAIOR ID:")
                print(f"   ID: {embarque_maior_id.id}")
                print(f"   Número: {embarque_maior_id.numero}")
                print(f"   Data: {embarque_maior_id.criado_em}")
                print(f"   Status: {embarque_maior_id.status}")
                print()
            
            if embarque_maior_numero:
                print(f"🔢 EMBARQUE COM MAIOR NÚMERO:")
                print(f"   ID: {embarque_maior_numero.id}")
                print(f"   Número: {embarque_maior_numero.numero}")
                print(f"   Data: {embarque_maior_numero.criado_em}")
                print(f"   Status: {embarque_maior_numero.status}")
                print()
            
            # Análise de inconsistências
            if diferenca > 0:
                print(f"⚠️ PROBLEMA DETECTADO:")
                print(f"   Os números estão {diferenca} valores ATRÁS dos IDs")
                print(f"   Próximo embarque seria: #{ultimo_numero + 1} com ID {ultimo_id + 1}")
                print(f"   Isso cria confusão para usuários e relatórios")
                print()
                
                # Calcular quanto seria "desperdiçado" em cada opção
                numeros_perdidos = diferenca
                ids_perdidos = ultimo_numero - ultimo_id if ultimo_numero > ultimo_id else 0
                
                print(f"💡 OPÇÕES DE CORREÇÃO:")
                print(f"   OPÇÃO 1 - AVANÇAR NÚMEROS:")
                print(f"     ✅ Próximo embarque: #{ultimo_id + 1} (pula {numeros_perdidos} números)")
                print(f"     ✅ ID e número sempre iguais daqui pra frente")
                print(f"     ⚠️ 'Desperdiça' números {ultimo_numero + 1} até {ultimo_id}")
                print(f"     ⚠️ Pode confundir usuários (saltou de #{ultimo_numero} para #{ultimo_id + 1})")
                print()
                print(f"   OPÇÃO 2 - REBOBINAR IDs (PostgreSQL):")
                print(f"     ✅ Próximo embarque: #{ultimo_numero + 1} com ID {ultimo_numero + 1}")
                print(f"     ✅ Mantém sequência natural dos números")
                print(f"     ⚠️ Requer reset da sequência PostgreSQL")
                print(f"     ⚠️ Operação mais complexa, mas mais 'limpa'")
                print()
            else:
                print("✅ NUMERAÇÃO SINCRONIZADA:")
                print("   IDs e números estão alinhados!")
                print("   Nenhuma correção necessária")
                
            return {
                'total_embarques': total_embarques,
                'ultimo_id': ultimo_id,
                'ultimo_numero': ultimo_numero,
                'diferenca': diferenca,
                'embarques_sem_numero': embarques_sem_numero,
                'precisa_correcao': diferenca != 0
            }
            
    except Exception as e:
        print(f"❌ ERRO ao analisar situação: {e}")
        return None

def opcao_1_avancar_numeros():
    """OPÇÃO 1: Avança os números para casar com os IDs"""
    print("🚀 OPÇÃO 1: AVANÇAR NÚMEROS PARA CASAR COM IDs")
    print("=" * 60)
    
    confirmacao = input("⚠️ Esta operação irá alterar a função de geração de números.\nTem certeza? (digite 'CONFIRMO'): ")
    
    if confirmacao != 'CONFIRMO':
        print("❌ Operação cancelada pelo usuário")
        return False
    
    try:
        from app import db, create_app
        from app.embarques.models import Embarque
        
        app = create_app()
        with app.app_context():
            ultimo_id = db.session.query(db.func.max(Embarque.id)).scalar() or 0
            ultimo_numero = db.session.query(db.func.max(Embarque.numero)).scalar() or 0
            
            print(f"📊 Situação atual:")
            print(f"   Último ID: {ultimo_id}")
            print(f"   Último número: {ultimo_numero}")
            print(f"   Diferença: {ultimo_id - ultimo_numero}")
            print()
            
            # Atualizar a função de geração de números
            print("🔧 Modificando função obter_proximo_numero_embarque()...")
            
            # Ler arquivo atual
            with open('app/utils/embarque_numero.py', 'r', encoding='utf-8') as f:
                conteudo_atual = f.read()
            
            # Backup
            with open('app/utils/embarque_numero.py.backup', 'w', encoding='utf-8') as f:
                f.write(conteudo_atual)
            
            # Nova implementação que sincroniza com IDs
            novo_conteudo = conteudo_atual.replace(
                'ultimo_numero = db.session.query(\n                db.func.coalesce(db.func.max(Embarque.numero), 0)\n            ).scalar()',
                f'''ultimo_numero = db.session.query(\n                db.func.coalesce(db.func.max(Embarque.numero), 0)\n            ).scalar()\n            \n            # 🔧 CORREÇÃO: Sincronizar com IDs se necessário\n            ultimo_id = db.session.query(\n                db.func.coalesce(db.func.max(Embarque.id), 0)\n            ).scalar()\n            \n            # Se ID está à frente, usar ID como base\n            if ultimo_id > ultimo_numero:\n                ultimo_numero = ultimo_id'''
            )
            
            # Salvar nova versão
            with open('app/utils/embarque_numero.py', 'w', encoding='utf-8') as f:
                f.write(novo_conteudo)
            
            print(f"✅ Função modificada com sucesso!")
            print(f"✅ Backup salvo em: app/utils/embarque_numero.py.backup")
            print()
            
            # Testar a nova função
            from app.utils.embarque_numero import obter_proximo_numero_embarque
            proximo_numero = obter_proximo_numero_embarque()
            
            print(f"🎯 RESULTADO:")
            print(f"   Próximo número que será gerado: {proximo_numero}")
            print(f"   Próximo ID que será usado: {ultimo_id + 1}")
            print(f"   Sincronização: {'✅ Perfeita' if proximo_numero == ultimo_id + 1 else '❌ Ainda desalinhada'}")
            print()
            print(f"💡 A partir de agora, todos os novos embarques terão número = ID")
            
            return True
            
    except Exception as e:
        print(f"❌ ERRO na Opção 1: {e}")
        return False

def opcao_2_rebobinar_ids():
    """OPÇÃO 2: Rebobina os IDs para casar com os números"""
    print("🔄 OPÇÃO 2: REBOBINAR IDs PARA CASAR COM NÚMEROS")
    print("=" * 60)
    
    print("⚠️ ATENÇÃO: Esta operação é mais complexa e requer:")
    print("   - Acesso direto ao PostgreSQL")
    print("   - Reset da sequência de auto-incremento")
    print("   - Pode impactar relacionamentos")
    print()
    
    confirmacao = input("⚠️ Tem certeza que quer prosseguir? (digite 'CONFIRMO'): ")
    
    if confirmacao != 'CONFIRMO':
        print("❌ Operação cancelada pelo usuário")
        return False
    
    try:
        from app import db, create_app
        from app.embarques.models import Embarque
        
        app = create_app()
        with app.app_context():
            ultimo_numero = db.session.query(db.func.max(Embarque.numero)).scalar() or 0
            ultimo_id = db.session.query(db.func.max(Embarque.id)).scalar() or 0
            
            print(f"📊 Situação atual:")
            print(f"   Último número: {ultimo_numero}")
            print(f"   Último ID: {ultimo_id}")
            print(f"   Novo valor da sequência será: {ultimo_numero + 1}")
            print()
            
            # Comando SQL para resetar sequência (PostgreSQL)
            sql_reset = f"SELECT setval('embarques_id_seq', {ultimo_numero}, true);"
            
            print(f"🔧 SQL que será executado:")
            print(f"   {sql_reset}")
            print()
            
            confirmacao_sql = input("⚠️ Executar este comando SQL? (digite 'EXECUTAR'): ")
            
            if confirmacao_sql != 'EXECUTAR':
                print("❌ Comando SQL cancelado")
                return False
            
            # Executar o reset da sequência
            result = db.session.execute(db.text(sql_reset))
            db.session.commit()
            
            # Verificar resultado
            fetch_result = result.fetchone()
            resultado = fetch_result[0] if fetch_result else None
            
            print(f"✅ Sequência resetada com sucesso!")
            print(f"✅ Novo valor da sequência: {resultado}")
            print()
            
            # Testar criando um embarque fictício para verificar
            print("🧪 Teste: Verificando próximo ID que seria gerado...")
            
            # Simular inserção para ver próximo ID
            next_id_query = "SELECT nextval('embarques_id_seq');"
            next_id_result = db.session.execute(db.text(next_id_query))
            next_fetch = next_id_result.fetchone()
            proximo_id = next_fetch[0] if next_fetch else ultimo_numero + 1
            
            # Reverter o nextval (para não "desperdiçar" um número)
            revert_query = f"SELECT setval('embarques_id_seq', {ultimo_numero}, true);"
            db.session.execute(db.text(revert_query))
            db.session.commit()
            
            print(f"🎯 RESULTADO DO TESTE:")
            print(f"   Próximo ID que será gerado: {proximo_id}")
            print(f"   Próximo número que será gerado: {ultimo_numero + 1}")
            print(f"   Sincronização: {'✅ Perfeita' if proximo_id == ultimo_numero + 1 else '❌ Ainda desalinhada'}")
            print()
            print(f"💡 A partir de agora, todos os novos embarques terão ID = número")
            
            return True
            
    except Exception as e:
        print(f"❌ ERRO na Opção 2: {e}")
        print(f"💡 Dica: Verifique se está conectado ao PostgreSQL correto")
        return False

def desfazer_opcao_1():
    """Desfaz a Opção 1 restaurando o backup"""
    print("↩️ DESFAZER OPÇÃO 1: Restaurar função original")
    print("=" * 50)
    
    try:
        import os
        
        if not os.path.exists('app/utils/embarque_numero.py.backup'):
            print("❌ Arquivo de backup não encontrado!")
            return False
        
        # Restaurar backup
        with open('app/utils/embarque_numero.py.backup', 'r', encoding='utf-8') as f:
            conteudo_backup = f.read()
        
        with open('app/utils/embarque_numero.py', 'w', encoding='utf-8') as f:
            f.write(conteudo_backup)
        
        print("✅ Função original restaurada com sucesso!")
        print("✅ A numeração voltou ao comportamento anterior")
        
        return True
        
    except Exception as e:
        print(f"❌ ERRO ao desfazer: {e}")
        return False

def main():
    """Menu principal"""
    print("🔧 SINCRONIZADOR DE NUMERAÇÃO DE EMBARQUES")
    print("=" * 60)
    print("Resolve dessincronização entre 'numero' e 'id' dos embarques")
    print()
    
    while True:
        # Analisar situação atual
        situacao = analisar_situacao_atual()
        
        if not situacao:
            break
        
        if not situacao['precisa_correcao']:
            print("✅ Numeração já está sincronizada! Nenhuma ação necessária.")
            break
        
        print("📋 OPÇÕES DISPONÍVEIS:")
        print("   1️⃣  - Avançar números (pular para casar com IDs)")
        print("   2️⃣  - Rebobinar IDs (resetar sequência PostgreSQL)")
        print("   3️⃣  - Desfazer Opção 1 (restaurar backup)")
        print("   4️⃣  - Apenas analisar (não fazer nada)")
        print("   0️⃣  - Sair")
        print()
        
        opcao = input("🤔 Escolha uma opção (1/2/3/4/0): ").strip()
        
        if opcao == '1':
            sucesso = opcao_1_avancar_numeros()
            if sucesso:
                print("\n🎉 Opção 1 executada com sucesso!")
            else:
                print("\n❌ Falha na execução da Opção 1")
        
        elif opcao == '2':
            sucesso = opcao_2_rebobinar_ids()
            if sucesso:
                print("\n🎉 Opção 2 executada com sucesso!")
            else:
                print("\n❌ Falha na execução da Opção 2")
        
        elif opcao == '3':
            sucesso = desfazer_opcao_1()
            if sucesso:
                print("\n✅ Opção 1 desfeita com sucesso!")
            else:
                print("\n❌ Falha ao desfazer Opção 1")
        
        elif opcao == '4':
            print("\n📊 Análise concluída. Nenhuma alteração feita.")
        
        elif opcao == '0':
            print("\n👋 Saindo do sincronizador...")
            break
        
        else:
            print("\n❌ Opção inválida! Digite 1, 2, 3, 4 ou 0")
        
        print("\n" + "=" * 60)
        input("Pressione ENTER para continuar...")
        print()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⏹️ Operação interrompida pelo usuário")
    except Exception as e:
        print(f"\n\n❌ ERRO GERAL: {e}")
        import traceback
        traceback.print_exc() 