window.OnboardingEngine.register({
  id: 'motos_assai.lojas_lista',
  titulo: 'Lojas Sendas/Assai',
  autoStartRoute: '/motos-assai/lojas',
  steps: [
    { element: '#tabela-lojas-assai', title: 'Lojas cadastradas', description: 'Cada loja Sendas/Assai (LJ12, LJ34...) que recebe motos.' },
    { element: '#btn-mapa-lojas-assai', title: 'Visualizar no mapa', description: 'Mapa com numero de cada loja. Util para visualizar regioes atendidas.' }
  ]
});
