'use client';

import React from 'react';
import { 
  useLogin, 
  useValidateSession, 
  useSendQuestion, 
  useConversationHistory,
  useUserProfile 
} from '@/hooks/api-hooks';
import { LoginCredentials } from '@/lib/types';

/**
 * Example component demonstrating how to use the API hooks
 * This is for reference only and shows the proper usage patterns
 */
export function ApiUsageExample() {
  // Authentication hooks
  const loginMutation = useLogin({
    onSuccess: (data) => {
      console.log('Login successful:', data.user);
    },
    onError: (error) => {
      console.error('Login failed:', error.message);
    },
  });

  const { data: user, isLoading: isValidating } = useValidateSession();

  // Chat hooks
  const sendQuestionMutation = useSendQuestion({
    onSuccess: (response) => {
      console.log('Question sent successfully:', response);
    },
  });

  // User data hooks
  const { data: conversationHistory, isLoading: isLoadingHistory } = useConversationHistory(
    user?.id || '',
    1,
    10
  );

  const { data: userProfile, isLoading: isLoadingProfile } = useUserProfile(
    user?.id || ''
  );

  const handleLogin = async () => {
    const credentials: LoginCredentials = {
      username: 'example@email.com',
      password: 'password123',
      loginType: 'personal',
    };

    try {
      await loginMutation.mutateAsync(credentials);
    } catch (error) {
      console.error('Login error:', error);
    }
  };

  const handleSendQuestion = async () => {
    if (!user?.id) return;

    try {
      await sendQuestionMutation.mutateAsync({
        question: 'What are my top skills?',
      });
    } catch (error) {
      console.error('Send question error:', error);
    }
  };

  return (
    <div className="p-6 max-w-2xl mx-auto">
      <h1 className="text-2xl font-bold mb-6">API Usage Example</h1>
      
      {/* Authentication Section */}
      <section className="mb-8">
        <h2 className="text-xl font-semibold mb-4">Authentication</h2>
        
        {isValidating ? (
          <p>Validating session...</p>
        ) : user ? (
          <div className="bg-green-100 p-4 rounded">
            <p>Logged in as: {user.name}</p>
            <p>User type: {user.type}</p>
          </div>
        ) : (
          <div>
            <p className="mb-2">Not logged in</p>
            <button
              onClick={handleLogin}
              disabled={loginMutation.isPending}
              className="bg-blue-500 text-white px-4 py-2 rounded disabled:opacity-50"
            >
              {loginMutation.isPending ? 'Logging in...' : 'Login'}
            </button>
          </div>
        )}
      </section>

      {/* Chat Section */}
      {user && (
        <section className="mb-8">
          <h2 className="text-xl font-semibold mb-4">Chat</h2>
          
          <button
            onClick={handleSendQuestion}
            disabled={sendQuestionMutation.isPending}
            className="bg-green-500 text-white px-4 py-2 rounded disabled:opacity-50"
          >
            {sendQuestionMutation.isPending ? 'Sending...' : 'Send Question'}
          </button>
          
          {sendQuestionMutation.isError && (
            <p className="text-red-500 mt-2">
              Error: {sendQuestionMutation.error?.message}
            </p>
          )}
        </section>
      )}

      {/* User Profile Section */}
      {user && (
        <section className="mb-8">
          <h2 className="text-xl font-semibold mb-4">User Profile</h2>
          
          {isLoadingProfile ? (
            <p>Loading profile...</p>
          ) : userProfile ? (
            <div className="bg-gray-100 p-4 rounded">
              <p>Document count: {userProfile.user.document_count}</p>
              <p>Conversation count: {userProfile.user.conversation_count}</p>
              <p>Processing status: {userProfile.user.processing_status}</p>
            </div>
          ) : (
            <p>No profile data available</p>
          )}
        </section>
      )}

      {/* Conversation History Section */}
      {user && (
        <section className="mb-8">
          <h2 className="text-xl font-semibold mb-4">Conversation History</h2>
          
          {isLoadingHistory ? (
            <p>Loading history...</p>
          ) : conversationHistory ? (
            <div>
              <p className="mb-2">Total conversations: {conversationHistory.total}</p>
              <div className="space-y-2">
                {conversationHistory.conversations.map((conversation) => (
                  <div key={conversation.conversation_id} className="bg-gray-100 p-3 rounded">
                    <p className="font-medium">ID: {conversation.conversation_id}</p>
                    <p className="text-sm text-gray-600">
                      Messages: {conversation.message_count}
                    </p>
                    <p className="text-sm text-gray-600">
                      Created: {new Date(conversation.created_at).toLocaleDateString()}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <p>No conversation history available</p>
          )}
        </section>
      )}

      {/* Error Handling Examples */}
      <section className="mb-8">
        <h2 className="text-xl font-semibold mb-4">Error Handling</h2>
        <div className="text-sm text-gray-600">
          <p>• Authentication errors automatically trigger logout</p>
          <p>• Rate limit errors show countdown timers</p>
          <p>• Network errors provide retry options</p>
          <p>• Validation errors highlight specific fields</p>
        </div>
      </section>
    </div>
  );
}

export default ApiUsageExample;