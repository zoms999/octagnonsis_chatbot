// Core TypeScript type definitions

// Authentication types
export interface AuthUser {
  id: string;
  name: string;
  type: 'personal' | 'organization_admin' | 'organization_member';
  ac_id?: string;
  sex?: string;
  isPaid?: boolean;
  productType?: string;
  isExpired?: boolean;
  state?: string;
  sessionCode?: string;
  ins_seq?: number;
}

export interface LoginCredentials {
  username: string;
  password: string;
  loginType: 'personal' | 'organization';
  sessionCode?: string;
}

export interface LoginResponse {
  success: boolean;
  message: string;
  user?: AuthUser;
  tokens?: {
    access: string;
    refresh: string;
  };
  expires_at?: string;
}

// Chat types
export interface ChatMessage {
  id: string;
  type: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  confidence_score?: number;
  processing_time?: number;
  retrieved_documents?: DocumentReference[];
  conversation_id?: string;
}

export interface DocumentReference {
  id: string;
  type: string;
  title: string;
  preview: string;
  relevance_score: number;
}

export interface ChatResponse {
  conversation_id: string;
  response: string;
  retrieved_documents: DocumentReference[];
  confidence_score: number;
  processing_time: number;
  timestamp: string;
}

// WebSocket types
export interface WebSocketState {
  status: 'connecting' | 'connected' | 'disconnected' | 'error';
  lastError?: string;
  reconnectAttempts: number;
}

export interface WebSocketMessage {
  type: 'question' | 'status' | 'response' | 'error';
  data: any;
  timestamp: string;
}

// ETL types
export interface ETLJob {
  job_id: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
  progress: number;
  current_step: string;
  estimated_completion_time?: string;
  error_message?: string;
  created_at: string;
  updated_at: string;
}

// User management types
export interface UserProfile {
  user_id: string;
  document_count: number;
  conversation_count: number;
  available_document_types: string[];
  last_conversation_at?: string;
  processing_status: 'none' | 'pending' | 'completed' | 'failed';
}

export interface UserDocument {
  id: string;
  doc_type: string;
  title: string;
  preview: DocumentPreview;
  created_at: string;
  updated_at: string;
}

export interface DocumentPreview {
  primary_tendency?: string;
  top_skills?: string[];
  top_jobs?: string[];
  summary?: string;
}

// API response types
export interface ApiResponse<T = any> {
  data: T;
  message?: string;
  status: number;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  limit: number;
  has_next: boolean;
  has_prev: boolean;
}

// Conversation History API responses
export interface Conversation {
  conversation_id: string;
  user_id: string;
  title?: string;
  created_at: string;
  updated_at: string;
  message_count: number;
  last_message_preview?: string;
}

export interface ConversationDetail {
  conversation_id: string;
  messages: ChatMessage[];
  created_at: string;
  updated_at: string;
}

export interface ConversationHistoryResponse {
  conversations: Conversation[];
  total: number;
  page: number;
  limit: number;
}

// ETL API responses
export interface ETLJobsResponse {
  jobs: ETLJob[];
  total: number;
  page: number;
  limit: number;
}

export interface ETLJobStatusResponse {
  job_id: string;
  status: ETLJob['status'];
  progress: number;
  current_step: string;
  estimated_completion_time?: string;
  error_message?: string;
  created_at: string;
  updated_at: string;
}

export interface ETLJobResponse {
  job_id: string;
  progress_url: string;
  estimated_completion_time: string;
}

// User Management API responses
export interface UserDocumentsResponse {
  documents: UserDocument[];
  total: number;
  page: number;
  limit: number;
}

export interface UserProfileResponse {
  user: UserProfile;
}

// Chat feedback types
export interface ChatFeedback {
  conversation_id: string;
  message_id: string;
  feedback_type: 'helpful' | 'not_helpful' | 'rating';
  rating?: number;
  comments?: string;
}

export interface ChatFeedbackResponse {
  feedback_id: string;
  message: string;
}

// WebSocket message types
export interface QuestionMessage {
  type: 'question';
  data: {
    question: string;
    conversation_id?: string;
  };
}

export interface StatusMessage {
  type: 'status';
  data: {
    status: 'processing' | 'generating' | 'complete';
    progress?: number;
  };
}

export interface ResponseMessage {
  type: 'response';
  data: ChatResponse;
}

export interface ErrorMessage {
  type: 'error';
  data: {
    message: string;
    code?: string;
  };
}

// Error types
export interface ApiError {
  message: string;
  status: number;
  code?: string;
  details?: Record<string, any>;
}

export interface NetworkError extends Error {
  status?: number;
  code?: string;
}

export interface AuthError extends ApiError {
  type: 'auth_error';
}

export interface RateLimitError extends ApiError {
  type: 'rate_limit';
  retry_after?: number;
}

export interface ValidationError extends ApiError {
  type: 'validation_error';
  field_errors?: Record<string, string[]>;
}

export interface ServerError extends ApiError {
  type: 'server_error';
}

// Environment configuration
export interface EnvironmentConfig {
  NEXT_PUBLIC_API_BASE: string;
  NEXT_PUBLIC_WS_BASE: string;
  NEXT_PUBLIC_ADMIN_TOKEN?: string;
  NODE_ENV: 'development' | 'production' | 'test';
}