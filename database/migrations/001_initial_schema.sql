-- Initial schema migration for Aptitude Chatbot RAG System
-- Creates chat_ prefixed tables with pgvector support

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
-- gen_random_uuid() is provided by pgcrypto in PostgreSQL
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- User management table
CREATE TABLE chat_users (
    user_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    anp_seq INTEGER UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(255),
    test_completed_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Document storage with vector embeddings
CREATE TABLE chat_documents (
    doc_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES chat_users(user_id) ON DELETE CASCADE,
    doc_type VARCHAR(50) NOT NULL,
    content JSONB NOT NULL,
    summary_text TEXT NOT NULL,
    embedding_vector vector(768) NOT NULL,
    doc_metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Job and career information
CREATE TABLE chat_jobs (
    job_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_code VARCHAR(20) UNIQUE NOT NULL,
    job_name VARCHAR(200) NOT NULL,
    job_outline TEXT,
    main_business TEXT,
    embedding_vector vector(768),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Academic major information  
CREATE TABLE chat_majors (
    major_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    major_code VARCHAR(20) UNIQUE NOT NULL,
    major_name VARCHAR(200) NOT NULL,
    description TEXT,
    embedding_vector vector(768),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Conversation history
CREATE TABLE chat_conversations (
    conversation_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES chat_users(user_id) ON DELETE CASCADE,
    question TEXT NOT NULL,
    response TEXT NOT NULL,
    retrieved_doc_ids UUID[] DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ETL job tracking
CREATE TABLE chat_etl_jobs (
    job_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id VARCHAR(100),
    user_id UUID NOT NULL REFERENCES chat_users(user_id) ON DELETE CASCADE,
    anp_seq INTEGER NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    progress_percentage INTEGER DEFAULT 0,
    current_step VARCHAR(255),
    completed_steps INTEGER DEFAULT 0,
    total_steps INTEGER DEFAULT 7,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    query_results_summary JSONB,
    documents_created TEXT[]
);

-- Create indexes for performance
CREATE INDEX idx_chat_users_anp_seq ON chat_users(anp_seq);
CREATE INDEX idx_chat_documents_user_id ON chat_documents(user_id);
CREATE INDEX idx_chat_documents_doc_type ON chat_documents(doc_type);
CREATE INDEX idx_chat_conversations_user_id ON chat_conversations(user_id);
CREATE INDEX idx_chat_jobs_job_code ON chat_jobs(job_code);
CREATE INDEX idx_chat_majors_major_code ON chat_majors(major_code);

-- Vector similarity search indexes using HNSW
CREATE INDEX idx_chat_documents_embedding ON chat_documents USING hnsw (embedding_vector vector_cosine_ops);
CREATE INDEX idx_chat_jobs_embedding ON chat_jobs USING hnsw (embedding_vector vector_cosine_ops);
CREATE INDEX idx_chat_majors_embedding ON chat_majors USING hnsw (embedding_vector vector_cosine_ops);

-- Add constraints
ALTER TABLE chat_documents ADD CONSTRAINT chk_doc_type 
    CHECK (doc_type IN ('PERSONALITY_PROFILE', 'THINKING_SKILLS', 'CAREER_RECOMMENDATIONS', 
                       'LEARNING_STYLE', 'COMPETENCY_ANALYSIS', 'PREFERENCE_ANALYSIS'));

-- Create updated_at trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply updated_at triggers
CREATE TRIGGER update_chat_users_updated_at BEFORE UPDATE ON chat_users 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_chat_documents_updated_at BEFORE UPDATE ON chat_documents 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();