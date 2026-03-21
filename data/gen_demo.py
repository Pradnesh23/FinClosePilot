import csv, random
from datetime import date, timedelta

random.seed(42)
rows = []
start = date(2025, 10, 1)

# 1. BENFORD VIOLATION - XYZ Supplies - 47 txns skewed to 7,8,9
benford_amounts = [78500,89000,97000,75200,82300,93100,87500,76800,91000,84500,
                   77300,88200,96500,79100,83700,92400,86000,75800,80900,94000,
                   78100,87000,73500,81200,90500,76300,85000,92000,79800,88500,
                   74200,83000,91500,77800,86200,93500,80100,75500,89500,72000,
                   84000,90000,78900,87200,95000,76100,82000]
for i,amt in enumerate(benford_amounts):
    d = start + timedelta(days=i % 90)
    rows.append([f'TXN-{1000+i}',d,'XYZ Supplies Pvt Ltd','27AABCX1234D1ZS',
                 f'INV-XYZ-{500+i}',amt,'DEBIT','Procurement Services','5100','9965',18,0,round(amt*0.09,2),round(amt*0.09,2),
                 'ERP',round(amt*1.2),'CORP','REGULAR',''])

# 2. DUPLICATE PAYMENT - INV-2025-445
rows.append(['TXN-2000',date(2025,12,12),'Sharma Enterprises','29AABCS5678E2ZT','INV-2025-445',87500,'DEBIT','Office Supplies','5200','9990',18,0,7875,7875,'ERP',90000,'CORP','REGULAR',''])
rows.append(['TXN-2001',date(2025,12,14),'Sharma Enterprises','29AABCS5678E2ZT','INV-2025-445',87500,'DEBIT','Office Supplies','5200','9990',18,0,7875,7875,'ERP',90000,'CORP','REGULAR',''])

# 3. ITC HARD BLOCK - Grand Hyatt Section 17(5)(b)(i)
rows.append(['TXN-2100',date(2025,12,15),'Grand Hyatt Events','19AABCG7890H1ZK','INV-GHE-001',185000,'DEBIT','Corporate Hospitality & Entertainment Services','6100','9963',18,0,16650,16650,'ERP',200000,'CORP','VENDOR',''])

# 4. TIMING DIFFERENCES Dec 31
rows.append(['TXN-2200',date(2025,12,31),'Tata Consultancy Services','27AAACT2727Q1ZX','INV-TCS-Q3',450000,'DEBIT','IT Consulting Services','5300','9983',18,0,40500,40500,'ERP',460000,'TECH','SERVICE','2026-01-03'])
rows.append(['TXN-2201',date(2025,12,31),'Infosys Ltd','29AAACI1681G1ZK','INV-INFY-Q3',230000,'DEBIT','Software Development','5300','9983',18,0,20700,20700,'ERP',240000,'TECH','SERVICE','2026-01-02'])
rows.append(['TXN-2202',date(2025,12,31),'Wipro Ltd','29AAACW4313F1ZZ','INV-WIP-Q3',115000,'DEBIT','Data Analytics','5300','9983',18,0,10350,10350,'ERP',120000,'TECH','SERVICE','2026-01-04'])

# 5. ITC MISMATCH - Rule 36(4)
rows.append(['TXN-2300',date(2025,11,15),'Tech Services Ltd','06AABCT9012F3ZU','INV-TSL-001',280000,'DEBIT','Technology Services','5000','9983',18,0,25200,25200,'ERP',290000,'TECH','SERVICE',''])

# 6. BUDGET VARIANCE - Travel 340% over
rows.append(['TXN-2400',date(2025,10,20),'International Travel Co','29AABCI7890J2ZM','INV-ITC-001',1847000,'DEBIT','International roadshow customer conference Mumbai travel conveyance','6200','9964',18,0,166230,166230,'ERP',420000,'CORP','SERVICE',''])

# 7. ROUND NUMBER CLUSTER
for i in range(8):
    amt = 500000 if i%2==0 else 1000000
    d = start + timedelta(days=15*i)
    rows.append([f'TXN-{2500+i}',d,f'Generic Trading Co {i+1}',f'27AABCG{i:04d}X1ZY',f'INV-RND-{i+1}',amt,'DEBIT','Miscellaneous Services','5900','9999',18,0,round(amt*0.09),round(amt*0.09),'ERP',amt,'CORP','REGULAR',''])

# 8. R&D TAX OPPORTUNITY - Section 35
rows.append(['TXN-2600',date(2025,11,1),'InnovateTech Labs','29AABCI1111A1ZL','INV-ITL-001',1250000,'DEBIT','Research & Development Product Innovation Lab','5400','9983',18,0,112500,112500,'ERP',1300000,'TECH','MSME',''])

# 9. MSME OVERDUE - Section 43B
msme = [('QuickParts MSME','24AABCQ3456K1ZN',75000,'INV-QP-001'),
        ('SmallBiz Supplies','27AABCS9999M2ZT',85000,'INV-SB-001'),
        ('LocalVendor MSME','29AABCL2222N3ZU',180000,'INV-LV-001')]
for i,(vn,vg,amt,inv) in enumerate(msme):
    d = start + timedelta(days=i*5)
    rows.append([f'TXN-{2700+i}',d,vn,vg,inv,amt,'DEBIT','Office Supplies','5200','9990',18,0,round(amt*0.09),round(amt*0.09),'ERP',amt,'CORP','MSME',''])

# FILL to 500 with regular vendors
vendors = [
    ('Reliance Industries','27AAACR4849E1ZU'),('Hindustan Unilever','27AAACH4714N1ZU'),
    ('HDFC Bank Charges','27AAACH2702H1ZF'),('ICICI Bank Services','27AAACI0263C1ZN'),
    ('Axis Bank Services','27AAACA1234B1ZL'),('Mahindra & Mahindra','27AAACM3025F1ZT'),
    ('L&T Engineering','27AABCL0001A1ZX'),('Bajaj Auto Ltd','27AAACB3834M1ZU'),
    ('Sun Pharma','27AAACS4699J1ZY'),('Asian Paints','27AAACA8945P1ZM'),
]
rid = 3000
while len(rows) < 500:
    v = vendors[rid % len(vendors)]
    d = start + timedelta(days=rid % 90)
    amt = random.randint(5000, 300000)
    rows.append([f'TXN-{rid}',d,v[0],v[1],f'INV-{rid}-A',amt,'DEBIT','Business Services','5100','9983',18,0,round(amt*0.09),round(amt*0.09),'ERP',int(amt*1.1),'CORP','REGULAR',''])
    rid += 1

header = ['transaction_id','date','vendor_name','vendor_gstin','invoice_no','amount','type','narration','gl_account','hsn_code','gst_rate','igst','cgst','sgst','source','budget_amount','cost_centre','vendor_type','payment_date']

with open('data/demo/demo_transactions.csv','w',newline='',encoding='utf-8') as f:
    w = csv.writer(f)
    w.writerow(header)
    w.writerows(rows)

print(f'Written {len(rows)} transactions')
