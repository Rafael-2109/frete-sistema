window.OnboardingEngine.register({
  id: 'hora.vendas_lista',
  titulo: 'Vendas (NF de saida)',
  requirePerm: { modulo: 'vendas', acao: 'ver' },
  autoStartRoute: '/hora/vendas',
  steps: [
    { element: '#filtros-vendas', title: 'Filtros', description: 'Cliente, chassi, status, periodo. Encontre cotacoes, pedidos confirmados ou faturados.' },
    { element: '#btn-nova-venda', title: 'Criar pedido de venda', description: 'Comeca uma cotacao manual via TagPlus. Cliente, chassi, forma de pagamento.' },
    { element: '#tabela-vendas', title: 'Lista de vendas', description: 'Status: COTACAO → CONFIRMADO → FATURADO → CANCELADO. Cada um permite operacoes diferentes.' }
  ]
});
