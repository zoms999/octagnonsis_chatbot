import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { useRouter } from 'next/navigation';
import { LoginForm } from './src/components/auth/login-form';
import { useAuth } from './src/providers/auth-provider';

// Mock Next.js router
vi.mock('next/navigation', () => ({
  useRouter: vi.fn(),
}));

// Mock auth provider
vi.mock('./src/providers/auth-provider', () => ({
  useAuth: vi.fn(),
}));

const mockPush = vi.fn();
const mockLogin = vi.fn();
const mockClearError = vi.fn();

const defaultAuthState = {
  login: mockLogin,
  isLoading: false,
  error: null,
  clearError: mockClearError,
  isAuthenticated: false,
};

describe('Debug LoginForm', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    
    (useRouter as any).mockReturnValue({
      push: mockPush,
    });

    (useAuth as any).mockReturnValue(defaultAuthState);
  });

  it('should debug form validation', async () => {
    render(<LoginForm />);

    const submitButton = screen.getByRole('button', { name: 'Sign In' });
    
    // Check if mockLogin was called (it shouldn't be if validation works)
    fireEvent.click(submitButton);

    await waitFor(() => {
      // Check if login was called (it shouldn't be if validation fails)
      console.log('mockLogin called:', mockLogin.mock.calls.length);
    });

    // Check if any error elements exist
    const errorElements = screen.queryAllByRole('alert');
    console.log('Error elements found:', errorElements.length);
    
    // Check for any text containing "required"
    const requiredTexts = screen.queryAllByText(/required/i);
    console.log('Required texts found:', requiredTexts.length);
    requiredTexts.forEach((element, index) => {
      console.log(`Required text ${index}:`, element.textContent);
    });

    // Check all elements with error styling
    const container = screen.getByRole('button', { name: 'Sign In' }).closest('form');
    if (container) {
      const allElements = container.querySelectorAll('*');
      console.log('Total elements in form:', allElements.length);
      
      // Look for elements with error classes or text
      const errorClasses = Array.from(allElements).filter(el => 
        el.className.includes('destructive') || 
        el.textContent?.includes('required')
      );
      console.log('Elements with error styling:', errorClasses.length);
      errorClasses.forEach((el, i) => {
        console.log(`Error element ${i}:`, el.textContent, el.className);
      });
    }
  });
});