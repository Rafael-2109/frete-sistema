"""
Script de Alimentação Inicial - Contas a Receber (Desde 24/11/2025)
====================================================================

Este script faz a carga inicial de TODOS os dados do Odoo desde 24/11/2025
para a tabela contas_a_receber.

Data: 2025-11-27
Autor: Sistema de Fretes

Uso:
    python scripts/migrations/alimentacao_inicial_contas_receber.py
"""

import sys
import os
from datetime import date

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db
from app.financeiro.services.sincronizacao_contas_receber_service import SincronizacaoContasReceberService
from app.financeiro.models import ContasAReceber
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def alimentacao_inicial():
    """
    Executa a alimentação inicial de Contas a Receber desde 24/11/2025.
    Busca TODOS os registros do período, sem filtro de chave.
    """
    app = create_app()

    with app.app_context():
        print("\n" + "=" * 70)
        print("📊 ALIMENTAÇÃO INICIAL - CONTAS A RECEBER (DESDE 24/11/2025)")
        print("=" * 70)

        # Data inicial: 24/11/2025
        data_inicio = date(2025, 11, 24)

        print(f"\n📅 Data inicial: {data_inicio}")
        print(f"📅 Data final: {date.today()}")

        # Verificar se já existem dados
        total_existente = ContasAReceber.query.count()
        if total_existente > 0:
            print(f"\n⚠️  Já existem {total_existente} registros na tabela contas_a_receber")
            resposta = input("   Deseja continuar mesmo assim? (s/N): ")
            if resposta.lower() != 's':
                print("\n❌ Operação cancelada pelo usuário.")
                return

        # Criar serviço e executar sincronização
        service = SincronizacaoContasReceberService()

        print("\n🔄 Iniciando sincronização desde 24/11/2025...")
        estatisticas = service.sincronizar(data_inicio=data_inicio, limite=None)

        # Resumo final
        print("\n" + "=" * 70)
        print("📋 RESUMO DA ALIMENTAÇÃO INICIAL")
        print("=" * 70)

        total_final = ContasAReceber.query.count()
        print(f"\n📊 Total de registros em contas_a_receber: {total_final}")
        print(f"   - Novos: {estatisticas.get('novos', 0)}")
        print(f"   - Atualizados: {estatisticas.get('atualizados', 0)}")
        print(f"   - Enriquecidos: {estatisticas.get('enriquecidos', 0)}")
        print(f"   - Snapshots: {estatisticas.get('snapshots_criados', 0)}")
        print(f"   - Erros: {estatisticas.get('erros', 0)}")

        if estatisticas.get('sucesso'):
            print("\n✅ Alimentação inicial concluída com sucesso!")
        else:
            print("\n❌ Alimentação inicial concluída com erros.")
            if estatisticas.get('erro'):
                print(f"   Erro: {estatisticas.get('erro')}")

        # Mostrar amostra de dados
        amostra = ContasAReceber.query.limit(5).all()
        if amostra:
            print("\n📄 Amostra de registros:")
            for conta in amostra:
                raz = conta.raz_social_red or (conta.raz_social[:30] if conta.raz_social else 'N/A')
                valor = conta.valor_titulo if conta.valor_titulo else 0
                print(f"   - {conta.empresa_nome} | NF {conta.titulo_nf}-{conta.parcela} | {raz} | R$ {valor:.2f}")

        print("\n")


if __name__ == '__main__':
    alimentacao_inicial()
