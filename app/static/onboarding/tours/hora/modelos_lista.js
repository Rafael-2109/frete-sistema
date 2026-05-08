window.OnboardingEngine.register({
  id: 'hora.modelos_lista',
  titulo: 'Catalogo de modelos',
  requirePerm: { modulo: 'modelos', acao: 'ver' },
  autoStartRoute: '/hora/modelos',
  steps: [
    { element: '#tabela-modelos', title: 'Modelos cadastrados', description: 'Cada modelo de moto eletrica. Preco a vista, a prazo, foto, aliases (variacoes de nome).' },
    { element: '#btn-novo-modelo', title: 'Cadastrar modelo', description: 'Modelo + 2 precos (vista/prazo). Aliases gerenciam variacoes (ex: BOB AM = BOB).' },
    { element: '#btn-pendencias', title: 'Modelos pendentes', description: 'Nomes que apareceram em NFs/pedidos mas nao bateram com nenhum modelo. Resolva para criar HoraMoto.' }
  ]
});
