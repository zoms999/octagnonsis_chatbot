import { 
  useQuery, 
  useMutation, 
  useQueryClient,
  UseQueryOptions,
  UseMutationOptions,
} from '@tanstack/react-query';
import { 
  ApiClient, 
  ApiErrorHandler 
} from '@/lib/api';
import { 
  queryKeys, 
  cacheConfig, 
  cacheUtils,
  handleQueryError 
} from '@/lib/react-query';
import { 
  LoginCredentials,
  LoginResponse,
  AuthUser,
  ChatResponse,
  ChatFeedback,
  ChatFeedbackResponse,
  ConversationHistoryResponse,
  ConversationDetail,
  ETLJobsResponse,
  ETLJobStatusResponse,
  ETLJobResponse,
  UserProfileResponse,
  UserDocumentsResponse,
  ApiError,
} from '@/lib/types';
import { ErrorHandler } from '@/lib/error-handling';

// Authentication hooks
export function useLogin(
  options?: UseMutationOptions<LoginResponse, ApiError, LoginCredentials>
) {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: ApiClient.login,
    onSuccess: (data) => {
      // Cache user data after successful login
      if (data.user) {
        queryClient.setQueryData(queryKeys.auth.user, data.user);
        
        // Prefetch user data
        if (data.user.id) {
          cacheUtils.prefetchUserData(data.user.id);
        }
      }
    },
    onError: (error: ApiError) => {
      ErrorHandler.logError(error, 'login');
      if (ApiErrorHandler.isAuthError(error)) {
        ErrorHandler.handleAuthError(error);
      }
    },
    ...options,
  });
}

export function useValidateSession(
  options?: UseQueryOptions<AuthUser, ApiError>
) {
  return useQuery({
    queryKey: queryKeys.auth.user,
    queryFn: ApiClient.validateSession,
    ...cacheConfig.auth,
    retry: false, // Don't retry auth validation
    ...options,
  });
}

export function useLogout(
  options?: UseMutationOptions<void, ApiError, void>
) {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: ApiClient.logout,
    onSuccess: () => {
      // Clear all cached data on logout
      cacheUtils.clearAllCache();
    },
    onError: (error: ApiError) => {
      ErrorHandler.logError(error, 'logout');
      // Clear cache even if logout request fails
      cacheUtils.clearAllCache();
    },
    ...options,
  });
}

// Chat hooks
export function useSendQuestion(
  options?: UseMutationOptions<ChatResponse, ApiError, { question: string; conversationId?: string }>
) {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: ({ question, conversationId }) => 
      ApiClient.sendQuestion(question, conversationId),
    onMutate: async ({ question, conversationId }) => {
      // Optimistic update: add user message immediately
      const user = queryClient.getQueryData<AuthUser>(queryKeys.auth.user);
      if (!user?.id) return;
      
      // Cancel outgoing refetches
      await queryClient.cancelQueries({ 
        queryKey: queryKeys.chat.history(user.id) 
      });
      
      if (conversationId) {
        await queryClient.cancelQueries({ 
          queryKey: queryKeys.chat.conversation(conversationId) 
        });
        
        // Optimistically add user message to conversation
        const rollback = cacheUtils.optimisticUpdate<ConversationDetail>(
          queryKeys.chat.conversation(conversationId),
          (old) => {
            const userMessage = {
              id: `temp-${Date.now()}`,
              type: 'user' as const,
              content: question,
              timestamp: new Date(),
              conversation_id: conversationId,
            };
            
            if (old) {
              return {
                ...old,
                messages: [...old.messages, userMessage],
                updated_at: new Date().toISOString(),
              };
            }
            
            return {
              conversation_id: conversationId,
              messages: [userMessage],
              created_at: new Date().toISOString(),
              updated_at: new Date().toISOString(),
            };
          }
        );
        
        return { rollback };
      }
    },
    onSuccess: (data, variables, context) => {
      // Update conversation history
      const user = queryClient.getQueryData<AuthUser>(queryKeys.auth.user);
      if (user?.id) {
        queryClient.invalidateQueries({ 
          queryKey: queryKeys.chat.history(user.id) 
        });
      }
      
      // Update conversation detail with actual response
      if (data.conversation_id) {
        cacheUtils.updateQueryData<ConversationDetail>(
          queryKeys.chat.conversation(data.conversation_id),
          (old) => {
            const assistantMessage = {
              id: `${Date.now()}`,
              type: 'assistant' as const,
              content: data.response,
              timestamp: new Date(data.timestamp),
              confidence_score: data.confidence_score,
              processing_time: data.processing_time,
              retrieved_documents: data.retrieved_documents,
              conversation_id: data.conversation_id,
            };
            
            if (old) {
              // Replace temp user message and add assistant response
              const messages = old.messages.filter(m => !m.id.startsWith('temp-'));
              const userMessage = {
                id: `user-${Date.now()}`,
                type: 'user' as const,
                content: variables.question,
                timestamp: new Date(data.timestamp),
                conversation_id: data.conversation_id,
              };
              
              return {
                ...old,
                messages: [...messages, userMessage, assistantMessage],
                updated_at: data.timestamp,
              };
            }
            
            return {
              conversation_id: data.conversation_id,
              messages: [assistantMessage],
              created_at: data.timestamp,
              updated_at: data.timestamp,
            };
          }
        );
      }
    },
    onError: (error: ApiError, variables, context) => {
      // Rollback optimistic update on error
      if (context?.rollback) {
        context.rollback();
      }
      
      ErrorHandler.logError(error, 'send_question');
      if (ApiErrorHandler.isRateLimitError(error)) {
        ErrorHandler.handleRateLimitError(error);
      }
    },
    ...options,
  });
}

