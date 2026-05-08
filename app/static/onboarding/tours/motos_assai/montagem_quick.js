window.OnboardingEngine.register({
  id: 'motos_assai.montagem_quick',
  titulo: 'Montar moto (ESTOQUE -> MONTADA)',
  autoStartRoute: '/motos-assai/montagem',
  steps: [
    {
      element: '#scan-input',
      title: 'Aponte o QR ou digite o chassi',
      description: 'Tela de chao de fabrica. Suporta leitor USB (Enter dispara), camera mobile e digitacao.'
    },
    {
      element: '#btn-marcar-montada',
      title: 'Marcar como MONTADA',
      description: 'Caminho feliz: chassi montado e OK -> vira MONTADA, proxima parada e DISPONIVEL.'
    },
    {
      element: '#btn-marcar-pendente',
      title: 'Marcar como PENDENTE',
      description: 'Defeito de peca? Marca PENDENTE com descricao. Resolve depois com PENDENCIA_RESOLVIDA -> MONTADA.'
    },
    {
      element: '#historico-3-ultimas',
      title: 'Ultimas 3 acoes',
      description: 'Vista rapida do que voce acabou de fazer. Util para ver se errou e desfazer.'
    }
  ]
});
