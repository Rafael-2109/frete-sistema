window.OnboardingEngine.register({
  id: 'hora.recebimentos_lista',
  titulo: 'Recebimentos da Motochefe',
  requirePerm: { modulo: 'recebimentos', acao: 'ver' },
  autoStartRoute: '/hora/recebimentos',
  steps: [
    { element: '#filtros-recebimentos', title: 'Filtros', description: 'Loja, status, periodo. Filtra recebimentos em andamento, finalizados ou com divergencia.' },
    { element: '#btn-novo-recebimento', title: 'Iniciar recebimento', description: 'Comeca um novo recebimento a partir de uma NF parseada. Conferencia chassi por chassi.' },
    { element: '#tabela-recebimentos', title: 'Lista de recebimentos', description: 'Status: EM_CONFERENCIA, FINALIZADO, COM_DIVERGENCIA. Clique para abrir o wizard.' }
  ]
});
