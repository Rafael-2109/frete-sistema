"""
Script de Migração: Inserir tipos iniciais de Contas a Receber
==============================================================

Este script insere os tipos iniciais para:
- confirmacao: CONFIRMADO, ABERTO
- forma_confirmacao: PORTAL, EMAIL, TELEFONE, LOGISTICA
- acao_necessaria: LIGAR, MANDAR EMAIL, VERIFICAR PORTAL
- tipo (abatimento): VERBA, ACAO COMERCIAL, DEVOLUCAO

Data: 2025-11-27
Autor: Sistema de Fretes
"""

import sys
import os

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db
from sqlalchemy import text


def inserir_tipos_contas_a_receber():
    """Insere os tipos iniciais de Contas a Receber"""

    app = create_app()

    with app.app_context():
        try:
            print("=" * 60)
            print("MIGRAÇÃO: Inserir Tipos de Contas a Receber")
            print("=" * 60)

            # Definição dos tipos
            tipos = [
                # =====================================================
                # CONFIRMAÇÃO (contas_a_receber.confirmacao)
                # =====================================================
                {
                    'tipo': 'CONFIRMADO',
                    'considera_a_receber': True,
                    'tabela': 'contas_a_receber',
                    'campo': 'confirmacao',
                    'explicacao': 'Título com confirmação de entrega validada',
                    'criado_por': 'Sistema'
                },
                {
                    'tipo': 'ABERTO',
                    'considera_a_receber': True,
                    'tabela': 'contas_a_receber',
                    'campo': 'confirmacao',
                    'explicacao': 'Título ainda não confirmado',
                    'criado_por': 'Sistema'
                },

                # =====================================================
                # FORMA DE CONFIRMAÇÃO (contas_a_receber.forma_confirmacao)
                # =====================================================
                {
                    'tipo': 'PORTAL',
                    'considera_a_receber': True,
                    'tabela': 'contas_a_receber',
                    'campo': 'forma_confirmacao',
                    'explicacao': 'Confirmação via portal do cliente',
                    'criado_por': 'Sistema'
                },
                {
                    'tipo': 'EMAIL',
                    'considera_a_receber': True,
                    'tabela': 'contas_a_receber',
                    'campo': 'forma_confirmacao',
                    'explicacao': 'Confirmação via e-mail',
                    'criado_por': 'Sistema'
                },
                {
                    'tipo': 'TELEFONE',
                    'considera_a_receber': True,
                    'tabela': 'contas_a_receber',
                    'campo': 'forma_confirmacao',
                    'explicacao': 'Confirmação via telefone',
                    'criado_por': 'Sistema'
                },
                {
                    'tipo': 'LOGISTICA',
                    'considera_a_receber': True,
                    'tabela': 'contas_a_receber',
                    'campo': 'forma_confirmacao',
                    'explicacao': 'Confirmação via logística/transportadora',
                    'criado_por': 'Sistema'
                },

                # =====================================================
                # AÇÃO NECESSÁRIA (contas_a_receber.acao_necessaria)
                # =====================================================
                {
                    'tipo': 'LIGAR',
                    'considera_a_receber': True,
                    'tabela': 'contas_a_receber',
                    'campo': 'acao_necessaria',
                    'explicacao': 'Necessário ligar para o cliente',
                    'criado_por': 'Sistema'
                },
                {
                    'tipo': 'MANDAR EMAIL',
                    'considera_a_receber': True,
                    'tabela': 'contas_a_receber',
                    'campo': 'acao_necessaria',
                    'explicacao': 'Necessário enviar e-mail para o cliente',
                    'criado_por': 'Sistema'
                },
                {
                    'tipo': 'VERIFICAR PORTAL',
                    'considera_a_receber': True,
                    'tabela': 'contas_a_receber',
                    'campo': 'acao_necessaria',
                    'explicacao': 'Necessário verificar portal do cliente',
                    'criado_por': 'Sistema'
                },

                # =====================================================
                # TIPO DE ABATIMENTO (contas_a_receber_abatimento.tipo)
                # =====================================================
                {
                    'tipo': 'VERBA',
                    'considera_a_receber': True,
                    'tabela': 'contas_a_receber_abatimento',
                    'campo': 'tipo',
                    'explicacao': 'Abatimento por verba comercial',
                    'criado_por': 'Sistema'
                },
                {
                    'tipo': 'ACAO COMERCIAL',
                    'considera_a_receber': True,
                    'tabela': 'contas_a_receber_abatimento',
                    'campo': 'tipo',
                    'explicacao': 'Abatimento por ação comercial',
                    'criado_por': 'Sistema'
                },
                {
                    'tipo': 'DEVOLUCAO',
                    'considera_a_receber': True,
                    'tabela': 'contas_a_receber_abatimento',
                    'campo': 'tipo',
                    'explicacao': 'Abatimento por devolução de mercadoria',
                    'criado_por': 'Sistema'
                },
            ]

            # Inserir tipos
            print(f"\n📝 Inserindo {len(tipos)} tipos...")

            for tipo_data in tipos:
                # Verificar se já existe
                existe = db.session.execute(text("""
                    SELECT id FROM contas_a_receber_tipos
                    WHERE tipo = :tipo AND tabela = :tabela AND campo = :campo
                """), {
                    'tipo': tipo_data['tipo'],
                    'tabela': tipo_data['tabela'],
                    'campo': tipo_data['campo']
                }).fetchone()

                if existe:
                    print(f"   ⏭️  {tipo_data['tipo']} ({tipo_data['tabela']}.{tipo_data['campo']}) - já existe")
                    continue

                # Inserir
                db.session.execute(text("""
                    INSERT INTO contas_a_receber_tipos
                    (tipo, considera_a_receber, tabela, campo, explicacao, ativo, criado_por, criado_em)
                    VALUES
                    (:tipo, :considera_a_receber, :tabela, :campo, :explicacao, TRUE, :criado_por, CURRENT_TIMESTAMP)
                """), tipo_data)

                print(f"   ✅ {tipo_data['tipo']} ({tipo_data['tabela']}.{tipo_data['campo']})")

            db.session.commit()

            print("\n" + "=" * 60)
            print("✅ TIPOS INSERIDOS COM SUCESSO!")
            print("=" * 60)

            # Mostrar resumo
            resultado = db.session.execute(text("""
                SELECT tabela, campo, COUNT(*) as qtd
                FROM contas_a_receber_tipos
                GROUP BY tabela, campo
                ORDER BY tabela, campo
            """)).fetchall()

            print("\n📊 Resumo por tabela/campo:")
            for row in resultado:
                print(f"   {row[0]}.{row[1]}: {row[2]} tipos")

            print("\n")
            return True

        except Exception as e:
            db.session.rollback()
            print(f"\n❌ ERRO na inserção: {e}")
            import traceback
            traceback.print_exc()
            return False


if __name__ == '__main__':
    inserir_tipos_contas_a_receber()
