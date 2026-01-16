"""
Script para consultar tabelas desconhecidas do Odoo
====================================================

Usado para descoberta de campos e consultas em tabelas nao mapeadas.

Funcionalidades:
- Listar campos de qualquer modelo
- Buscar campo por nome
- Consulta generica com filtros JSON
- Inspecionar estrutura de modelo

Autor: Sistema de Fretes
Data: 02/12/2025
"""

import sys
import os
import argparse
import json
from typing import Dict, List, Any, Optional

# Adiciona path do projeto
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..')))


# ==============================================================================
# FUNCOES DE DESCOBERTA
# ==============================================================================

def listar_campos(odoo, modelo: str, buscar: Optional[str] = None) -> Dict[str, Any]:
    """
    Lista campos de um modelo do Odoo
    """
    resultado = {
        'sucesso': False,
        'modelo': modelo,
        'total': 0,
        'campos': [],
        'erro': None
    }

    try:
        # Buscar campos do modelo
        campos = odoo.execute_kw(
            modelo,
            'fields_get',
            [],
            {'attributes': ['string', 'type', 'help', 'required', 'readonly']}
        )

        if not campos:
            resultado['erro'] = f'Modelo nao encontrado ou sem campos: {modelo}'
            return resultado

        # Formatar campos
        lista_campos = []
        for nome, info in campos.items():
            campo = {
                'nome': nome,
                'tipo': info.get('type', 'unknown'),
                'descricao': info.get('string', ''),
                'help': info.get('help', ''),
                'obrigatorio': info.get('required', False),
                'readonly': info.get('readonly', False),
            }

            # Filtrar por termo de busca
            if buscar:
                termo = buscar.lower()
                if termo not in nome.lower() and termo not in campo['descricao'].lower():
                    continue

            lista_campos.append(campo)

        # Ordenar por nome
        lista_campos.sort(key=lambda x: x['nome'])

        resultado['sucesso'] = True
        resultado['total'] = len(lista_campos)
        resultado['campos'] = lista_campos

    except Exception as e:
        resultado['erro'] = str(e)

    return resultado


def consultar_generica(odoo, modelo: str, filtro: list, campos: list, limit: int) -> Dict[str, Any]:
    """
    Consulta generica em qualquer modelo do Odoo
    """
    resultado = {
        'sucesso': False,
        'modelo': modelo,
        'filtro': filtro,
        'total': 0,
        'registros': [],
        'erro': None
    }

    try:
        registros = odoo.search_read(
            modelo,
            filtro,
            fields=campos if campos else None,
            limit=limit
        )

        resultado['sucesso'] = True
        resultado['total'] = len(registros)
        resultado['registros'] = registros

    except Exception as e:
        resultado['erro'] = str(e)

    return resultado


def inspecionar_registro(odoo, modelo: str, registro_id: int) -> Dict[str, Any]:
    """
    Inspeciona todos os campos de um registro especifico
    """
    resultado = {
        'sucesso': False,
        'modelo': modelo,
        'registro_id': registro_id,
        'dados': None,
        'erro': None
    }

    try:
        registros = odoo.read(modelo, [registro_id])

        if not registros:
            resultado['erro'] = f'Registro {registro_id} nao encontrado'
            return resultado

        resultado['sucesso'] = True
        resultado['dados'] = registros[0]

    except Exception as e:
        resultado['erro'] = str(e)

    return resultado


