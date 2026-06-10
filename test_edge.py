from rich.markup import render

try:
    markup = r'[@click="speak_text(\'Das ist so \\\'gut\\\'!\')"][underline bright_yellow]"Das ist so \'gut\'!"[/][/]'
    render(markup)
    print("Success 1")
except Exception as e:
    print(f"Error 1: {e}")

try:
    markup = "[@click=\"speak_text('Das ist so \\'gut\\'!')\"][underline bright_yellow]\"Das ist so 'gut'!\"[/][/]"
    render(markup)
    print("Success 2")
except Exception as e:
    print(f"Error 2: {e}")
