import { useEffect, useState, useCallback, useRef } from 'react';
import { useAuth } from '@/providers/auth-provider';
import { 
  WebSocketClient, 
  WebSocketState, 
  WebSocketMessage, 
  getWebSocketClient, 
  resetWebSocketClient 
} from '@/lib/websocket';
import { 
  WebSocketMessageHandler, 
  RateLimitConfig, 
  MessageHandler 
} from '@/lib/websocket-handlers';
import { 
  EnhancedChatHandler, 
  ChatFallbackConfig 
} from '@/lib/chat-fallback';

export function useWebSocket() {
  const { user, getToken } = useAuth();
  const [state, setState] = useState<WebSocketState>({
    status: 'disconnected',
    reconnectAttempts: 0,
  });
  const clientRef = useRef<WebSocketClient | null>(null);

  const connect = useCallback(async () => {
    if (!user?.id) {
      console.warn('Cannot connect WebSocket: No user ID');
      return;
    }

    try {
      const token = await getToken();
      const client = getWebSocketClient(user.id);
      clientRef.current = client;

      // Subscribe to state changes
      const unsubscribeState = client.subscribeToState(setState);

      // Connect with token
      client.connect(token);

      // Cleanup function
      return () => {
        unsubscribeState();
      };
    } catch (error) {
      console.error('Failed to connect WebSocket:', error);
      setState({
        status: 'error',
        lastError: 'Failed to initialize connection',
        reconnectAttempts: 0,
      });
    }
  }, [user?.id, getToken]);

  const disconnect = useCallback(() => {
    if (clientRef.current) {
      clientRef.current.disconnect();
    }
  }, []);

  const send = useCallback((message: WebSocketMessage) => {
    if (clientRef.current) {
      clientRef.current.send(message);
    } else {
      console.warn('Cannot send message: WebSocket not connected');
    }
  }, []);

  // Auto-connect when user is available
  useEffect(() => {
    if (user?.id) {
      const cleanup = connect();
      return () => {
        cleanup?.then(fn => fn?.());
      };
    } else {
      // Reset client when user logs out
      resetWebSocketClient();
      setState({
        status: 'disconnected',
        reconnectAttempts: 0,
      });
    }
  }, [user?.id, connect]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      disconnect();
    };
  }, [disconnect]);

  // Debug WebSocket state
  useEffect(() => {
    console.log('WebSocket state changed:', {
      status: state.status,
      isConnected: state.status === 'connected',
      reconnectAttempts: state.reconnectAttempts,
      lastError: state.lastError
    });
  }, [state]);

  return {
    state,
    connect,
    disconnect,
    send,
    isConnected: state.status === 'connected',
    isConnecting: state.status === 'connecting',
    isDisconnected: state.status === 'disconnected',
    hasError: state.status === 'error',
  };
}

export function useWebSocketSubscription<T = any>(
  eventType: string,
  handler: (message: WebSocketMessage) => void,
  deps: React.DependencyList = []
) {
  const { user } = useAuth();
  const handlerRef = useRef(handler);

  // Update handler ref when it changes
  useEffect(() => {
    handlerRef.current = handler;
  }, [handler]);

  useEffect(() => {
    if (!user?.id) return;

    try {
      const client = getWebSocketClient(user.id);
      
      // Wrap handler to use current ref
      const wrappedHandler = (message: WebSocketMessage) => {
        handlerRef.current(message);
      };

      const unsubscribe = client.subscribe(eventType, wrappedHandler);
      return unsubscribe;
    } catch (error) {
      console.error('Failed to subscribe to WebSocket events:', error);
    }
  }, [eventType, user?.id, ...deps]);
}

