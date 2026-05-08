window.OnboardingEngine.register({
  id: 'hora.emprestimos_lista',
  titulo: 'Emprestimos com lojas externas',
  requirePerm: { modulo: 'emprestimos', acao: 'ver' },
  autoStartRoute: '/hora/emprestimos',
  steps: [
    { element: '#filtros-emprestimos', title: 'Filtros', description: 'Emprestimos de motos com lojas parceiras (nao da HORA). Cobranca por ressarcimento.' },
    { element: '#btn-novo-emprestimo', title: 'Novo emprestimo', description: 'Registra moto emprestada. Quando voltar ou for cobrada, atualiza status.' },
    { element: '#tabela-emprestimos', title: 'Lista de emprestimos', description: 'Status: ABERTO, RESSARCIDO, CANCELADO.' }
  ]
});
