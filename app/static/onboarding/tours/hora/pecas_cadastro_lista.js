window.OnboardingEngine.register({
  id: 'hora.pecas_cadastro_lista',
  titulo: 'Cadastro de pecas',
  requirePerm: { modulo: 'pecas_cadastro', acao: 'ver' },
  autoStartRoute: '/hora/pecas/cadastro',
  steps: [
    { element: '#tabela-pecas-cadastro', title: 'Pecas cadastradas', description: 'Capacete, retrovisor, bateria... Codigo interno, NCM, CFOP, preco padrao.' },
    { element: '#btn-nova-peca', title: 'Cadastrar peca', description: 'Pecas sao fungiveis (sem chassi). Saldo gerenciado por movimentos no estoque.' }
  ]
});
