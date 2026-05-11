"""
Catalogo declarativo de comandos navegaveis para Ctrl+K.

Cada item espelha EXATAMENTE uma entrada de _sidebar.html (ou submenu/header),
com a MESMA condicao de permissao.

Validador automatico: scripts/audits/cmdk_catalog_validator.py
Ao adicionar/remover item da sidebar, atualizar esta lista.
"""
from dataclasses import dataclass
from typing import Callable, Optional

from flask import current_app, url_for
from flask_login import current_user

from app.cmdk.services import permissoes as P


# =============================================================================
# Modelo
# =============================================================================

@dataclass(frozen=True)
class Comando:
    endpoint: str                    # endpoint Flask para url_for
    label: str                       # nome curto exibido
    subtitle: str                    # "Grupo > Submenu"
    icon: str                        # classe FontAwesome
    can_show: Callable               # callback(user) -> bool
    keywords: str = ''               # termos extras para busca (sinonimos)
    url_kwargs: Optional[dict] = None  # kwargs para url_for (ex: {'posicao': 'todos'})


# =============================================================================
# Catalogo (~107 comandos espelhando _sidebar.html)
# =============================================================================
# Ordem segue _sidebar.html. Comentarios indicam linhas-fonte.

COMANDOS: list[Comando] = [

    # -------------------------------------------------------------------------
    # LOGISTICA > Operacional (sidebar L57-101)
    # -------------------------------------------------------------------------
    Comando('pedidos.lista_pedidos', 'Lista de Pedidos',
            'Logística › Operacional', 'fas fa-list-alt',
            P.has_logistica, 'pedidos lista carteira'),
    Comando('separacao.listar', 'Separação',
            'Logística › Operacional', 'fas fa-boxes',
            P.has_logistica, 'separacao lote'),
    Comando('separacao.importar', 'Importar Separação',
            'Logística › Operacional', 'fas fa-upload',
            P.has_logistica, 'separacao importar planilha'),
    Comando('embarques.listar_embarques', 'Embarques',
            'Logística › Operacional', 'fas fa-shipping-fast',
            P.has_logistica, 'embarque transporte'),
    Comando('portaria.dashboard', 'Portaria',
            'Logística › Operacional', 'fas fa-truck',
            P.has_logistica, 'portaria entrada saida'),
    Comando('rastreamento.tela_monitoramento', 'Rastreamento GPS',
            'Logística › Operacional', 'fas fa-satellite-dish',
            P.has_logistica, 'rastreio gps mapa'),
    Comando('monitoramento.listar_entregas', 'Entregas Monitoradas',
            'Logística › Operacional', 'fas fa-eye',
            P.has_logistica, 'entregas monitoramento canhoto'),
    Comando('devolucao.devolucao_ocorrencia.index', 'Ocorrências Devolução',
            'Logística › Operacional', 'fas fa-undo-alt',
            P.has_logistica, 'devolucao nfd ocorrencia'),
    Comando('pallet_v3.unified.index', 'Gestão de Pallets',
            'Logística › Operacional', 'fas fa-pallet',
            P.has_logistica, 'pallet vasilhame'),
    Comando('portaria.historico', 'Histórico Portaria',
            'Logística › Operacional', 'fas fa-history',
            P.has_logistica, 'portaria historico'),
    Comando('recebimento_views.central_compras', 'Central Compras',
            'Logística › Operacional', 'fas fa-shopping-cart',
            P.has_logistica, 'compras recebimento PO NF DFE'),

    # -------------------------------------------------------------------------
    # LOGISTICA > Carteira & Estoque (sidebar L104-152)
    # -------------------------------------------------------------------------
    Comando('carteira.index', 'Carteira de Pedidos',
            'Logística › Carteira & Estoque', 'fas fa-shopping-cart',
            P.has_logistica, 'carteira pedidos'),
    Comando('manufatura.index', 'Manufatura/PCP',
            'Logística › Carteira & Estoque', 'fas fa-industry',
            P.has_logistica, 'manufatura pcp producao'),
    Comando('producao.listar_programacao', 'Programação Produção',
            'Logística › Carteira & Estoque', 'fas fa-calendar-check',
            P.has_logistica, 'programacao producao'),
    Comando('producao.listar_palletizacao', 'Cadastro Palletização',
            'Logística › Carteira & Estoque', 'fas fa-cubes',
            P.has_logistica, 'palletizacao cadastro'),
    Comando('sugestao_compras.index', 'Sugestão de Compras',
            'Logística › Carteira & Estoque', 'fas fa-shopping-cart',
            P.has_logistica, 'compras sugestao'),
    Comando('estoque.listar_movimentacoes', 'Movimentações Estoque',
            'Logística › Carteira & Estoque', 'fas fa-exchange-alt',
            P.has_logistica, 'estoque movimentacao'),
    Comando('estoque.saldo_estoque', 'Saldo de Estoque',
            'Logística › Carteira & Estoque', 'fas fa-chart-line',
            P.has_logistica, 'estoque saldo posicao'),
    Comando('estoque.listar_unificacao_codigos', 'Unificação Códigos',
            'Logística › Carteira & Estoque', 'fas fa-link',
            P.has_logistica, 'unificacao codigos produtos'),
    Comando('faturamento.listar_faturamento_produtos', 'Faturamento por Produto',
            'Logística › Carteira & Estoque', 'fas fa-receipt',
            P.has_logistica, 'faturamento produto NF'),
    Comando('localidades.listar_rotas', 'Cadastro de Rotas',
            'Logística › Carteira & Estoque', 'fas fa-route',
            P.has_logistica, 'rotas cadastro'),
    Comando('localidades.listar_sub_rotas', 'Sub-rotas',
            'Logística › Carteira & Estoque', 'fas fa-map-marker-alt',
            P.has_logistica, 'sub-rotas localidade'),

    # -------------------------------------------------------------------------
    # LOGISTICA > Cadastros (sidebar L154-212)
    # -------------------------------------------------------------------------
    Comando('transportadoras.cadastrar_transportadora', 'Transportadoras',
            'Logística › Cadastros', 'fas fa-truck',
            P.cadastros_transportadoras, 'transportadora cadastro'),
    Comando('portaria.cadastrar_motorista', 'Cadastrar Motorista',
            'Logística › Cadastros', 'fas fa-user-plus',
            P.cadastros_motoristas, 'motorista cadastro'),
    Comando('portaria.listar_motoristas', 'Motoristas',
            'Logística › Cadastros', 'fas fa-users',
            P.cadastros_motoristas, 'motoristas lista'),
    Comando('localidades.cadastrar_cidade', 'Cidades',
            'Logística › Cadastros', 'fas fa-map-marker-alt',
            P.cadastros_localidades, 'cidades localidade'),
    Comando('veiculos.admin_veiculos', 'Administrar Veículos',
            'Logística › Cadastros', 'fas fa-truck',
            P.cadastros_veiculos, 'veiculos admin'),
    Comando('cadastros_agendamento.listar_contatos', 'Agendamento',
            'Logística › Cadastros', 'fas fa-calendar-alt',
            P.cadastros_agendamento, 'agendamento contatos'),
    Comando('tabelas.cadastrar_tabela_frete', 'Tabelas de Frete',
            'Logística › Cadastros', 'fas fa-table',
            P.cadastros_tabelas, 'tabelas frete cadastro'),
    Comando('tabelas.importar_tabela_frete', 'Importar Tabelas',
            'Logística › Cadastros', 'fas fa-upload',
            P.cadastros_tabelas, 'tabelas importar'),
    Comando('tabelas.historico_tabelas', 'Histórico Tabelas',
            'Logística › Cadastros', 'fas fa-history',
            P.cadastros_tabelas, 'tabelas historico'),
    Comando('tabelas.simulacao_frete', 'Simulação de Frete',
            'Logística › Cadastros', 'fas fa-calculator',
            P.cadastros_tabelas, 'simulacao frete cotacao'),

    # -------------------------------------------------------------------------
    # LOGISTICA > Consultas (sidebar L214-248)
    # -------------------------------------------------------------------------
    Comando('fretes.listar_fretes', 'Buscar Fretes',
            'Logística › Consultas', 'fas fa-search',
            P.has_logistica, 'fretes buscar consulta'),
    Comando('tabelas.listar_todas_tabelas', 'Consulta de Tabelas',
            'Logística › Consultas', 'fas fa-eye',
            P.has_logistica, 'tabelas consulta'),
    Comando('vinculos.consulta_vinculos', 'Consulta de Vínculos',
            'Logística › Consultas', 'fas fa-link',
            P.has_logistica, 'vinculos consulta'),
    Comando('cadastros_agendamento.importar_contatos', 'Importar Agendamento',
            'Logística › Consultas', 'fas fa-calendar-plus',
            P.has_logistica, 'agendamento importar contatos'),
    Comando('vinculos.importar_vinculos', 'Importar Vínculos',
            'Logística › Consultas', 'fas fa-link',
            P.has_logistica, 'vinculos importar'),
    Comando('financeiro.importar_pendencias', 'Pendências Financeiras',
            'Logística › Consultas', 'fas fa-file-import',
            P.has_logistica, 'financeiro pendencias importar'),
    Comando('tagplus.pagina_importacao', 'TagPlus',
            'Logística › Consultas', 'fas fa-sync',
            P.has_logistica, 'tagplus importacao'),

    # -------------------------------------------------------------------------
    # MOTOCHEFE (sidebar L262-345)
    # -------------------------------------------------------------------------
    Comando('motochefe.listar_equipes', 'Equipes de Vendas',
            'MotoChefe', 'fas fa-users',
            P.has_motochefe, 'equipes vendas motochefe'),
    Comando('motochefe.listar_crossdocking', 'CrossDocking',
            'MotoChefe', 'fas fa-truck-loading',
            P.has_motochefe, 'crossdocking motochefe'),
    Comando('motochefe.listar_vendedores', 'Vendedores',
            'MotoChefe', 'fas fa-user-tie',
            P.has_motochefe, 'vendedores motochefe'),
    Comando('motochefe.listar_transportadoras', 'Transportadoras',
            'MotoChefe', 'fas fa-truck',
            P.has_motochefe, 'transportadoras motochefe'),
    Comando('motochefe.listar_clientes', 'Clientes',
            'MotoChefe', 'fas fa-building',
            P.has_motochefe, 'clientes motochefe'),
    Comando('motochefe.listar_empresas', 'Empresas Faturamento',
            'MotoChefe', 'fas fa-industry',
            P.has_motochefe, 'empresas faturamento motochefe'),
    Comando('motochefe.listar_modelos', 'Modelos de Motos',
            'MotoChefe', 'fas fa-list',
            P.has_motochefe, 'modelos motos motochefe'),
    Comando('motochefe.listar_motos', 'Estoque (Chassi)',
            'MotoChefe', 'fas fa-motorcycle',
            P.has_motochefe, 'estoque chassi motos motochefe'),
    Comando('motochefe.listar_pedidos', 'Pedidos de Venda',
            'MotoChefe', 'fas fa-file-invoice',
            P.has_motochefe, 'pedidos venda motochefe'),
    Comando('motochefe.listar_titulos', 'Títulos a Receber',
            'MotoChefe', 'fas fa-receipt',
            P.has_motochefe, 'titulos receber motochefe'),
    Comando('motochefe.listar_comissoes', 'Comissões',
            'MotoChefe', 'fas fa-hand-holding-usd',
            P.has_motochefe, 'comissoes motochefe'),
    Comando('motochefe.listar_embarques', 'Embarques MotoChefe',
            'MotoChefe', 'fas fa-shipping-fast',
            P.has_motochefe, 'embarques motochefe'),
    Comando('motochefe.extrato_financeiro', 'Extrato Financeiro',
            'MotoChefe', 'fas fa-file-invoice-dollar',
            P.has_motochefe, 'extrato financeiro motochefe'),
    Comando('motochefe.listar_contas_a_pagar', 'Contas a Pagar',
            'MotoChefe', 'fas fa-hand-holding-usd',
            P.has_motochefe, 'contas pagar motochefe'),
    Comando('motochefe.listar_contas_a_receber', 'Contas a Receber',
            'MotoChefe', 'fas fa-money-bill-wave',
            P.has_motochefe, 'contas receber motochefe'),
    Comando('motochefe.listar_titulos_a_pagar_route', 'Títulos a Pagar',
            'MotoChefe', 'fas fa-file-invoice',
            P.has_motochefe, 'titulos pagar motochefe'),
    Comando('motochefe.custos_operacionais', 'Custos Operacionais',
            'MotoChefe', 'fas fa-dollar-sign',
            P.has_motochefe, 'custos operacionais motochefe'),
    Comando('motochefe.listar_despesas', 'Despesas Mensais',
            'MotoChefe', 'fas fa-wallet',
            P.has_motochefe, 'despesas mensais motochefe'),
    Comando('motochefe.confirmacao_pedidos', 'Confirmação Pedidos',
            'MotoChefe', 'fas fa-tasks',
            P.has_motochefe, 'confirmacao pedidos motochefe'),

    # -------------------------------------------------------------------------
    # LOJAS HORA (sidebar L348-524) — permissoes granulares tem_perm_hora
    # -------------------------------------------------------------------------
    Comando('hora.dashboard', 'Dashboard HORA',
            'Lojas HORA', 'fas fa-tachometer-alt',
            P.hora_perm('dashboard'), 'lojas hora dashboard'),
    Comando('hora.modelos_lista', 'Modelos',
            'Lojas HORA › Cadastros', 'fas fa-motorcycle',
            P.hora_perm('modelos'), 'modelos hora motos'),
    Comando('hora.modelos_pendencias_lista', 'Modelos pendentes',
            'Lojas HORA › Cadastros', 'fas fa-question-circle',
            P.hora_perm('modelos'), 'modelos pendentes hora'),
    Comando('hora.modelos_unificar_form', 'Unificar modelos',
            'Lojas HORA › Cadastros', 'fas fa-compress-arrows-alt',
            P.hora_perm('modelos', 'aprovar'), 'unificar modelos hora'),
    Comando('hora.lojas_lista', 'Lojas',
            'Lojas HORA › Cadastros', 'fas fa-store-alt',
            P.hora_perm('lojas'), 'lojas hora lista'),
    Comando('hora.permissoes_lista', 'Usuários HORA',
            'Lojas HORA › Cadastros', 'fas fa-user-shield',
            P.hora_perm('usuarios'), 'usuarios permissoes hora'),
    Comando('hora.tagplus_forma_map_lista', 'Formas de pagamento',
            'Lojas HORA › Cadastros', 'fas fa-money-bill-wave',
            P.hora_perm('tagplus'), 'pagamento formas hora tagplus'),
    Comando('hora.pedidos_lista', 'Pedidos de Compras HORA',
            'Lojas HORA › Movimentação', 'fas fa-clipboard-list',
            P.hora_perm('pedidos'), 'pedidos compras hora'),
    Comando('hora.pedidos_importar_imagem', 'Importar Pedido (OCR)',
            'Lojas HORA › Movimentação', 'fas fa-camera',
            P.hora_perm('pedidos', 'criar'), 'importar pedido OCR hora'),
    Comando('hora.nfs_lista', 'NFs de Entrada HORA',
            'Lojas HORA › Movimentação', 'fas fa-file-invoice',
            P.hora_perm('nfs'), 'nfs entrada hora'),
    Comando('hora.recebimentos_lista', 'Recebimento HORA',
            'Lojas HORA › Movimentação', 'fas fa-box-open',
            P.hora_perm('recebimentos'), 'recebimento hora'),
    Comando('hora.vendas_lista', 'Pedidos de Venda HORA',
            'Lojas HORA › Movimentação', 'fas fa-cash-register',
            P.hora_perm('vendas'), 'vendas pedidos hora'),
    Comando('hora.tagplus_emissoes_lista', 'NFs de Saída HORA',
            'Lojas HORA › Movimentação', 'fas fa-file-invoice-dollar',
            P.hora_perm('tagplus'), 'nfs saida hora tagplus'),
    Comando('hora.transferencias_lista', 'Transferências HORA',
            'Lojas HORA › Movimentação', 'fas fa-exchange-alt',
            P.hora_perm('transferencias'), 'transferencias hora'),
    Comando('hora.emprestimos_lista', 'Empréstimos HORA',
            'Lojas HORA › Movimentação', 'fas fa-handshake',
            P.hora_perm('emprestimos'), 'emprestimos hora'),
    Comando('hora.estoque_lista', 'Estoque HORA',
            'Lojas HORA › Movimentação', 'fas fa-warehouse',
            P.hora_perm('estoque'), 'estoque hora'),
    Comando('hora.pecas_lista', 'Peças faltando',
            'Lojas HORA › Ocorrências', 'fas fa-puzzle-piece',
            P.hora_perm('pecas'), 'pecas faltando hora'),
    Comando('hora.devolucoes_lista', 'Devoluções HORA',
            'Lojas HORA › Ocorrências', 'fas fa-undo',
            P.hora_perm('devolucoes'), 'devolucoes hora'),
    Comando('hora.avarias_lista', 'Avarias HORA',
            'Lojas HORA › Ocorrências', 'fas fa-tools',
            P.hora_perm('avarias'), 'avarias hora'),
    Comando('hora.tagplus_pedido_venda_novo', 'Novo Pedido de Venda HORA',
            'Lojas HORA › Faturamento', 'fas fa-plus-circle',
            P.hora_perm('vendas', 'criar'), 'novo pedido venda hora'),
    Comando('hora.tagplus_conta', 'Conta TagPlus',
            'Lojas HORA › Faturamento', 'fas fa-key',
            P.hora_perm('tagplus'), 'tagplus conta hora'),
    Comando('hora.tagplus_checklist', 'Checklist TagPlus',
            'Lojas HORA › Faturamento', 'fas fa-clipboard-check',
            P.hora_perm('tagplus'), 'tagplus checklist hora'),
    Comando('hora.tagplus_produto_map_lista', 'Mapeamento produtos',
            'Lojas HORA › Faturamento', 'fas fa-link',
            P.hora_perm('tagplus'), 'mapeamento produtos hora tagplus'),
    Comando('hora.tagplus_backfill', 'Backfill API',
            'Lojas HORA › Faturamento', 'fas fa-cloud-download-alt',
            P.hora_perm('tagplus'), 'backfill api hora'),
    Comando('hora.vendas_upload', 'Backfill DANFE PDF',
            'Lojas HORA › Faturamento', 'fas fa-upload',
            P.hora_perm('tagplus'), 'backfill danfe pdf hora'),
    Comando('hora.tagplus_backfill_pedidos_legados', 'Backfill pedidos legados',
            'Lojas HORA › Faturamento', 'fas fa-history',
            P.hora_perm('tagplus'), 'backfill pedidos legados hora'),

    # -------------------------------------------------------------------------
    # MOTOS ASSAI (sidebar L527-534)
    # -------------------------------------------------------------------------
    Comando('motos_assai.dashboard', 'Motos Assai',
            'Motos Assai', 'fas fa-motorcycle',
            P.has_motos_assai, 'motos assai sendas QPA'),

    # -------------------------------------------------------------------------
    # CARVIA (sidebar L540-560)
    # -------------------------------------------------------------------------
    Comando('carvia.fluxo_caixa', 'CarVia — Vencimentos',
            'CarVia', 'fas fa-truck-moving',
            P.has_carvia, 'carvia vencimentos fluxo caixa'),
    Comando('carvia.dashboard', 'CarVia Dashboard',
            'CarVia', 'fas fa-tachometer-alt',
            P.has_carvia, 'carvia dashboard'),

    # -------------------------------------------------------------------------
    # FINANCEIRO (sidebar L563-664)
    # -------------------------------------------------------------------------
    Comando('financeiro.dashboard', 'Central Financeira',
            'Financeiro', 'fas fa-landmark',
            P.acessa_financeiro_geral, 'financeiro central dashboard'),
    Comando('custeio.index', 'Sistema de Custeio',
            'Financeiro', 'fas fa-calculator',
            P.is_admin, 'custeio sistema admin'),
    Comando('fretes.index', 'Dashboard Fretes',
            'Financeiro › Fretes', 'fas fa-tachometer-alt',
            P.fretes_visualizar, 'fretes dashboard'),
    Comando('fretes.lancar_cte', 'Lançar CTe',
            'Financeiro › Fretes', 'fas fa-plus-circle',
            P.fretes_lancar, 'cte lancar frete'),
    Comando('fretes.listar_aprovacoes', 'Aprovações',
            'Financeiro › Fretes', 'fas fa-check-circle',
            P.fretes_aprovar, 'aprovacao fretes'),
    Comando('fretes.listar_faturas', 'Faturas de Frete',
            'Financeiro › Fretes', 'fas fa-file-pdf',
            P.fretes_faturas, 'faturas frete'),
    Comando('fretes.relatorio_analise_fretes', 'Análise de Fretes',
            'Financeiro', 'fas fa-chart-bar',
            P.pode_acessar_financeiro, 'analise fretes relatorio'),
    Comando('fretes.listar_pendencias_cancelamento_cte', 'Pendências Cancel. CTe',
            'Financeiro', 'fas fa-envelope-open-text',
            P.pode_acessar_financeiro, 'cancelamento cte pendencias'),
    Comando('recebimento_views.central_fiscal', 'Central Fiscal',
            'Financeiro', 'fas fa-file-invoice',
            P.financeiro_pendencias, 'central fiscal nf entrada'),
    Comando('financeiro.comprovantes_hub', 'Comprovantes Boleto',
            'Financeiro', 'fas fa-receipt',
            P.pode_acessar_financeiro, 'comprovantes boleto'),
    Comando('financeiro.remessa_vortx_historico', 'Remessas VORTX',
            'Financeiro', 'fas fa-file-invoice-dollar',
            P.pode_gerar_remessa_vortx, 'vortx remessa'),
    Comando('carvia.nova_despesa_extra_por_nf_carvia', 'Nova Despesa Extra CarVia',
            'Financeiro › CarVia', 'fas fa-plus',
            P.has_carvia, 'despesa extra carvia'),
    Comando('carvia.buscar_operacao_para_cte_complementar', 'Criar CTe Complementar',
            'Financeiro › CarVia', 'fas fa-file-invoice',
            P.has_carvia, 'cte complementar carvia'),
    Comando('carvia.simulador_carga', 'Simulador 3D',
            'Financeiro › CarVia', 'fas fa-cube',
            P.has_carvia, 'simulador 3D carga carvia'),

    # -------------------------------------------------------------------------
    # COMERCIAL (sidebar L669-704)
    # -------------------------------------------------------------------------
    Comando('comercial.dashboard_diretoria', 'Dashboard Comercial',
            'Comercial', 'fas fa-chart-bar',
            P.comercial, 'comercial dashboard diretoria'),
    Comando('comercial.lista_clientes', 'Acompanhamento Clientes',
            'Comercial', 'fas fa-building',
            P.comercial, 'comercial clientes acompanhamento',
            url_kwargs={'posicao': 'em_aberto'}),
    Comando('comercial.lista_clientes', 'Posição Total Clientes',
            'Comercial', 'fas fa-list-alt',
            P.comercial, 'comercial clientes posicao total',
            url_kwargs={'posicao': 'todos'}),
    Comando('comercial.analise_margem', 'Análise de Margem',
            'Comercial', 'fas fa-chart-pie',
            P.comercial_nao_vendedor, 'margem analise comercial'),
    Comando('comercial.admin_permissoes', 'Gerenciar Permissões Comercial',
            'Comercial', 'fas fa-user-shield',
            P.comercial_admin_ou_gerente, 'permissoes comercial admin'),

    # -------------------------------------------------------------------------
    # ADMINISTRACAO > Usuarios (sidebar L719-747)
    # -------------------------------------------------------------------------
    Comando('auth.usuarios_pendentes', 'Pendentes Aprovação',
            'Administração › Usuários', 'fas fa-user-clock',
            P.admin_usuarios_aprovar, 'usuarios pendentes aprovar'),
    Comando('auth.listar_usuarios', 'Todos Usuários',
            'Administração › Usuários', 'fas fa-users',
            P.admin_usuarios_aprovar, 'usuarios todos lista'),
    Comando('auth.registro', 'Link Registro Público',
            'Administração › Usuários', 'fas fa-external-link-alt',
            P.admin_usuarios, 'registro publico link'),
    Comando('auth.registro_motochefe_sp', 'Link Cadastro MotoChefe',
            'Administração › Usuários', 'fas fa-external-link-alt',
            P.admin_usuarios, 'cadastro motochefe link'),
    Comando('auth.registro_motos_assai', 'Link Cadastro Motos Assai',
            'Administração › Usuários', 'fas fa-external-link-alt',
            P.admin_usuarios, 'cadastro motos assai link'),

    # -------------------------------------------------------------------------
    # ADMINISTRACAO > Pessoal (sidebar L751-790, restrito users 1, 62)
    # -------------------------------------------------------------------------
    Comando('pessoal.pessoal_dashboard.index', 'Pessoal — Dashboard',
            'Administração › Pessoal', 'fas fa-chart-pie',
            P.is_user_pessoal, 'pessoal dashboard'),
    Comando('pessoal.pessoal_fluxo_caixa.index', 'Pessoal — Fluxo de Caixa',
            'Administração › Pessoal', 'fas fa-water',
            P.is_user_pessoal, 'pessoal fluxo caixa'),
    Comando('pessoal.pessoal_fluxo_caixa.faturas_index', 'Pessoal — Faturas Cartão',
            'Administração › Pessoal', 'fas fa-credit-card',
            P.is_user_pessoal, 'pessoal faturas cartao'),
    Comando('pessoal.pessoal_matches_empresa.index', 'Pessoal — Matches Empresa',
            'Administração › Pessoal', 'fas fa-link',
            P.is_user_pessoal, 'pessoal matches empresa'),
    Comando('pessoal.pessoal_transacoes.listar', 'Pessoal — Transações',
            'Administração › Pessoal', 'fas fa-receipt',
            P.is_user_pessoal, 'pessoal transacoes'),
    Comando('pessoal.pessoal_analise.index', 'Pessoal — Análise',
            'Administração › Pessoal', 'fas fa-chart-line',
            P.is_user_pessoal, 'pessoal analise'),
    Comando('pessoal.pessoal_importacao.importar', 'Pessoal — Importar CSV',
            'Administração › Pessoal', 'fas fa-file-upload',
            P.is_user_pessoal, 'pessoal importar csv'),
    Comando('pessoal.pessoal_orcamento.index', 'Pessoal — Orçamento',
            'Administração › Pessoal', 'fas fa-calculator',
            P.is_user_pessoal, 'pessoal orcamento'),
    Comando('pessoal.pessoal_provisao.index', 'Pessoal — Provisões',
            'Administração › Pessoal', 'fas fa-calendar-plus',
            P.is_user_pessoal, 'pessoal provisao'),
    Comando('pessoal.pessoal_configuracao.index', 'Pessoal — Configuração',
            'Administração › Pessoal', 'fas fa-cog',
            P.is_user_pessoal, 'pessoal configuracao'),

    # -------------------------------------------------------------------------
    # ADMINISTRACAO > Seguranca (sidebar L795-816, admin only)
    # -------------------------------------------------------------------------
    Comando('seguranca.dashboard', 'Segurança — Dashboard',
            'Administração › Segurança', 'fas fa-tachometer-alt',
            P.is_admin, 'seguranca dashboard'),
    Comando('seguranca.listar_vulnerabilidades', 'Segurança — Vulnerabilidades',
            'Administração › Segurança', 'fas fa-bug',
            P.is_admin, 'vulnerabilidades seguranca'),
    Comando('seguranca.verificar_senha', 'Segurança — Verificar Senha',
            'Administração › Segurança', 'fas fa-key',
            P.is_admin, 'verificar senha seguranca'),
    Comando('seguranca.configuracao', 'Segurança — Configuração',
            'Administração › Segurança', 'fas fa-cog',
            P.is_admin, 'configuracao seguranca'),

    # -------------------------------------------------------------------------
    # ADMINISTRACAO > IA (sidebar L820-857)
    # -------------------------------------------------------------------------
    Comando('agente.pagina_chat', 'Agente Nacom',
            'Administração › IA', 'fas fa-comments',
            P.agente_nacom, 'agente nacom chat IA'),
    Comando('agente_lojas.pagina_chat', 'Agente Lojas HORA',
            'Administração › IA', 'fas fa-motorcycle',
            P.agente_lojas, 'agente lojas hora chat IA'),
    Comando('agente.pagina_insights', 'Insights',
            'Administração › IA', 'fas fa-chart-bar',
            P.is_admin, 'insights analytics'),
    Comando('agente.admin_session_store_page', 'SessionStore',
            'Administração › IA', 'fas fa-database',
            P.is_admin, 'sessionstore observability'),
]


