window.OnboardingEngine.register({
  id: 'hora.pedidos_lista',
  titulo: 'Pedidos de compra (HORA → Motochefe)',
  requirePerm: { modulo: 'pedidos', acao: 'ver' },
  autoStartRoute: '/hora/pedidos',
  steps: [
    { element: '#filtros-pedidos', title: 'Filtros', description: 'Filtre por loja, status, periodo. Util para encontrar pedidos abertos ou em producao.' },
    { element: '#btn-novo-pedido', title: 'Criar pedido novo', description: 'Compra que a HORA faz da Motochefe. Define loja destino e itens (motos/pecas).' },
    { element: '#tabela-pedidos', title: 'Lista de pedidos', description: 'Cada linha = 1 pedido. Status mostra: ABERTO, EM_PRODUCAO, RECEBIDO, CANCELADO.' }
  ]
});
