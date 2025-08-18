import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { vi, describe, it, expect, beforeEach } from 'vitest';
import { FeedbackForm } from '../feedback-form';

describe('FeedbackForm', () => {
  const mockProps = {
    messageId: 'msg-123',
    conversationId: 'conv-456',
    feedbackType: 'rating' as const,
    onSubmit: vi.fn(),
    onCancel: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders rating stars for rating feedback type', () => {
    render(<FeedbackForm {...mockProps} />);
    
    expect(screen.getByText('평점을 선택해주세요')).toBeInTheDocument();
    expect(screen.getByText('5/5')).toBeInTheDocument();
    
    // Should have 5 star buttons
    const stars = screen.getAllByText('⭐');
    expect(stars).toHaveLength(5);
  });

  it('does not render rating stars for non-rating feedback type', () => {
    render(<FeedbackForm {...mockProps} feedbackType="helpful" />);
    
    expect(screen.queryByText('평점을 선택해주세요')).not.toBeInTheDocument();
  });

  it('renders comments textarea', () => {
    render(<FeedbackForm {...mockProps} />);
    
    expect(screen.getByLabelText('추가 의견 (선택사항)')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('응답에 대한 의견을 자유롭게 작성해주세요...')).toBeInTheDocument();
  });

  it('updates rating when star is clicked', () => {
    render(<FeedbackForm {...mockProps} />);
    
    const stars = screen.getAllByText('⭐');
    fireEvent.click(stars[2]); // Click 3rd star (rating 3)
    
    expect(screen.getByText('3/5')).toBeInTheDocument();
  });

  it('updates comments when textarea is changed', () => {
    render(<FeedbackForm {...mockProps} />);
    
    const textarea = screen.getByLabelText('추가 의견 (선택사항)');
    fireEvent.change(textarea, { target: { value: 'Test comment' } });
    
    expect(textarea).toHaveValue('Test comment');
    expect(screen.getByText('12/500')).toBeInTheDocument();
  });

  it('validates rating range', async () => {
    render(<FeedbackForm {...mockProps} />);
    
    // Try to submit with default rating (should be valid)
    const submitButton = screen.getByText('피드백 제출');
    fireEvent.click(submitButton);
    
    // Should call onSubmit with valid rating
    await waitFor(() => {
      expect(mockProps.onSubmit).toHaveBeenCalledWith({
        conversation_id: 'conv-456',
        message_id: 'msg-123',
        feedback_type: 'rating',
        rating: 5,
        comments: undefined,
      });
    });
  });

  it('validates comments length', async () => {
    render(<FeedbackForm {...mockProps} />);
    
    const textarea = screen.getByLabelText('추가 의견 (선택사항)');
    const longComment = 'a'.repeat(501); // Exceed 500 character limit
    
    fireEvent.change(textarea, { target: { value: longComment } });
    
    const submitButton = screen.getByText('피드백 제출');
    fireEvent.click(submitButton);
    
    await waitFor(() => {
      expect(screen.getByText('의견은 500자 이하로 입력해주세요.')).toBeInTheDocument();
    });
    
    expect(mockProps.onSubmit).not.toHaveBeenCalled();
  });

  it('submits feedback with correct data', async () => {
    render(<FeedbackForm {...mockProps} />);
    
    // Set rating to 4
    const stars = screen.getAllByText('⭐');
    fireEvent.click(stars[3]);
    
    // Add comment
    const textarea = screen.getByLabelText('추가 의견 (선택사항)');
    fireEvent.change(textarea, { target: { value: 'Great response!' } });
    
    // Submit form
    fireEvent.click(screen.getByText('피드백 제출'));
    
    await waitFor(() => {
      expect(mockProps.onSubmit).toHaveBeenCalledWith({
        conversation_id: 'conv-456',
        message_id: 'msg-123',
        feedback_type: 'rating',
        rating: 4,
        comments: 'Great response!',
      });
    });
  });

  it('submits feedback without optional fields', async () => {
    render(<FeedbackForm {...mockProps} feedbackType="helpful" />);
    
    fireEvent.click(screen.getByText('피드백 제출'));
    
    await waitFor(() => {
      expect(mockProps.onSubmit).toHaveBeenCalledWith({
        conversation_id: 'conv-456',
        message_id: 'msg-123',
        feedback_type: 'helpful',
        rating: undefined,
        comments: undefined,
      });
    });
  });

  it('calls onCancel when cancel button is clicked', () => {
    render(<FeedbackForm {...mockProps} />);
    
    fireEvent.click(screen.getByText('취소'));
    
    expect(mockProps.onCancel).toHaveBeenCalled();
  });

  it('handles form submission correctly', async () => {
    render(<FeedbackForm {...mockProps} />);
    
    const submitButton = screen.getByText('피드백 제출');
    const cancelButton = screen.getByText('취소');
    
    // Initially buttons should be enabled
    expect(submitButton).not.toBeDisabled();
    expect(cancelButton).not.toBeDisabled();
    
    fireEvent.click(submitButton);
    
    // Should call onSubmit
    await waitFor(() => {
      expect(mockProps.onSubmit).toHaveBeenCalled();
    });
  });

  it('shows character count for comments', () => {
    render(<FeedbackForm {...mockProps} />);
    
    const textarea = screen.getByLabelText('추가 의견 (선택사항)');
    fireEvent.change(textarea, { target: { value: 'Hello' } });
    
    expect(screen.getByText('5/500')).toBeInTheDocument();
  });
});