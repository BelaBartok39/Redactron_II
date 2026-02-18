import { useState, useEffect, useCallback } from 'react';
import { useParams, Link } from 'react-router-dom';
import { api } from '../api/client';
import type { Document, Finding, PIITypeCount } from '../types';
import FilterPanel from '../components/FilterPanel';
import FindingsList from '../components/FindingsList';

export default function DocumentPage() {
  const { id } = useParams<{ id: string }>();
  const [doc, setDoc] = useState<Document | null>(null);
  const [findings, setFindings] = useState<Finding[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [piiTypes, setPiiTypes] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  // Filters
  const [filterType, setFilterType] = useState('');
  const [filterConfidence, setFilterConfidence] = useState(0);

  const pageSize = 100;

  const loadDoc = useCallback(async () => {
    if (!id) return;
    try {
      const [d, types] = await Promise.all([
        api.getDocument(id),
        api.getPiiTypes(),
      ]);
      setDoc(d);
      setPiiTypes(types.map((t: PIITypeCount) => t.pii_type));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load document');
    }
  }, [id]);

  const loadFindings = useCallback(async () => {
    if (!id) return;
    try {
      const res = await api.getFindings(id, {
        page,
        page_size: pageSize,
        pii_type: filterType || undefined,
        min_confidence: filterConfidence || undefined,
      });
      setFindings(res.items);
      setTotal(res.total);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load findings');
    } finally {
      setLoading(false);
    }
  }, [id, page, filterType, filterConfidence]);

  useEffect(() => {
    loadDoc();
  }, [loadDoc]);

  useEffect(() => {
    loadFindings();
  }, [loadFindings]);

  if (loading) return <div className="loading">Loading document...</div>;
  if (error) return <div className="error-message">{error}</div>;
  if (!doc) return <div className="error-message">Document not found.</div>;

  const totalPages = Math.ceil(total / pageSize);

  return (
    <div>
      <div style={{ marginBottom: 16 }}>
        <Link
          to={`/batches/${doc.batch_id}`}
          style={{ fontSize: '0.8rem', color: 'var(--accent)', textDecoration: 'none' }}
        >
          &larr; Back to Batch
        </Link>
      </div>

      <div className="detail-header">
        <div>
          <h2 style={{ fontFamily: 'var(--font-mono)', fontSize: '1.1rem' }}>{doc.filename}</h2>
          <div style={{ display: 'flex', gap: 12, alignItems: 'center', marginTop: 8 }}>
            <span className={`badge badge-${doc.status}`}>{doc.status}</span>
            {doc.processed_at && (
              <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                Processed: {new Date(doc.processed_at).toLocaleString()}
              </span>
            )}
          </div>
        </div>
        <div className="detail-header-stats">
          <div className="detail-stat">
            <span className="num">{doc.page_count}</span>
            <span className="label">Pages</span>
          </div>
          <div className="detail-stat">
            <span className="num" style={{ color: doc.finding_count > 0 ? 'var(--severity-critical)' : undefined }}>
              {doc.finding_count}
            </span>
            <span className="label">Findings</span>
          </div>
        </div>
      </div>

      <FilterPanel
        piiTypes={piiTypes}
        selectedType={filterType}
        onTypeChange={(v) => { setFilterType(v); setPage(1); }}
        confidence={filterConfidence}
        onConfidenceChange={(v) => { setFilterConfidence(v); setPage(1); }}
      />

      <div className="card">
        <div className="card-header">
          <span className="card-title">Findings ({total})</span>
        </div>
        <FindingsList findings={findings} groupByPage />
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
