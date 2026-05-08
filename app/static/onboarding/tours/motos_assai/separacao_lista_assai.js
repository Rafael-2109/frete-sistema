window.OnboardingEngine.register({
  id: 'motos_assai.separacao_lista',
  titulo: 'Separacoes em andamento',
  autoStartRoute: '/motos-assai/separacao',
  steps: [
    { element: '#filtros-separacao', title: 'Filtros', description: 'Status (aberta/fechada), pedido, loja Sendas.' },
    { element: '#tabela-separacao', title: 'Lista de separacoes', description: 'Cada linha = pedido + loja sendo separado. Clique para abrir e escanear chassis.' }
  ]
});
