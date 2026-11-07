"""Run the predeclared experiment matrix sequentially on one machine."""
import argparse
import itertools
from pathlib import Path
import subprocess
import sys


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--data', type=Path, default=Path('data/mvtec'))
    p.add_argument('--categories', nargs='+', choices=['screw','capsule','metal_nut'], default=['screw','capsule','metal_nut'])
    p.add_argument('--sizes', nargs='+', type=int, default=[224])
    p.add_argument('--layers', nargs='+', choices=['layer2','layer3','fusion'], default=['layer2','layer3','fusion'])
    p.add_argument('--seeds', nargs='+', type=int, default=[0,1,2])
    p.add_argument('--device', default='auto')
    p.add_argument('--bank-vectors', type=int)
    p.add_argument('--output', type=Path, default=Path('results/runs'))
    p.add_argument('--dry-run', action='store_true')
    a = p.parse_args()
    combinations = list(itertools.product(a.categories, a.sizes, a.layers, a.seeds))
    print(f'{len(combinations)} experiments; sequential execution; matching completed runs are skipped.', flush=True)
    for i, (category, size, layer, seed) in enumerate(combinations, 1):
        command = [sys.executable, 'run_experiment.py', '--data', str(a.data), '--category', category,
                   '--size', str(size), '--layers', layer, '--seed', str(seed),
                   '--device', a.device, '--output', str(a.output), '--resume']
        if a.bank_vectors:
            command += ['--bank-vectors', str(a.bank_vectors)]
        print(f'[{i}/{len(combinations)}] ' + ' '.join(command), flush=True)
        if not a.dry_run:
            subprocess.run(command, check=True, cwd=Path(__file__).resolve().parent)


if __name__ == '__main__':
    main()
