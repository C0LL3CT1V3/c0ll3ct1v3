#!/usr/bin/env python3
"""
Import Chase credit card transactions and rebuild expense database.
"""

import sqlite3
import csv
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from accounting_core.paths import get_finance_db_path


def _db_path():
    return get_finance_db_path()

# Map Chase categories to our categories
CATEGORY_MAP = {
    'Bills & Utilities': None,  # Will use keywords
    'Food & Drink': None,  # Need to distinguish inventory vs meals
    'Gas': 'Car & Truck',
    'Merchandise & Inventory': 'Supplies',  # Or Cost of Goods Sold
    'Office & Shipping': 'Office Expense',
    'Professional Services': 'Software',
    'Repair & Maintenance': 'Repairs',
    'Automotive': 'Car & Truck',
    'Education': 'Other Expenses',
    'Gifts & Donations': 'Other Expenses',
    'Fees & Adjustments': 'Other Expenses',
}

# Vendor-based categorization (more specific than Chase categories)
VENDOR_CATEGORIES = {
    # Coffee suppliers - these are inventory, not meals
    'boxcar coffee': 'Supplies',
    'sp barista': 'Supplies',
    'espresso parts': 'Supplies',
    'voltage coffee': 'Supplies',
    'captain + stoker': 'Supplies',
    'compact coffee': 'Supplies',
    'coffee by topo': 'Supplies',
    'the silver whisker': 'Supplies',
    'webstaurant store': 'Supplies',
    
    # Software/subscriptions
    'adobe': 'Software',
    'squarespace': 'Software',
    'sqsp': 'Software',
    
    # Insurance
    'hiscox': 'Insurance',
    
    # Internet
    'starlink': 'Utilities',
    
    # Hardware stores
    'home depot': 'Repairs',
    'ace hardware': 'Repairs',
    'poncha lumber': 'Repairs',
    
    # Gas
    'shell oil': 'Car & Truck',
    'conoco': 'Car & Truck',
    'maverik': 'Car & Truck',
    
    # Inventory/supplies
    'amazon': 'Supplies',
    'temu': 'Supplies',
    'walmart': 'Supplies',
    'wm supercenter': 'Supplies',
    'ebay': 'Supplies',
    'adorama': 'Supplies',
    'spark fun': 'Supplies',
    'adafruit': 'Supplies',
    
    # Auto parts
    'autozone': 'Car & Truck',
    'napa auto': 'Car & Truck',
    'parts geek': 'Car & Truck',
    'parts town': 'Supplies',
    'auto paint': 'Car & Truck',
    
    # Insurance
    'progressive': 'Insurance',
    
    # Government fees
    'chaffee county': 'Taxes & Licenses',
    'co motor veh': 'Taxes & Licenses',
    'salida *gov': 'Taxes & Licenses',
    
    # Training
    '360training': 'Other Expenses',
    
    # Thrift/vintage (for resale?)
    'antiques and what nots': 'Supplies',
    'arc thrift': 'Supplies',
    'new horizons thrift': 'Supplies',
    'the globe': 'Supplies',
    
    # Square hardware
    'square hardware': 'Equipment',
    
    # Food that's likely inventory
    'scanga meat': 'Supplies',
    'lagree': 'Supplies',  # LaGree's Food Store - inventory
    'safeway': 'Supplies',  # Likely inventory
}

def categorize_transaction(description: str, chase_category: str, amount: float) -> str:
    """Determine category based on vendor and context."""
    desc_lower = description.lower()
    
    # Check vendor-specific mappings first
    for vendor, category in VENDOR_CATEGORIES.items():
        if vendor in desc_lower:
            return category
    
    # Payments to card are transfers
    if 'payment thank' in desc_lower or 'automatic payment' in desc_lower:
        return 'Transfer'
    
    # Pay yourself back credits
    if 'payyourselfback' in desc_lower:
        return 'Transfer'
    
    # Square hardware
    if 'square hardware' in desc_lower:
        return 'Equipment'
    
    # Default to Chase category if mapped, otherwise Other
    return CATEGORY_MAP.get(chase_category, 'Other Expenses')


