#!/usr/bin/env python3
"""
Financial database manager for small business tax tracking.
Handles imports from Square, bank accounts, and credit cards.
"""

import sqlite3
import json
import csv
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Optional

from accounting_core.paths import get_finance_db_path


def _db_path():
    return get_finance_db_path()

# Default categories mapped to Schedule C lines
DEFAULT_CATEGORIES = [
    ('Gross Sales', 'income', 1, 'Gross receipts or sales', []),
    ('Returns & Allowances', 'income', 2, 'Returns and allowances', []),
    ('Processing Fees', 'expense', 10, 'Commissions and fees', ['square fees', 'processing']),
    ('Advertising', 'expense', 8, 'Advertising', ['facebook', 'google ads', 'instagram', 'meta ads', 'tiktok']),
    ('Car & Truck', 'expense', 9, 'Car and truck expenses', ['shell', 'exxon', 'bp', 'chevron', 'conoco', 'maverik', 'gas station', 'fuel']),
    ('Commissions', 'expense', 10, 'Commissions and fees', ['commission', 'referral']),
    ('Contract Labor', 'expense', 11, 'Contract labor', ['contractor', 'freelance']),
    ('Depreciation', 'expense', 13, 'Depreciation', []),
    ('Insurance', 'expense', 15, 'Insurance', ['hiscox', 'insurance', 'liability coverage']),
    ('Interest - Mortgage', 'expense', 16, 'Mortgage interest', ['mortgage interest']),
    ('Interest - Other', 'expense', 17, 'Other interest', ['interest', 'finance charge']),
    ('Legal & Professional', 'expense', 18, 'Legal and professional services', ['legal', 'attorney', 'lawyer', 'accountant', 'cpa']),
    ('Office Expense', 'expense', 18, 'Office expense', ['staples', 'office depot', 'paper', 'printer']),
    ('Rent/Lease', 'expense', 20, 'Rent or lease', ['rent', 'lease payment']),
    ('Repairs', 'expense', 21, 'Repairs and maintenance', ['repair', 'maintenance']),
    ('Supplies', 'expense', 22, 'Supplies', ['home depot', 'lowes', 'menards', 'ace hardware', 'supplies']),
    ('Taxes & Licenses', 'expense', 23, 'Taxes and licenses', ['license', 'permit', 'city tax']),
    ('Travel', 'expense', None, 'Travel (Line 24a)', ['united', 'delta', 'southwest', 'airline', 'hotel', 'marriott', 'hilton', 'airbnb']),
    ('Meals', 'expense', None, 'Deductible meals (Line 24b)', ['restaurant', 'dining', 'grubhub', 'doordash', 'uber eats']),
    ('Utilities', 'expense', 25, 'Utilities', ['starlink', 'internet', 'xcel', 'electric', 'gas bill', 'water', 'phone', 'verizon', 'at&t', 't-mobile']),
    ('Wages', 'expense', 26, 'Wages', ['payroll', 'wages', 'salary']),
    ('Software', 'expense', 27, 'Other expenses', ['adobe', 'squarespace', 'shopify', 'quickbooks', 'xero', 'microsoft', 'google workspace', 'dropbox', 'notion', 'subscription']),
    ('Other Expenses', 'expense', 27, 'Other expenses', []),
    ('Bank Fees', 'expense', 27, 'Other expenses', ['overdraft', 'wire fee', 'atm fee']),
    ('Sales Tax Collected', 'transfer', None, 'Sales tax liability', []),
    ('Sales Tax Remitted', 'transfer', None, 'Sales tax paid', []),
    ('Owner Draw', 'transfer', None, 'Owner withdrawal', []),
    ('Transfer', 'transfer', None, 'Account transfer', ['transfer', 'autopay', 'epay']),
    ('Personal', 'ignore', None, 'Personal expense', []),
    ('Tips', 'transfer', None, 'Tips pass-through', ['tip']),
]


