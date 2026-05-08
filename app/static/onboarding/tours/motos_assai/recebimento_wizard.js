window.OnboardingEngine.register({
  id: 'motos_assai.recebimento_wizard',
  titulo: 'Conferir recibo da Motochefe',
  autoStartRoute: '/motos-assai/recibos/*/conferir',
  steps: [
    {
      element: '#recibo-header',
      title: 'Recibo em conferencia',
      description: 'O numero do recibo vem do PDF/Excel que o admin subiu. Aqui voce confere chassi por chassi.'
    },
    {
      element: '#progress-steps',
      title: 'Wizard em 4 passos',
      description: 'Recibo -> Escanear -> Confirmar -> Finalizar. Voce esta no passo 2 (Escanear).'
    },
    {
      element: '#scan-area',
      title: 'Aponte o QR do chassi',
      description: 'Use a camera traseira do celular. <strong>Se a camera falhar</strong> ou QR estiver danificado, use a digitacao manual logo abaixo.'
    },
    {
      element: '#chassi-input',
      title: 'Digitacao manual (fallback)',
      description: 'Operadores rapidos digitam direto sem usar camera. <strong>Pressione Enter</strong> para validar.'
    },
    {
      element: '#btn-validar',
      title: 'Validar antes de salvar',
      description: 'Checa: chassi pertence a este recibo? Ja foi conferido? Modelo bate com o regex do cadastro?'
    },
    {
      element: '#lista-conferidos',
      title: 'Acompanhe o progresso',
      description: 'Quando todos os chassis estiverem conferidos, o botao <strong>Finalizar</strong> aparece. Faltantes viram evento MOTO_FALTANDO.'
    }
  ]
});
