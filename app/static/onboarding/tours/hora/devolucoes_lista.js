window.OnboardingEngine.register({
  id: 'hora.devolucoes_lista',
  titulo: 'Devolucoes ao fornecedor',
  requirePerm: { modulo: 'devolucoes', acao: 'ver' },
  autoStartRoute: '/hora/devolucoes',
  steps: [
    { element: '#filtros-devolucoes', title: 'Filtros', description: 'Devolucoes que a HORA faz a Motochefe (problemas no recebimento).' },
    { element: '#btn-nova-devolucao', title: 'Nova devolucao', description: 'Registra motos com defeito que voltam pro fornecedor.' },
    { element: '#tabela-devolucoes', title: 'Lista de devolucoes', description: 'Status: ABERTA, ENVIADA, CONFIRMADA, CANCELADA.' }
  ]
});
