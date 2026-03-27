import os

files = [
    'backend/agents/model_router.py',
    'backend/agents/pipeline.py',
    'backend/agents/reports/tax_optimiser.py',
    'backend/api/routes.py',
    'backend/database/audit_logger.py',
    'backend/database/models.py',
    'backend/memory/letta_client.py',
    'requirements.txt'
]

with open('conflicts.log', 'w', encoding='utf-8') as out:
    for f in files:
        if not os.path.exists(f):
            continue
        with open(f, 'r', encoding='utf-8') as src:
            lines = src.readlines()
            
        out.write(f"\\n{'='*50}\\nFILE: {f}\\n{'='*50}\\n")
        
        in_conflict = False
        for i, line in enumerate(lines):
            if line.startswith('<<<<<<<'):
                in_conflict = True
                out.write(f"\\n--- CONFLICT START (line {i+1}) ---\\n")
            
            if in_conflict:
                out.write(line)
                
            if line.startswith('>>>>>>>'):
                in_conflict = False
                out.write("--- CONFLICT END ---\\n\\n")
