"""Use the unmodified, pinned official PatchCore core through its Python API."""
import random
import sys

import numpy as np
import torch
from torchvision.models import Wide_ResNet50_2_Weights, wide_resnet50_2

from study.io import ROOT

VENDOR = ROOT / 'vendor/patchcore-inspection'
sys.path.insert(0, str(VENDOR / 'src'))
from patchcore.patchcore import PatchCore  # noqa: E402
from patchcore.common import FaissNN  # noqa: E402
from patchcore.sampler import ApproximateGreedyCoresetSampler  # noqa: E402

LAYERS = {'layer2': ['layer2'], 'layer3': ['layer3'], 'fusion': ['layer2', 'layer3']}


def seed_everything(seed):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
        torch.backends.cuda.matmul.allow_tf32 = False
        torch.backends.cudnn.allow_tf32 = False
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True


def resolve_device(requested):
    if requested == 'auto':
        return torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    device = torch.device(requested)
    if device.type not in ('cpu', 'cuda'):
        raise ValueError('Use auto, cpu, or cuda.')
    if device.type == 'cuda' and not torch.cuda.is_available():
        raise ValueError('CUDA is unavailable. Install a CUDA-enabled PyTorch build or use --device cpu.')
    return device


def make_model(config, device):
    seed_everything(0)  # Backbone construction must not alter coreset seed comparisons.
    backbone = wide_resnet50_2(weights=Wide_ResNet50_2_Weights.IMAGENET1K_V1)
    backbone.eval().requires_grad_(False)
    backbone.name = 'wideresnet50'
    sampler = ApproximateGreedyCoresetSampler(config['coreset_ratio'], device)
    model = PatchCore(device)
    model.load(
        backbone=backbone, layers_to_extract_from=LAYERS[config['layers']],
        device=device, input_shape=(3, config['image_size'], config['image_size']),
        pretrain_embed_dimension=config['embedding_dim'], target_embed_dimension=config['embedding_dim'],
        patchsize=3, anomaly_score_num_nn=1,
        featuresampler=sampler, nn_method=FaissNN(False, config['threads']),
    )
    model.eval()
    seed_everything(config['seed'])
    return model
