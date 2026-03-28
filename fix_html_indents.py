import os
import re

directories = [
    r"c:\Users\HP\Desktop\project_bitumen sales\bitumen sales dashboard",
    r"c:\Users\HP\Desktop\project_bitumen sales\bitumen sales dashboard\command_intel"
]

def fix_file(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    # Find all occurrences of anything inside st.markdown(..., unsafe_allow_html=True)
    # Actually, a simpler approach is to use re.sub on lines that look like HTML tags but have leading spaces
    
    # Let's replace 4 or more spaces that are followed by a `<` character with just `<`
    # This will dedent any HTML tag that is indented.
    # What about text inside the HTML tags that is also indented?
    # e.g. "       Global Bitumen Price Prediction Engine"
    # We can just remove ALL indentation that is 4 or more spaces if it's inside a multi-line string.
    # But it's easier to just remove any line starting with spaces then `<` and also remove spaces at the beginning of any line that's purely text inside HTML.
    
    # An incredibly safe regex for Streamlit markdown html issues:
    # Just remove leading spaces on any line that has an HTML tag `<div`, `<span`, `<p`, `<h`, `</div`
    
    new_content = re.sub(r'\n[ \t]+(<(?:div|span|h[1-6]|p|b|i|br|strong|/div|/span|/h[1-6]|/p|/b|/i|/br|/strong)[^>]*>)', r'\n\1', content)
    
    if new_content != content:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(new_content)
        print(f"Fixed {filepath}")

for d in directories:
    for filename in os.listdir(d):
        if filename.endswith(".py"):
            fix_file(os.path.join(d, filename))

print("Done fixing HTML indents.")
