-- Analytics and Feedback schema additions

-- Extend chat_conversations with analytics fields
ALTER TABLE chat_conversations ADD COLUMN IF NOT EXISTS confidence_score DOUBLE PRECISION;
ALTER TABLE chat_conversations ADD COLUMN IF NOT EXISTS quality_label VARCHAR(20);
ALTER TABLE chat_conversations ADD COLUMN IF NOT EXISTS processing_time DOUBLE PRECISION;
ALTER TABLE chat_conversations ADD COLUMN IF NOT EXISTS question_category VARCHAR(50);
ALTER TABLE chat_conversations ADD COLUMN IF NOT EXISTS question_intent VARCHAR(50);
ALTER TABLE chat_conversations ADD COLUMN IF NOT EXISTS ab_variant VARCHAR(10);
ALTER TABLE chat_conversations ADD COLUMN IF NOT EXISTS prompt_template VARCHAR(50);

-- Feedback table for user satisfaction
CREATE TABLE IF NOT EXISTS chat_feedback (
    feedback_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES chat_conversations(conversation_id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES chat_users(user_id) ON DELETE CASCADE,
    rating INTEGER CHECK (rating BETWEEN 1 AND 5),
    helpful BOOLEAN,
    comment TEXT,
    tags TEXT[],
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_chat_feedback_user_id ON chat_feedback(user_id);
CREATE INDEX IF NOT EXISTS idx_chat_feedback_conversation_id ON chat_feedback(conversation_id);


