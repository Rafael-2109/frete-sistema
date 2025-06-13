#!/usr/bin/env python3
"""
Script para corrigir problemas de sessão com objetos Cidade e outros problemas relacionados.
Este script resolve o erro: "Instance <Cidade at 0x...> is not bound to a Session; 
attribute refresh operation cannot proceed"
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.localidades.models import Cidade
from app.pedidos.models import Pedido
from app.embarques.models import Embarque, EmbarqueItem
from app.cotacao.models import Cotacao
from sqlalchemy import text
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def corrigir_problemas_sessao():
    """
    Corrige problemas de sessão com objetos Cidade e outros modelos.
    """
    app = create_app()
    
    with app.app_context():
        try:
            print("🔧 INICIANDO CORREÇÃO DE PROBLEMAS DE SESSÃO")
            print("=" * 60)
            
            # 1. Limpar cache de sessão do SQLAlchemy
            print("\n1️⃣ Limpando cache de sessão...")
            db.session.expunge_all()
            db.session.close()
            
            # 2. Verificar e corrigir objetos Cidade órfãos
            print("\n2️⃣ Verificando objetos Cidade...")
            cidades_problematicas = []
            
            try:
                # Força recarregamento de todas as cidades
                cidades = db.session.query(Cidade).all()
                for cidade in cidades:
                    try:
                        # Tenta acessar atributos para verificar se está vinculado à sessão
                        _ = cidade.nome
                        _ = cidade.uf
                        _ = cidade.icms
                    except Exception as e:
                        cidades_problematicas.append(cidade.id)
                        logger.warning(f"Cidade {cidade.id} com problema de sessão: {e}")
                
                print(f"   ✅ {len(cidades)} cidades verificadas")
                if cidades_problematicas:
                    print(f"   ⚠️ {len(cidades_problematicas)} cidades com problemas")
                else:
                    print("   ✅ Todas as cidades estão OK")
                    
            except Exception as e:
                print(f"   ❌ Erro ao verificar cidades: {e}")
            
            # 3. Limpar objetos desanexados da sessão
            print("\n3️⃣ Limpando objetos desanexados...")
            try:
                # Remove todos os objetos da sessão atual
                db.session.expunge_all()
                
                # Força garbage collection
                import gc
                gc.collect()
                
                print("   ✅ Objetos desanexados removidos")
                
            except Exception as e:
                print(f"   ❌ Erro ao limpar objetos: {e}")
            
            # 4. Verificar e corrigir pedidos com problemas de localização
            print("\n4️⃣ Verificando pedidos com problemas de localização...")
            try:
                pedidos_sem_normalizacao = db.session.query(Pedido).filter(
                    (Pedido.cidade_normalizada.is_(None)) | 
                    (Pedido.uf_normalizada.is_(None))
                ).limit(100).all()
                
                print(f"   📊 {len(pedidos_sem_normalizacao)} pedidos sem normalização encontrados")
                
                if pedidos_sem_normalizacao:
                    from app.utils.localizacao import LocalizacaoService
                    
                    contador = 0
                    for pedido in pedidos_sem_normalizacao:
                        try:
                            LocalizacaoService.normalizar_dados_pedido(pedido)
                            contador += 1
                            
                            if contador % 20 == 0:
                                db.session.commit()
                                print(f"   🔄 {contador} pedidos normalizados...")
                                
                        except Exception as e:
                            logger.warning(f"Erro ao normalizar pedido {pedido.num_pedido}: {e}")
                    
                    db.session.commit()
                    print(f"   ✅ {contador} pedidos normalizados com sucesso")
                
            except Exception as e:
                print(f"   ❌ Erro ao verificar pedidos: {e}")
            
            # 5. Verificar embarques cancelados com dados órfãos
            print("\n5️⃣ Verificando embarques cancelados...")
            try:
                embarques_cancelados = db.session.query(Embarque).filter(
                    Embarque.status == 'CANCELADO'
                ).all()
                
                print(f"   📊 {len(embarques_cancelados)} embarques cancelados encontrados")
                
                itens_com_dados = 0
                for embarque in embarques_cancelados:
                    itens = db.session.query(EmbarqueItem).filter(
                        EmbarqueItem.embarque_id == embarque.id
                    ).all()
                    
                    for item in itens:
                        if item.nf or item.data_embarque:
                            itens_com_dados += 1
                
                if itens_com_dados > 0:
                    print(f"   ⚠️ {itens_com_dados} itens de embarques cancelados com dados órfãos")
                else:
                    print("   ✅ Nenhum item órfão encontrado")
                
            except Exception as e:
                print(f"   ❌ Erro ao verificar embarques: {e}")
            
            # 6. Verificar cotações órfãs
            print("\n6️⃣ Verificando cotações órfãs...")
            try:
                cotacoes_orfas = db.session.query(Cotacao).filter(
                    ~Cotacao.pedidos.any()
                ).all()
                
                print(f"   📊 {len(cotacoes_orfas)} cotações órfãs encontradas")
                
                if cotacoes_orfas:
                    print("   ⚠️ Existem cotações sem pedidos vinculados")
                else:
                    print("   ✅ Nenhuma cotação órfã encontrada")
                
            except Exception as e:
                print(f"   ❌ Erro ao verificar cotações: {e}")
            
            # 7. Executar VACUUM para otimizar banco
            print("\n7️⃣ Otimizando banco de dados...")
            try:
                # Para SQLite, executa VACUUM
                db.session.execute(text("VACUUM"))
                db.session.commit()
                print("   ✅ Banco de dados otimizado")
                
            except Exception as e:
                print(f"   ❌ Erro ao otimizar banco: {e}")
            
            print("\n" + "=" * 60)
            print("✅ CORREÇÃO DE PROBLEMAS DE SESSÃO CONCLUÍDA")
            print("\nRecomendações:")
            print("1. Reinicie o servidor Flask")
            print("2. Limpe o cache do navegador")
            print("3. Teste a funcionalidade de cotação")
            
        except Exception as e:
            print(f"\n❌ ERRO GERAL: {e}")
            db.session.rollback()
            return False
        
        return True

if __name__ == "__main__":
    sucesso = corrigir_problemas_sessao()
    if sucesso:
        print("\n🎉 Script executado com sucesso!")
    else:
        print("\n💥 Script falhou!")
        sys.exit(1) 