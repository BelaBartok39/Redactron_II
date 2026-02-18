import { useState, useEffect } from 'react';
import { api } from '../api/client';
import type { Batch } from '../types';

interface ReportState {
  batchId: string;
  format: 'pdf' | 'csv';
  status: 'idle' | 'generating' | 'done' | 'error';
  reportId?: string;
  error?: string;
}

export default function ReportsPage() {
  const [batches, setBatches] = useState<Batch[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [reports, setReports] = useState<Map<string, ReportState>>(new Map());

  useEffect(() => {
    api.getBatches()
      .then(setBatches)
      .catch((err) => setError(err instanceof Error ? err.message : 'Failed to load batches'))
      .finally(() => setLoading(false));
  }, []);

  const handleGenerate = async (batchId: string, format: 'pdf' | 'csv') => {
    const key = `${batchId}-${format}`;
    setReports((prev) => new Map(prev).set(key, { batchId, format, status: 'generating' }));

    try {
      const result = await api.generateReport(batchId, format);
      setReports((prev) =>
        new Map(prev).set(key, { batchId, format, status: 'done', reportId: result.id })
      );
    } catch (err) {
      setReports((prev) =>
        new Map(prev).set(key, {
          batchId,
          format,
          status: 'error',
          error: err instanceof Error ? err.message : 'Failed',
        })
      );
    }
  };

  const getReportState = (batchId: string, format: 'pdf' | 'csv'): ReportState | undefined => {
    return reports.get(`${batchId}-${format}`);
  };

  if (loading) return <div className="loading">Loading reports...</div>;
  if (error) return <div className="error-message">{error}</div>;

  const completedBatches = batches.filter((b) => b.status === 'complete');

  return (
    <div>
      <div className="section-header">
        <span className="section-title">Generate Reports</span>
      </div>

      {completedBatches.length === 0 ? (
        <div className="card">
          <p style={{ color: 'var(--text-muted)' }}>
            No completed batches available for report generation.
          </p>
        </div>
      ) : (
        <div className="table-wrapper">
          <table>
            <thead>
              <tr>
                <th>Batch Name</th>
                <th>Documents</th>
                <th>Findings</th>
                <th>Created</th>
                <th>PDF Report</th>
                <th>CSV Export</th>
              </tr>
            </thead>
            <tbody>
              {completedBatches.map((batch) => {
                const pdfState = getReportState(batch.id, 'pdf');
                const csvState = getReportState(batch.id, 'csv');

                return (
                  <tr key={batch.id}>
                    <td style={{ fontWeight: 600 }}>{batch.name}</td>
                    <td>{batch.total_docs}</td>
                    <td>{batch.docs_with_findings}</td>
                    <td>{new Date(batch.created_at).toLocaleDateString()}</td>
                    <td>
                      <ReportButton
                        state={pdfState}
                        format="pdf"
                        onGenerate={() => handleGenerate(batch.id, 'pdf')}
                      />
                    </td>
                    <td>
                      <ReportButton
                        state={csvState}
                        format="csv"
                        onGenerate={() => handleGenerate(batch.id, 'csv')}
                      />
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function ReportButton({
  state,
  format,
  onGenerate,
}: {
  state: ReportState | undefined;
  format: 'pdf' | 'csv';
  onGenerate: () => void;
}) {
  if (!state || state.status === 'idle') {
    return (
      <button className="btn btn-secondary btn-sm" onClick={onGenerate}>
        Generate {format.toUpperCase()}
      </button>
    );
  }

  if (state.status === 'generating') {
    return (
      <button className="btn btn-secondary btn-sm" disabled>
        Generating...
      </button>
    );
  }

  if (state.status === 'error') {
    return (
      <div>
        <span style={{ color: 'var(--severity-critical)', fontSize: '0.75rem' }}>
          Error: {state.error}
        </span>
        <button
          className="btn btn-secondary btn-sm"
          onClick={onGenerate}
          style={{ marginLeft: 8 }}
        >
          Retry
        </button>
      </div>
    );
  }

  // done
  return (
    <a
      href={api.downloadReport(state.reportId!)}
      className="btn btn-primary btn-sm"
      download
    >
      Download {format.toUpperCase()}
    </a>
  );
}
