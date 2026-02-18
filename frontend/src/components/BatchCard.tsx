import { Link } from 'react-router-dom';
import type { Batch } from '../types';

function statusBadgeClass(status: string): string {
  switch (status) {
    case 'complete': return 'badge badge-complete';
    case 'processing': return 'badge badge-processing';
    case 'error': return 'badge badge-error';
    default: return 'badge badge-pending';
  }
}

export default function BatchCard({ batch }: { batch: Batch }) {
  return (
    <Link to={`/batches/${batch.id}`} className="batch-card">
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
      </div>
    </Link>
  );
}
