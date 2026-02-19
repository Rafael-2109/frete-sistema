-- Migration: Reset transfer_status stale para recebimento_lf
-- Contexto: RecebimentoLf com transfer_status='processando' ha >30min
--           indica job morto por deploy/OOM sem atualizar status.
-- Uso: Executar via Render Shell

-- Verificar ANTES
SELECT id, numero_nf, transfer_status, atualizado_em,
       EXTRACT(EPOCH FROM (NOW() - atualizado_em)) / 60 AS minutos_stale
FROM recebimento_lf
WHERE transfer_status = 'processando'
ORDER BY atualizado_em ASC;

-- Resetar stale (>30min)
UPDATE recebimento_lf
SET transfer_status = 'erro',
    transfer_erro_mensagem = 'Reset automatico: transfer_status stale (processando >30min, job morto por deploy)'
WHERE transfer_status = 'processando'
  AND atualizado_em < NOW() - INTERVAL '30 minutes';

-- Verificar DEPOIS
SELECT id, numero_nf, transfer_status, transfer_erro_mensagem
FROM recebimento_lf
WHERE transfer_status = 'erro'
  AND transfer_erro_mensagem LIKE 'Reset automatico%'
ORDER BY id;
