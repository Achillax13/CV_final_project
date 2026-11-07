"""Build the slide-only English final-project presentation from recorded results."""
import csv
from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.util import Inches, Pt


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'output/presentation/group6_patchcore_final_presentation.pptx'
SUMMARY = ROOT / 'results/summary_windows/mean_std.csv'
NAVY = RGBColor(23, 50, 77)
BLUE = RGBColor(37, 118, 168)
INK = RGBColor(31, 42, 54)
MUTED = RGBColor(85, 100, 112)
PALE = RGBColor(237, 244, 248)
WHITE = RGBColor(255, 255, 255)

prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)
blank = prs.slide_layouts[6]


def rect(slide, x, y, w, h, fill, line=None):
    shape = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
    shape.fill.solid()
    shape.fill.fore_color.rgb = fill
    shape.line.fill.background() if line is None else None
    return shape


def text(slide, value, x, y, w, h, size=20, bold=False, color=INK, font='Aptos', align=None):
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = box.text_frame
    tf.clear()
    tf.word_wrap = True
    tf.margin_left = Inches(.02)
    tf.margin_right = Inches(.02)
    tf.margin_top = Inches(.01)
    tf.margin_bottom = Inches(.01)
    for i, line in enumerate(value.split('\n')):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.text = line
        p.font.name = font
        p.font.size = Pt(size)
        p.font.bold = bold
        p.font.color.rgb = color
        p.space_after = Pt(7)
        if align is not None:
            p.alignment = align
    return box


def slide(title, source=''):
    s = prs.slides.add_slide(blank)
    s.background.fill.solid()
    s.background.fill.fore_color.rgb = WHITE
    rect(s, 0, 0, .16, 7.5, BLUE)
    text(s, title, .55, .35, 12.1, .62, 27, True, NAVY)
    rect(s, .57, 1.08, 12.05, .018, PALE)
    text(s, source or 'Group 6  |  PatchCore small-defect localization', .6, 7.12, 11.8, .23, 9, False, MUTED)
    text(s, str(len(prs.slides)), 12.25, 7.10, .4, .24, 9, False, MUTED, align=PP_ALIGN.RIGHT)
    return s


def bullets(s, lines, x=.75, y=1.43, w=11.7, size=21, gap=.72):
    for i, line in enumerate(lines):
        rect(s, x, y+i*gap+.12, .1, .1, BLUE)
        text(s, line, x+.28, y+i*gap, w-.28, gap-.07, size)


def image_fit(s, path, x, y, w, h):
    from PIL import Image
    with Image.open(path) as im:
        iw, ih = im.size
    scale = min(w/iw, h/ih)
    dw, dh = iw*scale, ih*scale
    s.shapes.add_picture(str(path), Inches(x+(w-dw)/2), Inches(y+(h-dh)/2), width=Inches(dw), height=Inches(dh))


def table(s, headers, rows, x, y, widths, row_h=.40, font=15):
    t = s.shapes.add_table(len(rows)+1, len(headers), Inches(x), Inches(y), Inches(sum(widths)), Inches(row_h*(len(rows)+1))).table
    for j, width in enumerate(widths):
        t.columns[j].width = Inches(width)
    for i, row in enumerate([headers]+rows):
        for j, val in enumerate(row):
            c = t.cell(i,j)
            c.text = str(val)
            c.fill.solid()
            c.fill.fore_color.rgb = NAVY if i == 0 else (WHITE if i%2 else PALE)
            c.vertical_anchor = MSO_ANCHOR.MIDDLE
            c.margin_left = Inches(.11)
            c.margin_right = Inches(.08)
            c.margin_top = Inches(.04)
            c.margin_bottom = Inches(.04)
            for p in c.text_frame.paragraphs:
                p.font.name = 'Aptos'
                p.font.size = Pt(font)
                p.font.bold = i == 0
                p.font.color.rgb = WHITE if i == 0 else INK
    return t


with SUMMARY.open(newline='', encoding='utf-8') as f:
    data = list(csv.DictReader(f))
