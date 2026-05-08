window.OnboardingEngine.register({
  id: 'hora.avaria_nova',
  titulo: 'Registrar avaria',
  requirePerm: { modulo: 'avarias', acao: 'criar' },
  autoStartRoute: '/hora/avarias/nova',
  steps: [
    { element: '#campo-chassi',          title: 'Chassi avariado',         description: 'Pode estar em qualquer status (estoque, vendido, em transito). Avaria nao muda status, so sinaliza.' },
    { element: '#campo-foto',            title: 'Foto obrigatoria',        description: 'Suba no minimo 1 foto da avaria. <strong>Vai pro S3</strong> e fica vinculada a avaria.' },
    { element: '#campo-descricao',       title: 'Descricao (≥3 caracteres)', description: 'Texto curto explicando o problema. Aparece no detalhe e nos relatorios.' },
    { element: '#btn-salvar-avaria',     title: 'Salvar',                  description: 'Cria registro + emite evento AVARIADA. Multiplas avarias por chassi sao permitidas.' }
  ]
});
