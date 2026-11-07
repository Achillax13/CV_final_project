"""Audit original defect areas and preprocessing before model evaluation."""
import argparse
from collections import Counter
from pathlib import Path

from study.io import write_csv, write_json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from study.data import CATEGORIES, audit_record, discover


def inspect(data, categories, size, resize, output):
    rows = []
    for category in categories:
        for split in ('train', 'test'):
            rows.extend(audit_record(r, resize, size) for r in discover(data, category, split))
    summaries = []
    fig, axes = plt.subplots(1, len(categories), figsize=(5 * len(categories), 4), squeeze=False)
    for ax, category in zip(axes[0], categories):
        test = [r for r in rows if r['category'] == category and r['split'] == 'test']
        defects = [r for r in test if r['is_anomaly']]
        counts = Counter(r['group'] for r in test)
        summaries.append({
            'category': category, 'image_size': size, 'resize': resize,
            'n_train_normal': sum(r['category'] == category and r['split'] == 'train' for r in rows),
            'n_test_normal': counts['normal'], 'n_test_small': counts['small'], 'n_test_large': counts['large'],
            'n_crop_removed_defect': sum(r['cropped_defect_pixels'] > 0 for r in defects),
            'n_lost_all_after_transform': sum(r['lost_all_after_transform'] for r in defects),
        })
        ax.hist([r['original_area_ratio'] * 100 for r in defects], bins=20, edgecolor='white')
        ax.axvline(1, color='red', linestyle='--', label='Small defect cutoff: 1%')
        ax.set(title=category, xlabel='Original annotated area (%)', ylabel='Image count')
        ax.legend(fontsize=8)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(output / 'defect_area_histograms.png', dpi=160)
    plt.close(fig)
    write_csv(output / 'samples.csv', rows)
    write_csv(output / 'summary.csv', summaries)
    write_json(output / 'audit.json', {'image_size': size, 'resize': resize, 'summary': summaries, 'samples': rows})
    for summary in summaries:
        print(summary)
    return rows


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--data', type=Path, default=Path('data/mvtec'))
    p.add_argument('--categories', nargs='+', choices=CATEGORIES, default=list(CATEGORIES))
    p.add_argument('--size', type=int, default=224)
    p.add_argument('--resize', type=int)
    p.add_argument('--output', type=Path)
    a = p.parse_args()
    inspect(a.data, a.categories, a.size, a.resize or round(a.size * 256 / 224),
            a.output or Path(f'results/audit/size{a.size}'))


if __name__ == '__main__':
    main()
