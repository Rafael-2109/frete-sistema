#!/usr/bin/env python3
"""
Script de teste específico para verificar o problema do dropzone
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
    # Usar pandas para criar um arquivo Excel real
    try:
        import pandas as pd
        
        # Criar dados de teste
        df = pd.DataFrame({
            'CNPJ/CPF': ['11.111.111/0001-11'],
            'Data Expedição': ['10/01/2025'],
            'Data Agendamento': ['11/01/2025'],
            'Observação': ['Teste dropzone']
        })
        
        # Salvar como Excel
        test_file = os.path.join(tempfile.gettempdir(), "test_dropzone_sendas.xlsx")
        df.to_excel(test_file, index=False)
        logger.info(f"✅ Arquivo Excel criado: {test_file}")
        return test_file
        
    except ImportError:
        # Se não tiver pandas, criar arquivo simples
        test_file = os.path.join(tempfile.gettempdir(), "test_dropzone_sendas.xlsx")
        with open(test_file, 'wb') as f:
            # Escrever alguns bytes para simular arquivo
            f.write(b'PK')  # Assinatura de arquivo ZIP/Excel
            f.write(b'\x00' * 100)  # Adicionar conteúdo dummy
        logger.info(f"⚠️ Arquivo dummy criado (sem pandas): {test_file}")
        return test_file

def testar_upload_direto():
    """Testa o upload diretamente via subprocess"""
    
    # Criar arquivo de teste
    test_file = criar_arquivo_teste()
    
    if not os.path.exists(test_file):
        logger.error(f"❌ Arquivo de teste não foi criado: {test_file}")
        return False
    
    logger.info(f"📁 Arquivo de teste: {test_file}")
    logger.info(f"📁 Tamanho: {os.path.getsize(test_file)} bytes")
    logger.info(f"📁 Legível: {os.access(test_file, os.R_OK)}")
    
    print("\n" + "=" * 60)
    print("TESTANDO UPLOAD VIA SUBPROCESS")
    print("=" * 60)
    
    # Caminho do script
    script_path = "/home/rafaelnascimento/projetos/frete_sistema/app/portal/sendas/upload_planilha_subprocess.py"
    
    if not os.path.exists(script_path):
        logger.error(f"❌ Script não encontrado: {script_path}")
        return False
    
    # Executar o script
    try:
        logger.info("🚀 Iniciando subprocess...")
        result = subprocess.run(
            [sys.executable, script_path, test_file],
            capture_output=True,
            text=True,
            timeout=120  # 2 minutos
        )
        
        print(f"\n📊 Return code: {result.returncode}")
        print(f"\n📝 STDOUT:\n{result.stdout}")
        
        if result.stderr:
            print(f"\n⚠️ STDERR:\n{result.stderr}")
        
        # Tentar fazer parse do JSON
        if result.stdout:
            lines = result.stdout.strip().split('\n')
            for line in reversed(lines):
                if line.strip().startswith('{') and line.strip().endswith('}'):
                    try:
                        response = json.loads(line.strip())
                        print(f"\n✅ JSON Response:")
                        print(json.dumps(response, indent=2))
                        
                        if response.get('success'):
                            print("\n🎉 UPLOAD BEM-SUCEDIDO!")
                        else:
                            print(f"\n❌ UPLOAD FALHOU: {response.get('error')}")
                        
                        return response.get('success', False)
                    except json.JSONDecodeError as e:
                        logger.error(f"❌ Erro ao decodificar JSON: {e}")
                        logger.debug(f"Linha tentada: {line}")
            
            print("\n⚠️ Nenhum JSON válido encontrado na resposta")
        
    except subprocess.TimeoutExpired:
        print("\n❌ ERRO: Timeout no teste (120 segundos)")
    except Exception as e:
        print(f"\n❌ ERRO: {e}")
        print(f"❌ Tipo: {type(e).__name__}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Limpar arquivo de teste
        if os.path.exists(test_file):
            os.remove(test_file)
            logger.info(f"🗑️ Arquivo de teste removido")
    
    return False

def testar_consumidor_direto():
    """Testa o consumidor diretamente sem subprocess"""
    print("\n" + "=" * 60)
    print("TESTANDO CONSUMIDOR DIRETAMENTE (ASYNC)")
    print("=" * 60)
    
    import asyncio
    import sys
    sys.path.insert(0, '/home/rafaelnascimento/projetos/frete_sistema/app/portal/sendas')
    
    from consumir_agendas import ConsumirAgendasSendas
    
    # Criar arquivo de teste
    test_file = criar_arquivo_teste()
    
    async def run_test():
        try:
            consumidor = ConsumirAgendasSendas()
            logger.info("✅ Consumidor criado")
            
            # Testar upload
            resultado = await consumidor.run_upload_planilha(test_file)
            
            if resultado:
                print("\n🎉 UPLOAD DIRETO BEM-SUCEDIDO!")
            else:
                print("\n❌ UPLOAD DIRETO FALHOU")
            
            return resultado
            
        except Exception as e:
            print(f"\n❌ ERRO NO TESTE DIRETO: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            # Limpar
            if os.path.exists(test_file):
                os.remove(test_file)
    
    # Executar teste async
    return asyncio.run(run_test())

if __name__ == "__main__":
    print("🔍 TESTE DE UPLOAD DROPZONE SENDAS")
    print("=" * 60)
    
    # Testar via subprocess (como o Flask faz)
    sucesso_subprocess = testar_upload_direto()
    
    # Se falhou, testar direto para comparar
    if not sucesso_subprocess:
        print("\n⚠️ Upload via subprocess falhou. Testando método direto...")
        sucesso_direto = testar_consumidor_direto()
        
        if sucesso_direto:
            print("\n🔍 DIAGNÓSTICO: Upload funciona direto mas falha via subprocess")
            print("   Possível problema de isolamento ou contexto")
        else:
            print("\n🔍 DIAGNÓSTICO: Upload falha em ambos os métodos")
            print("   Problema está na interação com o portal Sendas")
    else:
        print("\n✅ TESTE CONCLUÍDO COM SUCESSO!")