import csv, random
from datetime import date, timedelta

random.seed(42)
rows = []
start = date(2025, 10, 1)

# Generate GST Portal Data
gst_rows = []
gst_header = ['gstin_supplier','trade_name','invoice_no','invoice_date','invoice_value','rate','taxable_value','igst','cgst','sgst','filing_status']

# 1. Matches for most regular transactions
for i in range(3000, 3100):
    amt = random.randint(5000, 300000)
    gst_rows.append(['27AAACR4849E1ZU','Reliance Industries',f'INV-{i}-A',(start + timedelta(days=i%90)).strftime('%Y-%m-%d'),
                     amt,18,amt,0,round(amt*0.09),round(amt*0.09),'FILED'])

# 2. MATCH - XYZ Supplies (Benford violation) - supplier filed correctly
benford_amounts = [78500,89000,97000,75200,82300,93100,87500,76800,91000,84500][:10] # type: ignore
for i,amt in enumerate(benford_amounts):
    gst_rows.append(['27AABCX1234D1ZS','XYZ Supplies Pvt Ltd',f'INV-XYZ-{500+i}',(start + timedelta(days=i%90)).strftime('%Y-%m-%d'),
                     amt,18,amt,0,round(amt*0.09,2),round(amt*0.09,2),'FILED'])

# 3. RULE 36(4) VIOLATION - Tech Services didn't file GSTR-1
# We purposely OMIT Tech Services Ltd details from here to trigger the Rule 36(4) mismatch since Books>GSTR2A

with open('data/demo/demo_gst_portal.csv','w',newline='',encoding='utf-8') as f:
    w = csv.writer(f)
    w.writerow(gst_header)
    w.writerows(gst_rows)


# Generate Bank Statement
bank_rows = []
bank_header = ['date','description','reference_no','debit','credit','balance']
bal = 50000000

for i in range(3000, 3050):
    amt = random.randint(5000, 300000)
    bal -= amt
    bank_rows.append([(start + timedelta(days=i%90)).strftime('%Y-%m-%d'),f'NEFT TO RELIANCE - INV-{i}-A',f'REF{i}998877',amt,0,bal])

# Bank Reconciliation Break - Payment cleared in bank but not in books
bank_rows.append(['2025-12-30','RTGS TO VENDOR UNKNOWN','RTGS999888777',450000,0,bal-450000])

with open('data/demo/demo_bank_statement.csv','w',newline='',encoding='utf-8') as f:
    w = csv.writer(f)
    w.writerow(bank_header)
    w.writerows(bank_rows)

print("Generated GST and Bank statements.")
