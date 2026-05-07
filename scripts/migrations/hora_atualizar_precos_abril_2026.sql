-- =============================================================================
-- Atualizacao da TABELA DE PRECOS Lojas HORA (ABRIL/2026)
-- Fonte: WhatsApp Image 2026-05-06 at 20.16.40.jpeg ("MOTO CHEFE - TABELA DE PRECOS")
-- Data: 2026-05-07
-- Tabela alvo: hora_modelo (HoraModelo) — campos preco_a_vista, preco_a_prazo, potencia_motor
-- =============================================================================
--
-- COMO USAR:
--   1) Rodar primeiro o SELECT "ANTES" para ver estado atual.
--   2) Rodar BEGIN; UPDATE...; (sem COMMIT ainda).
--   3) Rodar SELECT "DEPOIS" para conferir.
--   4) Se ok, COMMIT;  Se nao, ROLLBACK;
--
-- MAPEAMENTO IMAGEM -> hora_modelo (cruzado com hora_modelo_alias):
--   BIG TRI         -> id=17 BIG TRI            [match direto canonico]
--   BOB             -> id=9  BOB                [match direto canonico]
--   GIGA            -> id=10 GIGA               [match direto canonico]
--   JET             -> id=6  JET                [match direto canonico]
--   JET MAX         -> id=13 JET MAX            [match direto canonico]
--   JOY SUPER       -> id=25 JOY SUPER          [match direto canonico]
--   MIA             -> id=28 MIA                [match direto canonico]
--   MIA TRI         -> id=26 MIA TRI            [match direto canonico]
--   RET             -> id=2  RET                [match direto canonico]
--   ROMA            -> id=11 ROMA               [match direto canonico]
--   S8 (MC-20)      -> id=29 S8-12              [ASSUNCAO: alias TAGPLUS_CODIGO 'MT-S8-M20' bate "MC-20"]
--   SOFIA           -> id=27 SOFIA              [match direto canonico]
--   SOMA            -> id=24 SOMA               [match direto canonico]
--   STYLE (VTB3)    -> id=22 VTB 3              [ASSUNCAO: "VTB3" da imagem == "VTB 3" canonico]
--   VED             -> id=14 VED                [match direto canonico]
--   X11             -> id=15 X11-12             [ASSUNCAO: unico canonico iniciando por X11; alias TP 'MT-X11 12']
--   X12             -> id=23 X12-10             [ASSUNCAO: unico canonico iniciando por X12; alias TP 'MT-X12 10']
--   X15             -> id=4  X15                [match direto canonico]
--
-- NAO MODIFICADOS (canonicos existentes que nao constam na imagem):
--   id=53 DESCONHECIDO   (sentinela)
--   id=30 PITICA 500
--   id=20 S8-MINI
--   id=21 VTB 4
--   id=16 JETMAX (ja inativo, ativo=false)
--
-- OBS: A tabela "PROMOCOES DO MES" (JET, RET, SOMA, X12, GIGA) tem precos
-- IDENTICOS aos da tabela normal, portanto nao gera UPDATEs distintos.
--
-- INVARIANTE: Esta operacao mexe em hora_modelo (UPDATE permitido por design
-- — campos preco_a_*) e NAO em hora_moto (insert-once). Nao viola Invariante 4.
-- =============================================================================


-- ======================== SELECT "ANTES" ========================
SELECT id, nome_modelo, potencia_motor, preco_a_vista, preco_a_prazo, atualizado_em
FROM hora_modelo
WHERE id IN (17, 9, 10, 6, 13, 25, 28, 26, 2, 11, 29, 27, 24, 22, 14, 15, 23, 4)
ORDER BY nome_modelo;


-- ======================== UPDATES ========================
BEGIN;

-- BIG TRI / 1000W / R$ 12.390,00 / R$ 12.990,00
UPDATE hora_modelo SET potencia_motor = '1000W', preco_a_vista = 12390.00, preco_a_prazo = 12990.00,
    atualizado_em = (NOW() AT TIME ZONE 'America/Sao_Paulo')
WHERE id = 17;

-- BOB / 1000W / R$ 7.900,00 / R$ 8.290,00
UPDATE hora_modelo SET potencia_motor = '1000W', preco_a_vista = 7900.00, preco_a_prazo = 8290.00,
    atualizado_em = (NOW() AT TIME ZONE 'America/Sao_Paulo')
WHERE id = 9;

-- GIGA / 1000W / R$ 9.990,00 / R$ 10.990,00
UPDATE hora_modelo SET potencia_motor = '1000W', preco_a_vista = 9990.00, preco_a_prazo = 10990.00,
    atualizado_em = (NOW() AT TIME ZONE 'America/Sao_Paulo')
WHERE id = 10;

-- JET / 1000W / R$ 9.990,00 / R$ 10.990,00
UPDATE hora_modelo SET potencia_motor = '1000W', preco_a_vista = 9990.00, preco_a_prazo = 10990.00,
    atualizado_em = (NOW() AT TIME ZONE 'America/Sao_Paulo')
WHERE id = 6;

-- JET MAX / 1000W / R$ 11.990,00 / R$ 12.990,00
UPDATE hora_modelo SET potencia_motor = '1000W', preco_a_vista = 11990.00, preco_a_prazo = 12990.00,
    atualizado_em = (NOW() AT TIME ZONE 'America/Sao_Paulo')
