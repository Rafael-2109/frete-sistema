#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para Normalizar Nomes de Tabelas nos Vínculos
==================================================

Este script converte todos os nomes de tabelas nos vínculos (CidadeAtendida) 
para MAIÚSCULA, resolvendo divergências de case com as tabelas de frete.
"""

import sys
from app import create_app, db
from app.vinculos.models import CidadeAtendida
from app.tabelas.models import TabelaFrete

def normalizar_nomes_tabelas():
    """Normaliza todos os nomes de tabelas para maiúscula"""
    
    app = create_app()
    
    with app.app_context():
        print("🔧 === NORMALIZAÇÃO DE NOMES DE TABELAS ===")
        
        # 1. Buscar todos os vínculos
        vinculos = CidadeAtendida.query.all()
        total_vinculos = len(vinculos)
        
        print(f"📊 Total de vínculos encontrados: {total_vinculos}")
        
        if total_vinculos == 0:
            print("⚠️ Nenhum vínculo encontrado.")
            return
        
        # 2. Analisar estado atual
        vinculos_minuscula = 0
        vinculos_maiuscula = 0
        
        for vinculo in vinculos:
            if vinculo.nome_tabela != vinculo.nome_tabela.upper():
                vinculos_minuscula += 1
            else:
                vinculos_maiuscula += 1
        
        print(f"📈 Vínculos em maiúscula: {vinculos_maiuscula}")
        print(f"📉 Vínculos em minúscula/misto: {vinculos_minuscula}")
        
        if vinculos_minuscula == 0:
            print("✅ Todos os vínculos já estão em maiúscula!")
            return
        
        # 3. Confirmar execução
        print(f"\n🔄 Será feita a conversão de {vinculos_minuscula} vínculos para MAIÚSCULA.")
        print("⚠️ Esta operação é irreversível!")
        
        confirmacao = input("Deseja continuar? (digite 'SIM' para confirmar): ").strip().upper()
        
        if confirmacao != 'SIM':
            print("❌ Operação cancelada pelo usuário.")
            return
        
        # 4. Executar normalização
        print("\n🔧 Iniciando normalização...")
        
        contador_alterados = 0
        contador_erros = 0
        
        for vinculo in vinculos:
            try:
                nome_original = vinculo.nome_tabela
                nome_normalizado = nome_original.upper().strip()
                
                if nome_original != nome_normalizado:
                    vinculo.nome_tabela = nome_normalizado
                    contador_alterados += 1
                    
                    if contador_alterados % 100 == 0:
                        print(f"💾 {contador_alterados} vínculos processados...")
                        
            except Exception as e:
                print(f"❌ Erro no vínculo ID {vinculo.id}: {e}")
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
        print(f"✅ Vínculos alterados: {contador_alterados}")
        print(f"⚠️ Erros encontrados: {contador_erros}")
        print(f"📈 Total processado: {total_vinculos}")
        
        # 7. Verificação pós-normalização
        print("\n🔍 Verificando impacto nas tabelas órfãs...")
        
        # Conta tabelas que agora TÊM vínculos
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
        
        print("\n🎉 Normalização concluída com sucesso!")

if __name__ == "__main__":
    print("🔧 Normalizador de Nomes de Tabelas")
    print("Este script converterá todos os nomes de tabelas nos vínculos para MAIÚSCULA")
    print("-" * 70)
    
    normalizar_nomes_tabelas() 