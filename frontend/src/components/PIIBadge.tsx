const SEVERITY_MAP: Record<string, string> = {
  // Critical
  SSN: 'critical',
  CREDIT_CARD: 'critical',
  US_BANK_NUMBER: 'critical',
  US_SSN: 'critical',
  // High
  PERSON: 'high',
  US_DRIVER_LICENSE: 'high',
  US_PASSPORT: 'high',
  DATE_OF_BIRTH: 'high',
  // Medium
  PHONE_NUMBER: 'medium',
  EMAIL_ADDRESS: 'medium',
  LOCATION: 'medium',
  ADDRESS: 'medium',
  // Low
  IP_ADDRESS: 'low',
  URL: 'low',
  // Info
  AGE: 'info',
  GENDER: 'info',
};

function getSeverity(piiType: string): string {
  return SEVERITY_MAP[piiType] || 'info';
}

export default function PIIBadge({ type }: { type: string }) {
  const severity = getSeverity(type);
  const label = type.replace(/_/g, ' ');
  return (
    <span className={`pii-badge pii-${severity}`}>{label}</span>
  );
}
