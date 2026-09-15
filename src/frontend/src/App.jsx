import React, { useState, useEffect } from 'react';
import Navbar from './components/Navbar';
import Landing from './pages/Landing';
import Dashboard from './pages/Dashboard';
import Validation from './pages/Validation';
import AtRisk from './pages/AtRisk';
import ChatPanel from './components/ChatPanel';
import ErrorBoundary from './components/ErrorBoundary';
import { api } from './lib/api';

export default function App() {
  const [currentRoute, setCurrentRoute] = useState('landing');
  const [lots, setLots] = useState([]);
  const [selectedLotId, setSelectedLotId] = useState('LOT-2231');
  const [selectedLot, setSelectedLot] = useState(null);
  const [defects, setDefects] = useState([]);
  const [findings, setFindings] = useState(null);
  const [tier, setTier] = useState('tier2'); // 'tier2' (Calibrated ML) or 'tier1' (Heuristic)
  const [atRiskBatches, setAtRiskBatches] = useState([]);
  const [validationData, setValidationData] = useState(null);
  const [isChatOpen, setIsChatOpen] = useState(false);
  const [heldLots, setHeldLots] = useState({});
  const [isLoading, setIsLoading] = useState(true);

  // 1. Fetch Lots and initial data on mount
  useEffect(() => {
    async function initData() {
      setIsLoading(true);
      try {
        const [lotsRes, riskRes, valRes] = await Promise.all([
          api.getLots().catch(() => ({ lots: [] })),
          api.getPredictRisk().catch(() => ({ batches: [] })),
          api.getValidationMetrics().catch(() => null),
        ]);

        if (lotsRes.lots && lotsRes.lots.length > 0) {
          setLots(lotsRes.lots);
          // Find an excursion lot like LOT-2231 or first excursion lot
          const target = lotsRes.lots.find((l) => l.lot_id === 'LOT-2231') ||
                         lotsRes.lots.find((l) => l.final_yield_pct !== null && l.final_yield_pct < 90) ||
                         lotsRes.lots[0];
          setSelectedLotId(target.lot_id);
          setSelectedLot(target);
        }

        if (riskRes.batches) {
          setAtRiskBatches(riskRes.batches);
        }

        if (valRes) {
          setValidationData(valRes);
        }
      } catch (err) {
        console.warn('Initial data load error:', err);
      } finally {
        setIsLoading(false);
      }
    }
    initData();
  }, []);

  // 2. Fetch lot-specific data when selectedLotId or tier changes
  useEffect(() => {
    if (!selectedLotId) return;

    // Update selectedLot object
    const found = lots.find((l) => l.lot_id === selectedLotId);
    if (found) setSelectedLot(found);

    async function loadLotData() {
      try {
        const [defectsRes, rcRes] = await Promise.all([
          api.getDefects(selectedLotId, 1500).catch(() => ({ defects: [] })),
          api.getRootCause(selectedLotId, tier).catch(() => null),
        ]);

        setDefects(defectsRes.defects || []);
        if (rcRes) setFindings(rcRes);
      } catch (err) {
        console.warn('Lot data load error:', err);
      }
    }
    loadLotData();
  }, [selectedLotId, tier, lots]);

  // Handle lot selection
  const handleSelectLot = (lotId) => {
    setSelectedLotId(lotId);
    const found = lots.find((l) => l.lot_id === lotId);
    if (found) setSelectedLot(found);
  };

  // Handle holding lot dispatch
  const handleHoldLot = (lotId) => {
    setHeldLots((prev) => ({
      ...prev,
      [lotId]: !prev[lotId],
    }));
  };

  // Re-fetch lots list after ingesting a new lot
  const handleRefreshLots = async (newLotId) => {
    try {
      const res = await api.getLots();
      if (res.lots && res.lots.length > 0) {
        setLots(res.lots);
        if (newLotId) {
          handleSelectLot(newLotId);
        }
      }
    } catch (err) {
      console.warn('Failed to refresh lots:', err);
    }
  };

  return (
    <div className="min-h-screen bg-canvas text-slate-100 flex flex-col font-sans selection:bg-cyan/30 selection:text-white">
      {/* Top Navigation */}
      <Navbar
        currentRoute={currentRoute}
        onNavigate={setCurrentRoute}
        lots={lots}
        selectedLotId={selectedLotId}
        onSelectLot={handleSelectLot}
        onToggleChat={() => setIsChatOpen(!isChatOpen)}
        isChatOpen={isChatOpen}
      />

      {/* Main Content Pages */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 pt-6">
        <ErrorBoundary>
          {currentRoute === 'landing' && (
            <Landing
              onNavigate={setCurrentRoute}
              onOpenChat={() => setIsChatOpen(true)}
              sampleLot={selectedLot}
              sampleDefects={defects}
            />
          )}

          {currentRoute === 'dashboard' && (
            <Dashboard
              lots={lots}
              selectedLot={selectedLot}
              selectedLotId={selectedLotId}
              onSelectLot={handleSelectLot}
              defects={defects}
              findings={findings}
              tier={tier}
              onChangeTier={setTier}
              atRiskBatches={atRiskBatches}
              heldLots={heldLots}
              onHoldLot={handleHoldLot}
              isLoading={isLoading}
              onRefreshLots={handleRefreshLots}
            />
          )}

          {currentRoute === 'validation' && (
            <Validation
              validationData={validationData}
              onNavigate={setCurrentRoute}
            />
          )}

          {currentRoute === 'at-risk' && (
            <AtRisk
              batches={atRiskBatches}
              onSelectLot={(lotId) => {
                handleSelectLot(lotId);
                setCurrentRoute('dashboard');
              }}
              onHoldLot={handleHoldLot}
              heldLots={heldLots}
              onNavigate={setCurrentRoute}
            />
          )}
        </ErrorBoundary>
      </main>

      {/* Persistent "Ask Bob" Cleanroom Copilot */}
      <ChatPanel
        lotId={selectedLotId}
        isOpen={isChatOpen}
        onClose={() => setIsChatOpen(false)}
        onLotChange={(lot) => {
          // When user switches lot via Past Conversations, also update the app's selected lot
          const found = lots.find((l) => l.lot_id === lot);
          if (found && setSelectedLot) setSelectedLot(found);
        }}
        onInspectFinding={(finding) => {
          setCurrentRoute('dashboard');
        }}
      />
    </div>
  );
}
