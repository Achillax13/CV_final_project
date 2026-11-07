"""Build the final English PDF from completed Windows experiments."""
import csv
import json
from html import escape
from pathlib import Path
from urllib.parse import urlparse

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    Image, PageBreak, KeepTogether,
)


ROOT = Path(__file__).resolve().parents[1]
SUMMARY = ROOT / 'results/summary_windows/mean_std.csv'
AUDIT = ROOT / 'results/audit/size224/summary.csv'
TEMP = ROOT / 'tmp/pdfs'
OUTPUT = ROOT / 'output/pdf/group6_patchcore_final_report.pdf'
VIDEO_LINK_FILE = ROOT / 'docs/presentation_video_url.txt'
CATS = ['screw', 'capsule', 'metal_nut']
LAYERS = ['layer2', 'layer3', 'fusion']
NAVY = colors.HexColor('#17324D')
BLUE = colors.HexColor('#2576A8')
PALE = colors.HexColor('#EDF4F8')


def read_rows():
    with SUMMARY.open(newline='', encoding='utf-8') as f:
        rows = list(csv.DictReader(f))
    lookup = {(r['category'], int(r['image_size']), r['layers'], r['budget'], r['group']): r for r in rows}
    expected = {(cat, size, layer, 'ratio0.1', 'small') for cat in CATS for size in [224, 320] for layer in LAYERS}
    expected |= {(cat, 224, layer, 'bank4096', 'small') for cat in CATS for layer in LAYERS}
    missing = expected - set(lookup)
    if missing:
        raise RuntimeError(f'Missing summary rows: {sorted(missing)}')
    if any(int(lookup[k]['n_seeds']) != 3 for k in expected):
        raise RuntimeError('The report requires all three seeds in each condition.')
    with AUDIT.open(newline='', encoding='utf-8') as f:
        audit = list(csv.DictReader(f))
    return lookup, audit


def val(row, key):
    return float(row[key])


def make_chart(lookup):
    TEMP.mkdir(parents=True, exist_ok=True)
    path = TEMP / 'small_defect_aupro.png'
    fig, axes = plt.subplots(1, 2, figsize=(9, 3.3), sharey=True)
    palette = {'layer2': '#1686A7', 'layer3': '#D98F35', 'fusion': '#31527D'}
    for ax, size in zip(axes, [224, 320]):
        x = np.arange(3)
        for i, layer in enumerate(LAYERS):
            vals = [val(lookup[(cat,size,layer,'ratio0.1','small')], 'aupro_mean') for cat in CATS]
            errs = [val(lookup[(cat,size,layer,'ratio0.1','small')], 'aupro_std') for cat in CATS]
            ax.bar(x+(i-1)*.25, vals, .23, color=palette[layer], label=layer, yerr=errs, capsize=2)
        ax.set_xticks(x, ['screw','capsule','metal nut'])
        ax.set_ylim(.70, 1.01)
        ax.set_title(f'{size} pixel input')
        ax.grid(axis='y', alpha=.2)
    axes[0].set_ylabel('Small-defect AUPRO@0.3')
    axes[1].legend(frameon=False, ncol=3, loc='lower center', bbox_to_anchor=(.5,-.27))
    fig.subplots_adjust(bottom=.25, wspace=.12, left=.07, right=.99, top=.88)
    fig.savefig(path, dpi=190)
    plt.close(fig)
    return path


