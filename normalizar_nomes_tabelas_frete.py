#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para Normalizar Nomes de Tabelas nas Tabelas de Frete
============================================================

Este script converte todos os nomes de tabelas na tabela 'tabelas_frete' 
para MAIÚSCULA, garantindo compatibilidade com os vínculos.
"""

import sys
from app import create_app, db
from app.tabelas.models import TabelaFrete
from app.vinculos.models import CidadeAtendida

def normalizar_nomes_tabelas_frete():
    """Normaliza todos os nomes de tabelas para maiúscula na tabela tabelas_frete"""
    
    app = create_app()
    
    with app.app_context():
        print("🔧 === NORMALIZAÇÃO DE NOMES DE TABELAS (TABELAS_FRETE) ===")
        
        # 1. Buscar todas as tabelas de frete
        tabelas = TabelaFrete.query.all()
        total_tabelas = len(tabelas)
        
        print(f"📊 Total de tabelas de frete encontradas: {total_tabelas}")
        
        if total_tabelas == 0:
            print("⚠️ Nenhuma tabela de frete encontrada.")
            return
        
        # 2. Analisar estado atual
        tabelas_minuscula = 0
        tabelas_maiuscula = 0
        
        for tabela in tabelas:
            if tabela.nome_tabela != tabela.nome_tabela.upper():
                tabelas_minuscula += 1
            else:
                tabelas_maiuscula += 1
        
        print(f"📈 Tabelas em maiúscula: {tabelas_maiuscula}")
        print(f"📉 Tabelas em minúscula/misto: {tabelas_minuscula}")
        
        if tabelas_minuscula == 0:
            print("✅ Todas as tabelas já estão em maiúscula!")
            return
        
        # 3. Confirmar execução
        print(f"\n🔄 Será feita a conversão de {tabelas_minuscula} tabelas para MAIÚSCULA.")
        print("⚠️ Esta operação é irreversível!")
        
        confirmacao = input("Deseja continuar? (digite 'SIM' para confirmar): ").strip().upper()
        
        if confirmacao != 'SIM':
            print("❌ Operação cancelada pelo usuário.")
            return
        
        # 4. Executar normalização
        print("\n🔧 Iniciando normalização...")
        
        contador_alterados = 0
        contador_erros = 0
        
        for tabela in tabelas:
            try:
                nome_original = tabela.nome_tabela
                nome_normalizado = nome_original.upper().strip()
                
                if nome_original != nome_normalizado:
                    tabela.nome_tabela = nome_normalizado
                    contador_alterados += 1
                    
                    if contador_alterados % 100 == 0:
                        print(f"💾 {contador_alterados} tabelas processadas...")
                        
            except Exception as e:
                print(f"❌ Erro na tabela ID {tabela.id}: {e}")
                contador_erros += 1
        
        # 5. Salvar alterações
        try:
            db.session.commit()
            print("✅ Alterações salvas no banco de dados!")
        except Exception as e:
            db.session.rollback()
            print(f"❌ Erro ao salvar: {e}")
            return
        
        # 6. Relatório final
        print("\n📊 === RELATÓRIO FINAL ===")
        print(f"✅ Tabelas alteradas: {contador_alterados}")
        print(f"⚠️ Erros encontrados: {contador_erros}")
        print(f"📈 Total processado: {total_tabelas}")
        
        # 7. Verificação pós-normalização - compatibilidade com vínculos
        print("\n🔍 Verificando compatibilidade com vínculos...")
        
        # Conta tabelas que agora TÊM vínculos compatíveis
        tabelas_com_vinculo = db.session.query(TabelaFrete.transportadora_id, TabelaFrete.nome_tabela).join(
            CidadeAtendida,
            db.and_(
                CidadeAtendida.transportadora_id == TabelaFrete.transportadora_id,
                CidadeAtendida.nome_tabela == TabelaFrete.nome_tabela
            )
        ).distinct().count()
        
        # Conta total de combinações únicas de tabelas
        total_combinacoes = db.session.query(TabelaFrete.transportadora_id, TabelaFrete.nome_tabela).distinct().count()
        
        tabelas_orfas = total_combinacoes - tabelas_com_vinculo
        
        print(f"📊 Combinações de tabelas com vínculos: {tabelas_com_vinculo}")
        print(f"📊 Combinações de tabelas órfãs: {tabelas_orfas}")
        print(f"📊 Percentual com vínculos: {(tabelas_com_vinculo/total_combinacoes*100):.1f}%")
        
        # 8. Sugestão baseada no resultado
        if tabelas_orfas > 0:
            print(f"\n💡 PRÓXIMOS PASSOS:")
            print(f"   1. Execute também: python normalizar_nomes_tabelas.py (para vínculos)")
            print(f"   2. Verifique se os vínculos estão importados corretamente")
            print(f"   3. {tabelas_orfas} tabelas ainda estão órfãs - pode ser necessário importar vínculos")
        
        print("\n🎉 Normalização de tabelas de frete concluída com sucesso!")

def verificar_compatibilidade():
    """Verifica compatibilidade entre nomes de tabelas e vínculos"""
    
    app = create_app()
    
    with app.app_context():
        print("🔍 === VERIFICAÇÃO DE COMPATIBILIDADE ===")
        
        # Busca diferenças de case entre tabelas e vínculos
        print("\n📋 Analisando diferenças de case...")
        
        # Tabelas de frete com case misturado
        tabelas_case_problema = db.session.query(TabelaFrete).filter(
            TabelaFrete.nome_tabela != db.func.upper(TabelaFrete.nome_tabela)
        ).distinct(TabelaFrete.nome_tabela).all()
        
        if tabelas_case_problema:
            print(f"📉 Tabelas de frete com case não-maiúscula:")
            for t in tabelas_case_problema[:10]:  # Mostra apenas 10 exemplos
                print(f"   • '{t.nome_tabela}' -> '{t.nome_tabela.upper()}'")
            if len(tabelas_case_problema) > 10:
                print(f"   ... e mais {len(tabelas_case_problema) - 10} tabelas")
        
        # Vínculos com case misturado
        vinculos_case_problema = db.session.query(CidadeAtendida).filter(
            CidadeAtendida.nome_tabela != db.func.upper(CidadeAtendida.nome_tabela)
        ).distinct(CidadeAtendida.nome_tabela).all()
        
        if vinculos_case_problema:
            print(f"📉 Vínculos com case não-maiúscula:")
            for v in vinculos_case_problema[:10]:  # Mostra apenas 10 exemplos
                print(f"   • '{v.nome_tabela}' -> '{v.nome_tabela.upper()}'")
            if len(vinculos_case_problema) > 10:
                print(f"   ... e mais {len(vinculos_case_problema) - 10} vínculos")
        
        # Estatísticas finais
        total_problemas = len(tabelas_case_problema) + len(vinculos_case_problema)
        
        print(f"\n📊 RESUMO:")
        print(f"   • Tabelas de frete com problema de case: {len(tabelas_case_problema)}")
        print(f"   • Vínculos com problema de case: {len(vinculos_case_problema)}")
        print(f"   • Total de problemas: {total_problemas}")
        
        if total_problemas > 0:
            print(f"\n💡 RECOMENDAÇÃO:")
            if len(tabelas_case_problema) > 0:
                print(f"   1. Execute: python normalizar_nomes_tabelas_frete.py")
            if len(vinculos_case_problema) > 0:
                print(f"   2. Execute: python normalizar_nomes_tabelas.py")
        else:
            print(f"\n✅ Todos os nomes estão em maiúscula! Sistema consistente.")

if __name__ == "__main__":
    print("🔧 Normalizador de Nomes de Tabelas de Frete")
    print("Este script converterá todos os nomes de tabelas nas TABELAS DE FRETE para MAIÚSCULA")
    print("-" * 80)
    
    if len(sys.argv) > 1 and sys.argv[1] == "--verificar":
        verificar_compatibilidade()
    else:
        print("1. Verificando compatibilidade atual...")
        verificar_compatibilidade()
        
        print("\n2. Executando normalização...")
        normalizar_nomes_tabelas_frete() 