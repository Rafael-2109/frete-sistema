-- Migration: Adicionar campos de subcategorias em cadastro_palletizacao
-- Data: 2025-08-07
-- Descrição: Adiciona campos para filtros de embalagem, matéria-prima e categorias

-- Adicionar novos campos
ALTER TABLE cadastro_palletizacao 
ADD COLUMN IF NOT EXISTS tipo_embalagem VARCHAR(50),
ADD COLUMN IF NOT EXISTS tipo_materia_prima VARCHAR(50),
ADD COLUMN IF NOT EXISTS categoria_produto VARCHAR(50),
ADD COLUMN IF NOT EXISTS subcategoria VARCHAR(50),
ADD COLUMN IF NOT EXISTS linha_producao VARCHAR(50);

-- Criar índices para melhor performance nos filtros
CREATE INDEX IF NOT EXISTS idx_cadastro_pallet_embalagem ON cadastro_palletizacao(tipo_embalagem);
CREATE INDEX IF NOT EXISTS idx_cadastro_pallet_materia ON cadastro_palletizacao(tipo_materia_prima);
CREATE INDEX IF NOT EXISTS idx_cadastro_pallet_categoria ON cadastro_palletizacao(categoria_produto);
CREATE INDEX IF NOT EXISTS idx_cadastro_pallet_linha ON cadastro_palletizacao(linha_producao);

-- Comentários explicativos
COMMENT ON COLUMN cadastro_palletizacao.categoria_produto IS 'Categoria: PALMITO, CONSERVAS, MOLHOS, ÓLEOS';
COMMENT ON COLUMN cadastro_palletizacao.tipo_materia_prima IS 'Matéria-prima: AZ VSC, AZ VF, CEBOLINHA, OL. MISTO (AZ=Azeitona, VSC=Verde Sem Caroço, VF=Verde Fatiada, OL=Óleo)';
COMMENT ON COLUMN cadastro_palletizacao.tipo_embalagem IS 'Embalagem: BD 6X2, VD 12X500, GARRAFA 12X500, PET 12X200, POUCH 18X150 (BD=Balde, VD=Vidro, PET=Frasco PET)';
COMMENT ON COLUMN cadastro_palletizacao.linha_producao IS 'Linha: 1106, 1101 1/6, LF (La Famiglia), VALE SUL (terceirizado)';
COMMENT ON COLUMN cadastro_palletizacao.subcategoria IS 'Subcategoria específica do produto';

-- Exemplos de valores para popular baseados nos produtos existentes
/*
-- Categoria baseada no nome do produto
UPDATE cadastro_palletizacao SET 
    categoria_produto = CASE 
        WHEN nome_produto LIKE '%PALMITO%' THEN 'PALMITO'
        WHEN nome_produto LIKE '%AZEITONA%' THEN 'CONSERVAS'
        WHEN nome_produto LIKE '%MOLHO%' THEN 'MOLHOS'
        WHEN nome_produto LIKE '%ÓLEO%' OR nome_produto LIKE '%OLEO%' THEN 'ÓLEOS'
        WHEN nome_produto LIKE '%CONSERVA%' THEN 'CONSERVAS'
        ELSE NULL
    END
WHERE categoria_produto IS NULL;

-- Embalagem baseada no nome do produto
UPDATE cadastro_palletizacao SET 
    tipo_embalagem = CASE 
        WHEN nome_produto LIKE '%BALDE%' OR nome_produto LIKE '%BD %' THEN 'BD 6X2'
        WHEN nome_produto LIKE '%VIDRO%' OR nome_produto LIKE '%VD %' THEN 'VD 12X500'
        WHEN nome_produto LIKE '%GARRAFA%' THEN 'GARRAFA 12X500'
        WHEN nome_produto LIKE '%PET%' THEN 'PET 12X200'
        WHEN nome_produto LIKE '%POUCH%' THEN 'POUCH 18X150'
        ELSE NULL
    END
WHERE tipo_embalagem IS NULL;

-- Matéria-prima baseada no nome do produto
UPDATE cadastro_palletizacao SET 
    tipo_materia_prima = CASE 
        WHEN nome_produto LIKE '%AZEITONA%VERDE%' AND nome_produto LIKE '%S/C%' THEN 'AZ VSC'
        WHEN nome_produto LIKE '%AZEITONA%VERDE%' AND nome_produto LIKE '%FATIAD%' THEN 'AZ VF'
        WHEN nome_produto LIKE '%CEBOLINHA%' THEN 'CEBOLINHA'
        WHEN nome_produto LIKE '%ÓLEO%MISTO%' OR nome_produto LIKE '%OLEO%MISTO%' THEN 'OL. MISTO'
        ELSE NULL
    END
WHERE tipo_materia_prima IS NULL;
*/