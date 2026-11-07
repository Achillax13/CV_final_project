"""Create a Traditional Chinese companion to the English slide deck."""
from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.util import Pt


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'output/presentation/group6_patchcore_final_presentation.pptx'
OUTPUT = ROOT / 'output/presentation/group6_patchcore_final_presentation_zh.pptx'

T = {
    'When Do Multiscale Features Help Small Defect Localization?': '多尺度特徵何時有助於小瑕疵定位？',
    'Group 6  |  PatchCore small-defect localization': '第六組  |  PatchCore 小瑕疵定位',
    'Accuracy and efficiency of PatchCore on MVTec AD': 'PatchCore 在 MVTec AD 的準確度與效率',
    'Group 6  |  Computer Vision Final Project  |  November 2026': '第六組  |  電腦視覺期末專案  |  2026 年 11 月',
    'Main question: Does feature fusion help when defects are small and memory is limited?': '核心問題：瑕疵很小、記憶庫有限時，融合特徵真的有幫助嗎？',
    'Problem and research question': '研究問題與動機',
    'Industrial training sets often contain normal images but few examples of future defects.': '工業檢測通常有正常訓練影像，卻難以預先收集未來可能出現的各種瑕疵。',
    'PatchCore compares each test patch with a memory bank of normal patch features.': 'PatchCore 將測試影像的每個 patch，與正常影像特徵組成的記憶庫比較。',
    'For small defects, we ask whether combining layer2 and layer3 improves localization enough to justify its cost.': '小瑕疵定位中，融合 layer2 與 layer3 的收益值得額外成本嗎？',
    'Related work and our contribution': '相關研究與本組貢獻',
    'Papers [1]–[9] are listed in the English report': '文獻 [1]–[9] 的完整書目見英文報告',
    'We define small defects from original masks, compare feature layers at matched storage, and audit cropping and latency.': '我們依原始 mask 定義小瑕疵，在相同儲存量下比較特徵層，並檢查裁切與推論時間。',
    'Hypotheses and design': '研究問題與比較設計',
    'Protocol follows the final English report': '實驗設定與英文期末報告一致',
    'The PatchCore architecture is unchanged. Our study tests when each feature setting helps.': '我們沿用 PatchCore 架構，檢查不同特徵設定在什麼條件下有效。',
    'Dataset and original defect areas': '資料集與原始瑕疵面積',
    'Small = original mask area ≤ 1% of original image. The groups are fixed before resizing or cropping.': '小瑕疵定義：原始 mask 面積不超過原圖 1%；分組在縮放與裁切前就固定。',
    'Method: from normal images to anomaly maps': '方法：從正常影像到異常熱力圖',
    'Normal train images': '正常訓練影像',
    'Frozen WRN50-2\nlayer2 / layer3 / fusion': '凍結的 WRN50-2\nlayer2 / layer3 / 融合',
    'Approximate greedy\ncoreset bank': '近似貪婪抽樣\ncoreset 記憶庫',
    'CPU FAISS\n1-nearest neighbor': 'CPU FAISS\n最近鄰搜尋',
    'Anomaly map': '異常熱力圖',
    'Only normal training images enter the bank. CUDA runs feature extraction and coreset sampling; FAISS search runs on CPU.': '只有正常訓練圖進入記憶庫。CUDA 負責特徵提取與 coreset 抽樣；FAISS 在 CPU 搜尋。',
    'Experimental protocol': '實驗設定',
    '54 main runs + 27 fixed-bank runs on a Windows RTX 5060 Laptop GPU': 'Windows RTX 5060 Laptop GPU：54 次主實驗與 27 次固定容量實驗',
    'How results are evaluated': '結果如何評估',
    'study/metrics.py  ·  final report Methodology': 'study/metrics.py  ·  英文報告 Methodology',
    'Primary metric: small-defect AUPRO@0.3, normalized over false-positive rates 0 to 0.3.': '主指標是小瑕疵 AUPRO@0.3：計算誤報率 0 到 0.3 區間的標準化面積。',
    'Secondary metrics: pixel AUROC and image AUROC.': '補充指標：pixel AUROC 與 image AUROC。',
    'We also measure bank vector storage and synchronized batch-1 latency.': '另外量測記憶庫向量儲存量，以及同步後 batch-1 推論時間。',
    'Normal test images are included in subgroup metrics; test masks never select a model threshold.': '分組指標包含正常測試圖；我們沒有用測試 mask 選擇模型門檻。',
    'Main result: layer2 beats layer3': '主要結果：layer2 優於 layer3',
    'Mean ± sample SD across three coreset seeds  ·  10% bank': '三個 coreset 種子的平均值 ± 樣本標準差  ·  10% 記憶庫',
    'Layer2 scores higher in all six category × input-size comparisons. Fusion is close to layer2, without a consistent gain.': '六組類別 × 尺寸比較中，layer2 都高於 layer3。融合接近 layer2，但沒有穩定增益。',
    '320-pixel input raises AUPRO and latency': '320 像素提高 AUPRO，也增加延遲',
    '10% coreset  ·  224 vs 320 pixels': '10% coreset  ·  比較 224 與 320 像素',
    'All nine category–feature combinations improve at 320 pixels.': '九組類別與特徵組合在 320 像素時都提高。',
    'Bank storage and inference time increase; resize and smoothing scales also change.': '記憶庫與推論時間也增加；縮放與平滑的相對尺度同時改變。',
    'Equal 16 MiB banks: fusion still lacks a clear gain': '同為 16 MiB：融合仍無明顯優勢',
    '224 pixels  ·  4096 vectors per bank  ·  three coreset seeds': '224 像素  ·  每個記憶庫 4096 向量  ·  三個 coreset 種子',
    'Layer2 is faster in all three categories. The 0.0002 metal-nut fusion difference comes from a subgroup with seven anomaly images.': '三類資料中 layer2 都較快。metal_nut 的融合僅高 0.0002，而該分組只有七張異常圖。',
    'Localization versus bank vector storage': '定位準確度與記憶庫容量',
    'Each point is a three-seed mean  ·  bank vector storage only': '每點是三個種子的平均值  ·  橫軸僅計向量儲存量',
    'Equal stored vector bytes do not imply equal peak GPU memory, feature-extraction cost, or query-grid size.': '向量儲存量相同，不代表 GPU 峰值記憶體、特徵提取成本或查詢網格相同。',
    'Qualitative results: screw and capsule': '瑕疵案例：screw 與 capsule',
    '224-pixel input  ·  seed 0  ·  results/figures': '224 像素  ·  seed 0  ·  results/figures',
    'Input, transformed ground truth, layer2, layer3, and fusion maps. Heatmap panels have separate display color scales.': '依序為輸入圖、變換後標註與三種特徵熱力圖；各熱力圖使用獨立的顯示色階。',
    'Qualitative result and uncertainty: metal nut': '瑕疵案例與不確定性：metal nut',
    'results/figures  ·  paired image bootstrap in results/comparisons': 'results/figures  ·  成對影像 bootstrap 見 results/comparisons',
    'Only seven metal-nut anomaly images fall in the small-defect group.': 'metal_nut 的小瑕疵分組只有七張異常圖。',
    'The paired bootstrap compares one seed-0 fitted model pair per category and size.': '成對 bootstrap 對每個類別與尺寸，只比較一組 seed 0 模型。',
    'Three-seed standard deviations describe coreset variation, not population-level certainty.': '三個種子的標準差描述 coreset 變動，無法推論整體母群的確定性。',
    'Conclusion and limits': '結論與限制',
    'Scope: three MVTec AD categories and one frozen backbone': '研究範圍：三類 MVTec AD 資料與一個凍結的 backbone',
    'Layer2 gives the strongest overall small-defect localization in this study.': '在本研究中，layer2 的整體小瑕疵定位表現最好。',
    'Fusion gives no consistent benefit, including with equal 16 MiB banks.': '即使固定 16 MiB 記憶庫，融合仍沒有一致的收益。',
    'Layer3 is faster and stores fewer vectors in the 10% coreset condition.': '在 10% coreset 條件下，layer3 較快、儲存的向量也較少。',
    '320-pixel inputs improve localization while increasing latency and bank storage.': '320 像素改善定位，同時增加延遲與記憶庫容量。',
    'For inspection systems, layer2 is a practical starting point when localization matters most; layer3 trades accuracy for speed and storage.': '若檢測系統重視定位，可先評估 layer2；若更重視速度與容量，layer3 有取捨空間。',
    'Next: test more categories and backbones, and separate preprocessing effects from input-resolution gains.': '後續可擴充類別與 backbone，並分開檢驗前處理與解析度的影響。',
    'References and reproducibility': '參考文獻與重現資訊',
    'Full bibliography and methods: output/pdf/group6_patchcore_final_report.pdf': '完整書目與方法：output/pdf/group6_patchcore_final_report.pdf',
    'Code, compact results, and English report: github.com/bernie90103/CV_final_project': '程式、精簡結果與英文報告：github.com/bernie90103/CV_final_project',
    'Approach': '方法', 'Key idea': '核心做法', 'Connection to our study': '與本研究的關係',
    'Patch-feature distribution': '建立 patch 特徵分布', 'Another normal-only baseline': '另一種只用正常圖的基準',
    'Coreset + nearest neighbor': 'coreset 加最近鄰', 'Our fixed architecture': '本研究沿用的架構',
    'Multiscale teacher features': '多尺度教師特徵', 'Alternative feature use': '另一種特徵使用方式',
    'Feature-layer selection matters': '特徵層選擇會影響結果', 'Motivates layer comparison': '支持比較不同特徵層',
    'Low-latency anomaly detection': '低延遲異常偵測', 'Efficiency context': '提供效率比較背景',
    'Question': '問題', 'Comparison': '比較條件', 'What would support it?': '支持假設的結果',
    'layer2 vs layer3': 'layer2 與 layer3', 'Higher small-defect AUPRO for layer2': 'layer2 的小瑕疵 AUPRO 較高',
    'fusion vs single layers': '融合與單層特徵', 'Consistent localization gain from fusion': '融合有穩定定位增益',
    'equal 16 MiB banks': '相同 16 MiB 記憶庫', 'Fusion gain after matching vector storage': '容量相同後融合仍有增益',
    'Category': '類別', 'Normal train': '正常訓練圖', 'Normal test': '正常測試圖',
    'Small defects': '小瑕疵', 'Larger defects': '較大瑕疵',
    'Condition': '條件', 'Values': '設定',
    'Dataset': '資料集', 'screw, capsule, metal_nut; official train/test split': 'screw、capsule、metal_nut；官方訓練／測試分割',
    'Features': '特徵', 'layer2, layer3, fusion': 'layer2、layer3、融合',
    'Seeds': '種子', '0, 1, 2 for the coreset': 'coreset 種子 0、1、2',
    'Input size': '輸入尺寸', '224 and 320 pixels; resize + center crop': '224 與 320 像素；縮放後中心裁切',
    'Main bank': '主實驗記憶庫', '10% approximate greedy coreset: 54 runs': '10% 近似貪婪 coreset：54 次',
    'Matched bank': '固定容量記憶庫', '4096 × 1024 float32 vectors = 16 MiB: 27 runs': '4096 × 1024 個 float32 向量 = 16 MiB：27 次',
    'Layer2 category': 'layer2 類別', '224 AUPRO': '224 AUPRO', '320 AUPRO': '320 AUPRO',
    'Gain': '增量', 'Latency ratio': '延遲倍率',
    'Layer2 AUPRO': 'layer2 AUPRO', 'Fusion AUPRO': '融合 AUPRO',
    'Layer2 ms': 'layer2 毫秒', 'Fusion ms': '融合 毫秒',
}


