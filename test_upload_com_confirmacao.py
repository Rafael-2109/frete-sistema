#!/usr/bin/env python3
"""
Script de teste para verificar upload com confirmação de demanda
"""

import subprocess
import sys
import json
import tempfile
import os
import logging

# Configurar logging detalhado
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def criar_arquivo_teste():
    """Cria um arquivo Excel de teste"""
    try:
        import pandas as pd
        
        # Criar dados de teste
        df = pd.DataFrame({
            'CNPJ/CPF': ['11.111.111/0001-11'],
            'Data Expedição': ['10/01/2025'],
            'Data Agendamento': ['11/01/2025'],
            'Observação': ['Teste confirmação demanda']
        })
        
        # Salvar como Excel
        test_file = os.path.join(tempfile.gettempdir(), "test_confirmacao_demanda.xlsx")
        df.to_excel(test_file, index=False)
        logger.info(f"✅ Arquivo Excel criado: {test_file}")
        return test_file
        
    except ImportError:
        # Se não tiver pandas, criar arquivo simples
        test_file = os.path.join(tempfile.gettempdir(), "test_confirmacao_demanda.xlsx")
        with open(test_file, 'wb') as f:
            # Escrever alguns bytes para simular arquivo
            f.write(b'PK')  # Assinatura de arquivo ZIP/Excel
            f.write(b'\x00' * 100)  # Adicionar conteúdo dummy
        logger.info(f"⚠️ Arquivo dummy criado (sem pandas): {test_file}")
        return test_file

def testar_upload_com_confirmacao():
    """Testa o upload com confirmação de demanda"""
    
    print("\n" + "=" * 60)
    print("TESTE DE UPLOAD COM CONFIRMAÇÃO DE DEMANDA")
    print("=" * 60)
    
    # Criar arquivo de teste
    test_file = criar_arquivo_teste()
    
    if not os.path.exists(test_file):
        logger.error(f"❌ Arquivo de teste não foi criado: {test_file}")
        return False
    
    logger.info(f"📁 Arquivo de teste: {test_file}")
    logger.info(f"📁 Tamanho: {os.path.getsize(test_file)} bytes")
    
    # Caminho do script
    script_path = "/home/rafaelnascimento/projetos/frete_sistema/app/portal/sendas/upload_planilha_subprocess.py"
    
    if not os.path.exists(script_path):
        logger.error(f"❌ Script não encontrado: {script_path}")
        return False
    
    # Executar o script
    try:
        logger.info("🚀 Iniciando upload com confirmação...")
        print("\n📤 Executando upload da planilha...")
        print("🔍 Observando logs para verificar confirmação de demanda...")
        print("-" * 60)
        
        result = subprocess.run(
            [sys.executable, script_path, test_file],
            capture_output=True,
            text=True,
            timeout=180  # 3 minutos para dar tempo de confirmar
        )
        
        print(f"\n📊 Return code: {result.returncode}")
        
        # Verificar logs específicos da confirmação
        if result.stderr:
            linhas_importantes = []
            for linha in result.stderr.split('\n'):
                if any(texto in linha for texto in [
                    'CONFIRMAR DEMANDA',
                    'confirmação',
                    'Clicou em CONFIRMAR',
                    'Botão CONFIRMAR',
                    'Mensagem de sucesso',
                    'Mensagem de erro'
                ]):
                    linhas_importantes.append(linha)
            
            if linhas_importantes:
                print("\n🔍 LOGS DE CONFIRMAÇÃO ENCONTRADOS:")
                print("-" * 60)
                for linha in linhas_importantes:
                    print(linha)
                print("-" * 60)
        
        # Parse do resultado JSON
        if result.stdout:
            lines = result.stdout.strip().split('\n')
            for line in reversed(lines):
                if line.strip().startswith('{') and line.strip().endswith('}'):
                    try:
                        response = json.loads(line.strip())
                        print(f"\n✅ JSON Response:")
                        print(json.dumps(response, indent=2))
                        
                        if response.get('success'):
                            print("\n🎉 UPLOAD E CONFIRMAÇÃO BEM-SUCEDIDOS!")
                            
                            # Verificar se houve confirmação nos logs
                            if result.stderr and 'CONFIRMAR DEMANDA' in result.stderr:
                                print("✅ Confirmação de demanda foi executada")
                            else:
                                print("⚠️ Upload feito mas confirmação pode não ter sido necessária")
                        else:
                            print(f"\n❌ FALHA: {response.get('error')}")
                        
                        return response.get('success', False)
                    except json.JSONDecodeError as e:
                        logger.error(f"❌ Erro ao decodificar JSON: {e}")
            
            print("\n⚠️ Nenhum JSON válido encontrado na resposta")
        
        # Mostrar stderr completo se precisar debug
        if result.returncode != 0 and result.stderr:
            print("\n📝 STDERR COMPLETO (para debug):")
            print("-" * 60)
            print(result.stderr[-2000:])  # Últimos 2000 caracteres
        
    except subprocess.TimeoutExpired:
        print("\n❌ ERRO: Timeout no teste (180 segundos)")
        return False
    except Exception as e:
        print(f"\n❌ ERRO: {e}")
        print(f"❌ Tipo: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # Limpar arquivo de teste
        if os.path.exists(test_file):
            os.remove(test_file)
            logger.info(f"🗑️ Arquivo de teste removido")
    
    return False

if __name__ == "__main__":
    print("🔍 TESTE DE UPLOAD COM CONFIRMAÇÃO DE DEMANDA - SENDAS")
    print("=" * 60)
    
    sucesso = testar_upload_com_confirmacao()
    
    if sucesso:
        print("\n✅ TESTE CONCLUÍDO COM SUCESSO!")
        print("   - Upload realizado")
        print("   - Confirmação de demanda executada (se necessária)")
    else:
        print("\n❌ TESTE FALHOU")
        print("   Verifique os logs acima para detalhes")