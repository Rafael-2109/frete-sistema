window.OnboardingEngine.register({
  id: 'motos_assai.carregamento_lista',
  titulo: 'Carregamentos — visao geral',
  autoStartRoute: '/motos-assai/carregamento',
  steps: [
    {
      element: '#btn-iniciar-carregamento',
      title: 'Iniciar novo carregamento',
      description: 'Abre modal para escolher pedido + loja Sendas. A2: N carregamentos paralelos podem coexistir para o mesmo (pedido, loja) — cada um vira um veiculo de carga independente.'
    },
    {
      element: '#tabela-em-andamento',
      title: 'Em andamento',
      description: 'Carregamentos EM_CARREGAMENTO ativos. Clique "Continuar" para abrir a tela de escaneio e adicionar mais chassis.'
    },
    {
      element: '#tabela-finalizados',
      title: 'Finalizados recentes',
      description: 'Carregamentos FINALIZADO. Cada um gerou ou atualizou uma Sep CARREGADA. Clique no Sep # para ver a separacao alvo.'
    }
  ]
});