def import_chase_csv(csv_path: Path):
    """Import Chase credit card transaction CSV."""
    conn = sqlite3.connect(_db_path())
    
    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    
    imported = 0
    skipped = 0
    
    for row in rows:
        card = row.get('Card', '').strip()
        date_str = row.get('Transaction Date', '').strip()
        post_date = row.get('Post Date', '').strip()
        description = row.get('Description', '').strip()
        category = row.get('Category', '').strip()
        tx_type = row.get('Type', '').strip()
        amount_str = row.get('Amount', '').strip()
        memo = row.get('Memo', '').strip()
        
        if not date_str or not amount_str:
            continue
        
        try:
            date = datetime.strptime(date_str, '%m/%d/%Y').date()
            amount = float(amount_str)
        except:
            continue
        
        # Skip if it's a payment (positive amount for payments)
        if amount > 0:
            skipped += 1
            continue
        
        # Get account ID for this card
        account_row = conn.execute(
            "SELECT id FROM accounts WHERE account_number_last4 = ?", (card,)
        ).fetchone()
        account_id = account_row[0] if account_row else None
        
        # Categorize
        category_name = categorize_transaction(description, category, amount)
        
        # Get category ID
        cat_row = conn.execute(
            "SELECT id FROM categories WHERE name = ?", (category_name,)
        ).fetchone()
        category_id = cat_row[0] if cat_row else None
        
        # Check if already imported
        existing = conn.execute('''
            SELECT id FROM transactions 
            WHERE date = ? AND description = ? AND amount = ?
        ''', (date, description, amount)).fetchone()
        
        if existing:
            skipped += 1
            continue
        
        # Insert
        conn.execute('''
            INSERT INTO transactions 
            (source, source_account_id, date, description, amount, category_id, tax_year, raw_data)
            VALUES ('credit_card', ?, ?, ?, ?, ?, ?, ?)
        ''', (account_id, date, description, amount, category_id, date.year, 
              f'{{"card": "{card}", "post_date": "{post_date}", "chase_category": "{category}", "memo": "{memo}"}}'))
        
        imported += 1
    
    conn.commit()
    conn.close()
    
    print(f"Imported {imported} credit card transactions, skipped {skipped}")
    return imported


def summarize_by_category(tax_year: int = 2025):
    """Summarize expenses by category for a tax year."""
    conn = sqlite3.connect(_db_path())
    conn.row_factory = sqlite3.Row
    
    # Get expenses by category
    expenses = conn.execute('''
        SELECT c.name, c.schedule_c_line, SUM(ABS(t.amount)) as total, COUNT(*) as count
        FROM transactions t
        JOIN categories c ON t.category_id = c.id
        WHERE t.tax_year = ? AND c.type = 'expense' AND t.is_business = 1
        GROUP BY c.id
        ORDER BY total DESC
    ''', (tax_year,)).fetchall()
    
    print(f"\nEXPENSE SUMMARY - {tax_year}")
    print("=" * 60)
    total = 0
    for e in expenses:
        print(f"{e['name']:30} ${e['total']:>10,.2f} ({e['count']} txns) [Line {e['schedule_c_line'] or '27'}]")
        total += e['total']
    
    print("-" * 60)
    print(f"{'TOTAL EXPENSES':30} ${total:>10,.2f}")
    
    conn.close()
    return total


if __name__ == '__main__':
    import os
    from accounting_core.paths import get_samples_dir

    csv_path = Path(os.environ.get("CHASE_CSV", str(get_samples_dir() / "chase-sample.csv")))
    if csv_path.exists():
        print("Importing Chase credit card transactions...")
        import_chase_csv(csv_path)
        summarize_by_category(2025)
    else:
        print(f"File not found: {csv_path}")
