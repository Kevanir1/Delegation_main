-- Migration script to add new columns and tables
-- Run this script on existing database

-- Add role and manager_id columns to employee table if they don't exist
DO $$ 
BEGIN
    -- Add role column
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'employee' AND column_name = 'role'
    ) THEN
        ALTER TABLE "employee" ADD COLUMN "role" varchar(50) DEFAULT 'employee' NOT NULL;
    END IF;

    -- Add manager_id column
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'employee' AND column_name = 'manager_id'
    ) THEN
        ALTER TABLE "employee" ADD COLUMN "manager_id" integer;
    END IF;

    -- Add first_name column
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'employee' AND column_name = 'first_name'
    ) THEN
        ALTER TABLE "employee" ADD COLUMN "first_name" varchar(100) DEFAULT 'User' NOT NULL;
    END IF;

    -- Add last_name column
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'employee' AND column_name = 'last_name'
    ) THEN
        ALTER TABLE "employee" ADD COLUMN "last_name" varchar(100) DEFAULT 'User' NOT NULL;
    END IF;
END $$;

-- Add foreign key constraint for manager_id if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints 
        WHERE constraint_name = 'fk_employee_manager'
    ) THEN
        ALTER TABLE "employee"
        ADD CONSTRAINT "fk_employee_manager"
        FOREIGN KEY ("manager_id") REFERENCES "employee" ("id")
        ON DELETE SET NULL ON UPDATE CASCADE;
    END IF;
END $$;

-- Add country, city, name and purpose columns to delegation table if they don't exist
-- Drop destination column if it exists (migration from old schema)
DO $$ 
BEGIN
    -- Add country column
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'delegation' AND column_name = 'country'
    ) THEN
        ALTER TABLE "delegation" ADD COLUMN "country" varchar(100);
    END IF;

    -- Add city column
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'delegation' AND column_name = 'city'
    ) THEN
        ALTER TABLE "delegation" ADD COLUMN "city" varchar(100);
    END IF;

    -- Add name column
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'delegation' AND column_name = 'name'
    ) THEN
        ALTER TABLE "delegation" ADD COLUMN "name" varchar(255);
    END IF;

    -- Add purpose column
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'delegation' AND column_name = 'purpose'
    ) THEN
        ALTER TABLE "delegation" ADD COLUMN "purpose" text;
    END IF;

    -- Drop old destination column if it exists
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'delegation' AND column_name = 'destination'
    ) THEN
        ALTER TABLE "delegation" DROP COLUMN "destination";
    END IF;
END $$;

-- Create document table if it doesn't exist
CREATE TABLE IF NOT EXISTS "document" (
  "id" serial PRIMARY KEY,
  "delegation_id" integer NOT NULL,
  "expense_id" integer,
  "filename" varchar(255) NOT NULL,
  "file_path" varchar(500) NOT NULL,
  "file_type" varchar(50),
  "description" text,
  "uploaded_at" timestamp DEFAULT CURRENT_TIMESTAMP
);

-- Add foreign key constraints for document table if they don't exist
DO $$
BEGIN
    -- Foreign key to delegation
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints 
        WHERE constraint_name = 'fk_document_delegation'
    ) THEN
        ALTER TABLE "document"
        ADD CONSTRAINT "fk_document_delegation"
        FOREIGN KEY ("delegation_id") REFERENCES "delegation" ("id")
        ON DELETE CASCADE ON UPDATE CASCADE;
    END IF;

    -- Foreign key to expense
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints 
        WHERE constraint_name = 'fk_document_expense'
    ) THEN
        ALTER TABLE "document"
        ADD CONSTRAINT "fk_document_expense"
        FOREIGN KEY ("expense_id") REFERENCES "expense" ("id")
        ON DELETE CASCADE ON UPDATE CASCADE;
    END IF;
END $$;
