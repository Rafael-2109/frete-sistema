#!/usr/bin/env python3
"""
Script para testar a API de separações e verificar o campo protocolo_portal
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.separacao.models import Separacao
from app.portal.models import PortalIntegracao
import json
from flask import Flask

app = create_app()

def criar_integracao_teste():
    """Cria uma integração de teste para verificar se aparece na API"""
    with app.app_context():
        # Buscar uma separação existente
        separacao = db.session.query(Separacao).first()
        
        if not separacao:
            print("❌ Nenhuma separação encontrada")
            return None
            
        print(f"📦 Usando separação: {separacao.separacao_lote_id}")
        
        # Verificar se já existe integração
        integracao = db.session.query(PortalIntegracao).filter(
            PortalIntegracao.lote_id == separacao.separacao_lote_id
        ).first()
        
        if not integracao:
            print("➕ Criando integração de teste...")
            integracao = PortalIntegracao(
                portal='atacadao',
                lote_id=separacao.separacao_lote_id,
                tipo_lote='separacao',
                protocolo_portal='TEST-PROT-123456',
                status='confirmado',
                usuario_solicitante='teste'
            )
            db.session.add(integracao)
            db.session.commit()
            print(f"✅ Integração criada com protocolo: {integracao.protocolo_portal}")
        else:
            print(f"✅ Integração já existe com protocolo: {integracao.protocolo_portal}")
            
        return separacao.num_pedido, separacao.separacao_lote_id

def testar_api_diretamente():
    """Testa a API diretamente para verificar o retorno"""
    with app.app_context():
        with app.test_client() as client:
            # Buscar uma separação com integração
            dados = criar_integracao_teste()
            
            if not dados:
                return
                
            num_pedido, lote_id = dados
            
            print(f"\n🔍 Testando API para pedido: {num_pedido}")
            
            # Fazer requisição para a API
            response = client.get(f'/carteira/api/pedido/{num_pedido}/separacoes-completas')
            
            if response.status_code == 200:
                data = response.get_json()
                
                if data.get('success'):
                    print(f"✅ API retornou {len(data.get('separacoes', []))} separações")
                    
                    # Procurar a separação com o lote_id
                    for sep in data.get('separacoes', []):
                        if sep.get('separacao_lote_id') == lote_id:
                            print(f"\n📋 Separação encontrada:")
                            print(f"   Lote ID: {sep.get('separacao_lote_id')}")
                            print(f"   Status: {sep.get('status')}")
                            
                            # VERIFICAÇÃO CRÍTICA
                            if 'protocolo_portal' in sep:
                                print(f"   ✅ CAMPO protocolo_portal EXISTE: {sep.get('protocolo_portal')}")
                                
                                if sep.get('protocolo_portal'):
                                    print("   ✅✅✅ PROTOCOLO PRESENTE - BOTÕES DEVEM APARECER!")
                                else:
                                    print("   ⚠️ Protocolo existe mas está vazio")
                            else:
                                print("   ❌❌❌ CAMPO protocolo_portal NÃO EXISTE NO RETORNO!")
                                print("   ❌ ESTE É O PROBLEMA - O CAMPO NÃO ESTÁ SENDO RETORNADO!")
                            
                            # Mostrar todos os campos retornados
                            print(f"\n   📊 Campos retornados: {list(sep.keys())}")
                            break
                    else:
                        print(f"❌ Separação com lote_id {lote_id} não encontrada no retorno")
                else:
                    print(f"❌ API retornou erro: {data.get('error')}")
            else:
                print(f"❌ Erro HTTP: {response.status_code}")
                
def verificar_logs_servidor():
    """Verifica os logs do servidor para debug"""
    print("\n" + "=" * 60)
    print("📋 VERIFICANDO LOGS")
    print("=" * 60)
    
    with app.app_context():
        # Verificar últimos logs do portal
        from app.portal.models import PortalLog
        
        logs = db.session.query(PortalLog).order_by(
            PortalLog.criado_em.desc()
        ).limit(5).all()
        
        if logs:
            print("Últimos logs do portal:")
            for log in logs:
                print(f"   - {log.acao}: {log.mensagem[:50]}...")
        else:
            print("Nenhum log encontrado")

if __name__ == "__main__":
    print("=" * 60)
    print("🔍 TESTE COMPLETO DA API DE SEPARAÇÕES")
    print("=" * 60)
    
    testar_api_diretamente()
    verificar_logs_servidor()
    
    print("\n" + "=" * 60)
    print("📝 DIAGNÓSTICO FINAL:")
    print("=" * 60)
    print("Se o campo protocolo_portal NÃO aparece no retorno:")
    print("1. ❌ O problema está na API (separacoes_api.py)")
    print("2. Verifique se o servidor foi reiniciado")
    print("3. Verifique os logs de erro no terminal do servidor")
    print("")
    print("Se o campo protocolo_portal APARECE no retorno:")
    print("1. ✅ A API está funcionando")
    print("2. Limpe o cache do navegador (Ctrl+F5)")
    print("3. Verifique o console do navegador (F12)")
    print("=" * 60)