def make_tradeoff_chart(lookup):
    path = TEMP / 'accuracy_memory_tradeoff.png'
    fig, axes = plt.subplots(1, 3, figsize=(9, 3.1), sharey=True)
    palette = {'layer2': '#1686A7', 'layer3': '#D98F35', 'fusion': '#31527D'}
    conditions = [(224,'ratio0.1','o'),(320,'ratio0.1','s'),(224,'bank4096','D')]
    for ax, cat in zip(axes, CATS):
        for size,budget,marker in conditions:
            for layer in LAYERS:
                r = lookup[(cat,size,layer,budget,'small')]
                ax.scatter(val(r,'bank_MiB_mean'),val(r,'aupro_mean'),s=48,marker=marker,
                           color=palette[layer],edgecolor='white',linewidth=.5,zorder=3)
        ax.set_title(cat.replace('_',' '))
        ax.set_xscale('log')
        from matplotlib.ticker import NullLocator
        ax.xaxis.set_minor_locator(NullLocator())
        ax.set_xlim(12,300)
        ax.set_xticks([16,64,256],['16','64','256'])
        ax.set_ylim(.70,1.01)
        ax.grid(alpha=.18)
        ax.set_xlabel('Bank vector storage (MiB)')
    axes[0].set_ylabel('Small-defect AUPRO@0.3')
    from matplotlib.lines import Line2D
    colors_legend=[Line2D([0],[0],marker='o',linestyle='None',color=palette[l],label=l) for l in LAYERS]
    marker_legend=[Line2D([0],[0],marker=m,linestyle='None',color='#555',label=label) for _,_,m,label in [(224,'ratio0.1','o','224 / 10%'),(320,'ratio0.1','s','320 / 10%'),(224,'bank4096','D','224 / 16 MiB')]]
    fig.legend(handles=colors_legend+marker_legend,ncol=6,frameon=False,loc='lower center',bbox_to_anchor=(.5,-.035),fontsize=7)
    fig.subplots_adjust(left=.075,right=.995,top=.89,bottom=.25,wspace=.16)
    fig.savefig(path,dpi=190,bbox_inches='tight')
    plt.close(fig)
    return path


def footer(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor('#D8E2E8'))
    canvas.line(42, 43, 570, 43)
    canvas.setFont('Helvetica', 8)
    canvas.setFillColor(colors.HexColor('#61717E'))
    canvas.drawString(42, 30, 'Group 6 | PatchCore small-defect localization | Windows RTX 5060')
    canvas.drawRightString(570, 30, str(doc.page))
    canvas.restoreState()


def table(data, widths, font=8, header=True):
    t = Table(data, colWidths=widths, repeatRows=1 if header else 0, hAlign='LEFT')
    cmds = [
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,0), (-1,-1), font),
        ('LEADING', (0,0), (-1,-1), font+2),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('LINEBELOW', (0,-1), (-1,-1), .5, colors.HexColor('#CBD8DF')),
    ]
    if header:
        cmds += [('BACKGROUND', (0,0), (-1,0), NAVY), ('TEXTCOLOR', (0,0), (-1,0), colors.white),
                 ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                 ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, PALE])]
    t.setStyle(TableStyle(cmds))
    return t


def run_table(lookup, size, budget):
    data = [['Category', 'Features', 'Small AUPRO', 'All AUPRO', 'Bank MiB', 'Latency ms']]
    for cat in CATS:
        for layer in LAYERS:
            s = lookup[(cat,size,layer,budget,'small')]
            a = lookup[(cat,size,layer,budget,'all')]
            data.append([cat.replace('_',' '),layer,
                         f"{val(s,'aupro_mean'):.4f} +/- {val(s,'aupro_std'):.4f}",
                         f"{val(a,'aupro_mean'):.4f}",
                         f"{val(s,'bank_MiB_mean'):.1f}",
                         f"{val(s,'median_latency_ms_mean'):.1f}"])
    result = table(data, [78,65,124,85,80,80], font=8)
    if budget == 'bank4096':
        result.setStyle(TableStyle([('TOPPADDING',(0,0),(-1,-1),3),('BOTTOMPADDING',(0,0),(-1,-1),3)]))
    return result