def replace_text(tf, value, font='Microsoft JhengHei'):
    first = next((r for p in tf.paragraphs for r in p.runs), None)
    para = tf.paragraphs[0]
    size = (first.font.size if first is not None else None) or para.font.size or Pt(18)
    bold = first.font.bold if first is not None and first.font.bold is not None else para.font.bold
    align = para.alignment
    color = None
    try:
        color = first.font.color.rgb if first is not None else None
    except (AttributeError, TypeError):
        pass
    if color is None:
        try:
            color = para.font.color.rgb
        except (AttributeError, TypeError):
            pass
    tf.text = value
    for p in tf.paragraphs:
        p.alignment = align
        p.font.name = font
        p.font.size = size
        p.font.bold = bold
        if color is not None:
            p.font.color.rgb = color
        for r in p.runs:
            r.font.name = font
            r.font.size = size
            r.font.bold = bold
            if color is not None:
                r.font.color.rgb = color


def main():
    deck = Presentation(SOURCE)
    missing = set()
    for slide in deck.slides:
        for shape in slide.shapes:
            if shape.has_text_frame and shape.text:
                original = shape.text
                if original in T:
                    replace_text(shape.text_frame, T[original], 'Consolas' if original.startswith(('LAYERS =', 'def aupro')) else 'Microsoft JhengHei')
                elif original.isdigit() or original in ('→', 'Yang Cao  ·  Bernie Chen  ·  Celine Li') or original.startswith(('LAYERS =', 'def aupro', 'MVTec AD [1]', 'PatchCore [6]', '10% coreset', '224-pixel input', 'results/figures', '[1] Bergmann')):
                    continue
                else:
                    missing.add(original)
            if shape.has_table:
                for row in shape.table.rows:
                    for cell in row.cells:
                        original = cell.text
                        if original in T:
                            replace_text(cell.text_frame, T[original])
                        elif original.replace('.', '').replace('+', '').replace('×', '').isdigit() or original in ('screw','capsule','metal nut','PaDiM [3]','PatchCore [6]','Reverse Distillation [7]','Heckler et al. [8]','EfficientAD [9]','H1','H2','H3'):
                            continue
                        else:
                            missing.add(original)
    if missing:
        raise RuntimeError('Untranslated text: ' + repr(sorted(missing)))
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    deck.save(OUTPUT)
    print(f'{OUTPUT} ({len(deck.slides)} slides)')


if __name__ == '__main__':
    main()
