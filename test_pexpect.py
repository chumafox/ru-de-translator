import pexpect
import sys
import time


def test():
    child = pexpect.spawn(
        "uv run python app.py",
        cwd="/Users/jenyanovak/Projects/active/ru-de-translator/ru_de_translator",
        encoding="utf-8",
    )
    child.logfile = sys.stdout

    print("Waiting for startup...")
    time.sleep(2)

    # Open chat
    child.send("\x03")  # Ctrl+C
    time.sleep(1)

    # Type message
    child.send("Hallo, wie geht es dir?\r")

    # Wait for response
    print("\nWaiting for Qwen to reply...")
    # Because TUI redraws, we just wait for something indicating completion
    # We will just wait 30 seconds
    time.sleep(30)

    child.send("\x11")  # Ctrl+Q to quit
    time.sleep(1)
    print("Done")


if __name__ == "__main__":
    test()
