"""Composite a user-provided transparent product cutout without AI repainting."""
import argparse
import json
from pathlib import Path
from PIL import Image, ImageOps


def compose(source, output, width=1600, height=1600, background=None):
    if type(width) is not int or type(height) is not int or not 128 <= width <= 4096 or not 128 <= height <= 4096 or width * height > 16_000_000:
        raise ValueError('Invalid canvas size')
    source, output = Path(source), Path(output)
    if output.exists() or output.suffix.lower() != '.png':
        raise ValueError('Choose a new PNG output path')
    with Image.open(source) as im:
        if getattr(im, 'n_frames', 1) != 1 or im.width * im.height > 20_000_000:
            raise ValueError('Unsupported source')
        im = ImageOps.exif_transpose(im).convert('RGBA')
        alpha = im.getchannel('A')
        if alpha.getextrema()[0] != 0 or alpha.getextrema()[1] == 0:
            raise ValueError('Transparent product cutout required; this tool does not remove backgrounds')
        product = im.crop(alpha.getbbox())
    if background:
        with Image.open(background) as bg:
            if getattr(bg, 'n_frames', 1) != 1 or bg.width * bg.height > 20_000_000:
                raise ValueError('Unsupported background')
            canvas = ImageOps.fit(ImageOps.exif_transpose(bg).convert('RGB'), (width, height)).convert('RGBA')
    else:
        canvas = Image.new('RGBA', (width, height), 'white')
    scale = min(width * .88 / product.width, height * .88 / product.height)
    size = (max(1, round(product.width * scale)), max(1, round(product.height * scale)))
    scaled = product.resize(size, Image.Resampling.LANCZOS)
    x, y = (width - size[0]) // 2, (height - size[1]) // 2
    canvas.alpha_composite(scaled, (x, y))
    with output.open('xb') as stream:
        canvas.convert('RGB').save(stream, 'PNG')
    return {'output':str(output.resolve()), 'size':[width,height], 'product_box':[x,y,*size],
            'method':'original cutout compositing, no AI repaint', 'resampled':scale != 1,
            'white_background':not bool(background), 'platform_approved':False}


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',required=True);p.add_argument('--output',required=True)
    p.add_argument('--width',type=int,default=1600);p.add_argument('--height',type=int,default=1600)
    p.add_argument('--background')
    a=p.parse_args()
    try:print(json.dumps(compose(a.source,a.output,a.width,a.height,a.background),ensure_ascii=True))
    except (ValueError,OSError) as e:p.exit(1,str(e)+'\n')
