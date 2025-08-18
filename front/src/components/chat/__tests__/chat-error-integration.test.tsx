import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { ChatContainer } from '../chat-container-improved';
import { AuthProvider } from '@/providers/auth-provider';
import { ApiClient } from '@/lib/api';

// Mock the API client
vi.mock('@/lib/api', () => ({
  ApiClient: {
    sendQuestion: vi.fn()
  }
}));

// Mock auth provider
const mockUser = {
  id: 'test-user-123',
  name: 'Test User',
  email: 'test@example.com'
};

const MockAuthProvider = ({ children }: { children: React.ReactNode }) => {
  return (
    <AuthProvider value={{
      user: mockUser,
      isAuthenticated: true,
      isLoading: false,
      login: vi.fn(),
      logout: vi.fn(),
      refreshToken: vi.fn()
    }}>
      {children}
    </AuthProvider>
  );
};

describe('Chat Error Integration', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should display network error when API call fails', async () => {
    // Mock API to throw network error
    const mockSendQuestion = vi.mocked(ApiClient.sendQuestion);
    mockSendQuestion.mockRejectedValue(new Error('Failed to fetch'));

    render(
      <MockAuthProvider>
        <ChatContainer 
          userHasDocuments={true}
          debugMode={false}
        />
      </MockAuthProvider>
    );

    // Find and fill the chat input
    const chatInput = screen.getByPlaceholderText(/적성 분석에 대해 궁금한 것을 물어보세요/);
    fireEvent.change(chatInput, { target: { value: 'Test question' } });

    // Submit the message
    const sendButton = screen.getByRole('button', { name: /send/i }) || 
                      screen.getByRole('button', { name: /전송/i });
    if (sendButton) {
      fireEvent.click(sendButton);
    } else {
      // Try pressing Enter
      fireEvent.keyDown(chatInput, { key: 'Enter', code: 'Enter' });
    }

    // Wait for error to appear
    await waitFor(() => {
      expect(screen.getByTestId('error-display')).toBeInTheDocument();
    }, { timeout: 3000 });

    // Check error message
    expect(screen.getByText(/네트워크 연결에 문제가 있습니다/)).toBeInTheDocument();
    expect(screen.getByText('다시 시도')).toBeInTheDocument();
  });

  it('should display authentication error when user is not authenticated', async () => {
    // Mock API to throw auth error
    const mockSendQuestion = vi.mocked(ApiClient.sendQuestion);
    const authError = new Error('Unauthorized');
    (authError as any).status = 401;
    (authError as any).type = 'auth_error';
    mockSendQuestion.mockRejectedValue(authError);

    render(
      <MockAuthProvider>
        <ChatContainer 
          userHasDocuments={true}
          debugMode={false}
        />
      </MockAuthProvider>
    );

    // Find and fill the chat input
    const chatInput = screen.getByPlaceholderText(/적성 분석에 대해 궁금한 것을 물어보세요/);
    fireEvent.change(chatInput, { target: { value: 'Test question' } });

    // Submit the message
    fireEvent.keyDown(chatInput, { key: 'Enter', code: 'Enter' });

    // Wait for error to appear
    await waitFor(() => {
      expect(screen.getByTestId('error-display')).toBeInTheDocument();
    }, { timeout: 3000 });

    // Check error message
    expect(screen.getByText(/로그인이 필요하거나 세션이 만료/)).toBeInTheDocument();
    expect(screen.getByText('로그인하기')).toBeInTheDocument();
  });

  it('should display server error when API returns 500', async () => {
    // Mock API to throw server error
    const mockSendQuestion = vi.mocked(ApiClient.sendQuestion);
    const serverError = new Error('Internal Server Error');
    (serverError as any).status = 500;
    (serverError as any).type = 'server_error';
    mockSendQuestion.mkRejectedValue(serverError);

    render(
      <MockAuthProvider>
        <ChatContainer 
          userHasDocuments={true}
          debugMode={false}
        />
      </MockAuthProvider>
    );

    // Find and fill the chat input
    const chatInput = screen.getByPlaceholderText(/적성 분석에 대해 궁금한 것을 물어보세요/);
    fireEvent.change(chatInput, { target: { value: 'Test question' } });

    // Submit the message
    fireEvent.keyDown(chatInput, { key: 'Enter', code: 'Enter' });

    // Wait for error to appear
    await waitFor(() => {
      expect(screen.getByTestId('error-display')).toBeInTheDocument();
    }, { timeout: 3000 });

    // Check error message
    expect(screen.getByText(/서버에 일시적인 문제가 발생했습니다/)).toBeInTheDocument();
    expect(screen.getByText('다시 시도')).toBeInTheDocument();
  });

  it('should handle retry functionality', async () => {
    // Mock API to fail first, then succeed
    const mockSendQuestion = vi.mocked(ApiClient.sendQuestion);
    mockSendQuestion
      .mockRejectedValueOnce(new Error('Failed to fetch'))
      .mockResolvedValueOnce({
        response: 'Test response',
        conversation_id: 'test-conv-123',
        confidence_score: 0.9,
        processing_time: 1.5,
        retrieved_documents: [],
        timestamp: new Date().toISOString()
      });

    render(
      <MockAuthProvider>
        <ChatContainer 
          userHasDocuments={true}
          debugMode={false}
        />
      </MockAuthProvider>
    );

    // Send a message that will fail
    const chatInput = screen.getByPlaceholderText(/적성 분석에 대해 궁금한 것을 물어보세요/);
    fireEvent.change(chatInput, { target: { value: 'Test question' } });
    fireEvent.keyDown(chatInput, { key: 'Enter', code: 'Enter' });

    // Wait for error to appear
    await waitFor(() => {
      expect(screen.getByTestId('error-display')).toBeInTheDocument();
    });

    // Click retry button
    const retryButton = screen.getByText('다시 시도');
    fireEvent.click(retryButton);

    // Wait for success (error should disappear)
    await waitFor(() => {
      expect(screen.queryByTestId('error-display')).not.toBeInTheDocument();
    }, { timeout: 3000 });

    // Should see the response message
    expect(screen.getByText('Test response')).toBeInTheDocument();
  });

  it('should dismiss error when dismiss button is clicked', async () => {
    // Mock API to throw error
    const mockSendQuestion = vi.mocked(ApiClient.sendQuestion);
    mockSendQuestion.mockRejectedValue(new Error('Failed to fetch'));

    render(
      <MockAuthProvider>
        <ChatContainer 
          userHasDocuments={true}
          debugMode={false}
        />
      </MockAuthProvider>
    );

    // Send a message that will fail
    const chatInput = screen.getByPlaceholderText(/적성 분석에 대해 궁금한 것을 물어보세요/);
    fireEvent.change(chatInput, { target: { value: 'Test question' } });
    fireEvent.keyDown(chatInput, { key: 'Enter', code: 'Enter' });

    // Wait for error to appear
    await waitFor(() => {
      expect(screen.getByTestId('error-display')).toBeInTheDocument();
    });

    // Click dismiss button (X button or 닫기 button)
    const dismissButton = screen.getByText('닫기') || screen.getByLabelText(/닫기/);
    fireEvent.click(dismissButton);

    // Error should disappear
    await waitFor(() => {
      expect(screen.queryByTestId('error-display')).not.toBeInTheDocument();
    });
  });
});