"""
Service de Precificação - Sistema MotoCHEFE
Aplica regras de CrossDocking ou EquipeVendasMoto baseado no cliente
"""
from decimal import Decimal
from app.motochefe.models import ClienteMoto, EquipeVendasMoto, CrossDocking


def obter_regras_aplicaveis(cliente_id, equipe_id):
    """
    Retorna objeto de regras (CrossDocking ou EquipeVendasMoto)
    baseado na configuração do cliente

    Args:
        cliente_id: int
        equipe_id: int

    Returns:
        dict: {
            'tipo': 'crossdocking' ou 'equipe',
            'objeto': CrossDocking ou EquipeVendasMoto,
            'preco_metodo': callable,
            'permitir_montagem': bool,
            'tipo_comissao': str,
            'valor_comissao_fixa': Decimal,
            'percentual_comissao': Decimal,
            'comissao_rateada': bool
        }
    """
    cliente = ClienteMoto.query.get(cliente_id)

    if cliente and cliente.crossdocking:
        # ✅ Usa regras de CrossDocking genérico (único registro)
        crossdocking = CrossDocking.query.first()  # ⚠️ ALTERADO: Busca o único registro genérico

        if not crossdocking:
            # ⚠️ Erro crítico: CrossDocking não configurado
            raise ValueError(
                "Cliente configurado para CrossDocking mas registro genérico não existe! "
                "Execute o script de criação do CrossDocking genérico."
            )

        return {
            'tipo': 'crossdocking',
            'objeto': crossdocking,
            'preco_metodo': crossdocking.obter_preco_modelo,
            'permitir_montagem': crossdocking.permitir_montagem,
            'tipo_comissao': crossdocking.tipo_comissao,
            'valor_comissao_fixa': crossdocking.valor_comissao_fixa,
            'percentual_comissao': crossdocking.percentual_comissao,
            'comissao_rateada': crossdocking.comissao_rateada,
        }
    else:
        # ✅ Usa regras de EquipeVendasMoto
        equipe = EquipeVendasMoto.query.get(equipe_id)
        if equipe:
            return {
                'tipo': 'equipe',
                'objeto': equipe,
                'preco_metodo': equipe.obter_preco_modelo,
                'permitir_montagem': equipe.permitir_montagem,
                'tipo_comissao': equipe.tipo_comissao,
                'valor_comissao_fixa': equipe.valor_comissao_fixa,
                'percentual_comissao': equipe.percentual_comissao,
                'comissao_rateada': equipe.comissao_rateada,
            }
        else:
            return {
                'tipo': 'none',
                'objeto': None,
                'preco_metodo': None,
                'permitir_montagem': False,
                'tipo_comissao': 'FIXA_EXCEDENTE',
                'valor_comissao_fixa': Decimal('0'),
                'percentual_comissao': Decimal('0'),
                'comissao_rateada': True,
            }


def obter_preco_venda(cliente_id, equipe_id, modelo_id):
    """
    Retorna preço de venda considerando CrossDocking ou Equipe

    Args:
        cliente_id: int
        equipe_id: int
        modelo_id: int

    Returns:
        Decimal: Preço de venda
    """
    regras = obter_regras_aplicaveis(cliente_id, equipe_id)

    if regras['preco_metodo']:
        return regras['preco_metodo'](modelo_id)

    return Decimal('0')


def obter_configuracao_equipe(equipe_id):
    """
    Retorna configuração de prazo e parcelamento da equipe

    Args:
        equipe_id: int

    Returns:
        dict: {
            'permitir_prazo': bool,
            'permitir_parcelamento': bool,
            'permitir_montagem': bool
        }
    """
    equipe = EquipeVendasMoto.query.get(equipe_id)

    if not equipe:
        return {
            'permitir_prazo': False,
            'permitir_parcelamento': False,
            'permitir_montagem': False
        }

    return {
        'permitir_prazo': equipe.permitir_prazo,
        'permitir_parcelamento': equipe.permitir_parcelamento,
        'permitir_montagem': equipe.permitir_montagem
    }
