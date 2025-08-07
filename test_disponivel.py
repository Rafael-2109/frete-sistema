#!/usr/bin/env python
"""
Script para testar cálculo de disponibilidade
"""

from app import create_app, db
from app.estoque.services.estoque_tempo_real import ServicoEstoqueTempoReal
from app.estoque.models_tempo_real import EstoqueTempoReal
from datetime import date

app = create_app()

with app.app_context():
    # Recalcular ruptura D7 primeiro
    ServicoEstoqueTempoReal.calcular_ruptura_d7('4520145')
    db.session.commit()
    
    # Buscar estoque atualizado
    estoque = EstoqueTempoReal.query.filter_by(cod_produto='4520145').first()
    if estoque:
        print(f"Produto: {estoque.cod_produto} - {estoque.nome_produto}")
        print(f"Estoque Atual: {estoque.saldo_atual}")
        print(f"Est.Min.D+7 (banco): {estoque.menor_estoque_d7}")
        print(f"Dia Ruptura (banco): {estoque.dia_ruptura}")
    
    print("\n" + "="*60 + "\n")
    
    # Obter projeção completa
    projecao = ServicoEstoqueTempoReal.get_projecao_completa('4520145', dias=10)
    
    if projecao:
        print(f'Produto: {projecao["cod_produto"]} - {projecao["nome_produto"]}')
        print(f'Estoque Atual: {projecao["estoque_atual"]}')
        print(f'Est.Min.D+7 (calculado): {projecao["menor_estoque_d7"]}')
        print(f'Data Disponível: {projecao.get("data_disponivel")}')
        print(f'Qtd Disponível: {projecao.get("qtd_disponivel")}')
        print(f'Dia Ruptura: {projecao.get("dia_ruptura")}')
        print()
        print('Projeção D0-D10:')
        for p in projecao['projecao']:
            if p['entrada'] > 0 or p['saida'] > 0:
                print(f"  D{p['dia']} ({p['data']}): Entrada {p['entrada']}, Saída {p['saida']} → Saldo {p['saldo_final']}")