export function useSubmitFeedback(
  options?: UseMutationOptions<ChatFeedbackResponse, ApiError, ChatFeedback>
) {
  return useMutation({
    mutationFn: ApiClient.submitFeedback,
    onError: (error: ApiError) => {
      ErrorHandler.logError(error, 'submit_feedback');
    },
    ...options,
  });
}

export function useConversationHistory(
  userId: string,
  page: number = 1,
  limit: number = 20,
  options?: UseQueryOptions<ConversationHistoryResponse, ApiError>
) {
  return useQuery({
    queryKey: queryKeys.chat.history(userId, page, limit),
    queryFn: () => ApiClient.getConversationHistory(userId, page, limit),
    enabled: !!userId,
    ...cacheConfig.conversations,
    ...options,
  });
}

export function useConversationDetail(
  conversationId: string,
  options?: UseQueryOptions<ConversationDetail, ApiError>
) {
  return useQuery({
    queryKey: queryKeys.chat.conversation(conversationId),
    queryFn: () => ApiClient.getConversationDetail(conversationId),
    enabled: !!conversationId,
    ...cacheConfig.conversations,
    ...options,
  });
}

// ETL hooks
export function useETLJobs(
  userId: string,
  page: number = 1,
  limit: number = 20,
  options?: UseQueryOptions<ETLJobsResponse, ApiError>
) {
  return useQuery({
    queryKey: queryKeys.etl.jobs(userId, page, limit),
    queryFn: () => ApiClient.getETLJobs(userId, page, limit),
    enabled: !!userId,
    ...cacheConfig.etlJobs,
    ...options,
  });
}

export function useETLJobStatus(
  jobId: string,
  options?: UseQueryOptions<ETLJobStatusResponse, ApiError>
) {
  return useQuery({
    queryKey: queryKeys.etl.jobStatus(jobId),
    queryFn: () => ApiClient.getETLJobStatus(jobId),
    enabled: !!jobId,
    ...cacheConfig.etlJobStatus,
    refetchInterval: (data) => {
      // Auto-refetch if job is still running
      if (data && 'status' in data && (data.status === 'running' || data.status === 'pending')) {
        return 5000; // Refetch every 5 seconds
      }
      return false;
    },
    ...options,
  });
}

