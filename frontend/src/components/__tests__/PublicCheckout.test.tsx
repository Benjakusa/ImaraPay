import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { PublicCheckout } from '../PublicCheckout';
import { api } from '../../services/api';

vi.mock('../../services/api', () => ({
    api: {
        getCheckoutDetails: vi.fn(),
    },
}));

describe('PublicCheckout Component', () => {
    const mockRequest = {
        id: 'req-1',
        public_token: 'tok-1',
        merchant_name: 'Imara Tech',
        amount_minor: 50000,
        currency: 'KES',
        reference: 'INV-001',
        description: 'Service Fee',
        customer_phone: '',
        status: 'CREATED' as const,
        expires_at: '2026-09-02T00:00:00Z',
        is_expired: false,
    };

    it('renders checkout details correctly', async () => {
        vi.mocked(api.getCheckoutDetails).mockResolvedValue(mockRequest);

        render(<PublicCheckout publicToken="tok-1" onBackToDashboard={() => { }} />);

        // Test for loading state initially
        expect(screen.getByText(/Loading Secure Checkout/i)).toBeInTheDocument();

        // Check merchant and amount after load
        expect(await screen.findByText('Imara Tech')).toBeInTheDocument();
        expect(screen.getByText('KES 50,000')).toBeInTheDocument(); // 50000 minor = 50,000 formatted

        // Check form
        expect(screen.getByPlaceholderText('0712 345 678')).toBeInTheDocument();
    });
});
