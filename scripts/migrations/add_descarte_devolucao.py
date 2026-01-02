#!/usr/bin/env python3
"""
Migracao: Criar tabela descarte_devolucao

Tabela para registrar descartes autorizados de devolucoes.
Fluxo: Autorizacao -> Termo enviado -> Termo retornado -> Descartado

Data: 31/12/2024
Autor: Sistema de Fretes - Modulo Devolucoes

SQL para rodar diretamente no Shell do Render:

CREATE TABLE descarte_devolucao (
    id SERIAL PRIMARY KEY,
    ocorrencia_devolucao_id INTEGER NOT NULL REFERENCES ocorrencia_devolucao(id) ON DELETE CASCADE,
    numero_termo VARCHAR(50),
    data_autorizacao TIMESTAMP NOT NULL DEFAULT NOW(),
    autorizado_por VARCHAR(100) NOT NULL,
    motivo_descarte VARCHAR(50) NOT NULL,
    descricao_motivo TEXT,
    valor_mercadoria NUMERIC(15, 2),
    termo_path VARCHAR(500),
    termo_nome_arquivo VARCHAR(255),
    termo_enviado_em TIMESTAMP,
    termo_enviado_para VARCHAR(255),
    termo_assinado_path VARCHAR(500),
    termo_assinado_nome_arquivo VARCHAR(255),
    termo_retornado_em TIMESTAMP,
    comprovante_path VARCHAR(500),
    comprovante_nome_arquivo VARCHAR(255),
    data_descarte DATE,
    tem_custo BOOLEAN NOT NULL DEFAULT FALSE,
    valor_descarte NUMERIC(15, 2),
    fornecedor_descarte VARCHAR(255),
    despesa_extra_id INTEGER REFERENCES despesas_extras(id),
    status VARCHAR(20) NOT NULL DEFAULT 'AUTORIZADO',
    observacoes TEXT,
    criado_em TIMESTAMP NOT NULL DEFAULT NOW(),
    criado_por VARCHAR(100) NOT NULL,
    atualizado_em TIMESTAMP DEFAULT NOW(),
    atualizado_por VARCHAR(100),
    ativo BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE INDEX idx_descarte_ocorrencia ON descarte_devolucao(ocorrencia_devolucao_id);
CREATE INDEX idx_descarte_numero_termo ON descarte_devolucao(numero_termo);
CREATE INDEX idx_descarte_despesa ON descarte_devolucao(despesa_extra_id);
CREATE INDEX idx_descarte_status ON descarte_devolucao(status);
CREATE INDEX idx_descarte_data_autorizacao ON descarte_devolucao(data_autorizacao);
CREATE INDEX idx_descarte_ativo ON descarte_devolucao(ativo);
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db
from sqlalchemy import text


def executar_migracao():
    """Cria tabela descarte_devolucao."""
    app = create_app()
    with app.app_context():
        try:
            # Verificar se tabela ja existe
            resultado = db.session.execute(text("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_name = 'descarte_devolucao'
            """))

            if resultado.fetchone():
                print("Tabela descarte_devolucao ja existe. Nada a fazer.")
                return True

            # Criar tabela
            print("Criando tabela descarte_devolucao...")
            db.session.execute(text("""
                CREATE TABLE descarte_devolucao (
                    id SERIAL PRIMARY KEY,
                    ocorrencia_devolucao_id INTEGER NOT NULL REFERENCES ocorrencia_devolucao(id) ON DELETE CASCADE,
                    numero_termo VARCHAR(50),
                    data_autorizacao TIMESTAMP NOT NULL DEFAULT NOW(),
                    autorizado_por VARCHAR(100) NOT NULL,
                    motivo_descarte VARCHAR(50) NOT NULL,
                    descricao_motivo TEXT,
                    valor_mercadoria NUMERIC(15, 2),
                    termo_path VARCHAR(500),
                    termo_nome_arquivo VARCHAR(255),
                    termo_enviado_em TIMESTAMP,
                    termo_enviado_para VARCHAR(255),
                    termo_assinado_path VARCHAR(500),
                    termo_assinado_nome_arquivo VARCHAR(255),
                    termo_retornado_em TIMESTAMP,
                    comprovante_path VARCHAR(500),
                    comprovante_nome_arquivo VARCHAR(255),
                    data_descarte DATE,
                    tem_custo BOOLEAN NOT NULL DEFAULT FALSE,
                    valor_descarte NUMERIC(15, 2),
                    fornecedor_descarte VARCHAR(255),
                    despesa_extra_id INTEGER REFERENCES despesas_extras(id),
                    status VARCHAR(20) NOT NULL DEFAULT 'AUTORIZADO',
                    observacoes TEXT,
                    criado_em TIMESTAMP NOT NULL DEFAULT NOW(),
                    criado_por VARCHAR(100) NOT NULL,
                    atualizado_em TIMESTAMP DEFAULT NOW(),
                    atualizado_por VARCHAR(100),
                    ativo BOOLEAN NOT NULL DEFAULT TRUE
                )
            """))

            # Criar indices
            print("Criando indices...")
            db.session.execute(text("""
                CREATE INDEX idx_descarte_ocorrencia ON descarte_devolucao(ocorrencia_devolucao_id)
            """))
            db.session.execute(text("""
                CREATE INDEX idx_descarte_numero_termo ON descarte_devolucao(numero_termo)
            """))
            db.session.execute(text("""
                CREATE INDEX idx_descarte_despesa ON descarte_devolucao(despesa_extra_id)
            """))
            db.session.execute(text("""
                CREATE INDEX idx_descarte_status ON descarte_devolucao(status)
            """))
            db.session.execute(text("""
                CREATE INDEX idx_descarte_data_autorizacao ON descarte_devolucao(data_autorizacao)
            """))
            db.session.execute(text("""
                CREATE INDEX idx_descarte_ativo ON descarte_devolucao(ativo)
            """))

            db.session.commit()

            print("Tabela descarte_devolucao criada com sucesso!")
            return True

        except Exception as e:
            print(f"Erro na migracao: {e}")
            db.session.rollback()
            return False


def verificar_migracao():
    """Verifica se a migracao foi aplicada."""
    app = create_app()
    with app.app_context():
        try:
            resultado = db.session.execute(text("""
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_name = 'descarte_devolucao'
                ORDER BY ordinal_position
            """))

            colunas = resultado.fetchall()
            if colunas:
                print(f"Tabela descarte_devolucao encontrada com {len(colunas)} colunas:")
                for col in colunas:
                    print(f"  - {col[0]}: {col[1]}")
                return True
            else:
                print("Tabela nao encontrada!")
                return False

        except Exception as e:
            print(f"Erro ao verificar: {e}")
            return False


if __name__ == '__main__':
    print("=" * 60)
    print("MIGRACAO: Criar tabela descarte_devolucao")
    print("=" * 60)

    if '--check' in sys.argv:
        verificar_migracao()
    else:
        if executar_migracao():
            print("\n" + "=" * 60)
            print("VERIFICANDO MIGRACAO...")
            verificar_migracao()
