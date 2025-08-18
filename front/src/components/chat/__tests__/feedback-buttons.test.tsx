import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { vi, describe, it, expect, beforeEach } from 'vitest';
import { FeedbackButtons } from '../feedback-buttons';
import { ChatFeedback } from '@/lib/types';

// Mock the Modal component
vi.mock('@/components/ui/modal', () => ({
  Modal: ({ children, isOpen, title }: any) => 
    isOpen ? (
      <div data-testid="modal">
        <h2>{title}</h2>
        {children}
      </div>
    ) : null,
}));

// Mock the FeedbackForm component
vi.mock('../feedback-form', () => ({
  FeedbackForm: ({ onSubmit, onCancel, feedbackType }: any) => (
    <div data-testid="feedback-form">
      <span>Feedback Type: {feedbackType}</span>
      <button onClick={() => onSubmit({ feedback_type: feedbackType })}>Submit</button>
      <button onClick={onCancel}>Cancel</button>
    </div>
  ),
}));

describe('FeedbackButtons', () => {
  const mockProps = {
    messageId: 'msg-123',
    conversationId: 'conv-456',
    onFeedbackSubmitted: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders all feedback buttons', () => {
    render(<FeedbackButtons {...mockProps} />);
    
    expect(screen.getByText('👍 도움됨')).toBeInTheDocument();
    expect(screen.getByText('👎 도움안됨')).toBeInTheDocument();
    expect(screen.getByText('⭐ 평가하기')).toBeInTheDocument();
  });

  it('calls onFeedbackSubmitted when helpful button is clicked', async () => {
    render(<FeedbackButtons {...mockProps} />);
    
    fireEvent.click(screen.getByText('👍 도움됨'));
    
    await waitFor(() => {
      expect(mockProps.onFeedbackSubmitted).toHaveBeenCalledWith({
        conversation_id: 'conv-456',
        message_id: 'msg-123',
        feedback_type: 'helpful',
      });
    });
  });

  it('calls onFeedbackSubmitted when not helpful button is clicked', async () => {
    render(<FeedbackButtons {...mockProps} />);
    
    fireEvent.click(screen.getByText('👎 도움안됨'));
    
    await waitFor(() => {
      expect(mockProps.onFeedbackSubmitted).toHaveBeenCalledWith({
        conversation_id: 'conv-456',
        message_id: 'msg-123',
        feedback_type: 'not_helpful',
      });
    });
  });

  it('opens modal when rating button is clicked', () => {
    render(<FeedbackButtons {...mockProps} />);
    
    fireEvent.click(screen.getByText('⭐ 평가하기'));
    
    expect(screen.getByTestId('modal')).toBeInTheDocument();
    expect(screen.getByText('응답 평가')).toBeInTheDocument();
    expect(screen.getByTestId('feedback-form')).toBeInTheDocument();
  });

  it('closes modal when feedback form is cancelled', () => {
    render(<FeedbackButtons {...mockProps} />);
    
    // Open modal
    fireEvent.click(screen.getByText('⭐ 평가하기'));
    expect(screen.getByTestId('modal')).toBeInTheDocument();
    
    // Cancel form
    fireEvent.click(screen.getByText('Cancel'));
    expect(screen.queryByTestId('modal')).not.toBeInTheDocument();
  });

  it('submits feedback and closes modal when form is submitted', () => {
    render(<FeedbackButtons {...mockProps} />);
    
    // Open modal
    fireEvent.click(screen.getByText('⭐ 평가하기'));
    
    // Submit form
    fireEvent.click(screen.getByText('Submit'));
    
    expect(mockProps.onFeedbackSubmitted).toHaveBeenCalledWith({
      feedback_type: 'rating',
    });
    expect(screen.queryByTestId('modal')).not.toBeInTheDocument();
  });

  it('handles button interactions correctly', async () => {
    render(<FeedbackButtons {...mockProps} />);
    
    const helpfulButton = screen.getByText('👍 도움됨');
    const notHelpfulButton = screen.getByText('👎 도움안됨');
    const ratingButton = screen.getByText('⭐ 평가하기');
    
    // All buttons should be enabled initially
    expect(helpfulButton).not.toBeDisabled();
    expect(notHelpfulButton).not.toBeDisabled();
    expect(ratingButton).not.toBeDisabled();
    
    // Click helpful button
    fireEvent.click(helpfulButton);
    
    // Verify feedback was submitted
    await waitFor(() => {
      expect(mockProps.onFeedbackSubmitted).toHaveBeenCalledWith({
        conversation_id: 'conv-456',
        message_id: 'msg-123',
        feedback_type: 'helpful',
      });
    });
  });
});