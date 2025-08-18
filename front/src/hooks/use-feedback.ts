'use client';

import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { ChatFeedback, ChatFeedbackResponse } from '@/lib/types';
import ApiClient from '@/lib/api';

interface UseFeedbackOptions {
  onSuccess?: (response: ChatFeedbackResponse) => void;
  onError?: (error: Error) => void;
}

export function useFeedback(options: UseFeedbackOptions = {}) {
  const [submittedFeedback, setSubmittedFeedback] = useState<Set<string>>(new Set());

  const feedbackMutation = useMutation({
    mutationFn: (feedback: ChatFeedback) => ApiClient.submitFeedback(feedback),
    onSuccess: (response, variables) => {
      // Mark this message as having feedback submitted
      setSubmittedFeedback(prev => new Set(prev).add(variables.message_id));
      options.onSuccess?.(response);
    },
    onError: options.onError,
  });

  const submitFeedback = (feedback: ChatFeedback) => {
    feedbackMutation.mutate(feedback);
  };

  const hasFeedback = (messageId: string) => {
    return submittedFeedback.has(messageId);
  };

  return {
    submitFeedback,
    hasFeedback,
    isSubmitting: feedbackMutation.isPending,
    error: feedbackMutation.error,
    isSuccess: feedbackMutation.isSuccess,
  };
}