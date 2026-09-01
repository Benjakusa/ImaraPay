import { useState, useEffect, type FormEvent } from 'react';
import type { PhoneIdentity } from '../types';
import { api } from '../services/api';

export interface UsePhoneIdentitiesReturn {
    identities: PhoneIdentity[];
    newPhone: string;
    setNewPhone: (v: string) => void;
    newRole: 'ADMIN' | 'STAFF';
    setNewRole: (v: 'ADMIN' | 'STAFF') => void;
    otpVerifyPhone: string | null;
    otpInput: string;
    setOtpInput: (v: string) => void;
    devOtp: string | null;
    staffError: string;
    staffSuccess: string;
    handleAddPhone: (e: FormEvent) => Promise<void>;
    handleVerifyOTP: (e: FormEvent) => Promise<void>;
    handleRevokePhone: (id: string) => Promise<void>;
    cancelOtp: () => void;
    loadIdentities: () => Promise<void>;
}

/**
 * Encapsulates all state and async handlers for phone-identity management
 * (add phone, OTP verify, revoke). Shared between WhatsAppHub and SettingsView.
 */
export function usePhoneIdentities(): UsePhoneIdentitiesReturn {
    const [identities, setIdentities] = useState<PhoneIdentity[]>([]);
    const [newPhone, setNewPhone] = useState('');
    const [newRole, setNewRole] = useState<'ADMIN' | 'STAFF'>('STAFF');
    const [otpVerifyPhone, setOtpVerifyPhone] = useState<string | null>(null);
    const [otpInput, setOtpInput] = useState('');
    const [devOtp, setDevOtp] = useState<string | null>(null);
    const [staffError, setStaffError] = useState('');
    const [staffSuccess, setStaffSuccess] = useState('');

    const loadIdentities = async () => {
        try {
            const data = await api.getPhoneIdentities();
            setIdentities(data);
        } catch (err) {
            console.error('Failed to load identities', err);
        }
    };

    useEffect(() => {
        loadIdentities();
    }, []);

    const handleAddPhone = async (e: FormEvent) => {
        e.preventDefault();
        setStaffError('');
        setStaffSuccess('');
        setDevOtp(null);

        if (!newPhone.trim()) {
            setStaffError('Please enter a phone number');
            return;
        }

        try {
            const res = await api.bindPhoneIdentity(newPhone, newRole);
            setOtpVerifyPhone(newPhone);
            setStaffSuccess(res.message || 'OTP sent successfully!');
            if (res.dev_otp) setDevOtp(res.dev_otp);
        } catch (err: any) {
            setStaffError(err.response?.data?.error || 'Failed to bind phone number');
        }
    };

    const handleVerifyOTP = async (e: FormEvent) => {
        e.preventDefault();
        setStaffError('');
        setStaffSuccess('');

        if (!otpVerifyPhone || !otpInput) return;

        try {
            await api.confirmPhoneOTP(otpVerifyPhone, otpInput);
            setStaffSuccess(`Successfully verified and linked ${otpVerifyPhone}!`);
            setOtpVerifyPhone(null);
            setOtpInput('');
            setNewPhone('');
            setDevOtp(null);
            loadIdentities();
        } catch (err: any) {
            setStaffError(err.response?.data?.error || 'Invalid or expired OTP');
        }
    };

    const handleRevokePhone = async (id: string) => {
        setStaffError('');
        setStaffSuccess('');

        if (!confirm('Are you sure you want to revoke this phone identity?')) return;

        try {
            await api.revokePhoneIdentity(id);
            setStaffSuccess('Phone number access revoked.');
            loadIdentities();
        } catch (err: any) {
            setStaffError(err.response?.data?.error || 'Failed to revoke phone number');
        }
    };

    const cancelOtp = () => {
        setOtpVerifyPhone(null);
        setStaffSuccess('');
        setDevOtp(null);
    };

    return {
        identities,
        newPhone,
        setNewPhone,
        newRole,
        setNewRole,
        otpVerifyPhone,
        otpInput,
        setOtpInput,
        devOtp,
        staffError,
        staffSuccess,
        handleAddPhone,
        handleVerifyOTP,
        handleRevokePhone,
        cancelOtp,
        loadIdentities,
    };
}
