window.OnboardingEngine.register({
  id: 'hora.venda_manual_nova',
  titulo: 'Criar pedido de venda',
  requirePerm: { modulo: 'vendas', acao: 'criar' },
  autoStartRoute: '/hora/tagplus/pedido-venda/novo',
  steps: [
    {
      element: '#campo-cliente-cpfcnpj',
      title: 'CPF ou CNPJ do cliente',
      description: 'Pode ser PF ou PJ. <strong>Toda NFe sai como consumidor final</strong>, nao importa o tipo.'
    },
    {
      element: '#campo-cliente-nome',
      title: 'Nome do cliente',
      description: 'Vai no destinatario da NFe. Digite igual ao documento.'
    },
    {
      element: '#secao-itens',
      title: 'Itens do pedido',
      description: 'Adicione motos (por chassi) e/ou pecas (por codigo). Pelo menos 1 item obrigatorio.'
    },
    {
      element: '#btn-add-moto',
      title: 'Adicionar moto',
      description: 'Escolha modelo + chassi especifico. <strong>Lock pessimista:</strong> ninguem mais pode reservar esse chassi ate cancelar ou faturar.'
    },
    {
      element: '#campo-forma-pagamento',
      title: 'Forma de pagamento',
      description: 'PIX, cartao, dinheiro, misto. Define se entra preco a vista ou a prazo do modelo.'
    },
    {
      element: '#btn-salvar-cotacao',
      title: 'Salvar como COTACAO',
      description: 'Status COTACAO permite editar tudo. Quando confirmar, vira CONFIRMADO (so edita observacao). NFe emite quando o gerente confirmar.'
    }
  ]
});
