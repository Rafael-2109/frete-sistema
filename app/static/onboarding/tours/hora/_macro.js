// app/static/onboarding/tours/hora/_macro.js
//
// Tour macro do modulo Lojas HORA.
// Aponta para os triggers VISIVEIS dos dropdowns Bootstrap (nao itens internos).
// Itens dentro de dropdowns colapsados tem dimensoes 0,0 e quebram o Driver.js.
window.OnboardingEngine.register({
  id: 'hora.macro',
  titulo: 'Bem-vindo a Lojas HORA',
  autoStartRoute: '/hora/dashboard',
  steps: [
    {
      element: '#menu-dashboard',
      title: 'Dashboard',
      description: 'Visao geral das suas lojas: motos disponiveis, vendas do mes, pedidos em aberto, divergencias.',
      requirePerm: { modulo: 'dashboard', acao: 'ver' }
    },
    {
      element: '#menu-trigger-cadastros',
      title: 'Cadastros',
      description: 'Lojas, modelos de motos, tabelas de preco, usuarios e permissoes. Tudo que e configuracao base do sistema.',
      requirePerm: { modulo: 'modelos', acao: 'ver' }
    },
    {
      element: '#menu-trigger-movimentacao',
      title: 'Movimentacao (operacao do dia)',
      description: 'Aqui voce acessa <strong>Pedidos, NFs, Recebimentos, Vendas, Transferencias, Estoque e Pecas</strong>. E o menu mais usado no dia a dia.',
      requirePerm: { modulo: 'estoque', acao: 'ver' }
    },
    {
      element: '#menu-trigger-ocorrencias',
      title: 'Ocorrencias',
      description: 'Devolucoes (de cliente ou ao fornecedor), avarias e pecas faltando. Onde voce registra problemas que aparecem na operacao.',
      requirePerm: { modulo: 'avarias', acao: 'ver' }
    },
    {
      element: '#menu-trigger-faturamento',
      title: 'Faturamento (NFe via TagPlus)',
      description: 'Configuracao OAuth do TagPlus, mapeamento de produtos, formas de pagamento e fila de emissoes de NFe.',
      requirePerm: { modulo: 'tagplus', acao: 'ver' }
    },
    {
      element: '#help-button',
      title: 'Precisou de ajuda em alguma tela?',
      description: 'Clique neste botao <strong>Ajuda</strong> em qualquer tela. Se houver tour especifico daquela tela, ele aparece em destaque no topo do menu.'
    }
  ]
});
