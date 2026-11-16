# -*- coding: utf-8 -*-
"""替换 MFA 的 MFAAvalonia.Core.dll 内嵌 logo.ico（原地，大小不变）。

用法：
    python tools/patch_core_logo.py <MFAAvalonia.Core.dll> <maa-icon.png>
"""
import io
import struct
import sys
from pathlib import Path

from PIL import Image


def make_icon_ico(png_path: Path, max_size: int) -> bytes:
    """把 png 转成单尺寸 256 的 ico（调色板压缩），控制体积。"""
    src = Image.open(png_path).convert("RGBA")
    base = src.resize((256, 256), Image.LANCZOS)
    p = base.quantize(colors=256, method=Image.Quantize.FASTOCTREE)
    buf = io.BytesIO()
    p.save(buf, format="PNG", optimize=True)
    png = buf.getvalue()

    ico = bytearray()
    ico += b"\x00\x00\x01\x00\x01\x00"
    ico += bytes([0, 0, 0, 0])
    ico += b"\x00\x00\x01\x00"
    ico += len(png).to_bytes(4, "little")
    ico += (22).to_bytes(4, "little")
    ico += png
    if len(ico) > max_size:
        raise ValueError(f"生成的 ico {len(ico)} 字节超过上限 {max_size}")
    return bytes(ico)


def find_logo_ico(data: bytes):
    """定位 dll 内嵌 logo.ico 的偏移与总大小。"""
    name = data.find(b"logo.ico")
    if name < 0:
        return None
    ico_off = data.find(b"\x00\x00\x01\x00", name)
    if ico_off < 0:
        return None
    if ico_off + 6 > len(data):
        return None
    count = struct.unpack_from("<H", data, ico_off + 4)[0]
    if not 1 <= count <= 20:
        return None
    total = 6 + 16 * count
    for k in range(count):
        entry = ico_off + 6 + 16 * k
        if entry + 16 > len(data):
            return None
        size = struct.unpack_from("<I", data, entry + 8)[0]
        offset = struct.unpack_from("<I", data, entry + 12)[0]
        total = max(total, offset + size)
    return ico_off, total


def patch(dll_path: Path, png_path: Path) -> bool:
    data = bytearray(dll_path.read_bytes())
    found = find_logo_ico(data)
    if not found:
        print(f"[提示] {dll_path.name} 里没找到内嵌 logo.ico，跳过")
        return False
    off, size = found
    ico = make_icon_ico(png_path, size)
    data[off:off + size] = ico + bytes(size - len(ico))
    dll_path.write_bytes(bytes(data))
    print(f"[提示] 已替换 {dll_path.name} 内嵌 logo（{len(ico)}/{size} 字节）")
    return True


def main():
    if len(sys.argv) < 3:
        print("用法: python tools/patch_core_logo.py <MFAAvalonia.Core.dll> <maa-icon.png>")
        sys.exit(1)
    dll = Path(sys.argv[1])
    png = Path(sys.argv[2])
    if not dll.exists():
        print(f"[提示] 找不到 {dll}，跳过")
        return
    patch(dll, png)


if __name__ == "__main__":
    main()
