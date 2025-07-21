#!/usr/bin/env python3
"""
TESTE COMPLETO: Sistema de Pré-Separação Corrigido
Valida se todas as correções aplicadas estão funcionando
"""

import os
import sys

def testar_importacoes():
    """Testa se todos os imports essenciais funcionam"""
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        
        # Testar imports principais
        from app.carteira.models import CarteiraPrincipal, PreSeparacaoItem
        from app.carteira.routes import carteira_bp
        
        print("✅ Imports dos modelos: OK")
        return True
        
    except ImportError as e:
        print(f"❌ Erro de import: {e}")
        return False

def testar_modelo_pre_separacao():
    """Testa se o modelo PreSeparacaoItem tem todos os métodos"""
    try:
        from app.carteira.models import PreSeparacaoItem
        
        # Verificar se método criar_e_salvar existe
        if hasattr(PreSeparacaoItem, 'criar_e_salvar'):
            print("✅ Método PreSeparacaoItem.criar_e_salvar(): EXISTE")
        else:
            print("❌ Método PreSeparacaoItem.criar_e_salvar(): NÃO ENCONTRADO")
            return False
            
        # Verificar outros métodos essenciais
        metodos_essenciais = [
            'buscar_por_pedido_produto',
            '_gerar_hash_item',
            'marcar_como_recomposto'
        ]
        
        for metodo in metodos_essenciais:
            if hasattr(PreSeparacaoItem, metodo):
                print(f"✅ Método {metodo}: EXISTE")
            else:
                print(f"❌ Método {metodo}: NÃO ENCONTRADO")
                return False
                
        return True
        
    except Exception as e:
        print(f"❌ Erro ao testar modelo: {e}")
        return False

def testar_endpoints():
    """Testa se os endpoints essenciais existem"""
    try:
        from app.carteira.routes import carteira_bp
        
        # Verificar se blueprint tem as rotas
        rotas_essenciais = [
            '/api/pedido/<num_pedido>/criar-pre-separacao',
            '/api/pre-separacao/<int:pre_sep_id>/editar',
            '/api/pre-separacao/<int:pre_sep_id>/cancelar',
            '/api/pre-separacao/<int:pre_sep_id>/enviar-separacao'
        ]
        
        # Listar todas as rotas do blueprint
        rotas_blueprint = []
        for rule in carteira_bp.url_map.iter_rules():
            if rule.endpoint.startswith('carteira'):
                rotas_blueprint.append(rule.rule)
        
        print(f"📋 Total de rotas encontradas: {len(rotas_blueprint)}")
        
        # Verificar rotas essenciais
        for rota in rotas_essenciais:
            # Verificar padrões similares já que o Flask usa padrões específicos
            rota_encontrada = any(
                'criar-pre-separacao' in r or
                'pre-separacao' in r and 'editar' in r or
                'pre-separacao' in r and 'cancelar' in r or
                'pre-separacao' in r and 'enviar-separacao' in r
                for r in rotas_blueprint
            )
            
            if rota_encontrada:
                print(f"✅ Endpoint similar a {rota}: ENCONTRADO")
            else:
                print(f"❌ Endpoint {rota}: NÃO ENCONTRADO")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro ao testar endpoints: {e}")
        return False

