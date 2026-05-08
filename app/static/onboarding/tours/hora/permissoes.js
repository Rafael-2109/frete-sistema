window.OnboardingEngine.register({
  id: 'hora.permissoes',
  titulo: 'Gerenciar permissoes de usuarios',
  requirePerm: { modulo: 'usuarios', acao: 'ver' },
  autoStartRoute: '/hora/permissoes',
  steps: [
    { element: '#card-pendentes',        title: 'Cadastros pendentes',     description: 'Usuarios novos esperando aprovacao. Voce define a loja deles e aprova. Sem loja = sem acesso.' },
    { element: '#tabela-usuarios',       title: 'Lista de usuarios ativos', description: 'Cada linha = 1 usuario com permissao HORA. Clique no nome para abrir a matriz modulo × acao.' },
    { element: '#matriz-modulos',        title: 'Matriz granular',          description: '21 modulos × 5 acoes (Ver/Criar/Editar/Apagar/Aprovar). Marque so o que o usuario precisa.' },
    { element: '#btn-salvar-matriz',     title: 'Salvar',                   description: 'Upsert em batch. Toma efeito no proximo refresh do usuario (cache por instancia no current_user).' }
  ]
});
