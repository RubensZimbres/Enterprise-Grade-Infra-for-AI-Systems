import '@testing-library/jest-dom'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import PaymentClient from '../app/payment/PaymentClient'

// Mock Stripe elements
jest.mock('@stripe/react-stripe-js', () => ({
  EmbeddedCheckoutProvider: ({ children }: any) => <div data-testid="checkout-provider">{children}</div>,
  EmbeddedCheckout: () => <div data-testid="embedded-checkout">Stripe Embedded Checkout</div>,
}));

jest.mock('@stripe/stripe-js', () => ({
  loadStripe: jest.fn().mockResolvedValue({}),
}));

// Mock fetch
global.fetch = jest.fn();

describe('PaymentClient', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders the initial email step', () => {
    render(<PaymentClient publishableKey="pk_test_123" />);
    
    expect(screen.getByText('Payment Details')).toBeInTheDocument();
    expect(screen.getByText('$36.00 USD')).toBeInTheDocument();
    expect(screen.getByLabelText(/Email Address/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Pay with Card/i })).toBeInTheDocument();
  });

  it('transitions to checkout after email submission', async () => {
    // Mock successful API call
    (global.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      json: async () => ({ client_secret: 'test_secret' }),
    });

    render(<PaymentClient publishableKey="pk_test_123" />);

    // Enter email
    const emailInput = screen.getByLabelText(/Email Address/i);
    fireEvent.change(emailInput, { target: { value: 'test@example.com' } });

    // Click submit
    const submitButton = screen.getByRole('button', { name: /Pay with Card/i });
    fireEvent.click(submitButton);

    // Should verify loading state if possible, or wait for next step
    await waitFor(() => {
      expect(screen.getByTestId('checkout-provider')).toBeInTheDocument();
      expect(screen.getByTestId('embedded-checkout')).toBeInTheDocument();
    });

    // Check if fetch was called correctly
    expect(global.fetch).toHaveBeenCalledWith('/api/create-checkout-session', expect.objectContaining({
      method: 'POST',
      body: JSON.stringify({ email: 'test@example.com' }),
    }));
  });

  it('handles API errors', async () => {
    // Mock failed API call
    (global.fetch as jest.Mock).mockResolvedValue({
      ok: false,
      json: async () => ({ error: 'Payment initialization failed' }),
    });

    render(<PaymentClient publishableKey="pk_test_123" />);

    fireEvent.change(screen.getByLabelText(/Email Address/i), { target: { value: 'test@example.com' } });
    fireEvent.click(screen.getByRole('button', { name: /Pay with Card/i }));

    await waitFor(() => {
      expect(screen.getByText('Payment initialization failed')).toBeInTheDocument();
    });
  });
});