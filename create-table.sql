CREATE TABLE "employee" (
  "id" serial PRIMARY KEY,
  "username" varchar(120) UNIQUE NOT NULL,
  "email" varchar(120) UNIQUE NOT NULL,
  "password" varchar(255) NOT NULL,
  "is_active" boolean DEFAULT true NOT NULL,
  "created_at" timestamp
);

CREATE TABLE "expense" (
  "id" serial PRIMARY KEY,
  "explanation" text,
  "payed_at" timestamp,
  "amount" numeric(10,2) NOT NULL,
  "pln_amount" numeric(10,2) NOT NULL,
  "exchange_rate" numeric(8,4) NOT NULL,
  "currency_id" integer NOT NULL,
  "delegation_id" integer NOT NULL,
  "status" varchar,
  "category_id" integer NOT NULL,
  "created_at" timestamp,
  "closed_at" timestamp
);

CREATE TABLE "delegation" (
  "id" serial PRIMARY KEY,
  "employee_id" integer NOT NULL,
  "start_date" date NOT NULL,
  "end_date" date NOT NULL,
  "status" varchar DEFAULT 'draft',
  "created_at" timestamp,
  "closed_at" timestamp,
  "export_date" timestamp
);

CREATE TABLE "expense_category" (
  "id" serial PRIMARY KEY,
  "name" varchar NOT NULL
);

CREATE TABLE "currency" (
  "id" serial PRIMARY KEY,
  "name" varchar NOT NULL
);

CREATE TABLE "exchange_rate" (
  "id" serial PRIMARY KEY,
  "currency_id" integer NOT NULL,
  "rate_to_pln" numeric(8,4) NOT NULL,
  "date_set" date NOT NULL
);

CREATE UNIQUE INDEX ON "exchange_rate" ("currency_id", "date_set");

COMMENT ON COLUMN "expense"."explanation" IS 'Note why the expense was needed';

COMMENT ON COLUMN "delegation"."export_date" IS 'Data eksportu do systemu księgowego (JPK/CSV)';
