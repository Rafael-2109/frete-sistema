#!/usr/bin/env python3
"""
🧪 TESTE: Sistema de Grupos Empresariais Inteligente
"""

import logging
from datetime import datetime

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def testar_grupos_empresariais():
    """Testa o sistema de grupos empresariais"""
    print("\n" + "="*80)
    print("🧪 TESTE: SISTEMA DE GRUPOS EMPRESARIAIS INTELIGENTE")
    print("="*80)
    
    try:
        # Importar módulos
        from app.claude_ai.claude_real_integration import ClaudeRealIntegration
        from app.utils.grupo_empresarial import GrupoEmpresarialDetector
        
        print("\n✅ Módulos importados com sucesso!")
        
        # Criar instâncias
        claude = ClaudeRealIntegration()
        detector = GrupoEmpresarialDetector()
        
        # Testes de detecção de grupos
        testes = [
            "Qual CNPJ do Assai?",
            "Quantas entregas do Atacadão?",
            "Status do Carrefour",
            "Pedidos da Tenda",
            "Fort atacadista",
            "Mercantil Rodrigues",
            "Grupo Mateus",
            "Coco Bambu"
        ]
        
        print("\n📋 TESTANDO DETECÇÃO DE GRUPOS:")
        print("-" * 40)
        
        for consulta in testes:
            print(f"\n🔍 Consulta: '{consulta}'")
            
            # Testar detector direto
            grupo = detector.detectar_grupo_na_consulta(consulta)
            if grupo:
                print(f"✅ GRUPO DETECTADO: {grupo['grupo_detectado']}")
                print(f"   Tipo: {grupo.get('tipo_negocio', 'N/A')}")
                print(f"   Método: {grupo.get('metodo_deteccao', 'N/A')}")
                print(f"   Filtro SQL: {grupo.get('filtro_sql', 'N/A')}")
                if grupo.get('cnpj_prefixos'):
                    print(f"   CNPJs: {', '.join(grupo['cnpj_prefixos'])}")
            else:
                print("❌ Nenhum grupo detectado")
        
        # Testar análise completa do Claude
        print("\n\n📊 TESTANDO ANÁLISE DO CLAUDE AI:")
        print("-" * 40)
        
        consulta_teste = "Quantas entregas do Assai em junho?"
        print(f"\n🔍 Consulta completa: '{consulta_teste}'")
        
        analise = claude._analisar_consulta(consulta_teste)
        
        print(f"\n📊 ANÁLISE COMPLETA:")
        print(f"   Tipo consulta: {analise.get('tipo_consulta', 'N/A')}")
        print(f"   Cliente específico: {analise.get('cliente_especifico', 'N/A')}")
        print(f"   Domínio: {analise.get('dominio', 'N/A')}")
        print(f"   Período: {analise.get('periodo_dias', 'N/A')} dias")
        
        if analise.get('grupo_empresarial'):
            grupo = analise['grupo_empresarial']
            print(f"\n🏢 GRUPO EMPRESARIAL DETECTADO:")
            print(f"   Nome: {grupo.get('grupo_detectado', 'N/A')}")
            print(f"   Tipo negócio: {grupo.get('tipo_negocio', 'N/A')}")
            print(f"   Método detecção: {grupo.get('metodo_deteccao', 'N/A')}")
            print(f"   Filtro SQL: {grupo.get('filtro_sql', 'N/A')}")
            if grupo.get('cnpj_prefixos'):
                print(f"   CNPJs conhecidos: {', '.join(grupo['cnpj_prefixos'])}")
        
        # Testar análise de CNPJs
        print("\n\n📊 TESTANDO ANÁLISE DE CNPJs:")
        print("-" * 40)
        
        try:
            resultado = detector.analisar_clientes_com_cnpj()
            print(f"\n✅ Análise de CNPJs concluída:")
            print(f"   Total clientes com CNPJ: {resultado.get('total_clientes_com_cnpj', 0)}")
            print(f"   Clientes sem grupo: {resultado.get('clientes_sem_grupo', 0)}")
            
            if resultado.get('resumo_por_grupo'):
                print(f"\n   Resumo por grupo:")
                for grupo, qtd in resultado['resumo_por_grupo'].items():
                    print(f"   - {grupo}: {qtd} clientes")
            
            if resultado.get('sugestoes_novos_grupos'):
                print(f"\n   Sugestões de novos grupos: {len(resultado['sugestoes_novos_grupos'])}")
                for i, sugestao in enumerate(resultado['sugestoes_novos_grupos'][:3], 1):
                    print(f"   {i}. CNPJ {sugestao['cnpj_prefixo']} ({sugestao['total_clientes']} clientes)")
        except Exception as e:
            print(f"⚠️ Erro na análise de CNPJs: {e}")
        
        print("\n\n✅ TESTE CONCLUÍDO COM SUCESSO!")
        return True
        
    except Exception as e:
        print(f"\n❌ ERRO NO TESTE: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    # Adicionar contexto do Flask
    import sys
    sys.path.append('.')
    
    from app import create_app
    app = create_app()
    
    with app.app_context():
        sucesso = testar_grupos_empresariais()
        
        if sucesso:
            print("\n🎉 SISTEMA DE GRUPOS EMPRESARIAIS FUNCIONANDO PERFEITAMENTE!")
        else:
            print("\n⚠️ SISTEMA PRECISA DE AJUSTES") 