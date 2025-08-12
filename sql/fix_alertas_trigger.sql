-- =====================================================
-- Correção do trigger em alertas_separacao_cotada
-- =====================================================

-- Primeiro, verificar se o campo updated_at existe
ALTER TABLE alertas_separacao_cotada 
ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;

-- Se o trigger existir, removê-lo temporariamente
DROP TRIGGER IF EXISTS update_alertas_separacao_cotada_updated_at ON alertas_separacao_cotada;

-- Recriar o trigger apenas se o campo existir
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name = 'alertas_separacao_cotada' 
        AND column_name = 'updated_at'
    ) THEN
        CREATE TRIGGER update_alertas_separacao_cotada_updated_at
        BEFORE UPDATE ON alertas_separacao_cotada
        FOR EACH ROW
        EXECUTE FUNCTION update_updated_at_column();
    END IF;
END $$;