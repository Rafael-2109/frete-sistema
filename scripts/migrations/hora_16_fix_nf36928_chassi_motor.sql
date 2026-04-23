-- Migration HORA 16: data-fix NF 36928 — inverter chassi <-> motor das 2 motos RET.
--
-- Bug: parser LLM (app/carvia/services/parsers/danfe_pdf_parser.py) inverteu
-- chassi e motor para as 2 motos RET da NF 36928 (chave 33260409089839000112550000000369281387401233).
--
-- Estado ATUAL (errado):
--   item 23 (PRETO): numero_chassi='LM60V1000W2025051000290', motor_texto='172922504731222'
--   item 24 (CINZA): numero_chassi='LM60V1000W2025062100443', motor_texto='172922506731648'
--
-- Estado CORRETO (pos-fix):
--   item 23 (PRETO): numero_chassi='172922504731222',          motor_texto='LM60V1000W2025051000290'
--   item 24 (CINZA): numero_chassi='172922506731648',          motor_texto='LM60V1000W2025062100443'
--
-- Os chassis corretos ('17292...') ja existem em hora_moto (criados pelo pedido 1)
-- e em hora_pedido_item (itens 3 e 8). Basta:
--   1) Mover a FK do hora_nf_entrada_item para o chassi correto
--   2) Preencher numero_motor nas hora_moto corretas
--   3) Remover as 2 hora_moto orfas (com chassi errado = LM60...)
--
-- Pre-condicoes validadas em 2026-04-22:
--   - Nenhuma referencia em hora_moto_evento, hora_recebimento_conferencia,
--     hora_venda_item, hora_avaria, hora_transferencia_item, hora_peca_faltando
--     para os 4 chassis envolvidos. Recebimento fisico ainda nao ocorreu.
--
-- IDEMPOTENTE: guards WHERE impedem re-aplicacao.

BEGIN;

-- 1) Corrigir item 23 da NF 36928 (chassi + motor_texto_original)
UPDATE hora_nf_entrada_item
   SET numero_chassi = '172922504731222',
       numero_motor_texto_original = 'LM60V1000W2025051000290'
 WHERE id = 23
   AND nf_id = 2
   AND numero_chassi = 'LM60V1000W2025051000290';

-- 2) Corrigir item 24 da NF 36928
UPDATE hora_nf_entrada_item
   SET numero_chassi = '172922506731648',
       numero_motor_texto_original = 'LM60V1000W2025062100443'
 WHERE id = 24
   AND nf_id = 2
   AND numero_chassi = 'LM60V1000W2025062100443';

-- 3) Preencher numero_motor nas hora_moto corretas (hoje motor=NULL)
UPDATE hora_moto
   SET numero_motor = 'LM60V1000W2025051000290'
 WHERE numero_chassi = '172922504731222'
   AND numero_motor IS NULL;

UPDATE hora_moto
   SET numero_motor = 'LM60V1000W2025062100443'
 WHERE numero_chassi = '172922506731648'
   AND numero_motor IS NULL;

-- 4) Remover as 2 hora_moto orfas (chassi errado, agora sem referencia)
DELETE FROM hora_moto
 WHERE numero_chassi IN ('LM60V1000W2025051000290', 'LM60V1000W2025062100443')
   AND NOT EXISTS (
     SELECT 1 FROM hora_nf_entrada_item i WHERE i.numero_chassi = hora_moto.numero_chassi
   )
   AND NOT EXISTS (
     SELECT 1 FROM hora_pedido_item p WHERE p.numero_chassi = hora_moto.numero_chassi
   )
   AND NOT EXISTS (
     SELECT 1 FROM hora_moto_evento e WHERE e.numero_chassi = hora_moto.numero_chassi
   );

COMMIT;