export function useWebSocketChat(
  rateLimitConfig?: RateLimitConfig,
  fallbackConfig?: ChatFallbackConfig
) {
  const { send, state, isConnected } = useWebSocket();
  const { user } = useAuth();
  const [isProcessing, setIsProcessing] = useState(false);
  const [lastResponse, setLastResponse] = useState<any>(null);
  const [lastError, setLastError] = useState<string | null>(null);
  const [rateLimitStatus, setRateLimitStatus] = useState({
    canSendMessage: true,
    remainingMessages: 10,
    timeUntilNextMessage: 0,
  });
  const [usedFallback, setUsedFallback] = useState(false);

  // Message handler and enhanced chat handler refs
  const messageHandlerRef = useRef<WebSocketMessageHandler | null>(null);
  const chatHandlerRef = useRef<EnhancedChatHandler | null>(null);

  // Initialize message handler
  useEffect(() => {
    const onRateLimitExceeded = (timeUntilNext: number) => {
      setLastError(`Rate limit exceeded. Please wait ${Math.ceil(timeUntilNext / 1000)} seconds.`);
      setRateLimitStatus(prev => ({
        ...prev,
        canSendMessage: false,
        timeUntilNextMessage: timeUntilNext,
      }));
    };

    messageHandlerRef.current = new WebSocketMessageHandler(
      rateLimitConfig,
      onRateLimitExceeded
    );

    chatHandlerRef.current = new EnhancedChatHandler(fallbackConfig, {
      onMessage: (message) => {
        console.log('useWebSocketChat: onMessage called with:', message);
        if (message.type === 'response') {
          console.log('useWebSocketChat: Setting lastResponse to:', message.data);
          setLastResponse(message.data);
          setIsProcessing(false);
          setLastError(null);
        }
      },
      onError: (error) => {
        setLastError(error);
        setIsProcessing(false);
      },
      onFallbackUsed: (reason) => {
        setUsedFallback(true);
        console.log('Using HTTP fallback:', reason);
      },
    });

    return () => {
      messageHandlerRef.current?.clearHandlers();
    };
  }, [rateLimitConfig, fallbackConfig]);

  // Handle WebSocket connection status changes
  useEffect(() => {
    if (chatHandlerRef.current) {
      chatHandlerRef.current.onWebSocketStatusChange(isConnected);
    }
    
    // Automatically enable fallback when WebSocket is not connected
    if (!isConnected && state.status !== 'connecting') {
      setUsedFallback(true);
      console.log('WebSocket not connected, enabling fallback mode');
    } else if (isConnected) {
      setUsedFallback(false);
      console.log('WebSocket connected, disabling fallback mode');
    }
  }, [isConnected, state.status]);

  // Handle status messages
  useWebSocketSubscription('status', (message) => {
    const { status } = message.data;
    setIsProcessing(status === 'processing' || status === 'generating');
  });

  // Handle response messages
  useWebSocketSubscription('response', (message) => {
    setLastResponse(message.data);
    setIsProcessing(false);
    setLastError(null);
    setUsedFallback(false);
  });

  // Handle error messages
  useWebSocketSubscription('error', (message) => {
    setLastError(message.data.message);
    setIsProcessing(false);
  });

  // Update rate limit status periodically
  useEffect(() => {
    const updateRateLimit = () => {
      if (messageHandlerRef.current) {
        const status = messageHandlerRef.current.getRateLimitStatus();
        setRateLimitStatus(status);
      }
    };

    const interval = setInterval(updateRateLimit, 1000);
    return () => clearInterval(interval);
  }, []);

  const sendQuestion = useCallback(async (question: string, conversationId?: string) => {
    // Get user ID from either id or user_id field (for backward compatibility)
    const userId = user?.id || (user as any)?.user_id;
    
    console.log('useWebSocketChat.sendQuestion called:', {
      question: question.substring(0, 50) + '...',
      conversationId,
      userId,
      userObject: user,
      hasChatHandler: !!chatHandlerRef.current,
      hasMessageHandler: !!messageHandlerRef.current
    });

    if (!question.trim()) {
      console.log('Question is empty, setting error');
      setLastError('Question cannot be empty');
      return;
    }

    const rateLimitStatus = messageHandlerRef.current?.getRateLimitStatus();
    console.log('Rate limit status:', rateLimitStatus);

    if (!rateLimitStatus?.canSendMessage) {
      const timeUntil = rateLimitStatus?.timeUntilNextMessage || 0;
      console.log('Rate limit exceeded, timeUntil:', timeUntil);
      setLastError(`Rate limit exceeded. Please wait ${Math.ceil(timeUntil / 1000)} seconds.`);
      return;
    }

    console.log('Setting processing state to true');
    setIsProcessing(true);
    setLastError(null);
    // Don't reset usedFallback here - let the connection status handle it

    try {
      if (chatHandlerRef.current) {
        console.log('Calling chatHandlerRef.current.sendQuestion');
        await chatHandlerRef.current.sendQuestion(
          question.trim(),
          conversationId,
          userId,
          send
        );
        console.log('chatHandlerRef.current.sendQuestion completed');
      } else {
        console.error('chatHandlerRef.current is null');
        setLastError('Chat handler not initialized');
        setIsProcessing(false);
      }
    } catch (error: any) {
      console.error('Error in sendQuestion:', error);
      setLastError(error.message || 'Failed to send question');
      setIsProcessing(false);
    }
  }, [send, user]);

  const forceFallback = useCallback(() => {
    if (chatHandlerRef.current) {
      chatHandlerRef.current.forceFallback();
    }
  }, []);

  const disableFallback = useCallback(() => {
    if (chatHandlerRef.current) {
      chatHandlerRef.current.disableFallback();
    }
  }, []);

  return {
    sendQuestion,
    isProcessing,
    lastResponse,
    lastError,
    connectionState: state,
    isConnected,
    rateLimitStatus,
    usedFallback,
    fallbackStatus: chatHandlerRef.current?.getStatus(),
    forceFallback,
    disableFallback,
  };
}

export function useWebSocketETL() {
  const { user } = useAuth();
  const [jobUpdates, setJobUpdates] = useState<Map<string, any>>(new Map());

  // Handle ETL job updates
  useWebSocketSubscription('etl_update', (message) => {
    const { job_id, ...jobData } = message.data;
    setJobUpdates(prev => new Map(prev.set(job_id, jobData)));
  });

  const getJobUpdate = useCallback((jobId: string) => {
    return jobUpdates.get(jobId);
  }, [jobUpdates]);

  const clearJobUpdate = useCallback((jobId: string) => {
    setJobUpdates(prev => {
      const newMap = new Map(prev);
      newMap.delete(jobId);
      return newMap;
    });
  }, []);

  return {
    jobUpdates,
    getJobUpdate,
    clearJobUpdate,
  };
}