WHERE id = 13;

-- JOY SUPER / 800W / R$ 6.990,00 / R$ 7.490,00
UPDATE hora_modelo SET potencia_motor = '800W', preco_a_vista = 6990.00, preco_a_prazo = 7490.00,
    atualizado_em = (NOW() AT TIME ZONE 'America/Sao_Paulo')
WHERE id = 25;

-- MIA / 1000W / R$ 9.490,00 / R$ 9.990,00
UPDATE hora_modelo SET potencia_motor = '1000W', preco_a_vista = 9490.00, preco_a_prazo = 9990.00,
    atualizado_em = (NOW() AT TIME ZONE 'America/Sao_Paulo')
WHERE id = 28;

-- MIA TRI / 800W / R$ 11.890,00 / R$ 12.490,00
UPDATE hora_modelo SET potencia_motor = '800W', preco_a_vista = 11890.00, preco_a_prazo = 12490.00,
    atualizado_em = (NOW() AT TIME ZONE 'America/Sao_Paulo')
WHERE id = 26;

-- RET / 1000W / R$ 8.490,00 / R$ 8.990,00
UPDATE hora_modelo SET potencia_motor = '1000W', preco_a_vista = 8490.00, preco_a_prazo = 8990.00,
    atualizado_em = (NOW() AT TIME ZONE 'America/Sao_Paulo')
WHERE id = 2;

-- ROMA / 3000W / R$ 14.290,00 / R$ 14.990,00
UPDATE hora_modelo SET potencia_motor = '3000W', preco_a_vista = 14290.00, preco_a_prazo = 14990.00,
    atualizado_em = (NOW() AT TIME ZONE 'America/Sao_Paulo')
WHERE id = 11;

-- S8 (MC-20) / 3000W / R$ 11.990,00 / R$ 12.590,00  -- canonico S8-12
UPDATE hora_modelo SET potencia_motor = '3000W', preco_a_vista = 11990.00, preco_a_prazo = 12590.00,
    atualizado_em = (NOW() AT TIME ZONE 'America/Sao_Paulo')
WHERE id = 29;

-- SOFIA / 1000W / R$ 9.900,00 / R$ 10.390,00
UPDATE hora_modelo SET potencia_motor = '1000W', preco_a_vista = 9900.00, preco_a_prazo = 10390.00,
    atualizado_em = (NOW() AT TIME ZONE 'America/Sao_Paulo')
WHERE id = 27;

-- SOMA / 1000W / R$ 8.490,00 / R$ 8.990,00
UPDATE hora_modelo SET potencia_motor = '1000W', preco_a_vista = 8490.00, preco_a_prazo = 8990.00,
    atualizado_em = (NOW() AT TIME ZONE 'America/Sao_Paulo')
WHERE id = 24;

-- STYLE (VTB3) / 750W / R$ 9.990,00 / R$ 10.490,00  -- canonico VTB 3
UPDATE hora_modelo SET potencia_motor = '750W', preco_a_vista = 9990.00, preco_a_prazo = 10490.00,
    atualizado_em = (NOW() AT TIME ZONE 'America/Sao_Paulo')
WHERE id = 22;

-- VED / 1000W / R$ 14.490,00 / R$ 15.290,00
UPDATE hora_modelo SET potencia_motor = '1000W', preco_a_vista = 14490.00, preco_a_prazo = 15290.00,
    atualizado_em = (NOW() AT TIME ZONE 'America/Sao_Paulo')
WHERE id = 14;

-- X11 / 3000W / R$ 11.390,00 / R$ 11.990,00  -- canonico X11-12
UPDATE hora_modelo SET potencia_motor = '3000W', preco_a_vista = 11390.00, preco_a_prazo = 11990.00,
    atualizado_em = (NOW() AT TIME ZONE 'America/Sao_Paulo')
WHERE id = 15;

-- X12 / 1000W / R$ 9.990,00 / R$ 10.990,00  -- canonico X12-10
UPDATE hora_modelo SET potencia_motor = '1000W', preco_a_vista = 9990.00, preco_a_prazo = 10990.00,
    atualizado_em = (NOW() AT TIME ZONE 'America/Sao_Paulo')
WHERE id = 23;

-- X15 / 3000W / R$ 14.490,00 / R$ 15.290,00
UPDATE hora_modelo SET potencia_motor = '3000W', preco_a_vista = 14490.00, preco_a_prazo = 15290.00,
    atualizado_em = (NOW() AT TIME ZONE 'America/Sao_Paulo')
WHERE id = 4;


-- ======================== SELECT "DEPOIS" (dentro da transacao) ========================
SELECT id, nome_modelo, potencia_motor, preco_a_vista, preco_a_prazo, atualizado_em
FROM hora_modelo
WHERE id IN (17, 9, 10, 6, 13, 25, 28, 26, 2, 11, 29, 27, 24, 22, 14, 15, 23, 4)
ORDER BY nome_modelo;


-- =============================================================================
-- Conferir os 18 registros acima:
--   - Se OK ->  COMMIT;
--   - Se NOK -> ROLLBACK;
-- =============================================================================
-- COMMIT;
-- ROLLBACK;
