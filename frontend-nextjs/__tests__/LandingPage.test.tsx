import '@testing-library/jest-dom'
import { render, screen } from '@testing-library/react'
import LandingPage from '../app/page'

describe('LandingPage', () => {
  beforeEach(() => {
    render(<LandingPage />)
  })

  it('renders the main heading', () => {
    const heading = screen.getByRole('heading', { level: 1 })
    expect(heading).toBeInTheDocument()
    expect(heading).toHaveTextContent('Enterprise AI Agent')
  })

  it('renders the secure shield icon', () => {
    expect(screen.getByLabelText('Secure Shield Icon')).toBeInTheDocument()
  })

  it('renders the secure pipeline sub-heading', () => {
    expect(screen.getByText('Secure RAG Pipeline v2.0')).toBeInTheDocument()
  })

  it('renders the access initialization link correctly', () => {
    const link = screen.getByRole('link', { name: /Initialize Access/i })
    expect(link).toBeInTheDocument()
    expect(link).toHaveAttribute('href', '/payment')
  })

  it('renders the security footer', () => {
    expect(screen.getByText(/End-to-End Encrypted/i)).toBeInTheDocument()
    expect(screen.getByText(/DLP Guardrails Active/i)).toBeInTheDocument()
  })
})