R = {(r['category'], int(r['image_size']), r['layers'], r['budget'], r['group']): r for r in data}
def a(cat, size, layer, budget='ratio0.1'):
    return float(R[(cat,size,layer,budget,'small')]['aupro_mean'])
def latency(cat, size, layer, budget='ratio0.1'):
    return float(R[(cat,size,layer,budget,'small')]['median_latency_ms_mean'])


# 1
s = slide('When Do Multiscale Features Help Small Defect Localization?')
text(s, 'Accuracy and efficiency of PatchCore on MVTec AD', .82, 1.65, 11.8, .8, 28, False, BLUE)
text(s, 'Yang Cao  ·  Bernie Chen  ·  Celine Li', .82, 3.0, 11.2, .48, 22, True, NAVY)
text(s, 'Group 6  |  Computer Vision Final Project  |  November 2026', .82, 3.57, 11.2, .45, 17, False, MUTED)
text(s, 'Main question: Does feature fusion help when defects are small and memory is limited?', .82, 5.28, 11.5, .75, 23, True, INK)

# 2
s = slide('Problem and research question', 'MVTec AD [1]  ·  PatchCore [6]')
bullets(s, ['Industrial training sets often contain normal images but few examples of future defects.',
            'PatchCore compares each test patch with a memory bank of normal patch features.',
            'For small defects, we ask whether combining layer2 and layer3 improves localization enough to justify its cost.'], y=1.55, size=22, gap=1.35)

# 3
s = slide('Related work and our contribution', 'Papers [1]–[9] are listed in the English report')
table(s, ['Approach', 'Key idea', 'Connection to our study'], [
    ['PaDiM [3]', 'Patch-feature distribution', 'Another normal-only baseline'],
    ['PatchCore [6]', 'Coreset + nearest neighbor', 'Our fixed architecture'],
    ['Reverse Distillation [7]', 'Multiscale teacher features', 'Alternative feature use'],
    ['Heckler et al. [8]', 'Feature-layer selection matters', 'Motivates layer comparison'],
    ['EfficientAD [9]', 'Low-latency anomaly detection', 'Efficiency context'],
], .65, 1.6, [2.3, 4.5, 5.1], .72, 17)
text(s, 'We define small defects from original masks, compare feature layers at matched storage, and audit cropping and latency.', .75, 5.9, 11.8, .7, 21, True, NAVY)

# 4
s = slide('Hypotheses and design', 'Protocol follows the final English report')
table(s, ['Question', 'Comparison', 'What would support it?'], [
    ['H1', 'layer2 vs layer3', 'Higher small-defect AUPRO for layer2'],
    ['H2', 'fusion vs single layers', 'Consistent localization gain from fusion'],
    ['H3', 'equal 16 MiB banks', 'Fusion gain after matching vector storage'],
], .8, 1.7, [1.5, 4.1, 5.9], .9, 19)
text(s, 'The PatchCore architecture is unchanged. Our study tests when each feature setting helps.', .85, 5.62, 11.7, .75, 21, False, INK)

# 5
s = slide('Dataset and original defect areas', 'MVTec AD [1]  ·  results/audit/size224')
table(s, ['Category', 'Normal train', 'Normal test', 'Small defects', 'Larger defects'], [
    ['screw', '320', '41', '118', '1'], ['capsule', '219', '23', '85', '24'], ['metal nut', '220', '22', '7', '86'],
], .8, 1.42, [2.3, 2.25, 2.25, 2.4, 2.4], .48, 16)
image_fit(s, ROOT/'results/audit/size224/defect_area_histograms.png', .9, 3.53, 11.65, 2.72)
text(s, 'Small = original mask area ≤ 1% of original image. The groups are fixed before resizing or cropping.', .9, 6.45, 11.7, .5, 16, False, MUTED)

# 6
s = slide('Method: from normal images to anomaly maps', 'PatchCore [6]  ·  study/model.py')
labels = ['Normal train images', 'Frozen WRN50-2\nlayer2 / layer3 / fusion', 'Approximate greedy\ncoreset bank', 'CPU FAISS\n1-nearest neighbor', 'Anomaly map']
for i, label in enumerate(labels):
    x = .65+i*2.53
    rect(s, x, 1.55, 2.16, 1.28, NAVY if i in (1,3) else PALE)
    text(s, label, x+.13, 1.88, 1.9, .8, 15, True, WHITE if i in (1,3) else NAVY, align=PP_ALIGN.CENTER)
    if i<4:
        text(s, '→', x+2.17, 1.92, .35, .5, 24, True, BLUE)
