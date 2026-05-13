window.OnboardingEngine.register({
  id: 'motos_assai.carregamento_escanear',
  titulo: 'Escanear chassis no carregamento',
  autoStartRoute: '/motos-assai/carregamento/*',
  steps: [
    {
      element: '#header-carregamento',
      title: 'Pedido + loja + status',
      description: 'Carregamento de pedido X para loja LJ12. Status atual: EM_CARREGAMENTO (escaneando), FINALIZADO (Sep CARREGADA criada/atualizada) ou CANCELADO.'
    },
    {
      element: '#scan-input-card',
      title: 'Escaneie chassi (QR / barcode / digitar)',
      description: 'A1: NAO emite evento aqui — estado muda apenas ao finalizar. S3=c: lock pessimista garante que o mesmo chassi nao entre em 2 carregamentos ativos.'
    },
    {
      element: '#items-table',
      title: 'Items escaneados',
      description: 'Lista dos chassis escaneados neste carregamento. Botao "Remover" funciona apenas durante EM_CARREGAMENTO (apos finalizar, use "Alterar" para reabrir — S6=a).'
    },
    {
      element: '#botoes-acao',
      title: 'Finalizar / Cancelar / Alterar',
      description: 'Finalizar roda 8 fases (sep alvo, sobrescrever chassis, limite, evento CARREGADA, Excel, mirror, divergencia NF, recalcular pedido). Cancelar exige motivo. Alterar reabre carregamento FINALIZADO (regredí Sep CARREGADA->FECHADA).'
    }
  ]
});
