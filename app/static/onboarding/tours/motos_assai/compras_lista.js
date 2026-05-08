window.OnboardingEngine.register({
  id: 'motos_assai.compras_lista',
  titulo: 'Compras Motochefe (POs)',
  adminOnly: true,
  autoStartRoute: '/motos-assai/compras',
  steps: [
    { element: '#filtros-compras', title: 'Filtros', description: 'Status, numero MA-AAAA-NNNN, periodo.' },
    { element: '#btn-nova-compra', title: 'Consolidar nova compra', description: 'Selecione pedidos VOE abertos para criar 1 PO consolidado.' },
    { element: '#tabela-compras', title: 'Lista de compras', description: 'Cada compra agrupa N pedidos. Baixe o PDF do PO para enviar a Motochefe.' }
  ]
});
