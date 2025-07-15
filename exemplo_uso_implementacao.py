#!/usr/bin/env python3
"""
Exemplo Prático de Uso da Implementação
======================================

Este arquivo demonstra como usar a nova integração com Odoo
implementada corretamente.

Execução:
    python exemplo_uso_implementacao.py

Autor: Sistema de Fretes - Integração Odoo
Data: 2025-07-14
"""

import sys
import os
from datetime import datetime, timedelta
import json

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def exemplo_importacao_basica():
    """
    Exemplo de importação básica de faturamento
    """
    print("=== EXEMPLO 1: IMPORTAÇÃO BÁSICA ===")
    
    try:
        from app.odoo.services.faturamento_service import FaturamentoService
        
        # Criar instância do serviço
        service = FaturamentoService()
        
        # Importar dados do mês atual
        resultado = service.importar_faturamento_odoo()
        
        # Verificar resultado
        if resultado['success']:
            print(f"✅ Importação realizada com sucesso!")
            print(f"   - Total importado: {resultado['total_importado']} registros")
            print(f"   - Total processado: {resultado['total_processado']} registros")
            print(f"   - Timestamp: {resultado['timestamp']}")
        else:
            print(f"❌ Erro na importação: {resultado['message']}")
            
    except Exception as e:
        print(f"❌ Erro: {e}")

def exemplo_importacao_com_filtros():
    """
    Exemplo de importação com filtros específicos
    """
    print("\n=== EXEMPLO 2: IMPORTAÇÃO COM FILTROS ===")
    
    try:
        from app.odoo.services.faturamento_service import FaturamentoService
        
        service = FaturamentoService()
        
        # Definir filtros
        filtros = {
            'state': 'sale',                    # Apenas pedidos confirmados
            'data_inicio': '2025-07-01',        # A partir de julho
            'invoice_status': 'to invoice'      # Pendente de faturamento
        }
        
        print(f"Filtros aplicados: {json.dumps(filtros, indent=2)}")
        
        # Importar com filtros
        resultado = service.importar_faturamento_odoo(filtros)
        
        if resultado['success']:
            print(f"✅ Importação filtrada realizada com sucesso!")
            print(f"   - Total importado: {resultado['total_importado']} registros")
            print(f"   - Total processado: {resultado['total_processado']} registros")
            print(f"   - Filtros aplicados: {resultado['filtros_aplicados']}")
        else:
            print(f"❌ Erro na importação: {resultado['message']}")
            
    except Exception as e:
        print(f"❌ Erro: {e}")

def exemplo_busca_por_filtro():
    """
    Exemplo de busca de dados por filtro específico
    """
    print("\n=== EXEMPLO 3: BUSCA POR FILTRO ===")
    
    try:
        from app.odoo.services.faturamento_service import FaturamentoService
        
        service = FaturamentoService()
        
        # Buscar faturamento pendente
        dados = service.buscar_faturamento_por_filtro('faturamento_pendente')
        
        if dados:
            print(f"✅ Encontrados {len(dados)} registros pendentes de faturamento")
            
            # Mostrar exemplo do primeiro registro
            if dados:
                primeiro = dados[0]
                print("\nExemplo de registro encontrado:")
                print(f"   - Pedido: {primeiro.get('nome_pedido')}")
                print(f"   - Cliente: {primeiro.get('nome_cliente')}")
                print(f"   - Produto: {primeiro.get('nome_produto')}")
                print(f"   - Quantidade: {primeiro.get('quantidade_produto')}")
                print(f"   - Valor: R$ {primeiro.get('preco_unitario'):.2f}")
                print(f"   - Status: {primeiro.get('status_pedido')}")
        else:
            print("ℹ️ Nenhum registro pendente de faturamento encontrado")
            
    except Exception as e:
        print(f"❌ Erro: {e}")

def exemplo_sincronizacao_completa():
    """
    Exemplo de sincronização completa (histórico)
    """
    print("\n=== EXEMPLO 4: SINCRONIZAÇÃO COMPLETA ===")
    
    try:
        from app.odoo.services.faturamento_service import FaturamentoService
        
        service = FaturamentoService()
        
        # Sincronizar dados completos (mês atual + histórico)
        print("Iniciando sincronização completa (pode demorar alguns minutos)...")
        resultado = service.sincronizar_faturamento_completo()
        
        if resultado['success']:
            print(f"✅ Sincronização completa realizada com sucesso!")
            print(f"   - Total importado: {resultado['total_importado']} registros")
            print(f"   - Total processado: {resultado['total_processado']} registros")
            print(f"   - Mensagem: {resultado['message']}")
        else:
            print(f"❌ Erro na sincronização: {resultado['message']}")
            
    except Exception as e:
        print(f"❌ Erro: {e}")

