import { useState, useEffect, useCallback } from 'react';
import { useParams, Link } from 'react-router-dom';
import { api } from '../api/client';
import type { Batch, Document, PIITypeCount } from '../types';
import FilterPanel from '../components/FilterPanel';
import DocumentTable from '../components/DocumentTable';

export default function BatchDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [batch, setBatch] = useState<Batch | null>(null);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [piiTypes, setPiiTypes] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  // Filters
  const [filterType, setFilterType] = useState('');
  const [filterConfidence, setFilterConfidence] = useState(0);
  const [filterHasFindings, setFilterHasFindings] = useState(false);

  const pageSize = 50;

  const loadBatch = useCallback(async () => {
    if (!id) return;
    try {
      const [b, types] = await Promise.all([
        api.getBatch(id),
        api.getPiiTypes(),
      ]);
      setBatch(b);
      setPiiTypes(types.map((t: PIITypeCount) => t.pii_type));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load batch');
    }
  }, [id]);

  const loadDocuments = useCallback(async () => {
    if (!id) return;
    try {
      const res = await api.getDocuments(id, {
        page,
        page_size: pageSize,
        pii_type: filterType || undefined,
        min_confidence: filterConfidence || undefined,
        has_findings: filterHasFindings || undefined,
      });
      setDocuments(res.items);
      setTotal(res.total);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load documents');
    } finally {
      setLoading(false);
    }
  }, [id, page, filterType, filterConfidence, filterHasFindings]);

  useEffect(() => {
    loadBatch();
  }, [loadBatch]);

  useEffect(() => {
    loadDocuments();
  }, [loadDocuments]);

  // Poll if processing
  useEffect(() => {
    if (!batch || batch.status !== 'processing') return;
    const interval = setInterval(() => {
      loadBatch();
      loadDocuments();
    }, 3000);
    return () => clearInterval(interval);
  }, [batch, loadBatch, loadDocuments]);

  if (loading) return <div className="loading">Loading batch...</div>;
  if (error) return <div className="error-message">{error}</div>;
  if (!batch) return <div className="error-message">Batch not found.</div>;

  const progress = batch.total_docs > 0
    ? Math.round((batch.processed_docs / batch.total_docs) * 100)
    : 0;
  const totalPages = Math.ceil(total / pageSize);

  const statusClass = (() => {
    switch (batch.status) {
      case 'complete': return 'badge badge-complete';
      case 'processing': return 'badge badge-processing';
      case 'error': return 'badge badge-error';
      default: return 'badge badge-pending';
    }
  })();

  return (
    <div>
      <div style={{ marginBottom: 16 }}>
        <Link to="/" style={{ fontSize: '0.8rem', color: 'var(--accent)', textDecoration: 'none' }}>
          &larr; Back to Dashboard
        </Link>
      </div>

      <div className="detail-header">
        <div>
          <h2>{batch.name}</h2>
          <div style={{ display: 'flex', gap: 12, alignItems: 'center', marginTop: 8 }}>
            <span className={statusClass}>{batch.status}</span>
            <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
              {new Date(batch.created_at).toLocaleString()}
            </span>
            <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
              {batch.source_path}
            </span>
          </div>
        </div>
        <div className="detail-header-stats">
          <div className="detail-stat">
            <span className="num">{batch.total_docs}</span>
            <span className="label">Total Docs</span>
          </div>
          <div className="detail-stat">
            <span className="num">{batch.processed_docs}</span>
            <span className="label">Processed</span>
          </div>
          <div className="detail-stat">
            <span className="num">{batch.docs_with_findings}</span>
            <span className="label">With Findings</span>
          </div>
        </div>
      </div>

      {batch.status === 'processing' && (
        <div style={{ marginBottom: 16 }}>
          <div className="progress-bar">
            <div className="progress-bar-fill" style={{ width: `${progress}%` }} />
          </div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            {batch.processed_docs} / {batch.total_docs} ({progress}%)
          </div>
        </div>
      )}

      <FilterPanel
        piiTypes={piiTypes}
        selectedType={filterType}
        onTypeChange={(v) => { setFilterType(v); setPage(1); }}
        confidence={filterConfidence}
        onConfidenceChange={(v) => { setFilterConfidence(v); setPage(1); }}
        hasFindings={filterHasFindings}
        onHasFindingsChange={(v) => { setFilterHasFindings(v); setPage(1); }}
        showHasFindings
      />

      <div className="card">
        <div className="card-header">
          <span className="card-title">Documents ({total})</span>
        </div>
        <DocumentTable documents={documents} />
      </div>

      {totalPages > 1 && (
        <div className="pagination">
          <button
            className="btn btn-secondary btn-sm"
            disabled={page <= 1}
            onClick={() => setPage(page - 1)}
          >
            Previous
          </button>
          <span className="pagination-info">
            Page {page} of {totalPages}
          </span>
          <button
            className="btn btn-secondary btn-sm"
            disabled={page >= totalPages}
            onClick={() => setPage(page + 1)}
          >
            Next
          </button>
        </div>
      )}
    </div>
  );
}
