#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script para Verificar Dados Pós-Importação
==========================================

Este script verifica se os dados estão consistentes após a importação
que gerou o DetachedInstanceError, para determinar se é necessário
reimportar os dados ou se apenas as correções resolvem o problema.
"""

import os
import sys
from datetime import datetime

def verificar_dados_localmente():
    """Verifica dados no ambiente local"""
    
    print("🔍 === VERIFICAÇÃO DE DADOS PÓS-IMPORTAÇÃO ===")
    print("📅 Data:", datetime.now().strftime("%d/%m/%Y %H:%M:%S"))
    print()
    
    try:
        # Tenta importar e inicializar o app
        sys.path.append('.')
        from app import create_app, db
        from app.pedidos.models import Pedido
        from app.separacao.models import Separacao
        
        app = create_app()
        
        with app.app_context():
            print("📊 === ESTATÍSTICAS DOS DADOS ===")
            print()
            
            # Conta pedidos
            total_pedidos = Pedido.query.count()
            print(f"📦 Total de pedidos: {total_pedidos}")
            
            # Conta separações
            total_separacoes = Separacao.query.count()
            print(f"📋 Total de separações: {total_separacoes}")
            
            # Verifica pedidos específicos do log
            pedidos_do_log = [
                'VCD2519528', 'VCD2519549', 'VCD2519564', 'VCD2519532',
                'VCD2519535', 'VCD2519508', 'VCD2519515', 'VCD2519524',
                'VCD2519516', 'VCD2519519', 'VCD2519523', 'VCD2519527',
                'VCD2519526', 'VCD2519357', 'VCD2519356', 'VCD2519545'
            ]
            
            print()
            print("🎯 === VERIFICAÇÃO DOS PEDIDOS DO LOG ===")
            pedidos_encontrados = 0
            
            for numero_pedido in pedidos_do_log:
                pedido = Pedido.query.filter_by(num_pedido=numero_pedido).first()
                if pedido:
                    pedidos_encontrados += 1
                    print(f"✅ {numero_pedido} - Encontrado")
                    
                    # Verifica separações do pedido
                    separacoes_pedido = Separacao.query.filter_by(num_pedido=numero_pedido).count()
                    if separacoes_pedido > 0:
                        print(f"   📋 {separacoes_pedido} separações vinculadas")
                    else:
                        print(f"   ⚠️ Sem separações vinculadas")
                else:
                    print(f"❌ {numero_pedido} - NÃO encontrado")
            
            print()
            print(f"📈 Pedidos do log encontrados: {pedidos_encontrados}/{len(pedidos_do_log)}")
            
            # Verifica separações órfãs
            print()
            print("🔍 === VERIFICAÇÃO DE SEPARAÇÕES ÓRFÃS ===")
            
            # Separações sem pedido correspondente
            separacoes_orfas = db.session.query(Separacao).outerjoin(
                Pedido, Separacao.num_pedido == Pedido.num_pedido
            ).filter(Pedido.num_pedido.is_(None)).count()
            
            print(f"👻 Separações órfãs: {separacoes_orfas}")
            
            if separacoes_orfas == 0:
                print("✅ Excelente! Não há separações órfãs")
            elif separacoes_orfas < 50:
                print("⚠️ Poucas separações órfãs - aceitável")
            else:
                print("❌ Muitas separações órfãs - pode indicar problema")
            
            # Verifica lotes
            print()
            print("📦 === VERIFICAÇÃO DE LOTES ===")
            
            lotes_unicos = db.session.query(Separacao.lote).distinct().count()
            separacoes_com_lote = Separacao.query.filter(Separacao.lote.isnot(None)).count()
            separacoes_sem_lote = Separacao.query.filter(Separacao.lote.is_(None)).count()
            
            print(f"🏷️ Lotes únicos: {lotes_unicos}")
            print(f"📋 Separações com lote: {separacoes_com_lote}")
            print(f"❓ Separações sem lote: {separacoes_sem_lote}")
            
            return True
            
    except Exception as e:
        print(f"❌ Erro ao verificar dados: {e}")
        return False

def mostrar_comandos_render():
    """Mostra comandos para verificar no Render"""
    
    print()
    print("🌐 === COMANDOS PARA VERIFICAR NO RENDER ===")
    print()
    
    comandos = [
        {
            "desc": "Contar pedidos total",
            "cmd": "python -c \"from app import create_app, db; from app.pedidos.models import Pedido; app=create_app(); app.app_context().push(); print(f'Pedidos: {Pedido.query.count()}')\""
        },
        {
            "desc": "Contar separações total", 
            "cmd": "python -c \"from app import create_app, db; from app.separacao.models import Separacao; app=create_app(); app.app_context().push(); print(f'Separações: {Separacao.query.count()}')\""
        },
        {
            "desc": "Verificar pedido específico",
            "cmd": "python -c \"from app import create_app, db; from app.pedidos.models import Pedido; app=create_app(); app.app_context().push(); p=Pedido.query.filter_by(num_pedido='VCD2519528').first(); print(f'Pedido VCD2519528: {\"Encontrado\" if p else \"Não encontrado\"}')\""
        },
        {
            "desc": "Contar separações órfãs",
            "cmd": "python -c \"from app import create_app, db; from app.pedidos.models import Pedido; from app.separacao.models import Separacao; app=create_app(); app.app_context().push(); orfas=db.session.query(Separacao).outerjoin(Pedido, Separacao.num_pedido == Pedido.num_pedido).filter(Pedido.num_pedido.is_(None)).count(); print(f'Órfãs: {orfas}')\""
        }
    ]
    
    for i, cmd_info in enumerate(comandos, 1):
        print(f"{i}. **{cmd_info['desc']}**")
        print(f"   ```bash")
        print(f"   {cmd_info['cmd']}")
        print(f"   ```")
        print()

def diagnosticar_situacao():
    """Diagnostica a situação e dá recomendações"""
    
    print("🩺 === DIAGNÓSTICO E RECOMENDAÇÕES ===")
    print()
    
    print("📋 **SITUAÇÃO ATUAL BASEADA NO LOG:**")
    print()
    print("✅ **IMPORTAÇÃO FOI CONCLUÍDA COM SUCESSO**")
    print("   - 329 separações órfãs foram corrigidas")
    print("   - Lotes foram criados para múltiplos pedidos")
    print("   - Processo terminou com HTTP 200 (sucesso)")
    print()
    
    print("❌ **ERRO OCORREU POSTERIORMENTE**")
    print("   - Erro foi na /cotacao/tela (tela de cotação)")
    print("   - Não foi durante a importação")
    print("   - DetachedInstanceError ao tentar buscar cidade")
    print()
    
    print("🎯 **RECOMENDAÇÃO:**")
    print()
    print("1. ✅ **NÃO APAGUE OS DADOS** - A importação funcionou")
    print("2. ✅ **AS CORREÇÕES JÁ FORAM FEITAS** - Sistema protegido")
    print("3. ✅ **TESTE A COTAÇÃO NOVAMENTE** - Deve funcionar agora")
    print("4. ⚠️ **SE AINDA DER ERRO** - Aí sim considere reimportar")
    print()
    
    print("🧪 **COMO TESTAR SE ESTÁ FUNCIONANDO:**")
    print("   1. Acesse o sistema no Render")
    print("   2. Vá em Pedidos > Lista de Pedidos")
    print("   3. Selecione alguns pedidos")
    print("   4. Clique em 'Iniciar Cotação'")
    print("   5. Se funcionar = Problema resolvido!")
    print("   6. Se der erro = Execute verificação no Render")
    print()

def mostrar_script_verificacao_render():
    """Cria script para executar no Render Shell"""
    
    print("📝 === SCRIPT PARA RENDER SHELL ===")
    print()
    print("```python")
    print("# Cole este código no Render Shell")
    print("from app import create_app, db")
    print("from app.pedidos.models import Pedido")
    print("from app.separacao.models import Separacao")
    print()
    print("app = create_app()")
    print("with app.app_context():")
    print("    print('📊 VERIFICAÇÃO DE DADOS')")
    print("    print(f'📦 Pedidos: {Pedido.query.count()}')")
    print("    print(f'📋 Separações: {Separacao.query.count()}')")
    print("    ")
    print("    # Verifica pedidos específicos do log")
    print("    pedidos_teste = ['VCD2519528', 'VCD2519549', 'VCD2519564']")
    print("    for num in pedidos_teste:")
    print("        p = Pedido.query.filter_by(num_pedido=num).first()")
    print("        status = '✅ OK' if p else '❌ MISSING'")
    print("        print(f'{num}: {status}')")
    print("    ")
    print("    # Verifica separações órfãs")
    print("    orfas = db.session.query(Separacao).outerjoin(")
    print("        Pedido, Separacao.num_pedido == Pedido.num_pedido")
    print("    ).filter(Pedido.num_pedido.is_(None)).count()")
    print("    print(f'👻 Órfãs: {orfas}')")
    print("    ")
    print("    print('✅ Verificação concluída')")
    print("```")
    print()

if __name__ == "__main__":
    verificar_dados_localmente()
    mostrar_comandos_render()
    diagnosticar_situacao()
    mostrar_script_verificacao_render()
    
    print("🎯 **PRÓXIMOS PASSOS:**")
    print("1. Execute o script de verificação no Render Shell")
    print("2. Teste a cotação no sistema")
    print("3. Se funcionar: problema resolvido!")
    print("4. Se não funcionar: me avise com os resultados da verificação") 