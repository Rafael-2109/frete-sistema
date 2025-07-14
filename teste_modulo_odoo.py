#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script de Teste do Módulo Odoo
==============================

Script para testar a implementação do módulo Odoo
e validar as funcionalidades principais.

Uso:
    python teste_modulo_odoo.py

Autor: Sistema de Fretes
Data: 2025-07-14
"""

import os
import sys
import unittest
from datetime import date, datetime

# Adicionar o diretório do projeto ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Testa se todos os imports funcionam"""
    try:
        print("🧪 Testando imports...")
        
        # Importar módulo principal
        from app.odoo import odoo_bp, get_faturamento_service, ODOO_CONFIG
        print("✅ Módulo principal importado com sucesso")
        
        # Importar utilitários
        from app.odoo.utils.connection import get_odoo_connection, test_connection
        from app.odoo.utils.mappers import get_faturamento_produto_mapper
        print("✅ Utilitários importados com sucesso")
        
        # Importar serviços
        from app.odoo.services.faturamento_service import FaturamentoService
        print("✅ Serviços importados com sucesso")
        
        # Importar rotas
        from app.odoo.routes.faturamento import faturamento_bp
        print("✅ Rotas importadas com sucesso")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro no import: {e}")
        return False

def test_configuration():
    """Testa se a configuração está correta"""
    try:
        print("\n🧪 Testando configuração...")
        
        from app.odoo import ODOO_CONFIG
        
        # Verificar campos obrigatórios
        required_fields = ['url', 'database', 'username', 'api_key']
        for field in required_fields:
            if field not in ODOO_CONFIG:
                print(f"❌ Campo obrigatório '{field}' não encontrado na configuração")
                return False
            if not ODOO_CONFIG[field]:
                print(f"❌ Campo '{field}' está vazio na configuração")
                return False
        
        print("✅ Configuração está correta")
        return True
        
    except Exception as e:
        print(f"❌ Erro na configuração: {e}")
        return False

def test_mappers():
    """Testa se os mapeadores funcionam"""
    try:
        print("\n🧪 Testando mapeadores...")
        
        from app.odoo.utils.mappers import (
            get_faturamento_produto_mapper,
            get_faturamento_mapper,
            get_carteira_mapper
        )
        
        # Testar mapeador de produto
        produto_mapper = get_faturamento_produto_mapper()
        
        # Dados de teste
        odoo_data = {
            'x_studio_nf_e': '123456',
            'partner_id': [1, 'Cliente Teste'],
            'quantity': 10.0,
            'l10n_br_total_nfe': 1000.0,
            'gross_weight': 2.5,
            'date': '2025-07-14',
            'state': 'posted'
        }
        
        mapped_data = produto_mapper.map_data(odoo_data)
        
        # Verificar se o peso total foi calculado corretamente
        expected_peso_total = 2.5 * 10.0  # peso_unitario * quantidade
        if mapped_data.get('peso_total') != expected_peso_total:
            print(f"❌ Cálculo de peso total incorreto: esperado {expected_peso_total}, obtido {mapped_data.get('peso_total')}")
            return False
        
        print("✅ Mapeadores funcionando corretamente")
        return True
        
    except Exception as e:
        print(f"❌ Erro nos mapeadores: {e}")
        return False

def test_service_initialization():
    """Testa se os serviços inicializam corretamente"""
    try:
        print("\n🧪 Testando inicialização dos serviços...")
        
        from app.odoo.services.faturamento_service import FaturamentoService
        
        # Inicializar serviço
        service = FaturamentoService()
        
        # Verificar se métodos existem
        methods = [
            'importar_faturamento_produtos',
            'gerar_faturamento_consolidado',
            'sincronizar_automatica',
            'obter_estatisticas',
            'validar_integridade'
        ]
        
        for method in methods:
            if not hasattr(service, method):
                print(f"❌ Método '{method}' não encontrado no serviço")
                return False
        
        print("✅ Serviços inicializados corretamente")
        return True
        
    except Exception as e:
        print(f"❌ Erro na inicialização dos serviços: {e}")
        return False

def test_model_field():
    """Testa se o campo peso_unitario_produto existe no modelo"""
    try:
        print("\n🧪 Testando campo peso_unitario_produto...")
        
        from app.faturamento.models import FaturamentoProduto
        
        # Verificar se o campo existe
        if not hasattr(FaturamentoProduto, 'peso_unitario_produto'):
            print("❌ Campo 'peso_unitario_produto' não encontrado no modelo FaturamentoProduto")
            return False
        
        print("✅ Campo peso_unitario_produto encontrado no modelo")
        return True
        
    except Exception as e:
        print(f"❌ Erro ao verificar modelo: {e}")
        return False

def test_blueprints():
    """Testa se os blueprints estão configurados corretamente"""
    try:
        print("\n🧪 Testando blueprints...")
        
        from app.odoo import odoo_bp
        from app.odoo.routes.faturamento import faturamento_bp
        
        # Verificar se blueprints existem
        if not odoo_bp:
            print("❌ Blueprint principal 'odoo_bp' não encontrado")
            return False
        
        if not faturamento_bp:
            print("❌ Blueprint 'faturamento_bp' não encontrado")
            return False
        
        # Verificar se as rotas estão registradas
        if not odoo_bp.deferred_functions:
            print("⚠️ Nenhuma rota registrada no blueprint principal")
        
        print("✅ Blueprints configurados corretamente")
        return True
        
    except Exception as e:
        print(f"❌ Erro nos blueprints: {e}")
        return False

def run_all_tests():
    """Executa todos os testes"""
    print("🚀 Iniciando testes do módulo Odoo...")
    print("=" * 50)
    
    tests = [
        test_imports,
        test_configuration,
        test_model_field,
        test_mappers,
        test_service_initialization,
        test_blueprints
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ Erro inesperado no teste {test.__name__}: {e}")
            failed += 1
    
    print("\n" + "=" * 50)
    print(f"📊 Resultados dos testes:")
    print(f"✅ Passou: {passed}")
    print(f"❌ Falhou: {failed}")
    print(f"📈 Taxa de sucesso: {passed/(passed+failed)*100:.1f}%")
    
    if failed == 0:
        print("\n🎉 Todos os testes passaram! O módulo Odoo está pronto para uso.")
        return True
    else:
        print(f"\n⚠️ {failed} teste(s) falharam. Verifique os problemas acima.")
        return False

def main():
    """Função principal"""
    if len(sys.argv) > 1 and sys.argv[1] == '--help':
        print(__doc__)
        return
    
    success = run_all_tests()
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main() 