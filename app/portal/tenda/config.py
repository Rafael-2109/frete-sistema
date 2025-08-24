"""
Configurações do Portal Tenda (Agendar Entrega)
Baseado no mapeamento das telas e fluxo real do portal
"""

TENDA_CONFIG = {
    'urls': {
        'base': 'https://v1.agendarentrega.com',
        'login': 'https://v1.agendarentrega.com/auth/login',
        'login_password': 'https://v1.agendarentrega.com/auth/login/password',
        'marcar_agenda': 'https://v1.agendarentrega.com/agenda-entrega/marcar-agenda',
        'pesquisar_pdd': 'https://v1.agendarentrega.com/pesquisar-pdd',
        'finalizar_agendamento': 'https://v1.agendarentrega.com/finalizar',
        'consultar_protocolo': 'https://v1.agendarentrega.com/consultar/{protocolo}'
    },
    
    'seletores': {
        # Tela 1 - Marcar Agenda
        'checkbox_sem_xml': 'input[type="checkbox"][value=""]',  # Marcar agenda sem XML
        'campo_tipo_remetente': 'select[name="tipo_remetente"]',
        'campo_cnpj_fornecedor': 'input[name="identidade"]',  # CPF ou CNPJ
        'campo_filtro_destinatario': 'div[role="menu"] span[role="menuitem"]',
        'campo_local_entrega': 'ul[role="listbox"] li[role="option"]',
        'botao_confirmar_tela1': 'button[type="submit"]',
        
        # Tela 2 - Pesquisar PDD (Pedido de Distribuição)
        'botao_pesquisar_pdd': 'button.pesquisar-pdd',
        'campo_busca_pdd': 'input[name="pdd_search"]',
        'lista_pdd': 'div.modal-pdd div.linha-pdd',
        'checkbox_pdd': 'input[type="checkbox"].pdd-select',
        'botao_confirmar_produtos': 'button.confirmar-produtos',
        'botao_proximo_tela2': 'button.proximo',
        
        # Tela 3 - Configurações Finais
        'select_veiculo': 'select[name="tipo_veiculo"]',
        'select_tipo_carga': 'select[name="tipo_carga"]',
        'select_tipo_volume': 'select[name="tipo_volume"]',
        'campo_qtd_volume': 'input[name="quantidade_volume"]',
        'campo_data_agendamento': 'input[type="date"]',
        'select_horario': 'select[name="horario_agendamento"]',
        'botao_finalizar': 'button.finalizar-agendamento',
        
        # Elementos de feedback
        'protocolo_gerado': 'div.protocolo-numero',
        'mensagem_sucesso': 'div.alert-success',
        'mensagem_erro': 'div.alert-danger',
        
        # Indicadores de login
        'campo_usuario': 'input[name="username"]',
        'campo_senha': 'input[name="password"]',
        'botao_login': 'button[type="submit"]',
        'usuario_logado': 'span.user-name'
    },
    
    'valores_padrao': {
        'cnpj_fornecedor': '61.724.241/0003-30',  # CNPJ fixo do fornecedor
        'tipo_remetente': 'F',  # Valor fixo: F = Fornecedor / Distribuidor
        'tipo_remetente_texto': 'Fornecedor / Distribuidor',  # Texto exibido
        'marcar_sem_xml': True,
        'tipo_volume': 'pallet',
        'tipo_carga': 'paletizada'
    },
    
    'locais_entrega': {
        # Mapeamento de CNPJ para data-value do local de entrega
        # Estes valores precisam ser mapeados conforme o De-Para cadastrado
        '01157555000100': '15644de0-a3ca-11ed-be47-027c76ee0e9a',  # BNSU - CD
        '01157555000200': 'c44e17f3-ff1d-11ed-a55e-027b54a41676',  # CT03 - AMOREIRAS
        '01157555000300': 'c3cca362-ff1d-11ed-a55e-027b54a41676',  # CT05 - CAMPINAS
        # Adicionar mais mapeamentos conforme necessário
    },
    
    'tipos_veiculo': {
        'pequeno': 'VAN',
        'medio': 'TRUCK',
        'grande': 'CARRETA',
        'bitruck': 'BITRUCK'
    },
    
    'tipos_carga': {
        'paletizada': 'PALETIZADA',
        'granel': 'GRANEL',
        'caixas': 'CAIXAS'
    },
    
    'tipos_volume': {
        'pallet': 'PALLET',
        'caixa': 'CAIXA',
        'fardo': 'FARDO',
        'unidade': 'UNIDADE'
    },
    
    'horarios_disponveis': [
        '08:00', '08:30', '09:00', '09:30', '10:00', '10:30',
        '11:00', '11:30', '12:00', '13:00', '13:30', '14:00',
        '14:30', '15:00', '15:30', '16:00', '16:30', '17:00'
    ],
    
    'timeouts': {
        'page_load': 30,
        'element_wait': 10,
        'form_submit': 20,
        'modal_wait': 5,
        'pdd_search': 15
    },
    
    'mensagens': {
        'sucesso': [
            'Agendamento realizado com sucesso',
            'Protocolo gerado',
            'Solicitação confirmada'
        ],
        'status': {
            'aguardando': 'Aguardando confirmação',
            'confirmado': 'Agendamento confirmado',
            'cancelado': 'Agendamento cancelado',
            'em_analise': 'Em análise'
        }
    },
    
    'tem_captcha': False,
    'tem_2fa': False,
    
    # Regras de negócio específicas do Tenda
    'regras_negocio': {
        'min_pallets': 1,
        'max_pallets': 33,  # Máximo para carreta
        'lead_time_minimo': 2,  # Dias úteis
        'antecedencia_maxima': 30,  # Dias
        'requer_pdd': True,  # Sempre requer seleção de PDD
        'permite_agendamento_sem_xml': True
    }
}