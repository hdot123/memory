#!/usr/bin/env python3
"""Fix tests to pass content parameter to _truth_basis_errors_for"""

import re
from pathlib import Path

def fix_test_file(test_file: Path):
    """Fix a single test file"""
    content = test_file.read_text()
    lines = content.split('\n')
    new_lines = []
    
    i = 0
    while i < len(lines):
        line = lines[i]
        
        # Check if this line has _truth_basis_errors_for(path) call
        if '_truth_basis_errors_for(path)' in line:
            # Look backwards to find the write_text call
            j = i - 1
            while j >= 0:
                if 'path.write_text(' in lines[j]:
                    break
                j -= 1
            
            if j >= 0:
                # Find the end of write_text call
                k = j
                paren_count = 0
                found_start = False
                while k < len(lines):
                    for ch in lines[k]:
                        if ch == '(':
                            paren_count += 1
                            found_start = True
                        elif ch == ')':
                            paren_count -= 1
                    
                    if found_start and paren_count == 0:
                        break
                    k += 1
                
                # Extract the text content from write_text
                write_text_block = '\n'.join(lines[j:k+1])
                # Find the text argument
                match = re.search(r'write_text\(\s*(?:f?["\'].*?["\']|["\'].*?["\'])', write_text_block, re.DOTALL)
                if match:
                    text_var = match.group(0).split('write_text(')[1].split(',')[0]
                    # Insert content = path.read_text() before the errors call
                    indent = len(line) - len(line.lstrip())
                    new_lines.append(' ' * indent + f'content = path.read_text()')
                    # Replace the call
                    new_line = line.replace('_truth_basis_errors_for(path)', '_truth_basis_errors_for(path, content)')
                    new_lines.append(new_line)
                else:
                    new_lines.append(line)
            else:
                new_lines.append(line)
        else:
            new_lines.append(line)
        
        i += 1
    
    test_file.write_text('\n'.join(new_lines))
    print(f"Fixed {test_file}")

# Fix all test files
test_files = [
    Path('tests/test_gateway_truth_basis_coverage.py'),
    Path('tests/test_business_policy_schema.py'),
    Path('tests/test_init_completeness.py'),
]

for test_file in test_files:
    if test_file.exists():
        fix_test_file(test_file)

print("All test files fixed!")
