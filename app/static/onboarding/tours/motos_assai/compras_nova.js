window.OnboardingEngine.register({
  id: 'motos_assai.compras_nova',
  titulo: 'Consolidar compra Motochefe',
  adminOnly: true,
  autoStartRoute: '/motos-assai/compras/nova',
  steps: [
    { element: '#multiselect-pedidos',   title: 'Selecione pedidos VOE', description: 'N pedidos viram 1 compra (PO). Sistema soma quantidades por modelo automaticamente.' },
    { element: '#preview-totalizadores', title: 'Preview do PO',         description: 'Lista consolidada: modelo X qtd_total. Verifique antes de gerar — nao tem desfazer trivial.' },
    { element: '#btn-gerar-compra',      title: 'Criar compra MA-AAAA-NNNN', description: 'Cria assai_compra_motochefe + assai_compra_motochefe_pedido (N:N). Pedidos viram EM_PRODUCAO.' },
    { element: '#btn-baixar-pdf',        title: 'Baixar PO em PDF',      description: 'WeasyPrint renderiza modelo, qtd, total. Esse PDF vai pro vendedor da Motochefe.' }
  ]
});
