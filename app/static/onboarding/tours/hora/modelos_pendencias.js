window.OnboardingEngine.register({
  id: 'hora.modelos_pendencias',
  titulo: 'Resolver modelos pendentes',
  requirePerm: { modulo: 'modelos', acao: 'editar' },
  autoStartRoute: '/hora/modelos/pendencias',
  steps: [
    { element: '#tabela-pendencias',     title: 'Nomes desconhecidos',   description: 'Cada linha = nome que apareceu numa NF/pedido/TagPlus mas nao bate com nenhum modelo cadastrado.' },
    { element: '#btn-vincular',          title: 'Vincular a modelo existente', description: 'Cria HoraModeloAlias apontando o nome para um modelo. Retroativamente cria HoraMoto pros chassis travados.' },
    { element: '#btn-criar-novo',        title: 'Criar novo modelo',     description: 'Se for modelo realmente novo. Cria HoraModelo + alias automaticamente.' },
    { element: '#btn-ignorar',           title: 'Ignorar (lixo)',        description: 'Para nomes mal extraidos pelo parser que nao da pra resolver. Nao cria nada.' }
  ]
});
