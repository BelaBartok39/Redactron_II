interface FilterPanelProps {
  piiTypes: string[];
  selectedType: string;
  onTypeChange: (type: string) => void;
  confidence: number;
  onConfidenceChange: (value: number) => void;
  hasFindings?: boolean;
  onHasFindingsChange?: (value: boolean) => void;
  showHasFindings?: boolean;
}

export default function FilterPanel({
  piiTypes,
  selectedType,
  onTypeChange,
  confidence,
  onConfidenceChange,
  hasFindings,
  onHasFindingsChange,
  showHasFindings = false,
}: FilterPanelProps) {
  return (
    <div className="filter-panel">
      <div className="filter-group">
        <label>PII Type</label>
        <select
          className="form-input"
          value={selectedType}
          onChange={(e) => onTypeChange(e.target.value)}
        >
          <option value="">All Types</option>
          {piiTypes.map((t) => (
            <option key={t} value={t}>
              {t.replace(/_/g, ' ')}
            </option>
          ))}
        </select>
      </div>

      <div className="filter-group">
        <label>Min Confidence: {Math.round(confidence * 100)}%</label>
        <input
          type="range"
          className="form-range"
          min="0"
          max="1"
          step="0.05"
          value={confidence}
          onChange={(e) => onConfidenceChange(parseFloat(e.target.value))}
        />
      </div>

      {showHasFindings && onHasFindingsChange && (
        <div className="filter-group">
          <label>
            <input
              type="checkbox"
              checked={hasFindings || false}
              onChange={(e) => onHasFindingsChange(e.target.checked)}
              style={{ marginRight: 6 }}
            />
            Only with findings
          </label>
        </div>
      )}
    </div>
  );
}
