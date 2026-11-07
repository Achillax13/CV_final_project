from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

from study.data import geometry, load_pair


def save_examples(records, rows, maps, resize, size, output, limit=9):
    """Deterministic examples chosen by ID and group, never by model performance."""
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    selected = []
    per_group = max(1, limit // 3)
    for group in ('normal', 'small', 'large'):
        selected.extend([i for i, r in enumerate(rows) if r['group'] == group][:per_group])
    low, high = float(np.min(maps)), float(np.max(maps))
    for i in selected[:limit]:
        image, mask = load_pair(records[i])
        image, mask = geometry(image, mask, resize, size)
        fig, axes = plt.subplots(1, 4, figsize=(12, 3))
        axes[0].imshow(image)
        axes[1].imshow(mask, cmap='gray', vmin=0, vmax=255)
        axes[2].imshow(maps[i], cmap='inferno', vmin=low, vmax=high)
        axes[3].imshow(image)
        axes[3].imshow(maps[i], cmap='inferno', alpha=.5, vmin=low, vmax=high)
        for ax, title in zip(axes, ['Input', 'Ground truth', 'Anomaly map', 'Overlay']):
            ax.set_title(title)
            ax.axis('off')
        fig.suptitle(f"{rows[i]['sample_id']} | group={rows[i]['group']}", fontsize=9)
        fig.tight_layout()
        fig.savefig(output / f'{i:04d}_{rows[i]["group"]}.png', dpi=130)
        plt.close(fig)
