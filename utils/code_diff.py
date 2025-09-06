import difflib

def show_code_diff(original: str, modified: str, title: str = "Code Changes"):
    """
    Display a unified diff between original and modified code.

    Args:
        original: Original code string
        modified: Modified code string
        title: Title for the diff output
    """
    diff = difflib.unified_diff(
        original.splitlines(keepends=True),
        modified.splitlines(keepends=True),
        fromfile="original",
        tofile="modified",
        lineterm=""
    )
    print(f"\n📝 {title}")
    print("-" * 40)
    for line in diff:
        print(line.rstrip())
    print("-" * 40)