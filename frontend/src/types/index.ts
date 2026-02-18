export interface Batch {
  id: string;
  name: string;
  source_path: string;
  created_at: string;
  status: string;
  total_docs: number;
  processed_docs: number;
  docs_with_findings: number;
}

export interface Document {
  id: string;
  batch_id: string;
  filename: string;
  page_count: number;
  status: string;
  finding_count: number;
  processed_at: string | null;
}

export interface Finding {
  id: string;
  document_id: string;
  page_number: number;
  pii_type: string;
  confidence: number;
  context_snippet: string;
  char_offset: number;
  char_length: number;
}

export interface Stats {
  total_batches: number;
  total_documents: number;
  total_findings: number;
  docs_with_findings: number;
  pii_type_counts: Record<string, number>;
}

export interface PIITypeCount {
  pii_type: string;
  count: number;
  avg_confidence: number;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}
