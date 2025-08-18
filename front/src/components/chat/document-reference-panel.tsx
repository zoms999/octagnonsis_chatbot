'use client';

import React, { useState } from 'react';
import { DocumentReference } from '@/lib/types';
import { cn } from '@/lib/utils';

interface DocumentReferencePanelProps {
  documents: DocumentReference[];
  isCollapsed?: boolean;
  onToggle?: () => void;
  className?: string;
}

export function DocumentReferencePanel({
  documents,
  isCollapsed = false,
  onToggle,
  className
}: DocumentReferencePanelProps) {
  const [expandedDocuments, setExpandedDocuments] = useState<Set<string>>(new Set());

  const toggleDocumentExpansion = (docId: string) => {
    const newExpanded = new Set(expandedDocuments);
    if (newExpanded.has(docId)) {
      newExpanded.delete(docId);
    } else {
      newExpanded.add(docId);
    }
    setExpandedDocuments(newExpanded);
  };

  const getRelevanceColor = (score: number) => {
    if (score >= 0.8) return 'text-green-600 bg-green-50';
    if (score >= 0.6) return 'text-yellow-600 bg-yellow-50';
    return 'text-red-600 bg-red-50';
  };

  const getDocumentTypeLabel = (type: string) => {
    const typeLabels: Record<string, string> = {
      'primary_tendency': '주요 성향',
      'top_skills': '핵심 역량',
      'top_jobs': '추천 직업',
      'personality': '성격 분석',
      'aptitude': '적성 검사',
      'career': '진로 분석',
      'default': '문서'
    };
    return typeLabels[type] || typeLabels.default;
  };

  return (
    <div className={cn(
      'bg-white border-l border-gray-200 transition-all duration-300 ease-in-out',
      'flex flex-col h-full',
      isCollapsed ? 'w-12' : 'w-80',
      className
    )} data-testid="document-panel">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-gray-200 bg-gray-50">
        {!isCollapsed && (
          <div className="flex items-center space-x-2">
            <svg className="h-5 w-5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            <h3 className="text-sm font-semibold text-gray-900">참조 문서</h3>
            {(documents?.length || 0) > 0 && (
              <span className="inline-flex items-center px-2 py-1 rounded-full text-xs bg-blue-100 text-blue-800">
                {documents?.length || 0}
              </span>
            )}
          </div>
        )}
        
        {onToggle && (
          <button
            onClick={onToggle}
            className="p-1 rounded-md hover:bg-gray-200 transition-colors"
            aria-label={isCollapsed ? '패널 열기' : '패널 닫기'}
            data-testid="panel-toggle"
          >
            <svg 
              className={cn(
                'h-4 w-4 text-gray-600 transition-transform duration-200',
                isCollapsed ? 'rotate-180' : ''
              )} 
              fill="none" 
              stroke="currentColor" 
              viewBox="0 0 24 24"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
          </button>
        )}
      </div>

      {/* Content */}
      {!isCollapsed && (
        <div className="flex-1 overflow-y-auto">
          {(documents?.length || 0) === 0 ? (
            <div className="p-6 text-center">
              <div className="text-gray-400 mb-4">
                <svg className="h-12 w-12 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
              </div>
              <p className="text-sm text-gray-500 mb-2">참조된 문서가 없습니다</p>
              <p className="text-xs text-gray-400">
                질문을 하시면 관련 문서가 여기에 표시됩니다
              </p>
            </div>
          ) : (
            <div className="p-4 space-y-3">
              {/* Document count summary */}
              <div className="text-xs text-gray-500 mb-4 pb-2 border-b border-gray-100" data-testid="retrieved-documents">
                총 {documents?.length || 0}개의 문서에서 정보를 참조했습니다
              </div>

              {/* Document list */}
              {documents?.map((document, index) => {
                const isExpanded = expandedDocuments.has(document.id);
                const relevanceScore = Math.round(document.relevance_score * 100);
                
                return (
                  <div
                    key={document.id}
                    className="border border-gray-200 rounded-lg overflow-hidden hover:shadow-sm transition-shadow"
                    data-testid="document-item"
                  >
                    {/* Document header */}
                    <div className="p-3 bg-gray-50">
                      <div className="flex items-start justify-between mb-2">
                        <div className="flex-1 min-w-0">
                          <h4 className="text-sm font-medium text-gray-900 line-clamp-2 mb-1">
                            {document.title}
                          </h4>
                          <div className="flex items-center space-x-2">
                            <span className="inline-flex items-center px-2 py-1 rounded-full text-xs bg-blue-100 text-blue-800">
                              {getDocumentTypeLabel(document.type)}
                            </span>
                            <div className={cn(
                              'inline-flex items-center px-2 py-1 rounded-full text-xs font-medium',
                              getRelevanceColor(document.relevance_score)
                            )} data-testid="relevance-score">
                              <svg className="h-3 w-3 mr-1" fill="currentColor" viewBox="0 0 20 20">
                                <path fillRule="evenodd" d="M11.49 3.17c-.38-1.56-2.6-1.56-2.98 0a1.532 1.532 0 01-2.286.948c-1.372-.836-2.942.734-2.106 2.106.54.886.061 2.042-.947 2.287-1.561.379-1.561 2.6 0 2.978a1.532 1.532 0 01.947 2.287c-.836 1.372.734 2.942 2.106 2.106a1.532 1.532 0 012.287.947c.379 1.561 2.6 1.561 2.978 0a1.533 1.533 0 012.287-.947c1.372.836 2.942-.734 2.106-2.106a1.533 1.533 0 01.947-2.287c1.561-.379 1.561-2.6 0-2.978a1.532 1.532 0 01-.947-2.287c.836-1.372-.734-2.942-2.106-2.106a1.532 1.532 0 01-2.287-.947zM10 13a3 3 0 100-6 3 3 0 000 6z" clipRule="evenodd" />
                              </svg>
                              {relevanceScore}%
                            </div>
                          </div>
                        </div>
                        
                        <button
                          onClick={() => toggleDocumentExpansion(document.id)}
                          className="ml-2 p-1 rounded-md hover:bg-gray-200 transition-colors flex-shrink-0"
                          aria-label={isExpanded ? '접기' : '펼치기'}
                        >
                          <svg 
                            className={cn(
                              'h-4 w-4 text-gray-500 transition-transform duration-200',
                              isExpanded ? 'rotate-180' : ''
                            )} 
                            fill="none" 
                            stroke="currentColor" 
                            viewBox="0 0 24 24"
                          >
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                          </svg>
                        </button>
                      </div>
                    </div>

                    {/* Document preview */}
                    <div className="p-3">
                      <p className={cn(
                        'text-xs text-gray-600 leading-relaxed',
                        isExpanded ? '' : 'line-clamp-2'
                      )}>
                        {document.preview}
                      </p>
                      
                      {!isExpanded && document.preview.length > 100 && (
                        <button
                          onClick={() => toggleDocumentExpansion(document.id)}
                          className="text-xs text-blue-600 hover:text-blue-800 mt-1 font-medium"
                        >
                          더 보기
                        </button>
                      )}
                    </div>

                    {/* Document metadata (when expanded) */}
                    {isExpanded && (
                      <div className="px-3 pb-3 border-t border-gray-100 pt-2">
                        <div className="flex items-center justify-between text-xs text-gray-500">
                          <span>문서 ID: {document.id}</span>
                          <span>관련도: {relevanceScore}%</span>
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* Collapsed state indicator */}
      {isCollapsed && (documents?.length || 0) > 0 && (
        <div className="flex-1 flex flex-col items-center justify-center p-2">
          <div className="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center mb-2">
            <span className="text-xs font-semibold text-blue-800">{documents?.length || 0}</span>
          </div>
          <div className="text-xs text-gray-500 text-center leading-tight">
            참조<br />문서
          </div>
        </div>
      )}
    </div>
  );
}