text(s, "LAYERS = {'layer2': ['layer2'], 'layer3': ['layer3'],\n          'fusion': ['layer2', 'layer3']}\nsampler = ApproximateGreedyCoresetSampler(config['coreset_ratio'], device)", .78, 3.52, 11.9, 1.48, 18, False, INK, font='Consolas')
text(s, 'Only normal training images enter the bank. CUDA runs feature extraction and coreset sampling; FAISS search runs on CPU.', .8, 5.45, 11.75, .8, 19)

# 7
s = slide('Experimental protocol', '54 main runs + 27 fixed-bank runs on a Windows RTX 5060 Laptop GPU')
table(s, ['Condition', 'Values'], [
    ['Dataset', 'screw, capsule, metal_nut; official train/test split'],
    ['Features', 'layer2, layer3, fusion'],
    ['Seeds', '0, 1, 2 for the coreset'],
    ['Input size', '224 and 320 pixels; resize + center crop'],
    ['Main bank', '10% approximate greedy coreset: 54 runs'],
    ['Matched bank', '4096 × 1024 float32 vectors = 16 MiB: 27 runs'],
], .9, 1.45, [2.7, 8.7], .72, 18)

# 8
s = slide('How results are evaluated', 'study/metrics.py  ·  final report Methodology')
bullets(s, ['Primary metric: small-defect AUPRO@0.3, normalized over false-positive rates 0 to 0.3.',
            'Secondary metrics: pixel AUROC and image AUROC.',
            'We also measure bank vector storage and synchronized batch-1 latency.',
            'Normal test images are included in subgroup metrics; test masks never select a model threshold.'], y=1.45, size=20, gap=1.0)
text(s, 'def aupro(masks, maps, fpr_limit=.3):', .95, 5.78, 10.8, .55, 20, False, NAVY, font='Consolas')

# 9
s = slide('Main result: layer2 beats layer3', 'Mean ± sample SD across three coreset seeds  ·  10% bank')
image_fit(s, ROOT/'tmp/pdfs/small_defect_aupro.png', .75, 1.36, 11.9, 4.45)
text(s, 'Layer2 scores higher in all six category × input-size comparisons. Fusion is close to layer2, without a consistent gain.', .95, 5.97, 11.6, .75, 21, True, NAVY)

# 10
s = slide('320-pixel input raises AUPRO and latency', '10% coreset  ·  224 vs 320 pixels')
rows=[]
for cat in ['screw','capsule','metal_nut']:
    x,y=a(cat,224,'layer2'),a(cat,320,'layer2')
    rows.append([cat.replace('_',' '),f'{x:.4f}',f'{y:.4f}',f'+{y-x:.4f}',f'{latency(cat,320,"layer2")/latency(cat,224,"layer2"):.1f}×'])
table(s, ['Layer2 category', '224 AUPRO', '320 AUPRO', 'Gain', 'Latency ratio'], rows, .82, 1.7, [3.0, 2.1, 2.1, 1.7, 2.4], .78, 18)
bullets(s, ['All nine category–feature combinations improve at 320 pixels.',
            'Bank storage and inference time increase; resize and smoothing scales also change.'], x=.87, y=5.3, size=19, gap=.7)

# 11
s = slide('Equal 16 MiB banks: fusion still lacks a clear gain', '224 pixels  ·  4096 vectors per bank  ·  three coreset seeds')
rows=[]
for cat in ['screw','capsule','metal_nut']:
    rows.append([cat.replace('_',' '),f'{a(cat,224,"layer2","bank4096"):.4f}',
                 f'{a(cat,224,"fusion","bank4096"):.4f}',
                 f'{latency(cat,224,"layer2","bank4096"):.1f}',
                 f'{latency(cat,224,"fusion","bank4096"):.1f}'])
