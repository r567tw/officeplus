import sys

if len(sys.argv) != 2:
    print(f"用法：python {sys.argv[0]} <檔案>")
    sys.exit(1)

filename = sys.argv[1]

try:
    with open(filename, "r", encoding="utf-8") as f:
        text = f.read()

    chars = len(text.replace(" ", "").replace("\n", ""))
    lines = len(text.splitlines())
    words = len(text.split())

    print(f"字數：{chars}")
    print(f"單字數：{words}")
    print(f"行數：{lines}")

except FileNotFoundError:
    print(f"找不到檔案：{filename}")
