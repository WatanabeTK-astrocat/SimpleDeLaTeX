import argparse
import sys
from pathlib import Path
from typing import Optional

# ここに削除対象コマンドを書く（バックスラッシュは不要）
TARGET_COMMANDS = {
    "edit",
}

def read_balanced(text: str, start: int, open_ch: str, close_ch: str) -> Optional[tuple[str, int]]:
    """
    text[start] が open_ch であることを前提に、
    対応する close_ch までをネスト込みで読んで、
    中身と「次に読むべき位置」を返す。

    返り値:
        (content, next_index)
    失敗時:
        None
    """
    if start >= len(text) or text[start] != open_ch:
        return None

    depth = 0
    i = start
    buf = []

    while i < len(text):
        ch = text[i]

        if ch == open_ch:
            depth += 1
            if depth > 1:
                buf.append(ch)

        elif ch == close_ch:
            depth -= 1
            if depth == 0:
                return ("".join(buf), i + 1)
            elif depth < 0:
                return None
            else:
                buf.append(ch)

        else:
            buf.append(ch)

        i += 1

    # 閉じ括弧が見つからなかった
    return None


def read_command_name(text: str, start: int) -> Optional[tuple[str, int]]:
    """
    text[start] == '\\' を前提に、直後の英字列をコマンド名として読む。
    返り値: (command_name, next_index)
    失敗時: None
    """
    if start >= len(text) or text[start] != "\\":
        return None

    i = start + 1
    begin = i

    while i < len(text) and text[i].isalpha():
        i += 1

    if i == begin:
        return None

    return text[begin:i], i


def transform_text(text: str, target_commands: set[str]) -> str:
    """
    指定コマンドだけを展開して、コマンド名を除去した文字列を返す。
    """
    out = []
    i = 0
    n = len(text)

    while i < n:
        if text[i] != "\\":
            out.append(text[i])
            i += 1
            continue

        cmd_info = read_command_name(text, i)
        if cmd_info is None:
            # バックスラッシュ単体など
            out.append(text[i])
            i += 1
            continue

        cmd_name, j = cmd_info

        if cmd_name not in target_commands:
            # 対象外コマンドはそのまま残す
            out.append(text[i:j])
            i = j
            continue

        # 任意引数 [...]
        optional_arg = None
        if j < n and text[j] == "[":
            result = read_balanced(text, j, "[", "]")
            if result is None:
                # 壊れた構文なら元のまま出す
                out.append(text[i])
                i += 1
                continue
            optional_arg, j = result

        # 必須引数 {...}
        if j < n and text[j] == "{":
            result = read_balanced(text, j, "{", "}")
            if result is None:
                out.append(text[i])
                i += 1
                continue
            required_arg, j = result
        else:
            # 想定形でなければ元のまま残す
            out.append(text[i])
            i += 1
            continue

        # 置換
        if optional_arg is not None:
            out.append(optional_arg)
            out.append(" ")
            out.append(required_arg)
        else:
            out.append(required_arg)

        i = j

    return "".join(out)


def make_output_path(input_path: Path) -> Path:
    return input_path.with_name(f"{input_path.stem}-copy{input_path.suffix}")

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Remove selected LaTeX commands while keeping their argument contents."
    )
    parser.add_argument(
        "input",
        help="Input .tex file",
    )
    return parser.parse_args()

def main():
    args = parse_args()
    input_path = Path(args.input)

    if not input_path.exists():
        print(f"Error: file not found: {input_path}", file=sys.stderr)
        return 1

    try:
        text = input_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        print(f"Error: could not decode as UTF-8: {input_path}", file=sys.stderr)
        return 1
    except OSError as e:
        print(f"Error: failed to read file: {e}", file=sys.stderr)
        return 1

    converted = transform_text(text, TARGET_COMMANDS)
    output_path = make_output_path(input_path)

    try:
        output_path.write_text(converted, encoding="utf-8")
    except OSError as e:
        print(f"Error: failed to write file: {e}", file=sys.stderr)
        return 1

    print(f"Written: {output_path}")
    return 0


if __name__ == "__main__":
    main()
