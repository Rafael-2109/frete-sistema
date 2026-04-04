-- Migration: Popular dimensoes internas do bau para todos os veiculos cadastrados.
-- Valores em centimetros (cm), pesquisados via fichas tecnicas e fontes do mercado.
-- Uso: Executar no Render Shell (Postgres read-write)
--
-- Fontes:
--   FIORINO: Ficha tecnica Fiat Fiorino Furgao MY24 (media.stellantis.com)
--   VAN/HR: Hyundai HR bau padrao (Superbid/Truckvan, 3.00m x 1.80m x 2.00m)
--   MASTER: Renault Master Grand Furgao L2H2 (dimensoes tipicas L2H2)
--   IVECO: Iveco Daily chassi-cabine + bau (Superbid/BasWorld)
--   3/4: MB Accelo 1016 / bau padrao 4t (VendaTruck, GuiaLog)
--   TOCO: Bau padrao 6t (GuiaLog, Facchini, Santana Baus)
--   TRUCK: Bau padrao truck 6x2 (Randon 8.55m, multiplas fontes)
--   CARRETA: Semi-reboque padrao (GuiaLog, 14.94m)
--   BI-TRUCK: Bau padrao bi-truck 8x2 (Mathias Implementos, Randon)
--   CABOTAGEM: Container 40 pes dry ISO standard

-- Idempotente: so atualiza se o campo estiver NULL (nao sobrescreve valores manuais)

UPDATE veiculos SET
    comprimento_bau = 188.7,
    largura_bau = 108.9,
    altura_bau = 133.9
WHERE id = 1 AND nome = 'FIORINO' AND comprimento_bau IS NULL;

UPDATE veiculos SET
    comprimento_bau = 300.0,
    largura_bau = 180.0,
    altura_bau = 200.0
WHERE id = 2 AND nome = 'VAN/HR' AND comprimento_bau IS NULL;

UPDATE veiculos SET
    comprimento_bau = 373.0,
    largura_bau = 176.5,
    altura_bau = 185.6
WHERE id = 3 AND nome = 'MASTER' AND comprimento_bau IS NULL;

UPDATE veiculos SET
    comprimento_bau = 480.0,
    largura_bau = 215.0,
    altura_bau = 210.0
WHERE id = 4 AND nome = 'IVECO' AND comprimento_bau IS NULL;

UPDATE veiculos SET
    comprimento_bau = 510.0,
    largura_bau = 215.0,
    altura_bau = 220.0
WHERE id = 5 AND nome = '3/4' AND comprimento_bau IS NULL;

UPDATE veiculos SET
    comprimento_bau = 700.0,
    largura_bau = 244.0,
    altura_bau = 260.0
WHERE id = 6 AND nome = 'TOCO' AND comprimento_bau IS NULL;

UPDATE veiculos SET
    comprimento_bau = 850.0,
    largura_bau = 244.0,
    altura_bau = 260.0
WHERE id = 7 AND nome = 'TRUCK' AND comprimento_bau IS NULL;

UPDATE veiculos SET
    comprimento_bau = 1494.0,
    largura_bau = 248.0,
    altura_bau = 273.0
WHERE id = 8 AND nome = 'CARRETA' AND comprimento_bau IS NULL;

UPDATE veiculos SET
    comprimento_bau = 950.0,
    largura_bau = 250.0,
    altura_bau = 265.0
WHERE id = 9 AND nome = 'BI-TRUCK' AND comprimento_bau IS NULL;

UPDATE veiculos SET
    comprimento_bau = 1203.2,
    largura_bau = 235.0,
    altura_bau = 239.2
WHERE id = 10 AND nome = 'CABOTAGEM' AND comprimento_bau IS NULL;
