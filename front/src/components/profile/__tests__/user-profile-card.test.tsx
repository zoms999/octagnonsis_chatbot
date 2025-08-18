import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { vi, describe, it, expect, beforeEach } from 'vitest';
import { UserProfileCard } from '../user-profile-card';
import { AuthUser, UserProfileResponse } from '@/lib/types';

// Mock the auth provider
vi.mock('@/providers/auth-provider', () => ({
  useAuth: vi.fn(),
}));

// Mock the API hooks
vi.mock('@/hooks/api-hooks', () => ({
  useUserProfile: vi.fn(),
}));

// Mock date-fns
vi.mock('date-fns', () => ({
  formatDistanceToNow: vi.fn(() => '2시간 전'),
}));

// Mock date-fns/locale
vi.mock('date-fns/locale', () => ({
  ko: {},
}));

import { useAuth } from '@/providers/auth-provider';
import { useUserProfile } from '@/hooks/api-hooks';

const mockUser: AuthUser = {
  id: 'user-123',
  name: '홍길동',
  type: 'personal',
  ac_id: 'AC123',
  isPaid: true,
  isExpired: false,
  productType: 'premium',
  sessionCode: 'SESSION123',
};

const mockProfileResponse: UserProfileResponse = {
  user: {
    user_id: 'user-123',
    document_count: 5,
    conversation_count: 12,
    available_document_types: ['primary_tendency', 'top_skills', 'top_jobs'],
    last_conversation_at: '2024-01-15T10:30:00Z',
    processing_status: 'completed',
  },
};

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>
      {children}
    </QueryClientProvider>
  );
};

describe('UserProfileCard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders user information correctly', async () => {
    (useAuth as any).mockReturnValue({ user: mockUser });
    (useUserProfile as any).mockReturnValue({
      data: mockProfileResponse,
      isLoading: false,
      error: null,
    });

    render(<UserProfileCard />, { wrapper: createWrapper() });

    // Check user information
    expect(screen.getByText('홍길동')).toBeInTheDocument();
    expect(screen.getByText('user-123')).toBeInTheDocument();
    expect(screen.getByText('개인 사용자')).toBeInTheDocument();
    expect(screen.getByText('AC123')).toBeInTheDocument();
    expect(screen.getByText('SESSION123')).toBeInTheDocument();
    expect(screen.getByText('premium')).toBeInTheDocument();

    // Check status badges
    expect(screen.getByText('유료')).toBeInTheDocument();
    expect(screen.getByText('활성')).toBeInTheDocument();
  });

  it('displays usage statistics when profile data is loaded', async () => {
    (useAuth as any).mockReturnValue({ user: mockUser });
    (useUserProfile as any).mockReturnValue({
      data: mockProfileResponse,
      isLoading: false,
      error: null,
    });

    render(<UserProfileCard />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('5')).toBeInTheDocument(); // document count
      expect(screen.getByText('12')).toBeInTheDocument(); // conversation count
      expect(screen.getByText('2시간 전')).toBeInTheDocument(); // last conversation
    });

    expect(screen.getByText('보유 문서')).toBeInTheDocument();
    expect(screen.getByText('대화 수')).toBeInTheDocument();
    expect(screen.getByText('마지막 대화')).toBeInTheDocument();
  });

  it('displays processing status badge', async () => {
    (useAuth as any).mockReturnValue({ user: mockUser });
    (useUserProfile as any).mockReturnValue({
      data: mockProfileResponse,
      isLoading: false,
      error: null,
    });

    render(<UserProfileCard />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('처리 완료')).toBeInTheDocument();
    });
  });

  it('displays available document types', async () => {
    (useAuth as any).mockReturnValue({ user: mockUser });
    (useUserProfile as any).mockReturnValue({
      data: mockProfileResponse,
      isLoading: false,
      error: null,
    });

    render(<UserProfileCard />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('주요 성향')).toBeInTheDocument();
      expect(screen.getByText('상위 기술')).toBeInTheDocument();
      expect(screen.getByText('추천 직업')).toBeInTheDocument();
    });
  });

  it('handles different user types correctly', () => {
    const orgAdminUser: AuthUser = {
      ...mockUser,
      type: 'organization_admin',
    };

    (useAuth as any).mockReturnValue({ user: orgAdminUser });
    (useUserProfile as any).mockReturnValue({
      data: mockProfileResponse,
      isLoading: false,
      error: null,
    });

    render(<UserProfileCard />, { wrapper: createWrapper() });

    expect(screen.getByText('기관 관리자')).toBeInTheDocument();
  });

  it('handles loading state', () => {
    (useAuth as any).mockReturnValue({ user: mockUser });
    (useUserProfile as any).mockReturnValue({
      data: null,
      isLoading: true,
      error: null,
    });

    render(<UserProfileCard />, { wrapper: createWrapper() });

    // Should show skeleton loading states
    expect(screen.getByText('사용 통계')).toBeInTheDocument();
  });

  it('handles API error', async () => {
    (useAuth as any).mockReturnValue({ user: mockUser });
    (useUserProfile as any).mockReturnValue({
      data: null,
      isLoading: false,
      error: new Error('API Error'),
    });

    render(<UserProfileCard />, { wrapper: createWrapper() });

    expect(screen.getByText('프로필 정보를 불러오는 중 오류가 발생했습니다.')).toBeInTheDocument();
    expect(screen.getByText('잠시 후 다시 시도해주세요.')).toBeInTheDocument();
  });

  it('handles no user case', () => {
    (useAuth as any).mockReturnValue({ user: null });
    (useUserProfile as any).mockReturnValue({
      data: null,
      isLoading: false,
      error: null,
    });

    render(<UserProfileCard />, { wrapper: createWrapper() });

    expect(screen.getByText('사용자 정보를 불러올 수 없습니다.')).toBeInTheDocument();
  });
});