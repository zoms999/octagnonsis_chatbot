import * as React from 'react';
import { cn } from '@/lib/utils';

interface SkeletonProps {
  className?: string;
}

const Skeleton = ({ className }: SkeletonProps) => {
  return (
    <div
      className={cn(
        'animate-pulse rounded-md bg-muted',
        className
      )}
      role="status"
      aria-label="Loading content"
    />
  );
};

// Predefined skeleton patterns for common use cases

const SkeletonText = ({ lines = 3, className }: { lines?: number; className?: string }) => {
  return (
    <div className={cn('space-y-2', className)}>
      {Array.from({ length: lines }).map((_, i) => (
        <Skeleton
          key={i}
          className={cn(
            'h-4',
            i === lines - 1 ? 'w-3/4' : 'w-full' // Last line is shorter
          )}
        />
      ))}
    </div>
  );
};

const SkeletonCard = ({ className }: { className?: string }) => {
  return (
    <div className={cn('space-y-3', className)}>
      <Skeleton className="h-4 w-1/2" />
      <SkeletonText lines={2} />
      <div className="flex space-x-2">
        <Skeleton className="h-8 w-16" />
        <Skeleton className="h-8 w-16" />
      </div>
    </div>
  );
};

const SkeletonAvatar = ({ size = 'md', className }: { size?: 'sm' | 'md' | 'lg'; className?: string }) => {
  const sizeClasses = {
    sm: 'h-8 w-8',
    md: 'h-10 w-10',
    lg: 'h-12 w-12',
  };

  return (
    <Skeleton
      className={cn(
        'rounded-full',
        sizeClasses[size],
        className
      )}
    />
  );
};

const SkeletonButton = ({ className }: { className?: string }) => {
  return (
    <Skeleton className={cn('h-10 w-24 rounded-md', className)} />
  );
};

const SkeletonTable = ({ rows = 5, columns = 4, className }: { rows?: number; columns?: number; className?: string }) => {
  return (
    <div className={cn('space-y-3', className)}>
      {/* Header */}
      <div className="flex space-x-4">
        {Array.from({ length: columns }).map((_, i) => (
          <Skeleton key={`header-${i}`} className="h-4 flex-1" />
        ))}
      </div>
      {/* Rows */}
      {Array.from({ length: rows }).map((_, rowIndex) => (
        <div key={`row-${rowIndex}`} className="flex space-x-4">
          {Array.from({ length: columns }).map((_, colIndex) => (
            <Skeleton key={`cell-${rowIndex}-${colIndex}`} className="h-4 flex-1" />
          ))}
        </div>
      ))}
    </div>
  );
};

const SkeletonList = ({ items = 5, className }: { items?: number; className?: string }) => {
  return (
    <div className={cn('space-y-4', className)}>
      {Array.from({ length: items }).map((_, i) => (
        <div key={i} className="flex items-center space-x-3">
          <SkeletonAvatar size="sm" />
          <div className="flex-1 space-y-2">
            <Skeleton className="h-4 w-3/4" />
            <Skeleton className="h-3 w-1/2" />
          </div>
        </div>
      ))}
    </div>
  );
};

// Chat-specific skeleton
const SkeletonChatMessage = ({ isUser = false, className }: { isUser?: boolean; className?: string }) => {
  return (
    <div className={cn('flex gap-3', isUser ? 'justify-end' : 'justify-start', className)}>
      {!isUser && <SkeletonAvatar size="sm" />}
      <div className={cn('space-y-2 max-w-xs', isUser ? 'items-end' : 'items-start')}>
        <Skeleton className="h-4 w-32" />
        <div className={cn('rounded-lg p-3 space-y-2', isUser ? 'bg-primary/10' : 'bg-muted')}>
          <SkeletonText lines={2} />
        </div>
      </div>
      {isUser && <SkeletonAvatar size="sm" />}
    </div>
  );
};

const SkeletonChatHistory = ({ messages = 5, className }: { messages?: number; className?: string }) => {
  return (
    <div className={cn('space-y-4', className)}>
      {Array.from({ length: messages }).map((_, i) => (
        <SkeletonChatMessage key={i} isUser={i % 2 === 0} />
      ))}
    </div>
  );
};

export {
  Skeleton,
  SkeletonText,
  SkeletonCard,
  SkeletonAvatar,
  SkeletonButton,
  SkeletonTable,
  SkeletonList,
  SkeletonChatMessage,
  SkeletonChatHistory,
};