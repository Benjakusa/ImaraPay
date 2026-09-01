import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { WhatsAppHub } from '../WhatsAppHub';

// Mock the API service
vi.mock('../../services/api', () => ({
    api: {
        sendWhatsAppCommand: vi.fn(),
        getPhoneIdentities: vi.fn().mockResolvedValue([]),
        bindPhoneIdentity: vi.fn(),
    },
}));

describe('WhatsAppHub Component', () => {
    const mockWhatsappProps = {
        id: 'wa-123',
        phone_number_id: '12345',
        display_phone_number: '+254 712 345 678',
        waba_id: 'wa-123',
        status: 'CONNECTED' as const,
        auto_send_receipts: true,
        connected_at: '2026-08-01T00:00:00Z',
    };

    it('renders the chat simulator by default', () => {
        render(<WhatsAppHub whatsapp={mockWhatsappProps} onRefresh={() => { }} />);

        // Check for bot greeting
        expect(screen.getByText(/Welcome to Imara Pay WhatsApp Bot/i)).toBeInTheDocument();

        // Check for the command input
        expect(screen.getByPlaceholderText(/Type WhatsApp command/i)).toBeInTheDocument();
    });

    it('switches to the staff tab and renders the link phone form', () => {
        render(<WhatsAppHub whatsapp={mockWhatsappProps} onRefresh={() => { }} />);

        // Click the staff tab
        const staffTab = screen.getByText(/Linked Phone Numbers/i);
        fireEvent.click(staffTab);

        // Form should appear
        expect(screen.getByText(/Link Phone Number/i)).toBeInTheDocument();
        expect(screen.getByPlaceholderText(/e\.g\. \+254 712 345678/i)).toBeInTheDocument();
        expect(screen.getByText(/Send Verification Code/i)).toBeInTheDocument();
    });
});
