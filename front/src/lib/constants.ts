// Application constants

// API endpoints
export const API_ENDPOINTS = {
  // Authentication
  LOGIN: '/api/auth/login',
  LOGOUT: '/api/auth/logout',
  ME: '/api/auth/me',
  REFRESH: '/api/auth/refresh',

  // Chat
  CHAT_QUESTION: '/api/chat/question',
  CHAT_FEEDBACK: '/api/chat/feedback',
  CHAT_HISTORY: '/api/chat/history',
  CHAT_WS: '/api/chat/ws',

  // ETL
  ETL_JOBS: '/api/etl/users',
  ETL_JOB_STATUS: '/api/etl/jobs',
  ETL_JOB_PROGRESS: '/api/etl/jobs',
  ETL_REPROCESS: '/api/etl/users',

  // Users
  USER_PROFILE: '/api/users',
  USER_DOCUMENTS: '/api/users',
} as const;

// WebSocket events
export const WS_EVENTS = {
  CONNECT: 'connect',
  DISCONNECT: 'disconnect',
  MESSAGE: 'message',
  ERROR: 'error',
  QUESTION: 'question',
  RESPONSE: 'response',
  STATUS: 'status',
} as const;

// Local storage keys
export const STORAGE_KEYS = {
  ACCESS_TOKEN: 'access_token',
  REFRESH_TOKEN: 'refresh_token',
  USER_DATA: 'user_data',
  THEME: 'theme',
  LANGUAGE: 'language',
} as const;

// Query keys for React Query
export const QUERY_KEYS = {
  // Auth
  AUTH_USER: ['auth', 'user'],
  
  // Chat
  CHAT_HISTORY: ['chat', 'history'],
  CONVERSATION: ['chat', 'conversation'],
  
  // ETL
  ETL_JOBS: ['etl', 'jobs'],
  ETL_JOB_STATUS: ['etl', 'job', 'status'],
  
  // User
  USER_PROFILE: ['user', 'profile'],
  USER_DOCUMENTS: ['user', 'documents'],
} as const;

// Default pagination
export const PAGINATION = {
  DEFAULT_LIMIT: 20,
  MAX_LIMIT: 100,
} as const;

// WebSocket configuration
export const WS_CONFIG = {
  RECONNECT_INTERVAL: 1000,
  MAX_RECONNECT_ATTEMPTS: 5,
  HEARTBEAT_INTERVAL: 30000,
} as const;

// Rate limiting
export const RATE_LIMITS = {
  CHAT_MESSAGES_PER_MINUTE: 10,
  API_REQUESTS_PER_MINUTE: 60,
} as const;

// File upload limits
export const FILE_LIMITS = {
  MAX_SIZE: 10 * 1024 * 1024, // 10MB
  ALLOWED_TYPES: ['application/pdf', 'text/plain', 'application/msword'],
} as const;

// UI constants
export const UI = {
  TOAST_DURATION: 5000,
  LOADING_DELAY: 200,
  ANIMATION_DURATION: 300,
} as const;

// Breakpoints (matching Tailwind CSS)
export const BREAKPOINTS = {
  SM: 640,
  MD: 768,
  LG: 1024,
  XL: 1280,
  '2XL': 1536,
} as const;