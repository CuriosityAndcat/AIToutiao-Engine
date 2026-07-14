"""独立后处理脚本：裁剪 AI 生成图片的水印区域
不修改任何引擎代码，仅处理已生成的图片文件。
用法：python scripts/crop_watermark.py <input_dir> <output_dir>
"""
import os
import sys
from PIL import Image

# 水印高度占图片约 8-10%，保守裁剪 10%（102px 对于 1024px 图）
CROP_BOTTOM_PCT = 0.10

def crop_bottom_watermark(input_path, output_path):
    img = Image.open(input_path)
    w, h = img.size
    new_h = int(h * (1 - CROP_BOTTOM_PCT))
    cropped = img.crop((0, 0, w, new_h))
    cropped.save(output_path)
    print(f"  {os.path.basename(input_path)}: {w}x{h} -> {w}x{new_h}")

if __name__ == "__main__":
    src_dir = sys.argv[1] if len(sys.argv) > 1 else "outputs"
    dst_dir = sys.argv[2] if len(sys.argv) > 2 else src_dir

    os.makedirs(dst_dir, exist_ok=True)
    for fn in sorted(os.listdir(src_dir)):
        if fn.lower().endswith(('.png', '.jpg', '.jpeg')):
            crop_bottom_watermark(
                os.path.join(src_dir, fn),
                os.path.join(dst_dir, fn)
            )
    print("Done.")
