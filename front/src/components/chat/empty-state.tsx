'use client';

import React from 'react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

interface EmptyStateProps {
  userHasDocuments?: boolean;
  onUploadDocuments?: () => void;
  onViewProfile?: () => void;
  className?: string;
}

export function EmptyState({
  userHasDocuments = true,
  onUploadDocuments,
  onViewProfile,
  className
}: EmptyStateProps) {
  if (!userHasDocuments) {
    return (
      <div className={cn(
        'flex flex-col items-center justify-center p-8 text-center',
        className
      )} data-testid="no-documents-message">
        <div className="max-w-md">
          <div className="text-6xl mb-4">📄</div>
          <h3 className="text-lg font-semibold text-gray-900 mb-2">
            분석할 문서가 없습니다
          </h3>
          <p className="text-gray-600 mb-6">
            적성 분석을 위해서는 먼저 적성검사 결과 문서를 업로드해야 합니다.
            문서를 업로드하고 처리가 완료되면 AI 챗봇과 대화할 수 있습니다.
          </p>
          
          <div className="flex flex-col sm:flex-row gap-3 justify-center">
            {onViewProfile && (
              <Button
                onClick={onViewProfile}
                variant="outline"
                className="px-6"
              >
                프로필 확인
              </Button>
            )}
            {onUploadDocuments && (
              <Button
                onClick={onUploadDocuments}
                className="px-6"
                data-testid="upload-documents-link"
              >
                문서 업로드
              </Button>
            )}
          </div>
          
          <div className="mt-6 p-4 bg-blue-50 rounded-lg">
            <h4 className="text-sm font-medium text-blue-900 mb-2">
              💡 업로드 가능한 문서 유형
            </h4>
            <ul className="text-xs text-blue-700 space-y-1">
              <li>• 적성검사 결과 보고서 (PDF, DOC)</li>
              <li>• 성격 유형 분석 결과</li>
              <li>• 직업 적성 평가서</li>
            </ul>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={cn(
      'flex flex-col items-center justify-center p-8 text-center',
      className
    )}>
      <div className="max-w-md">
        <div className="text-6xl mb-4">💬</div>
        <h3 className="text-lg font-semibold text-gray-900 mb-2">
          AI 적성 분석 챗봇에 오신 것을 환영합니다!
        </h3>
        <p className="text-gray-600 mb-6">
          적성 분석 결과에 대해 궁금한 것이 있으시면 언제든 물어보세요.
          AI가 여러분의 적성과 관련된 질문에 답변해드립니다.
        </p>
        
        <div className="grid grid-cols-1 gap-3 text-sm">
          <div className="p-3 bg-gray-50 rounded-lg text-left">
            <div className="font-medium text-gray-900 mb-1">
              💼 "내 적성에 맞는 직업은 무엇인가요?"
            </div>
            <div className="text-gray-600 text-xs">
              적성 분석 결과를 바탕으로 추천 직업을 알려드립니다.
            </div>
          </div>
          
          <div className="p-3 bg-gray-50 rounded-lg text-left">
            <div className="font-medium text-gray-900 mb-1">
              🎯 "내 강점과 약점은 무엇인가요?"
            </div>
            <div className="text-gray-600 text-xs">
              분석된 성격 유형과 능력을 자세히 설명해드립니다.
            </div>
          </div>
          
          <div className="p-3 bg-gray-50 rounded-lg text-left">
            <div className="font-medium text-gray-900 mb-1">
              📚 "어떤 분야를 더 공부해야 하나요?"
            </div>
            <div className="text-gray-600 text-xs">
              적성에 맞는 학습 방향과 개발 영역을 제안합니다.
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}