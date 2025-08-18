'use client';

import * as React from 'react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';

interface SidebarProps {
  children: React.ReactNode;
  className?: string;
  isCollapsed?: boolean;
  onToggle?: () => void;
  side?: 'left' | 'right';
  title?: string;
}

const Sidebar = ({ 
  children, 
  className, 
  isCollapsed = false, 
  onToggle, 
  side = 'right',
  title 
}: SidebarProps) => {
  return (
    <aside
      className={cn(
        'relative border-l bg-background transition-all duration-300 ease-in-out',
        side === 'left' && 'border-l-0 border-r',
        isCollapsed ? 'w-0 overflow-hidden' : 'w-80',
        'lg:w-80', // Always show full width on large screens
        className
      )}
      aria-label={title || 'Sidebar'}
    >
      {/* Toggle Button */}
      {onToggle && (
        <Button
          variant="ghost"
          size="icon"
          onClick={onToggle}
          className={cn(
            'absolute top-4 z-10 h-8 w-8',
            side === 'right' ? '-left-4' : '-right-4',
            'bg-background border shadow-md hover:shadow-lg'
          )}
          aria-label={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          <svg
            className={cn(
              'h-4 w-4 transition-transform',
              isCollapsed ? 'rotate-180' : '',
              side === 'left' && 'rotate-180'
            )}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M9 5l7 7-7 7"
            />
          </svg>
        </Button>
      )}

      {/* Sidebar Content */}
      <div className={cn('h-full flex flex-col', isCollapsed && 'hidden')}>
        {/* Header */}
        {title && (
          <div className="flex items-center justify-between p-4 border-b">
            <h2 className="text-lg font-semibold">{title}</h2>
          </div>
        )}

        {/* Content */}
        <div className="flex-1 overflow-auto">
          {children}
        </div>
      </div>
    </aside>
  );
};

// Document Panel Sidebar - Specific implementation for chat documents
interface DocumentPanelProps {
  documents?: Array<{
    id: string;
    title: string;
    preview: string;
    relevance_score: number;
    type: string;
  }>;
  isCollapsed?: boolean;
  onToggle?: () => void;
  className?: string;
}

const DocumentPanel = ({ documents = [], isCollapsed, onToggle, className }: DocumentPanelProps) => {
  return (
    <Sidebar
      title="참조 문서"
      isCollapsed={isCollapsed}
      onToggle={onToggle}
      className={className}
    >
      <div className="p-4 space-y-4">
        {documents.length === 0 ? (
          <div className="text-center text-muted-foreground py-8">
            <svg className="h-12 w-12 mx-auto mb-4 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            <p className="text-sm">참조된 문서가 없습니다</p>
          </div>
        ) : (
          <>
            <div className="text-sm text-muted-foreground mb-2">
              {documents.length}개의 문서가 참조되었습니다
            </div>
            {documents.map((doc) => (
              <div
                key={doc.id}
                className="border rounded-lg p-3 space-y-2 hover:bg-accent/50 transition-colors"
              >
                <div className="flex items-start justify-between">
                  <h4 className="text-sm font-medium line-clamp-2">{doc.title}</h4>
                  <div className="flex items-center space-x-1 text-xs text-muted-foreground ml-2">
                    <svg className="h-3 w-3" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M11.49 3.17c-.38-1.56-2.6-1.56-2.98 0a1.532 1.532 0 01-2.286.948c-1.372-.836-2.942.734-2.106 2.106.54.886.061 2.042-.947 2.287-1.561.379-1.561 2.6 0 2.978a1.532 1.532 0 01.947 2.287c-.836 1.372.734 2.942 2.106 2.106a1.532 1.532 0 012.287.947c.379 1.561 2.6 1.561 2.978 0a1.533 1.533 0 012.287-.947c1.372.836 2.942-.734 2.106-2.106a1.533 1.533 0 01.947-2.287c1.561-.379 1.561-2.6 0-2.978a1.532 1.532 0 01-.947-2.287c.836-1.372-.734-2.942-2.106-2.106a1.532 1.532 0 01-2.287-.947zM10 13a3 3 0 100-6 3 3 0 000 6z" clipRule="evenodd" />
                    </svg>
                    <span>{Math.round(doc.relevance_score * 100)}%</span>
                  </div>
                </div>
                <p className="text-xs text-muted-foreground line-clamp-3">
                  {doc.preview}
                </p>
                <div className="flex items-center justify-between">
                  <span className="inline-flex items-center px-2 py-1 rounded-full text-xs bg-secondary text-secondary-foreground">
                    {doc.type}
                  </span>
                </div>
              </div>
            ))}
          </>
        )}
      </div>
    </Sidebar>
  );
};

export { Sidebar, DocumentPanel };