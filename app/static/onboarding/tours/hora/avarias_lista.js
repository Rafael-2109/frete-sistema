window.OnboardingEngine.register({
  id: 'hora.avarias_lista',
  titulo: 'Avarias em estoque',
  requirePerm: { modulo: 'avarias', acao: 'ver' },
  autoStartRoute: '/hora/avarias',
  steps: [
    { element: '#filtros-avarias', title: 'Filtros', description: 'Loja, status (aberta/resolvida/ignorada), periodo.' },
    { element: '#btn-nova-avaria', title: 'Registrar avaria', description: 'Foto + descricao da avaria. <strong>Nao bloqueia venda</strong> — so sinaliza.' },
    { element: '#tabela-avarias', title: 'Lista de avarias', description: 'Aberta = ainda nao resolvida. Multiplas avarias por chassi sao permitidas.' }
  ]
});
