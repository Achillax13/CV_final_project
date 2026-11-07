"""Aggregate completed formal runs; never mix debug runs into report tables."""
import argparse
from collections import defaultdict
import json
from pathlib import Path

from study.io import write_csv, write_json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np



def summarize(root, output):
    rows = []
    for complete in sorted(Path(root).rglob('complete.json')):
        folder = complete.parent
        config = json.loads((folder / 'config.json').read_text())
        if config['debug_subset']:
            continue
        metrics = json.loads((folder / 'metrics.json').read_text())
        runtime = json.loads((folder / 'runtime.json').read_text())
        for group in ['all', 'small', 'large']:
            rows.append({
                'category': config['category'], 'image_size': config['image_size'],
                'layers': config['layers'], 'seed': config['seed'],
                'budget': f"bank{config['bank_vectors_requested']}" if config['bank_vectors_requested'] else f"ratio{config['coreset_ratio']:g}",
                'group': group, **metrics[group],
                'bank_MiB': runtime['bank_vector_bytes'] / 2**20,
                'median_latency_ms': runtime['median_latency_ms'],
                'device': config['device'], 'system': runtime['system'],
                'dataset_sha256': config['dataset_sha256'], 'study_source_sha256': config['study_source_sha256'],
            })
    if not rows:
        print('No completed formal runs found. Debug subset runs are excluded.')
        return []
    keys = ['category','image_size','layers','budget','group','device','system','dataset_sha256','study_source_sha256']
    buckets = defaultdict(list)
    for row in rows:
        buckets[tuple(row[k] for k in keys)].append(row)
    summary = []
    for key, values in buckets.items():
        if len({r['seed'] for r in values}) != len(values):
            raise ValueError(f'Duplicate seeds in aggregate {key}; narrow --root to one study.')
        row = dict(zip(keys, key))
        row.update(n_seeds=len(values), seeds=','.join(str(r['seed']) for r in values),
                   n_normal=values[0]['n_normal'], n_anomaly=values[0]['n_anomaly'])
        for metric in ['aupro','pixel_auroc','image_auroc','bank_MiB','median_latency_ms']:
            data = [r[metric] for r in values if r[metric] is not None]
            row[metric + '_mean'] = float(np.mean(data)) if data else None
            row[metric + '_std'] = float(np.std(data, ddof=1)) if len(data) > 1 else None
        summary.append(row)
    output = Path(output)
    write_csv(output / 'per_seed.csv', rows)
    write_csv(output / 'mean_std.csv', summary)
    write_json(output / 'summary.json', summary)
    # Separate panels prevent different categories or resolutions being conflated.
    panels = sorted({(r['category'], r['image_size'], r['budget']) for r in summary})
    for category, size, budget in panels:
        fig, ax = plt.subplots(figsize=(6,4))
        for row in summary:
            if (row['category'],row['image_size'],row['budget'],row['group']) != (category,size,budget,'small'):
                continue
            if row['aupro_mean'] is not None:
                ax.errorbar(row['bank_MiB_mean'], row['aupro_mean'], yerr=row['aupro_std'] or 0, fmt='o', capsize=3)
                ax.annotate(row['layers'], (row['bank_MiB_mean'],row['aupro_mean']), xytext=(4,4), textcoords='offset points')
        ax.set(xlabel='Memory bank (MiB)',ylabel='Small-defect AUPRO@0.3',title=f'{category}, input {size}, {budget}',ylim=(0,1.03))
        fig.tight_layout()
        fig.savefig(output / f'{category}_{size}_{budget}_tradeoff.png', dpi=160)
        plt.close(fig)
    print(f'Summarized {len(rows)//3} formal runs into {output}')
    return summary


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, default=Path('results/runs'))
    p.add_argument('--output', type=Path, default=Path('results/summary'))
    a = p.parse_args()
    summarize(a.root,a.output)
