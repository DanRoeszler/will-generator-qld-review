# Queensland Will Generator

A premium, solicitor-grade will generation web application for Queensland residents.

## Features

- **Deterministic PDF Generation**: Same payload always produces identical PDF bytes
- **Professional PDF Output**: A4 layout with proper margins and solicitor-grade formatting
- **Two-Pass Rendering**: Accurate "Page X of Y" footers on multi-page documents
- **Strict Validation**: Exceeds human paralegal review standards
- **Security**: CSRF protection, rate limiting, input sanitization
- **Admin Interface**: Protected admin routes for submission management

## Quick Start

### Local Development

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set up environment variables:**
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

3. **Run the application:**
   ```bash
   flask run
   ```

4. **Open in browser:**
   Navigate to `http://localhost:5000`

### Docker Compose

```bash
docker-compose up --build
```

The application will be available at `http://localhost:5000`

## Testing

Run all tests:
```bash
pytest
```

Run with verbose output:
```bash
pytest -v
```

## API Endpoints

### POST /api/validate
Validate a will payload without generating a PDF.

**Request:**
```json
{
  "eligibility": {
    "confirm_age_over_18": true,
    "confirm_qld": true,
    "confirm_not_legal_advice": true
  },
  "will_maker": {
    "full_name": "John Smith",
    "dob": "1970-01-15",
    "occupation": "Engineer",
    "address": {
      "street": "123 Test Street",
      "suburb": "Brisbane",
      "state": "QLD",
      "postcode": "4000"
    },
    "email": "john@example.com",
    "phone": "0412 345 678",
    "relationship_status": "married"
  },
  ...
}
```

**Response:**
```json
{
  "ok": true,
  "errors": [],
  "warnings": []
}
```

### POST /api/generate
Generate a will PDF.

**Request:** Same as validate endpoint.

**Response:** PDF file with `Content-Type: application/pdf`

### GET /api/download/{submission_id}
Download a previously generated PDF.

## Determinism Guarantee

This application guarantees that **the same validated payload will always generate identical PDF bytes**.

This is achieved through:

1. **Stored Generation Timestamp**: Each submission stores a `generation_timestamp` at creation time
2. **No System Time Calls**: All rendering uses the stored timestamp, never `datetime.utcnow()`
3. **ReportLab Invariant Mode**: `rl_config.invariant = 1` ensures deterministic PDF output
4. **Stable Metadata**: PDF metadata (creation date, author, etc.) uses the stored timestamp

To verify determinism:
```python
# Generate PDF twice with same payload
curl -X POST http://localhost:5000/api/generate \
  -H "Content-Type: application/json" \
  -d @payload.json > will1.pdf

curl -X POST http://localhost:5000/api/generate \
  -H "Content-Type: application/json" \
  -d @payload.json > will2.pdf

# Compare
 diff will1.pdf will2.pdf  # Should produce no output
```

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `SECRET_KEY` | Flask secret key | Yes |
| `DATABASE_URL` | Database connection URL | No (defaults to SQLite) |
| `ADMIN_USERNAME` | Admin username | No |
| `ADMIN_PASSWORD_HASH` | SHA-256 hash of admin password | No |
| `SMTP_HOST` | SMTP server hostname | No |
| `SMTP_PORT` | SMTP server port | No (default: 587) |
| `SMTP_USERNAME` | SMTP username | No |
| `SMTP_PASSWORD` | SMTP password | No |

## Admin Access

To enable admin access:

1. Set `ADMIN_USERNAME` and `ADMIN_PASSWORD_HASH` in `.env`
2. Generate password hash: `python -c "import hashlib; print(hashlib.sha256('your-password'.encode()).hexdigest())"`
3. Access admin panel at `/admin/login`

If admin credentials are not configured, admin routes return 503.

## Troubleshooting

### Tests failing

Run tests with verbose output to see detailed error messages:
```bash
pytest -v --tb=short
```

### PDF not deterministic

Ensure `rl_config.invariant = 1` is set in `app/pdf_generator.py`. This is required for deterministic PDF generation.

### Validation errors

Check that your payload includes all required fields:
- `eligibility` section with all confirmations
- `will_maker` with all fields including `phone`
- `dependants.has_other_dependants`
- `survivorship.days` and `substitution.rule`
- `declarations` with all confirmation fields

## Architecture

```
questionnaire payload
    ↓
validation.py (strict JSON schema validation)
    ↓
context_builder.py (builds context with derived flags)
    ↓
clause_logic.py (selects and orders clauses)
    ↓
clause_renderer.py (renders clause blocks)
    ↓
modular_will_template.j2 (clause text fragments)
    ↓
pdf_generator.py (two-pass ReportLab PDF rendering)
    ↓
Deterministic PDF with integrity hash
```

## License

This project is provided as-is for educational and development purposes.
