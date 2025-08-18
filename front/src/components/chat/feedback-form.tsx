'use client';

import React, { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { ChatFeedback } from '@/lib/types';
import { cn } from '@/lib/utils';

interface FeedbackFormProps {
  messageId: string;
  conversationId: string;
  feedbackType: 'helpful' | 'not_helpful' | 'rating';
  onSubmit: (feedback: ChatFeedback) => void;
  onCancel: () => void;
}

export function FeedbackForm({
  messageId,
  conversationId,
  feedbackType,
  onSubmit,
  onCancel,
}: FeedbackFormProps) {
  const [rating, setRating] = useState<number>(5);
  const [comments, setComments] = useState<string>('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});

  const validateForm = (): boolean => {
    const newErrors: Record<string, string> = {};

    if (feedbackType === 'rating' && (rating < 1 || rating > 5)) {
      newErrors.rating = '평점은 1-5 사이의 값이어야 합니다.';
    }

    if (comments.length > 500) {
      newErrors.comments = '의견은 500자 이하로 입력해주세요.';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!validateForm()) {
      return;
    }

    setIsSubmitting(true);
    
    try {
      const feedback: ChatFeedback = {
        conversation_id: conversationId,
        message_id: messageId,
        feedback_type: feedbackType,
        rating: feedbackType === 'rating' ? rating : undefined,
        comments: comments.trim() || undefined,
      };

      onSubmit(feedback);
    } catch (error) {
      console.error('Failed to submit feedback:', error);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleRatingClick = (value: number) => {
    setRating(value);
    setErrors(prev => ({ ...prev, rating: '' }));
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {feedbackType === 'rating' && (
        <div className="space-y-2">
          <label className="block text-sm font-medium text-gray-700">
            평점을 선택해주세요
          </label>
          <div className="flex items-center gap-1">
            {[1, 2, 3, 4, 5].map((value) => (
              <button
                key={value}
                type="button"
                onClick={() => handleRatingClick(value)}
                className={cn(
                  'text-2xl transition-colors hover:scale-110',
                  value <= rating ? 'text-yellow-400' : 'text-gray-300'
                )}
              >
                ⭐
              </button>
            ))}
            <span className="ml-2 text-sm text-gray-600">
              {rating}/5
            </span>
          </div>
          {errors.rating && (
            <p className="text-sm text-red-600">{errors.rating}</p>
          )}
        </div>
      )}

      <div className="space-y-2">
        <label htmlFor="comments" className="block text-sm font-medium text-gray-700">
          추가 의견 (선택사항)
        </label>
        <textarea
          id="comments"
          value={comments}
          onChange={(e) => {
            setComments(e.target.value);
            setErrors(prev => ({ ...prev, comments: '' }));
          }}
          placeholder="응답에 대한 의견을 자유롭게 작성해주세요..."
          className={cn(
            'w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm',
            'focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
            'resize-none',
            errors.comments && 'border-red-500 focus:ring-red-500 focus:border-red-500'
          )}
          rows={4}
          maxLength={500}
        />
        <div className="flex justify-between text-xs text-gray-500">
          <span>{comments.length}/500</span>
          {errors.comments && (
            <span className="text-red-600">{errors.comments}</span>
          )}
        </div>
      </div>

      <div className="flex justify-end gap-3 pt-4">
        <Button
          type="button"
          variant="outline"
          onClick={onCancel}
          disabled={isSubmitting}
        >
          취소
        </Button>
        <Button
          type="submit"
          disabled={isSubmitting}
          className="bg-blue-600 hover:bg-blue-700"
        >
          {isSubmitting ? '제출 중...' : '피드백 제출'}
        </Button>
      </div>
    </form>
  );
}