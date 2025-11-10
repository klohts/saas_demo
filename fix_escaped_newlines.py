import re

f = "main.py"
code = open(f).read()

# Remove literal backslash+n that was written into the file
code = code.replace("\\n", "")

# Also remove any trailing backslash at end of lines (dangerous in Python)
code = re.sub(r"\\\\[ \t]*$", "", code, flags=re.MULTILINE)

# Save the cleaned file
open(f, "w").write(code)
print("✅ Removed invalid \\n sequences and cleaned backslashes")
