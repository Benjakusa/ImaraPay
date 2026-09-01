import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { PaymentRequestsList } from '../PaymentRequestsList';

describe('PaymentRequestsList Component', () => {
    it('renders empty state correctly', () => {
        render(<PaymentRequestsList requests={[]} onRefresh={() => { }} onOpenCheckout={() => { }} />);

        expect(screen.getByText(/No payment requests found/i)).toBeInTheDocument();
        expect(screen.getByText(/Create New Request/i)).toBeInTheDocument();
    });

    it('renders a list of payment requests', () => {
        const mockRequests = [
            {
                id: 'req-1',
                public_token: 'tok-1',
                amount_minor: 2500,
                currency: 'KES',
                reference: 'INV-001',
                description: 'Test Inv',
                customer_phone: '254700000000',
                status: 'SUCCEEDED' as const,
                expires_at: '2026-09-02T00:00:00Z',
                created_at: '2026-09-01T00:00:00Z',
                checkout_url: 'http://localhost/pay/tok-1',
                is_expired: false,
            }
        ];

        render(<PaymentRequestsList requests={mockRequests as any} onRefresh={() => { }} onOpenCheckout={() => { }} />);

        expect(screen.getByText('INV-001')).toBeInTheDocument();
        expect(screen.getByText(/KES 2,500/i)).toBeInTheDocument();
        expect(screen.getByText('SUCCEEDED')).toBeInTheDocument();
    });
});
