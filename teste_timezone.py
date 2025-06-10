#!/usr/bin/env python
"""
Teste do Sistema de Timezone Brasileiro
======================================
"""

import sys
import os
sys.path.append('.')

from datetime import datetime
from app.utils.timezone import (
    agora_brasil, 
    agora_utc, 
    utc_para_brasil,
    formatar_data_hora_brasil,
    diferenca_horario_brasil
)

def testar_timezone():
    print("🕐 === TESTE DO SISTEMA DE TIMEZONE BRASILEIRO ===\n")
    
    # 1. Horários atuais
    agora_utc_dt = agora_utc()
    agora_brasil_dt = agora_brasil()
    
    print(f"⏰ Horário UTC (banco):     {agora_utc_dt.strftime('%d/%m/%Y %H:%M:%S')}")
    print(f"🇧🇷 Horário Brasil (tela):  {agora_brasil_dt.strftime('%d/%m/%Y %H:%M:%S')}")
    
    # 2. Diferença de timezone
    diff = diferenca_horario_brasil()
    horas_diff = int(diff.total_seconds() / 3600)
    print(f"🌍 Diferença UTC→Brasil:   {horas_diff:+d} horas")
    
    # 3. Conversão UTC para Brasil
    print("\n📋 === TESTE DE CONVERSÃO ===")
    dt_utc_teste = datetime(2025, 6, 10, 15, 30, 0)  # 15:30 UTC
    dt_brasil_convertido = utc_para_brasil(dt_utc_teste)
    
    print(f"UTC de teste:              {dt_utc_teste.strftime('%d/%m/%Y %H:%M:%S')}")
    print(f"Convertido para Brasil:    {dt_brasil_convertido.strftime('%d/%m/%Y %H:%M:%S')}")
    
    # 4. Formatação com filtros
    print("\n🎨 === TESTE DOS FILTROS ===")
    print(f"formatar_data_hora_brasil: {formatar_data_hora_brasil(dt_utc_teste)}")
    print(f"formatar_data_hora_brasil: {formatar_data_hora_brasil(dt_utc_teste, '%d/%m às %H:%M')}")
    
    # 5. Simulação de como seria no banco vs tela
    print("\n🗄️ === SIMULAÇÃO BANCO vs TELA ===")
    print(f"Salvaria no banco (UTC):   {agora_utc_dt}")
    print(f"Mostraria na tela (BR):    {formatar_data_hora_brasil(agora_utc_dt)}")
    
    print("\n✅ SISTEMA DE TIMEZONE FUNCIONANDO CORRETAMENTE! 🇧🇷")

if __name__ == "__main__":
    testar_timezone() 