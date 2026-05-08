window.OnboardingEngine.register({
  id: 'hora.modelos_novo',
  titulo: 'Cadastrar modelo de moto',
  requirePerm: { modulo: 'modelos', acao: 'criar' },
  autoStartRoute: '/hora/modelos/novo',
  steps: [
    { element: '#campo-nome',            title: 'Nome canonico',     description: 'Nome principal. Variacoes virao como ALIASES (ex: "BOB AM" vira alias do modelo "BOB").' },
    { element: '#campo-preco-vista',     title: 'Preco a vista',     description: 'Aplica em vendas com forma de pagamento PIX, dinheiro, debito ou MISTO sem prazo.' },
    { element: '#campo-preco-prazo',     title: 'Preco a prazo',     description: 'Aplica em vendas com cartao credito ou outras formas com tipo_pagamento = A_PRAZO.' },
    { element: '#campo-foto',            title: 'Foto do modelo (opcional)', description: 'Mostrada na lista de modelos e no catalogo de venda. Sobe pro S3.' },
    { element: '#btn-salvar',            title: 'Salvar',            description: 'Cria modelo + alias inicial NOME_LIVRE. Pronto para receber chassis em recebimentos.' }
  ]
});
