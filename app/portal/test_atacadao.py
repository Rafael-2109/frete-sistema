#!/usr/bin/env python
"""
Script de teste para validar a integração com o portal Atacadão
"""

import os
import sys
from pathlib import Path
from datetime import datetime, date, timedelta

# Adicionar o diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app import create_app, db
from app.portal.models import PortalIntegracao, PortalConfiguracao
from app.portal.atacadao.models import ProdutoDeParaAtacadao
from app.portal.utils.grupo_empresarial import GrupoEmpresarial

def testar_grupo_empresarial():
    """Testa identificação de grupo empresarial por CNPJ"""
    print("\n📋 TESTE 1: Identificação de Grupo Empresarial")
    print("=" * 50)
    
    # CNPJs de teste
    cnpjs_teste = [
        ('93.209.765/0001-00', 'Atacadão S.A.'),
        ('75.315.333/0001-30', 'Atacadão Distribuição'),
        ('00.063.960/0001-34', 'Atacadão Comercial'),
        ('01.157.555/0001-00', 'Tenda Atacado'),
        ('06.057.223/0001-71', 'Assaí/Sendas'),
        ('12.345.678/0001-90', 'Empresa Desconhecida')
    ]
    
    for cnpj, nome in cnpjs_teste:
        grupo = GrupoEmpresarial.identificar_grupo(cnpj)
        portal = GrupoEmpresarial.identificar_portal(cnpj)
        cnpj_formatado = GrupoEmpresarial.formatar_cnpj(cnpj)
        
        if grupo:
            print(f"✅ {cnpj_formatado} ({nome})")
            print(f"   Grupo: {grupo}")
            print(f"   Portal: {portal}")
        else:
            print(f"❌ {cnpj_formatado} ({nome}) - Não identificado")
    
    return True

def testar_modelos_portal():
    """Testa criação e consulta de modelos do portal"""
    print("\n📋 TESTE 2: Modelos do Portal")
    print("=" * 50)
    
    app = create_app()
    
    with app.app_context():
        try:
            # Teste 1: Criar configuração do Atacadão
            config = PortalConfiguracao.query.filter_by(portal='atacadao').first()
            
            if not config:
                config = PortalConfiguracao(
                    portal='atacadao',
                    url_portal='https://atacadao.hodiebooking.com.br',
                    url_login='https://atacadao.hodiebooking.com.br/',
                    seletores_css={
                        'campo_pedido': '#nr_pedido',
                        'botao_filtrar': '#enviarFiltros'
                    },
                    ativo=True
                )
                db.session.add(config)
                db.session.commit()
                print("✅ Configuração do Atacadão criada")
            else:
                print("✅ Configuração do Atacadão já existe")
            
            # Teste 2: Criar integração de teste
            integracao = PortalIntegracao(
                portal='atacadao',
                lote_id='TEST-001',
                tipo_lote='separacao',
                status='aguardando',
                data_solicitacao=datetime.now(),
                data_agendamento=date.today() + timedelta(days=2),
                usuario_solicitante='Teste Automático',
                dados_enviados={
                    'pedido_cliente': 'PC-123456',
                    'cnpj': '93.209.765/0001-00',
                    'transportadora': 'Transportadora Teste'
                }
            )
            db.session.add(integracao)
            db.session.commit()
            print(f"✅ Integração de teste criada - ID: {integracao.id}")
            
            # Teste 3: Criar DE-PARA de produtos
            depara = ProdutoDeParaAtacadao.obter_codigo_atacadao('PROD001', '93.209.765/0001-00')
            
            if not depara:
                depara = ProdutoDeParaAtacadao(
                    codigo_nosso='PROD001',
                    descricao_nosso='Produto Teste 001',
                    codigo_atacadao='ATK001',
                    descricao_atacadao='Produto Atacadão 001',
                    cnpj_cliente='93.209.765/0001-00',
                    fator_conversao=1.0,
                    ativo=True,
                    criado_por='Teste'
                )
                db.session.add(depara)
                db.session.commit()
                print("✅ DE-PARA de produto criado")
            else:
                print("✅ DE-PARA de produto já existe")
            
            # Teste 4: Consultar dados
            total_integracoes = PortalIntegracao.query.count()
            total_depara = ProdutoDeParaAtacadao.query.count()
            
            print(f"\n📊 Estatísticas:")
            print(f"   Total de integrações: {total_integracoes}")
            print(f"   Total de DE-PARA: {total_depara}")
            
            # Teste 5: Buscar código Atacadão
            codigo_atacadao = ProdutoDeParaAtacadao.obter_codigo_atacadao(
                'PROD001', 
                '93.209.765/0001-00'
            )
            
            if codigo_atacadao:
                print(f"✅ Mapeamento encontrado: PROD001 -> {codigo_atacadao}")
            else:
                print("❌ Mapeamento não encontrado")
            
            return True
            
        except Exception as e:
            print(f"❌ Erro: {e}")
            db.session.rollback()
            return False

