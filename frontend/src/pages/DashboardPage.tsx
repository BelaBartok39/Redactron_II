import { useState, useEffect, useCallback } from 'react';
import { api } from '../api/client';
import type { Stats, Batch, PIITypeCount } from '../types';
import StatsOverview from '../components/StatsOverview';
import BatchCard from '../components/BatchCard';

const PII_BAR_COLORS: Record<string, string> = {
  SSN: '#ef4444',
  US_SSN: '#ef4444',
  CREDIT_CARD: '#ef4444',
  US_BANK_NUMBER: '#ef4444',
  PERSON: '#f97316',
  US_DRIVER_LICENSE: '#f97316',
  US_PASSPORT: '#f97316',
  DATE_OF_BIRTH: '#f97316',
  PHONE_NUMBER: '#eab308',
  EMAIL_ADDRESS: '#eab308',
  LOCATION: '#eab308',
  ADDRESS: '#eab308',
  IP_ADDRESS: '#3b82f6',
  URL: '#3b82f6',
};

function getBarColor(piiType: string): string {
  return PII_BAR_COLORS[piiType] || '#6b7280';
}

export default function DashboardPage() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [batches, setBatches] = useState<Batch[]>([]);
  const [piiTypes, setPiiTypes] = useState<PIITypeCount[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showScanDialog, setShowScanDialog] = useState(false);
  const [scanPath, setScanPath] = useState('');
  const [scanThreshold, setScanThreshold] = useState(0.7);
  const [scanWorkers, setScanWorkers] = useState(4);
  const [scanning, setScanning] = useState(false);
  const [activeBatchId, setActiveBatchId] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    try {
      const [s, b, p] = await Promise.all([
        api.getStats(),
        api.getBatches(),
        api.getPiiTypes(),
      ]);
      setStats(s);
      setBatches(b);
      setPiiTypes(p);
      setError('');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Poll for active batch progress
  useEffect(() => {
    if (!activeBatchId) return;

    const interval = setInterval(async () => {
      try {
        const batch = await api.getBatch(activeBatchId);
        if (batch.status === 'completed' || batch.status === 'error') {
          setActiveBatchId(null);
          setScanning(false);
          loadData();
        } else {
          // Update the batch in the list
          setBatches((prev) =>
            prev.map((b) => (b.id === batch.id ? batch : b))
          );
        }
      } catch {
        // Ignore polling errors
      }
    }, 2000);

    return () => clearInterval(interval);
  }, [activeBatchId, loadData]);

  const handleDeleteBatch = useCallback((id: string) => {
    setBatches((prev) => prev.filter((b) => b.id !== id));
    // Refresh stats since counts changed
    api.getStats().then(setStats).catch(() => {});
    api.getPiiTypes().then(setPiiTypes).catch(() => {});
  }, []);

  const handleClearAll = async () => {
    if (!confirm('Delete ALL batches, documents, and findings? This cannot be undone.')) {
      return;
    }
    try {
      await api.deleteAllBatches();
      loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to clear data');
    }
  };

  const handleStartScan = async () => {
    if (!scanPath.trim()) return;
    setScanning(true);
    try {
      const batch = await api.startScan(scanPath.trim(), {
        confidence_threshold: scanThreshold,
        worker_count: scanWorkers,
      });
      setActiveBatchId(batch.id);
      setShowScanDialog(false);
      setScanPath('');
      loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start scan');
      setScanning(false);
    }
  };

  if (loading) return <div className="loading">Loading dashboard...</div>;
  if (error && !stats) return <div className="error-message">{error}</div>;

  const maxCount = piiTypes.length > 0
    ? Math.max(...piiTypes.map((t) => t.count))
    : 1;

  return (
    <div>
      {stats && <StatsOverview stats={stats} />}

      {error && <div className="error-message" style={{ marginBottom: 16 }}>{error}</div>}

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24, marginBottom: 24 }}>
        {/* PII Distribution */}
        <div className="card">
          <div className="card-header">
            <span className="card-title">PII Type Distribution</span>
          </div>
          {piiTypes.length === 0 ? (
            <p style={{ color: 'var(--text-muted)' }}>No findings yet.</p>
          ) : (
            piiTypes.map((t) => (
              <div key={t.pii_type} className="pii-bar-row">
                <span className="pii-bar-label">{t.pii_type.replace(/_/g, ' ')}</span>
                <div className="pii-bar-track">
                  <div
                    className="pii-bar-fill"
                    style={{
                      width: `${(t.count / maxCount) * 100}%`,
                      background: getBarColor(t.pii_type),
                    }}
                  />
                </div>
                <span className="pii-bar-count">{t.count}</span>
              </div>
            ))
          )}
        </div>

        {/* Scan Progress (if active) */}
        <div className="card">
          <div className="card-header">
            <span className="card-title">Quick Actions</span>
          </div>
          <button
            className="btn btn-primary"
            onClick={() => setShowScanDialog(true)}
            disabled={scanning}
            style={{ width: '100%', justifyContent: 'center', marginBottom: 8 }}
          >
            {scanning ? 'Scan in Progress...' : 'New Scan'}
          </button>
          <button
            className="btn btn-secondary"
            onClick={handleClearAll}
            disabled={scanning || batches.length === 0}
            style={{ width: '100%', justifyContent: 'center', marginBottom: 16 }}
          >
            Clear All Data
          </button>
          {activeBatchId && batches.find((b) => b.id === activeBatchId) && (() => {
            const active = batches.find((b) => b.id === activeBatchId)!;
            const pct = active.total_docs > 0
              ? Math.round((active.processed_docs / active.total_docs) * 100)
              : 0;
            return (
              <div>
                <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: 4 }}>
                  Processing: {active.name}
                </div>
                <div className="progress-bar">
                  <div className="progress-bar-fill" style={{ width: `${pct}%` }} />
                </div>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                  {active.processed_docs} / {active.total_docs} documents ({pct}%)
                </div>
              </div>
            );
          })()}
        </div>
      </div>

      {/* Recent Batches */}
      <div className="section-header">
        <span className="section-title">Recent Batches</span>
      </div>
      <div className="batches-list">
        {batches.length === 0 ? (
          <p style={{ color: 'var(--text-muted)', padding: 16 }}>
            No batches yet. Start a scan to begin.
          </p>
        ) : (
          batches.slice(0, 10).map((batch) => (
            <BatchCard key={batch.id} batch={batch} onDeleted={handleDeleteBatch} />
          ))
        )}
      </div>

      {/* Scan Dialog */}
      {showScanDialog && (
        <div className="dialog-backdrop" onClick={() => setShowScanDialog(false)}>
          <div className="dialog" onClick={(e) => e.stopPropagation()}>
            <div className="dialog-title">Start New Scan</div>
            <div className="form-group">
              <label className="form-label">Folder Path</label>
              <input
                type="text"
                className="form-input"
                placeholder="/path/to/documents"
                value={scanPath}
                onChange={(e) => setScanPath(e.target.value)}
                autoFocus
              />
            </div>
            <div className="form-group">
              <label className="form-label">
                Confidence Threshold: {Math.round(scanThreshold * 100)}%
              </label>
              <input
                type="range"
                className="form-range"
                min="0.1"
                max="1"
                step="0.05"
                value={scanThreshold}
                onChange={(e) => setScanThreshold(parseFloat(e.target.value))}
              />
            </div>
            <div className="form-group">
              <label className="form-label">Worker Count</label>
              <input
                type="number"
                className="form-input"
                min="1"
                max="16"
                value={scanWorkers}
                onChange={(e) => setScanWorkers(parseInt(e.target.value, 10) || 1)}
              />
            </div>
            <div className="dialog-actions">
              <button
                className="btn btn-secondary"
                onClick={() => setShowScanDialog(false)}
              >
                Cancel
              </button>
              <button
                className="btn btn-primary"
                onClick={handleStartScan}
                disabled={!scanPath.trim() || scanning}
              >
                Start Scan
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
