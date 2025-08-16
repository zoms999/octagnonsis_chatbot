-- Add error tracking fields to chat_etl_jobs
ALTER TABLE chat_etl_jobs
    ADD COLUMN IF NOT EXISTS error_type VARCHAR(100),
    ADD COLUMN IF NOT EXISTS failed_stage VARCHAR(100);


