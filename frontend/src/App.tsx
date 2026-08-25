import { useState, useEffect } from 'react';
import { Navigation } from './components/Navigation';
import { DashboardOverview } from './components/DashboardOverview';
import { OnboardingWizard } from './components/OnboardingWizard';
import { PaymentRequestsList } from './components/PaymentRequestsList';
import { TransactionsExplorer } from './components/TransactionsExplorer';
import { WhatsAppHub } from './components/WhatsAppHub';
import { SandboxSimulator } from './components/SandboxSimulator';
import { PublicCheckout } from './components/PublicCheckout';
import { AuditLogsView } from './components/AuditLogsView';
import { SettingsView } from './components/SettingsView';
import { MagicLinkReport } from './components/MagicLinkReport';
import { StepUpConfirm } from './components/StepUpConfirm';
import { api } from './services/api';
import type { DashboardSummary, PaymentRequest, Transaction, MerchantProfile, WhatsAppAccount, PaymentProviderAccount } from './types';

export function App() {
  const [currentTab, setCurrentTab] = useState('dashboard');
  const [showOnboarding, setShowOnboarding] = useState(false);
  const [checkoutToken, setCheckoutToken] = useState<string | null>(null);
  const [magicReportToken, setMagicReportToken] = useState<string | null>(null);
  const [stepUpToken, setStepUpToken] = useState<string | null>(null);

  // App Data
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [requests, setRequests] = useState<PaymentRequest[]>([]);
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [merchantProfile, setMerchantProfile] = useState<MerchantProfile | null>(null);
  const [whatsapp, setWhatsapp] = useState<WhatsAppAccount | null>(null);
  const [provider, setProvider] = useState<PaymentProviderAccount | null>(null);
  const [tenantName, setTenantName] = useState('Nairobi Tech Supplies');

  useEffect(() => {
    const path = window.location.pathname;
    if (path.startsWith('/p/')) {
      const token = path.replace('/p/', '');
      if (token) {
        setCheckoutToken(token);
      }
    } else if (path.startsWith('/view/report/')) {
      const token = path.replace('/view/report/', '');
      if (token) {
        setMagicReportToken(token);
      }
    } else if (path.startsWith('/view/step-up/')) {
      const token = path.replace('/view/step-up/', '');
      if (token) {
        setStepUpToken(token);
      }
    }
  }, []);

  const loadData = async () => {
    try {
      const [merchantData, summaryData, reqsData, txsData] = await Promise.all([
        api.getMerchantMe(),
        api.getDashboardSummary(),
        api.getPaymentRequests(),
        api.getTransactions()
      ]);

      if (merchantData.tenant) setTenantName(merchantData.tenant.name);
      if (merchantData.profile) setMerchantProfile(merchantData.profile);
      if (merchantData.whatsapp) setWhatsapp(merchantData.whatsapp);
      if (merchantData.provider) setProvider(merchantData.provider);

      setSummary(summaryData);
      setRequests(reqsData.length ? reqsData : summaryData.recent_requests || []);
      setTransactions(txsData.length ? txsData : summaryData.recent_transactions || []);
    } catch (err) {
      console.error('Failed to load merchant data', err);
    }
  };

  useEffect(() => {
    loadData();
    const interval = setInterval(() => {
      loadData();
    }, 5000);
    return () => clearInterval(interval);
  }, []);

  if (checkoutToken) {
    return (
      <PublicCheckout
        publicToken={checkoutToken}
        onBackToDashboard={() => {
          window.history.pushState({}, '', '/');
          setCheckoutToken(null);
        }}
      />
    );
  }

  if (magicReportToken) {
    return (
      <MagicLinkReport
        token={magicReportToken}
        onClose={() => {
          window.history.pushState({}, '', '/');
          setMagicReportToken(null);
        }}
      />
    );
  }

  if (stepUpToken) {
    return (
      <StepUpConfirm
        token={stepUpToken}
        onClose={() => {
          window.history.pushState({}, '', '/');
          setStepUpToken(null);
        }}
      />
    );
  }

  return (
    <div className="min-h-screen bg-[#0A0F1D] text-slate-100 flex flex-col md:flex-row">
      <Navigation
        currentTab={currentTab}
        setCurrentTab={setCurrentTab}
        tenantName={tenantName}
        onOpenOnboarding={() => setShowOnboarding(true)}
      />

      <main className="flex-1 p-6 md:p-8 max-w-7xl mx-auto overflow-y-auto">
        {currentTab === 'dashboard' && (
          <DashboardOverview
            summary={summary}
            onRequestNewPayment={() => setCurrentTab('payment-requests')}
            onSelectRequest={(req) => setCheckoutToken(req.public_token)}
            onOpenSimulator={() => setCurrentTab('simulator')}
          />
        )}

        {currentTab === 'payment-requests' && (
          <PaymentRequestsList
            requests={requests}
            onRefresh={loadData}
            onOpenCheckout={(token) => setCheckoutToken(token)}
          />
        )}

        {currentTab === 'transactions' && (
          <TransactionsExplorer transactions={transactions} />
        )}

        {currentTab === 'whatsapp' && (
          <WhatsAppHub whatsapp={whatsapp} onRefresh={loadData} />
        )}

        {currentTab === 'simulator' && (
          <SandboxSimulator requests={requests} onRefresh={loadData} />
        )}

        {currentTab === 'audit' && (
          <AuditLogsView />
        )}

        {currentTab === 'settings' && (
          <SettingsView profile={merchantProfile} provider={provider} onRefresh={loadData} />
        )}
      </main>

      {showOnboarding && (
        <OnboardingWizard
          onComplete={() => {
            setShowOnboarding(false);
            loadData();
          }}
          onClose={() => setShowOnboarding(false)}
        />
      )}
    </div>
  );
}

export default App;
