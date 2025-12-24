# Database Migrations

This directory contains database migration scripts for the PlayStudy backend.

## Current Migrations

### Add Encrypted Narrative Field

**Purpose:** Add encryption at rest for mentor narratives in the topics table.

**Files:**
- `add_encrypted_narrative_field.py` - Python migration script (preferred)
- `add_encrypted_narrative_field.sql` - SQL migration script (alternative)

## Running Migrations

### Option 1: Python Migration (Recommended)

The Python script provides better error handling, data migration, and verification.

**Prerequisites:**
1. Backend dependencies installed (`pip install -r requirements.txt`)
2. Environment variables configured (create `.env` from `.env.example`)
3. Database running and accessible

**Run the migration:**
```bash
cd backend
python migrations/add_encrypted_narrative_field.py
```

**What it does:**
1. Checks if `encrypted_mentor_narrative` column exists
2. Adds the column if missing
3. Migrates existing plain text narratives to encrypted format
4. Verifies encryption/decryption works
5. Reports migration status

### Option 2: SQL Migration

Use this if you prefer direct SQL or if the Python migration fails.

**Run the migration:**
```bash
psql -U <username> -d playstudy_db -f migrations/add_encrypted_narrative_field.sql
```

Or using the connection string from your `.env`:
```bash
# Extract connection details from DATABASE_URL
psql $DATABASE_URL -f migrations/add_encrypted_narrative_field.sql
```

**What it does:**
1. Adds `encrypted_mentor_narrative` column if it doesn't exist
2. Creates an index for better performance
3. Shows summary of narratives (plain vs encrypted)

## Environment Setup

Before running migrations, ensure you have:

1. **Database Connection** - Set `DATABASE_URL` in `.env`:
   ```bash
   DATABASE_URL=postgresql+psycopg://localhost/playstudy_db
   ```

2. **Encryption Key** - Set `FIELD_ENCRYPTION_KEY` in `.env`:
   ```bash
   # Generate a new key:
   python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

   # Add to .env:
   FIELD_ENCRYPTION_KEY=your-generated-key-here
   ```

3. **Other Required Variables** - Copy from `.env.example`:
   ```bash
   cp .env.example .env
   # Edit .env and fill in required values
   ```

## Troubleshooting

### Error: Column already exists

This is safe to ignore. The migration script checks for existing columns and skips creation if already present.

### Error: Missing dependencies

Install backend dependencies:
```bash
pip install -r requirements.txt
```

### Error: Database connection failed

1. Check if PostgreSQL is running:
   ```bash
   sudo service postgresql status
   ```

2. Start PostgreSQL if needed:
   ```bash
   sudo service postgresql start
   ```

3. Verify DATABASE_URL in `.env` is correct

4. Test connection:
   ```bash
   psql $DATABASE_URL -c "SELECT version();"
   ```

### Error: Missing environment variables

Create `.env` file with required variables:
```bash
cp .env.example .env
# Edit .env and add:
# - DATABASE_URL
# - FIELD_ENCRYPTION_KEY
# - Other required keys
```

### Error: Decryption failed

If you see decryption errors:

1. Verify `FIELD_ENCRYPTION_KEY` matches the key used for encryption
2. Check that the key hasn't changed between encryption and decryption
3. Ensure the key is a valid Fernet key (44 characters, base64 encoded)

## Verification

After running the migration, verify it worked:

```sql
-- Check column exists
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'topics'
AND column_name = 'encrypted_mentor_narrative';

-- Count encrypted vs plain narratives
SELECT
    COUNT(*) as total_topics,
    COUNT(mentor_narrative) as plain_narratives,
    COUNT(encrypted_mentor_narrative) as encrypted_narratives
FROM topics;
```

## Manual Rollback (if needed)

If you need to remove the encrypted column:

```sql
-- WARNING: This will delete all encrypted narratives!
ALTER TABLE topics DROP COLUMN encrypted_mentor_narrative;
```

**Note:** Only do this if you're absolutely sure. The plain text `mentor_narrative` column is kept for backward compatibility, so you won't lose data.

## Security Notes

- **Never commit `.env` files** - They contain sensitive encryption keys
- **Never log encryption keys** - Even in debug mode
- **Rotate keys periodically** - Use key versioning for smooth transitions
- **Test decryption** - Always verify you can decrypt after encrypting

## Next Steps

After running this migration:

1. Test that mentor narratives are being encrypted when created
2. Test that narratives can be decrypted when retrieved
3. Monitor logs for any encryption/decryption errors
4. Consider enabling encryption in transit (see `ENCRYPTION_IN_TRANSIT.md`)
5. In production, remove the `mentor_narrative` column after confirming all data is encrypted

## Questions?

See:
- `backend/SECURITY.md` - Comprehensive security documentation
- `backend/ENCRYPTION_IN_TRANSIT.md` - Encryption in transit guide
- `backend/app/core/field_encryption.py` - Encryption service code
- `backend/app/models/topic.py` - Topic model with encryption helpers
