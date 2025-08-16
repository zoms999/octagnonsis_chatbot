-- Migration: Add USER_PROFILE to document type constraint
-- Date: 2025-08-12
-- Description: Updates the chk_doc_type constraint to include USER_PROFILE document type

-- Drop the existing constraint
ALTER TABLE chat_documents DROP CONSTRAINT IF EXISTS chk_doc_type;

-- Add the updated constraint with USER_PROFILE included
ALTER TABLE chat_documents ADD CONSTRAINT chk_doc_type 
    CHECK (doc_type IN ('USER_PROFILE', 'PERSONALITY_PROFILE', 'THINKING_SKILLS', 'CAREER_RECOMMENDATIONS', 
                       'LEARNING_STYLE', 'COMPETENCY_ANALYSIS', 'PREFERENCE_ANALYSIS'));