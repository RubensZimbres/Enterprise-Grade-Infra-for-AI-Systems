import '@testing-library/jest-dom'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import ChatPage from '../app/chat/page'
import { auth } from '@/lib/firebase'

// Mock Firebase Auth
jest.mock('@/lib/firebase', () => ({
  auth: {
    currentUser: {
      getIdToken: jest.fn(),
    },
  },
}));

// Mock Next Navigation
jest.mock('next/navigation', () => ({
  useRouter: () => ({
    push: jest.fn(),
  }),
}));

// Mock fetch
global.fetch = jest.fn();

describe('ChatPage', () => {
  const mockScrollIntoView = jest.fn();

  beforeAll(() => {
    // Mock scrollIntoView
    Element.prototype.scrollIntoView = mockScrollIntoView;
    // Mock TextDecoder
    global.TextDecoder = class {
      decode(chunk: any) {
        return chunk ? String.fromCharCode(...chunk) : '';
      }
    } as any;
  });

  beforeEach(() => {
    jest.clearAllMocks();
    (auth.currentUser?.getIdToken as jest.Mock).mockResolvedValue('mock-token');
    
    // Default fetch mock to prevent undefined errors
    (global.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      status: 200,
      body: {
        getReader: () => ({
          read: jest.fn()
            .mockResolvedValueOnce({ done: false, value: new Uint8Array([79, 75]) }) // "OK"
            .mockResolvedValueOnce({ done: true, value: undefined }),
        }),
      },
      json: jest.fn().mockResolvedValue({}),
    });
  });

  it('renders input and empty state', () => {
    render(<ChatPage />);
    expect(screen.getByPlaceholderText(/Query the internal knowledge base/i)).toBeInTheDocument();
    expect(screen.getByText(/Welcome to the Secure Knowledge Base/i)).toBeInTheDocument();
  });

  it('sends a message and displays user input', async () => {
    render(<ChatPage />);
    const input = screen.getByPlaceholderText(/Query the internal knowledge base/i);
    const button = screen.getByRole('button');

    fireEvent.change(input, { target: { value: 'Hello AI' } });
    fireEvent.click(button);

    // Should show user message
    expect(screen.getByText('Hello AI')).toBeInTheDocument();
    // Input should be cleared
    expect(input).toHaveValue('');

    // Wait for the async operation to complete to avoid act warnings
    await waitFor(() => {
      expect(screen.getByText('OK')).toBeInTheDocument();
    });
  });

  it('displays streaming response', async () => {
    // Mock streaming response
    const mockStream = new ReadableStream({
      start(controller) {
        controller.enqueue(new Uint8Array([72, 101, 108, 108, 111])); // "Hello"
        controller.close();
      },
    });

    (global.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      status: 200,
      body: {
        getReader: () => mockStream.getReader(),
      },
    });

    render(<ChatPage />);
    const input = screen.getByPlaceholderText(/Query the internal knowledge base/i);
    const button = screen.getByRole('button');

    fireEvent.change(input, { target: { value: 'Hi' } });
    fireEvent.click(button);

    await waitFor(() => {
      expect(screen.getByText(/Hello/i)).toBeInTheDocument();
    });
  });

  it('handles errors gracefully', async () => {
    (global.fetch as jest.Mock).mockRejectedValue(new Error('Network error'));

    render(<ChatPage />);
    const input = screen.getByPlaceholderText(/Query the internal knowledge base/i);
    const button = screen.getByRole('button');

    fireEvent.change(input, { target: { value: 'Hi' } });
    fireEvent.click(button);

    await waitFor(() => {
      expect(screen.getByText(/Error: Network error/i)).toBeInTheDocument();
    });
  });
});
