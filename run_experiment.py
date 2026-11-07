"""Build and evaluate one frozen-backbone PatchCore experiment."""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import subprocess
import time

# Keep all caches inside the project so the experiment is portable.
from study.io import ROOT, sha256, write_csv, write_json
os.environ.setdefault('TORCH_HOME', str(ROOT / '.cache/torch'))
os.environ.setdefault('MPLCONFIGDIR', str(ROOT / '.cache/matplotlib'))

import numpy as np
import torch
from torch.utils.data import DataLoader

from study.data import CATEGORIES, MVTecImages, audit_record, discover
from study.metrics import evaluate_groups
from study.model import LAYERS, VENDOR, make_model, resolve_device, seed_everything
from study.plots import save_examples


def synchronize(device):
    if device.type == 'cuda':
        torch.cuda.synchronize(device)


def dataset_fingerprint(records):
    # Content hashing detects replaced data even when names and counts agree.
    digest = hashlib.sha256()
    for r in records:
        digest.update(r.sample_id.encode())
        digest.update(sha256(r.path).encode())
        if r.mask:
            digest.update(sha256(r.mask).encode())
    return digest.hexdigest()


def source_fingerprint():
    paths = [ROOT / 'run_experiment.py', *sorted((ROOT / 'study').glob('*.py'))]
    return hashlib.sha256(''.join(sha256(p) for p in paths).encode()).hexdigest()