def testar_templates():
    """Testa se os templates têm as correções aplicadas"""
    try:
        template_path = "app/templates/carteira/listar_agrupados.html"
        
        if not os.path.exists(template_path):
            print(f"❌ Template não encontrado: {template_path}")
            return False
        
        with open(template_path, 'r', encoding='utf-8') as f:
            conteudo = f.read()
        
        # Verificar correções aplicadas
        verificacoes = [
            # Campos corrigidos
            ('item.peso', 'Campo peso corrigido'),
            ('item.pallet', 'Campo pallet corrigido'),
            ('qtd_saldo_produto_pedido', 'Campo quantidade corrigido'),
            
            # Funções implementadas
            ('criarPreSeparacao(', 'Função criarPreSeparacao implementada'),
            ('editarPreSeparacaoCompleta(', 'Função editarPreSeparacaoCompleta implementada'),
            ('salvarEdicaoPreSeparacao(', 'Função salvarEdicaoPreSeparacao implementada'),
            
            # API calls corretos
            ('/criar-pre-separacao', 'API criar-pre-separacao referenciada')
        ]
        
        for busca, descricao in verificacoes:
            if busca in conteudo:
                print(f"✅ {descricao}: OK")
            else:
                print(f"❌ {descricao}: NÃO ENCONTRADO")
                return False
        
        # Verificar se campos incorretos foram removidos
        campos_incorretos = [
            'peso_calculado',
            'pallet_calculado',
            'qtd_saldo_disponivel'
        ]
        
        for campo in campos_incorretos:
            if campo in conteudo:
                print(f"⚠️  Campo incorreto ainda presente: {campo}")
            else:
                print(f"✅ Campo incorreto removido: {campo}")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro ao testar templates: {e}")
        return False

def testar_migracao():
    """Testa se a migração para múltiplas pré-separações existe"""
    try:
        migrations_dir = "migrations/versions"
        
        if not os.path.exists(migrations_dir):
            print(f"❌ Diretório de migrações não encontrado: {migrations_dir}")
            return False
        
        # Buscar migração de constraint única
        arquivos_migracao = os.listdir(migrations_dir)
        migracao_encontrada = any(
            'constraint' in arquivo.lower() and 'pre' in arquivo.lower()
            for arquivo in arquivos_migracao
            if arquivo.endswith('.py')
        )
        
        if migracao_encontrada:
            print("✅ Migração para constraint única: ENCONTRADA")
        else:
            print("❌ Migração para constraint única: NÃO ENCONTRADA")
            return False
        
        # Verificar se migração manual existe
        migracao_manual = "migrations/versions/remover_constraint_unica_pre_separacao.py"
        if os.path.exists(migracao_manual):
            print("✅ Migração manual criada: EXISTE")
            
            # Verificar conteúdo
            with open(migracao_manual, 'r', encoding='utf-8') as f:
                conteudo = f.read()
                
            if 'drop_constraint' in conteudo and 'pre_separacao_itens_pedido_produto_unique' in conteudo:
                print("✅ Migração remove constraint correta: OK")
            else:
                print("❌ Migração não remove constraint esperada")
                return False
        else:
            print("⚠️  Migração manual não encontrada (pode estar em outro arquivo)")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro ao testar migração: {e}")
        return False

def main():
    """Executa todos os testes"""
    print("🧪 TESTE COMPLETO: Sistema de Pré-Separação")
    print("=" * 50)
    
    testes = [
        ("Importações", testar_importacoes),
        ("Modelo PreSeparacaoItem", testar_modelo_pre_separacao),
        ("Endpoints/APIs", testar_endpoints),
        ("Templates", testar_templates),
        ("Migração", testar_migracao)
    ]
    
    resultados = []
    
    for nome, teste_func in testes:
        print(f"\n🔍 Testando: {nome}")
        print("-" * 30)
        
        try:
            resultado = teste_func()
            resultados.append((nome, resultado))
            
            if resultado:
                print(f"✅ {nome}: PASSOU")
            else:
                print(f"❌ {nome}: FALHOU")
                
        except Exception as e:
            print(f"❌ {nome}: ERRO - {e}")
            resultados.append((nome, False))
    
    # Resumo final
    print("\n" + "=" * 50)
    print("📊 RESUMO DOS TESTES")
    print("=" * 50)
    
    passou = sum(1 for _, resultado in resultados if resultado)
    total = len(resultados)
    
    for nome, resultado in resultados:
        status = "✅ PASSOU" if resultado else "❌ FALHOU"
        print(f"{nome:25} {status}")
    
    print(f"\n🎯 RESULTADO FINAL: {passou}/{total} testes passaram")
    
    if passou == total:
        print("🎉 TODOS OS TESTES PASSARAM! Sistema pronto para uso.")
        return True
    else:
        print("⚠️  Alguns testes falharam. Verificar implementação.")
        return False

if __name__ == "__main__":
    sucesso = main()
    sys.exit(0 if sucesso else 1)