# ==============================================================================
# MAIN
# ==============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='Consulta tabelas desconhecidas do Odoo (descoberta)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  # Listar todos os campos de um modelo
  python consultando_desconhecidas.py --modelo l10n_br_ciel_it_account.dfe --listar-campos

  # Buscar campo especifico
  python consultando_desconhecidas.py --modelo res.partner --buscar-campo cnpj

  # Consulta generica
  python consultando_desconhecidas.py --modelo res.partner \\
    --filtro '[["l10n_br_cnpj","ilike","93209765"]]' \\
    --campos '["id","name","l10n_br_cnpj"]' --limit 5

  # Inspecionar registro
  python consultando_desconhecidas.py --modelo res.partner --inspecionar 123
        """
    )

    # Argumentos obrigatorios
    parser.add_argument('--modelo', required=True, help='Nome do modelo Odoo (ex: res.partner)')

    # Modos de operacao
    parser.add_argument('--listar-campos', action='store_true', help='Lista todos os campos do modelo')
    parser.add_argument('--buscar-campo', help='Busca campo por nome ou descricao')
    parser.add_argument('--inspecionar', type=int, help='Inspeciona registro por ID')

    # Consulta generica
    parser.add_argument('--filtro', help='Filtro em formato JSON (ex: [[\"name\",\"=\",\"teste\"]])')
    parser.add_argument('--campos', help='Campos a retornar em formato JSON (ex: [\"id\",\"name\"])')
    parser.add_argument('--limit', type=int, default=10, help='Limite de resultados (padrao: 10)')

    # Formato de saida
    parser.add_argument('--json', action='store_true', help='Saida em JSON')

    args = parser.parse_args()

    # Conectar ao Odoo
    from app.odoo.utils.connection import get_odoo_connection

    try:
        odoo = get_odoo_connection()
        if not odoo.authenticate():
            print("ERRO: Falha na autenticacao com Odoo")
            sys.exit(1)
    except Exception as e:
        print(f"ERRO: {e}")
        sys.exit(1)

    # Executar operacao
    if args.listar_campos or args.buscar_campo:
        resultado = listar_campos(odoo, args.modelo, args.buscar_campo)

    elif args.inspecionar:
        resultado = inspecionar_registro(odoo, args.modelo, args.inspecionar)

    elif args.filtro:
        try:
            filtro = json.loads(args.filtro)
        except json.JSONDecodeError as e:
            print(f"ERRO: Filtro JSON invalido: {e}")
            sys.exit(1)

        campos = None
        if args.campos:
            try:
                campos = json.loads(args.campos)
            except json.JSONDecodeError as e:
                print(f"ERRO: Campos JSON invalido: {e}")
                sys.exit(1)

        resultado = consultar_generica(odoo, args.modelo, filtro, campos, args.limit)

    else:
        print("ERRO: Especifique uma operacao: --listar-campos, --buscar-campo, --filtro ou --inspecionar")
        sys.exit(1)

    # Saida
    if args.json:
        print(json.dumps(resultado, indent=2, default=str, ensure_ascii=False))
    else:
        if resultado['sucesso']:
            if 'campos' in resultado:
                print(f"\n{'='*60}")
                print(f"CAMPOS DO MODELO: {resultado['modelo']}")
                print(f"Total: {resultado['total']} campo(s)")
                print(f"{'='*60}\n")

                for campo in resultado['campos']:
                    tipo = campo['tipo']
                    obrig = '*' if campo['obrigatorio'] else ''
                    print(f"{campo['nome']}{obrig} ({tipo})")
                    if campo['descricao']:
                        print(f"  Descricao: {campo['descricao']}")
                    if campo['help']:
                        print(f"  Ajuda: {campo['help'][:100]}...")
                    print()

            elif 'registros' in resultado:
                print(f"\n{'='*60}")
                print(f"CONSULTA: {resultado['modelo']}")
                print(f"Filtro: {resultado['filtro']}")
                print(f"Total: {resultado['total']} registro(s)")
                print(f"{'='*60}\n")

                for reg in resultado['registros']:
                    print(json.dumps(reg, indent=2, default=str, ensure_ascii=False))
                    print()

            elif 'dados' in resultado:
                print(f"\n{'='*60}")
                print(f"REGISTRO: {resultado['modelo']} ID={resultado['registro_id']}")
                print(f"{'='*60}\n")
                print(json.dumps(resultado['dados'], indent=2, default=str, ensure_ascii=False))

        else:
            print(f"\nERRO: {resultado['erro']}")


if __name__ == '__main__':
    main()
