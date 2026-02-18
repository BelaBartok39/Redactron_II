import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api/client';
import type { Batch } from '../types';

function statusBadgeClass(status: string): string {
  switch (status) {
    case 'completed': return 'badge badge-complete';
    case 'processing': return 'badge badge-processing';
    case 'error': return 'badge badge-error';
    default: return 'badge badge-pending';
  }
}

interface BatchCardProps {
  batch: Batch;
  onDeleted?: (id: string) => void;
}

export default function BatchCard({ batch, onDeleted }: BatchCardProps) {
  const navigate = useNavigate();
  const [deleting, setDeleting] = useState(false);

  const handleDelete = async (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (!confirm(`Delete batch "${batch.name}"? This removes all its documents and findings.`)) {
      return;
    }
    setDeleting(true);
    try {
      await api.deleteBatch(batch.id);
      onDeleted?.(batch.id);
    } catch {
      setDeleting(false);
    }
  };

  return (
    <div
      className="batch-card"
      style={{ cursor: 'pointer', position: 'relative' }}
      onClick={() => navigate(`/batches/${batch.id}`)}
    >
      <div className="batch-card-info">
        <span className="batch-card-name">{batch.name}</span>
        <div className="batch-card-meta">
          <span className={statusBadgeClass(batch.status)}>{batch.status}</span>
          <span>{new Date(batch.created_at).toLocaleDateString()}</span>
          <span>{batch.source_path}</span>
        </div>
      </div>
      <div className="batch-card-stats">
        <div className="batch-card-stat">
          <span className="num">{batch.total_docs}</span>
          <span className="label">Docs</span>
        </div>
        <div className="batch-card-stat">
          <span className="num">{batch.processed_docs}</span>
          <span className="label">Processed</span>
        </div>
        <div className="batch-card-stat">
          <span className="num">{batch.docs_with_findings}</span>
          <span className="label">With Findings</span>
        </div>
        <button
          className="btn btn-secondary"
          onClick={handleDelete}
          disabled={deleting}
          style={{
            padding: '4px 10px',
            fontSize: '0.75rem',
            alignSelf: 'center',
            marginLeft: 8,
          }}
        >
          {deleting ? '...' : 'Delete'}
        </button>
      </div>
    </div>
  );
}
