// app/static/onboarding/tours/hora/_macro.js
window.OnboardingEngine.register({
  id: 'hora.macro',
  titulo: 'Bem-vindo a Lojas HORA',
  autoStartRoute: '/hora/dashboard',
  steps: [
    {
      element: '#menu-vendas',
      title: 'Vendas (NF saida)',
      description: 'Aqui voce cria pedidos de venda, acompanha o que foi faturado e gerencia devolucoes.',
      requirePerm: { modulo: 'vendas', acao: 'ver' }
    },
    {
      element: '#menu-estoque',
      title: 'Estoque de motos',
      description: 'Lista de motos por loja e por chassi. Mostra tambem avarias e reservas de pedido.',
      requirePerm: { modulo: 'estoque', acao: 'ver' }
    },
    {
      element: '#menu-recebimentos',
      title: 'Receber NF da Motochefe',
      description: 'Suba o PDF da NF, confira chassi por chassi e finalize o recebimento. <strong>Daqui sai a entrada de motos no estoque.</strong>',
      requirePerm: { modulo: 'recebimentos', acao: 'ver' }
    },
    {
      element: '#menu-transferencias',
      title: 'Transferir entre lojas',
      description: 'Movimentacao de motos entre filiais. Precisa de confirmacao na loja destino para concluir.',
      requirePerm: { modulo: 'transferencias', acao: 'ver' }
    },
    {
      element: '#menu-pecas-estoque',
      title: 'Pecas e acessorios',
      description: 'Capacete, retrovisor, bateria. Saldo por loja, transferencia e ajuste manual.',
      requirePerm: { modulo: 'pecas_estoque', acao: 'ver' }
    },
    {
      element: '#menu-tagplus',
      title: 'NFe via TagPlus',
      description: 'Emissao fiscal eletronica. Precisa de OAuth configurado e mapeamento de produtos.',
      requirePerm: { modulo: 'tagplus', acao: 'ver' }
    },
    {
      element: '#menu-modelos',
      title: 'Catalogo de modelos',
      description: 'Cadastro central de modelos com preco a vista/a prazo. Resolve nomes divergentes (BOB AM = BOB).',
      requirePerm: { modulo: 'modelos', acao: 'ver' }
    },
    {
      element: '#menu-permissoes',
      title: 'Gerenciar usuarios',
      description: 'Aprovar cadastros pendentes, atribuir lojas e configurar permissoes granulares por modulo.',
      requirePerm: { modulo: 'usuarios', acao: 'ver' }
    },
    {
      element: '#help-button',
      title: 'Precisou de ajuda?',
      description: 'Clique no <strong>?</strong> em qualquer tela para ver o tour daquela tela especifica.'
    }
  ]
});
