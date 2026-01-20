"""
Script para sincronizar extratos pendentes com baixas já realizadas.

Uso:
    python scripts/sincronizar_extratos.py                    # Modo padrão (via títulos pagos)
    python scripts/sincronizar_extratos.py --janela 240       # Últimos 240 minutos
    python scripts/sincronizar_extratos.py --revalidar        # TODOS os pendentes (via títulos locais)
    python scripts/sincronizar_extratos.py --lote 123         # Específico de um lote CNAB
    python scripts/sincronizar_extratos.py --odoo             # Via write_date do Odoo (incremental)
    python scripts/sincronizar_extratos.py --odoo-completo    # TODOS via Odoo (primeira vez/manutenção)
    python scripts/sincronizar_extratos.py --completo         # Todos os métodos combinados

Modos de Sincronização:
    - Padrão: Verifica títulos pagos (ContasAReceber.parcela_paga) e atualiza extratos
    - --odoo: Consulta Odoo para linhas conciliadas (via write_date) - INCREMENTAL
    - --odoo-completo: Consulta Odoo para TODOS os extratos pendentes - COMPLETO
    - --completo: Executa AMBOS os métodos para máxima cobertura
    - --revalidar: Reprocessa TODOS os extratos pendentes (via títulos locais)
"""

import sys
import os
import argparse

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app


