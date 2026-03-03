-- Fix nome_emitente incorreto em 5 NFs CarVia (CNPJ 33119545000413)
-- Bug: parser DANFE PDF parseava "Est D, 345" (endereco) em vez do nome real
-- Idempotente: so atualiza registros com nome errado

-- Diagnostico ANTES
SELECT id, numero_nf, nome_emitente
FROM carvia_nfs
WHERE cnpj_emitente = '33119545000413'
  AND nome_emitente = 'Est D, 345';

-- Fix
UPDATE carvia_nfs
SET nome_emitente = 'NOTCO BRASIL DISTRIBUICAO E COMERCI PRODUTOS ALIMENTICIOS LT'
WHERE cnpj_emitente = '33119545000413'
  AND nome_emitente = 'Est D, 345';

-- Diagnostico DEPOIS
SELECT id, numero_nf, nome_emitente
FROM carvia_nfs
WHERE cnpj_emitente = '33119545000413';
