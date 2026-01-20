import '@testing-library/jest-dom'
import { render, screen, waitFor } from '@testing-library/react'
import { AuthProvider } from '../components/AuthProvider'
import { onAuthStateChanged } from 'firebase/auth'
import { useRouter, usePathname } from 'next/navigation'

// Mock Firebase
jest.mock('@/lib/firebase', () => ({
  auth: {},
}));

jest.mock('firebase/auth', () => ({
  onAuthStateChanged: jest.fn(),
}));

// Mock Next Navigation
jest.mock('next/navigation', () => ({
  useRouter: jest.fn(),
  usePathname: jest.fn(),
}));

describe('AuthProvider', () => {
  const mockPush = jest.fn();
  
  beforeEach(() => {
    jest.clearAllMocks();
    (useRouter as jest.Mock).mockReturnValue({ push: mockPush });
  });

  it('renders loading state initially', () => {
    (onAuthStateChanged as jest.Mock).mockImplementation(() => jest.fn());
    (usePathname as jest.Mock).mockReturnValue('/protected');

    render(
      <AuthProvider>
        <div>Protected Content</div>
      </AuthProvider>
    );

    expect(screen.getByText('Loading...')).toBeInTheDocument();
  });

  it('redirects to login if user is null and path is protected', async () => {
    // Simulate no user
    (onAuthStateChanged as jest.Mock).mockImplementation((auth, callback) => {
      callback(null); // No user
      return jest.fn(); // Unsubscribe
    });
    (usePathname as jest.Mock).mockReturnValue('/protected');

    render(
      <AuthProvider>
        <div>Protected Content</div>
      </AuthProvider>
    );

    await waitFor(() => {
      expect(mockPush).toHaveBeenCalledWith('/login');
    });
  });

  it('renders children if user is authenticated', async () => {
    // Simulate user
    (onAuthStateChanged as jest.Mock).mockImplementation((auth, callback) => {
      callback({ uid: '123' }); // Authenticated
      return jest.fn();
    });
    (usePathname as jest.Mock).mockReturnValue('/protected');

    render(
      <AuthProvider>
        <div>Protected Content</div>
      </AuthProvider>
    );

    await waitFor(() => {
      expect(screen.getByText('Protected Content')).toBeInTheDocument();
      expect(mockPush).not.toHaveBeenCalled();
    });
  });

  it('allows access to public paths without user', async () => {
    // Simulate no user
    (onAuthStateChanged as jest.Mock).mockImplementation((auth, callback) => {
      callback(null);
      return jest.fn();
    });
    (usePathname as jest.Mock).mockReturnValue('/login');

    render(
      <AuthProvider>
        <div>Login Page</div>
      </AuthProvider>
    );

    await waitFor(() => {
      expect(screen.getByText('Login Page')).toBeInTheDocument();
      expect(mockPush).not.toHaveBeenCalled();
    });
  });
});
