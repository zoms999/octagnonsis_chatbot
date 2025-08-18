import { describe, it, expect } from 'vitest';
import { validateLoginCredentials } from '../auth';
import { LoginCredentials } from '../types';

describe('Form Validation Utilities', () => {
  describe('validateLoginCredentials', () => {
    describe('Personal login validation', () => {
      it('should pass validation for valid personal credentials', () => {
        const credentials: LoginCredentials = {
          username: 'testuser',
          password: 'password123',
          loginType: 'personal',
        };

        const errors = validateLoginCredentials(credentials);
        expect(errors).toHaveLength(0);
      });

      it('should fail validation for missing username', () => {
        const credentials: LoginCredentials = {
          username: '',
          password: 'password123',
          loginType: 'personal',
        };

        const errors = validateLoginCredentials(credentials);
        expect(errors).toContain('Username is required');
      });

      it('should fail validation for whitespace-only username', () => {
        const credentials: LoginCredentials = {
          username: '   ',
          password: 'password123',
          loginType: 'personal',
        };

        const errors = validateLoginCredentials(credentials);
        expect(errors).toContain('Username is required');
      });

      it('should fail validation for missing password', () => {
        const credentials: LoginCredentials = {
          username: 'testuser',
          password: '',
          loginType: 'personal',
        };

        const errors = validateLoginCredentials(credentials);
        expect(errors).toContain('Password is required');
      });

      it('should fail validation for whitespace-only password', () => {
        const credentials: LoginCredentials = {
          username: 'testuser',
          password: '   ',
          loginType: 'personal',
        };

        const errors = validateLoginCredentials(credentials);
        expect(errors).toContain('Password is required');
      });

      it('should not require session code for personal login', () => {
        const credentials: LoginCredentials = {
          username: 'testuser',
          password: 'password123',
          loginType: 'personal',
          sessionCode: '', // Empty session code should be fine for personal
        };

        const errors = validateLoginCredentials(credentials);
        expect(errors).not.toContain('Session code is required for organization login');
      });
    });

    describe('Organization login validation', () => {
      it('should pass validation for valid organization credentials', () => {
        const credentials: LoginCredentials = {
          username: 'testuser',
          password: 'password123',
          loginType: 'organization',
          sessionCode: 'ABC123',
        };

        const errors = validateLoginCredentials(credentials);
        expect(errors).toHaveLength(0);
      });

      it('should fail validation for missing session code', () => {
        const credentials: LoginCredentials = {
          username: 'testuser',
          password: 'password123',
          loginType: 'organization',
        };

        const errors = validateLoginCredentials(credentials);
        expect(errors).toContain('Session code is required for organization login');
      });

      it('should fail validation for empty session code', () => {
        const credentials: LoginCredentials = {
          username: 'testuser',
          password: 'password123',
          loginType: 'organization',
          sessionCode: '',
        };

        const errors = validateLoginCredentials(credentials);
        expect(errors).toContain('Session code is required for organization login');
      });

      it('should fail validation for whitespace-only session code', () => {
        const credentials: LoginCredentials = {
          username: 'testuser',
          password: 'password123',
          loginType: 'organization',
          sessionCode: '   ',
        };

        const errors = validateLoginCredentials(credentials);
        expect(errors).toContain('Session code is required for organization login');
      });

      it('should still validate username and password for organization login', () => {
        const credentials: LoginCredentials = {
          username: '',
          password: '',
          loginType: 'organization',
          sessionCode: 'ABC123',
        };

        const errors = validateLoginCredentials(credentials);
        expect(errors).toContain('Username is required');
        expect(errors).toContain('Password is required');
        expect(errors).not.toContain('Session code is required for organization login');
      });
    });

    describe('Multiple validation errors', () => {
      it('should return all validation errors for completely empty personal credentials', () => {
        const credentials: LoginCredentials = {
          username: '',
          password: '',
          loginType: 'personal',
        };

        const errors = validateLoginCredentials(credentials);
        expect(errors).toHaveLength(2);
        expect(errors).toContain('Username is required');
        expect(errors).toContain('Password is required');
      });

      it('should return all validation errors for completely empty organization credentials', () => {
        const credentials: LoginCredentials = {
          username: '',
          password: '',
          loginType: 'organization',
          sessionCode: '',
        };

        const errors = validateLoginCredentials(credentials);
        expect(errors).toHaveLength(3);
        expect(errors).toContain('Username is required');
        expect(errors).toContain('Password is required');
        expect(errors).toContain('Session code is required for organization login');
      });

      it('should return errors in consistent order', () => {
        const credentials: LoginCredentials = {
          username: '',
          password: '',
          loginType: 'organization',
          sessionCode: '',
        };

        const errors = validateLoginCredentials(credentials);
        expect(errors[0]).toBe('Username is required');
        expect(errors[1]).toBe('Password is required');
        expect(errors[2]).toBe('Session code is required for organization login');
      });
    });

    describe('Edge cases', () => {
      it('should handle undefined values gracefully', () => {
        const credentials: LoginCredentials = {
          username: undefined as any,
          password: undefined as any,
          loginType: 'personal',
        };

        const errors = validateLoginCredentials(credentials);
        expect(errors).toContain('Username is required');
        expect(errors).toContain('Password is required');
      });

      it('should handle null values gracefully', () => {
        const credentials: LoginCredentials = {
          username: null as any,
          password: null as any,
          loginType: 'organization',
          sessionCode: null as any,
        };

        const errors = validateLoginCredentials(credentials);
        expect(errors).toContain('Username is required');
        expect(errors).toContain('Password is required');
        expect(errors).toContain('Session code is required for organization login');
      });

      it('should trim whitespace when checking for empty values', () => {
        const credentials: LoginCredentials = {
          username: '  testuser  ',
          password: '  password123  ',
          loginType: 'organization',
          sessionCode: '  ABC123  ',
        };

        const errors = validateLoginCredentials(credentials);
        expect(errors).toHaveLength(0);
      });

      it('should handle very long input values', () => {
        const longString = 'a'.repeat(1000);
        const credentials: LoginCredentials = {
          username: longString,
          password: longString,
          loginType: 'organization',
          sessionCode: longString,
        };

        const errors = validateLoginCredentials(credentials);
        expect(errors).toHaveLength(0);
      });

      it('should handle special characters in input values', () => {
        const credentials: LoginCredentials = {
          username: 'test@user.com',
          password: 'p@ssw0rd!#$%',
          loginType: 'organization',
          sessionCode: 'ABC-123_XYZ',
        };

        const errors = validateLoginCredentials(credentials);
        expect(errors).toHaveLength(0);
      });

      it('should handle unicode characters in input values', () => {
        const credentials: LoginCredentials = {
          username: 'тестuser',
          password: 'пароль123',
          loginType: 'organization',
          sessionCode: 'АБВ123',
        };

        const errors = validateLoginCredentials(credentials);
        expect(errors).toHaveLength(0);
      });
    });
  });
});