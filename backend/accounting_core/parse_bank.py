#!/usr/bin/env python3
"""Parse bank transactions CSV and categorize for tax purposes."""

import csv
from decimal import Decimal
from datetime import datetime
from collections import defaultdict
from pathlib import Path

def main():
    csv_path = Path(__import__("os").environ.get(
        "BANK_CSV",
        str(__import__("pathlib").Path(__file__).resolve().parent.parent.parent / "samples" / "chase-sample.csv"),
    ))
    
    transactions = []
    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            date_str = row.get('Processed Date', '').strip()
            description = row.get('Description', '').strip()
            credit_debit = row.get('Credit or Debit', '').strip()
            amount_str = row.get('Amount', '').strip()
            
            if not date_str or not amount_str:
                continue
            
            try:
                date = datetime.strptime(date_str, '%Y-%m-%d')
                amount = Decimal(amount_str)
            except:
                continue
            
            if credit_debit == 'Debit':
                amount = -amount
            
            transactions.append({
                'date': date,
                'description': description,
                'amount': amount
            })
    
    # Categorize transactions
    categories = defaultdict(list)
    
    for tx in transactions:
        desc_lower = tx['description'].lower()
        
        if 'square inc' in desc_lower:
            if 'acctverify' in desc_lower:
                categories['square_verify'].append(tx)
            elif tx['amount'] > 0:
                categories['square_deposits'].append(tx)
            else:
                categories['square_other'].append(tx)
        elif 'co dept revenue' in desc_lower:
            categories['sales_tax_payments'].append(tx)
        elif 'chase credit crd' in desc_lower:
            categories['chase_cc_payments'].append(tx)
        elif 'bill paid' in desc_lower:
            categories['bill_payments'].append(tx)
        elif 'wire transfer' in desc_lower:
            categories['wire_transfers'].append(tx)
        elif 'check' in desc_lower:
            categories['checks'].append(tx)
        elif 'dda regular deposit' in desc_lower:
            categories['dda_deposits'].append(tx)
        elif 'atm w/d' in desc_lower:
            categories['atm_withdrawals'].append(tx)
        elif 'overdraft fee' in desc_lower:
            categories['bank_fees'].append(tx)
        elif 'domestic wire transfer fee' in desc_lower:
            categories['bank_fees'].append(tx)
        elif 'venmo' in desc_lower:
            categories['venmo'].append(tx)
        else:
            categories['other'].append(tx)
    
    # Print summary
    print("=" * 70)
    print("BANK ACCOUNT ANALYSIS - 2025")
    print("=" * 70)
    print()
    
    # Square Deposits
    square_deposits = categories['square_deposits']
    total_square = sum(tx['amount'] for tx in square_deposits)
    print(f"SQUARE DEPOSITS (Net after fees)")
    print("-" * 50)
    print(f"  Count: {len(square_deposits)}")
    print(f"  Total: ${total_square:,.2f}")
    print(f"  Period: {min(tx['date'] for tx in square_deposits).strftime('%Y-%m-%d')} to {max(tx['date'] for tx in square_deposits).strftime('%Y-%m-%d')}")
    print()
    
    # Sales Tax Payments
    tax_payments = categories['sales_tax_payments']
    total_tax = sum(tx['amount'] for tx in tax_payments)
    print(f"SALES TAX PAYMENTS (to Colorado Dept of Revenue)")
    print("-" * 50)
    for tx in sorted(tax_payments, key=lambda x: x['date']):
        print(f"  {tx['date'].strftime('%Y-%m-%d')}: ${-tx['amount']:,.2f}")
    print(f"  TOTAL: ${-total_tax:,.2f}")
    print()
    
    # Chase CC Payments
    cc_payments = categories['chase_cc_payments']
    total_cc = sum(tx['amount'] for tx in cc_payments)
    print(f"CHASE CREDIT CARD PAYMENTS")
    print("-" * 50)
    for tx in sorted(cc_payments, key=lambda x: x['date']):
        print(f"  {tx['date'].strftime('%Y-%m-%d')}: ${-tx['amount']:,.2f}")
    print(f"  TOTAL: ${-total_cc:,.2f}")
    print()
    
    # Bill Payments (need clarification)
    bill_payments = categories['bill_payments']
    total_bills = sum(tx['amount'] for tx in bill_payments)
    print(f"BILL PAYMENTS (needs classification)")
    print("-" * 50)
    payees = defaultdict(Decimal)
    for tx in bill_payments:
        # Extract payee name
        desc = tx['description']
        if 'PHILLIP WARD' in desc:
            payees['Phillip Ward'] += tx['amount']
        elif 'NICHOLAS MACIEL' in desc:
            payees['Nicholas Maciel'] += tx['amount']
        elif 'DANIELLE HAUGER' in desc:
            payees['Danielle Hauger'] += tx['amount']
        elif 'MOLLY JONES' in desc:
            payees['Molly Jones'] += tx['amount']
    
    for payee, amount in sorted(payees.items(), key=lambda x: x[1]):
        print(f"  {payee}: ${-amount:,.2f}")
    print(f"  TOTAL: ${-total_bills:,.2f}")
    print()
    
    # Bank Fees
    bank_fees = categories['bank_fees']
    total_fees = sum(tx['amount'] for tx in bank_fees)
    print(f"BANK FEES (deductible)")
    print("-" * 50)
    for tx in bank_fees:
        print(f"  {tx['date'].strftime('%Y-%m-%d')}: {tx['description']}: ${-tx['amount']:,.2f}")
    print(f"  TOTAL: ${-total_fees:,.2f}")
    print()
    
    # DDA Deposits (other income?)
    dda_deposits = categories['dda_deposits']
    total_dda = sum(tx['amount'] for tx in dda_deposits)
    print(f"OTHER DEPOSITS (DDA Regular)")
    print("-" * 50)
    for tx in sorted(dda_deposits, key=lambda x: x['date']):
        print(f"  {tx['date'].strftime('%Y-%m-%d')}: ${tx['amount']:,.2f}")
    print(f"  TOTAL: ${total_dda:,.2f}")
    print()
    
    # Wire Transfers
    wires = categories['wire_transfers']
    print(f"WIRE TRANSFERS")
    print("-" * 50)
    for tx in wires:
        print(f"  {tx['date'].strftime('%Y-%m-%d')}: ${tx['amount']:,.2f} - {tx['description'][:60]}...")
    print()
    
    # Venmo
    venmo = categories['venmo']
    total_venmo = sum(tx['amount'] for tx in venmo)
    print(f"VENMO TRANSACTIONS")
    print("-" * 50)
    for tx in venmo:
        print(f"  {tx['date'].strftime('%Y-%m-%d')}: ${tx['amount']:,.2f}")
    print()
    
    # Summary for Schedule C
    print("=" * 70)
    print("SUMMARY FOR SCHEDULE C")
    print("=" * 70)
    print()
    print("INCOME:")
    print(f"  Gross Sales (from Square):     $26,416.25")
    print(f"  Less: Returns & Discounts:     ($683.37)")
    print(f"  Net Sales:                     $25,732.88")
    print()
    print("EXPENSES:")
    print(f"  Square Processing Fees:        $1,074.50")
    print(f"  Bank Fees:                     ${-total_fees:,.2f}")
    print(f"  Chase CC Payments:             ${-total_cc:,.2f} (verify actual expenses)")
    print()
    print("QUESTIONS TO RESOLVE:")
    print("-" * 50)
    print("1. Bill payments to Phillip, Nicholas, Danielle, Molly:")
    print("   - Are these wages (W-2)? Contract labor (1099-NEC)?")
    print("   - Or owner draws (not deductible)?")
    print()
    print("2. DDA Regular Deposits (${:,.2f}):".format(total_dda))
    print("   - What is the source of this income?")
    print("   - Is it business-related?")
    print()
    print("3. Wire transfer ($1,350 credit + check for $1,350):")
    print("   - 'Truck payback' - personal or business?")
    print()
    
    # Write categorized data
    output_path = Path(__import__("os").environ.get(
        "BANK_CATEGORIZED_CSV",
        str(__import__("pathlib").Path(__file__).resolve().parent.parent.parent / "samples" / "out" / "bank-categorized-sample.csv"),
    ))
    with open(output_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Date', 'Description', 'Amount', 'Category'])
        for cat, txs in sorted(categories.items()):
            for tx in sorted(txs, key=lambda x: x['date']):
                writer.writerow([
                    tx['date'].strftime('%Y-%m-%d'),
                    tx['description'],
                    f"${tx['amount']:,.2f}",
                    cat
                ])
    print(f"\nCategorized transactions written to: {output_path}")

if __name__ == '__main__':
    main()
