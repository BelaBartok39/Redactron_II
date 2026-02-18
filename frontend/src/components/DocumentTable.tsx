import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import type { Document } from '../types';

type SortKey = 'filename' | 'page_count' | 'finding_count' | 'status';

function statusBadgeClass(status: string): string {
  switch (status) {
    case 'complete': return 'badge badge-complete';
    case 'processing': return 'badge badge-processing';
    case 'error': return 'badge badge-error';
    default: return 'badge badge-pending';
  }
}

interface DocumentTableProps {
  documents: Document[];
}

export default function DocumentTable({ documents }: DocumentTableProps) {
  const navigate = useNavigate();
  const [sortKey, setSortKey] = useState<SortKey>('finding_count');
  const [sortAsc, setSortAsc] = useState(false);

  const handleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortAsc(!sortAsc);
    } else {
      setSortKey(key);
      setSortAsc(key === 'filename');
    }
  };

  const sorted = [...documents].sort((a, b) => {
    const av = a[sortKey];
    const bv = b[sortKey];
    if (typeof av === 'string' && typeof bv === 'string') {
      return sortAsc ? av.localeCompare(bv) : bv.localeCompare(av);
    }
    return sortAsc ? (av as number) - (bv as number) : (bv as number) - (av as number);
  });

  const arrow = (key: SortKey) =>
    sortKey === key ? (sortAsc ? ' \u25B2' : ' \u25BC') : '';

  return (
    <div className="table-wrapper">
      <table>
        <thead>
          <tr>
            <th onClick={() => handleSort('filename')}>Filename{arrow('filename')}</th>
            <th onClick={() => handleSort('page_count')}>Pages{arrow('page_count')}</th>
            <th onClick={() => handleSort('finding_count')}>Findings{arrow('finding_count')}</th>
            <th onClick={() => handleSort('status')}>Status{arrow('status')}</th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((doc) => (
            <tr
              key={doc.id}
              className="clickable"
              onClick={() => navigate(`/documents/${doc.id}`)}
            >
              <td style={{ fontFamily: 'var(--font-mono)', fontSize: '0.8rem' }}>{doc.filename}</td>
              <td>{doc.page_count}</td>
              <td>
                <strong style={{ color: doc.finding_count > 0 ? 'var(--severity-critical)' : 'var(--text-muted)' }}>
                  {doc.finding_count}
                </strong>
              </td>
              <td><span className={statusBadgeClass(doc.status)}>{doc.status}</span></td>
            </tr>
          ))}
          {sorted.length === 0 && (
            <tr>
              <td colSpan={4} style={{ textAlign: 'center', color: 'var(--text-muted)', padding: 24 }}>
                No documents found.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