def main():
    parser = argparse.ArgumentParser(
        description='Sincronizar extratos pendentes',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  python scripts/sincronizar_extratos.py                 # Sincroniza via títulos pagos
  python scripts/sincronizar_extratos.py --odoo          # Sincroniza via Odoo write_date (incremental)
  python scripts/sincronizar_extratos.py --odoo-completo # Sincroniza TODOS via Odoo (primeira vez)
  python scripts/sincronizar_extratos.py --completo      # Ambos os métodos
  python scripts/sincronizar_extratos.py --revalidar     # Reprocessa TODOS (via títulos locais)
  python scripts/sincronizar_extratos.py --lote 123      # Sincroniza lote CNAB específico
        """
    )
    parser.add_argument('--janela', type=int, default=120,
                        help='Janela de tempo em minutos (default: 120)')
    parser.add_argument('--limite', type=int, default=500,
                        help='Limite de registros (default: 500)')
    parser.add_argument('--revalidar', action='store_true',
                        help='Revalidar TODOS os extratos pendentes (⚠️ lento)')
    parser.add_argument('--lote', type=int,
                        help='Sincronizar extratos de um lote CNAB específico')
    parser.add_argument('--odoo', action='store_true',
                        help='Sincronizar via write_date do Odoo (incremental - detecta conciliações recentes)')
    parser.add_argument('--odoo-completo', action='store_true',
                        help='Sincronizar TODOS extratos via Odoo (primeira vez/manutenção - consulta is_reconciled)')
    parser.add_argument('--completo', action='store_true',
                        help='Executar TODOS os métodos de sincronização combinados')

    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        from app.financeiro.services.sincronizacao_extratos_service import SincronizacaoExtratosService

        service = SincronizacaoExtratosService()

        print("=" * 60)
        print("SINCRONIZAÇÃO DE EXTRATOS")
        print("=" * 60)

        if args.lote:
            print(f"📦 Sincronizando extratos do lote CNAB #{args.lote}...")
            resultado = service.sincronizar_extratos_por_cnab(lote_id=args.lote)
            _exibir_resultado_lote(resultado)

        elif args.revalidar:
            print("⚠️  REVALIDANDO TODOS OS EXTRATOS PENDENTES...")
            print("Isso pode demorar. Pressione Ctrl+C para cancelar.")
            print()
            resultado = service.revalidar_todos_extratos_pendentes()
            _exibir_resultado_padrao(resultado)

        elif args.completo:
            print(f"🔄 Sincronização COMPLETA (todos os métodos)")
            print(f"   Janela: {args.janela} minutos")
            print()
            resultado = service.sincronizar_completo(
                janela_minutos=args.janela,
                limite=args.limite
            )
            _exibir_resultado_completo(resultado)

        elif getattr(args, 'odoo_completo', False):
            print("🌐 Sincronizando TODOS os extratos via Odoo (is_reconciled)")
            print("⚠️  Isso pode demorar. Pressione Ctrl+C para cancelar.")
            print()
            resultado = service.revalidar_todos_extratos_via_odoo()
            _exibir_resultado_odoo_completo(resultado)

        elif args.odoo:
            print(f"🌐 Sincronizando via Odoo (write_date - incremental)")
            print(f"   Janela: {args.janela} minutos")
            print()
            resultado = service.sincronizar_via_odoo(
                janela_minutos=args.janela,
                limite=args.limite
            )
            _exibir_resultado_odoo(resultado)

        else:
            print(f"📋 Sincronizando via títulos pagos")
            print(f"   Janela: {args.janela} minutos")
            print()
            resultado = service.sincronizar_extratos_pendentes(
                janela_minutos=args.janela,
                limite=args.limite
            )
            _exibir_resultado_padrao(resultado)

        print("=" * 60)


def _exibir_resultado_padrao(resultado):
    """Exibe resultado do método padrão (via títulos)."""
    print()
    print("=" * 60)
    print("RESULTADO:")
    print("=" * 60)

    if resultado.get('success'):
        stats = resultado.get('stats', {})
        print(f"✅ Sincronização concluída!")
        print()
        print(f"  Total verificados: {stats.get('total_verificados', 0)}")

        # Estatísticas detalhadas (para revalidação completa)
        if 'com_titulo_verificados' in stats:
            print()
            print("  --- Extratos COM título vinculado ---")
            print(f"      Verificados: {stats.get('com_titulo_verificados', 0)}")

        if 'sem_titulo_verificados' in stats:
            print()
            print("  --- Extratos SEM título vinculado ---")
            print(f"      Verificados: {stats.get('sem_titulo_verificados', 0)}")
            print(f"      Títulos encontrados: {stats.get('titulos_encontrados', 0)}")

        print()
        print("  --- Resultados ---")
        print(f"  Títulos pagos detectados: {stats.get('titulos_pagos_detectados', 0)}")
        print(f"  Atualizados por título: {stats.get('atualizados_por_titulo', 0)}")
        print(f"  Atualizados por CNAB: {stats.get('atualizados_por_cnab', 0)}")
        print(f"  Sem alteração: {stats.get('sem_alteracao', 0)}")
        print(f"  Erros: {stats.get('erros', 0)}")
    else:
        print(f"❌ Erro: {resultado.get('error', 'Desconhecido')}")


def _exibir_resultado_odoo(resultado):
    """Exibe resultado do método Odoo (via write_date - incremental)."""
    print()
    print("=" * 60)
    print("RESULTADO (Sincronização via Odoo - Incremental):")
    print("=" * 60)

    if resultado.get('success'):
        stats = resultado.get('stats', {})
        print(f"✅ Sincronização via Odoo concluída!")
        print()
        print(f"  Linhas verificadas no Odoo: {stats.get('linhas_odoo_verificadas', 0)}")
        print(f"  Extratos atualizados: {stats.get('extratos_atualizados', 0)}")
        print(f"  Já conciliados: {stats.get('ja_conciliados', 0)}")
        print(f"  Não encontrados no sistema: {stats.get('extratos_nao_encontrados', 0)}")
        print(f"  Erros: {stats.get('erros', 0)}")
    else:
        print(f"❌ Erro: {resultado.get('error', 'Desconhecido')}")


def _exibir_resultado_odoo_completo(resultado):
    """Exibe resultado do método Odoo completo (todos extratos)."""
    print()
    print("=" * 60)
    print("RESULTADO (Sincronização COMPLETA via Odoo):")
    print("=" * 60)

    if resultado.get('success'):
        stats = resultado.get('stats', {})
        print(f"✅ Revalidação via Odoo concluída!")
        print()
        print(f"  Total extratos no sistema: {stats.get('total_extratos_sistema', 0)}")
        print(f"  Total verificados: {stats.get('total_verificados', 0)}")
        print()
        print("  --- Status no Odoo ---")
        print(f"      Conciliados no Odoo: {stats.get('conciliados_no_odoo', 0)}")
        print(f"      NÃO conciliados no Odoo: {stats.get('nao_conciliados_no_odoo', 0)}")
        print(f"      Statement line não encontrado: {stats.get('statement_line_nao_encontrado', 0)}")
        print()
        print("  --- Ações realizadas ---")
        print(f"      Extratos ATUALIZADOS: {stats.get('atualizados', 0)}")
        print(f"      Já conciliados no sistema: {stats.get('ja_conciliados_sistema', 0)}")
        print(f"      Erros: {stats.get('erros', 0)}")

        if stats.get('atualizados', 0) > 0:
            print()
            print(f"  🎉 {stats.get('atualizados', 0)} extratos foram marcados como CONCILIADO!")
    else:
        print(f"❌ Erro: {resultado.get('error', 'Desconhecido')}")


def _exibir_resultado_completo(resultado):
    """Exibe resultado do método completo (combinado)."""
    print()
    print("=" * 60)
    print("RESULTADO (Sincronização COMPLETA):")
    print("=" * 60)

    stats_comb = resultado.get('stats_combinadas', {})
    print(f"{'✅' if resultado.get('success') else '⚠️'} Sincronização finalizada")
    print()
    print(f"  TOTAL ATUALIZADOS: {stats_comb.get('total_atualizados', 0)}")
    print(f"  ERROS TOTAIS: {stats_comb.get('erros_totais', 0)}")
    print()

    # Detalhes por método
    metodo_titulos = resultado.get('metodo_titulos', {})
    if metodo_titulos:
        print("  --- Método Títulos Pagos ---")
        if metodo_titulos.get('success'):
            stats_t = metodo_titulos.get('stats', {})
            print(f"      Verificados: {stats_t.get('total_verificados', 0)}")
            print(f"      Por título: {stats_t.get('atualizados_por_titulo', 0)}")
            print(f"      Por CNAB: {stats_t.get('atualizados_por_cnab', 0)}")
        else:
            print(f"      ❌ Erro: {metodo_titulos.get('error', 'Desconhecido')}")
        print()

    metodo_odoo = resultado.get('metodo_odoo', {})
    if metodo_odoo:
        print("  --- Método Odoo (write_date) ---")
        if metodo_odoo.get('success'):
            stats_o = metodo_odoo.get('stats', {})
            print(f"      Linhas Odoo: {stats_o.get('linhas_odoo_verificadas', 0)}")
            print(f"      Atualizados: {stats_o.get('extratos_atualizados', 0)}")
            print(f"      Já conciliados: {stats_o.get('ja_conciliados', 0)}")
        else:
            print(f"      ❌ Erro: {metodo_odoo.get('error', 'Desconhecido')}")


def _exibir_resultado_lote(resultado):
    """Exibe resultado da sincronização de lote CNAB."""
    print()
    print("=" * 60)
    print("RESULTADO (Lote CNAB):")
    print("=" * 60)

    if resultado.get('success'):
        stats = resultado.get('stats', {})
        print(f"✅ Sincronização do lote concluída!")
        print()
        print(f"  Total de itens CNAB: {stats.get('total', 0)}")
        print(f"  Atualizados: {stats.get('atualizados', 0)}")
        print(f"  Já vinculados: {stats.get('ja_vinculados', 0)}")
        print(f"  Sem extrato correspondente: {stats.get('sem_extrato', 0)}")
    else:
        print(f"❌ Erro: {resultado.get('error', 'Desconhecido')}")


if __name__ == '__main__':
    main()
