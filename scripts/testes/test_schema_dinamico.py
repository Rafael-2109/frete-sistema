#!/usr/bin/env python3
"""
Teste do Schema Dinâmico usando SQLAlchemy inspect.

Este script testa a funcionalidade de gerar schema dinamicamente
dos models do sistema sem usar o hardcoded.

Execute com: python scripts/testes/test_schema_dinamico.py
"""

import sys
import os

# Adiciona o diretório raiz ao path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app


def test_schema_dinamico():
    """Testa geração de schema dinâmico."""
    app = create_app()

    with app.app_context():
        from sqlalchemy import inspect

        # Mapeamento de models para testar
        models_para_testar = {
            'Separacao': 'app.separacao.models',
            'CarteiraPrincipal': 'app.carteira.models',
            'FaturamentoProduto': 'app.faturamento.models',
            'Embarque': 'app.embarques.models',
            'CadastroPalletizacao': 'app.producao.models',
        }

        print("=" * 60)
        print("TESTE DE SCHEMA DINÂMICO")
        print("=" * 60)

        for model_name, module_path in models_para_testar.items():
            print(f"\n--- {model_name} ({module_path}) ---")

            try:
                # Importa o módulo
                import importlib
                module = importlib.import_module(module_path)

                # Obtém a classe do model
                model_class = getattr(module, model_name, None)

                if model_class is None:
                    print(f"  ERRO: Model {model_name} não encontrado no módulo")
                    continue

                # Usa inspect para obter informações
                mapper = inspect(model_class)

                print(f"  Tabela: {model_class.__tablename__}")
                print(f"  Colunas ({len(list(mapper.columns))}):")

                for column in mapper.columns:
                    tipo = str(column.type)[:30]
                    nullable = "opcional" if column.nullable else "obrigatório"
                    pk = " [PK]" if column.primary_key else ""
                    fk = " [FK]" if column.foreign_keys else ""
                    print(f"    - {column.name}: {tipo} ({nullable}){pk}{fk}")

                # Relacionamentos
                if mapper.relationships:
                    print(f"  Relacionamentos ({len(list(mapper.relationships))}):")
                    for rel in mapper.relationships:
                        try:
                            target = rel.mapper.class_.__name__
                            print(f"    - {rel.key} -> {target}")
                        except Exception as e:
                            print(f"    - {rel.key} -> (erro: {e})")

                print(f"  OK: Schema gerado com sucesso")

            except Exception as e:
                print(f"  ERRO: {e}")
                import traceback
                traceback.print_exc()

        print("\n" + "=" * 60)
        print("TESTE DE FORMATAÇÃO PARA PROMPT")
        print("=" * 60)

        # Testa formatação para prompt
        try:
            resultado = _formatar_schema_para_prompt('Separacao', 'app.separacao.models')
            print(resultado[:1000] if resultado else "Nenhum resultado")
            print("\nOK: Formatação funcionou!")
        except Exception as e:
            print(f"ERRO na formatação: {e}")
            import traceback
            traceback.print_exc()


def _formatar_schema_para_prompt(model_name: str, module_path: str) -> str:
    """
    Formata um model para string de prompt.

    Esta é a função que será usada no tool_registry.py
    """
    from sqlalchemy import inspect
    import importlib

    try:
        module = importlib.import_module(module_path)
        model_class = getattr(module, model_name, None)

        if model_class is None:
            return f"Model {model_name} não encontrado"

        mapper = inspect(model_class)

        linhas = [f"\n=== TABELA: {model_class.__tablename__} ==="]

        # Colunas agrupadas por tipo
        campos_id = []
        campos_data = []
        campos_valor = []
        campos_outros = []

        for column in mapper.columns:
            tipo_str = str(column.type).lower()
            nullable = "opcional" if column.nullable else "obrigatório"

            info = f"{column.name}: {str(column.type)[:20]} ({nullable})"

            # Categoriza
            if column.primary_key or 'id' in column.name.lower():
                campos_id.append(info)
            elif 'date' in tipo_str or 'time' in tipo_str:
                campos_data.append(info)
            elif 'numeric' in tipo_str or 'float' in tipo_str or 'integer' in tipo_str:
                campos_valor.append(info)
            else:
                campos_outros.append(info)

        if campos_id:
            linhas.append("\nIdentificação:")
            for c in campos_id:
                linhas.append(f"  - {c}")

        if campos_data:
            linhas.append("\nDatas:")
            for c in campos_data:
                linhas.append(f"  - {c}")

        if campos_valor:
            linhas.append("\nValores/Quantidades:")
            for c in campos_valor[:10]:  # Limita a 10
                linhas.append(f"  - {c}")
            if len(campos_valor) > 10:
                linhas.append(f"  ... e mais {len(campos_valor) - 10} campos")

        if campos_outros:
            linhas.append("\nOutros campos:")
            for c in campos_outros[:15]:  # Limita a 15
                linhas.append(f"  - {c}")
            if len(campos_outros) > 15:
                linhas.append(f"  ... e mais {len(campos_outros) - 15} campos")

        # Relacionamentos
        if mapper.relationships:
            linhas.append("\nRelacionamentos:")
            for rel in list(mapper.relationships)[:5]:  # Limita a 5
                try:
                    target = rel.mapper.class_.__name__
                    linhas.append(f"  - {rel.key} -> {target}")
                except:
                    pass

        return "\n".join(linhas)

    except Exception as e:
        return f"Erro ao formatar {model_name}: {e}"


if __name__ == "__main__":
    test_schema_dinamico()
