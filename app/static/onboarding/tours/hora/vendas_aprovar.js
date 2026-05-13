// Tour gated em `vendas/editar` (era `aprovar` ate 2026-05-13).
// Desde a mudanca de fluxo no mesmo dia, vendedor padrao (perm 'editar')
// passou a CONFIRMAR pedidos via #btn-confirmar — antes era exclusivo de
// gerente (perm 'aprovar'). Tour cobre as 5 acoes visiveis ao vendedor;
// steps que apontam para botoes ocultos para o usuario atual (ex.: emitir
// NFe so aparece com perm 'criar') sao automaticamente pulados pelo Engine.
window.OnboardingEngine.register({
  id: 'hora.vendas_aprovar',
  titulo: 'Confirmar venda e emitir NFe',
  requirePerm: { modulo: 'vendas', acao: 'editar' },
  autoStartRoute: '/hora/vendas/*',
  steps: [
    { element: '#timeline-status',       title: 'Status do pedido',    description: 'Estados: COTACAO → CONFIRMADO → FATURADO → CANCELADO. Cada um tem campos editaveis diferentes.' },
    { element: '#btn-confirmar',         title: 'Confirmar pedido',    description: 'Vira CONFIRMADO. Trava CPF/nome (vao pra NFe). Permite editar contato, endereco, observacao. Apos confirmar, apenas gerente reabre.' },
    { element: '#btn-emitir-nfe',        title: 'Emitir NFe via TagPlus', description: 'Enfileira job no Redis. Webhook do TagPlus avisa quando aprovou na SEFAZ → vira FATURADO.' },
    { element: '#secao-historico',       title: 'Auditoria completa',  description: '14 acoes registradas (CRIOU, CONFIRMOU, EMITIU_NFE, CANCELOU...). Cada uma com usuario e timestamp.' },
    { element: '#btn-cancelar-pedido',   title: 'Cancelar pedido',     description: 'COTACAO/CONFIRMADO: cancela direto. FATURADO: precisa cancelar NFe na SEFAZ antes (botao na secao NFe).' }
  ]
});
