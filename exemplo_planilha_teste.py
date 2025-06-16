#!/usr/bin/env python3
"""
📋 EXEMPLO - PLANILHA DE TESTE PARA MONITORAMENTO
Cria uma planilha de exemplo para testar o script de atualização
"""

import pandas as pd
from datetime import datetime, date

def criar_planilha_exemplo():
    """Cria uma planilha de exemplo para teste"""
    
    # Dados de exemplo
    dados = [
        {
            'numero_nf': '123456',
            'status': 'Entregue',
            'data_entrega_realizada': '15/01/2025',
        },
        {
            'numero_nf': '123457', 
            'situacao': 'Cancelada',
        },
        {
            'numero_nf': '123458',
            'finalizacao': 'Devolvida',
        },
        {
            'numero_nf': '123459',
            'Status': 'Entregue',
            'realizada': '20/01/2025',
        }
    ]
    
    # Cria DataFrame
    df = pd.DataFrame(dados)
    
    # Salva planilha
    arquivo = 'exemplo_monitoramento_teste.xlsx'
    df.to_excel(arquivo, index=False)
    
    print(f"✅ Planilha exemplo criada: {arquivo}")
    print(f"📋 Estrutura:")
    print(df.to_string(index=False))
    
    print(f"\n💡 EXEMPLOS DE NOMES ACEITOS PARA COLUNAS:")
    print(f"   Status: 'status', 'Status', 'situacao', 'finalizacao', 'status_finalizacao'")
    print(f"   Data entrega: 'data_entrega_realizada', 'realizada', 'dt_realizada'")
    print(f"   Embarque: 'data_embarque', 'embarque', 'dt_embarque'")
    
    return arquivo

if __name__ == '__main__':
    criar_planilha_exemplo() 