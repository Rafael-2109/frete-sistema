window.OnboardingEngine.register({
  id: 'motos_assai.separacao_chassi',
  titulo: 'Separar pedido (chassis para o cliente)',
  autoStartRoute: '/motos-assai/pedidos/*/separar/*',
  steps: [
    {
      element: '#header-pedido-loja',
      title: 'Pedido + loja Sendas',
      description: 'Voce esta separando o pedido X para a loja LJ12 do Assai.'
    },
    {
      element: '#barras-saldo',
      title: 'Saldo por modelo',
      description: 'Cada barra = 1 modelo do pedido. Faltam X chassis pra completar. Fungivel: qualquer chassi DISPONIVEL do mesmo modelo serve.'
    },
    {
      element: '#scan-input',
      title: 'Escaneie o chassi DISPONIVEL',
      description: 'Race condition: se 2 operadores escanearem o mesmo chassi, o segundo recebe 409 e tenta de novo.'
    },
    {
      element: '#btn-finalizar-separacao',
      title: 'Finalizar quando completo',
      description: 'Aparece quando saldo = 0. Move a separacao para FECHADA e libera para gerar Excel Q.P.A.'
    }
  ]
});
