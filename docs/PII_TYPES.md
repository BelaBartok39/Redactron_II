# PII Types Catalog

## Built-in Presidio Recognizers

| Entity Type | Description | Example | Severity |
|------------|-------------|---------|----------|
| PERSON | Person name | "John Smith" | 4 |
| EMAIL_ADDRESS | Email | "john@example.com" | 3 |
| PHONE_NUMBER | Phone/fax | "(555) 123-4567" | 3 |
| US_SSN | Social Security Number | "123-45-6789" | 5 |
| US_DRIVER_LICENSE | Driver's license | State-specific patterns | 5 |
| US_PASSPORT | Passport number | 9-digit number | 5 |
| CREDIT_CARD | Credit/debit card | "4111-1111-1111-1111" | 5 |
| US_BANK_NUMBER | Bank account | Variable length digits | 5 |
| US_ITIN | Individual TIN | "9XX-XX-XXXX" | 5 |
| IP_ADDRESS | IPv4/IPv6 | "192.168.1.1" | 2 |
| DATE_TIME | Date/time | "01/15/2024" | 1 |
| LOCATION | Address/location | "123 Main St, City, ST" | 3 |
| MEDICAL_LICENSE | Medical license | State-specific | 4 |
| URL | Web URL | "https://example.com" | 1 |

## Custom Legal Recognizers

### Case Number (CASE_NUMBER)
- **Patterns**: `XX-CV-XXXXX`, `XXXX-CR-XXXXXX`, `Case No. XXXXXXX`
- **Context words**: "case", "docket", "cause", "matter"
- **Severity**: 3

### Legal Role Name (LEGAL_ROLE_NAME)
- **Detection**: Person names appearing near role keywords
- **Role keywords**: "judge", "attorney", "counsel", "victim", "witness", "minor", "defendant", "plaintiff", "petitioner", "respondent"
- **Severity**: 5

### Government ID (government_id.py)
- **SSN variants**: Full (XXX-XX-XXXX), partial (last 4), with/without dashes
- **Driver's license**: State-specific patterns (CA: 1 letter + 7 digits, etc.)
- **Passport**: 9-digit US passport numbers

### Financial (financial_pii.py)
- **Routing numbers**: 9-digit ABA routing numbers with check digit validation
- **Account numbers**: 8-17 digit sequences near financial keywords

### Medical (medical_pii.py)
- **Medical record numbers**: Alphanumeric patterns near "MRN", "medical record", "patient ID"
- **Health info**: Condition/diagnosis mentions near person names

### Digital (digital_pii.py)
- **IPv4**: Standard dotted notation with valid ranges
- **IPv6**: Full and abbreviated formats
- **MAC addresses**: XX:XX:XX:XX:XX:XX and XX-XX-XX-XX-XX-XX
- **Device IDs**: IMEI (15 digits), serial numbers near device keywords
