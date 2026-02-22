-- Fix: nf_devolucao_linha — CAIXA → UNIDADE (validação por preço)
-- 26 linhas onde qtd_por_caixa=1 mas preço indica unidade individual.
-- Executar via Render Shell após verificação.

-- Verificar estado atual ANTES
SELECT id, codigo_produto_interno, unidade_medida, quantidade,
       quantidade_convertida, qtd_por_caixa, metodo_resolucao, peso_bruto
FROM nf_devolucao_linha
WHERE id IN (8267,8274,8275,8276,8277,8278,8281,8284,8286,8290,8291,8292,
             8296,8297,8298,8299,8300,8301,8302,8303,8304,8305,8306,8307,8308,8311)
  AND qtd_por_caixa = 1
ORDER BY id;

-- Aplicar correções (idempotente: WHERE qtd_por_caixa = 1)
-- Fórmula: qtd_conv = qtd / N, peso = qtd_conv * peso_prod

UPDATE nf_devolucao_linha SET qtd_por_caixa = 6, quantidade_convertida = 0.333, peso_bruto = 7.00, metodo_resolucao = 'DEPARA+PRECO', atualizado_em = NOW() WHERE id = 8267 AND qtd_por_caixa = 1;
UPDATE nf_devolucao_linha SET qtd_por_caixa = 6, quantidade_convertida = 50.000, peso_bruto = 510.00, metodo_resolucao = 'DEPARA_GRUPO+PRECO', atualizado_em = NOW() WHERE id = 8274 AND qtd_por_caixa = 1;
UPDATE nf_devolucao_linha SET qtd_por_caixa = 6, quantidade_convertida = 3.000, peso_bruto = 30.60, metodo_resolucao = 'DEPARA_GRUPO+PRECO', atualizado_em = NOW() WHERE id = 8275 AND qtd_por_caixa = 1;
UPDATE nf_devolucao_linha SET qtd_por_caixa = 6, quantidade_convertida = 32.000, peso_bruto = 672.00, metodo_resolucao = 'DEPARA_GRUPO+PRECO', atualizado_em = NOW() WHERE id = 8276 AND qtd_por_caixa = 1;
UPDATE nf_devolucao_linha SET qtd_por_caixa = 6, quantidade_convertida = 7.000, peso_bruto = 71.40, metodo_resolucao = 'DEPARA_GRUPO+PRECO', atualizado_em = NOW() WHERE id = 8277 AND qtd_por_caixa = 1;
UPDATE nf_devolucao_linha SET qtd_por_caixa = 12, quantidade_convertida = 80.000, peso_bruto = 624.00, metodo_resolucao = 'DEPARA_GRUPO+PRECO', atualizado_em = NOW() WHERE id = 8278 AND qtd_por_caixa = 1;
UPDATE nf_devolucao_linha SET qtd_por_caixa = 6, quantidade_convertida = 2.667, peso_bruto = 35.74, metodo_resolucao = 'DEPARA_GRUPO+PRECO', atualizado_em = NOW() WHERE id = 8281 AND qtd_por_caixa = 1;
UPDATE nf_devolucao_linha SET qtd_por_caixa = 6, quantidade_convertida = 0.500, peso_bruto = 5.10, metodo_resolucao = 'DEPARA_GRUPO+PRECO', atualizado_em = NOW() WHERE id = 8284 AND qtd_por_caixa = 1;
UPDATE nf_devolucao_linha SET qtd_por_caixa = 6, quantidade_convertida = 1.000, peso_bruto = 21.00, metodo_resolucao = 'DEPARA+PRECO', atualizado_em = NOW() WHERE id = 8286 AND qtd_por_caixa = 1;
UPDATE nf_devolucao_linha SET qtd_por_caixa = 6, quantidade_convertida = 0.333, peso_bruto = 7.00, metodo_resolucao = 'DEPARA+PRECO', atualizado_em = NOW() WHERE id = 8290 AND qtd_por_caixa = 1;
UPDATE nf_devolucao_linha SET qtd_por_caixa = 6, quantidade_convertida = 0.667, peso_bruto = 14.01, metodo_resolucao = 'DEPARA+PRECO', atualizado_em = NOW() WHERE id = 8291 AND qtd_por_caixa = 1;
UPDATE nf_devolucao_linha SET qtd_por_caixa = 30, quantidade_convertida = 0.867, peso_bruto = 5.09, metodo_resolucao = 'DEPARA_GRUPO+PRECO', atualizado_em = NOW() WHERE id = 8292 AND qtd_por_caixa = 1;
UPDATE nf_devolucao_linha SET qtd_por_caixa = 36, quantidade_convertida = 3.000, peso_bruto = 15.69, metodo_resolucao = 'DEPARA_GRUPO+PRECO', atualizado_em = NOW() WHERE id = 8296 AND qtd_por_caixa = 1;
UPDATE nf_devolucao_linha SET qtd_por_caixa = 6, quantidade_convertida = 1.000, peso_bruto = 13.40, metodo_resolucao = 'DEPARA_GRUPO+PRECO', atualizado_em = NOW() WHERE id = 8297 AND qtd_por_caixa = 1;
UPDATE nf_devolucao_linha SET qtd_por_caixa = 12, quantidade_convertida = 1.000, peso_bruto = 7.80, metodo_resolucao = 'DEPARA_GRUPO+PRECO', atualizado_em = NOW() WHERE id = 8298 AND qtd_por_caixa = 1;
UPDATE nf_devolucao_linha SET qtd_por_caixa = 18, quantidade_convertida = 1.000, peso_bruto = 5.46, metodo_resolucao = 'DEPARA_GRUPO+PRECO', atualizado_em = NOW() WHERE id = 8299 AND qtd_por_caixa = 1;
UPDATE nf_devolucao_linha SET qtd_por_caixa = 30, quantidade_convertida = 2.000, peso_bruto = 11.14, metodo_resolucao = 'DEPARA_GRUPO+PRECO', atualizado_em = NOW() WHERE id = 8300 AND qtd_por_caixa = 1;
UPDATE nf_devolucao_linha SET qtd_por_caixa = 6, quantidade_convertida = 1.667, peso_bruto = 35.01, metodo_resolucao = 'DEPARA_GRUPO+PRECO', atualizado_em = NOW() WHERE id = 8301 AND qtd_por_caixa = 1;
UPDATE nf_devolucao_linha SET qtd_por_caixa = 6, quantidade_convertida = 0.167, peso_bruto = 3.51, metodo_resolucao = 'DEPARA_GRUPO+PRECO', atualizado_em = NOW() WHERE id = 8302 AND qtd_por_caixa = 1;
UPDATE nf_devolucao_linha SET qtd_por_caixa = 18, quantidade_convertida = 3.000, peso_bruto = 16.38, metodo_resolucao = 'DEPARA_GRUPO+PRECO', atualizado_em = NOW() WHERE id = 8303 AND qtd_por_caixa = 1;
UPDATE nf_devolucao_linha SET qtd_por_caixa = 18, quantidade_convertida = 4.611, peso_bruto = 27.67, metodo_resolucao = 'DEPARA_GRUPO+PRECO', atualizado_em = NOW() WHERE id = 8304 AND qtd_por_caixa = 1;
UPDATE nf_devolucao_linha SET qtd_por_caixa = 18, quantidade_convertida = 3.000, peso_bruto = 18.00, metodo_resolucao = 'DEPARA_GRUPO+PRECO', atualizado_em = NOW() WHERE id = 8305 AND qtd_por_caixa = 1;
UPDATE nf_devolucao_linha SET qtd_por_caixa = 12, quantidade_convertida = 1.000, peso_bruto = 2.68, metodo_resolucao = 'DEPARA_GRUPO+PRECO', atualizado_em = NOW() WHERE id = 8306 AND qtd_por_caixa = 1;
UPDATE nf_devolucao_linha SET qtd_por_caixa = 6, quantidade_convertida = 1.167, peso_bruto = 24.51, metodo_resolucao = 'DEPARA_GRUPO+PRECO', atualizado_em = NOW() WHERE id = 8307 AND qtd_por_caixa = 1;
UPDATE nf_devolucao_linha SET qtd_por_caixa = 6, quantidade_convertida = 5.833, peso_bruto = 122.49, metodo_resolucao = 'DEPARA_GRUPO+PRECO', atualizado_em = NOW() WHERE id = 8308 AND qtd_por_caixa = 1;
UPDATE nf_devolucao_linha SET qtd_por_caixa = 30, quantidade_convertida = 1.200, peso_bruto = 6.68, metodo_resolucao = 'DEPARA_GRUPO+PRECO', atualizado_em = NOW() WHERE id = 8311 AND qtd_por_caixa = 1;

-- Verificar estado APÓS
SELECT id, codigo_produto_interno, unidade_medida, quantidade,
       quantidade_convertida, qtd_por_caixa, metodo_resolucao, peso_bruto
FROM nf_devolucao_linha
WHERE id IN (8267,8274,8275,8276,8277,8278,8281,8284,8286,8290,8291,8292,
             8296,8297,8298,8299,8300,8301,8302,8303,8304,8305,8306,8307,8308,8311)
ORDER BY id;
