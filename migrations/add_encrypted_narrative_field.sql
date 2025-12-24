-- Migration: Add encrypted_mentor_narrative field to topics table
-- Adds encryption at rest for mentor narratives

-- Add the encrypted_mentor_narrative column if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'topics'
        AND column_name = 'encrypted_mentor_narrative'
    ) THEN
        ALTER TABLE topics ADD COLUMN encrypted_mentor_narrative TEXT NULL;
        RAISE NOTICE 'Column encrypted_mentor_narrative added successfully';
    ELSE
        RAISE NOTICE 'Column encrypted_mentor_narrative already exists';
    END IF;
END $$;

-- Create an index on encrypted_mentor_narrative for faster lookups (optional)
CREATE INDEX IF NOT EXISTS idx_topics_encrypted_narrative
ON topics(id)
WHERE encrypted_mentor_narrative IS NOT NULL;

-- Display migration summary
SELECT
    COUNT(*) as total_topics,
    COUNT(mentor_narrative) as topics_with_plain_narrative,
    COUNT(encrypted_mentor_narrative) as topics_with_encrypted_narrative
FROM topics;
