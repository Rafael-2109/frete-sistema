#!/usr/bin/env python3
"""
Script para buscar tabelas de frete que atendem uma cidade.

Uso:
    python buscar_tabelas_cidade.py --cidade "Manaus" --uf AM
    python buscar_tabelas_cidade.py --cidade "Campinas"
    python buscar_tabelas_cidade.py --cidade "Sao Paulo" --uf SP --tipo-carga FRACIONADA
"""

import argparse
import json
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..')))


def buscar_tabelas_cidade(
    cidade: str,
    uf: str = None,
    tipo_carga: str = None,
    uf_origem: str = 'SP'
) -> dict:
    """
    Busca todas as tabelas de frete que atendem uma cidade.

    Fluxo:
    1. Normaliza nome da cidade
    2. Busca na tabela 'cidades' (localidades) — checando ambiguidade de UF
    3. Busca vínculos (CidadeAtendida) por codigo_ibge
    4. Busca TabelaFrete para cada vínculo (com suporte a grupo empresarial)
    5. Enriquece com dados de veículo para DIRETA

    Args:
        cidade: Nome da cidade (com ou sem acentos)
        uf: UF (obrigatório se cidade existir em múltiplos estados)
        tipo_carga: Filtrar por DIRETA ou FRACIONADA
        uf_origem: UF de origem (default: SP)

    Returns:
        dict: {sucesso, cidade, uf, codigo_ibge, icms_cidade, tabelas, total_tabelas}
    """
    from app import create_app, db
    from app.localidades.models import Cidade
    from app.vinculos.models import CidadeAtendida
    from app.tabelas.models import TabelaFrete
    from app.veiculos.models import Veiculo
    from app.utils.string_utils import remover_acentos
    from app.utils.grupo_empresarial import grupo_service
    from app.utils.tabela_frete_manager import TabelaFreteManager
    from sqlalchemy import func

    resultado = {
        'sucesso': False,
        'cidade_original': cidade,
        'uf_informada': uf,
        'tabelas': [],
        'total_tabelas': 0
    }

    if not cidade:
        resultado['erro'] = 'Nome da cidade nao informado'
        return resultado

    app = create_app()
    with app.app_context():
        try:
            # 1. Normalizar cidade
            cidade_normalizada = remover_acentos(cidade.strip()).upper()

            # 2. Buscar na tabela 'cidades' todas que casam com o nome
            cidades_db = Cidade.query.all()
            cidades_encontradas = []
            for c in cidades_db:
                nome_db_normalizado = remover_acentos(c.nome.strip()).upper()
                if nome_db_normalizado == cidade_normalizada:
                    cidades_encontradas.append(c)

            if not cidades_encontradas:
                resultado['erro'] = f"Cidade '{cidade}' nao encontrada na base de localidades"
                return resultado

            # 3. Checar ambiguidade de UF
            ufs_encontradas = list(set(c.uf for c in cidades_encontradas))

            if len(ufs_encontradas) > 1 and not uf:
                resultado['ambiguidade'] = True
                resultado['opcoes_uf'] = sorted(ufs_encontradas)
                resultado['mensagem'] = (
                    f"A cidade '{cidade}' existe em {len(ufs_encontradas)} estados: "
                    f"{', '.join(sorted(ufs_encontradas))}. Informe o UF com --uf."
                )
                return resultado

            # 4. Resolver cidade definitiva
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

            # Carregar dados da cidade
            cidade_nome = cidade_obj.nome
            cidade_uf = cidade_obj.uf
            cidade_icms = cidade_obj.icms or 0
            cidade_codigo_ibge = cidade_obj.codigo_ibge

            resultado['cidade'] = cidade_nome
            resultado['uf'] = cidade_uf
            resultado['codigo_ibge'] = cidade_codigo_ibge
            resultado['icms_cidade'] = cidade_icms

            # 5. Buscar vínculos por codigo_ibge
            atendimentos = CidadeAtendida.query.filter(
                CidadeAtendida.codigo_ibge == cidade_codigo_ibge
            ).all()

            if not atendimentos:
                resultado['sucesso'] = True
                resultado['mensagem'] = f"Nenhuma transportadora atende {cidade_nome}/{cidade_uf}"
                return resultado

            # 6. Carregar veículos para referência de peso máximo
            veiculos = {v.nome: v.peso_maximo for v in Veiculo.query.all()}

            # 7. Para cada vínculo, buscar tabelas
            tabelas_resultado = []
            tabelas_vistas = set()  # Evitar duplicatas

            for at in atendimentos:
                # Filtrar transportadoras inativas
                if hasattr(at.transportadora, 'ativo') and not at.transportadora.ativo:
                    continue

                # Grupo empresarial
                grupo_ids = grupo_service.obter_transportadoras_grupo(at.transportadora_id)

                # Buscar tabelas
                query_tabelas = TabelaFrete.query.filter(
                    TabelaFrete.transportadora_id.in_(grupo_ids),
                    TabelaFrete.uf_origem == uf_origem,
                    TabelaFrete.uf_destino == cidade_uf,
                    func.upper(func.trim(TabelaFrete.nome_tabela)) == func.upper(func.trim(at.nome_tabela))
                )

                tabelas = query_tabelas.all()

                # Filtrar por tipo_carga se informado
                if tipo_carga:
                    tabelas = [t for t in tabelas if t.tipo_carga == tipo_carga.upper()]

                for tf in tabelas:
                    # Chave de deduplicação
                    chave = (tf.transportadora_id, tf.nome_tabela, tf.tipo_carga, tf.modalidade)
                    if chave in tabelas_vistas:
                        continue
                    tabelas_vistas.add(chave)

                    # Extrair dados via TabelaFreteManager
                    dados_tabela = TabelaFreteManager.preparar_dados_tabela(tf)

                    # Montar info da tabela
                    info_tabela = {
                        'transportadora': at.transportadora.razao_social,
                        'transportadora_id': at.transportadora_id,
                        'optante': at.transportadora.optante or False,
                        'nome_tabela': tf.nome_tabela,
                        'tipo_carga': tf.tipo_carga,
                        'modalidade': tf.modalidade,
                        'lead_time': at.lead_time,
                    }

                    # Adicionar campos da tabela de frete
                    for campo in TabelaFreteManager.CAMPOS:
                        if campo in ('modalidade', 'nome_tabela'):
                            continue  # Já incluídos acima
                        info_tabela[campo] = dados_tabela.get(campo, 0)

                    # Para DIRETA, adicionar peso máximo do veículo
                    if tf.tipo_carga == 'DIRETA' and tf.modalidade:
                        from app.utils.vehicle_utils import normalizar_nome_veiculo
                        modalidade_normalizada = normalizar_nome_veiculo(tf.modalidade)
                        peso_max = veiculos.get(modalidade_normalizada)
                        if peso_max:
                            info_tabela['peso_maximo_veiculo'] = peso_max

                    tabelas_resultado.append(info_tabela)

            # 8. Ordenar: FRACIONADA primeiro, depois DIRETA, por transportadora
            tabelas_resultado.sort(key=lambda x: (
                0 if x['tipo_carga'] == 'FRACIONADA' else 1,
                x['transportadora'],
                x.get('modalidade', '')
            ))

            resultado['sucesso'] = True
            resultado['tabelas'] = tabelas_resultado
            resultado['total_tabelas'] = len(tabelas_resultado)

            return resultado

        except Exception as e:
            resultado['erro'] = str(e)
            return resultado


def main():
    parser = argparse.ArgumentParser(
        description='Busca tabelas de frete que atendem uma cidade'
    )
    parser.add_argument('--cidade', type=str, required=True,
                        help='Nome da cidade (com ou sem acentos)')
    parser.add_argument('--uf', type=str, default=None,
                        help='UF (obrigatorio se cidade existir em multiplos estados)')
    parser.add_argument('--tipo-carga', type=str, default=None,
                        choices=['DIRETA', 'FRACIONADA'],
                        help='Filtrar por tipo de carga')
    parser.add_argument('--uf-origem', type=str, default='SP',
                        help='UF de origem (default: SP)')

    args = parser.parse_args()

    resultado = buscar_tabelas_cidade(
        cidade=args.cidade,
        uf=args.uf,
        tipo_carga=args.tipo_carga,
        uf_origem=args.uf_origem
    )

    print(json.dumps(resultado, indent=2, ensure_ascii=False, default=str))


if __name__ == '__main__':
    main()
