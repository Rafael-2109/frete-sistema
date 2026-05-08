window.OnboardingEngine.register({
  id: 'motos_assai.faturamento',
  titulo: 'Faturamento Q.P.A.',
  adminOnly: true,
  autoStartRoute: '/motos-assai/faturamento',
  steps: [
    { element: '#tabela-separacoes-fechadas', title: 'Separacoes prontas',  description: 'Aparecem aqui quando todos os chassis foram separados. Proximo passo: gerar Excel Q.P.A.' },
    { element: '#btn-gerar-excel',       title: 'Gerar Excel Q.P.A.',         description: '2 abas (PEDIDO + BASE LOJAS). Persiste em S3 + atualiza solicitacao_excel_s3_key. Espelha 285.xlsx.' },
    { element: '#btn-upload-nf',         title: 'Subir NF Q.P.A.',            description: 'Apos Sendas emitir a NF, suba aqui. Parser DANFE adapter (CarVia) faz match BATEU/DIVERGENTE com tolerancia 1%.' },
    { element: '#secao-resultado-match', title: 'Resultado do match',         description: 'BATEU = separacao vira FATURADA, chassis emitem evento FATURADA. DIVERGENTE = revisar manualmente.' }
  ]
});
