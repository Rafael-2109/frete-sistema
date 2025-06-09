from app import create_app, db
from app.tabelas.models import TabelaFrete
from app.transportadoras.models import Transportadora
from flask import json

def test_tabelas_existentes():
    app = create_app()
    with app.app_context():
        # 1. Verifica todas as tabelas
        todas_tabelas = TabelaFrete.query.all()
        print("\nTabelas encontradas no banco:")
        for tf in todas_tabelas:
            print(f"\nID: {tf.id}")
            print(f"Nome: {tf.nome_tabela}")
            print(f"Transportadora: {tf.transportadora.razao_social}")
            print(f"UF Origem: {tf.uf_origem}")
            print(f"UF Destino: {tf.uf_destino}")
            print(f"Tipo Carga: {tf.tipo_carga}")
            print(f"Modalidade: {tf.modalidade}")
            print("-" * 50)
            
        # 2. Verifica tabelas por transportadora
        print("\nTabelas por transportadora:")
        transportadoras = Transportadora.query.all()
        for transp in transportadoras:
            tabelas = TabelaFrete.query.filter_by(transportadora_id=transp.id).all()
            print(f"\n{transp.razao_social}:")
            if tabelas:
                for tf in tabelas:
                    print(f"- {tf.nome_tabela} ({tf.uf_origem}->{tf.uf_destino})")
            else:
                print("Nenhuma tabela encontrada")
            
if __name__ == '__main__':
    test_tabelas_existentes() 