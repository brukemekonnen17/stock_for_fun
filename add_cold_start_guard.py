#!/usr/bin/env python3
"""
Script to add cold-start guard to Cell 6 of the notebook.
Run this to insert the guard after df_clean assignment.
"""

import json
from pathlib import Path

notebook_path = Path("Analyst_Trade_Study.ipynb")

with open(notebook_path, 'r') as f:
    notebook = json.load(f)

# Find Cell 6 (data loading cell)
for i, cell in enumerate(notebook['cells']):
    source = ''.join(cell.get('source', []))
    if 'df_clean = run_hygiene_checks' in source:
        # Add cold-start guard after df_clean assignment
        lines = source.split('\n')
        new_lines = []
        guard_added = False
        
        for j, line in enumerate(lines):
            new_lines.append(line)
            if 'df_clean = run_hygiene_checks' in line and not guard_added:
                # Add guard after this line
                new_lines.append('')
                new_lines.append('    # --- Cold-start guard (fail-fast) ---')
                new_lines.append('    MIN_BARS = 200')
                new_lines.append('    if df_clean is None or df_clean.empty or len(df_clean) < MIN_BARS:')
                new_lines.append('        raise RuntimeError(')
                new_lines.append('            f"Cold-start / insufficient history: got {0 if df_clean is None or df_clean.empty else len(df_clean)} bars, need ≥ {MIN_BARS}."')
                new_lines.append('        )')
                new_lines.append('    required_cols = {"date", "open", "high", "low", "close", "adj_close", "volume"}')
                new_lines.append('    missing = required_cols - set(df_clean.columns)')
                new_lines.append('    if missing:')
                new_lines.append('        raise RuntimeError(f"Missing required columns: {sorted(missing)}")')
                new_lines.append('    print(f"✅ Cold-start guard passed: {len(df_clean)} bars (≥{MIN_BARS}), all required columns present")')
                guard_added = True
        
        notebook['cells'][i]['source'] = new_lines
        print(f"✅ Cold-start guard added to cell {i}")
        break

# Save notebook
with open(notebook_path, 'w') as f:
    json.dump(notebook, f, indent=1)

print("✅ Notebook updated")

