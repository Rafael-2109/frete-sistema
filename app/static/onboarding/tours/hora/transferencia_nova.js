window.OnboardingEngine.register({
  id: 'hora.transferencia_nova',
  titulo: 'Transferir motos entre lojas',
  requirePerm: { modulo: 'transferencias', acao: 'criar' },
  autoStartRoute: '/hora/transferencias/nova',
  steps: [
    {
      element: '#campo-loja-origem',
      title: 'Loja de origem',
      description: 'A loja que esta enviando. Voce so ve lojas onde tem permissao de origem.'
    },
    {
      element: '#campo-loja-destino',
      title: 'Loja de destino',
      description: 'Para onde a moto vai. Nao pode ser igual a origem.'
    },
    {
      element: '#secao-chassis',
      title: 'Selecione os chassis',
      description: 'Marque os chassis disponiveis na loja origem. Cada um vai virar 1 item de transferencia.'
    },
    {
      element: '#btn-emitir',
      title: 'Emitir transferencia',
      description: 'Status vira <strong>EM_TRANSITO</strong>. Loja destino precisa confirmar para virar TRANSFERIDA. Voce pode cancelar enquanto em transito.'
    }
  ]
});
