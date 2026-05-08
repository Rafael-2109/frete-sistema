window.OnboardingEngine.register({
  id: 'motos_assai.pedidos_lista',
  titulo: 'Pedidos VOE Q.P.A.',
  adminOnly: true,
  autoStartRoute: '/motos-assai/pedidos',
  steps: [
    { element: '#filtros-pedidos-voe', title: 'Filtros', description: 'Status, periodo. Encontre pedidos abertos ou ja consolidados.' },
    { element: '#btn-upload-pedido-voe', title: 'Subir PDF VOE', description: 'PDF do Sendas/Assai. Parser identifica 38 paginas × 3 modelos = 114 itens em ~30s.' },
    { element: '#tabela-pedidos-voe', title: 'Lista de pedidos', description: '<strong>ABERTO</strong> = aguarda voce consolidar manualmente em <strong>POs Motochefe → Novo PO</strong> (PO nao nasce automatico). <strong>EM_PRODUCAO</strong> = ja foi consolidado em PO.' }
  ]
});
