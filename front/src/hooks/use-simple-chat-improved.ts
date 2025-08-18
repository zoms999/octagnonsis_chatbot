import { useState, useCallback, useRef, useEffect, useMemo } from 'react';
import { useAuth } from '@/providers/auth-provider';
import { SimpleChatHandler, SimpleChatConfig, SimpleChatCallbacks } from '@/lib/simple-chat-handler-improved';
import { ChatMessage } from '@/lib/types';
import { extractUserId } from '@/lib/user-utils';
import { useChatErrorHandler } from './use-chat-error-handler';

export interface UseSimpleChatConfig extends SimpleChatConfig {
  // Additional hook-specific configuration
  autoResetError?: boolean;
  errorResetDelay?: number;
}

export interface UseSimpleChatReturn {
  sendQuestion: (question: string, conversationId?: string) => Promise<void>;
  isProcessing: boolean;
  lastMessage: ChatMessage | null;
  lastError: string | null;
  clearError: () => void;
  isReady: boolean;
  // Enhanced error handling
  currentError: any;
  errorHistory: any[];
  isShowingError: boolean;
  dismissError: () => void;
  retryLastAction: () => void;
}

/**
 * Improved simplified chat hook with better response handling and state management
 */
export function useSimpleChat(config: UseSimpleChatConfig = {}): UseSimpleChatReturn {
  const { user } = useAuth();
  const [isProcessing, setIsProcessing] = useState(false);
  const [lastMessage, setLastMessage] = useState<ChatMessage | null>(null);
  const [lastError, setLastError] = useState<string | null>(null);
  
  // Enhanced error handling
  const errorHandler = useChatErrorHandler({
    autoShow: true,
    maxErrors: 10,
    errorTimeout: config.autoResetError !== false ? (config.errorResetDelay || 5000) : 0,
    onRetry: () => {
      // This will be set by the sendQuestion function
    }
  });
  
  // Use ref to maintain handler instance across renders
  const handlerRef = useRef<SimpleChatHandler | null>(null);
  const errorTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const lastMessageIdRef = useRef<string | null>(null);
  const lastQuestionRef = useRef<{ question: string; conversationId?: string } | null>(null);

  // Initialize handler with callbacks
  useEffect(() => {
    console.log('useSimpleChat: Initializing handler with config:', config);
    
    const callbacks: SimpleChatCallbacks = {
      onMessage: (message: ChatMessage) => {
        console.log('useSimpleChat: Received message:', {
          id: message.id,
          type: message.type,
          contentLength: message.content?.length,
          conversationId: message.conversation_id
        });
        
        // Prevent duplicate message processing
        if (lastMessageIdRef.current === message.id) {
          console.log('useSimpleChat: Duplicate message ID detected, skipping:', message.id);
          return;
        }
        
        lastMessageIdRef.current = message.id;
        setLastMessage(message);
        setLastError(null); // Clear error on successful message
      },
      onError: (error: string, chatError?: any) => {
        console.error('useSimpleChat: Received error:', error);
        setLastError(error);
        
        // Handle error through enhanced error handler
        if (chatError) {
          errorHandler.handleError(chatError, {
            userId: extractUserId(user),
            conversationId: lastQuestionRef.current?.conversationId,
            question: lastQuestionRef.current?.question,
            endpoint: '/api/chat/question'
          });
        } else {
          // Fallback for string errors
          errorHandler.handleError(new Error(error), {
            userId: extractUserId(user),
            endpoint: '/api/chat/question'
          });
        }
      },
      onProcessingStart: () => {
        console.log('useSimpleChat: Processing started');
        setIsProcessing(true);
        setLastError(null); // Clear error when starting new request
      },
      onProcessingEnd: () => {
        console.log('useSimpleChat: Processing ended');
        setIsProcessing(false);
      }
    };

    handlerRef.current = new SimpleChatHandler(config, callbacks);
    console.log('useSimpleChat: Handler initialized:', !!handlerRef.current);

    return () => {
      // Cleanup timeout on unmount
      if (errorTimeoutRef.current) {
        clearTimeout(errorTimeoutRef.current);
      }
    };
  }, [config, errorHandler]);

  // Auto-reset error after delay
  useEffect(() => {
    if (lastError && config.autoResetError !== false) {
      const delay = config.errorResetDelay || 5000; // 5 seconds default
      
      errorTimeoutRef.current = setTimeout(() => {
        setLastError(null);
      }, delay);

      return () => {
        if (errorTimeoutRef.current) {
          clearTimeout(errorTimeoutRef.current);
        }
      };
    }
  }, [lastError, config.autoResetError, config.errorResetDelay]);

  const sendQuestion = useCallback(async (question: string, conversationId?: string) => {
    const userId = extractUserId(user);
    
    // Store current question for retry functionality
    lastQuestionRef.current = { question, conversationId };
    
    console.log('useSimpleChat.sendQuestion called:', {
      question: question.substring(0, 50) + '...',
      conversationId,
      userId,
      hasHandler: !!handlerRef.current,
      isProcessing
    });

    if (!userId) {
      const error = 'User not authenticated or user ID not available';
      console.error('useSimpleChat:', error);
      const authError = new Error(error);
      (authError as any).type = 'auth_error';
      (authError as any).status = 401;
      errorHandler.handleError(authError, {
        endpoint: '/api/chat/question',
        question: question.substring(0, 100)
      });
      setLastError(error);
      return;
    }

    if (!handlerRef.current) {
      const error = 'Chat handler not initialized';
      console.error('useSimpleChat:', error);
      errorHandler.handleError(new Error(error), {
        userId,
        endpoint: '/api/chat/question'
      });
      setLastError(error);
      return;
    }

    if (isProcessing) {
      const error = 'Already processing a message. Please wait.';
      console.log('useSimpleChat:', error);
      const processingError = new Error(error);
      (processingError as any).type = 'validation_error';
      errorHandler.handleError(processingError, {
        userId,
        conversationId,
        question: question.substring(0, 100),
        endpoint: '/api/chat/question'
      });
      setLastError(error);
      return;
    }

    try {
      console.log('useSimpleChat: Calling handler.sendQuestion');
      const result = await handlerRef.current.sendQuestion(question, conversationId, userId);
      console.log('useSimpleChat: Handler result:', {
        success: result.success,
        hasData: !!result.data,
        error: result.error
      });
      
      if (!result.success && result.error) {
        setLastError(result.error);
      }
    } catch (error: any) {
      const errorMessage = error.message || 'Failed to send question';
      console.error('useSimpleChat: Unexpected error:', error);
      
      // Handle unexpected errors
      errorHandler.handleError(error, {
        userId,
        conversationId,
        question: question.substring(0, 100),
        endpoint: '/api/chat/question'
      });
      
      setLastError(errorMessage);
    }
  }, [user, isProcessing, errorHandler]);

  const clearError = useCallback(() => {
    setLastError(null);
    errorHandler.clearError();
    if (errorTimeoutRef.current) {
      clearTimeout(errorTimeoutRef.current);
      errorTimeoutRef.current = null;
    }
  }, [errorHandler]);

  // Check if the hook is ready to send messages
  const isReady = useMemo(() => {
    try {
      const userId = extractUserId(user);
      const hasHandler = !!handlerRef.current;
      const ready = !!userId && hasHandler && !isProcessing;
      
      console.log('useSimpleChat: isReady calculation:', {
        user: !!user,
        userId: userId || 'null',
        hasHandler,
        isProcessing,
        ready,
        userObject: user
      });
      
      return ready;
    } catch (error) {
      console.error('useSimpleChat: Error calculating isReady:', error);
      return false;
    }
  }, [user, isProcessing]);

  // Set up retry functionality
  useEffect(() => {
    errorHandler.setRetryAction(() => {
      if (lastQuestionRef.current) {
        sendQuestion(lastQuestionRef.current.question, lastQuestionRef.current.conversationId);
      }
    });
  }, [errorHandler, sendQuestion]);

  return {
    sendQuestion,
    isProcessing,
    lastMessage,
    lastError,
    clearError,
    isReady,
    // Enhanced error handling
    currentError: errorHandler.currentError,
    errorHistory: errorHandler.errorHistory,
    isShowingError: errorHandler.isShowingError,
    dismissError: errorHandler.dismissError,
    retryLastAction: errorHandler.retryLastAction
  };
}

/**
 * Hook variant with predefined configuration for production use
 */
export function useSimpleChatProduction(): UseSimpleChatReturn {
  return useSimpleChat({
    enableDebugLogging: false,
    timeout: 30000,
    maxRetries: 2,
    retryDelay: 1000,
    autoResetError: true,
    errorResetDelay: 5000
  });
}

/**
 * Hook variant with predefined configuration for development/debugging
 */
export function useSimpleChatDebug(): UseSimpleChatReturn {
  return useSimpleChat({
    enableDebugLogging: true,
    timeout: 30000,
    maxRetries: 1,
    retryDelay: 500,
    autoResetError: false, // Keep errors visible for debugging
    errorResetDelay: 10000
  });
}