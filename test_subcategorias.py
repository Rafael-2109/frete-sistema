#!/usr/bin/env python3
"""
Script de teste para verificar se os filtros de subcategorias estão funcionando
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
app = create_app()
from app.producao.models import CadastroPalletizacao
from datetime import datetime

def testar_subcategorias():
    """Testa a funcionalidade de subcategorias"""
    
    with app.app_context():
        print("\n" + "="*60)
        print("TESTE DE SUBCATEGORIAS - CADASTRO PALLETIZAÇÃO")
        print("="*60)
        
        # 1. Verificar se os campos existem
        print("\n1. Verificando campos no modelo...")
        try:
            sample = CadastroPalletizacao.query.first()
            if sample:
                print(f"   ✓ Produto exemplo: {sample.cod_produto} - {sample.nome_produto}")
                print(f"   • Categoria: {sample.categoria_produto}")
                print(f"   • Embalagem: {sample.tipo_embalagem}")
                print(f"   • Matéria-Prima: {sample.tipo_materia_prima}")
                print(f"   • Linha Produção: {sample.linha_producao}")
            else:
                print("   ⚠ Nenhum produto cadastrado")
        except Exception as e:
            print(f"   ✗ Erro ao acessar campos: {e}")
        
        # 2. Inserir produtos de teste
        print("\n2. Inserindo produtos de teste...")
        produtos_teste = [
            {
                'cod_produto': 'TEST001',
                'nome_produto': 'PALMITO PUPUNHA INTEIRO 300G',
                'palletizacao': 144,
                'peso_bruto': 0.35,
                'categoria_produto': 'PALMITO',
                'tipo_embalagem': 'VD 12X500',
                'tipo_materia_prima': 'PALMITO',
                'linha_producao': '1106'
            },
            {
                'cod_produto': 'TEST002',
                'nome_produto': 'AZEITONA VERDE S/C 200G',
                'palletizacao': 120,
                'peso_bruto': 0.22,
                'categoria_produto': 'CONSERVAS',
                'tipo_embalagem': 'VD 12X500',
                'tipo_materia_prima': 'AZ VSC',
                'linha_producao': '1101 1/6'
            },
            {
                'cod_produto': 'TEST003',
                'nome_produto': 'MOLHO DE TOMATE TRADICIONAL 340G',
                'palletizacao': 180,
                'peso_bruto': 0.38,
                'categoria_produto': 'MOLHOS',
                'tipo_embalagem': 'GARRAFA 12X500',
                'tipo_materia_prima': 'TOMATE',
                'linha_producao': 'LF'
            }
        ]
        
        produtos_inseridos = 0
        for prod_data in produtos_teste:
            try:
                # Verificar se já existe
                existe = CadastroPalletizacao.query.filter_by(
                    cod_produto=prod_data['cod_produto']
                ).first()
                
                if existe:
                    # Atualizar
                    for key, value in prod_data.items():
                        setattr(existe, key, value)
                    print(f"   ✓ Atualizado: {prod_data['cod_produto']}")
                else:
                    # Criar novo
                    novo = CadastroPalletizacao(**prod_data)
                    db.session.add(novo)
                    print(f"   ✓ Inserido: {prod_data['cod_produto']}")
                
                produtos_inseridos += 1
                
            except Exception as e:
                print(f"   ✗ Erro no produto {prod_data['cod_produto']}: {e}")
        
        try:
            db.session.commit()
            print(f"\n   Total processado: {produtos_inseridos} produtos")
        except Exception as e:
            db.session.rollback()
            print(f"   ✗ Erro ao salvar: {e}")
        
        # 3. Testar consultas de valores únicos
        print("\n3. Testando consultas de valores únicos...")
        
        try:
            # Categorias
            categorias = db.session.query(CadastroPalletizacao.categoria_produto).distinct().filter(
                CadastroPalletizacao.categoria_produto.isnot(None)
            ).order_by(CadastroPalletizacao.categoria_produto).all()
            categorias = [c[0] for c in categorias if c[0]]
            print(f"   • Categorias encontradas ({len(categorias)}): {', '.join(categorias[:5])}")
            
            # Embalagens
            embalagens = db.session.query(CadastroPalletizacao.tipo_embalagem).distinct().filter(
                CadastroPalletizacao.tipo_embalagem.isnot(None)
            ).order_by(CadastroPalletizacao.tipo_embalagem).all()
            embalagens = [e[0] for e in embalagens if e[0]]
            print(f"   • Embalagens encontradas ({len(embalagens)}): {', '.join(embalagens[:5])}")
            
            # Matérias-primas
            materias = db.session.query(CadastroPalletizacao.tipo_materia_prima).distinct().filter(
                CadastroPalletizacao.tipo_materia_prima.isnot(None)
            ).order_by(CadastroPalletizacao.tipo_materia_prima).all()
            materias = [m[0] for m in materias if m[0]]
            print(f"   • Matérias-primas encontradas ({len(materias)}): {', '.join(materias[:5])}")
            
            # Linhas de produção
            linhas = db.session.query(CadastroPalletizacao.linha_producao).distinct().filter(
                CadastroPalletizacao.linha_producao.isnot(None)
            ).order_by(CadastroPalletizacao.linha_producao).all()
            linhas = [linha[0] for linha in linhas if linha[0]]
            print(f"   • Linhas de produção encontradas ({len(linhas)}): {', '.join(linhas[:5])}")
            
        except Exception as e:
            print(f"   ✗ Erro nas consultas: {e}")
        
        # 4. Testar filtros
        print("\n4. Testando filtros de produtos...")
        
        try:
            # Filtrar por categoria
            palmitos = CadastroPalletizacao.query.filter_by(categoria_produto='PALMITO').count()
            print(f"   • Produtos categoria PALMITO: {palmitos}")
            
            # Filtrar por embalagem
            vidros = CadastroPalletizacao.query.filter_by(tipo_embalagem='VD 12X500').count()
            print(f"   • Produtos embalagem VD 12X500: {vidros}")
            
            # Filtrar por matéria-prima
            azeitonas = CadastroPalletizacao.query.filter_by(tipo_materia_prima='AZ VSC').count()
            print(f"   • Produtos matéria-prima AZ VSC: {azeitonas}")
            
            # Filtrar por linha produção
            linha_1106 = CadastroPalletizacao.query.filter_by(linha_producao='1106').count()
            print(f"   • Produtos linha 1106: {linha_1106}")
            
            # Filtro combinado
            filtro_combo = CadastroPalletizacao.query.filter(
                CadastroPalletizacao.categoria_produto == 'CONSERVAS',
                CadastroPalletizacao.tipo_embalagem == 'VD 12X500'
            ).count()
            print(f"   • Produtos CONSERVAS em VD 12X500: {filtro_combo}")
            
        except Exception as e:
            print(f"   ✗ Erro nos filtros: {e}")
        
        # 5. Estatísticas gerais
        print("\n5. Estatísticas gerais...")
        try:
            total = CadastroPalletizacao.query.count()
            com_categoria = CadastroPalletizacao.query.filter(
                CadastroPalletizacao.categoria_produto.isnot(None)
            ).count()
            com_embalagem = CadastroPalletizacao.query.filter(
                CadastroPalletizacao.tipo_embalagem.isnot(None)
            ).count()
            com_materia = CadastroPalletizacao.query.filter(
                CadastroPalletizacao.tipo_materia_prima.isnot(None)
            ).count()
            com_linha = CadastroPalletizacao.query.filter(
                CadastroPalletizacao.linha_producao.isnot(None)
            ).count()
            
            print(f"   • Total de produtos: {total}")
            print(f"   • Com categoria: {com_categoria} ({100*com_categoria/total if total else 0:.1f}%)")
            print(f"   • Com embalagem: {com_embalagem} ({100*com_embalagem/total if total else 0:.1f}%)")
            print(f"   • Com matéria-prima: {com_materia} ({100*com_materia/total if total else 0:.1f}%)")
            print(f"   • Com linha produção: {com_linha} ({100*com_linha/total if total else 0:.1f}%)")
            
        except Exception as e:
            print(f"   ✗ Erro nas estatísticas: {e}")
        
        print("\n" + "="*60)
        print("TESTE CONCLUÍDO")
        print("="*60)
        
        # Verificar se o endpoint de API funciona
        print("\n6. Testando endpoint de API...")
        try:
            with app.test_client() as client:
                # Simular login (se necessário)
                from app.auth.models import Usuario
                user = Usuario.query.first()
                if user:
                    from flask_login import login_user
                    with client.session_transaction() as sess:
                        sess['_user_id'] = str(user.id)
                
                # Testar endpoint
                response = client.get('/estoque/saldo-estoque/api/subcategorias')
                if response.status_code == 200:
                    data = response.get_json()
                    if data and data.get('success'):
                        print("   ✓ API funcionando:")
                        print(f"     • Categorias: {len(data.get('categorias', []))}")
                        print(f"     • Embalagens: {len(data.get('embalagens', []))}")
                        print(f"     • Matérias-primas: {len(data.get('materias_primas', []))}")
                        print(f"     • Linhas produção: {len(data.get('linhas_producao', []))}")
                    else:
                        print(f"   ⚠ API retornou erro: {data}")
                else:
                    print(f"   ✗ API retornou status {response.status_code}")
        except Exception as e:
            print(f"   ✗ Erro ao testar API: {e}")
        
        print("\n✅ Teste finalizado!\n")

if __name__ == '__main__':
    testar_subcategorias()