from rich.markup import render

try:
    markup = '[@click="speak_text(\'das ist gut\')"][underline bright_yellow]"das ist gut"[/][/]'
    render(markup)
    print("Success 1")
except Exception as e:
    print(f"Error 1: {e}")

try:
    markup = '[@click="speak_text(\'Ich bin ein gutes Buch gelesen.\')"][underline bright_yellow]"Ich bin ein gutes Buch gelesen."[/][/]'
    render(markup)
    print("Success 2")
except Exception as e:
    print(f"Error 2: {e}")
