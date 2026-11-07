"""Recompute exact metrics from a saved run without rebuilding its model."""
import argparse
import json
from pathlib import Path

import numpy as np

from study.io import write_json
from study.metrics import evaluate_groups


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('run', type=Path)
    p.add_argument('--output', type=Path)
    a = p.parse_args()
    rows = json.loads((a.run / 'samples.json').read_text())
    with np.load(a.run / 'predictions.npz', allow_pickle=False) as data:
        if data['sample_ids'].tolist() != [r['sample_id'] for r in rows]:
            raise ValueError('Prediction/sample ordering mismatch.')
        result = evaluate_groups(rows, data['scores'], data['maps'], data['masks'])
    print(json.dumps(result, indent=2))
    if a.output:
        write_json(a.output, result)
