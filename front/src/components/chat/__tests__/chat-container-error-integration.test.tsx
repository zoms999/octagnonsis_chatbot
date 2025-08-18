import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { ChatContainer } from '../chat-container-improved';

// Mock the auth provider
const mockUser = {
    id: 'test-user-123',
    name: 'Test User',
    email: 'test@example.com'
};

const mockAuthProvider = {
    user: mockUser,
    isAuthenticated: true,
    isLoading: false
};

vi.mock('@/providers/auth-provider', () => ({
    useAuth: () => mockAuthProvider
}));

// Mock the API client to simulate errors
vi.mock('@/lib/api', () => ({
    ApiClient: {
        sendQuestion: vi.fn()
    }
}));

// Mock the document panel hook
vi.mock('@/hooks/use-document-panel', () => ({
    useDocumentPanel: () => ({
        documents: [],
        isCollapsed: false,
        hasDocuments: false,
        toggleCollapsed: vi.fn(),
        updateDocuments: vi.fn(),
        isMobile: false
    })
}));

// Mock other components to focus on error handling
vi.mock('./chat-message-list', () => ({
    ChatMessageList: ({ messages }: { messages: any[] }) => (
        <div data-testid="message-list">
            {messages.length} messages
        </div>
    )
}));

vi.mock('./chat-input', () => ({
    ChatInput: ({ onSendMessage, disabled, placeholder }: any) => (
        <div data-testid="chat-input">
            <input
                data-testid="message-input"
                placeholder={placeholder}
                disabled={disabled}
                onChange={(e) => {
                    // Simulate sending message on Enter
                    if (e.target.value === 'test message') {
                        onSendMessage('test message');
                    }
                }}
            />
        </div>
    )
}));

vi.mock('./empty-state', () => ({
    EmptyState: () => <div data-testid="empty-state">Empty State</div>
}));

vi.mock('./processing-status', () => ({
    ProcessingStatus: ({ status }: { status: string }) => (
        <div data-testid="processing-status">{status}</div>
    )
}));

vi.mock('./document-reference-panel', () => ({
    DocumentReferencePanel: () => <div data-testid="document-panel">Document Panel</div>
}));

vi.mock('@/components/debug/chat-debug-panel', () => ({
    ChatDebugPanel: () => <div data-testid="debug-panel">Debug Panel</div>
}));

