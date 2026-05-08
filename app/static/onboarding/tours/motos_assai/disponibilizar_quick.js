window.OnboardingEngine.register({
  id: 'motos_assai.disponibilizar_quick',
  titulo: 'Disponibilizar moto (MONTADA -> DISPONIVEL)',
  autoStartRoute: '/motos-assai/disponibilizar',
  steps: [
    {
      element: '#scan-input',
      title: 'Escaneie o chassi',
      description: 'Faca depois de colar a tag e o manual. <strong>DISPONIVEL = pronta para separar para um pedido.</strong>'
    },
    {
      element: '#btn-disponibilizar',
      title: 'Confirmar disponibilizacao',
      description: 'Emite evento DISPONIVEL. So funciona se o chassi esta MONTADA ou REVERTIDA_PARA_MONTADA.'
    },
    {
      element: '#btn-reverter',
      title: 'Reverter (se errou)',
      description: 'Volta DISPONIVEL -> REVERTIDA_PARA_MONTADA. <strong>Motivo obrigatorio (>=3 caracteres).</strong>'
    }
  ]
});
