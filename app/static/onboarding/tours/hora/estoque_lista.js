window.OnboardingEngine.register({
  id: 'hora.estoque_lista',
  titulo: 'Consultar estoque de motos',
  requirePerm: { modulo: 'estoque', acao: 'ver' },
  autoStartRoute: '/hora/estoque',
  steps: [
    { element: '#filtros-estoque',       title: 'Filtros',         description: 'Loja, modelo, busca por chassi (substring). Combinam — voce pode filtrar tudo junto.' },
    { element: '#tabela-estoque',        title: 'Lista de motos',  description: 'Cada linha = 1 chassi. <strong>Status efetivo</strong> vem do ultimo evento, nao do banco.' },
    { element: '#badge-avaria',          title: 'Avarias abertas', description: 'Badge amarelo "⚠ N" indica chassis com avarias registradas. Nao bloqueia venda, so avisa.' },
    { element: '#badge-reservado',       title: 'Reservas de pedido', description: 'Badge azul "Reservado em Pedido #X" = chassi em uma venda COTACAO/CONFIRMADO/FATURADO.' }
  ]
});
