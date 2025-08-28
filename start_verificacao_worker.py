#!/usr/bin/env python3
"""
Script para iniciar o worker de verificação de protocolos
Uso: python start_verificacao_worker.py
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app.workers.verificacao_protocolo_worker import processar_verificacao_protocolo

if __name__ == '__main__':
    print("=" * 60)
    print("🚀 INICIANDO WORKER DE VERIFICAÇÃO DE PROTOCOLOS")
    print("=" * 60)
    print("Pressione Ctrl+C para parar")
    print("-" * 60)
    
    try:
        processar_verificacao_protocolo()
    except KeyboardInterrupt:
        print("\n" + "=" * 60)
        print("⏹️  Worker parado pelo usuário")
        print("=" * 60)