-- Relacje zgodne z diagramem ERD
-- employee -> delegation (1:N)
ALTER TABLE "delegation"
  ADD CONSTRAINT "fk_delegation_employee"
  FOREIGN KEY ("employee_id") REFERENCES "employee" ("id")
  ON DELETE CASCADE ON UPDATE CASCADE;

-- delegation -> expense (1:N)
ALTER TABLE "expense"
  ADD CONSTRAINT "fk_expense_delegation"
  FOREIGN KEY ("delegation_id") REFERENCES "delegation" ("id")
  ON DELETE CASCADE ON UPDATE CASCADE;

-- expense_category -> expense (1:N)
ALTER TABLE "expense"
  ADD CONSTRAINT "fk_expense_category"
  FOREIGN KEY ("category_id") REFERENCES "expense_category" ("id")
  ON DELETE RESTRICT ON UPDATE CASCADE;

-- currency -> expense (1:N)
ALTER TABLE "expense"
  ADD CONSTRAINT "fk_expense_currency"
  FOREIGN KEY ("currency_id") REFERENCES "currency" ("id")
  ON DELETE RESTRICT ON UPDATE CASCADE;

-- currency -> exchange_rate (1:N)
ALTER TABLE "exchange_rate"
  ADD CONSTRAINT "fk_exchange_rate_currency"
  FOREIGN KEY ("currency_id") REFERENCES "currency" ("id")
  ON DELETE CASCADE ON UPDATE CASCADE;
