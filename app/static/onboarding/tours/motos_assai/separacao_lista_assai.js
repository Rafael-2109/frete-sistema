window.OnboardingEngine.register({
  id: 'motos_assai.separacao_lista',
  titulo: 'Separacoes em andamento',
  autoStartRoute: '/motos-assai/separacao',
  steps: [
    // 2026-05-13: removido step '#filtros-separacao' — feature de filtros nunca foi implementada
    // (id era esperancoso/antecipado pelo autor original do tour, sem callsite no template).
    { element: '#tabela-separacao', title: 'Lista de separacoes', description: 'Cada linha = pedido + loja sendo separado. Use os botoes (Visualizar / Datas / Alterar / Cancelar) para gerenciar a separacao. Clique em "Iniciar nova separacao" no topo para abrir o modal de criacao.' }
  ]
});
