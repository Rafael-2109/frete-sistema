"""
Jobs de teste para verificar o worker
"""
import time
from datetime import datetime

def teste_simples():
    """Job de teste simples"""
    print("✅ Job de teste executado com sucesso!")
    time.sleep(2)
    return {
        "resultado": "OK", 
        "timestamp": datetime.now().isoformat(),
        "mensagem": "Worker funcionando perfeitamente!"
    }

def teste_com_erro():
    """Job que gera erro proposital"""
    raise Exception("Erro de teste proposital!")

def teste_longo():
    """Job que demora mais tempo"""
    for i in range(5):
        print(f"Processando... {i+1}/5")
        time.sleep(1)
    return "Processamento longo concluído!"