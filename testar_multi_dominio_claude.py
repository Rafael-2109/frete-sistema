#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Teste da Nova Funcionalidade Multi-Domínio do Claude AI
Valida se o sistema consegue acessar múltiplas tabelas simultaneamente
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.claude_ai.claude_real_integration import ClaudeRealIntegration
import json

def testar_deteccao_multi_dominio():
    """Testa a detecção de consultas multi-domínio"""
    print("🧪 TESTE 1: Detecção de Consultas Multi-Domínio")
    print("=" * 60)
    
    claude = ClaudeRealIntegration()
    
    # Consultas que devem ativar multi-domínio
    consultas_multi = [
        "status geral do sistema",
        "análise completa dos dados",
        "resumo completo de todas as informações", 
        "relatório geral de entregas e fretes",
        "como está tudo no sistema",
        "dados completos dos clientes",
        "visão 360 do sistema"
    ]
    
    # Consultas que devem ser domínio único
    consultas_single = [
        "entregas do Assai",
        "fretes pendentes de aprovação",
        "pedidos abertos para cotação",
        "embarques aguardando saída"
    ]
    
    print("\n✅ CONSULTAS MULTI-DOMÍNIO:")
    for consulta in consultas_multi:
        analise = claude._analisar_consulta(consulta)
        multi_dominio = analise.get("multi_dominio", False)
        dominios = analise.get("dominios_solicitados", [])
        status = "✅ MULTI" if multi_dominio else "❌ SINGLE"
        print(f"   {status} | '{consulta}' → {len(dominios)} domínios: {dominios}")
    
    print("\n🎯 CONSULTAS DOMÍNIO ÚNICO:")
    for consulta in consultas_single:
        analise = claude._analisar_consulta(consulta)
        multi_dominio = analise.get("multi_dominio", False)
        dominio = analise.get("dominio", "")
        status = "✅ SINGLE" if not multi_dominio else "❌ MULTI"
        print(f"   {status} | '{consulta}' → Domínio: {dominio}")

def testar_carregamento_dados():
    """Testa o carregamento de dados multi-domínio"""
    print("\n\n🧪 TESTE 2: Carregamento de Dados Multi-Domínio")
    print("=" * 60)
    
    claude = ClaudeRealIntegration()
    
    # Simular análise multi-domínio
    analise_multi = {
        "tipo_consulta": "analise_completa",
        "multi_dominio": True,
        "dominios_solicitados": ["entregas", "pedidos", "fretes"],
        "periodo_dias": 30,
        "cliente_especifico": None
    }
    
    print("📊 Carregando dados de múltiplos domínios...")
    try:
        contexto = claude._carregar_contexto_inteligente(analise_multi)
        
        dados_especificos = contexto.get("dados_especificos", {})
        total_registros = contexto.get("registros_carregados", 0)
        
        print(f"\n✅ RESULTADO:")
        print(f"   Total de registros carregados: {total_registros}")
        print(f"   Domínios carregados: {len(dados_especificos)}")
        
        for dominio, dados in dados_especificos.items():
            count = dados.get("registros_carregados") or dados.get("total_registros", 0)
            print(f"   • {dominio.title()}: {count} registros")
            
        if len(dados_especificos) >= 2:
            print("\n🎉 SUCESSO: Sistema conseguiu carregar múltiplas tabelas!")
        else:
            print("\n❌ FALHA: Sistema carregou apenas 1 domínio")
            
    except Exception as e:
        print(f"\n❌ ERRO no carregamento: {e}")

