import os
import re

def fix_all_html():
    dirs = [
        r"c:\Users\HP\Desktop\project_bitumen sales\bitumen sales dashboard",
        r"c:\Users\HP\Desktop\project_bitumen sales\bitumen sales dashboard\command_intel"
    ]
    
    for d in dirs:
        for f in os.listdir(d):
            if f.endswith(".py"):
                path = os.path.join(d, f)
                with open(path, "r", encoding="utf-8") as file:
                    content = file.read()
                
                # We will aggressively strip leading spaces for any line inside the file that looks like it's inside a triple quote st.markdown block
                # Actually, an easier way is to just replace all `^[ \t]+` with `` for lines inside `st.markdown("""...""")`
                # Let's just do a regex replace that strips all leading whitespace on any line that contains an HTML tag, or is completely inside a markdown block.
                # Actually, the previous regex was: re.sub(r'\n[ \t]+(<(?:div|span|h[1-6]|p|b|i|br|strong|/div|/span|/h[1-6]|/p|/b|/i|/br|/strong)[^>]*>)', r'\n\1', content)
                # It worked really well! But maybe some text nodes were still indented?
                
                # Let's strip spaces before lines with just `{` or text inside those loops:
                # e.g., `<div style...>\n                     {amount}\n                 </div>`
                # Let's just strip leading spaces on ALL lines starting with 8+ spaces that do NOT contain Python keywords, but this is dangerous.
                
                # A safer way to fix Streamlit markdown:
                # Find all `st.markdown` calls that use triple quotes.
                
                pattern = r'(st\.markdown\([f]?(?:\"\"\"|\'\'\'))(.*?)((\"\"\"|\'\'\')\s*,\s*unsafe_allow_html=True\))'
                def replacer(match):
                    start = match.group(1)
                    inner = match.group(2)
                    end = match.group(3)
                    
                    # Remove all leading spaces on all lines in `inner`
                    unindented = "\n".join([line.lstrip() for line in inner.split("\n")])
                    return start + unindented + end
                
                new_content = re.sub(pattern, replacer, content, flags=re.DOTALL)
                
                if new_content != content:
                    with open(path, "w", encoding="utf-8") as file:
                        file.write(new_content)
                    print(f"Aggressively fixed {f}")

fix_all_html()
