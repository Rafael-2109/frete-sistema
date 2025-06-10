#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para Inicializar Veículos Padrão
========================================

Este script inicializa os veículos padrão do sistema, incluindo o novo MASTER.
"""

import sys
import os

def inicializar_veiculos():
    """Inicializa veículos padrão no banco de dados"""
    
    try:
        # Importar módulos do sistema
        from app import create_app, db
        from app.veiculos.models import Veiculo
        
        print("🚚 === INICIALIZAÇÃO DE VEÍCULOS ===\n")
        
        # Criar aplicação
        app = create_app()
        
        with app.app_context():
            # Verificar se já existem veículos
            veiculos_existentes = Veiculo.query.count()
            print(f"📊 Veículos já cadastrados: {veiculos_existentes}")
            
            if veiculos_existentes > 0:
                print("⚠️ Já existem veículos no sistema.")
                resposta = input("Deseja adicionar apenas os que faltam? (s/n): ").lower()
                if resposta != 's':
                    print("❌ Operação cancelada pelo usuário.")
                    return False
            
            # Veículos padrão do sistema (pesos atualizados)
            veiculos_padrao = [
                {'nome': 'FIORINO', 'peso_maximo': 600, 'descricao': 'Veículo leve para pequenas entregas'},
                {'nome': 'VAN/HR', 'peso_maximo': 1700, 'descricao': 'Van padrão - capacidade ampliada'},
                {'nome': 'MASTER', 'peso_maximo': 2000, 'descricao': 'Veículo Master - capacidade compacta'},
                {'nome': 'IVECO', 'peso_maximo': 2500, 'descricao': 'Veículo Iveco - porte médio'},
                {'nome': '3/4', 'peso_maximo': 4500, 'descricao': 'Caminhão 3/4 - capacidade ampliada'},
                {'nome': 'TOCO', 'peso_maximo': 6500, 'descricao': 'Caminhão toco - capacidade ampliada'},
                {'nome': 'TRUCK', 'peso_maximo': 14500, 'descricao': 'Caminhão truck - alta capacidade'},
                {'nome': 'CARRETA', 'peso_maximo': 27000, 'descricao': 'Carreta - capacidade máxima'},
            ]
            
            veiculos_criados = []
            veiculos_ja_existentes = []
            
            for veiculo_data in veiculos_padrao:
                # Verificar se já existe
                veiculo_existente = Veiculo.query.filter_by(nome=veiculo_data['nome']).first()
                
                if veiculo_existente:
                    veiculos_ja_existentes.append(veiculo_data['nome'])
                    print(f"⏭️ {veiculo_data['nome']} - já existe ({veiculo_existente.peso_maximo:,.0f} kg)")
                else:
                    # Criar novo veículo
                    veiculo = Veiculo(
                        nome=veiculo_data['nome'],
                        peso_maximo=veiculo_data['peso_maximo']
                    )
                    
                    db.session.add(veiculo)
                    veiculos_criados.append(veiculo_data['nome'])
                    print(f"✅ {veiculo_data['nome']} - criado ({veiculo_data['peso_maximo']:,.0f} kg)")
            
            # Commit das alterações
            if veiculos_criados:
                db.session.commit()
                print(f"\n💾 {len(veiculos_criados)} veículo(s) criado(s) com sucesso!")
            else:
                print("\n📋 Nenhum veículo novo foi criado.")
            
            # Relatório final
            total_veiculos = Veiculo.query.count()
            print(f"\n📊 === RELATÓRIO FINAL ===")
            print(f"✅ Veículos criados: {len(veiculos_criados)}")
            print(f"⏭️ Já existentes: {len(veiculos_ja_existentes)}")
            print(f"📈 Total no sistema: {total_veiculos}")
            
            if veiculos_criados:
                print(f"🎯 Novos veículos: {', '.join(veiculos_criados)}")
            
            # Listar todos os veículos ordenados por peso
            print(f"\n🚚 === VEÍCULOS NO SISTEMA ===")
            todos_veiculos = Veiculo.query.order_by(Veiculo.peso_maximo.asc()).all()
            
            for i, veiculo in enumerate(todos_veiculos, 1):
                status = "🆕" if veiculo.nome in veiculos_criados else "✅"
                especial = " ⭐ NOVO!" if veiculo.nome == "MASTER" else ""
                print(f"{status} {i}. {veiculo.nome:<10} - {veiculo.peso_maximo:>6,.0f} kg{especial}")
            
            return True
            
    except ImportError as e:
        print(f"❌ Erro de importação: {e}")
        print("💡 Certifique-se de estar no diretório correto e ter o ambiente virtual ativo.")
        return False
    except Exception as e:
        print(f"❌ Erro na inicialização: {e}")
        import traceback
        traceback.print_exc()
        return False

def verificar_ambiente():
    """Verifica se o ambiente está configurado corretamente"""
    
    print("🔍 === VERIFICAÇÃO DO AMBIENTE ===\n")
    
    # Verificar se está no diretório correto
    if not os.path.exists('app'):
        print("❌ Diretório 'app' não encontrado!")
        print("💡 Execute este script na raiz do projeto frete_sistema")
        return False
    
    if not os.path.exists('config.py'):
        print("❌ Arquivo 'config.py' não encontrado!")
        return False
    
    print("✅ Estrutura do projeto OK")
    
    # Verificar se pode importar o app
    try:
        sys.path.insert(0, os.getcwd())
        from app import create_app
        print("✅ Módulos do Flask OK")
        return True
    except ImportError as e:
        print(f"❌ Erro ao importar módulos: {e}")
        print("💡 Ative o ambiente virtual: source venv/bin/activate (Linux/Mac) ou venv\\Scripts\\activate (Windows)")
        return False

if __name__ == "__main__":
    print("🚚 INICIALIZADOR DE VEÍCULOS - Sistema de Fretes\n")
    
    # Verificar ambiente
    if not verificar_ambiente():
        print("\n💥 Falha na verificação do ambiente!")
        sys.exit(1)
    
    # Executar inicialização
    sucesso = inicializar_veiculos()
    
    if sucesso:
        print("\n🎉 === INICIALIZAÇÃO CONCLUÍDA COM SUCESSO! ===")
        print("✅ Veículos prontos para uso no sistema")
        print("🌐 Acesse: /veiculos/admin para gerenciar")
        sys.exit(0)
    else:
        print("\n💥 === FALHA NA INICIALIZAÇÃO ===")
        sys.exit(1) 