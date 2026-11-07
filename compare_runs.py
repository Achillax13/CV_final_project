"""Paired image bootstrap for AUPRO differences between two completed runs.

Exact AUPRO point estimates come from saved predictions. Bootstrap uses 4096
fixed score bins per model to avoid re-sorting millions of pixels 1000 times.
Every resample uses the same image multiplicities for both models. Sampling is
stratified by the original normal/small/large groups. This interval describes
test-image sampling uncertainty for one pair of fitted models, not seed variance.
"""
import argparse
import json
from pathlib import Path

import numpy as np
from scipy import ndimage

from study.io import write_json
from study.metrics import aupro


def integrate(x, y, limit=.3):
    x, y = np.r_[0.0,x], np.r_[0.0,y]
    right = np.searchsorted(x,limit,side='right')
    xx, yy = x[:right], y[:right]
    if xx[-1] < limit:
        yy = np.r_[yy,np.interp(limit,x[right-1:right+1],y[right-1:right+1])]
        xx = np.r_[xx,limit]
    return float(np.clip(np.trapezoid(yy,xx)/limit,0,1))


def sufficient_statistics(masks, maps, bins):
    if bins < 64:
        raise ValueError('Use at least 64 bins.')
    low, high = float(maps.min()), float(maps.max())
    edges = np.linspace(low, high if high > low else low+1, bins+1)
    backgrounds, overlaps, regions = [], [], []
    for mask, heatmap in zip(masks,maps):
        labels, count = ndimage.label(mask,structure=np.ones((3,3)))
        sizes = np.bincount(labels.ravel())
        inverse = np.zeros(len(sizes),dtype=float)
        inverse[1:] = 1/sizes[1:]
        weights = inverse[labels]
        backgrounds.append(np.histogram(heatmap[~mask],bins=edges)[0][::-1])
        overlaps.append(np.histogram(heatmap,bins=edges,weights=weights)[0][::-1])
        regions.append(count)
    return np.array(backgrounds,dtype=float),np.array(overlaps),np.array(regions)


def curve_from_counts(counts, stats):
    bg, overlap, regions = stats
    total_regions = counts @ regions
    bg_hist, overlap_hist = counts @ bg, counts @ overlap
    if total_regions == 0 or bg_hist.sum() == 0:
        return None
    return integrate(np.cumsum(bg_hist)/bg_hist.sum(),np.cumsum(overlap_hist)/total_regions)


def paired_bootstrap(rows, data_a, data_b, repeats=1000, bins=4096, seed=2026):
    if repeats < 100:
        raise ValueError('Use at least 100 bootstrap repetitions.')
    groups = np.array([r['group'] for r in rows])
    all_stats = [sufficient_statistics(d['masks'],d['maps'],bins) for d in [data_a,data_b]]
    rng = np.random.default_rng(seed)
    results = {}
    for group in ['all','small','large']:
        selected = np.flatnonzero(np.ones(len(rows),bool) if group == 'all' else ((groups == group)|(groups == 'normal')))
        n_normal = int((groups[selected] == 'normal').sum())
        n_anomaly = len(selected)-n_normal
        if n_normal < 5 or n_anomaly < 10:
            results[group] = {'status': 'insufficient_samples', 'n_normal': n_normal, 'n_anomaly': n_anomaly}
            continue
        stats = [tuple(x[selected] for x in s) for s in all_stats]
        base_counts = np.ones(len(selected),dtype=int)
        binned = [curve_from_counts(base_counts,s) for s in stats]
        exact = [aupro(d['masks'][selected],d['maps'][selected]) for d in [data_a,data_b]]
        if any(v is None for v in binned+exact):
            results[group] = {'status':'no_valid_transformed_regions'}
            continue
        strata = [np.flatnonzero(groups[selected] == g) for g in ['normal','small','large']]
        differences = []
        for _ in range(repeats):
            counts = np.zeros(len(selected),dtype=int)
            for stratum in strata:
                if len(stratum):
                    counts += np.bincount(rng.choice(stratum,len(stratum),replace=True),minlength=len(selected))
            values = [curve_from_counts(counts,s) for s in stats]
            if all(v is not None for v in values):
                differences.append(values[1]-values[0])
        error = max(abs(x-y) for x,y in zip(exact,binned))
        results[group] = {
            'status': 'ok' if error <= .005 else 'increase_bins_before_interpreting_interval',
            'n_normal': n_normal, 'n_anomaly': n_anomaly,
            'exact_aupro_a': exact[0], 'exact_aupro_b': exact[1], 'exact_difference_b_minus_a': exact[1]-exact[0],
            'binned_point_estimates': binned, 'max_point_approximation_error': error,
            'ci95_b_minus_a': np.quantile(differences,[.025,.975]).tolist() if len(differences) >= repeats*.95 else None,
            'valid_repeats': len(differences),
        }
    return {'repeats':repeats,'bins':bins,'seed':seed,'method':'paired stratified image percentile bootstrap; binned AUPRO@0.3',
            'direction':'B minus A; positive favors B','groups':results}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('a',type=Path)
    p.add_argument('b',type=Path)
    p.add_argument('--repeats',type=int,default=1000)
    p.add_argument('--bins',type=int,default=4096)
    p.add_argument('--output',type=Path,default=Path('results/comparisons/paired_bootstrap.json'))
    p.add_argument('--allow-debug',action='store_true')
    args=p.parse_args()
    configs,rows,data=[],[],[]
    for path in [args.a,args.b]:
        if not (path/'complete.json').exists():
            raise ValueError(f'Run is not complete: {path}')
        configs.append(json.loads((path/'config.json').read_text()))
        rows.append(json.loads((path/'samples.json').read_text()))
        with np.load(path/'predictions.npz',allow_pickle=False) as f:
            if f['sample_ids'].tolist() != [r['sample_id'] for r in rows[-1]]:
                raise ValueError('Prediction IDs disagree with the sample manifest.')
            data.append({key:f[key] for key in ['masks','maps']})
    if not args.allow_debug and any(c['debug_subset'] for c in configs):
        raise ValueError('Debug runs require --allow-debug and must not be used in the final report.')
    for key in ['category','dataset_sha256','study_source_sha256']:
        if configs[0][key] != configs[1][key]:
            raise ValueError(f'Runs differ in {key}; pairing is invalid.')
    if [(r['sample_id'],r['group']) for r in rows[0]] != [(r['sample_id'],r['group']) for r in rows[1]]:
        raise ValueError('Runs have different image IDs, ordering, or original-area groups.')
    result=paired_bootstrap(rows[0],data[0],data[1],args.repeats,args.bins)
    result.update(run_a=str(args.a),run_b=str(args.b),debug_subset=any(c['debug_subset'] for c in configs))
    write_json(args.output,result)
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    main()
