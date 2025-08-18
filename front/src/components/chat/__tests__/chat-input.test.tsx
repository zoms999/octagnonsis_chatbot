import React from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { vi, describe, it, beforeEach, expect } from 'vitest';
import { ChatInput } from '../chat-input';

describe('ChatInput', () => {
  const mockOnSendMessage = vi.fn();
  const defaultRateLimitStatus = {
    canSendMessage: true,
    remainingMessages: 10,
    timeUntilNextMessage: 0,
  };

  beforeEach(() => {
    mockOnSendMessage.mockClear();
  });

  it('renders input field and send button', () => {
    render(
      <ChatInput 
        onSendMessage={mockOnSendMessage}
        rateLimitStatus={defaultRateLimitStatus}
      />
    );
    
    expect(screen.getByPlaceholderText(/적성 분석에 대해 궁금한 것을/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '전송' })).toBeInTheDocument();
  });

  it('calls onSendMessage when form is submitted', async () => {
    const user = userEvent.setup();
    
    render(
      <ChatInput 
        onSendMessage={mockOnSendMessage}
        rateLimitStatus={defaultRateLimitStatus}
      />
    );
    
    const input = screen.getByRole('textbox');
    const sendButton = screen.getByRole('button', { name: '전송' });
    
    await user.type(input, 'Test message');
    await user.click(sendButton);
    
    expect(mockOnSendMessage).toHaveBeenCalledWith('Test message');
  });

  it('submits message on Enter key press', async () => {
    const user = userEvent.setup();
    
    render(
      <ChatInput 
        onSendMessage={mockOnSendMessage}
        rateLimitStatus={defaultRateLimitStatus}
      />
    );
    
    const input = screen.getByRole('textbox');
    
    await user.type(input, 'Test message');
    await user.keyboard('{Enter}');
    
    expect(mockOnSendMessage).toHaveBeenCalledWith('Test message');
  });

  it('does not submit on Shift+Enter', async () => {
    const user = userEvent.setup();
    
    render(
      <ChatInput 
        onSendMessage={mockOnSendMessage}
        rateLimitStatus={defaultRateLimitStatus}
      />
    );
    
    const input = screen.getByRole('textbox');
    
    await user.type(input, 'Test message');
    await user.keyboard('{Shift>}{Enter}{/Shift}');
    
    expect(mockOnSendMessage).not.toHaveBeenCalled();
  });

  it('clears input after sending message', async () => {
    const user = userEvent.setup();
    
    render(
      <ChatInput 
        onSendMessage={mockOnSendMessage}
        rateLimitStatus={defaultRateLimitStatus}
      />
    );
    
    const input = screen.getByRole('textbox') as HTMLTextAreaElement;
    const sendButton = screen.getByRole('button', { name: '전송' });
    
    await user.type(input, 'Test message');
    await user.click(sendButton);
    
    expect(input.value).toBe('');
  });

  it('disables input when disabled prop is true', () => {
    render(
      <ChatInput 
        onSendMessage={mockOnSendMessage}
        disabled={true}
        rateLimitStatus={defaultRateLimitStatus}
      />
    );
    
    const input = screen.getByRole('textbox');
    const sendButton = screen.getByRole('button', { name: '전송' });
    
    expect(input).toBeDisabled();
    expect(sendButton).toBeDisabled();
  });

  it('disables input when processing', () => {
    render(
      <ChatInput 
        onSendMessage={mockOnSendMessage}
        isProcessing={true}
        rateLimitStatus={defaultRateLimitStatus}
      />
    );
    
    const input = screen.getByRole('textbox');
    const sendButton = screen.getByRole('button');
    
    expect(input).toBeDisabled();
    expect(sendButton).toBeDisabled();
    expect(screen.getByText('전송중')).toBeInTheDocument();
  });

  it('shows rate limit warning when rate limited', () => {
    const rateLimitedStatus = {
      canSendMessage: false,
      remainingMessages: 0,
      timeUntilNextMessage: 30000, // 30 seconds
    };
    
    render(
      <ChatInput 
        onSendMessage={mockOnSendMessage}
        rateLimitStatus={rateLimitedStatus}
      />
    );
    
    expect(screen.getByText('메시지 전송 제한에 도달했습니다.')).toBeInTheDocument();
    expect(screen.getByText(/30초 후에 다시 시도해주세요/)).toBeInTheDocument();
  });

  it('shows character count', async () => {
    const user = userEvent.setup();
    
    render(
      <ChatInput 
        onSendMessage={mockOnSendMessage}
        maxLength={100}
        rateLimitStatus={defaultRateLimitStatus}
      />
    );
    
    const input = screen.getByRole('textbox');
    
    await user.type(input, 'Hello');
    
    expect(screen.getByText('95')).toBeInTheDocument(); // 100 - 5 = 95
  });

  it('shows remaining messages count', () => {
    render(
      <ChatInput 
        onSendMessage={mockOnSendMessage}
        rateLimitStatus={defaultRateLimitStatus}
      />
    );
    
    expect(screen.getByText('남은 메시지: 10개')).toBeInTheDocument();
  });

  it('does not submit empty or whitespace-only messages', async () => {
    const user = userEvent.setup();
    
    render(
      <ChatInput 
        onSendMessage={mockOnSendMessage}
        rateLimitStatus={defaultRateLimitStatus}
      />
    );
    
    const sendButton = screen.getByRole('button', { name: '전송' });
    
    // Try to submit empty message
    await user.click(sendButton);
    expect(mockOnSendMessage).not.toHaveBeenCalled();
    
    // Try to submit whitespace-only message
    const input = screen.getByRole('textbox');
    await user.type(input, '   ');
    await user.click(sendButton);
    expect(mockOnSendMessage).not.toHaveBeenCalled();
  });

  it('trims whitespace from messages', async () => {
    const user = userEvent.setup();
    
    render(
      <ChatInput 
        onSendMessage={mockOnSendMessage}
        rateLimitStatus={defaultRateLimitStatus}
      />
    );
    
    const input = screen.getByRole('textbox');
    const sendButton = screen.getByRole('button', { name: '전송' });
    
    await user.type(input, '  Test message  ');
    await user.click(sendButton);
    
    expect(mockOnSendMessage).toHaveBeenCalledWith('Test message');
  });

  it('applies custom className', () => {
    const { container } = render(
      <ChatInput 
        onSendMessage={mockOnSendMessage}
        rateLimitStatus={defaultRateLimitStatus}
        className="custom-class"
      />
    );
    
    expect(container.firstChild).toHaveClass('custom-class');
  });
});