def exemplo_teste_mapeamento():
    """
    Exemplo de teste do mapeamento de campos
    """
    print("\n=== EXEMPLO 5: TESTE DO MAPEAMENTO ===")
    
    try:
        from app.odoo.utils.campo_mapper import CampoMapper
        from app.odoo.utils.connection import get_connection
        
        # Conectar ao Odoo
        connection = get_connection()
        if not connection:
            print("❌ Falha na conexão com Odoo")
            return
            
        # Criar mapper
        mapper = CampoMapper()
        
        # Buscar dados de exemplo
        dados = mapper.buscar_dados_completos(connection, {}, limit=3)
        
        if dados:
            print(f"✅ Dados mapeados com sucesso! ({len(dados)} registros)")
            
            # Mostrar estrutura do primeiro registro
            primeiro = dados[0]
            print("\nCampos disponíveis no primeiro registro:")
            for campo, valor in list(primeiro.items())[:10]:
                print(f"   - {campo}: {valor}")
            print(f"   ... (total de {len(primeiro)} campos)")
            
            # Testar mapeamento para faturamento
            dados_faturamento = mapper.mapear_para_faturamento(dados)
            
            if dados_faturamento:
                print(f"\n✅ Mapeamento para faturamento: {len(dados_faturamento)} registros")
                
                # Mostrar campos mapeados
                primeiro_faturamento = dados_faturamento[0]
                campos_exemplo = [
                    'nome_pedido', 'codigo_produto', 'nome_produto',
                    'nome_cliente', 'cnpj_cliente', 'vendedor',
                    'quantidade_produto', 'preco_unitario', 'status_pedido'
                ]
                
                print("\nCampos mapeados para faturamento:")
                for campo in campos_exemplo:
                    valor = primeiro_faturamento.get(campo)
                    print(f"   - {campo}: {valor}")
        else:
            print("ℹ️ Nenhum dado encontrado para mapeamento")
            
    except Exception as e:
        print(f"❌ Erro: {e}")

def exemplo_verificacao_dados():
    """
    Exemplo de verificação dos dados importados
    """
    print("\n=== EXEMPLO 6: VERIFICAÇÃO DOS DADOS ===")
    
    try:
        from app.faturamento.models import FaturamentoProduto, RelatorioFaturamentoImportado
        from app import db
        
        # Contar registros em FaturamentoProduto
        total_produtos = db.session.query(FaturamentoProduto).count()
        print(f"📊 Total de produtos em FaturamentoProduto: {total_produtos}")
        
        # Contar registros em RelatorioFaturamentoImportado
        total_relatorios = db.session.query(RelatorioFaturamentoImportado).count()
        print(f"📊 Total de relatórios em RelatorioFaturamentoImportado: {total_relatorios}")
        
        # Mostrar últimos registros importados
        ultimos_produtos = db.session.query(FaturamentoProduto).order_by(
            FaturamentoProduto.created_at.desc()
        ).limit(3).all()
        
        if ultimos_produtos:
            print(f"\n📋 Últimos {len(ultimos_produtos)} produtos importados:")
            for produto in ultimos_produtos:
                print(f"   - {produto.numero_nf} | {produto.cod_produto} | {produto.nome_produto}")
        
        # Estatísticas por vendedor
        vendedores = db.session.query(
            FaturamentoProduto.vendedor,
            db.func.count(FaturamentoProduto.id).label('total')
        ).group_by(FaturamentoProduto.vendedor).order_by(db.text('total DESC')).limit(5).all()
        
        if vendedores:
            print(f"\n🏆 Top 5 vendedores por número de produtos:")
            for vendedor, total in vendedores:
                print(f"   - {vendedor}: {total} produtos")
                
    except Exception as e:
        print(f"❌ Erro: {e}")

def main():
    """
    Executa todos os exemplos
    """
    print("🚀 EXEMPLOS DE USO DA IMPLEMENTAÇÃO ODOO")
    print("=" * 50)
    
    # Exemplo 1: Importação básica
    exemplo_importacao_basica()
    
    # Exemplo 2: Importação com filtros
    exemplo_importacao_com_filtros()
    
    # Exemplo 3: Busca por filtro
    exemplo_busca_por_filtro()
    
    # Exemplo 4: Sincronização completa
    # exemplo_sincronizacao_completa()  # Comentado por ser demorado
    
    # Exemplo 5: Teste do mapeamento
    exemplo_teste_mapeamento()
    
    # Exemplo 6: Verificação dos dados
    exemplo_verificacao_dados()
    
    print("\n" + "=" * 50)
    print("✅ TODOS OS EXEMPLOS EXECUTADOS!")
    print("📚 Para mais informações, consulte: IMPLEMENTACAO_INTEGRACAO_ODOO.md")

if __name__ == "__main__":
    main() 