def testar_analise_dominio():
    """Testa a detecção automática de múltiplos domínios"""
    print("\n\n🧪 TESTE 3: Detecção Automática de Múltiplos Domínios")
    print("=" * 60)
    
    claude = ClaudeRealIntegration()
    
    # Consulta que menciona múltiplos domínios
    consulta_mixed = "Como estão os fretes e entregas do Assai? E os pedidos pendentes?"
    
    print(f"📝 Consulta: '{consulta_mixed}'")
    
    analise = claude._analisar_consulta(consulta_mixed)
    
    print(f"\n📊 ANÁLISE:")
    print(f"   Tipo: {analise.get('tipo_consulta')}")
    print(f"   Multi-domínio: {analise.get('multi_dominio')}")
    print(f"   Domínio principal: {analise.get('dominio')}")
    print(f"   Domínios solicitados: {analise.get('dominios_solicitados', [])}")
    print(f"   Cliente detectado: {analise.get('cliente_especifico')}")
    
    if analise.get("multi_dominio"):
        print("\n🎉 SUCESSO: Detectou consulta multi-domínio automaticamente!")
    else:
        print("\n⚠️ INFO: Consulta classificada como domínio único")

def testar_descricao_contexto():
    """Testa a descrição do contexto multi-domínio"""
    print("\n\n🧪 TESTE 4: Descrição do Contexto Multi-Domínio")
    print("=" * 60)
    
    claude = ClaudeRealIntegration()
    
    # Simular dados carregados
    claude._ultimo_contexto_carregado = {
        "dados_especificos": {
            "entregas": {
                "total_registros": 150,
                "registros_carregados": 150
            },
            "pedidos": {
                "registros_carregados": 75,
                "pedidos": {
                    "estatisticas": {
                        "pedidos_abertos": 25,
                        "pedidos_cotados": 30,
                        "pedidos_faturados": 20,
                        "valor_total": 250000.50
                    }
                }
            },
            "fretes": {
                "registros_carregados": 90,
                "fretes": {
                    "estatisticas": {
                        "fretes_aprovados": 60,
                        "fretes_pendentes": 20,
                        "fretes_pagos": 10,
                        "valor_total_cotado": 180000.75,
                        "valor_total_pago": 120000.25
                    }
                }
            }
        },
        "registros_carregados": 315
    }
    
    analise_multi = {
        "multi_dominio": True,
        "dominios_solicitados": ["entregas", "pedidos", "fretes"],
        "periodo_dias": 30
    }
    
    descricao = claude._descrever_contexto_carregado(analise_multi)
    
    print("📝 DESCRIÇÃO GERADA:")
    print("-" * 40)
    print(descricao)
    print("-" * 40)
    
    # Verificar se contém informações de múltiplos domínios
    if all(dominio in descricao for dominio in ["ENTREGAS", "PEDIDOS", "FRETES"]):
        print("\n🎉 SUCESSO: Descrição inclui informações de múltiplos domínios!")
    else:
        print("\n❌ FALHA: Descrição não inclui todos os domínios esperados")

def main():
    """Executa todos os testes"""
    print("🚀 TESTE DA FUNCIONALIDADE MULTI-DOMÍNIO DO CLAUDE AI")
    print("=" * 70)
    print("Objetivo: Validar se o Claude consegue acessar múltiplas tabelas")
    print("=" * 70)
    
    try:
        # Executar todos os testes
        testar_deteccao_multi_dominio()
        testar_carregamento_dados()
        testar_analise_dominio()
        testar_descricao_contexto()
        
        print("\n\n" + "=" * 70)
        print("✅ TESTES CONCLUÍDOS!")
        print("=" * 70)
        print("\n💡 COMO TESTAR NO SISTEMA:")
        print("   1. Acesse o Claude AI no sistema")
        print("   2. Digite: 'status geral do sistema'")
        print("   3. Verifique se a resposta inclui dados de múltiplas tabelas")
        print("   4. Digite: 'análise completa dos dados'")
        print("   5. Confirme se consegue ver entregas + pedidos + fretes")
        
        print("\n🎯 COMANDOS PARA TESTAR:")
        print("   • 'resumo completo de todas as informações'")
        print("   • 'como está tudo no sistema'")
        print("   • 'dados completos dos clientes'")
        print("   • 'visão 360 do sistema'")
        
        
    except Exception as e:
        print(f"\n❌ ERRO DURANTE OS TESTES: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 