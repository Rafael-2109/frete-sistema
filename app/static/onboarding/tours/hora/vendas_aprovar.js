window.OnboardingEngine.register({
  id: 'hora.vendas_aprovar',
  titulo: 'Aprovar venda e emitir NFe',
  requirePerm: { modulo: 'vendas', acao: 'aprovar' },
  autoStartRoute: '/hora/vendas/*',
  steps: [
    { element: '#timeline-status',       title: 'Status do pedido',    description: 'Estados: COTACAO → CONFIRMADO → FATURADO → CANCELADO. Cada um tem campos editaveis diferentes.' },
    { element: '#btn-confirmar',         title: 'Confirmar pedido',    description: 'Vira CONFIRMADO. Trava CPF/nome (vao pra NFe). Permite editar contato, endereco, observacao.' },
    { element: '#btn-emitir-nfe',        title: 'Emitir NFe via TagPlus', description: 'Enfileira job no Redis. Webhook do TagPlus avisa quando aprovou na SEFAZ → vira FATURADO.' },
    { element: '#secao-historico',       title: 'Auditoria completa',  description: '14 acoes registradas (CRIOU, CONFIRMOU, EMITIU_NFE, CANCELOU...). Cada uma com usuario e timestamp.' },
    { element: '#btn-cancelar-pedido',   title: 'Cancelar pedido',     description: 'COTACAO/CONFIRMADO: cancela direto. FATURADO: precisa cancelar NFe na SEFAZ antes (botao na secao NFe).' }
  ]
});
