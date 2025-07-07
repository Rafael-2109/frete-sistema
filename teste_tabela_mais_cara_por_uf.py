#!/usr/bin/env python3
"""
🧪 TESTE: TABELA MAIS CARA POR TRANSPORTADORA/UF/MODALIDADE
Script para validar a implementação da nova lógica
"""

import sys
import os
sys.path.insert(0, '.')

from app.utils.frete_simulador import calcular_fretes_possiveis
from app.localidades.models import Cidade
from app.tabelas.models import TabelaFrete
from app.transportadoras.models import Transportadora
from app.vinculos.models import CidadeAtendida
from app import create_app

def testar_logica_tabela_mais_cara():
    """
    Testa se a nova lógica está funcionando corretamente
    """
    app = create_app()
    
    with app.app_context():
        print("=" * 60)
        print("🧪 TESTE: LÓGICA TABELA MAIS CARA POR UF")
        print("=" * 60)
        
        # TESTE 1: Busca cidade para teste
        print("\n📍 TESTE 1: Buscando cidade de teste...")
        cidade_sp = Cidade.query.filter_by(uf='SP').first()
        
        if not cidade_sp:
            print("❌ Nenhuma cidade SP encontrada!")
            return False
            
        print(f"✅ Cidade encontrada: {cidade_sp.nome}/{cidade_sp.uf}")
        
        # TESTE 2: Verificar se existem tabelas DIRETA para SP
        print("\n📋 TESTE 2: Verificando tabelas DIRETA para SP...")
        tabelas_sp = TabelaFrete.query.filter(
            TabelaFrete.uf_destino == 'SP',
            TabelaFrete.tipo_carga == 'DIRETA'
        ).limit(5).all()
        
        if not tabelas_sp:
            print("❌ Nenhuma tabela DIRETA para SP encontrada!")
            return False
            
        print(f"✅ {len(tabelas_sp)} tabelas DIRETA encontradas para SP")
        for tabela in tabelas_sp:
            print(f"   📋 {tabela.transportadora.razao_social if tabela.transportadora else 'N/A'} - {tabela.nome_tabela} - {tabela.modalidade}")
        
        # TESTE 3: Verificar vínculos
        print("\n🔗 TESTE 3: Verificando vínculos...")
        vinculos = CidadeAtendida.query.filter_by(codigo_ibge=cidade_sp.codigo_ibge).limit(3).all()
        
        if not vinculos:
            print("❌ Nenhum vínculo encontrado para a cidade!")
            return False
            
        print(f"✅ {len(vinculos)} vínculos encontrados")
        
        # TESTE 4: Executar cálculo de fretes com nova lógica
        print("\n🎯 TESTE 4: Executando cálculo com nova lógica...")
        
        try:
            resultados = calcular_fretes_possiveis(
                cidade_destino_id=cidade_sp.id,
                peso_utilizado=2000,  # 2 toneladas
                valor_carga=50000,    # R$ 50.000
                tipo_carga="DIRETA"
            )
            
            if not resultados:
                print("❌ Nenhum resultado retornado!")
                return False
                
            print(f"✅ {len(resultados)} opções de frete calculadas")
            
            # TESTE 5: Verificar se a nova lógica está ativa
            print("\n🔍 TESTE 5: Analisando resultados...")
            
            grupos_encontrados = {}
            for resultado in resultados:
                chave = (resultado['transportadora_id'], resultado['uf'], resultado['modalidade'])
                
                if chave not in grupos_encontrados:
                    grupos_encontrados[chave] = []
                grupos_encontrados[chave].append(resultado)
            
            print(f"✅ {len(grupos_encontrados)} grupos (transportadora/UF/modalidade) encontrados")
            
            # Verifica se há seleção da tabela mais cara
            for chave, opcoes in grupos_encontrados.items():
                transportadora_id, uf, modalidade = chave
                print(f"\n📊 GRUPO: Transp {transportadora_id} - {uf} - {modalidade}")
                
                for opcao in opcoes:
                    nome_tabela = opcao.get('nome_tabela', '')
                    valor_liquido = opcao.get('valor_liquido', 0)
                    criterio = opcao.get('criterio_selecao', 'N/A')
                    
                    print(f"   💰 {nome_tabela}: R$ {valor_liquido:.2f}")
                    print(f"   📝 Critério: {criterio}")
                    
                    # Verifica se foi aplicada a lógica de "mais cara"
                    if "MAIS CARA" in nome_tabela:
                        print(f"   ✅ LÓGICA APLICADA: Tabela mais cara selecionada!")
                    elif "única" in criterio.lower():
                        print(f"   ✅ CASO ÚNICO: Apenas uma tabela disponível")
                    else:
                        print(f"   ⚠️  Status não identificado")
            
            print("\n" + "=" * 60)
            print("🎯 RESULTADO DO TESTE:")
            print("=" * 60)
            
            # Verifica se encontrou evidências da nova lógica
            evidencias_encontradas = 0
            
            for resultado in resultados:
                nome_tabela = resultado.get('nome_tabela', '')
                criterio = resultado.get('criterio_selecao', '')
                
                if "MAIS CARA p/" in nome_tabela:
                    evidencias_encontradas += 1
                elif "única para" in criterio.lower():
                    evidencias_encontradas += 1
            
            if evidencias_encontradas > 0:
                print(f"✅ SUCESSO: {evidencias_encontradas} evidências da nova lógica encontradas!")
                print("✅ Sistema está aplicando tabela mais cara por transportadora/UF/modalidade")
                return True
            else:
                print("❌ FALHA: Não foram encontradas evidências da nova lógica")
                print("❌ Verificar se as modificações foram aplicadas corretamente")
                return False
                
        except Exception as e:
            print(f"❌ ERRO durante o teste: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

def main():
    """
    Função principal do teste
    """
    print("🚀 Iniciando teste da lógica de tabela mais cara por UF...")
    
    sucesso = testar_logica_tabela_mais_cara()
    
    if sucesso:
        print("\n🎉 TESTE CONCLUÍDO COM SUCESSO!")
        print("✅ A implementação está funcionando corretamente")
    else:
        print("\n❌ TESTE FALHOU!")
        print("❌ Verificar implementação e tentar novamente")
    
    return sucesso

if __name__ == "__main__":
    main() 