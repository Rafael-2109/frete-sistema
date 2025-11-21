"""
Parser para processar planilha modelo do Portal Sendas
"""

import pandas as pd
from app import db
from app.portal.sendas.models_planilha import PlanilhaModeloSendas
import logging

logger = logging.getLogger(__name__)

def processar_planilha_modelo(filepath, usuario='Sistema'):
    """
    Processa a planilha modelo do Sendas e armazena no banco

    Args:
        filepath: Caminho do arquivo XLSX
        usuario: Usuário que está fazendo a importação

    Returns:
        dict: Resultado do processamento
    """
    try:
        # Ler arquivo XLSX pulando as duas primeiras linhas inúteis
        # O cabeçalho está na linha 3 (índice 2)
        df = pd.read_excel(filepath, engine='openpyxl', header=2)

        logger.info(f"Planilha lida: {len(df)} linhas, {len(df.columns)} colunas")
        logger.info(f"Colunas encontradas: {list(df.columns)[:5]}...")  # Log das primeiras 5 colunas

        # Verificar se tem as colunas esperadas (baseado nos nomes)
        # ✅ ATUALIZADO Nov/2025: Removido 'Número do pedido Trizy', adicionadas 3 colunas de data
        colunas_esperadas = [
            'Razão Social - Fornecedor',
            'Nome Fantasia - Fornecedor',
            'Unidade de destino',
            'UF Destino',
            'Fluxo de operação',
            'Código do pedido Cliente',
            'Código Produto Cliente',
            'Código Produto SKU Fornecedor',
            'EAN',
            'Setor',
            'Entrega De',          # ✅ NOVA - Coluna L (vem vazia na planilha modelo)
            'Entrega Até',         # ✅ NOVA - Coluna M (vem vazia na planilha modelo)
            'Data Ideal',          # ✅ NOVA - Coluna N (vem vazia na planilha modelo)
            'Descrição do Item',
            'Quantidade total',
            'Saldo disponível',
            'Unidade de medida'
        ]

        # Verificar colunas (ignorando a primeira que é Demanda)
        colunas_arquivo = df.columns.tolist()

        # Limpar tabela anterior
        PlanilhaModeloSendas.limpar_tabela()

        linhas_processadas = 0
        linhas_ignoradas = 0

        # Processar linha por linha
        for index, row in df.iterrows():
            try:
                # Criar registro com os dados EXATAMENTE como vêm
                # ✅ ATUALIZADO Nov/2025: Removido 'numero_pedido_trizy' (coluna não existe mais)
                novo_registro = PlanilhaModeloSendas(
                    razao_social_fornecedor=str(row.get('Razão Social - Fornecedor', '')),
                    nome_fantasia_fornecedor=str(row.get('Nome Fantasia - Fornecedor', '')),
                    unidade_destino=str(row.get('Unidade de destino', '')),
                    uf_destino=str(row.get('UF Destino', '')),
                    fluxo_operacao=str(row.get('Fluxo de operação', '')),
                    codigo_pedido_cliente=str(row.get('Código do pedido Cliente', '')),
                    codigo_produto_cliente=str(row.get('Código Produto Cliente', '')),
                    codigo_produto_sku_fornecedor=str(row.get('Código Produto SKU Fornecedor', '')),
                    ean=str(row.get('EAN', '')),
                    setor=str(row.get('Setor', '')),
                    numero_pedido_trizy='',  # ✅ Coluna removida do layout Sendas - manter vazio para compatibilidade
                    descricao_item=str(row.get('Descrição do Item', '')),
                    quantidade_total=float(row.get('Quantidade total', 0)) if pd.notna(row.get('Quantidade total')) else 0,
                    saldo_disponivel=float(row.get('Saldo disponível', 0)) if pd.notna(row.get('Saldo disponível')) else 0,
                    unidade_medida=str(row.get('Unidade de medida', '')),
                    usuario_importacao=usuario
                )

                db.session.add(novo_registro)
                linhas_processadas += 1

            except Exception as e:
                logger.warning(f"Erro na linha {index + 2}: {str(e)}") #type: ignore
                linhas_ignoradas += 1
                continue

        # Commit final
        db.session.commit()

        if linhas_processadas == 0:
            return {
                'sucesso': False,
                'mensagem': 'A planilha não possui linhas válidas'
            }

        return {
            'sucesso': True,
            'linhas_processadas': linhas_processadas,
            'linhas_ignoradas': linhas_ignoradas,
            'mensagem': f'Planilha importada com sucesso! {linhas_processadas} linhas processadas.'
        }

    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao processar planilha: {str(e)}")
        return {
            'sucesso': False,
            'mensagem': f'Erro ao processar arquivo: {str(e)}'
        }