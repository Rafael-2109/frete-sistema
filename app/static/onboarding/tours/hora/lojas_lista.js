window.OnboardingEngine.register({
  id: 'hora.lojas_lista',
  titulo: 'Cadastro de lojas',
  requirePerm: { modulo: 'lojas', acao: 'ver' },
  autoStartRoute: '/hora/lojas',
  steps: [
    { element: '#tabela-lojas', title: 'Lojas cadastradas', description: 'Cada loja fisica da HORA. Nome, CNPJ, endereco, geolocalizacao.' },
    { element: '#btn-nova-loja', title: 'Cadastrar loja', description: 'Lojas tem permissoes proprias — usuarios so veem dados das suas lojas.' },
    { element: '#btn-mapa-lojas', title: 'Visualizar no mapa', description: 'Mapa interativo com pins de cada loja. Util para gestao territorial.' }
  ]
});
