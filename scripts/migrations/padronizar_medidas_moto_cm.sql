-- Migration: Padronizar medidas de modelos de moto para centimetros (CM)
-- Multiplica comprimento/largura/altura por 100 onde valores estao em metros.
-- Idempotente: WHERE < 10 garante que valores ja em CM nao sao afetados.

UPDATE carvia_modelos_moto
SET comprimento = comprimento * 100,
    largura = largura * 100,
    altura = altura * 100
WHERE comprimento < 10
  AND largura < 10
  AND altura < 10;
