#!/usr/bin/env python3
"""
Script para calcular cotacao de frete detalhada.

Uso:
    python calcular_cotacao.py --peso 5000 --valor 50000 --cidade "Manaus" --uf AM
    python calcular_cotacao.py --peso 5000 --valor 50000 --cidade "Sao Paulo" --uf SP --detalhado
    python calcular_cotacao.py --peso 25000 --valor 200000 --cidade "Curitiba" --uf PR --tipo-carga DIRETA
"""

import argparse
import json
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..')))


def calcular_cotacao(
    peso: float,
    valor: float,
    cidade: str,
    uf: str = None,
    tipo_carga: str = None,
    uf_origem: str = 'SP',
    detalhado: bool = False,
    ordenar: str = 'menor_valor',
    limite: int = 10
) -> dict:
    """
    Calcula cotacao de frete para peso/valor/destino usando o motor existente.

    Reutiliza calcular_fretes_possiveis() de frete_simulador.py que ja:
    - Resolve cidade e busca CidadeAtendida por codigo_ibge
    - Filtra transportadoras ativas
    - Busca tabelas com suporte a grupo empresarial
    - Chama CalculadoraFrete.calcular_frete_unificado() para cada tabela
    - Aplica logica "tabela mais cara" para DIRETA

    Args:
        peso: Peso em kg
        valor: Valor da mercadoria em R$
        cidade: Nome da cidade destino
        uf: UF destino (obrigatorio se cidade ambigua)
        tipo_carga: DIRETA ou FRACIONADA
        uf_origem: UF de origem (default: SP)
        detalhado: Se True, inclui breakdown completo de cada opcao
        ordenar: menor_valor (default) ou menor_prazo
        limite: Maximo de opcoes (default: 10)

    Returns:
        dict: {sucesso, parametros, total_opcoes, opcoes}
    """
    from app import create_app, db
    from app.localidades.models import Cidade
    from app.vinculos.models import CidadeAtendida
    from app.utils.frete_simulador import calcular_fretes_possiveis
    from app.utils.string_utils import remover_acentos
    from sqlalchemy import func

    resultado = {
        'sucesso': False,
        'parametros': {
            'peso': peso,
            'valor': valor,
            'cidade': cidade,
            'uf': uf,
            'tipo_carga': tipo_carga
        },
        'opcoes': [],
        'total_opcoes': 0
    }

    if not peso or peso <= 0:
        resultado['erro'] = 'Peso deve ser maior que zero'
        return resultado

    if not valor or valor <= 0:
        resultado['erro'] = 'Valor da mercadoria deve ser maior que zero'
        return resultado

    if not cidade:
        resultado['erro'] = 'Nome da cidade nao informado'
        return resultado

    app = create_app()
    with app.app_context():
        try:
            # 1. Resolver cidade (mesma logica do buscar_tabelas_cidade.py)
            cidade_normalizada = remover_acentos(cidade.strip()).upper()

            cidades_db = Cidade.query.all()
            cidades_encontradas = []
            for c in cidades_db:
                nome_db_normalizado = remover_acentos(c.nome.strip()).upper()
                if nome_db_normalizado == cidade_normalizada:
                    cidades_encontradas.append(c)

            if not cidades_encontradas:
                resultado['erro'] = f"Cidade '{cidade}' nao encontrada na base de localidades"
                return resultado

            # Checar ambiguidade de UF
            ufs_encontradas = list(set(c.uf for c in cidades_encontradas))

            if len(ufs_encontradas) > 1 and not uf:
                resultado['ambiguidade'] = True
                resultado['opcoes_uf'] = sorted(ufs_encontradas)
                resultado['mensagem'] = (
                    f"A cidade '{cidade}' existe em {len(ufs_encontradas)} estados: "
                    f"{', '.join(sorted(ufs_encontradas))}. Informe o UF com --uf."
                )
                return resultado

            # Resolver cidade definitiva
            if uf:
                uf_upper = uf.strip().upper()
                cidade_obj = next(
                    (c for c in cidades_encontradas if c.uf.upper() == uf_upper),
                    None
                )
                if not cidade_obj:
                    resultado['erro'] = (
                        f"Cidade '{cidade}' nao encontrada no estado '{uf}'. "
                        f"Estados disponiveis: {', '.join(sorted(ufs_encontradas))}"
                    )
                    return resultado
            else:
                cidade_obj = cidades_encontradas[0]

            cidade_nome = cidade_obj.nome
            cidade_uf = cidade_obj.uf
            cidade_id = cidade_obj.id

            resultado['parametros']['cidade_resolvida'] = cidade_nome
            resultado['parametros']['uf_resolvida'] = cidade_uf

            # 2. Buscar lead_times dos vinculos para enriquecer resultado
            atendimentos = CidadeAtendida.query.filter(
                CidadeAtendida.codigo_ibge == cidade_obj.codigo_ibge
            ).all()

            # Mapa de lead_time por (transportadora_id, nome_tabela)
            lead_times = {}
            for at in atendimentos:
                chave = (at.transportadora_id, at.nome_tabela.strip().upper() if at.nome_tabela else '')
                lead_times[chave] = at.lead_time

            # 3. Chamar calcular_fretes_possiveis() — reutilizacao direta
            fretes = calcular_fretes_possiveis(
                cidade_destino_id=cidade_id,
                peso_utilizado=peso,
                valor_carga=valor,
                uf_origem=uf_origem,
                tipo_carga=tipo_carga
            )

            if not fretes:
                resultado['sucesso'] = True
                resultado['mensagem'] = (
                    f"Nenhuma opcao de frete encontrada para "
                    f"{cidade_nome}/{cidade_uf} ({peso}kg, R${valor:,.2f})"
                )
                return resultado

            # 4. Enriquecer e formatar resultados
            opcoes = []
            for frete in fretes:
                opcao = {
                    'transportadora': frete.get('transportadora', ''),
                    'transportadora_id': frete.get('transportadora_id'),
                    'nome_tabela': frete.get('nome_tabela', ''),
                    'tipo_carga': frete.get('tipo_carga', ''),
                    'modalidade': frete.get('modalidade', ''),
                    'valor_bruto': frete.get('detalhes_calculo', {}).get('frete_base', 0),
                    'valor_com_icms': frete.get('valor_total', 0),
                    'valor_liquido': frete.get('valor_liquido', 0),
                    'frete_por_kg': round(frete.get('valor_total', 0) / peso, 4) if peso > 0 else 0,
                    'percentual_sobre_valor': round(
                        (frete.get('valor_total', 0) / valor * 100), 2
                    ) if valor > 0 else 0,
                }

                # Enriquecer com lead_time
                t_id = frete.get('transportadora_id')
                n_tabela = (frete.get('nome_tabela', '') or '').strip().upper()
                # Limpar sufixos adicionados pelo simulador
                for sufixo in [' (MAIS CARA', ' (MAIS CARA -']:
                    if sufixo in n_tabela:
                        n_tabela = n_tabela[:n_tabela.index(sufixo)].strip()

                # Tentar encontrar lead_time por transportadora_id em qualquer tabela
                lt = lead_times.get((t_id, n_tabela))
                if lt is None:
                    # Tentar sem filtrar nome_tabela
                    for (tid, _), lt_val in lead_times.items():
                        if tid == t_id and lt_val is not None:
                            lt = lt_val
                            break
                opcao['lead_time'] = lt

                # Detalhes do calculo (se detalhado)
                if detalhado:
                    opcao['detalhes'] = frete.get('detalhes_calculo', {})

                opcoes.append(opcao)

            # 5. Ordenar
            if ordenar == 'menor_prazo':
                opcoes.sort(key=lambda x: (x.get('lead_time') or 999, x['valor_com_icms']))
            else:  # menor_valor (default)
                opcoes.sort(key=lambda x: x['valor_com_icms'])

            # 6. Aplicar limite e numerar
            opcoes = opcoes[:limite]
            for i, opcao in enumerate(opcoes, 1):
                opcao['posicao'] = i

            resultado['sucesso'] = True
            resultado['opcoes'] = opcoes
            resultado['total_opcoes'] = len(opcoes)

            # Melhor opcao
            if opcoes:
                melhor = opcoes[0]
                resultado['melhor_opcao'] = {
                    'transportadora': melhor['transportadora'],
                    'valor_com_icms': melhor['valor_com_icms'],
                    'criterio': ordenar
                }

            return resultado

        except Exception as e:
            resultado['erro'] = str(e)
            import traceback
            resultado['traceback'] = traceback.format_exc()
            return resultado


