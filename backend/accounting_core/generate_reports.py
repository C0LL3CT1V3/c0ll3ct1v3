#!/usr/bin/env python3
"""Generate financial reports from the finance database."""

import sqlite3
from decimal import Decimal
from pathlib import Path
from datetime import datetime

from accounting_core.paths import get_finance_db_path


def _db_path():
    return get_finance_db_path()

def generate_pl_statement(tax_year: int = 2025, output_path: Path = None):
    """Generate a Profit & Loss statement for a tax year."""
    conn = sqlite3.connect(_db_path())
    conn.row_factory = sqlite3.Row
    
    # Get Square data
    square = conn.execute('''
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
    
    # Get expenses by category
    expenses = conn.execute('''
        SELECT c.name, c.schedule_c_line, c.schedule_c_description, SUM(ABS(t.amount)) as total
        FROM transactions t
        JOIN categories c ON t.category_id = c.id
        WHERE t.tax_year = ? AND c.type = 'expense' AND t.is_business = 1
        GROUP BY c.id
        ORDER BY total DESC
    ''', (tax_year,)).fetchall()
    
    # Get uncategorized
    uncategorized = conn.execute('''
        SELECT date, description, amount FROM transactions
        WHERE tax_year = ? AND category_id IS NULL
        ORDER BY ABS(amount) DESC
    ''', (tax_year,)).fetchall()
    
    # Get owner draws
    draws = conn.execute('''
        SELECT SUM(ABS(amount)) as total FROM transactions t
        JOIN categories c ON t.category_id = c.id
        WHERE t.tax_year = ? AND c.name = 'Owner Draw'
    ''', (tax_year,)).fetchone()
    
    # Get sales tax remitted
    tax_remitted = conn.execute('''
        SELECT SUM(ABS(amount)) as total FROM transactions t
        JOIN categories c ON t.category_id = c.id
        WHERE t.tax_year = ? AND c.name = 'Sales Tax Remitted'
    ''', (tax_year,)).fetchone()
    
    # Calculate totals
    gross_sales = square['gross_sales'] or 0
    returns = square['returns'] or 0
    discounts = square['discounts'] or 0
    net_sales = square['net_sales'] or 0
    processing_fees = square['processing_fees'] or 0
    total_expenses = sum(e['total'] for e in expenses)
    
    # Build report
    lines = []
    lines.append(f"# Profit & Loss Statement - {tax_year}")
    lines.append("")
    lines.append("**Business:** [Business Name]")
    lines.append(f"**Tax Year:** January 1, {tax_year} – December 31, {tax_year}")
    lines.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Part I: Income (Schedule C)")
    lines.append("")
    lines.append("| Line | Description | Amount |")
    lines.append("|------|-------------|--------|")
    lines.append(f"| 1 | Gross receipts or sales | ${gross_sales:,.2f} |")
    lines.append(f"| 2 | Returns and allowances | (${returns + discounts:,.2f}) |")
    lines.append(f"| 3 | **Net sales** (Line 1 - Line 2) | **${net_sales:,.2f}** |")
    lines.append("")
    lines.append("### Non-Taxable Items")
    lines.append("")
    lines.append("| Description | Amount | Notes |")
    lines.append("|-------------|--------|-------|")
    lines.append(f"| Tips collected | ${square['tips'] or 0:,.2f} | Pass-through to workers |")
    lines.append(f"| Sales tax collected | ${square['taxes_collected'] or 0:,.2f} | Remitted to state |")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Part II: Expenses (Schedule C)")
    lines.append("")
    lines.append("| Line | Category | Amount |")
    lines.append("|------|----------|--------|")
    
    # Group by Schedule C line
    by_line = {}
    for e in expenses:
        line = e['schedule_c_line'] or 27
        if line not in by_line:
            by_line[line] = []
        by_line[line].append(e)
    
    for line_num in sorted(by_line.keys()):
        for e in by_line[line_num]:
            lines.append(f"| {e['schedule_c_line'] or '27'} | {e['name']} | ${e['total']:,.2f} |")
    
    lines.append(f"| | **Total Expenses** | **${total_expenses:,.2f}** |")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Net Operating Income")
    lines.append("")
    net_income = net_sales - total_expenses
    lines.append(f"| **Net Profit (Line 3 - Total Expenses)** | **${net_income:,.2f}** |")
    lines.append("")
    
    # Self-employment tax calculation
    se_tax = net_income * 0.9235 * 0.153 if net_income > 0 else 0
    lines.append("### Self-Employment Tax (Schedule SE)")
    lines.append("")
    lines.append(f"| Net earnings (92.35% of net profit) | ${net_income * 0.9235:,.2f} |")
    lines.append(f"| Self-employment tax (15.3%) | ${se_tax:,.2f} |")
    lines.append(f"| Deductible SE tax (50%) | ${se_tax / 2:,.2f} |")
    lines.append("")
    
    lines.append("---")
    lines.append("")
    lines.append("## Business Activity Summary")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|--------|-------|")
    
    # Get date range
    date_range = conn.execute('''
        SELECT MIN(date) as start, MAX(date) as end FROM square_daily
        WHERE gross_sales > 0
    ''').fetchone()
    
    lines.append(f"| Operating Period | {date_range['start']} to {date_range['end']} |")
    lines.append(f"| Total Transactions | {square['transaction_count'] or 0:,} |")
    lines.append(f"| Average Transaction | ${(gross_sales / (square['transaction_count'] or 1)):,.2f} |")
    lines.append(f"| Owner Draws | ${(draws['total'] or 0):,.2f} |")
    lines.append(f"| Sales Tax Remitted | ${(tax_remitted['total'] or 0):,.2f} |")
    lines.append("")
    
    # Uncategorized section
    if uncategorized:
        lines.append("---")
        lines.append("")
        lines.append("## ⚠️ Uncategorized Transactions (Require Review)")
        lines.append("")
        lines.append(f"Found {len(uncategorized)} uncategorized transactions.")
        lines.append("")
        lines.append("| Date | Description | Amount |")
        lines.append("|------|-------------|--------|")
        for tx in uncategorized[:20]:  # Show first 20
            lines.append(f"| {tx['date']} | {tx['description'][:40]}... | ${tx['amount']:,.2f} |")
        if len(uncategorized) > 20:
            lines.append(f"| | *...and {len(uncategorized) - 20} more* | |")
        lines.append("")
    
    lines.append("---")
    lines.append("")
    lines.append("## Notes & Questions")
    lines.append("")
    lines.append("### Owner Draws")
    lines.append("")
    lines.append(f"Total owner draws: ${(draws['total'] or 0):,.2f}")
    lines.append("- Owner draws are **not deductible** expenses")
    lines.append("- They represent money taken out of the business")
    lines.append("- Already included in net profit calculation above")
    lines.append("")
    lines.append("### Sales Tax")
    lines.append("")
    lines.append(f"- Collected: ${square['taxes_collected'] or 0:,.2f}")
    lines.append(f"- Remitted: ${tax_remitted['total'] or 0:,.2f}")
    lines.append("- Difference may be due to timing or rounding")
    lines.append("")
    lines.append("### Next Steps")
    lines.append("")
    lines.append("- [ ] Review uncategorized transactions")
    lines.append("- [ ] Confirm all expenses are business-related")
    lines.append("- [ ] Gather any missing receipts")
    lines.append("- [ ] Calculate home office deduction (Form 8829)")
    lines.append("- [ ] File Schedule C with Form 1040")
    lines.append("")
    
    report = "\n".join(lines)
    
    if output_path:
        with open(output_path, 'w') as f:
            f.write(report)
        print(f"Report written to: {output_path}")
    else:
        print(report)
    
    conn.close()
    return report


def generate_schedule_c_data(tax_year: int = 2025):
    """Generate data ready for Schedule C form filling."""
    conn = sqlite3.connect(_db_path())
    conn.row_factory = sqlite3.Row
    
    # Get all the data needed for Schedule C
    square = conn.execute('''
        SELECT 
            SUM(gross_sales) as gross_sales,
            SUM(returns) as returns,
            SUM(discounts) as discounts,
            SUM(net_sales) as net_sales,
            SUM(processing_fees) as processing_fees
        FROM square_daily
        WHERE date BETWEEN ? AND ?
    ''', (f'{tax_year}-01-01', f'{tax_year}-12-31')).fetchone()
    
    expenses_by_line = conn.execute('''
        SELECT c.schedule_c_line, SUM(ABS(t.amount)) as total
        FROM transactions t
        JOIN categories c ON t.category_id = c.id
        WHERE t.tax_year = ? AND c.type = 'expense' AND t.is_business = 1 AND c.schedule_c_line IS NOT NULL
        GROUP BY c.schedule_c_line
    ''', (tax_year,)).fetchall()
    
    # Build line dictionary
    lines = {
        1: square['gross_sales'] or 0,
        2: (square['returns'] or 0) + (square['discounts'] or 0),
    }
    lines[3] = lines[1] - lines[2]
    
    for e in expenses_by_line:
        lines[e['schedule_c_line']] = e['total']
    
    # Line 28: Total expenses
    lines[28] = sum(v for k, v in lines.items() if k >= 8 and k <= 27)
    
    # Line 29: Tentative profit
    lines[29] = lines[3] - lines[28]
    
    # Line 31: Net profit
    lines[31] = lines[29]  # Assuming no home office for now
    
    print("SCHEDULE C LINE VALUES")
    print("=" * 40)
    for line_num in sorted(lines.keys()):
        print(f"Line {line_num:2d}: ${lines[line_num]:,.2f}")
    
    conn.close()
    return lines


if __name__ == '__main__':
    import os
    import sys

    from accounting_core.paths import repo_root

    if len(sys.argv) > 1 and sys.argv[1] == '--schedule-c':
        generate_schedule_c_data(2025)
    else:
        default_out = repo_root() / "samples" / "out" / "profit-loss-sample.md"
        output = Path(os.environ.get("PROFIT_LOSS_OUTPUT", str(default_out)))
        output.parent.mkdir(parents=True, exist_ok=True)
        generate_pl_statement(2025, output)