describe('ChatContainer Error Integration', () => {
    beforeEach(() => {
        vi.clearAllMocks();

        // Mock console methods
        vi.spyOn(console, 'error').mockImplementation(() => { });
        vi.spyOn(console, 'warn').mockImplementation(() => { });
        vi.spyOn(console, 'log').mockImplementation(() => { });
        vi.spyOn(console, 'group').mockImplementation(() => { });
        vi.spyOn(console, 'groupEnd').mockImplementation(() => { });
    });

    it('should display network error when API call fails', async () => {
        const { ApiClient } = await import('@/lib/api');

        // Mock network error
        (ApiClient.sendQuestion as any).mockRejectedValue(
            new Error('Failed to fetch')
        );

        render(
            <ChatContainer
                userHasDocuments={true}
                showDocumentPanel={false}
            />
        );

        // Simulate sending a message
        const input = screen.getByTestId('message-input');
        fireEvent.change(input, { target: { value: 'test message' } });

        // Should show error display
        await waitFor(() => {
            expect(screen.getByTestId('error-display')).toBeInTheDocument();
        });

        // Should show network error message
        expect(screen.getByText('연결 오류')).toBeInTheDocument();
        expect(screen.getByText(/네트워크 연결에 문제가 있습니다/)).toBeInTheDocument();
    });

    it('should display authentication error when user is not authenticated', async () => {
        const { ApiClient } = await import('@/lib/api');

        // Mock auth error
        const authError = new Error('Unauthorized');
        (authError as any).status = 401;
        (authError as any).type = 'auth_error';

        (ApiClient.sendQuestion as any).mockRejectedValue(authError);

        // Mock unauthenticated user
        mockAuthProvider.user = null;
        mockAuthProvider.isAuthenticated = false;

        render(
            <ChatContainer
                userHasDocuments={true}
                showDocumentPanel={false}
            />
        );

        // Simulate sending a message
        const input = screen.getByTestId('message-input');
        fireEvent.change(input, { target: { value: 'test message' } });

        // Should show error display
        await waitFor(() => {
            expect(screen.getByTestId('error-display')).toBeInTheDocument();
        });

        // Should show auth error message
        expect(screen.getByText('인증 오류')).toBeInTheDocument();
        expect(screen.getByText(/로그인이 필요하거나 세션이 만료/)).toBeInTheDocument();

        // Reset mock
        mockAuthProvider.user = mockUser;
        mockAuthProvider.isAuthenticated = true;
    });

    it('should display server error when API returns 500', async () => {
        const { ApiClient } = await import('@/lib/api');

        // Mock server error
        const serverError = new Error('Internal Server Error');
        (serverError as any).status = 500;
        (serverError as any).type = 'server_error';

        (ApiClient.sendQuestion as any).mockRejectedValue(serverError);

        render(
            <ChatContainer
                userHasDocuments={true}
                showDocumentPanel={false}
            />
        );

        // Simulate sending a message
        const input = screen.getByTestId('message-input');
        fireEvent.change(input, { target: { value: 'test message' } });

        // Should show error display
        await waitFor(() => {
            expect(screen.getByTestId('error-display')).toBeInTheDocument();
        });

        // Should show server error message
        expect(screen.getByText('서버 오류')).toBeInTheDocument();
        expect(screen.getByText(/서버에 일시적인 문제가 발생/)).toBeInTheDocument();
    });

    it('should handle retry functionality', async () => {
        const { ApiClient } = await import('@/lib/api');

        // Mock network error initially, then success
        (ApiClient.sendQuestion as any)
            .mockRejectedValueOnce(new Error('Failed to fetch'))
            .mockResolvedValueOnce({
                response: 'Test response',
                conversation_id: 'test-conv-123',
                confidence_score: 0.9,
                processing_time: 1.5,
                retrieved_documents: []
            });

        render(
            <ChatContainer
                userHasDocuments={true}
                showDocumentPanel={false}
            />
        );

        // Simulate sending a message (should fail)
        const input = screen.getByTestId('message-input');
        fireEvent.change(input, { target: { value: 'test message' } });

        // Should show error display
        await waitFor(() => {
            expect(screen.getByTestId('error-display')).toBeInTheDocument();
        });

        // Click retry button
        const retryButton = screen.getByText('다시 시도');
        fireEvent.click(retryButton);

        // Should retry the API call
        await waitFor(() => {
            expect(ApiClient.sendQuestion).toHaveBeenCalledTimes(2);
        });

        // Error should be cleared after successful retry
        await waitFor(() => {
            expect(screen.queryByTestId('error-display')).not.toBeInTheDocument();
        });
    });

    it('should handle error dismissal', async () => {
        const { ApiClient } = await import('@/lib/api');

        // Mock network error
        (ApiClient.sendQuestion as any).mockRejectedValue(
            new Error('Failed to fetch')
        );

        render(
            <ChatContainer
                userHasDocuments={true}
                showDocumentPanel={false}
            />
        );

        // Simulate sending a message
        const input = screen.getByTestId('message-input');
        fireEvent.change(input, { target: { value: 'test message' } });

        // Should show error display
        await waitFor(() => {
            expect(screen.getByTestId('error-display')).toBeInTheDocument();
        });

        // Click dismiss button
        const dismissButton = screen.getByText('닫기');
        fireEvent.click(dismissButton);

        // Error should be dismissed
        await waitFor(() => {
            expect(screen.queryByTestId('error-display')).not.toBeInTheDocument();
        });
    });

    it('should show fallback error display for legacy errors', async () => {
        const { ApiClient } = await import('@/lib/api');

        // Mock a simple string error (legacy format)
        (ApiClient.sendQuestion as any).mockRejectedValue(
            new Error('Simple error message')
        );

        render(
            <ChatContainer
                userHasDocuments={true}
                showDocumentPanel={false}
            />
        );

        // Simulate sending a message
        const input = screen.getByTestId('message-input');
        fireEvent.change(input, { target: { value: 'test message' } });

        // Should show either enhanced or legacy error display
        await waitFor(() => {
            const errorDisplay = screen.queryByTestId('error-display');
            const legacyErrorDisplay = screen.queryByTestId('legacy-error-display');

            expect(errorDisplay || legacyErrorDisplay).toBeInTheDocument();
        });
    });

    it('should disable input when processing and show appropriate placeholder', () => {
        render(
            <ChatContainer
                userHasDocuments={true}
                showDocumentPanel={false}
            />
        );

        const input = screen.getByTestId('message-input');

        // Should show ready placeholder when not processing
        expect(input).toHaveAttribute('placeholder', expect.stringContaining('적성 분석에 대해 궁금한 것'));
    });

    it('should show empty state when user has no documents', () => {
        render(
            <ChatContainer
                userHasDocuments={false}
                showDocumentPanel={false}
            />
        );

        expect(screen.getByTestId('empty-state')).toBeInTheDocument();
    });

    it('should handle validation errors with field-specific feedback', async () => {
        const { ApiClient } = await import('@/lib/api');

        // Mock validation error
        const validationError = new Error('Validation failed');
        (validationError as any).status = 400;
        (validationError as any).type = 'validation_error';
        (validationError as any).field_errors = {
            question: 'Question is required'
        };

        (ApiClient.sendQuestion as any).mockRejectedValue(validationError);

        render(
            <ChatContainer
                userHasDocuments={true}
                showDocumentPanel={false}
            />
        );

        // Simulate sending a message
        const input = screen.getByTestId('message-input');
        fireEvent.change(input, { target: { value: 'test message' } });

        // Should show error display
        await waitFor(() => {
            expect(screen.getByTestId('error-display')).toBeInTheDocument();
        });

        // Should show validation error message
        expect(screen.getByText('입력 오류')).toBeInTheDocument();
        expect(screen.getByText(/입력한 내용에 문제가 있습니다/)).toBeInTheDocument();
    });
});