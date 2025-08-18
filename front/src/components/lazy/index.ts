import { lazy } from 'react';
import { withLazyLoading, LoadingFallbacks, createLazyRoute } from '@/lib/lazy-loading';

// Lazy load heavy page components
export const LazyETLPage = createLazyRoute(
  () => import('@/app/(protected)/etl/page'),
  LoadingFallbacks.ETLPage
);

export const LazyDocumentsPage = createLazyRoute(
  () => import('@/app/(protected)/documents/page'),
  LoadingFallbacks.DocumentsPage
);

export const LazyProfilePage = createLazyRoute(
  () => import('@/app/(protected)/profile/page'),
  LoadingFallbacks.ProfilePage
);

export const LazyChatPage = createLazyRoute(
  () => import('@/app/(protected)/chat/page'),
  LoadingFallbacks.ChatPage
);

// Lazy load heavy component groups
export const LazyETLComponents = {
  ETLJobList: withLazyLoading(
    lazy(() => import('@/components/etl/etl-job-list').then(m => ({ default: m.ETLJobList }))),
    LoadingFallbacks.Component
  ),
  ETLJobDetail: withLazyLoading(
    lazy(() => import('@/components/etl/etl-job-detail').then(m => ({ default: m.ETLJobDetail }))),
    LoadingFallbacks.Component
  ),
  RealTimeProgressMonitor: withLazyLoading(
    lazy(() => import('@/components/etl/real-time-progress-monitor').then(m => ({ default: m.RealTimeProgressMonitor }))),
    LoadingFallbacks.Component
  ),
};

export const LazyDocumentComponents = {
  DocumentsGrid: withLazyLoading(
    lazy(() => import('@/components/documents/documents-grid').then(m => ({ default: m.DocumentsGrid }))),
    LoadingFallbacks.Component
  ),
  DocumentReprocessing: withLazyLoading(
    lazy(() => import('@/components/documents/document-reprocessing').then(m => ({ default: m.DocumentReprocessing }))),
    LoadingFallbacks.Component
  ),
};

export const LazyChatComponents = {
  ChatContainer: withLazyLoading(
    lazy(() => import('@/components/chat/chat-container').then(m => ({ default: m.ChatContainer }))),
    LoadingFallbacks.Component
  ),
  DocumentReferencePanel: withLazyLoading(
    lazy(() => import('@/components/chat/document-reference-panel').then(m => ({ default: m.DocumentReferencePanel }))),
    LoadingFallbacks.Component
  ),
  ConversationHistoryList: withLazyLoading(
    lazy(() => import('@/components/history/conversation-history-list').then(m => ({ default: m.ConversationHistoryList }))),
    LoadingFallbacks.Component
  ),
};

export const LazyProfileComponents = {
  UserProfileCard: withLazyLoading(
    lazy(() => import('@/components/profile/user-profile-card').then(m => ({ default: m.UserProfileCard }))),
    LoadingFallbacks.Component
  ),
};

// Lazy load modals and overlays (these are good candidates for lazy loading)
export const LazyModals = {
  ConversationDetailModal: withLazyLoading(
    lazy(() => import('@/components/history/conversation-detail-modal').then(m => ({ default: m.ConversationDetailModal }))),
    LoadingFallbacks.Component
  ),
  FeedbackForm: withLazyLoading(
    lazy(() => import('@/components/chat/feedback-form').then(m => ({ default: m.FeedbackForm }))),
    LoadingFallbacks.Component
  ),
  ConfirmationDialog: withLazyLoading(
    lazy(() => import('@/components/ui/confirmation-dialog').then(m => ({ default: m.ConfirmationDialog }))),
    LoadingFallbacks.Component
  ),
};

// Preload functions for performance optimization
export const preloadComponents = {
  etl: () => Promise.all([
    import('@/components/etl/etl-job-list'),
    import('@/components/etl/etl-job-detail'),
    import('@/components/etl/real-time-progress-monitor'),
  ]),
  
  documents: () => Promise.all([
    import('@/components/documents/documents-grid'),
    import('@/components/documents/document-reprocessing'),
  ]),
  
  chat: () => Promise.all([
    import('@/components/chat/chat-container'),
    import('@/components/chat/document-reference-panel'),
  ]),
  
  profile: () => Promise.all([
    import('@/components/profile/user-profile-card'),
  ]),
  
  modals: () => Promise.all([
    import('@/components/history/conversation-detail-modal'),
    import('@/components/chat/feedback-form'),
    import('@/components/ui/confirmation-dialog'),
  ]),
};

// Bundle analysis helpers
export const bundleInfo = {
  // Estimated sizes (these would be updated based on actual bundle analysis)
  etlComponents: '~45KB',
  documentComponents: '~32KB', 
  chatComponents: '~58KB',
  profileComponents: '~18KB',
  modalComponents: '~25KB',
  
  // Priority levels for loading
  priority: {
    high: ['chat', 'profile'], // Most commonly used
    medium: ['documents', 'etl'], // Moderately used
    low: ['modals'], // Used on demand
  },
};