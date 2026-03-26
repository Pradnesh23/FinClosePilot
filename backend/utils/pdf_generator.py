"""
PDF Generation Utility for FinClosePilot.
Generates professional audit reports and financial summaries using fpdf2.
"""

import logging
from fpdf import FPDF
from datetime import datetime

logger = logging.getLogger(__name__)

class AuditPDF(FPDF):
    def header(self):
        # Logo
        # self.image('logo.png', 10, 8, 33)
        self.set_font('helvetica', 'B', 15)
        self.cell(0, 10, 'FinClosePilot — Confidential Audit Report', border=False, align='C')
        self.ln(10)
        self.set_font('helvetica', 'I', 8)
        self.cell(0, 10, f'Generated on: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}', border=False, align='R')
        self.ln(15)

    def footer(self):
        self.set_y(-15)
        self.set_font('helvetica', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}/{{nb}}', align='C')

def generate_audit_report_pdf(package: dict, output_path: str) -> str:
    """
    Generates a comprehensive PDF from an audit package.
    """
    pdf = AuditPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    # 1. Executive Summary
    pdf.set_font('helvetica', 'B', 14)
    pdf.cell(0, 10, '1. Executive Summary', ln=True)
    pdf.set_font('helvetica', '', 10)
    summary = package.get("run_summary", {})
    pdf.multi_cell(0, 7, (
        f"Run ID: {package.get('run_id')}\n"
        f"Period: {summary.get('period', 'N/A')}\n"
        f"Status: {summary.get('status', 'N/A')}\n"
        f"Total Records Processed: {summary.get('total_records', 0)}\n"
        f"Reconciliation Matches: {summary.get('matched_records', 0)}\n"
        f"Anomalies Detected: {package.get('anomalies_count', 0)}\n"
        f"Guardrail Violations: {package.get('guardrail_fires_count', 0)}\n"
    ))
    pdf.ln(5)

    # 2. Reconciliation Breaks
    pdf.set_font('helvetica', 'B', 14)
    pdf.cell(0, 10, '2. Reconciliation Discrepancies', ln=True)
    breaks = package.get("recon_breaks", [])
    if not breaks:
        pdf.set_font('helvetica', 'I', 10)
        pdf.cell(0, 10, 'No reconciliation breaks found.', ln=True)
    else:
        pdf.set_font('helvetica', 'B', 9)
        # Headers
        pdf.cell(30, 8, 'Type', 1)
        pdf.cell(60, 8, 'Vendor', 1)
        pdf.cell(30, 8, 'Amount', 1)
        pdf.cell(70, 8, 'Root Cause', 1)
        pdf.ln()
        pdf.set_font('helvetica', '', 8)
        for b in breaks[:20]: # Limit to top 20 for PDF
            pdf.cell(30, 7, str(b.get('recon_type', 'N/A')), 1)
            pdf.cell(60, 7, str(b.get('vendor_name', 'Unknown'))[:35], 1)
            pdf.cell(30, 7, f"{float(b.get('difference', 0)):,.2f}", 1)
            pdf.cell(70, 7, str(b.get('root_cause', 'N/A'))[:45], 1)
            pdf.ln()
    pdf.ln(10)

    # 3. Anomaly Findings
    pdf.set_font('helvetica', 'B', 14)
    pdf.cell(0, 10, '3. Forensic Anomaly Detection', ln=True)
    anomalies = package.get("anomalies", [])
    for a in anomalies:
        pdf.set_font('helvetica', 'B', 10)
        pdf.cell(0, 8, f"{a.get('anomaly_type')} - {a.get('severity')}", ln=True)
        pdf.set_font('helvetica', '', 9)
        pdf.multi_cell(0, 6, f"Reasoning: {a.get('reasoning')}")
        pdf.ln(2)
    pdf.ln(5)

    # 4. Certification
    pdf.set_font('helvetica', 'B', 14)
    pdf.cell(0, 10, '4. AI Certification & Disclaimer', ln=True)
    cert = package.get("certification", {})
    pdf.set_font('helvetica', 'I', 9)
    pdf.multi_cell(0, 6, (
        f"Prepared By: {cert.get('prepared_by')}\n"
        f"Validation Engine: {cert.get('model')}\n\n"
        f"DISCLAIMER: {cert.get('disclaimer')}"
    ))

    pdf.output(output_path)
    return output_path