table(s, ['Category', 'Layer2 AUPRO', 'Fusion AUPRO', 'Layer2 ms', 'Fusion ms'], rows, .78, 1.63, [2.6, 2.5, 2.5, 2.0, 2.0], .85, 18)
text(s, 'Layer2 is faster in all three categories. The 0.0002 metal-nut fusion difference comes from a subgroup with seven anomaly images.', .9, 5.6, 11.45, .88, 21, True, NAVY)

# 12
s = slide('Localization versus bank vector storage', 'Each point is a three-seed mean  ·  bank vector storage only')
image_fit(s, ROOT/'tmp/pdfs/accuracy_memory_tradeoff.png', .7, 1.3, 11.9, 4.72)
text(s, 'Equal stored vector bytes do not imply equal peak GPU memory, feature-extraction cost, or query-grid size.', .9, 6.13, 11.7, .6, 18, False, MUTED)

# 13
s = slide('Qualitative results: screw and capsule', '224-pixel input  ·  seed 0  ·  results/figures')
image_fit(s, ROOT/'results/figures/screw_small_comparison.png', .8, 1.32, 11.8, 2.37)
image_fit(s, ROOT/'results/figures/capsule_small_comparison.png', .8, 4.02, 11.8, 2.37)
text(s, 'Input, transformed ground truth, layer2, layer3, and fusion maps. Heatmap panels have separate display color scales.', .9, 6.64, 11.7, .35, 13, False, MUTED)

# 14
s = slide('Qualitative result and uncertainty: metal nut', 'results/figures  ·  paired image bootstrap in results/comparisons')
image_fit(s, ROOT/'results/figures/metal_nut_small_comparison.png', .78, 1.34, 11.8, 2.45)
bullets(s, ['Only seven metal-nut anomaly images fall in the small-defect group.',
            'The paired bootstrap compares one seed-0 fitted model pair per category and size.',
            'Three-seed standard deviations describe coreset variation, not population-level certainty.'], x=.82, y=4.18, size=18, gap=.75)

# 15
s = slide('Conclusion and limits', 'Scope: three MVTec AD categories and one frozen backbone')
bullets(s, ['Layer2 gives the strongest overall small-defect localization in this study.',
            'Fusion gives no consistent benefit, including with equal 16 MiB banks.',
            'Layer3 is faster and stores fewer vectors in the 10% coreset condition.',
            '320-pixel inputs improve localization while increasing latency and bank storage.'], y=1.4, size=21, gap=1.02)
text(s, 'For inspection systems, layer2 is a practical starting point when localization matters most; layer3 trades accuracy for speed and storage.', .88, 5.55, 11.6, .8, 17, False, NAVY)
text(s, 'Next: test more categories and backbones, and separate preprocessing effects from input-resolution gains.', .88, 6.48, 11.6, .39, 15, False, MUTED)

# 16
s = slide('References and reproducibility', 'Full bibliography and methods: output/pdf/group6_patchcore_final_report.pdf')
refs = [
    '[1] Bergmann et al. MVTec AD. CVPR 2019.',
    '[2] Bergmann et al. Uninformed Students. CVPR 2020.',
    '[3] Defard et al. PaDiM. ICPR Workshops and Challenges 2021.',
    '[4] Li et al. CutPaste. CVPR 2021.',
    '[5] Zavrtanik et al. DRAEM. ICCV 2021.',
    '[6] Roth et al. Towards Total Recall in Industrial Anomaly Detection. CVPR 2022.',
    '[7] Deng and Li. Reverse Distillation. CVPR 2022.',
    '[8] Heckler et al. Pretrained Feature Extractors. CVPR Workshops 2023.',
    '[9] Batzner et al. EfficientAD. WACV 2024.',
]
text(s, '\n'.join(refs), .78, 1.37, 11.75, 4.95, 15, False, INK)
text(s, 'Code, compact results, and English report: github.com/bernie90103/CV_final_project', .8, 6.47, 11.7, .4, 16, True, NAVY)

OUT.parent.mkdir(parents=True, exist_ok=True)
prs.save(OUT)
print(f'{OUT} ({len(prs.slides)} slides)')
