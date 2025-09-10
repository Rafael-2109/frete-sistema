#!/usr/bin/env python3
"""
Script de teste para o fluxo completo de agendamento Sendas
"""

import sys
import os
import asyncio
from datetime import datetime, timedelta

# Adicionar o caminho do projeto ao PYTHONPATH
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.portal.sendas.consumir_agendas import ConsumirAgendasSendas
from app.portal.sendas.preencher_planilha import PreencherPlanilhaSendas

async def test_upload_flow():
    """
    Testa o fluxo de upload da planilha
    """
    print("\n" + "="*60)
    print("🧪 TESTE DO FLUXO DE UPLOAD SENDAS")
    print("="*60)
    
    # Configurações de teste
    cnpj = "06.057.223/0233-84"
    data_agendamento = datetime.now() + timedelta(days=3)
    data_expedicao = datetime.now() + timedelta(days=2)
    
    print(f"\n📋 Configurações do teste:")
    print(f"  - CNPJ: {cnpj}")
    print(f"  - Data Agendamento: {data_agendamento.strftime('%d/%m/%Y')}")
    print(f"  - Data Expedição: {data_expedicao.strftime('%d/%m/%Y')}")
    
    try:
        # 1. Criar consumidor
        print("\n1️⃣ Criando consumidor Sendas...")
        consumidor = ConsumirAgendasSendas()
        print("   ✅ Consumidor criado")
        
        # 2. Baixar planilha modelo
        print("\n2️⃣ Baixando planilha modelo do portal...")
        arquivo_modelo = consumidor.baixar_planilha_modelo()
        
        if not arquivo_modelo:
            print("   ❌ Falha ao baixar planilha modelo")
            return False
        
        print(f"   ✅ Planilha baixada: {arquivo_modelo}")
        
        # 3. Preencher planilha
        print("\n3️⃣ Preenchendo planilha com dados...")
        preenchedor = PreencherPlanilhaSendas()
        
        # Gerar nome do arquivo de destino
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        nome_limpo = cnpj.replace('/', '_').replace('.', '_').replace('-', '_')
        arquivo_destino = f"/tmp/sendas_teste_{nome_limpo}_{timestamp}.xlsx"
        
        resultado = preenchedor.preencher_planilha(
            arquivo_origem=arquivo_modelo,
            cnpj=cnpj,
            data_agendamento=data_agendamento,
            arquivo_destino=arquivo_destino
        )
        
        if not resultado['sucesso']:
            print(f"   ❌ Falha ao preencher: {resultado.get('mensagem', 'Erro desconhecido')}")
            return False
        
        print(f"   ✅ Planilha preenchida:")
        print(f"      - Linhas preenchidas: {resultado['linhas_preenchidas']}")
        print(f"      - Peso total: {resultado['peso_total']} kg")
        print(f"      - Arquivo: {arquivo_destino}")
        
        # 4. Fazer upload da planilha
        print("\n4️⃣ Fazendo upload da planilha preenchida...")
        upload_sucesso = consumidor.fazer_upload_planilha_sync(arquivo_destino)
        
        if upload_sucesso:
            print("   ✅ Upload realizado com sucesso!")
        else:
            print("   ❌ Falha no upload da planilha")
            print("\n   ⚠️ Verifique se existe screenshot: erro_upload_botao_nao_encontrado.png")
            
        return upload_sucesso
        
    except Exception as e:
        print(f"\n❌ Erro no teste: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """
    Função principal
    """
    # Criar aplicação Flask
    app = create_app()
    
    with app.app_context():
        # Executar teste
        resultado = asyncio.run(test_upload_flow())
        
        print("\n" + "="*60)
        if resultado:
            print("✅ TESTE CONCLUÍDO COM SUCESSO!")
        else:
            print("❌ TESTE FALHOU - VERIFIQUE OS LOGS")
        print("="*60 + "\n")
        
        return 0 if resultado else 1

if __name__ == "__main__":
    exit(main())