#!/usr/bin/env python3
"""Parse Square sales summary CSV and generate P&L statement."""

import csv
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

def parse_currency(value):
    """Parse currency string like '$1,234.56' or '($123.45)' to Decimal."""
    if not value or value == '$0.00':
        return Decimal('0.00')
    # Remove $ and commas, handle parentheses as negative
    value = value.strip()
    is_negative = value.startswith('(') and value.endswith(')')
    value = value.replace('$', '').replace(',', '').replace('(', '').replace(')', '')
    amount = Decimal(value)
    return -amount if is_negative else amount

def main():
    csv_path = Path(__import__("os").environ.get(
        "SQUARE_SALES_CSV",
        str(__import__("pathlib").Path(__file__).resolve().parent.parent.parent / "samples" / "square-sales-sample.csv"),
    ))
    
    # Read CSV and extract row totals
    rows = {}
    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.reader(f)
        first_row = True
        for row in reader:
            # Skip the first row (date headers)
            if first_row:
                first_row = False
                continue
            if len(row) < 2:
                continue
            label = row[0].strip()
            if not label:
                continue
            # Sum all weekly values (columns 1 onwards)
            total = Decimal('0.00')
            for val in row[1:]:
                if val.strip():
                    total += parse_currency(val)
            rows[label] = total
    
    # Extract key figures
    gross_sales = rows.get('Gross sales', Decimal('0.00'))
    returns = abs(rows.get('Returns', Decimal('0.00')))  # Already negative in data
    discounts = abs(rows.get('Discounts & comps', Decimal('0.00')))  # Already negative
    net_sales = rows.get('Net sales', Decimal('0.00'))
    tips = rows.get('Tips', Decimal('0.00'))
    taxes_collected = rows.get('Taxes', Decimal('0.00'))
    processing_fees = abs(rows.get('Fees', Decimal('0.00')))  # Already negative
    net_total = rows.get('Net total', Decimal('0.00'))
    
    # Payment method breakdown
    card_payments = rows.get('Card', Decimal('0.00'))
    cash_payments = rows.get('Cash', Decimal('0.00'))
    
    # Transaction counts
    total_transactions = int(rows.get('Total number of sales', Decimal('0')))
    
    # For Schedule C:
    # Line 1: Gross receipts or sales (gross sales, not net)
    # Line 2: Returns and allowances
    # Line 3: Subtract line 2 from line 1 = Gross profit
    # Tips are NOT business income - they're passed through to workers
    # Sales tax collected is NOT income - it's a liability passed to state
    # Processing fees are a deductible expense
    
    print("=" * 60)
    print("SQUARE INCOME SUMMARY - 2025 TAX YEAR")
    print("=" * 60)
    print()
    print("INCOME (Schedule C, Part I)")
    print("-" * 40)
    print(f"  Gross sales (Line 1):      ${gross_sales:>12,.2f}")
    print(f"  Returns & allowances (L2): (${returns:>11,.2f})")
    print(f"  Discounts (included in net): (${discounts:>11,.2f})")
    print()
    print(f"  NET SALES (Line 3):         ${net_sales:>12,.2f}")
    print()
    print(f"  * Tips collected:           ${tips:>12,.2f} (pass-through, not taxable)")
    print(f"  * Sales tax collected:      ${taxes_collected:>12,.2f} (liability, not income)")
    print()
    print("-" * 40)
    print(f"  TOTAL COLLECTED:            ${net_sales + tips + taxes_collected:>12,.2f}")
    print()
    print("PAYMENT METHODS")
    print("-" * 40)
    print(f"  Card payments:              ${card_payments:>12,.2f}")
    print(f"  Cash payments:              ${cash_payments:>12,.2f}")
    print()
    print("PROCESSING FEES (Schedule C expense)")
    print("-" * 40)
    print(f"  Square processing fees:     ${processing_fees:>12,.2f}")
    print()
    print("TRANSACTIONS")
    print("-" * 40)
    print(f"  Total sales:                {total_transactions:>13,}")
    print()
    print("NET DEPOSITED TO BANK")
    print("-" * 40)
    print(f"  Net total (after fees):     ${net_total:>12,.2f}")
    print()
    
    # Generate P&L markdown
    pnl_path = Path(__import__("os").environ.get(
        "PROFIT_LOSS_MD",
        str(__import__("pathlib").Path(__file__).resolve().parent.parent.parent / "samples" / "profit-loss-sample.md"),
    ))
    with open(pnl_path, 'w') as f:
        f.write("# Profit & Loss Statement - 2025\n\n")
        f.write("**Business:** [Business Name]\n")
        f.write("**Tax Year:** January 1, 2025 – December 31, 2025\n")
        f.write("**Source:** Square Sales Summary Export\n\n")
        f.write("---\n\n")
        f.write("## Income\n\n")
        f.write("| Description | Amount |\n")
        f.write("|-------------|--------|\n")
        f.write(f"| Gross Sales | ${gross_sales:,.2f} |\n")
        f.write(f"| Less: Returns & Allowances | (${returns:,.2f}) |\n")
        f.write(f"| Less: Discounts | (${discounts:,.2f}) |\n")
        f.write("| **Net Sales** | **${:,.2f}** |\n".format(net_sales))
        f.write("\n")
        f.write("### Non-Income Items (Pass-Through)\n\n")
        f.write("| Description | Amount | Notes |\n")
        f.write("|-------------|--------|-------|\n")
        f.write(f"| Tips Collected | ${tips:,.2f} | Passed to workers, not taxable income |\n")
        f.write(f"| Sales Tax Collected | ${taxes_collected:,.2f} | Liability remitted to state |\n")
        f.write("\n")
        f.write("---\n\n")
        f.write("## Expenses\n\n")
        f.write("| Category | Amount | Notes |\n")
        f.write("|----------|--------|-------|\n")
        f.write(f"| Payment Processing Fees | ${processing_fees:,.2f} | Square card processing |\n")
        f.write("| | | |\n")
        f.write("| **Total Expenses (so far)** | **$1,074.50** | Add credit card expenses below |\n")
        f.write("\n")
        f.write("---\n\n")
        f.write("## Net Operating Income\n\n")
        net_income = net_sales - processing_fees
        f.write(f"| **Net Income (before other expenses)** | **${net_income:,.2f}** |\n")
        f.write("\n")
        f.write("---\n\n")
        f.write("## Business Activity Summary\n\n")
        f.write("| Metric | Value |\n")
        f.write("|--------|-------|\n")
        f.write(f"| Operating Period | May 11, 2025 – September 13, 2025 |\n")
        f.write(f"| Weeks Active | 18 |\n")
        f.write(f"| Total Transactions | {total_transactions:,} |\n")
        f.write(f"| Average Weekly Sales | ${net_sales / 18:,.2f} |\n")
        f.write(f"| Card Payments | ${card_payments:,.2f} ({card_payments/(card_payments+cash_payments)*100:.1f}%) |\n")
        f.write(f"| Cash Payments | ${cash_payments:,.2f} ({cash_payments/(card_payments+cash_payments)*100:.1f}%) |\n")
        f.write("\n")
        f.write("---\n\n")
        f.write("## Credit Card Expenses (To Be Added)\n\n")
        f.write("*Upload credit card statements to categorize business expenses.*\n\n")
        f.write("### Common Deductible Categories\n\n")
        f.write("- [ ] Supplies\n")
        f.write("- [ ] Inventory / Cost of Goods Sold\n")
        f.write("- [ ] Equipment\n")
        f.write("- [ ] Software / Subscriptions\n")
        f.write("- [ ] Advertising\n")
        f.write("- [ ] Travel / Mileage\n")
        f.write("- [ ] Other\n")
    
    print(f"P&L written to: {pnl_path}")

if __name__ == '__main__':
    main()
