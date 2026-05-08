window.OnboardingEngine.register({
  id: 'motos_assai.pedidos_upload',
  titulo: 'Subir pedido VOE Q.P.A.',
  adminOnly: true,
  autoStartRoute: '/motos-assai/pedidos/upload',
  steps: [
    { element: '#upload-area',           title: 'PDF VOE do Sendas/Assai', description: '38 paginas × 3 modelos = 114 itens em ~30s. Parser deterministico primeiro, fallback Haiku 4.5 → Sonnet 4.6.' },
    { element: '#area-preview',          title: 'Preview por loja',         description: 'Cada pagina = 1 loja Sendas (LJ12, LJ34...). Confira se identificou todas antes de salvar.' },
    { element: '#campo-confianca',       title: 'Score de confianca',       description: 'lojas_distintas / total_paginas. Abaixo de 70% dispara LLM. Abaixo de 50% bloqueia salvamento.' },
    { element: '#btn-salvar-pedido',     title: 'Salvar como ABERTO',       description: 'Cria assai_pedido_venda + N itens (loja × modelo). Pronto pra consolidar em compra Motochefe.' }
  ]
});
