function getColor(confidence: number): string {
  if (confidence >= 0.9) return '#ef4444';
  if (confidence >= 0.7) return '#f97316';
  if (confidence >= 0.5) return '#eab308';
  return '#3b82f6';
}

export default function ConfidenceBar({ confidence }: { confidence: number }) {
  const pct = Math.round(confidence * 100);
  return (
    <div className="confidence-bar-container">
      <div className="confidence-bar">
        <div
          className="confidence-bar-fill"
          style={{ width: `${pct}%`, background: getColor(confidence) }}
        />
      </div>
      <span className="confidence-label" style={{ color: getColor(confidence) }}>
        {pct}%
      </span>
    </div>
  );
}
