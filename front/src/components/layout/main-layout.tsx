'use client';

import * as React from 'react';
import { useAuth } from '@/providers/auth-provider';
import { Header } from './header';
import { Sidebar } from './sidebar';
import { cn } from '@/lib/utils';

interface MainLayoutProps {
  children: React.ReactNode;
  sidebar?: React.ReactNode;
  showSidebar?: boolean;
  sidebarTitle?: string;
  className?: string;
}

const MainLayout = ({ 
  children, 
  sidebar, 
  showSidebar = false, 
  sidebarTitle,
  className 
}: MainLayoutProps) => {
  const { isAuthenticated, isLoading } = useAuth();
  const [isSidebarCollapsed, setIsSidebarCollapsed] = React.useState(false);
  const [isMobile, setIsMobile] = React.useState(false);

  // Handle responsive behavior
  React.useEffect(() => {
    const checkMobile = () => {
      const mobile = window.innerWidth < 1024; // lg breakpoint
      setIsMobile(mobile);
      
      // Auto-collapse sidebar on mobile
      if (mobile && !isSidebarCollapsed) {
        setIsSidebarCollapsed(true);
      }
    };

    checkMobile();
    window.addEventListener('resize', checkMobile);
    return () => window.removeEventListener('resize', checkMobile);
  }, [isSidebarCollapsed]);

  // Don't render layout for unauthenticated users
  if (!isAuthenticated && !isLoading) {
    return <>{children}</>;
  }

  // Show loading state
  if (isLoading) {
    return (
      <div className="h-screen flex items-center justify-center">
        <div className="flex flex-col items-center space-y-4">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
          <p className="text-sm text-muted-foreground">로딩 중...</p>
        </div>
      </div>
    );
  }

  return (
    <div className={cn('min-h-screen bg-background', className)}>
      {/* Header */}
      <Header />

      {/* Main Content Area */}
      <div className="flex h-[calc(100vh-4rem)]"> {/* Subtract header height */}
        {/* Main Content */}
        <main 
          className={cn(
            'flex-1 overflow-auto',
            showSidebar && !isSidebarCollapsed && 'lg:mr-80' // Account for sidebar width
          )}
        >
          <div className="container mx-auto p-4 h-full">
            {children}
          </div>
        </main>

        {/* Sidebar */}
        {showSidebar && (
          <Sidebar
            title={sidebarTitle}
            isCollapsed={isSidebarCollapsed}
            onToggle={() => setIsSidebarCollapsed(!isSidebarCollapsed)}
            className={cn(
              'fixed right-0 top-16 h-[calc(100vh-4rem)] z-30',
              'lg:relative lg:top-0 lg:h-full lg:z-auto'
            )}
          >
            {sidebar}
          </Sidebar>
        )}
      </div>

      {/* Mobile Sidebar Backdrop */}
      {showSidebar && !isSidebarCollapsed && isMobile && (
        <div
          className="fixed inset-0 bg-black/50 z-20 lg:hidden"
          onClick={() => setIsSidebarCollapsed(true)}
          aria-hidden="true"
        />
      )}
    </div>
  );
};

// Specialized layout for chat pages with document panel
interface ChatLayoutProps {
  children: React.ReactNode;
  documents?: Array<{
    id: string;
    title: string;
    preview: string;
    relevance_score: number;
    type: string;
  }>;
  className?: string;
}

const ChatLayout = ({ children, documents = [], className }: ChatLayoutProps) => {
  return (
    <MainLayout
      showSidebar={true}
      sidebarTitle="참조 문서"
      sidebar={
        <div className="p-4 space-y-4">
          {documents.length === 0 ? (
            <div className="text-center text-muted-foreground py-8">
              <svg className="h-12 w-12 mx-auto mb-4 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              <p className="text-sm">참조된 문서가 없습니다</p>
              <p className="text-xs text-muted-foreground mt-1">
                질문을 하시면 관련 문서가 여기에 표시됩니다
              </p>
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
      }
      className={className}
    >
      {children}
    </MainLayout>
  );
};

// Simple layout for pages that don't need sidebar
interface SimpleLayoutProps {
  children: React.ReactNode;
  className?: string;
}

const SimpleLayout = ({ children, className }: SimpleLayoutProps) => {
  return (
    <MainLayout className={className}>
      {children}
    </MainLayout>
  );
};

export { MainLayout, ChatLayout, SimpleLayout };