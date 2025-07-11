#!/usr/bin/env python3
"""
Verificação rápida do status do sistema
"""

import json
import os
from datetime import datetime

def check_status():
    """Verifica status do último teste"""
    
    # Procurar arquivo mais recente
    arquivos = [f for f in os.listdir('.') if f.startswith('validacao_completa_')]
    
    if not arquivos:
        print("❌ Nenhum arquivo de validação encontrado")
        return
    
    # Pegar o mais recente
    arquivo_mais_recente = sorted(arquivos)[-1]
    
    with open(arquivo_mais_recente, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print("🎯 STATUS RÁPIDO DO SISTEMA")
    print("=" * 40)
    print(f"📊 Score Geral: {data['score_geral']}%")
    print(f"✅ Testes Aprovados: {data['testes_aprovados']}")
    print(f"❌ Testes Falharam: {data['testes_falharam']}")
    print(f"📋 Total de Testes: {data['testes_executados']}")
    
    # Classificação
    score = data['score_geral']
    if score >= 95:
        status = "🎉 EXCELENTE"
    elif score >= 80:
        status = "👍 BOM"
    elif score >= 60:
        status = "⚠️ PRECISA MELHORAR"
    else:
        status = "🔴 CRÍTICO"
    
    print(f"📈 Status: {status}")
    print(f"📅 Última validação: {arquivo_mais_recente}")
    
    if data['testes_falharam'] > 0:
        print("\n❌ FALHAS ENCONTRADAS:")
        falhas = [t for t in data['detalhes_testes'] if t['status'] == 'falhou']
        for falha in falhas[:3]:  # Mostrar apenas 3 primeiras
            print(f"  • {falha['teste']}")
    
    print("=" * 40)

if __name__ == "__main__":
    check_status() 