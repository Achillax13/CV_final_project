"""Cache and hash-check the official torchvision ImageNet V1 backbone weights."""
import os
from pathlib import Path

from study.io import ROOT, sha256, write_json
os.environ.setdefault('TORCH_HOME', str(ROOT / '.cache/torch'))

import torch
from torchvision.models import Wide_ResNet50_2_Weights, wide_resnet50_2


if __name__ == '__main__':
    weights = Wide_ResNet50_2_Weights.IMAGENET1K_V1
    wide_resnet50_2(weights=weights)
    path = Path(torch.hub.get_dir()) / 'checkpoints' / weights.url.rsplit('/', 1)[1]
    digest = sha256(path)
    expected = path.stem.rsplit('-', 1)[1]
    if not digest.startswith(expected):
        raise ValueError('The cached weight file does not match its official hash prefix.')
    write_json(ROOT / '.cache/weights.json', {'url': weights.url, 'sha256': digest, 'weights': weights.name})
    print(f'Weights verified: {path}')
