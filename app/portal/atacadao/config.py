"""
Configurações do Portal Atacadão (Hodie Booking)
Baseado no fluxo real do portal
"""

ATACADAO_CONFIG = {
    'urls': {
        'base': 'https://atacadao.hodiebooking.com.br',
        'login': 'https://atacadao.hodiebooking.com.br/',
        'pedidos': 'https://atacadao.hodiebooking.com.br/pedidos',
        'pedido_detalhe': 'https://atacadao.hodiebooking.com.br/pedidos/{pedido_id}',
        'criar_carga': 'https://atacadao.hodiebooking.com.br/cargas/create?id_pedido={pedido_id}',
        'carga_detalhe': 'https://atacadao.hodiebooking.com.br/cargas/{carga_id}',
        'agendamento_status': 'https://atacadao.hodiebooking.com.br/agendamentos/{protocolo}'
    },
    
    'seletores': {
        # Página de busca de pedidos
        'campo_pedido': '#nr_pedido',
        'botao_filtrar': '#enviarFiltros',
        'link_exibir_pedido': 'a[href*="/pedidos/"][title="Exibir"]',
        
        # Página do pedido
        'botao_solicitar_agendamento': '.btn_solicitar_agendamento',
        
        # Formulário de criação de carga/agendamento
        'campo_data_leadtime': '#leadtime_minimo',
        'campo_data_desejada': 'input[name="data_desejada"]',
        'campo_transportadora': '#transportadora',
        'botao_buscar_transportadora': 'button[data-target="#modal-transportadoras"]',
        
        # Modal de seleção de transportadora
        'radio_transportadora_agregado': 'input[id="1"][value*="Agregado"]',
        'botao_selecionar_transportadora': '.selecionar',
        
        # Campos do formulário de carga
        'select_carga_especie': 'select[name="carga_especie_id"]',
        'select_tipo_veiculo': 'select[name="tipo_veiculo"]',
        
        # Produtos - campos dinâmicos
        'campo_qtd_produto': 'input[name^="qtd_alocada"]',  # Campos de quantidade começam com qtd_alocada
        
        # Botão salvar
        'botao_salvar': '#salvar',
        
        # Modal de confirmação de NF
        'modal_sucesso': '#regSucesso',
        'botao_nao_incluir_nf': '#btnNao',
        'botao_sim_incluir_nf': '#btnSim',
        
        # Página de acompanhamento
        'link_acompanhe_agendamento': 'i.fa-arrow-circle-right',
        
        # Status do agendamento
        'numero_protocolo': '.box-numero-protocolo .valor',
        'status_agendamento': '.box-numero-protocolo .status span',
        
        # Indicadores de login/sessão
        'menu_principal': '.navbar-nav',
        'link_logout': 'a[href*="logout"]',
        'usuario_logado': '.user-name, .navbar-user'
    },
    
    'veiculos_permitidos': {
        '6': 'Kombi/Van - (Cód.: 1 - Máx: 5 paletes)',
        '5': 'F4000-3/4 - Baú - (Cód.: 3 - Máx: 10 paletes)',
        '11': 'Toco-Baú - (Cód.: 4 - Máx: 24 paletes)',
        '8': 'Truck-Baú - (Cód.: 5 - Máx: 75 paletes)',
        '2': 'Carreta-Baú - (Cód.: 7 - Máx: 80 paletes)'
    },
    
    'valores_padrao': {
        'transportadora_id': '1',  # ID da transportadora "Agregado"
        'carga_especie': '1',  # Paletizada
        'incluir_nf': False  # Não incluir NF no momento
    },
    
    'timeouts': {
        'page_load': 30,
        'element_wait': 10,
        'form_submit': 20,
        'modal_wait': 5
    },
    
    'mensagens': {
        'sucesso': [
            'Registro salvo com sucesso',
            'Solicitação de Agendamento',
            'Carga criada com sucesso'
        ],
        'status': {
            'aguardando': 'Aguardando aprovação',
            'aprovado': 'Aguardando check-in',
            'confirmado': 'Confirmado',
            'cancelado': 'Cancelado'
        }
    },
    
    'tem_captcha': True,
    'tem_2fa': False
}