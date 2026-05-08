window.OnboardingEngine.register({
  id: 'motos_assai.compras_lista',
  titulo: 'Compras Motochefe (POs)',
  adminOnly: true,
  autoStartRoute: '/motos-assai/compras',
  steps: [
    { element: '#filtros-compras', title: 'Filtros', description: 'Status, numero MA-AAAA-NNNN, periodo.' },
    { element: '#btn-nova-compra', title: 'Consolidar nova compra', description: 'Acao manual do admin: selecione pedidos VOE em ABERTO e some-os em 1 PO. <strong>O PO nao e gerado automaticamente</strong> ao subir VOE.' },
    { element: '#tabela-compras', title: 'Lista de compras', description: 'Cada PO agrupa N pedidos VOE. Clique no numero do PO para abrir o detalhe — la voce <strong>baixa o PDF</strong> para enviar a Motochefe e, quando as motos chegarem, <strong>importa o recibo Motochefe</strong>.' }
  ]
});
