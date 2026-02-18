import type { Stats } from '../types';

export default function StatsOverview({ stats }: { stats: Stats }) {
  const items = [
    { label: 'Total Batches', value: stats.total_batches },
    { label: 'Documents Scanned', value: stats.total_documents },
    { label: 'Total Findings', value: stats.total_findings },
    { label: 'Docs with Findings', value: stats.docs_with_findings },
  ];

  return (
    <div className="stats-row">
      {items.map((item) => (
        <div key={item.label} className="stat-card">
          <div className="stat-label">{item.label}</div>
          <div className="stat-value">{item.value.toLocaleString()}</div>
        </div>
      ))}
    </div>
  );
}
