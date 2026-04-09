-- Financial database schema for small business tax tracking
-- Stores transactions from Square, bank accounts, and credit cards

-- Accounts: bank accounts, credit cards, payment processors
CREATE TABLE IF NOT EXISTS accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    type TEXT NOT NULL CHECK(type IN ('bank', 'credit_card', 'payment_processor')),
    institution TEXT,
    account_number_last4 TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Categories: expense and income categories mapped to Schedule C lines
CREATE TABLE IF NOT EXISTS categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    type TEXT NOT NULL CHECK(type IN ('income', 'expense', 'transfer', 'ignore')),
    schedule_c_line INTEGER,
    schedule_c_description TEXT,
    keywords TEXT,  -- JSON array of keywords for auto-categorization
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Vendors/Payees: for tracking recurring payments
CREATE TABLE IF NOT EXISTS vendors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    default_category_id INTEGER,
    notes TEXT,
    FOREIGN KEY (default_category_id) REFERENCES categories(id)
);

-- Transactions: core transaction table
CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL CHECK(source IN ('square', 'bank', 'credit_card', 'manual')),
    source_account_id INTEGER,
    source_transaction_id TEXT,  -- Original ID from source system
    date DATE NOT NULL,
    description TEXT NOT NULL,
    amount REAL NOT NULL,  -- Positive = income, Negative = expense
    category_id INTEGER,
    vendor_id INTEGER,
    is_business INTEGER DEFAULT 1,  -- 1 = business, 0 = personal
    tax_year INTEGER,
    notes TEXT,
    raw_data TEXT,  -- JSON of original row data
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (source_account_id) REFERENCES accounts(id),
    FOREIGN KEY (category_id) REFERENCES categories(id),
    FOREIGN KEY (vendor_id) REFERENCES vendors(id)
);

-- Square Transactions: detailed Square data
CREATE TABLE IF NOT EXISTS square_daily (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date DATE NOT NULL,
    gross_sales REAL DEFAULT 0,
    returns REAL DEFAULT 0,
    discounts REAL DEFAULT 0,
    net_sales REAL DEFAULT 0,
    tips REAL DEFAULT 0,
    taxes_collected REAL DEFAULT 0,
    card_payments REAL DEFAULT 0,
    cash_payments REAL DEFAULT 0,
    processing_fees REAL DEFAULT 0,
    net_deposited REAL DEFAULT 0,
    transaction_count INTEGER DEFAULT 0,
    UNIQUE(date)
);

-- Sales Tax: track sales tax liability
CREATE TABLE IF NOT EXISTS sales_tax (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date DATE NOT NULL,
    collected REAL DEFAULT 0,
    remitted REAL DEFAULT 0,
    state TEXT DEFAULT 'CO',
    notes TEXT,
    UNIQUE(date, state)
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_transactions_date ON transactions(date);
CREATE INDEX IF NOT EXISTS idx_transactions_category ON transactions(category_id);
CREATE INDEX IF NOT EXISTS idx_transactions_tax_year ON transactions(tax_year);
CREATE INDEX IF NOT EXISTS idx_transactions_source ON transactions(source);
CREATE INDEX IF NOT EXISTS idx_square_daily_date ON square_daily(date);

-- Views for reporting
CREATE VIEW IF NOT EXISTS v_monthly_summary AS
SELECT 
    strftime('%Y-%m', date) as month,
    SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END) as total_income,
    SUM(CASE WHEN amount < 0 THEN ABS(amount) ELSE 0 END) as total_expenses,
    SUM(amount) as net_income
FROM transactions
WHERE is_business = 1
GROUP BY strftime('%Y-%m', date)
ORDER BY month;

CREATE VIEW IF NOT EXISTS v_category_summary AS
SELECT 
    c.name as category,
    c.type,
    c.schedule_c_line,
    SUM(ABS(t.amount)) as total,
    COUNT(*) as transaction_count
FROM transactions t
JOIN categories c ON t.category_id = c.id
WHERE t.is_business = 1
GROUP BY c.id
ORDER BY total DESC;

CREATE VIEW IF NOT EXISTS v_uncategorized AS
SELECT id, date, description, amount
FROM transactions
WHERE category_id IS NULL
ORDER BY date;
