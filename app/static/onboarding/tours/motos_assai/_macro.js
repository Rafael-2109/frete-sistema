// app/static/onboarding/tours/motos_assai/_macro.js
window.OnboardingEngine.register({
  id: 'motos_assai.macro',
  titulo: 'Bem-vindo ao Motos Assai',
  autoStartRoute: '/motos-assai/dashboard',
  steps: [
    {
      element: '#menu-recibos',
      title: 'Recibos da Motochefe',
      description: 'Cada recibo lista os chassis que vao chegar. Suba o PDF/Excel para comecar a conferencia.'
    },
    {
      element: '#menu-montagem',
      title: 'Montagem (chao)',
      description: 'Marque a moto como MONTADA depois de conferir que esta OK. Use o leitor QR ou digite o chassi.'
    },
    {
      element: '#menu-disponibilizar',
      title: 'Disponibilizar',
      description: 'Apos colar a tag e o manual, a moto vai para DISPONIVEL e pode ser separada para um pedido.'
    },
    {
      element: '#menu-separacao',
      title: 'Separacao',
      description: 'Vincula chassis DISPONIVEL aos pedidos. <strong>Fungivel:</strong> qualquer chassi do mesmo modelo serve.'
    },
    {
      element: '#menu-pedidos-voe',
      title: 'Pedidos VOE Q.P.A.',
      description: 'Suba o PDF VOE do Sendas/Assai. O sistema parseia 38 paginas em ~30s e cria os itens automaticamente.',
      adminOnly: true
    },
    {
      element: '#menu-compras',
      title: 'Compras Motochefe',
      description: 'Consolida N pedidos VOE em 1 pedido de compra (PO) para a Motochefe. Gera PDF com modelos e quantidades.',
      adminOnly: true
    },
    {
      element: '#menu-faturamento',
      title: 'Faturamento',
      description: 'Gera Excel Q.P.A. da separacao concluida. Depois suba a NF Q.P.A. emitida para fazer o match BATEU/DIVERGENTE.',
      adminOnly: true
    },
    {
      element: '#help-button',
      title: 'Precisou de ajuda?',
      description: 'Clique no <strong>?</strong> em qualquer tela para ver o tour daquela tela.'
    }
  ]
});
