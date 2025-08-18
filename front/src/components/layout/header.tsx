'use client';

import * as React from 'react';
import Link from 'next/link';
import { useAuth } from '@/providers/auth-provider';
import { Button } from '@/components/ui/button';
import { MobileNavigation } from '@/components/ui/navigation';
import { cn } from '@/lib/utils';

interface HeaderProps {
  className?: string;
}

const Header = ({ className }: HeaderProps) => {
  const { user, logout, isAuthenticated } = useAuth();

  // Navigation items for mobile menu
  const navigationItems = [
    {
      href: '/chat',
      label: 'Chat',
      icon: (
        <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
        </svg>
      ),
    },
    {
      href: '/history',
      label: 'History',
      icon: (
        <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
      ),
    },
    {
      href: '/profile',
      label: 'Profile',
      icon: (
        <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
        </svg>
      ),
    },
    {
      href: '/documents',
      label: 'Documents',
      icon: (
        <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
        </svg>
      ),
    },
    {
      href: '/etl',
      label: 'ETL Status',
      icon: (
        <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
        </svg>
      ),
    },
  ];

  const getUserTypeLabel = (type: string) => {
    switch (type) {
      case 'personal':
        return '개인';
      case 'organization_admin':
        return '기관 관리자';
      case 'organization_member':
        return '기관 구성원';
      default:
        return type;
    }
  };

  const getUserStatusBadge = () => {
    if (!user) return null;

    const isExpired = user.isExpired;
    const isPaid = user.isPaid;
    
    let badgeText = '';
    let badgeColor = '';

    if (isExpired) {
      badgeText = '만료됨';
      badgeColor = 'bg-red-100 text-red-800 border-red-200';
    } else if (isPaid) {
      badgeText = '유료';
      badgeColor = 'bg-green-100 text-green-800 border-green-200';
    } else {
      badgeText = '무료';
      badgeColor = 'bg-blue-100 text-blue-800 border-blue-200';
    }

    return (
      <span className={cn('inline-flex items-center px-2 py-1 rounded-full text-xs font-medium border', badgeColor)}>
        {badgeText}
      </span>
    );
  };

  if (!isAuthenticated) {
    return null;
  }

  return (
    <header className={cn('border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60', className)}>
      <div className="container flex h-16 items-center justify-between px-4">
        {/* Logo */}
        <div className="flex items-center space-x-4">
          <Link href="/chat" className="flex items-center space-x-2">
            <div className="h-8 w-8 rounded-lg bg-primary flex items-center justify-center">
              <svg className="h-5 w-5 text-primary-foreground" fill="currentColor" viewBox="0 0 24 24">
                <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>
              </svg>
            </div>
            <span className="hidden font-bold sm:inline-block">AI 적성 분석</span>
          </Link>
        </div>

        {/* Desktop Navigation - Hidden on mobile */}
        <nav className="hidden md:flex items-center space-x-6" role="navigation" aria-label="Main navigation">
          {navigationItems.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className="flex items-center space-x-1 text-sm font-medium transition-colors hover:text-primary"
            >
              {item.icon}
              <span>{item.label}</span>
            </Link>
          ))}
        </nav>

        {/* User Info and Actions */}
        <div className="flex items-center space-x-4" data-testid="user-menu">
          {/* User Status Badge */}
          <div className="hidden sm:flex items-center space-x-2">
            <div className="text-right">
              <div className="text-sm font-medium">{user?.name}</div>
              <div className="text-xs text-muted-foreground">
                {user?.type && getUserTypeLabel(user.type)}
              </div>
            </div>
            {getUserStatusBadge()}
          </div>

          {/* Logout Button - Desktop */}
          <Button
            variant="ghost"
            size="sm"
            onClick={logout}
            className="hidden sm:flex"
            data-testid="logout-button"
          >
            로그아웃
          </Button>

          {/* Mobile Navigation */}
          <MobileNavigation 
            items={[
              ...navigationItems,
              {
                href: '#',
                label: '로그아웃',
                icon: (
                  <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
                  </svg>
                ),
              },
            ]}
          />
        </div>
      </div>

      {/* Mobile User Info Bar */}
      <div className="sm:hidden border-t px-4 py-2 bg-muted/50">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <span className="text-sm font-medium">{user?.name}</span>
            <span className="text-xs text-muted-foreground">
              ({user?.type && getUserTypeLabel(user.type)})
            </span>
          </div>
          {getUserStatusBadge()}
        </div>
      </div>
    </header>
  );
};

export { Header };