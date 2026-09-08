import React, { useState, useEffect } from 'react';
import { Network, MessageSquare, FileText, LayoutDashboard } from 'lucide-react';
import { api } from './services/api';
import { HealthResponse, CaseOverviewStats } from './types';
import { Header } from './components/Header';
import { Sidebar } from './components/Sidebar';
import { NetworkExplorer } from './components/NetworkExplorer/NetworkExplorer';
import { AskQuestion } from './components/AskQuestion/AskQuestion';
import { CaseBreakdown } from './components/CaseBreakdown/CaseBreakdown';
import { OverviewDashboard } from './components/OverviewDashboard/OverviewDashboard';

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<string>('Network Explorer');
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [stats, setStats] = useState<CaseOverviewStats | null>(null);
  const [loadingStats, setLoadingStats] = useState<boolean>(false);

  const fetchStats = async () => {
    setLoadingStats(true);
    try {
      const [h, s] = await Promise.all([api.getHealth(), api.getCaseStats()]);
      setHealth(h);
      setStats(s);
    } catch (err) {
      console.error('Failed to load initial application state:', err);
    } finally {
      setLoadingStats(false);
    }
  };

  useEffect(() => {
    fetchStats();
    const interval = setInterval(() => {
      api.getHealth().then(setHealth).catch(() => {});
    }, 15000);
    return () => clearInterval(interval);
  }, []);

  const tabs = [
    { name: 'Network Explorer', icon: Network },
    { name: 'Ask a Question', icon: MessageSquare },
    { name: 'Case Breakdown', icon: FileText },
    { name: 'Overview Dashboard', icon: LayoutDashboard },
  ];

  return (
    <div className="min-h-screen bg-background text-slate-100 flex flex-col">
      {/* Top Header */}
      <Header health={health} />

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col lg:flex-row">
        {/* Left Sidebar */}
        <Sidebar stats={stats} loading={loadingStats} onRefresh={fetchStats} />

        {/* Center Panel */}
        <main className="flex-1 flex flex-col p-4 sm:p-6 overflow-x-hidden">
          {/* Tab Navigation */}
          <div className="flex items-center gap-2 border-b border-borderDark mb-6 overflow-x-auto">
            {tabs.map((tab) => {
              const Icon = tab.icon;
              const isActive = activeTab === tab.name;
              return (
                <button
                  key={tab.name}
                  onClick={() => setActiveTab(tab.name)}
                  className={`inline-flex items-center gap-2 px-4 py-3 text-xs font-mono font-semibold border-b-2 transition-all whitespace-nowrap ${
                    isActive
                      ? 'border-amberAccent text-amberAccent bg-surface/50'
                      : 'border-transparent text-textMuted hover:text-slate-200 hover:border-slate-700'
                  }`}
                >
                  <Icon className="w-4 h-4" />
                  <span>{tab.name}</span>
                </button>
              );
            })}
          </div>

          {/* Tab Content */}
          <div className="flex-1">
            {activeTab === 'Network Explorer' && <NetworkExplorer />}
            {activeTab === 'Ask a Question' && <AskQuestion />}
            {activeTab === 'Case Breakdown' && <CaseBreakdown />}
            {activeTab === 'Overview Dashboard' && <OverviewDashboard />}
          </div>
        </main>
      </div>
    </div>
  );
};

export default App;

