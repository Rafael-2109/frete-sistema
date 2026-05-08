window.OnboardingEngine.register({
  id: 'hora.transferencias_lista',
  titulo: 'Transferencias entre lojas',
  requirePerm: { modulo: 'transferencias', acao: 'ver' },
  autoStartRoute: '/hora/transferencias',
  steps: [
    { element: '#filtros-transferencias', title: 'Filtros', description: 'Status, loja origem, loja destino, periodo.' },
    { element: '#btn-nova-transferencia', title: 'Nova transferencia', description: 'Move motos entre lojas. Status EM_TRANSITO ate a loja destino confirmar.' },
    { element: '#tabela-transferencias', title: 'Lista de transferencias', description: 'EM_TRANSITO, TRANSFERIDA, CANCELADA. Cancele apenas em transito.' }
  ]
});
