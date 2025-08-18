'use client';

import React, { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Modal } from '@/components/ui/modal';
import { ChatFeedback } from '@/lib/types';
import { FeedbackForm } from './feedback-form';
import { cn } from '@/lib/utils';

interface FeedbackButtonsProps {
  messageId: string;
  conversationId: string;
  onFeedbackSubmitted?: (feedback: ChatFeedback) => void;
  className?: string;
}

export function FeedbackButtons({ 
  messageId, 
  conversationId, 
  onFeedbackSubmitted,
  className 
}: FeedbackButtonsProps) {
  const [showFeedbackModal, setShowFeedbackModal] = useState(false);
  const [feedbackType, setFeedbackType] = useState<'helpful' | 'not_helpful' | 'rating'>('helpful');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleQuickFeedback = async (type: 'helpful' | 'not_helpful') => {
    setIsSubmitting(true);
    try {
      const feedback: ChatFeedback = {
        conversation_id: conversationId,
        message_id: messageId,
        feedback_type: type,
      };
      
      onFeedbackSubmitted?.(feedback);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDetailedFeedback = (type: 'rating') => {
    setFeedbackType(type);
    setShowFeedbackModal(true);
  };

  const handleFeedbackFormSubmit = (feedback: ChatFeedback) => {
    onFeedbackSubmitted?.(feedback);
    setShowFeedbackModal(false);
  };

  return (
    <>
      <div className={cn('flex items-center gap-2 mt-2', className)}>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => handleQuickFeedback('helpful')}
          disabled={isSubmitting}
          className="text-xs text-gray-600 hover:text-green-600 hover:bg-green-50"
          data-testid="feedback-helpful"
        >
          👍 도움됨
        </Button>
        
        <Button
          variant="ghost"
          size="sm"
          onClick={() => handleQuickFeedback('not_helpful')}
          disabled={isSubmitting}
          className="text-xs text-gray-600 hover:text-red-600 hover:bg-red-50"
          data-testid="feedback-not-helpful"
        >
          👎 도움안됨
        </Button>
        
        <Button
          variant="ghost"
          size="sm"
          onClick={() => handleDetailedFeedback('rating')}
          disabled={isSubmitting}
          className="text-xs text-gray-600 hover:text-blue-600 hover:bg-blue-50"
          data-testid="feedback-detailed"
        >
          ⭐ 평가하기
        </Button>
      </div>

      {showFeedbackModal && (
        <Modal
          isOpen={showFeedbackModal}
          onClose={() => setShowFeedbackModal(false)}
          title="응답 평가"
        >
          <FeedbackForm
            messageId={messageId}
            conversationId={conversationId}
            feedbackType={feedbackType}
            onSubmit={handleFeedbackFormSubmit}
            onCancel={() => setShowFeedbackModal(false)}
          />
        </Modal>
      )}
    </>
  );
}