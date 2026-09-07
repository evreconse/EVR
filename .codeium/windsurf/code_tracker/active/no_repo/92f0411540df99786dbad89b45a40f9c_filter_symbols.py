Ý	"""
Filter existing symbols to exclude numeric prefixes
"""
import re

# Read existing symbols
with open("usdt_perpetual_symbols.py", "r") as f:
    content = f.read()

# Extract symbols list
match = re.search(r'SYMBOLS = \[(.*?)\]', content, re.DOTALL)
if match:
    symbols_str = match.group(1)
    symbols = [s.strip().strip('"').strip("'") for s in symbols_str.split(',') if s.strip()]
    
    print(f"Total symbols: {len(symbols)}")
    
    # Filter out symbols with numeric prefixes
    clean_symbols = [s for s in symbols if not s[0].isdigit()]
    
    print(f"After removing numeric prefixes: {len(clean_symbols)}")
    
    # Write new file
    with open("usdt_perpetual_symbols.py", "w") as f:
        f.write("# Auto-generated USDT Perpetual symbols from BingX (excluding TOP-20 and numeric prefixes)\n")
        f.write("SYMBOLS = [\n")
        for i, symbol in enumerate(clean_symbols):
            if i == len(clean_symbols) - 1:
                f.write(f'    "{symbol}"\n')
            else:
                f.write(f'    "{symbol}",\n')
        f.write("]\n")
    
    print(f"Saved {len(clean_symbols)} clean symbols")
    print()
    print("First 20 clean symbols:")
    for s in clean_symbols[:20]:
        print(f"  {s}")
Ý	*cascade082Mfile:///C:/Users/user/Documents/Default%20Project/EVRECONSE/filter_symbols.py