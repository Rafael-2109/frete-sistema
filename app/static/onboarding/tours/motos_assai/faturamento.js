window.OnboardingEngine.register({
  id: 'motos_assai.faturamento',
  titulo: 'Faturamento Q.P.A.',
  adminOnly: true,
  autoStartRoute: '/motos-assai/faturamento',
  steps: [
    { element: '#tabela-separacoes-prontas', title: 'Separacoes prontas',  description: 'Aparecem aqui quando todos os chassis foram separados. Proximo passo: gerar Excel Q.P.A. via botao Excel (abre a tela da Separacao).' },
    { element: '#btn-gerar-excel',       title: 'Gerar Excel Q.P.A.',         description: 'Botao "Excel" abre a tela da Separacao, de onde o operador gera/baixa o Excel Q.P.A. (2 abas: PEDIDO + BASE LOJAS).' },
    { element: '#btn-upload-nf',         title: 'Subir NF Q.P.A.',            description: 'Apos Sendas emitir a NF, suba o PDF aqui. Parser DANFE adapter (CarVia) faz match BATEU/DIVERGENTE com tolerancia 1%.' },
    { element: '#tabela-separacoes-faturadas', title: 'Faturadas',          description: 'Separacoes com NF Q.P.A. importada e match BATEU. Botao NF abre o PDF original (S3). Badge CCe abre o PDF da Carta de Correcao.' }
  ]
});
