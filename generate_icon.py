import struct
import zlib
from io import BytesIO
from pathlib import Path


def _create_png_data(width: int, height: int) -> bytes:
    """Create a PNG icon with a modern downloader-themed design."""
    from PIL import Image, ImageDraw

    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    cx, cy = width // 2, height // 2
    r = min(width, height) // 2 - 4

    outer_r = r
    inner_r = int(r * 0.82)

    for y in range(height):
        for x in range(width):
            dx, dy = x - cx, y - cy
            dist = (dx * dx + dy * dy) ** 0.5

            if dist > outer_r:
                continue

            if dist <= inner_r:
                if dist > inner_r * 0.7:
                    frac = (dist - inner_r * 0.7) / (inner_r * 0.3)
                    r_val = int(42 + (225 - 42) * frac)
                    g_val = int(95 + (130 - 95) * frac)
                    b_val = int(142 + (40 - 142) * frac)
                else:
                    r_val, g_val, b_val = 42, 95, 142

                a_val = 255
                img.putpixel((x, y), (r_val, g_val, b_val, a_val))
                continue

            edge = outer_r - dist
            soft = min(edge, 2.0) / 2.0

            frac = (dist - inner_r) / (outer_r - inner_r)
            r_val = int(225 + (42 - 225) * frac)
            g_val = int(130 + (95 - 130) * frac)
            b_val = int(40 + (142 - 40) * frac)

            a_val = int(255 * soft)
            if a_val > 0:
                img.putpixel((x, y), (r_val, g_val, b_val, int(255 * soft)))

    s = width // 2

    def draw_arrow(d: ImageDraw, c_x: int, c_y: int, sz: int) -> None:
        arrow_color = (255, 255, 255, 240)
        shaft_w = max(sz // 6, 2)
        head_w = sz // 2
        head_h = sz // 3

        left = (c_x - shaft_w // 2, c_y - sz // 4)
        right = (c_x + shaft_w // 2, c_y + sz // 4)
        d.rectangle([left[0], left[1], right[0], right[1]], fill=arrow_color)

        d.polygon([
            (c_x, c_y + sz // 4 + head_h),
            (c_x - head_w, c_y),
            (c_x + head_w, c_y),
        ], fill=arrow_color)

    def draw_play(d: ImageDraw, c_x: int, c_y: int, sz: int) -> None:
        play_color = (255, 255, 255, 230)
        size = sz * 0.35
        d.polygon([
            (c_x - size * 0.4, c_y - size * 0.55),
            (c_x - size * 0.4, c_y + size * 0.55),
            (c_x + size * 0.5, c_y),
        ], fill=play_color)

    draw_arrow(draw, cx - s // 3, cy, s)
    draw_play(draw, cx + s // 3, cy, s)

    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _png_to_ico(sizes: list[int]) -> bytes:
    """Convert PNG(s) to ICO format."""
    ico_dir = struct.pack("<HHH", 0, 1, len(sizes))

    png_chunks = []
    for s in sizes:
        png = _create_png_data(s, s)
        png_chunks.append(png)

    offset = 6 + 16 * len(sizes)
    for s, png in zip(sizes, png_chunks):
        bpp = 32
        ico_s = 0 if s == 256 else s
        ico_dir += struct.pack("<BBBBHHII", ico_s, ico_s, 0, 0, 1, bpp, len(png), offset)
        offset += len(png)

    return ico_dir + b"".join(png_chunks)


def generate_icon(output_path: str = "bot_icon.ico") -> str:
    path = Path(output_path)
    if not path.exists():
        sizes = [256, 128, 64, 48, 32, 24, 16]
        ico_data = _png_to_ico(sizes)
        path.write_bytes(ico_data)
        print(f"Icon generated: {path.resolve()}")
    else:
        print(f"Icon already exists: {path.resolve()}")
    return str(path)


if __name__ == "__main__":
    generate_icon()
