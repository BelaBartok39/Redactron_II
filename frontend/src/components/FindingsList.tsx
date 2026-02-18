import type { Finding } from '../types';
import PIIBadge from './PIIBadge';
import ConfidenceBar from './ConfidenceBar';

function highlightContext(snippet: string, offset: number, length: number) {
  // The context snippet is a small window around the PII.
  // char_offset is relative to the full page text, but the snippet is already
  // a small window. We'll try to highlight based on length from a reasonable position.
  // If the snippet itself is shorter than offset, just show it plain.
  if (offset < snippet.length && offset + length <= snippet.length) {
    const before = snippet.slice(0, offset);
    const match = snippet.slice(offset, offset + length);
    const after = snippet.slice(offset + length);
    return (
      <>
        {before}
        <span className="pii-highlight">{match}</span>
        {after}
      </>
    );
  }
  // Fallback: highlight anything that looks like it could be PII (the middle portion)
  return <>{snippet}</>;
}

interface FindingsListProps {
  findings: Finding[];
  groupByPage?: boolean;
}

export default function FindingsList({ findings, groupByPage = false }: FindingsListProps) {
  if (findings.length === 0) {
    return <p style={{ color: 'var(--text-muted)', padding: '16px 0' }}>No findings.</p>;
  }

  if (!groupByPage) {
    return (
      <div>
        {findings.map((f) => (
          <div key={f.id} className="finding-item">
            <div className="finding-meta">
              <PIIBadge type={f.pii_type} />
              <ConfidenceBar confidence={f.confidence} />
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                Page {f.page_number}
              </span>
            </div>
            <div className="context-snippet">
              {highlightContext(f.context_snippet, f.char_offset, f.char_length)}
            </div>
          </div>
        ))}
      </div>
    );
  }

  // Group by page
  const pages = new Map<number, Finding[]>();
  for (const f of findings) {
    const arr = pages.get(f.page_number) || [];
    arr.push(f);
    pages.set(f.page_number, arr);
  }

  const sortedPages = Array.from(pages.entries()).sort((a, b) => a[0] - b[0]);

  return (
    <div>
      {sortedPages.map(([page, pageFindings]) => (
        <div key={page} className="page-group">
          <div className="page-group-header">
            Page {page} ({pageFindings.length} finding{pageFindings.length !== 1 ? 's' : ''})
          </div>
          {pageFindings.map((f) => (
            <div key={f.id} className="finding-item">
              <div className="finding-meta">
                <PIIBadge type={f.pii_type} />
                <ConfidenceBar confidence={f.confidence} />
              </div>
              <div className="context-snippet">
                {highlightContext(f.context_snippet, f.char_offset, f.char_length)}
              </div>
            </div>
          ))}
        </div>
      ))}
    </div>
  );
}