def main():
    parser = argparse.ArgumentParser(
        description='Calcula cotacao de frete detalhada'
    )
    parser.add_argument('--peso', type=float, required=True,
                        help='Peso em kg')
    parser.add_argument('--valor', type=float, required=True,
                        help='Valor da mercadoria em R$')
    parser.add_argument('--cidade', type=str, required=True,
                        help='Nome da cidade destino')
    parser.add_argument('--uf', type=str, default=None,
                        help='UF destino (obrigatorio se cidade ambigua)')
    parser.add_argument('--tipo-carga', type=str, default=None,
                        choices=['DIRETA', 'FRACIONADA'],
                        help='Tipo de carga')
    parser.add_argument('--uf-origem', type=str, default='SP',
                        help='UF de origem (default: SP)')
    parser.add_argument('--detalhado', action='store_true',
                        help='Inclui breakdown completo de cada opcao')
    parser.add_argument('--ordenar', type=str, default='menor_valor',
                        choices=['menor_valor', 'menor_prazo'],
                        help='Criterio de ordenacao (default: menor_valor)')
    parser.add_argument('--limite', type=int, default=10,
                        help='Maximo de opcoes (default: 10)')

    args = parser.parse_args()

    resultado = calcular_cotacao(
        peso=args.peso,
        valor=args.valor,
        cidade=args.cidade,
        uf=args.uf,
        tipo_carga=args.tipo_carga,
        uf_origem=args.uf_origem,
        detalhado=args.detalhado,
        ordenar=args.ordenar,
        limite=args.limite
    )

    print(json.dumps(resultado, indent=2, ensure_ascii=False, default=str))


if __name__ == '__main__':
    main()