def run(args):
    if args.size < 32 or args.size % 16:
        raise ValueError('--size must be a multiple of 16 and >=32.')
    if not 0 < args.coreset_ratio < 1:
        raise ValueError('--coreset-ratio must be between 0 and 1.')
    if args.batch_size < 1 or args.threads < 1 or args.benchmark_repeats < 1 or args.warmup < 1:
        raise ValueError('Batch size, threads, warmup, and benchmark repeats must be positive.')
    if any(x is not None and x < 1 for x in (args.limit_train, args.limit_test_per_type, args.bank_vectors)):
        raise ValueError('Limits and bank vector count must be positive.')
    device = resolve_device(args.device)
    torch.set_num_threads(args.threads)
    train = discover(args.data, args.category, 'train')
    test = discover(args.data, args.category, 'test')
    if args.limit_train:
        train = train[:args.limit_train]
    if args.limit_test_per_type:
        test = [r for r in test if r in [x for x in test if x.defect_type == r.defect_type][:args.limit_test_per_type]]
    resize = args.resize or round(args.size * 256 / 224)
    if resize < args.size:
        raise ValueError('--resize must be at least --size.')
    debug = args.limit_train is not None or args.limit_test_per_type is not None
    config = {
        'category': args.category, 'layers': args.layers, 'seed': args.seed,
        'image_size': args.size, 'resize': resize, 'coreset_ratio': args.coreset_ratio,
        'bank_vectors_requested': args.bank_vectors, 'embedding_dim': args.embedding_dim,
        'batch_size': args.batch_size, 'threads': args.threads,
        'device': str(device), 'faiss_device': 'cpu', 'weights': 'IMAGENET1K_V1',
        'adaptive_pooling': 'official',
        'patch_size': 3, 'neighbors': 1, 'gaussian_sigma': 4,
        'limit_train': args.limit_train, 'limit_test_per_type': args.limit_test_per_type,
        'warmup': args.warmup, 'benchmark_repeats': args.benchmark_repeats,
        'aupro_fpr_limit': .3, 'region_connectivity': 8,
        'small_defect_threshold': .01, 'debug_subset': debug,
        'dataset_sha256': dataset_fingerprint(train + test), 'study_source_sha256': source_fingerprint(),
        'official_commit': subprocess.check_output(['git', '-C', str(VENDOR), 'rev-parse', 'HEAD'], text=True).strip(),
        'packages': {name: importlib.metadata.version(name) for name in ['torch','torchvision','timm','faiss-cpu','numpy','scipy','scikit-learn']},
        'system': platform.platform(),
    }
    tag = f'bank{args.bank_vectors}' if args.bank_vectors else f'ratio{args.coreset_ratio:g}'
    folder = args.output / ('debug' if debug else 'formal') / args.category / f'size{args.size}' / args.layers / tag / f'seed{args.seed}'
    if (folder / 'complete.json').exists():
        existing = json.loads((folder / 'config.json').read_text())
        if args.resume and existing == config:
            print(f'Already complete, config matches: {folder}', flush=True)
            return folder
        raise FileExistsError(f'{folder} already exists; use --resume for matching configs or a different --output.')
    if folder.exists() and any(folder.iterdir()):
        raise FileExistsError(f'Incomplete run at {folder}. Use a new --output or move this folder aside before retrying.')
    folder.mkdir(parents=True, exist_ok=True)
    write_json(folder / 'config.json', config)
    rows = [audit_record(r, resize, args.size) for r in test]
    write_json(folder / 'samples.json', rows)
    write_csv(folder / 'samples.csv', rows)
    print(f'Run: {folder}\nDevice: {device}; normal train={len(train)}, test={len(test)}', flush=True)
    train_data = MVTecImages(train, resize, args.size)
    test_data = MVTecImages(test, resize, args.size)
    loader = DataLoader(train_data, batch_size=args.batch_size, shuffle=False, num_workers=0)
    model = make_model(config, device)
    with torch.inference_mode():
        probe = train_data[0]['image'].unsqueeze(0).to(device)
        raw = model.forward_modules['feature_aggregator'](probe)
        shapes = {key: list(value.shape) for key, value in raw.items()}
    grid = shapes[LAYERS[args.layers][0]][-2:]
    n_candidates = len(train) * int(np.prod(grid))
    if args.bank_vectors:
        if args.bank_vectors >= n_candidates:
            raise ValueError(f'Budget must be smaller than {n_candidates} candidate vectors.')
        model.featuresampler.percentage = (args.bank_vectors + .5) / n_candidates
    if int(n_candidates * model.featuresampler.percentage) < 1:
        raise ValueError('Coreset would be empty; increase training data or the sampling ratio.')
    print(f'Feature grids: {shapes}; candidates={n_candidates}; retained≈{int(n_candidates * model.featuresampler.percentage)}', flush=True)
    # Reset after probing/initialization: seeds vary coreset sampling only.
    seed_everything(args.seed)
    synchronize(device)
    started = time.perf_counter()
    with torch.inference_mode():
        model.fit(loader)
    synchronize(device)
    fit_seconds = time.perf_counter() - started
    index = model.anomaly_scorer.nn_method.search_index
    (folder / 'model').mkdir(exist_ok=True)
    model.save_to_path(str(folder / 'model'))
    # Benchmark a deterministic spread of images. Loading and transforms are outside the timer.
    inputs = [test_data[i]['image'].unsqueeze(0) for i in np.linspace(0, len(test_data)-1, min(10, len(test_data)), dtype=int)]
    with torch.inference_mode():
        for i in range(args.warmup):
            model.predict(inputs[i % len(inputs)])
        synchronize(device)
        latency = []
        for i in range(args.benchmark_repeats):
            synchronize(device)
            start = time.perf_counter()
            model.predict(inputs[i % len(inputs)])
            synchronize(device)
            latency.append((time.perf_counter() - start) * 1000)
    scores, maps, masks = [], [], []
    for i in range(len(test_data)):
        item = test_data[i]
        with torch.inference_mode():
            score, heatmap = model.predict(item['image'].unsqueeze(0))
        scores.append(score[0])
        maps.append(heatmap[0])
        masks.append(item['mask'].numpy())
        if (i+1) % 25 == 0:
            print(f'Predicted {i+1}/{len(test_data)}', flush=True)
    scores, maps, masks = np.asarray(scores), np.asarray(maps, dtype=np.float32), np.asarray(masks, dtype=bool)
    np.savez_compressed(folder / 'predictions.npz', scores=scores, maps=maps, masks=masks,
                        sample_ids=np.array([r['sample_id'] for r in rows]))
    metrics = evaluate_groups(rows, scores, maps, masks)
    metrics['protocol'] = {'subgroups': 'Each subgroup includes all normal test images plus its anomalous images.',
                           'mask_space': 'resize + center crop; nearest neighbor masks',
                           'empty_masks': 'Retained and counted. AUPRO has no region contribution for vanished masks.',
                           'threshold_tuning': False}
    write_json(folder / 'metrics.json', metrics)
    model_files = list((folder / 'model').iterdir())
    runtime = {
        'feature_shapes': shapes, 'candidate_vectors': n_candidates,
        'bank_vectors': int(index.ntotal), 'embedding_dim': int(index.d),
        'bank_vector_bytes': int(index.ntotal * index.d * 4),
        'faiss_index_file_bytes': (folder / 'model/nnscorer_search_index.faiss').stat().st_size,
        'model_artifact_bytes': sum(p.stat().st_size for p in model_files),
        'fit_seconds': fit_seconds, 'median_latency_ms': float(np.median(latency)),
        'latency_ms': latency,
        'latency_scope': 'batch=1; includes host-to-device, backbone, CPU FAISS, upsample/smoothing; excludes disk I/O and preprocessing',
        'system': platform.platform(), 'processor': platform.processor(),
        'device_name': torch.cuda.get_device_name(device) if device.type == 'cuda' else platform.machine(),
        'packages': {name: importlib.metadata.version(name) for name in ['torch','torchvision','faiss-cpu','numpy','scipy','scikit-learn']},
    }
    write_json(folder / 'runtime.json', runtime)
    save_examples(test, rows, maps, resize, args.size, folder / 'examples')
    write_json(folder / 'complete.json', {'completed_utc': datetime.now(timezone.utc).isoformat(), 'debug_subset': debug})
    print(json.dumps({'metrics': metrics, 'median_latency_ms': runtime['median_latency_ms'], 'bank_MiB': runtime['bank_vector_bytes']/2**20}, indent=2), flush=True)
    return folder


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--data', type=Path, default=Path('data/mvtec'))
    p.add_argument('--category', choices=CATEGORIES, default='screw')
    p.add_argument('--layers', choices=LAYERS, default='fusion')
    p.add_argument('--size', type=int, default=224)
    p.add_argument('--resize', type=int)
    p.add_argument('--seed', type=int, default=0)
    p.add_argument('--coreset-ratio', type=float, default=.1)
    p.add_argument('--bank-vectors', type=int)
    p.add_argument('--embedding-dim', type=int, default=1024)
    p.add_argument('--batch-size', type=int, default=4)
    p.add_argument('--threads', type=int, default=4)
    p.add_argument('--device', default='auto')
    p.add_argument('--warmup', type=int, default=10)
    p.add_argument('--benchmark-repeats', type=int, default=30)
    p.add_argument('--limit-train', type=int)
    p.add_argument('--limit-test-per-type', type=int)
    p.add_argument('--output', type=Path, default=Path('results/runs'))
    p.add_argument('--resume', action='store_true')
    return p


if __name__ == '__main__':
    run(parser().parse_args())
