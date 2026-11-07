"""Exact tied-threshold ROC/PRO curves; no test-set threshold optimization.

AUPRO integrates average connected-region recall against global background FPR.
Regions use 8-connectivity. Area is clipped at FPR=.3 and divided by .3.
The algorithm sorts continuous scores and treats equal scores as one threshold.
"""
import numpy as np
from scipy import ndimage
from sklearn.metrics import roc_auc_score


def safe_auroc(labels, scores):
    labels, scores = np.asarray(labels), np.asarray(scores)
    if not np.isfinite(scores).all():
        raise ValueError('Non-finite anomaly scores.')
    return float(roc_auc_score(labels, scores)) if len(np.unique(labels)) == 2 else None


def pro_curve(masks, maps):
    masks, maps = np.asarray(masks, dtype=bool), np.asarray(maps)
    if masks.shape != maps.shape or masks.ndim != 3:
        raise ValueError('Masks and anomaly maps must have identical [N,H,W] shapes.')
    if not np.isfinite(maps).all():
        raise ValueError('Non-finite anomaly maps.')
    n_background = int((~masks).sum())
    weights = np.zeros(masks.shape, dtype=np.float64)
    n_regions = 0
    for i, mask in enumerate(masks):
        regions, count = ndimage.label(mask, structure=np.ones((3, 3)))
        sizes = np.bincount(regions.ravel())
        inverse = np.zeros(len(sizes), dtype=np.float64)
        inverse[1:] = 1.0 / sizes[1:]
        weights[i] = inverse[regions]
        n_regions += count
    if not n_regions or not n_background:
        return None
    order = np.argsort(-maps.ravel(), kind='stable')
    values = maps.ravel()[order]
    # Include a tied score only after every pixel with that score enters the set.
    endpoints = np.r_[np.flatnonzero(values[:-1] != values[1:]), len(values) - 1]
    fpr = np.cumsum((~masks).ravel()[order], dtype=np.float64)[endpoints] / n_background
    pro = np.cumsum(weights.ravel()[order], dtype=np.float64)[endpoints] / n_regions
    return np.r_[0.0, fpr], np.r_[0.0, pro]


def aupro(masks, maps, fpr_limit=.3):
    if not 0 < fpr_limit <= 1:
        raise ValueError('fpr_limit must be in (0,1].')
    curve = pro_curve(masks, maps)
    if curve is None:
        return None
    x, y = curve
    # Keep vertical segments; collapsing duplicate FPR values changes the area.
    right = int(np.searchsorted(x, fpr_limit, side='right'))
    clipped_x, clipped_y = x[:right], y[:right]
    if clipped_x[-1] < fpr_limit:
        value = np.interp(fpr_limit, x[right-1:right+1], y[right-1:right+1])
        clipped_x = np.r_[clipped_x, fpr_limit]
        clipped_y = np.r_[clipped_y, value]
    return float(np.clip(np.trapezoid(clipped_y, clipped_x) / fpr_limit, 0, 1))


def evaluate_groups(rows, scores, maps, masks, fpr_limit=.3):
    labels = np.array([r['is_anomaly'] for r in rows])
    groups = np.array([r['group'] for r in rows])
    result = {}
    for group in ('all', 'small', 'large'):
        selected = np.ones(len(rows), dtype=bool) if group == 'all' else ((groups == group) | (groups == 'normal'))
        positives = selected & (labels == 1)
        if not np.any(positives):
            result[group] = {'n_normal': int((selected & (labels == 0)).sum()), 'n_anomaly': 0,
                             'image_auroc': None, 'pixel_auroc': None, 'aupro': None,
                             'n_anomaly_empty_transformed_mask': 0}
            continue
        current_masks, current_maps = masks[selected], maps[selected]
        result[group] = {
            'n_normal': int((selected & (labels == 0)).sum()), 'n_anomaly': int(positives.sum()),
            'n_anomaly_empty_transformed_mask': int(sum(
                not np.any(masks[i]) for i in np.flatnonzero(positives))),
            'image_auroc': safe_auroc(labels[selected], scores[selected]),
            'pixel_auroc': safe_auroc(current_masks.ravel(), current_maps.ravel()),
            'aupro': aupro(current_masks, current_maps, fpr_limit),
        }
    return result
