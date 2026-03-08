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
        'agendamento_status': 'https://atacadao.hodiebooking.com.br/agendamentos/{protocolo}',
        'relatorio_itens': 'https://atacadao.hodiebooking.com.br/relatorio/itens',
        'planilha_pedidos': 'https://atacadao.hodiebooking.com.br/relatorio/planilhaPedidos',
        'cargas_planilha': 'https://atacadao.hodiebooking.com.br/cargas-planilha',
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
        'usuario_logado': '.user-name, .navbar-user',

        # Página /relatorio/planilhaPedidos (consultar saldo)
        'saldo_toggle_filtros': 'a[data-toggle="collapse"][data-target="#filtros-collapse"]',
        'saldo_limpar_datas': '#filtros-collapse > div.filtros-body > div > div.col-md-3.bootstrap-daterangepicker > div > span:nth-child(5) > button',
        'saldo_aplicar_filtros': '#enviarFiltros',
        'saldo_exportar_csv': '#exportarExcel',

        # Página /cargas-planilha (agendamento em lote)
        'lote_download_modelo': 'a.btn.btn-primary.pull-right',
        'lote_upload_browser': '#uploadForm > div > span > button.btn.btn-primary.inputfile-browser',
        'lote_enviar': '#enviar',
        'lote_confirmar_mapeamento': 'body > div.wrapper > div.content-wrapper > div.content > div > div:nth-child(3) > div > button.btn.btn-primary.pull-right',
        'lote_salvar': '#salvar2',
        'lote_modal_sucesso': '.modal-content:has-text("Registro criado com sucesso")',
        'lote_botao_ok': '#footerModalAlerta > div > div > button',
    },
    
    'veiculos_permitidos': {
        '6': 'Kombi/Van - (Cód.: 1 - Máx: 5 paletes)',
        '5': 'F4000-3/4 - Baú - (Cód.: 3 - Máx: 10 paletes) - Até 2.000 kg',
        '11': 'Toco-Baú - (Cód.: 4 - Máx: 24 paletes) - Até 4.000 kg',
        '8': 'Truck-Baú - (Cód.: 5 - Máx: 75 paletes) - Até 7.000 kg',
        '9': 'Truck-Sider - (Cód.: 6 - Máx: 75 paletes)',
        '2': 'Carreta-Baú - (Cód.: 7 - Máx: 80 paletes) - Acima de 7.000 kg',
        '4': 'Carreta-Sider - (Cód.: 8 - Máx: 80 paletes)',
        '3': 'Carreta-Container - (Cód.: 9 - Máx: 56 paletes)',
        '10': 'Carreta-Graneleira - (Cód.: 2 - Máx: 60 paletes)',
        '1': 'Bitrem-Graneleiro - (Cód.: 10 - Máx: 56 paletes)',
        '7': 'Rodotrem-Baú - (Cód.: 11 - Máx: 100 paletes)',
        '12': 'Truck-Graneleiro - (Cód.: 12 - Máx: 32 paletes)',
    },

    # Mapeamento Cod. planilha CSV → select value + nome + max_pallets
    # Cod. e usado na planilha de upload (coluna I do saldo, coluna veiculo do upload)
    # select_value e usado no agendamento individual via form HTML
    'veiculos_planilha': {
        '1': {'nome': 'Kombi/Van', 'max_pallets': 5, 'select_value': '6'},
        '2': {'nome': 'Carreta-Graneleira', 'max_pallets': 60, 'select_value': '10'},
        '3': {'nome': 'F4000-3/4 Bau', 'max_pallets': 10, 'select_value': '5'},
        '4': {'nome': 'Toco-Bau', 'max_pallets': 24, 'select_value': '11'},
        '5': {'nome': 'Truck-Bau', 'max_pallets': 75, 'select_value': '8'},
        '6': {'nome': 'Truck-Sider', 'max_pallets': 75, 'select_value': '9'},
        '7': {'nome': 'Carreta-Bau', 'max_pallets': 80, 'select_value': '2'},
        '8': {'nome': 'Carreta-Sider', 'max_pallets': 80, 'select_value': '4'},
        '9': {'nome': 'Carreta-Container', 'max_pallets': 56, 'select_value': '3'},
        '10': {'nome': 'Bitrem-Graneleiro', 'max_pallets': 56, 'select_value': '1'},
        '11': {'nome': 'Rodotrem-Bau', 'max_pallets': 100, 'select_value': '7'},
        '12': {'nome': 'Truck-Graneleiro', 'max_pallets': 32, 'select_value': '12'},
    },

    # Auto-selecao de veiculo por peso (usando Cod. planilha)
    'regras_veiculo_por_peso': {
        'ate_2000': '5',    # F4000-3/4  (Cód. planilha: 3)
        'ate_4000': '11',   # Toco-Baú   (Cód. planilha: 4)
        'ate_7000': '8',    # Truck-Baú  (Cód. planilha: 5)
        'acima_7000': '2'   # Carreta-Baú (Cód. planilha: 7)
    },

    # Auto-selecao por peso usando Cod. planilha (para scripts de agendamento lote)
    'regras_veiculo_planilha_por_peso': {
        'ate_2000': '3',    # F4000-3/4 Bau
        'ate_4000': '4',    # Toco-Bau
        'ate_7000': '5',    # Truck-Bau
        'acima_7000': '7'   # Carreta-Bau
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