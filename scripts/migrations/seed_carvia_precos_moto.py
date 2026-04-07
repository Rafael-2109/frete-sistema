"""
Seed: CarviaTabelaFrete + CarviaPrecoCategoriaMoto
===================================================
Cria tabelas de frete CarVia (pricing vazio) e vincula precos por categoria de moto.
Dados extraidos de template_tabelas_frete.xlsx (aba Precos Moto, 90 linhas).

Idempotente: verifica existencia antes de inserir.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app import create_app, db
from app.carvia.models import (
    CarviaCategoriaMoto, CarviaTabelaFrete, CarviaPrecoCategoriaMoto,
)
from app.utils.timezone import agora_utc_naive

# ---------------------------------------------------------------
# Dados do template (90 registros)
# Todas: uf_origem=SP, tipo_carga=FRACIONADA, modalidade=FRETE PESO
# ---------------------------------------------------------------
PRECOS = [
    # (nome_tabela, uf_destino, categoria_moto, valor_unitario)
    # --- CAPITAL / Leve ---
    ('CAPITAL', 'PR', 'Leve', 200),
    ('CAPITAL', 'DF', 'Leve', 250),
    ('CAPITAL', 'GO', 'Leve', 250),
    ('CAPITAL', 'MT', 'Leve', 250),
    ('CAPITAL', 'MS', 'Leve', 250),
    ('CAPITAL', 'RS', 'Leve', 250),
    ('CAPITAL', 'SC', 'Leve', 250),
    ('CAPITAL', 'AL', 'Leve', 300),
    ('CAPITAL', 'SE', 'Leve', 300),
    ('CAPITAL', 'BA', 'Leve', 300),
    ('CAPITAL', 'PE', 'Leve', 300),
    ('CAPITAL', 'CE', 'Leve', 300),
    ('CAPITAL', 'MA', 'Leve', 300),
    ('CAPITAL', 'PI', 'Leve', 300),
    ('CAPITAL', 'PB', 'Leve', 350),
    ('CAPITAL', 'TO', 'Leve', 350),
    ('CAPITAL', 'RN', 'Leve', 400),
    ('CAPITAL', 'RO', 'Leve', 400),
    ('CAPITAL', 'AP', 'Leve', 400),
    ('CAPITAL', 'PA', 'Leve', 400),
    ('CAPITAL', 'AC', 'Leve', 400),
    # --- INTERIOR / Leve ---
    ('INTERIOR', 'PR', 'Leve', 250),
    ('INTERIOR', 'DF', 'Leve', 320),
    ('INTERIOR', 'GO', 'Leve', 320),
    ('INTERIOR', 'MT', 'Leve', 350),
    ('INTERIOR', 'MS', 'Leve', 350),
    ('INTERIOR', 'RS', 'Leve', 300),
    ('INTERIOR', 'SC', 'Leve', 300),
    ('INTERIOR', 'AL', 'Leve', 400),
    ('INTERIOR', 'SE', 'Leve', 400),
    ('INTERIOR', 'BA', 'Leve', 500),
    ('INTERIOR', 'PE', 'Leve', 400),
    ('INTERIOR', 'CE', 'Leve', 400),
    ('INTERIOR', 'MA', 'Leve', 500),
    ('INTERIOR', 'PI', 'Leve', 500),
    ('INTERIOR', 'PB', 'Leve', 500),
    ('INTERIOR', 'TO', 'Leve', 500),
    ('INTERIOR', 'RN', 'Leve', 500),
    ('INTERIOR', 'RO', 'Leve', 500),
    ('INTERIOR', 'AP', 'Leve', 1200),
    ('INTERIOR', 'PA', 'Leve', 1200),
    ('INTERIOR', 'AC', 'Leve', 500),
    # --- CAPITAL / Pesado ---
    ('CAPITAL', 'PR', 'Pesado', 250),
    ('CAPITAL', 'DF', 'Pesado', 350),
    ('CAPITAL', 'GO', 'Pesado', 350),
    ('CAPITAL', 'MT', 'Pesado', 350),
    ('CAPITAL', 'MS', 'Pesado', 350),
    ('CAPITAL', 'RS', 'Pesado', 300),
    ('CAPITAL', 'SC', 'Pesado', 300),
    ('CAPITAL', 'AL', 'Pesado', 400),
    ('CAPITAL', 'SE', 'Pesado', 400),
    ('CAPITAL', 'BA', 'Pesado', 400),
    ('CAPITAL', 'PE', 'Pesado', 400),
    ('CAPITAL', 'CE', 'Pesado', 400),
    ('CAPITAL', 'MA', 'Pesado', 400),
    ('CAPITAL', 'PI', 'Pesado', 400),
    ('CAPITAL', 'PB', 'Pesado', 450),
    ('CAPITAL', 'TO', 'Pesado', 450),
    ('CAPITAL', 'RN', 'Pesado', 500),
    ('CAPITAL', 'RO', 'Pesado', 500),
    ('CAPITAL', 'AP', 'Pesado', 500),
    ('CAPITAL', 'PA', 'Pesado', 500),
    ('CAPITAL', 'AC', 'Pesado', 500),
    # --- INTERIOR / Pesado ---
    ('INTERIOR', 'PR', 'Pesado', 350),
    ('INTERIOR', 'DF', 'Pesado', 400),
    ('INTERIOR', 'GO', 'Pesado', 400),
    ('INTERIOR', 'MT', 'Pesado', 500),
    ('INTERIOR', 'MS', 'Pesado', 500),
    ('INTERIOR', 'RS', 'Pesado', 350),
    ('INTERIOR', 'SC', 'Pesado', 350),
    ('INTERIOR', 'AL', 'Pesado', 500),
    ('INTERIOR', 'SE', 'Pesado', 500),
    ('INTERIOR', 'BA', 'Pesado', 700),
    ('INTERIOR', 'PE', 'Pesado', 500),
    ('INTERIOR', 'CE', 'Pesado', 500),
    ('INTERIOR', 'MA', 'Pesado', 600),
    ('INTERIOR', 'PI', 'Pesado', 600),
    ('INTERIOR', 'PB', 'Pesado', 600),
    ('INTERIOR', 'TO', 'Pesado', 600),
    ('INTERIOR', 'RN', 'Pesado', 600),
    ('INTERIOR', 'RO', 'Pesado', 600),
    ('INTERIOR', 'AP', 'Pesado', 1400),
    ('INTERIOR', 'PA', 'Pesado', 1400),
    ('INTERIOR', 'AC', 'Pesado', 600),
    # --- REGIONAL / Leve ---
    ('REGIONAL', 'MT', 'Leve', 300),
    ('REGIONAL', 'MS', 'Leve', 300),
    ('REGIONAL', 'BA', 'Leve', 400),
    # --- REGIONAL / Pesado ---
    ('REGIONAL', 'MT', 'Pesado', 400),
    ('REGIONAL', 'MS', 'Pesado', 400),
    ('REGIONAL', 'BA', 'Pesado', 500),
]

UF_ORIGEM = 'SP'
TIPO_CARGA = 'FRACIONADA'
MODALIDADE = 'FRETE PESO'

def run():
    app = create_app()
    with app.app_context():
        agora = agora_utc_naive()
        criado_por = 'migration:seed_precos_moto'

        # 0. Resolver categorias por nome (nao hardcodar IDs)
        cats = {c.nome: c.id for c in CarviaCategoriaMoto.query.filter_by(ativo=True).all()}
        for cat_needed in ('Leve', 'Pesado'):
            if cat_needed not in cats:
                print(f"ERRO: Categoria '{cat_needed}' nao encontrada no banco!")
                return
        print(f"Categorias: {cats}")

        # 1. Identificar tabelas unicas necessarias
        tabelas_necessarias = set()
        for nome, uf_dest, _, _ in PRECOS:
            tabelas_necessarias.add((nome, uf_dest))

        # 2. Pre-cache tabelas existentes
        tabelas_cache = {}
        for t in CarviaTabelaFrete.query.filter_by(
            uf_origem=UF_ORIGEM, tipo_carga=TIPO_CARGA,
            modalidade=MODALIDADE, grupo_cliente_id=None,
        ).all():
            tabelas_cache[(t.nome_tabela, t.uf_destino)] = t

        # 3. Criar tabelas faltantes
        tabelas_criadas = 0
        for nome, uf_dest in sorted(tabelas_necessarias):
            if (nome, uf_dest) not in tabelas_cache:
                t = CarviaTabelaFrete(
                    uf_origem=UF_ORIGEM,
                    uf_destino=uf_dest,
                    nome_tabela=nome,
                    tipo_carga=TIPO_CARGA,
                    modalidade=MODALIDADE,
                    ativo=True,
                    criado_em=agora,
                    criado_por=criado_por,
                )
                db.session.add(t)
                db.session.flush()
                tabelas_cache[(nome, uf_dest)] = t
                tabelas_criadas += 1

        print(f"Tabelas frete: {tabelas_criadas} criadas, "
              f"{len(tabelas_necessarias) - tabelas_criadas} ja existiam")

        # 4. Criar precos por categoria de moto
        precos_criados = 0
        precos_atualizados = 0
        for nome, uf_dest, cat_nome, valor in PRECOS:
            tabela = tabelas_cache[(nome, uf_dest)]
            cat_id = cats[cat_nome]

            existente = CarviaPrecoCategoriaMoto.query.filter_by(
                tabela_frete_id=tabela.id,
                categoria_moto_id=cat_id,
            ).first()

            if existente:
                if existente.valor_unitario != valor:
                    existente.valor_unitario = valor
                    existente.ativo = True
                    precos_atualizados += 1
                # Ja existe com mesmo valor — skip
            else:
                p = CarviaPrecoCategoriaMoto(
                    tabela_frete_id=tabela.id,
                    categoria_moto_id=cat_id,
                    valor_unitario=valor,
                    ativo=True,
                    criado_em=agora,
                    criado_por=criado_por,
                )
                db.session.add(p)
                precos_criados += 1

        db.session.commit()
        print(f"Precos moto: {precos_criados} criados, {precos_atualizados} atualizados")
        print("Seed concluido com sucesso!")


if __name__ == '__main__':
    run()
