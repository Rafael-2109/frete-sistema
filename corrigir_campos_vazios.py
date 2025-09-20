#!/usr/bin/env python3
"""
Script para corrigir campos cod_uf e nome_cidade vazios em registros existentes
Aplica a lógica de fallback nos registros já existentes no banco
"""

from app import create_app, db
from app.carteira.models import CarteiraPrincipal
from sqlalchemy import text
import sys

def corrigir_campos_vazios():
    """Corrige campos cod_uf e nome_cidade vazios usando fallback"""

    print("="*60)
    print("CORREÇÃO DE CAMPOS VAZIOS (cod_uf e nome_cidade)")
    print("="*60)

    try:
        app = create_app()
        with app.app_context():

            print("\n📋 Identificando registros com campos vazios...")

            # Buscar registros com campos vazios
            registros_problema = db.session.query(CarteiraPrincipal).filter(
                CarteiraPrincipal.ativo == True,
                db.or_(
                    db.or_(CarteiraPrincipal.cod_uf == None, CarteiraPrincipal.cod_uf == ''),
                    db.or_(CarteiraPrincipal.nome_cidade == None, CarteiraPrincipal.nome_cidade == '')
                )
            ).all()

            if not registros_problema:
                print("✅ Nenhum registro com campos vazios encontrado!")
                return True

            print(f"\nEncontrados {len(registros_problema)} registros para corrigir:\n")

            corrigidos = 0
            erros = 0

            for item in registros_problema:
                try:
                    print(f"Corrigindo pedido {item.num_pedido}:")
                    print(f"  Estado atual: cod_uf='{item.cod_uf}', nome_cidade='{item.nome_cidade}'")

                    # Aplicar fallback para cod_uf
                    novo_cod_uf = item.cod_uf
                    if not novo_cod_uf or novo_cod_uf == '':
                        # Usar estado como fallback
                        if item.estado and item.estado != '':
                            novo_cod_uf = item.estado
                            print(f"  ✅ Usando estado como fallback: '{novo_cod_uf}'")
                        else:
                            # Se não tiver estado, usar 'SP' como default
                            novo_cod_uf = 'SP'
                            print(f"  ⚠️ Sem estado disponível, usando default: 'SP'")

                    # Aplicar fallback para nome_cidade
                    novo_nome_cidade = item.nome_cidade
                    if not novo_nome_cidade or novo_nome_cidade == '':
                        # Usar municipio como fallback
                        if item.municipio and item.municipio != '':
                            novo_nome_cidade = item.municipio
                            print(f"  ✅ Usando municipio como fallback: '{novo_nome_cidade}'")
                        else:
                            # Se não tiver municipio, deixar vazio (mas não NULL)
                            novo_nome_cidade = ''
                            print(f"  ⚠️ Sem municipio disponível, mantendo vazio")

                    # Atualizar o registro
                    item.cod_uf = novo_cod_uf
                    item.nome_cidade = novo_nome_cidade

                    print(f"  Estado corrigido: cod_uf='{novo_cod_uf}', nome_cidade='{novo_nome_cidade}'")
                    print()

                    corrigidos += 1

                except Exception as e:
                    print(f"  ❌ Erro ao corrigir: {e}")
                    print()
                    erros += 1

            # Salvar alterações
            if corrigidos > 0:
                print(f"\n💾 Salvando {corrigidos} correções no banco...")
                db.session.commit()
                print("✅ Correções salvas com sucesso!")
            else:
                print("\n⚠️ Nenhuma correção foi aplicada")

            # Verificar resultado final
            print("\n🔍 Verificando resultado final...")

            # Contar registros ainda com problemas
            sql_check = """
                SELECT COUNT(*) as total
                FROM carteira_principal
                WHERE ativo = true
                AND (cod_uf IS NULL OR cod_uf = '')
            """

            result = db.session.execute(text(sql_check))
            problemas_restantes = result.scalar()

            print("\n" + "="*60)
            print("RESUMO DA CORREÇÃO")
            print("="*60)
            print(f"\n📊 Estatísticas:")
            print(f"  - Registros identificados: {len(registros_problema)}")
            print(f"  - Registros corrigidos: {corrigidos}")
            print(f"  - Erros: {erros}")
            print(f"  - Problemas restantes: {problemas_restantes}")

            if problemas_restantes == 0:
                print("\n✅ SUCESSO! Todos os campos vazios foram corrigidos!")
            else:
                print(f"\n⚠️ Ainda existem {problemas_restantes} registros com problemas.")
                print("   Pode ser necessário investigar manualmente.")

            # Mostrar exemplos dos registros corrigidos
            if corrigidos > 0:
                print("\n📋 Exemplos de registros corrigidos:")
                exemplos = db.session.query(CarteiraPrincipal).filter(
                    CarteiraPrincipal.num_pedido.in_(['VCD2563487', 'VCD2563472', 'VCD2563471'])
                ).all()

                for ex in exemplos[:3]:
                    print(f"\nPedido: {ex.num_pedido}")
                    print(f"  cod_uf: '{ex.cod_uf}'")
                    print(f"  nome_cidade: '{ex.nome_cidade}'")
                    print(f"  estado: '{ex.estado}'")
                    print(f"  municipio: '{ex.municipio}'")

            return problemas_restantes == 0

    except Exception as e:
        print(f"\n❌ Erro fatal: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = corrigir_campos_vazios()
    sys.exit(0 if success else 1)