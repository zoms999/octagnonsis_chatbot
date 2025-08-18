import { useState, useCallback, useRef, useEffect } from 'react';
import { useAuth } from '@/providers/auth-provider';
import { SimpleChatHandler, SimpleChatConfig, SimpleChatCallbacks } from '@/lib/simple-chat-handler-improved';
import { ChatMessage } from '@/lib/types';
import { extractUserId } from '@/lib/user-utils';

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
}

/**
 * Improved simplified chat hook with better response handling and state management
 */
export function useSimpleChat(config: UseSimpleChatConfig = {}): UseSimpleChatReturn {
  const { user } = useAuth();
  const [isProcessing, setIsProcessing] = useState(false);
  const [lastMessage, setLastMessage] = useState<ChatMessage | null>(null);
  const [lastError, setLastError] = useState<string | null>(null);
  
  // Use ref to maintain handler instance across renders
  const handlerRef = useRef<SimpleChatHandler | null>(null);
  const errorTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const lastMessageIdRef = useRef<string | null>(null);

  // Initialize handler with callbacks
  useEffect(() => {
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
      onError: (error: string) => {
        console.error('useSimpleChat: Received error:', error);
        setLastError(error);
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

    return () => {
      // Cleanup timeout on unmount
      if (errorTimeoutRef.current) {
        clearTimeout(errorTimeoutRef.current);
      }
    };
  }, [config]);

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
      setLastError(error);
      return;
    }

    if (!handlerRef.current) {
      const error = 'Chat handler not initialized';
      console.error('useSimpleChat:', error);
      setLastError(error);
      return;
    }

    if (isProcessing) {
      const error = 'Already processing a message. Please wait.';
      console.log('useSimpleChat:', error);
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
      setLastError(errorMessage);
    }
  }, [user, isProcessing]);

  const clearError = useCallback(() => {
    setLastError(null);
    if (errorTimeoutRef.current) {
      clearTimeout(errorTimeoutRef.current);
      errorTimeoutRef.current = null;
    }
  }, []);

  // Check if the hook is ready to send messages
  const isReady = useCallback(() => {
    const userId = extractUserId(user);
    return !!userId && !!handlerRef.current && !isProcessing;
  }, [user, isProcessing]);

  return {
    sendQuestion,
    isProcessing,
    lastMessage,
    lastError,
    clearError,
    isReady: isReady()
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