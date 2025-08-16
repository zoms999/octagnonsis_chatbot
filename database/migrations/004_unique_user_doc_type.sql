-- Ensure unique constraint for (user_id, doc_type) on chat_documents
-- Also deduplicate existing rows to avoid constraint violation

-- 1) Remove duplicates keeping the most recently updated/created row
WITH ranked AS (
    SELECT 
        doc_id,
        ROW_NUMBER() OVER (
            PARTITION BY user_id, doc_type 
            ORDER BY updated_at DESC NULLS LAST, created_at DESC
        ) AS rn
    FROM chat_documents
)
DELETE FROM chat_documents d
USING ranked r
WHERE d.doc_id = r.doc_id AND r.rn > 1;

-- 2) Add unique constraint if it does not already exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint c
        JOIN pg_class t ON c.conrelid = t.oid
        JOIN pg_namespace n ON n.oid = t.relnamespace
        WHERE t.relname = 'chat_documents'
          AND n.nspname = 'public'
          AND c.conname = 'unique_user_doc_type'
    ) THEN
        ALTER TABLE public.chat_documents
        ADD CONSTRAINT unique_user_doc_type UNIQUE (user_id, doc_type);
    END IF;
END$$;