def bootstrap_table():
    data = [['Category','Input','Fusion - layer2','95% image CI','Status']]
    for size in [224,320]:
        for cat in CATS:
            path = ROOT / f'results/comparisons/{cat}_{size}_layer2_vs_fusion_seed0.json'
            result = json.loads(path.read_text(encoding='utf-8'))['groups']['small']
            if result['status'] == 'ok':
                delta = f"{result['exact_difference_b_minus_a']:+.4f}"
                lo, hi = result['ci95_b_minus_a']
                interval = f'[{lo:+.4f}, {hi:+.4f}]'
            else:
                delta, interval = 'N/A', 'N/A'
            data.append([cat.replace('_',' '),str(size),delta,interval,
                         'Insufficient n' if result['status'] == 'insufficient_samples' else 'Valid'])
    return table(data,[115,60,104,132,101],font=8)


def build(return_story=False):
    lookup, audit = read_rows()
    video_url = VIDEO_LINK_FILE.read_text(encoding='utf-8-sig').strip() if VIDEO_LINK_FILE.is_file() else ''
    if video_url:
        parsed = urlparse(video_url)
        if parsed.scheme != 'https' or not parsed.netloc or any(ch.isspace() for ch in video_url):
            raise ValueError(f'Invalid HTTPS presentation URL in {VIDEO_LINK_FILE}')
    chart = make_chart(lookup)
    tradeoff = make_tradeoff_chart(lookup)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='ReportTitle', parent=styles['Title'], fontName='Helvetica-Bold', fontSize=19, leading=23, textColor=NAVY, spaceAfter=10))
    styles.add(ParagraphStyle(name='Deck', parent=styles['Normal'], fontSize=10.5, leading=15, textColor=BLUE, spaceAfter=16))
    styles.add(ParagraphStyle(name='SectionX', parent=styles['Heading2'], fontName='Helvetica-Bold', fontSize=12, leading=15, textColor=NAVY, spaceBefore=14, spaceAfter=7, keepWithNext=True))
    styles.add(ParagraphStyle(name='BodyX', parent=styles['BodyText'], fontSize=9, leading=13, spaceAfter=8))
    styles.add(ParagraphStyle(name='CaptionX', parent=styles['BodyText'], fontSize=7.5, leading=10, textColor=colors.HexColor('#4D5D68'), spaceAfter=8))
    styles.add(ParagraphStyle(name='ReferenceX', parent=styles['BodyText'], fontSize=8, leading=11, spaceAfter=7))
    p = lambda text: Paragraph(text, styles['BodyX'])
    h = lambda text: Paragraph(text, styles['SectionX'])
    cap = lambda text: Paragraph(text, styles['CaptionX'])
    ref = lambda text: Paragraph(text, styles['ReferenceX'])
    story = []

    story += [Paragraph('When Do Multiscale Features Help Small Defect Localization?', styles['ReportTitle']),
              Paragraph('Accuracy and efficiency of PatchCore on MVTec AD', styles['Deck']),
              p('<b>Group 6:</b> Yang Cao, Bernie Chen, Celine Li &nbsp;&nbsp; | &nbsp;&nbsp; Final project report &nbsp;&nbsp; | &nbsp;&nbsp; 7 November 2026'),
              h('Abstract'),
              p('We tested PatchCore with frozen WideResNet50-2 layer2, layer3, and combined layer2+layer3 features on screw, capsule, and metal_nut. We used the official train/test split, three coreset seeds, and 224- and 320-pixel inputs. Layer2 outperformed layer3 on small-defect AUPRO@0.3 for every category and input size. Combining features gave no consistent gain over layer2. Increasing input size improved all nine category-feature combinations, while increasing bank storage and latency. We also compared the features with equal-sized memory banks.'),
              h('Introduction'),
              p('Industrial inspection often has normal training images but few examples of possible defects. MVTec AD reflects this setting: it provides normal training images and pixel-level masks for anomalous test images [1]. PatchCore compares pretrained patch features with a memory bank built from normal images [6]. We examine whether layer2, layer3, or their combined features locate small defects more accurately, and measure the storage and inference time each setting requires.'),
              h('Related work'),
              p('Uninformed Students trains students to reproduce a pretrained teacher on normal images; disagreement marks anomalies [2]. CutPaste trains with synthetic cut-and-paste defects [4]. DRAEM uses simulated anomalies to train a reconstruction and segmentation model [5]. Our experiments keep the PatchCore backbone frozen.'),
              p('PaDiM estimates a distribution for patch features at each spatial position [3]. PatchCore samples normal features into a coreset and scores test patches by nearest-neighbor distance [6]. Reverse Distillation learns to reconstruct multiscale teacher features [7]. Heckler et al. found that feature-layer choice can change localization performance and that one selected layer can outperform an ensemble [8]. EfficientAD studies low-latency visual anomaly detection [9].'),
              h('Study contribution'),
              p('PatchCore already combines layer2 and layer3 [6], and feature-layer selection has been studied [8]. Our contribution is a focused evaluation of small defects under controlled storage costs. We define the small-defect subgroup from original masks before preprocessing, compare three feature settings at two input sizes across three coreset seeds, and repeat the 224-pixel comparison with 4096 vectors per bank (16 MiB). We also audit cropped mask pixels and measure batch-1 latency on one Windows GPU. Matching stored vector bytes lets us assess fusion without giving it a larger bank than a single-layer setting.'),
              PageBreak(),
              h('Research questions and methodology'),
              p('<b>H1:</b> Does the finer layer2 representation localize small defects better than layer3? <b>H2:</b> Does combining layer2 and layer3 improve localization over either layer? <b>H3:</b> Does any fusion advantage shrink when memory-bank vector counts are matched? We evaluate the established PatchCore architecture.'),
              p('Following the PatchCore implementation [6], each memory bank contains patches from normal training images only. The model uses ImageNet V1 WideResNet50-2 weights, patch size 3, a 1024-dimensional final embedding, one exact CPU FAISS neighbor, and a 10% approximate greedy coreset. We resize and center crop inputs (256 to 224; 366 to 320) and transform masks with nearest-neighbor interpolation. We classify a defect as small when its original mask covers at most 1% of the original image, before evaluating any model. The primary metric is AUPRO normalized over false-positive rates from 0 to 0.3; pixel and image AUROC are secondary metrics.'),
              h('Dataset and data audit'),
              table([['Category','Normal train','Normal test','Small','Larger','Partial crop loss']] +
                    [[r['category'].replace('_',' '),r['n_train_normal'],r['n_test_normal'],r['n_test_small'],r['n_test_large'],r['n_crop_removed_defect']] for r in audit],
                    [105,82,82,70,70,103]),
              cap('Groups use defect area in the original images. Partial crop loss is shown for 224-pixel preprocessing; every annotated image retains some defect pixels. At 320 pixels, the crop-loss counts are 12 for screw, 3 for capsule, and 35 for metal nut.'),
              Spacer(1, 12)]

    histogram = ROOT / 'results/audit/size224/defect_area_histograms.png'
    story += [h('Original defect-area distributions'),
              Image(str(histogram), width=7.2*inch, height=2.48*inch),
              cap('Annotated defect area as a percentage of original image area. Red dashed lines mark the 1% cutoff for small defects. Each category uses its own x-axis scale.'),
              h('Preprocessing audit and evaluation groups'),
              p('An anomaly belongs to the small subgroup when its original mask covers more than 0% and at most 1% of the original image. Other anomaly images belong to the larger subgroup. Both subgroup metrics also include normal test images. Input resolution does not affect these groups.'),
              p('At 224 pixels, center cropping removes some annotated defect pixels from 11 screw, 3 capsule, and 33 metal-nut anomaly images. At 320 pixels, the counts are 12, 3, and 35. Every image retains some defect pixels under both transforms. Crop loss can still change the evaluated region and matters when examining individual failures.'),
              p('Within each input size, layer2, layer3, and fusion use the same spatial transform and transformed test masks. The transform changes between input sizes, so size comparisons also reflect preprocessing effects.'),
              Spacer(1, 12)]

    story += [h('Main experiment: 10% coreset, 224-pixel input'), run_table(lookup,224,'ratio0.1'),
              cap('Means and sample standard deviations across three coreset seeds. Each small-defect subgroup also includes all normal test images.'),
              h('Larger input: 10% coreset, 320-pixel input'), run_table(lookup,320,'ratio0.1'),
              cap('All timings use the same Windows RTX 5060 Laptop GPU. Feature extraction and coreset sampling run on CUDA; CPU FAISS performs nearest-neighbor search. Batch-1 latency includes transfers and postprocessing. We report the median of 30 timed iterations after 10 warmups.'),
              Spacer(1, 12)]

    story += [h('Small-defect localization by feature setting'), Image(str(chart),width=7.1*inch,height=2.60*inch),
              cap('Small-defect AUPRO@0.3 by category and input size. Error bars show the sample standard deviation across three coreset seeds; they do not measure uncertainty from test-image sampling.'),
              h('Interpretation of H1 and H2'),
              p('Layer2 has higher small-defect AUPRO than layer3 in all six category-size comparisons, consistent with H1. Layer3 uses about one quarter of the memory-bank vector storage and runs much faster. It may suit applications with less demanding localization requirements.'),
              p('Fusion scores are close to layer2 in all six comparisons, but they do not consistently exceed layer2, so the results do not support H2 as a general claim. With a 10% coreset, layer2 and fusion store the same number of 1024-dimensional vectors because the dense layer2 grid determines the patch count. Fusion requires additional computation with no clear localization gain here.'),
              h('Input size and its cost'),
              p('Moving from 224 to 320 pixels improves small-defect AUPRO in all nine category-feature comparisons. Layer2 gains 0.0139 on screw, 0.0130 on capsule, and 0.0011 on metal nut. Its mean latency rises by about 3x, and vector storage roughly doubles. Resize and Gaussian smoothing also change scale relative to the original image, so these gains include preprocessing effects.'),
              Spacer(1, 12)]

    story += [h('Paired test-image uncertainty for fusion versus layer2'),
              p('For each category and input size, we compared the seed-0 layer2 and fusion models on matched test images. We report exact AUPRO@0.3 as the point estimate and a percentile 95% interval from 1000 paired, stratified image-bootstrap resamples. The bootstrap uses 4096 score bins to reduce runtime; point-approximation error is below 0.005.'),
              bootstrap_table(),
              cap('Positive differences favor fusion. The interval reflects test-image resampling for one fitted model pair; it does not cover variation across the three coreset seeds. Metal nut has seven small-defect test images, below the prespecified minimum of ten anomalies.'),
              p('At 224 pixels, the capsule seed-0 interval falls below zero and favors layer2, while the screw interval includes zero. Both available intervals at 320 pixels include zero. Across these fitted pairs, we find no consistent fusion gain. The inference is limited to the sampled test images and one fitted pair per comparison.'),
              h('What the three-seed comparison can and cannot show'),
              p('The main tables give means and sample standard deviations for seeds 0, 1, and 2. Only the randomized coreset changes; the backbone, official split, and model settings remain fixed. These standard deviations measure coreset variation and cannot establish population-level certainty. We make no pooled significance claim across categories.'),
              Spacer(1, 10)]

    story += [h('H3: equal 4096-vector memory banks at 224 pixels'),
              p('Each feature setting retains 4096 float32 vectors with 1024 dimensions, giving 16 MiB of vector storage per fitted model. The coreset fraction varies by feature setting. This comparison matches stored vector bytes; peak RAM, GPU memory, feature extraction work, and query-grid size can still differ.'),
              run_table(lookup,224,'bank4096'),
              cap('Each category and feature setting has three coreset seeds. Test images and metric definitions match the 10% experiment.'),
              h('Practical tradeoff'),
              p('With a 16 MiB bank, layer2 scores 0.9593 versus 0.9505 for fusion on screw, and 0.9733 versus 0.9719 on capsule. Fusion scores 0.9953 versus 0.9951 on metal nut, a difference of 0.0002 in a subgroup with seven anomaly images. Layer2 is faster in each category, at about 39-41 ms versus 49-51 ms. The fixed-bank results show no consistent fusion advantage and more variation across screw seeds with this smaller bank.'),
              Spacer(1, 12)]

    story += [h('Accuracy and vector-storage tradeoff'),
              Image(str(tradeoff), width=7.25*inch, height=2.30*inch),
              cap('Each point shows a three-seed mean for one category and setting. Color denotes the feature set; marker denotes input size and coreset budget. Layer2 and fusion points can overlap when their scores are similar and storage is identical.'),
              p('With a 10% coreset, layer3 stores roughly a quarter as many vectors as layer2 or fusion because its feature grid is coarser. Moving from 224 to 320 pixels expands each bank and usually improves AUPRO while increasing latency. The 4096-vector condition gives every feature set a 16 MiB bank. Query-patch counts and backbone feature-extraction costs still vary.'),
              Spacer(1, 10)]

    screw = ROOT / 'results/figures/screw_small_comparison.png'
    capsule = ROOT / 'results/figures/capsule_small_comparison.png'
    metal_nut = ROOT / 'results/figures/metal_nut_small_comparison.png'
    story += [h('Qualitative examples'),
              Image(str(screw), width=7.2*inch, height=1.55*inch),
              cap('Screw small-defect example at 224 pixels and seed 0: input, transformed ground truth, and anomaly maps for layer2, layer3, and fusion.'),
              Image(str(capsule), width=7.2*inch, height=1.55*inch),
              cap('Capsule small-defect example. Each heatmap panel has its own display color scale. Metrics use the unscaled continuous scores.'),
              Image(str(metal_nut), width=7.2*inch, height=1.55*inch),
              cap('Metal-nut example. Its small-defect subgroup contains seven anomaly images, so the subgroup results are descriptive.'),
              h('Limitations and conclusion'),
              p('Screw has one larger-defect test image, and metal_nut has seven small-defect images. Results for those subgroups are descriptive. Center cropping removes some annotated pixels. Seed standard deviations measure coreset randomness but leave uncertainty from the finite test set unresolved. The study covers three MVTec AD categories and one backbone. We did not tune thresholds or hyperparameters on test masks.'),
              p('Across these experiments, layer2 gives the strongest overall small-defect localization. Fusion shows no consistent benefit, including with equal 16 MiB vector banks. Layer3 runs faster and uses less bank storage under the 10% coreset condition. A 320-pixel input improves localization while increasing latency and storage.'),
              Spacer(1, 10),
              h('References'),
              ref('[1] P. Bergmann, M. Fauser, D. Sattlegger, and C. Steger. "MVTec AD: A Comprehensive Real-World Dataset for Unsupervised Anomaly Detection." <i>CVPR</i>, pp. 9592-9600, 2019. <link href="https://openaccess.thecvf.com/content_CVPR_2019/html/Bergmann_MVTec_AD_--_A_Comprehensive_Real-World_Dataset_for_Unsupervised_Anomaly_CVPR_2019_paper.html">Official paper</link>.'),
              ref('[2] P. Bergmann, M. Fauser, D. Sattlegger, and C. Steger. "Uninformed Students: Student-Teacher Anomaly Detection With Discriminative Latent Embeddings." <i>CVPR</i>, pp. 4183-4192, 2020. <link href="https://openaccess.thecvf.com/content_CVPR_2020/html/Bergmann_Uninformed_Students_Student-Teacher_Anomaly_Detection_With_Discriminative_Latent_Embeddings_CVPR_2020_paper.html">Official paper</link>.'),
              ref('[3] T. Defard, A. Setkov, A. Loesch, and R. Audigier. "PaDiM: A Patch Distribution Modeling Framework for Anomaly Detection and Localization." <i>ICPR Workshops and Challenges</i>, pp. 475-489, 2021. doi:10.1007/978-3-030-68799-1_35. <link href="https://cea.hal.science/cea-03251821v1">Author manuscript</link>.'),
              ref('[4] C.-L. Li, K. Sohn, J. Yoon, and T. Pfister. "CutPaste: Self-Supervised Learning for Anomaly Detection and Localization." <i>CVPR</i>, pp. 9664-9674, 2021. <link href="https://openaccess.thecvf.com/content/CVPR2021/html/Li_CutPaste_Self-Supervised_Learning_for_Anomaly_Detection_and_Localization_CVPR_2021_paper.html">Official paper</link>.'),
              ref('[5] V. Zavrtanik, M. Kristan, and D. Skocaj. "DRAEM: A Discriminatively Trained Reconstruction Embedding for Surface Anomaly Detection." <i>ICCV</i>, pp. 8330-8339, 2021. <link href="https://openaccess.thecvf.com/content/ICCV2021/html/Zavrtanik_DRAEM_-_A_Discriminatively_Trained_Reconstruction_Embedding_for_Surface_Anomaly_ICCV_2021_paper.html">Official paper</link>.'),
              ref('[6] K. Roth, L. Pemula, J. Zepeda, B. Scholkopf, T. Brox, and P. Gehler. "Towards Total Recall in Industrial Anomaly Detection." <i>CVPR</i>, pp. 14318-14328, 2022. <link href="https://openaccess.thecvf.com/content/CVPR2022/html/Roth_Towards_Total_Recall_in_Industrial_Anomaly_Detection_CVPR_2022_paper.html">Official paper</link>.'),
              ref('[7] H. Deng and X. Li. "Anomaly Detection via Reverse Distillation From One-Class Embedding." <i>CVPR</i>, pp. 9737-9746, 2022. <link href="https://openaccess.thecvf.com/content/CVPR2022/html/Deng_Anomaly_Detection_via_Reverse_Distillation_From_One-Class_Embedding_CVPR_2022_paper.html">Official paper</link>.'),
              ref('[8] L. Heckler, R. Koenig, and P. Bergmann. "Exploring the Importance of Pretrained Feature Extractors for Unsupervised Anomaly Detection and Localization." <i>CVPR Workshops</i>, pp. 2917-2926, 2023. <link href="https://openaccess.thecvf.com/content/CVPR2023W/VAND/html/Heckler_Exploring_the_Importance_of_Pretrained_Feature_Extractors_for_Unsupervised_Anomaly_CVPRW_2023_paper.html">Official paper</link>.'),
              ref('[9] K. Batzner, L. Heckler, and R. Koenig. "EfficientAD: Accurate Visual Anomaly Detection at Millisecond-Level Latencies." <i>WACV</i>, pp. 128-138, 2024. <link href="https://openaccess.thecvf.com/content/WACV2024/html/Batzner_EfficientAD_Accurate_Visual_Anomaly_Detection_at_Millisecond-Level_Latencies_WACV_2024_paper.html">Official paper</link>.'),
              h('Reproducibility'),
              p('PatchCore code: <link href="https://github.com/amazon-science/patchcore-inspection">official repository</link>, pinned at commit fcaa92f. The results/runs_windows/formal/ directory contains configurations, package versions, data and source hashes, predictions, metrics, and runtime records. Per-seed and aggregate tables are in results/summary_windows/.')]

    if video_url:
        safe_url = escape(video_url, quote=True)
        story += [h('Presentation video'),
                  p(f'Slide-based presentation recording: <link href="{safe_url}">Watch on OneDrive</link>.')]

    if return_story:
        return story

    doc = SimpleDocTemplate(str(OUTPUT), pagesize=(612,792), leftMargin=42, rightMargin=42,
                            topMargin=42, bottomMargin=55, title='Group 6 PatchCore Final Report',
                            author='Yang Cao, Bernie Chen, Celine Li')
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    print(OUTPUT)


if __name__ == '__main__':
    build()