export function useRetryETLJob(
  options?: UseMutationOptions<ETLJobResponse, ApiError, string>
) {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: ApiClient.retryETLJob,
    onMutate: async (jobId) => {
      // Cancel outgoing refetches
      await queryClient.cancelQueries({ 
        queryKey: queryKeys.etl.jobStatus(jobId) 
      });
      
      // Optimistically update job status to pending
      const rollback = cacheUtils.optimisticUpdate<ETLJobStatusResponse>(
        queryKeys.etl.jobStatus(jobId),
        (old) => {
          if (old) {
            return {
              ...old,
              status: 'pending',
              progress: 0,
              current_step: 'Initializing retry...',
              updated_at: new Date().toISOString(),
            };
          }
          return old;
        }
      );
      
      return { rollback };
    },
    onSuccess: (data, jobId) => {
      // Invalidate job status and jobs list
      queryClient.invalidateQueries({ 
        queryKey: queryKeys.etl.jobStatus(jobId) 
      });
      
      // Invalidate all ETL jobs queries
      queryClient.invalidateQueries({ 
        queryKey: queryKeys.etl.all 
      });
    },
    onError: (error: ApiError, jobId, context) => {
      // Rollback optimistic update
      if (context?.rollback) {
        context.rollback();
      }
      
      ErrorHandler.logError(error, 'retry_etl_job');
    },
    ...options,
  });
}

export function useCancelETLJob(
  options?: UseMutationOptions<void, ApiError, string>
) {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: ApiClient.cancelETLJob,
    onSuccess: (data, jobId) => {
      // Invalidate job status and jobs list
      queryClient.invalidateQueries({ 
        queryKey: queryKeys.etl.jobStatus(jobId) 
      });
      
      // Invalidate all ETL jobs queries
      queryClient.invalidateQueries({ 
        queryKey: queryKeys.etl.all 
      });
    },
    onError: (error: ApiError) => {
      ErrorHandler.logError(error, 'cancel_etl_job');
    },
    ...options,
  });
}

export function useTriggerReprocessing(
  options?: UseMutationOptions<ETLJobResponse, ApiError, { userId: string; force?: boolean }>
) {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: ({ userId, force = false }) => 
      ApiClient.triggerReprocessing(userId, force),
    onMutate: async ({ userId }) => {
      // Cancel outgoing refetches for user data
      await Promise.all([
        queryClient.cancelQueries({ queryKey: queryKeys.user.profile(userId) }),
        queryClient.cancelQueries({ queryKey: queryKeys.etl.jobs(userId) }),
      ]);
      
      // Optimistically update user profile to show processing status
      const rollback = cacheUtils.optimisticUpdate<UserProfileResponse>(
        queryKeys.user.profile(userId),
        (old) => {
          if (old) {
            return {
              ...old,
              processing_status: 'pending',
            };
          }
          return old;
        }
      );
      
      return { rollback };
    },
    onSuccess: (data, { userId }) => {
      // Invalidate user-related queries
      cacheUtils.invalidateUserQueries(userId);
      
      // Prefetch updated data
      cacheUtils.prefetchUserData(userId, 'high');
    },
    onError: (error: ApiError, { userId }, context) => {
      // Rollback optimistic update
      if (context?.rollback) {
        context.rollback();
      }
      
      ErrorHandler.logError(error, 'trigger_reprocessing');
    },
    ...options,
  });
}

// User management hooks
export function useUserProfile(
  userId: string,
  options?: UseQueryOptions<UserProfileResponse, ApiError>
) {
  return useQuery({
    queryKey: queryKeys.user.profile(userId),
    queryFn: () => ApiClient.getUserProfile(userId),
    enabled: !!userId,
    ...cacheConfig.userProfile,
    ...options,
  });
}

export function useUserDocuments(
  userId: string,
  page: number = 1,
  limit: number = 20,
  docType?: string,
  options?: UseQueryOptions<UserDocumentsResponse, ApiError>
) {
  return useQuery({
    queryKey: queryKeys.user.documents(userId, page, limit, docType),
    queryFn: () => ApiClient.getUserDocuments(userId, page, limit, docType),
    enabled: !!userId,
    ...cacheConfig.documents,
    ...options,
  });
}

export function useReprocessUserDocuments(
  options?: UseMutationOptions<ETLJobResponse, ApiError, { userId: string; force?: boolean }>
) {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: ({ userId, force = false }) => 
      ApiClient.reprocessUserDocuments(userId, force),
    onSuccess: (data, { userId }) => {
      // Invalidate user-related queries
      cacheUtils.invalidateUserQueries(userId);
    },
    onError: (error: ApiError) => {
      ErrorHandler.logError(error, 'reprocess_user_documents');
    },
    ...options,
  });
}