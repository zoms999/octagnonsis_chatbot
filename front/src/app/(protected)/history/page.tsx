'use client';

import * as React from 'react';
import { SimpleLayout } from '@/components/layout';
import { ConversationHistoryList, ConversationDetailModal } from '@/components/history';
import { Conversation } from '@/lib/types';

export default function HistoryPage() {
  const [selectedConversation, setSelectedConversation] = React.useState<Conversation | null>(null);
  const [isModalOpen, setIsModalOpen] = React.useState(false);

  const handleConversationSelect = (conversation: Conversation) => {
    setSelectedConversation(conversation);
    setIsModalOpen(true);
  };

  const handleModalClose = () => {
    setIsModalOpen(false);
    setSelectedConversation(null);
  };

  const handleNavigateToConversation = (conversationId: string) => {
    // Navigate to chat with the selected conversation
    window.location.href = `/chat?conversation=${conversationId}`;
  };

  return (
    <SimpleLayout>
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold">대화 기록</h1>
          <p className="text-muted-foreground mt-1">
            이전 대화 내용을 확인하고 관리할 수 있습니다.
          </p>
        </div>

        <div className="bg-card rounded-lg border p-6">
          <ConversationHistoryList 
            onConversationSelect={handleConversationSelect}
          />
        </div>

        {/* Conversation Detail Modal */}
        <ConversationDetailModal
          conversation={selectedConversation}
          isOpen={isModalOpen}
          onClose={handleModalClose}
          onNavigateToConversation={handleNavigateToConversation}
        />
      </div>
    </SimpleLayout>
  );
}