def testar_mapper():
    """Testa o mapper do Atacadão"""
    print("\n📋 TESTE 3: Mapper do Atacadão")
    print("=" * 50)
    
    app = create_app()
    
    with app.app_context():
        try:
            from app.portal.atacadao.mapper import AtacadaoMapper
            from app.carteira.models import CarteiraPrincipal
            
            # Buscar um pedido real para testar
            pedido = CarteiraPrincipal.query.filter(
                CarteiraPrincipal.cnpj_cpf.like('93209765%')
            ).first()
            
            if pedido:
                print(f"✅ Pedido encontrado: {pedido.num_pedido}")
                
                # Testar mapeamento
                # Simular dados para teste
                dados_teste = {
                    'lote_id': 'TEST-001',
                    'num_pedido': pedido.num_pedido,
                    'cnpj_cpf': pedido.cnpj_cpf,
                    'pedido_cliente': pedido.pedido_cliente if hasattr(pedido, 'pedido_cliente') else 'PC-TEST',
                    'data_agendamento': date.today() + timedelta(days=2),
                    'transportadora': 'Transportadora Teste',
                    'tipo_veiculo': 'Carreta'
                }
                
                dados_mapeados = AtacadaoMapper.mapear_dados_sistema_para_portal(dados_teste)
                
                print(f"✅ Dados mapeados:")
                print(f"   CNPJ: {dados_mapeados.get('cnpj_cliente', 'N/A')}")
                print(f"   Pedido Cliente: {dados_mapeados.get('pedido_cliente', 'N/A')}")
                print(f"   Data Agendamento: {dados_mapeados.get('data_agendamento', 'N/A')}")
                
            else:
                print("⚠️ Nenhum pedido do Atacadão encontrado na carteira")
                
                # Criar exemplo fictício
                print("\n📝 Criando exemplo fictício para demonstração:")
                
                dados_exemplo = {
                    'lote_id': 'DEMO-001',
                    'cnpj_cpf': '93.209.765/0001-00',
                    'pedido_cliente': 'PC-DEMO-123',
                    'data_agendamento': date.today() + timedelta(days=3),
                    'transportadora': 'Demo Transportes',
                    'tipo_veiculo': 'Truck'
                }
                
                dados_portal = AtacadaoMapper.mapear_dados_sistema_para_portal(dados_exemplo)
                
                print(f"✅ Exemplo de mapeamento:")
                for chave, valor in dados_portal.items():
                    print(f"   {chave}: {valor}")
            
            return True
            
        except Exception as e:
            print(f"❌ Erro: {e}")
            import traceback
            traceback.print_exc()
            return False

def testar_browser_manager():
    """Testa o browser manager"""
    print("\n📋 TESTE 4: Browser Manager")
    print("=" * 50)
    
    try:
        from app.portal.browser_manager_v2 import BrowserManager
        
        # Testar detecção de ambiente
        manager = BrowserManager(mode='auto')
        
        print(f"✅ Modo detectado: {manager.mode}")
        print(f"   Ambiente: {manager._detect_environment()}")
        
        # Verificar Chrome Debug
        if manager._check_chrome_debug():
            print("✅ Chrome Debug disponível na porta 9222")
        else:
            print("⚠️ Chrome Debug não disponível")
            print("\n📝 Para usar Chrome existente, execute:")
            print('   google-chrome --remote-debugging-port=9222 --user-data-dir="/tmp/chrome_debug"')
        
        return True
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        return False

def main():
    """Executa todos os testes"""
    print("\n" + "=" * 60)
    print("🚀 TESTE DE INTEGRAÇÃO - PORTAL ATACADÃO")
    print("=" * 60)
    
    resultados = []
    
    # Executar testes
    testes = [
        ("Grupo Empresarial", testar_grupo_empresarial),
        ("Modelos Portal", testar_modelos_portal),
        ("Mapper Atacadão", testar_mapper),
        ("Browser Manager", testar_browser_manager)
    ]
    
    for nome, funcao_teste in testes:
        try:
            sucesso = funcao_teste()
            resultados.append((nome, sucesso))
        except Exception as e:
            print(f"\n❌ Erro no teste {nome}: {e}")
            resultados.append((nome, False))
    
    # Resumo
    print("\n" + "=" * 60)
    print("📊 RESUMO DOS TESTES")
    print("=" * 60)
    
    total = len(resultados)
    sucessos = sum(1 for _, sucesso in resultados if sucesso)
    
    for nome, sucesso in resultados:
        status = "✅" if sucesso else "❌"
        print(f"{status} {nome}")
    
    print(f"\n🎯 Resultado: {sucessos}/{total} testes passaram")
    
    if sucessos == total:
        print("\n✅ TODOS OS TESTES PASSARAM!")
        print("\n📝 Próximos passos:")
        print("1. Configure o Chrome com: google-chrome --remote-debugging-port=9222")
        print("2. Faça login manual no portal Atacadão")
        print("3. Execute a integração com um pedido real")
    else:
        print("\n⚠️ Alguns testes falharam. Verifique os erros acima.")
    
    return sucessos == total

if __name__ == '__main__':
    sys.exit(0 if main() else 1)