import ast

try:
    ast.parse("speak_text('\\[')")
    print("Success 1")
except Exception as e:
    print(f"Error 1: {e}")

try:
    ast.parse("speak_text('\[')")
    print("Success 2")
except Exception as e:
    print(f"Error 2: {e}")
