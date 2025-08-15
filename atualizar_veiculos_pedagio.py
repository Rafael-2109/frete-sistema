#!/usr/bin/env python
"""
Script para atualizar a tabela de veículos com dados para cálculo de pedágio
"""

from app import create_app, db
from app.veiculos.models import Veiculo

# Configuração dos veículos conforme solicitado
DADOS_VEICULOS = {
    # Carros (fator 1)
    'FIORINO': {'qtd_eixos': 2, 'tipo_veiculo': 'Carro', 'multiplicador': 1.0},
    'VAN/HR': {'qtd_eixos': 2, 'tipo_veiculo': 'Carro', 'multiplicador': 1.0},
    'MASTER': {'qtd_eixos': 2, 'tipo_veiculo': 'Carro', 'multiplicador': 1.0},
    
    # Caminhões (fator = número de eixos)
    'IVECO': {'qtd_eixos': 2, 'tipo_veiculo': 'Caminhão', 'multiplicador': 2.0},  # 2 eixos
    '3/4': {'qtd_eixos': 2, 'tipo_veiculo': 'Caminhão', 'multiplicador': 2.0},    # 2 eixos
    'TOCO': {'qtd_eixos': 2, 'tipo_veiculo': 'Caminhão', 'multiplicador': 2.0},   # 2 eixos (truck simples)
    'TRUCK': {'qtd_eixos': 3, 'tipo_veiculo': 'Caminhão', 'multiplicador': 3.0},  # 3 eixos
    'BI-TRUCK': {'qtd_eixos': 4, 'tipo_veiculo': 'Caminhão', 'multiplicador': 4.0}, # 4 eixos
    'CARRETA': {'qtd_eixos': 5, 'tipo_veiculo': 'Caminhão', 'multiplicador': 5.0},  # 5 eixos
    'CABOTAGEM': {'qtd_eixos': 5, 'tipo_veiculo': 'Caminhão', 'multiplicador': 5.0} # 5 eixos
}

def atualizar_veiculos():
    """Atualiza os veículos com dados de pedágio"""
    app = create_app()
    
    with app.app_context():
        # Primeiro, adicionar as colunas se não existirem
        try:
            from sqlalchemy import text
            db.session.execute(text("""
                ALTER TABLE veiculos 
                ADD COLUMN IF NOT EXISTS qtd_eixos INTEGER,
                ADD COLUMN IF NOT EXISTS tipo_veiculo VARCHAR(20),
                ADD COLUMN IF NOT EXISTS multiplicador_pedagio FLOAT DEFAULT 1.0
            """))
            db.session.commit()
            print("✅ Colunas adicionadas à tabela veiculos")
        except Exception as e:
            print(f"⚠️ Erro ao adicionar colunas (podem já existir): {e}")
            db.session.rollback()
        
        # Atualizar cada veículo
        veiculos = Veiculo.query.all()
        
        for veiculo in veiculos:
            if veiculo.nome in DADOS_VEICULOS:
                dados = DADOS_VEICULOS[veiculo.nome]
                veiculo.qtd_eixos = dados['qtd_eixos']
                veiculo.tipo_veiculo = dados['tipo_veiculo']
                veiculo.multiplicador_pedagio = dados['multiplicador']
                print(f"✅ Atualizado: {veiculo.nome:15} - {dados['qtd_eixos']} eixos - Tipo: {dados['tipo_veiculo']:10} - Fator: {dados['multiplicador']:.1f}x")
        
        db.session.commit()
        print("\n✅ Todos os veículos foram atualizados com sucesso!")
        
        # Mostrar resultado final
        print("\n📊 VEÍCULOS ATUALIZADOS:")
        print("-" * 100)
        print(f"{'NOME':15} | {'PESO MÁX':12} | {'TIPO':10} | {'EIXOS':6} | {'FATOR':6} | OBSERVAÇÃO")
        print("-" * 100)
        
        for veiculo in Veiculo.query.order_by(Veiculo.peso_maximo).all():
            obs = ""
            if veiculo.tipo_veiculo == 'Carro':
                obs = "Categoria B (até 3.500kg)"
            elif veiculo.tipo_veiculo == 'Caminhão':
                obs = f"Pedágio = Carro x {veiculo.multiplicador_pedagio:.0f}"
                
            print(f"{veiculo.nome:15} | {veiculo.peso_maximo:8.0f} kg | {veiculo.tipo_veiculo:10} | "
                  f"{veiculo.qtd_eixos:6} | {veiculo.multiplicador_pedagio:6.1f}x | {obs}")

if __name__ == "__main__":
    atualizar_veiculos()