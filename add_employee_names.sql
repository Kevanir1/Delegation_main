-- Migration: Add first_name and last_name to Employee table
-- Date: 2026-01-17

-- Add columns with default values for existing records
ALTER TABLE employee 
ADD COLUMN IF NOT EXISTS first_name VARCHAR(100) DEFAULT 'Imię',
ADD COLUMN IF NOT EXISTS last_name VARCHAR(100) DEFAULT 'Nazwisko';

-- Update defaults to be NOT NULL after setting initial values
ALTER TABLE employee 
ALTER COLUMN first_name SET NOT NULL,
ALTER COLUMN last_name SET NOT NULL;

-- Remove defaults after migration
ALTER TABLE employee 
ALTER COLUMN first_name DROP DEFAULT,
ALTER COLUMN last_name DROP DEFAULT;