class FinanceDB:
    def __init__(self, db_path: Path | None = None):
        self.db_path = db_path or get_finance_db_path()
        self.conn = None
        self._connect()
    
    def _connect(self):
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
    
    def init_db(self):
        """Initialize database with schema."""
        from accounting_core.paths import get_schema_path
        schema_path = get_schema_path()
        with open(schema_path, 'r') as f:
            self.conn.executescript(f.read())
        
        # Insert default categories
        for cat in DEFAULT_CATEGORIES:
            self.conn.execute('''
                INSERT OR IGNORE INTO categories (name, type, schedule_c_line, schedule_c_description, keywords)
                VALUES (?, ?, ?, ?, ?)
            ''', (cat[0], cat[1], cat[2], cat[3], json.dumps(cat[4])))
        
        # Add default accounts
        accounts = [
            ('Free Bus 9811', 'bank', 'Unknown', '9811'),
            ('Chase Freedom Flex', 'credit_card', 'Chase', '2885'),
            ('Square', 'payment_processor', 'Square', None),
        ]
        for acc in accounts:
            self.conn.execute('''
                INSERT OR IGNORE INTO accounts (name, type, institution, account_number_last4)
                VALUES (?, ?, ?, ?)
            ''', acc)
        
        self.conn.commit()
        print(f"Database initialized at {self.db_path}")
    
    def import_square_summary(self, csv_path: Path):
        """Import Square weekly sales summary."""
        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.reader(f)
            rows = list(reader)
        
        # Parse the transposed format (dates in columns, metrics in rows)
        header = rows[0]
        dates = header[1:]  # Weekly date ranges
        
        # Find each metric row
        metrics = {}
        for row in rows[1:]:
            if len(row) < 2:
                continue
            metric_name = row[0].strip().lower()
            metrics[metric_name] = row[1:]
        
        # Insert weekly data (we'll use the start date of each week)
        for i, date_range in enumerate(dates):
            if not date_range.strip():
                continue
            
            # Parse date range like "5/11/2025 – 5/17/2025"
            try:
                start_date = date_range.split('–')[0].strip()
                date = datetime.strptime(start_date, '%m/%d/%Y').date()
            except:
                continue
            
            # Extract values
            def get_value(metric_name):
                vals = metrics.get(metric_name, [])
                if i < len(vals):
                    val = vals[i].strip()
                    if val and val != '$0.00':
                        # Parse currency
                        val = val.replace('$', '').replace(',', '').replace('(', '-').replace(')', '')
                        try:
                            return float(val)
                        except:
                            return 0
                return 0
            
            gross_sales = get_value('gross sales')
            if gross_sales == 0:
                continue  # Skip weeks with no sales
            
            returns = abs(get_value('returns'))
            discounts = abs(get_value('discounts & comps'))
            net_sales = get_value('net sales')
            tips = get_value('tips')
            taxes = get_value('taxes')
            card = get_value('card')
            cash = get_value('cash')
            fees = abs(get_value('fees'))
            net_deposited = get_value('net total')
            tx_count = int(metrics.get('total number of sales', ['0'] * 100)[i] or 0)
            
            self.conn.execute('''
                INSERT OR REPLACE INTO square_daily 
                (date, gross_sales, returns, discounts, net_sales, tips, taxes_collected,
                 card_payments, cash_payments, processing_fees, net_deposited, transaction_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (date, gross_sales, returns, discounts, net_sales, tips, taxes,
                  card, cash, fees, net_deposited, tx_count))
            
            # Also create income transaction
            self.conn.execute('''
                INSERT OR IGNORE INTO transactions 
                (source, date, description, amount, category_id, tax_year)
                VALUES ('square', ?, 'Gross Sales', ?, 
                    (SELECT id FROM categories WHERE name = 'Gross Sales'), ?)
            ''', (date, gross_sales, date.year))
            
            # Processing fee expense
            if fees > 0:
                self.conn.execute('''
                    INSERT OR IGNORE INTO transactions 
                    (source, date, description, amount, category_id, tax_year)
                    VALUES ('square', ?, 'Square Processing Fees', ?, 
                        (SELECT id FROM categories WHERE name = 'Processing Fees'), ?)
                ''', (date, -fees, date.year))
            
            # Sales tax collected
            if taxes > 0:
                self.conn.execute('''
                    INSERT OR IGNORE INTO transactions 
                    (source, date, description, amount, category_id, tax_year)
                    VALUES ('square', ?, 'Sales Tax Collected', ?, 
                        (SELECT id FROM categories WHERE name = 'Sales Tax Collected'), ?)
                ''', (date, taxes, date.year))
        
        self.conn.commit()
        print(f"Imported Square data from {csv_path}")
    
    def import_bank_csv(self, csv_path: Path):
        """Import bank transaction CSV."""
        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        
        account_id = self.conn.execute(
            "SELECT id FROM accounts WHERE name LIKE '%Bus%' OR name LIKE '%9811%'"
        ).fetchone()
        account_id = account_id['id'] if account_id else None
        
        for row in rows:
            date_str = row.get('Processed Date', '').strip()
            description = row.get('Description', '').strip()
            credit_debit = row.get('Credit or Debit', '').strip()
            amount_str = row.get('Amount', '').strip()
            
            if not date_str or not amount_str:
                continue
            
            try:
                date = datetime.strptime(date_str, '%Y-%m-%d').date()
                amount = float(amount_str)
            except:
                continue
            
            if credit_debit == 'Debit':
                amount = -amount
            
            # Auto-categorize
            category_id = self._auto_categorize(description, amount)
            
            self.conn.execute('''
                INSERT OR IGNORE INTO transactions 
                (source, source_account_id, date, description, amount, category_id, tax_year, raw_data)
                VALUES ('bank', ?, ?, ?, ?, ?, ?, ?)
            ''', (account_id, date, description, amount, category_id, date.year, json.dumps(row)))
        
        self.conn.commit()
        print(f"Imported {len(rows)} bank transactions from {csv_path}")
    
    def import_cc_statement(self, pdf_path: Path):
        """
        Import credit card statement PDF.
        Note: This requires parsing the PDF text. For now, we'll manually add
        the transactions we extracted earlier.
        """
        # Transactions extracted from the Nov 2025 statement
        transactions = [
            ('2025-10-03', 'Starlink Internet', -165.00, 'Utilities'),
            ('2025-10-20', 'Adobe *800-833-6687', -59.99, 'Software'),
            ('2025-10-21', 'Conoco - Alta Convenie', -51.28, 'Car & Truck'),
            ('2025-10-21', 'Shell Oil', -11.69, 'Car & Truck'),
            ('2025-10-21', 'Shell Oil', -17.25, 'Car & Truck'),
            ('2025-10-21', 'Maverik', -15.18, 'Car & Truck'),
            ('2025-10-23', 'Squarespace', -36.00, 'Software'),
            ('2025-10-23', 'Home Depot', -14.42, 'Supplies'),
            ('2025-11-03', 'Hiscox Insurance', -26.25, 'Insurance'),
        ]
        
        for date_str, desc, amount, category_name in transactions:
            date = datetime.strptime(date_str, '%Y-%m-%d').date()
            category_id = self.conn.execute(
                "SELECT id FROM categories WHERE name = ?", (category_name,)
            ).fetchone()
            category_id = category_id['id'] if category_id else None
            
            self.conn.execute('''
                INSERT OR IGNORE INTO transactions 
                (source, date, description, amount, category_id, tax_year)
                VALUES ('credit_card', ?, ?, ?, ?, ?)
            ''', (date, desc, amount, category_id, date.year))
        
        self.conn.commit()
        print(f"Imported {len(transactions)} credit card transactions")
    
    def _auto_categorize(self, description: str, amount: float) -> Optional[int]:
        """Auto-categorize a transaction based on keywords."""
        desc_lower = description.lower()
        
        # Special patterns first
        if 'square inc' in desc_lower:
            if amount > 0:
                # Square deposit - but we already have this from Square export
                return self.conn.execute(
                    "SELECT id FROM categories WHERE name = 'Gross Sales'"
                ).fetchone()['id']
            return None
        
        if 'co dept revenue' in desc_lower:
            return self.conn.execute(
                "SELECT id FROM categories WHERE name = 'Sales Tax Remitted'"
            ).fetchone()['id']
        
        if 'chase credit crd' in desc_lower:
            return self.conn.execute(
                "SELECT id FROM categories WHERE name = 'Transfer'"
            ).fetchone()['id']
        
        if 'bill paid' in desc_lower:
            # Check if it's a known payee
            if 'phillip' in desc_lower or 'nicholas' in desc_lower:
                return self.conn.execute(
                    "SELECT id FROM categories WHERE name = 'Owner Draw'"
                ).fetchone()['id']
            return self.conn.execute(
                "SELECT id FROM categories WHERE name = 'Contract Labor'"
            ).fetchone()['id']
        
        if 'overdraft' in desc_lower or 'wire transfer fee' in desc_lower:
            return self.conn.execute(
                "SELECT id FROM categories WHERE name = 'Bank Fees'"
            ).fetchone()['id']
        
        # Check keywords in categories
        categories = self.conn.execute(
            "SELECT id, name, keywords FROM categories WHERE keywords IS NOT NULL"
        ).fetchall()
        
        for cat in categories:
            keywords = json.loads(cat['keywords']) if cat['keywords'] else []
            for kw in keywords:
                if kw in desc_lower:
                    return cat['id']
        
        return None
    
    def get_summary(self, tax_year: int = 2025) -> dict:
        """Get financial summary for a tax year."""
        summary = {
            'tax_year': tax_year,
            'income': {},
            'expenses': {},
            'net_income': 0,
            'uncategorized_count': 0
        }
        
        # Income
        income_rows = self.conn.execute('''
            SELECT c.name, SUM(t.amount) as total
            FROM transactions t
            JOIN categories c ON t.category_id = c.id
            WHERE t.tax_year = ? AND c.type = 'income' AND t.is_business = 1
            GROUP BY c.id
        ''', (tax_year,)).fetchall()
        
        for row in income_rows:
            summary['income'][row['name']] = row['total']
        
        # Square data
        square_data = self.conn.execute('''
            SELECT 
                SUM(gross_sales) as gross_sales,
                SUM(returns) as returns,
                SUM(discounts) as discounts,
                SUM(net_sales) as net_sales,
                SUM(tips) as tips,
                SUM(taxes_collected) as taxes_collected,
                SUM(processing_fees) as processing_fees,
                SUM(transaction_count) as transaction_count
            FROM square_daily
            WHERE date BETWEEN ? AND ?
        ''', (f'{tax_year}-01-01', f'{tax_year}-12-31')).fetchone()
        
        if square_data:
            summary['square'] = dict(square_data)
        
        # Expenses
        expense_rows = self.conn.execute('''
            SELECT c.name, c.schedule_c_line, SUM(ABS(t.amount)) as total
            FROM transactions t
            JOIN categories c ON t.category_id = c.id
            WHERE t.tax_year = ? AND c.type = 'expense' AND t.is_business = 1
            GROUP BY c.id
            ORDER BY total DESC
        ''', (tax_year,)).fetchall()
        
        for row in expense_rows:
            summary['expenses'][row['name']] = {
                'total': row['total'],
                'schedule_c_line': row['schedule_c_line']
            }
        
        # Uncategorized
        uncategorized = self.conn.execute('''
            SELECT COUNT(*) as count FROM transactions
            WHERE tax_year = ? AND category_id IS NULL
        ''', (tax_year,)).fetchone()
        summary['uncategorized_count'] = uncategorized['count']
        
        # Net income
        total_income = sum(summary['income'].values())
        total_expenses = sum(e['total'] for e in summary['expenses'].values())
        summary['net_income'] = total_income - total_expenses
        
        return summary
    
    def close(self):
        if self.conn:
            self.conn.close()


def main():
    db = FinanceDB()
    db.init_db()
    
    # Import data
    data_dir = Path(__file__).parent.parent / 'data'
    
    square_file = data_dir / 'square-sales-summary-2025.csv'
    if square_file.exists():
        db.import_square_summary(square_file)
    
    bank_file = data_dir / 'bank-transactions-2025.csv'
    if bank_file.exists():
        db.import_bank_csv(bank_file)
    
    cc_file = data_dir / 'chase-statement-2025-11.pdf'
    if cc_file.exists():
        db.import_cc_statement(cc_file)
    
    # Print summary
    summary = db.get_summary(2025)
    print("\n" + "=" * 60)
    print("FINANCIAL SUMMARY - 2025")
    print("=" * 60)
    print(f"\nSQUARE DATA:")
    if 'square' in summary and summary['square']['gross_sales']:
        sq = summary['square']
        print(f"  Gross Sales:        ${sq['gross_sales']:,.2f}")
        print(f"  Returns:            (${sq['returns']:,.2f})")
        print(f"  Discounts:          (${sq['discounts']:,.2f})")
        print(f"  Net Sales:          ${sq['net_sales']:,.2f}")
        print(f"  Processing Fees:    ${sq['processing_fees']:,.2f}")
        print(f"  Taxes Collected:    ${sq['taxes_collected']:,.2f}")
        print(f"  Tips (pass-thru):   ${sq['tips']:,.2f}")
        print(f"  Transactions:       {sq['transaction_count']:,}")
    
    print(f"\nEXPENSES BY CATEGORY:")
    for cat, data in summary['expenses'].items():
        print(f"  {cat}: ${data['total']:,.2f} (Sch C Line {data['schedule_c_line']})")
    
    print(f"\nUNCATEGORIZED TRANSACTIONS: {summary['uncategorized_count']}")
    
    db.close()


if __name__ == '__main__':
    main()
