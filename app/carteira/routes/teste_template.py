"""
Rota de teste para o template limpo da carteira agrupada
"""

from flask import render_template, jsonify
from flask_login import login_required
from datetime import date, datetime
from . import carteira_bp


@carteira_bp.route('/agrupados-limpo')
@login_required
def listar_agrupados_limpo():
    """
    Rota de teste para visualizar o template limpo da carteira agrupada
    com dados mock para validação da estrutura
    """
    
    # Dados mock para teste do template
    pedidos_mock = [
        {
            'num_pedido': 'PED001',
            'vendedor': 'João Silva',
            'equipe_vendas': 'Equipe Sul',
            'status_pedido': 'ABERTO',
            'data_pedido': date(2025, 1, 15),
            'raz_social_red': 'EMPRESA ABC LTDA',
            'cnpj_cpf': '12.345.678/0001-90',
            'nome_cidade': 'São Paulo',
            'cod_uf': 'SP',
            'rota': 'ROTA-SP-01',
            'sub_rota': 'SUB-SP-CENTRAL',
            'expedicao': date(2025, 1, 25),
            'agendamento': date(2025, 1, 26),
            'agendamento_confirmado': True,
            'protocolo': 'PROT12345',
            'valor_total': 15750.00,
            'peso_total': 320.5,
            'pallet_total': 4.2,
            'total_itens': 8,
            'qtd_separacoes': 2,
            'totalmente_separado': False,
            'pedido_cliente': 'PC-2025-001'
        },
        {
            'num_pedido': 'PED002',
            'vendedor': 'Maria Santos',
            'equipe_vendas': 'Equipe Norte',
            'status_pedido': 'COTADO',
            'data_pedido': date(2025, 1, 18),
            'raz_social_red': 'DISTRIBUIDORA XYZ S.A.',
            'cnpj_cpf': '98.765.432/0001-10',
            'nome_cidade': 'Rio de Janeiro',
            'cod_uf': 'RJ',
            'rota': 'ROTA-RJ-02',
            'sub_rota': 'SUB-RJ-ZONA-SUL',
            'expedicao': date(2025, 1, 28),
            'agendamento': None,
            'agendamento_confirmado': False,
            'protocolo': None,
            'valor_total': 8900.50,
            'peso_total': 180.3,
            'pallet_total': 2.1,
            'total_itens': 5,
            'qtd_separacoes': 1,
            'totalmente_separado': True,
            'pedido_cliente': 'PC-2025-002'
        },
        {
            'num_pedido': 'PED003',
            'vendedor': 'Carlos Oliveira',
            'equipe_vendas': 'Equipe Centro-Oeste',
            'status_pedido': 'ABERTO',
            'data_pedido': date(2025, 1, 20),
            'raz_social_red': 'COMERCIAL 123 EIRELI',
            'cnpj_cpf': '45.678.901/0001-23',
            'nome_cidade': 'Brasília',
            'cod_uf': 'DF',
            'rota': 'ROTA-DF-01',
            'sub_rota': None,
            'expedicao': None,
            'agendamento': None,
            'agendamento_confirmado': False,
            'protocolo': None,
            'valor_total': 22100.75,
            'peso_total': 450.8,
            'pallet_total': 6.5,
            'total_itens': 12,
            'qtd_separacoes': 0,
            'totalmente_separado': False,
            'pedido_cliente': None
        },
        {
            'num_pedido': 'PED004',
            'vendedor': 'Ana Costa',
            'equipe_vendas': 'Equipe Nordeste',
            'status_pedido': 'EMBARCADO',
            'data_pedido': date(2025, 1, 12),
            'raz_social_red': 'VAREJO MASTER LTDA',
            'cnpj_cpf': '78.901.234/0001-45',
            'nome_cidade': 'Salvador',
            'cod_uf': 'BA',
            'rota': 'ROTA-BA-03',
            'sub_rota': 'SUB-BA-METROPOLITANA',
            'expedicao': date(2025, 1, 22),
            'agendamento': date(2025, 1, 23),
            'agendamento_confirmado': False,  # Exemplo de "Ag. Aprovação"
            'protocolo': 'PROT67890',
            'valor_total': 5420.30,
            'peso_total': 95.2,
            'pallet_total': 1.3,
            'total_itens': 3,
            'qtd_separacoes': 3,
            'totalmente_separado': True,
            'pedido_cliente': 'PC-2025-004'
        }
    ]
    
    return render_template('carteira/agrupados_balanceado.html', 
                         pedidos=pedidos_mock,
                         total_pedidos=len(pedidos_mock))


# APIs reais implementadas em workspace_api.py