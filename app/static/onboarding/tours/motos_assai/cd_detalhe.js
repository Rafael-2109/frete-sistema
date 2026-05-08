window.OnboardingEngine.register({
  id: 'motos_assai.cd_detalhe',
  titulo: 'Centro de Distribuicao',
  autoStartRoute: '/motos-assai/cd',
  steps: [
    { element: '#info-cd', title: 'Dados do CD', description: 'Endereco, capacidade, equipe responsavel. Singleton — so existe 1 CD.' },
    { element: '#secao-pipeline-cd', title: 'Pipeline em tempo real', description: 'Quantidades atuais em cada estagio: ESTOQUE, MONTADA, DISPONIVEL, SEPARADA.' }
  ]
});