# =============================================================================
# API publica
# =============================================================================

def listar_para_usuario(user=None) -> list[dict]:
    """
    Retorna comandos visiveis para o usuario com URL resolvida.

    Itens com endpoint inexistente (rota nao registrada) sao silenciosamente
    pulados — Ctrl+K nao deve quebrar a UI.
    """
    user = user if user is not None else current_user
    items = []
    for cmd in COMANDOS:
        try:
            if not cmd.can_show(user):
                continue
            kwargs = cmd.url_kwargs or {}
            url = url_for(cmd.endpoint, **kwargs)
        except Exception as e:
            current_app.logger.debug(
                f"[cmdk] comando ignorado endpoint={cmd.endpoint}: {e}"
            )
            continue
        items.append({
            'id': f"{cmd.endpoint}::{','.join(sorted((cmd.url_kwargs or {}).keys()))}",
            'label': cmd.label,
            'subtitle': cmd.subtitle,
            'icon': cmd.icon,
            'url': url,
            'keywords': cmd.keywords,
            'tipo': 'comando',
        })
    return items


def filtrar(items: list[dict], q: str, limit: int = 8) -> list[dict]:
    """
    Filtra comandos por query (substring case-insensitive em label, subtitle, keywords).

    Score:
        1.0 = label exato
        0.9 = label.startswith
        0.7 = label.contains
        0.5 = subtitle.contains
        0.4 = keywords.contains
    """
    if not q:
        return items[:limit]
    q_lower = q.lower().strip()
    if not q_lower:
        return items[:limit]

    scored: list[tuple[float, dict]] = []
    for item in items:
        label_l = item['label'].lower()
        subtitle_l = item['subtitle'].lower()
        keywords_l = (item.get('keywords') or '').lower()

        score = 0.0
        if label_l == q_lower:
            score = 1.0
        elif label_l.startswith(q_lower):
            score = 0.9
        elif q_lower in label_l:
            score = 0.7
        elif q_lower in subtitle_l:
            score = 0.5
        elif q_lower in keywords_l:
            score = 0.4

        if score > 0:
            scored.append((score, item))

    scored.sort(key=lambda t: -t[0])
    return [{**item, 'score': score} for score, item in scored[:limit]]
