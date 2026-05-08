window.OnboardingEngine.register({
  id: 'hora.devolucoes_venda_lista',
  titulo: 'Devolucoes de venda',
  requirePerm: { modulo: 'devolucoes_venda', acao: 'ver' },
  autoStartRoute: '/hora/devolucoes-venda',
  steps: [
    { element: '#filtros-devolucoes-venda', title: 'Filtros', description: 'Cliente devolveu uma venda? Filtre por status e periodo.' },
    { element: '#btn-nova-devolucao-venda', title: 'Registrar devolucao', description: 'Selecione a venda original e os chassis que voltaram. Pode ser parcial.' },
    { element: '#tabela-devolucoes-venda', title: 'Lista de devolucoes', description: 'Cada devolucao emite evento DEVOLVIDA nos chassis e devolve ao estoque.' }
  ]
});
