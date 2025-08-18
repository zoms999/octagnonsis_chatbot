'use client';

import React from 'react';
import { useAuth } from '@/providers/auth-provider';
import { useUserProfile } from '@/hooks/api-hooks';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { AlertCircle, FileText, MessageSquare, Clock, Activity } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import { ko } from 'date-fns/locale';

interface UserProfileCardProps {
  className?: string;
}

export function UserProfileCard({ className }: UserProfileCardProps) {
  const { user } = useAuth();
  const { data: profileData, isLoading, error } = useUserProfile(user?.id || '');

  if (!user) {
    return (
      <Card className={`p-6 ${className}`}>
        <div className="text-center text-muted-foreground">
          <AlertCircle className="h-8 w-8 mx-auto mb-2" />
          <p>사용자 정보를 불러올 수 없습니다.</p>
        </div>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className={`p-6 ${className}`}>
        <div className="text-center text-destructive">
          <AlertCircle className="h-8 w-8 mx-auto mb-2" />
          <p>프로필 정보를 불러오는 중 오류가 발생했습니다.</p>
          <p className="text-sm text-muted-foreground mt-1">
            잠시 후 다시 시도해주세요.
          </p>
        </div>
      </Card>
    );
  }

  const profile = profileData?.user;

  const getProcessingStatusBadge = (status: string) => {
    switch (status) {
      case 'completed':
        return <Badge variant="success" className="bg-green-100 text-green-800">처리 완료</Badge>;
      case 'pending':
        return <Badge variant="warning" className="bg-yellow-100 text-yellow-800">처리 중</Badge>;
      case 'failed':
        return <Badge variant="destructive" className="bg-red-100 text-red-800">처리 실패</Badge>;
      case 'none':
      default:
        return <Badge variant="secondary" className="bg-gray-100 text-gray-800">미처리</Badge>;
    }
  };

  const getUserTypeLabel = (type: string) => {
    switch (type) {
      case 'personal':
        return '개인 사용자';
      case 'organization_admin':
        return '기관 관리자';
      case 'organization_member':
        return '기관 구성원';
      default:
        return type;
    }
  };

  return (
    <div className={`space-y-6 ${className}`}>
      {/* User Information Card */}
      <Card className="p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold">사용자 정보</h2>
          <div className="flex items-center space-x-2">
            <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${
              user.isPaid 
                ? 'bg-green-100 text-green-800' 
                : 'bg-blue-100 text-blue-800'
            }`}>
              {user.isPaid ? '유료' : '무료'}
            </span>
            <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${
              user.isExpired 
                ? 'bg-red-100 text-red-800' 
                : 'bg-green-100 text-green-800'
            }`}>
              {user.isExpired ? '만료됨' : '활성'}
            </span>
          </div>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="text-sm font-medium text-muted-foreground">이름</label>
            <p className="text-sm mt-1">{user.name}</p>
          </div>
          <div>
            <label className="text-sm font-medium text-muted-foreground">사용자 ID</label>
            <p className="text-sm font-mono mt-1">{user.id}</p>
          </div>
          <div>
            <label className="text-sm font-medium text-muted-foreground">계정 유형</label>
            <p className="text-sm mt-1">{getUserTypeLabel(user.type)}</p>
          </div>
          {user.ac_id && (
            <div>
              <label className="text-sm font-medium text-muted-foreground">AC ID</label>
              <p className="text-sm font-mono mt-1">{user.ac_id}</p>
            </div>
          )}
          {user.sessionCode && (
            <div>
              <label className="text-sm font-medium text-muted-foreground">세션 코드</label>
              <p className="text-sm font-mono mt-1">{user.sessionCode}</p>
            </div>
          )}
          {user.productType && (
            <div>
              <label className="text-sm font-medium text-muted-foreground">상품 유형</label>
              <p className="text-sm mt-1">{user.productType}</p>
            </div>
          )}
        </div>
      </Card>

      {/* Usage Statistics Card */}
      <Card className="p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold">사용 통계</h2>
          {profile && (
            <div className="flex items-center space-x-1">
              <Activity className="h-4 w-4 text-muted-foreground" />
              {getProcessingStatusBadge(profile.processing_status)}
            </div>
          )}
        </div>

        {isLoading ? (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {[...Array(3)].map((_, i) => (
              <div key={i} className="space-y-2">
                <Skeleton className="h-4 w-20" />
                <Skeleton className="h-8 w-16" />
              </div>
            ))}
          </div>
        ) : profile ? (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="text-center">
              <div className="flex items-center justify-center mb-2">
                <FileText className="h-5 w-5 text-blue-500 mr-2" />
                <span className="text-2xl font-bold text-blue-600">{profile.document_count}</span>
              </div>
              <p className="text-sm text-muted-foreground">보유 문서</p>
            </div>
            
            <div className="text-center">
              <div className="flex items-center justify-center mb-2">
                <MessageSquare className="h-5 w-5 text-green-500 mr-2" />
                <span className="text-2xl font-bold text-green-600">{profile.conversation_count}</span>
              </div>
              <p className="text-sm text-muted-foreground">대화 수</p>
            </div>
            
            <div className="text-center">
              <div className="flex items-center justify-center mb-2">
                <Clock className="h-5 w-5 text-purple-500 mr-2" />
                <span className="text-sm font-medium text-purple-600">
                  {profile.last_conversation_at 
                    ? formatDistanceToNow(new Date(profile.last_conversation_at), { 
                        addSuffix: true, 
                        locale: ko 
                      })
                    : '없음'
                  }
                </span>
              </div>
              <p className="text-sm text-muted-foreground">마지막 대화</p>
            </div>
          </div>
        ) : (
          <div className="text-center text-muted-foreground py-8">
            <FileText className="h-8 w-8 mx-auto mb-2 opacity-50" />
            <p>사용 통계를 불러올 수 없습니다.</p>
          </div>
        )}
      </Card>

      {/* Available Document Types Card */}
      {profile && profile.available_document_types.length > 0 && (
        <Card className="p-6">
          <h2 className="text-lg font-semibold mb-4">사용 가능한 문서 유형</h2>
          <div className="flex flex-wrap gap-2">
            {profile.available_document_types.map((docType) => (
              <Badge key={docType} variant="outline" className="text-sm">
                {docType === 'primary_tendency' && '주요 성향'}
                {docType === 'top_skills' && '상위 기술'}
                {docType === 'top_jobs' && '추천 직업'}
                {!['primary_tendency', 'top_skills', 'top_jobs'].includes(docType) && docType}
              </Badge>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
}