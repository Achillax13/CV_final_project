"""MVTec splits, original-area groups, and a shared image/mask geometry."""
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import torch
from PIL import Image
from torch.utils.data import Dataset
from torchvision.transforms import InterpolationMode
from torchvision.transforms import functional as TF


CATEGORIES = ('screw', 'capsule', 'metal_nut')


@dataclass(frozen=True)
class Record:
    path: Path
    mask: Path | None
    category: str
    split: str
    defect_type: str
    sample_id: str

    @property
    def anomalous(self):
        return self.defect_type != 'good'


def discover(root, category, split):
    if split not in ('train', 'test'):
        raise ValueError('Split must be train or test.')
    base = Path(root) / category
    folder = base / split
    if not folder.is_dir():
        raise FileNotFoundError(f'Missing {folder}. See README.md for the dataset layout.')
    records = []
    for path in sorted(folder.glob('*/*.png')):
        defect = path.parent.name
        if split == 'train' and defect != 'good':
            raise ValueError(f'Training must contain only normal images: {path}')
        mask = base / 'ground_truth' / defect / f'{path.stem}_mask.png' if defect != 'good' else None
        if mask is not None and not mask.is_file():
            raise FileNotFoundError(f'Missing mask for {path}: {mask}')
        records.append(Record(path, mask, category, split, defect, path.relative_to(Path(root)).as_posix()))
    if not records:
        raise ValueError(f'No PNG images in {folder}')
    return records


def load_pair(record):
    with Image.open(record.path) as f:
        image = f.convert('RGB')
    if record.mask:
        with Image.open(record.mask) as f:
            mask = f.convert('L')
        if mask.size != image.size:
            raise ValueError(f'Image/mask dimensions differ: {record.sample_id}')
        if not np.any(np.asarray(mask) > 0):
            raise ValueError(f'Anomalous image has an empty original mask: {record.sample_id}')
    else:
        mask = Image.new('L', image.size, 0)
    mask = Image.fromarray((np.asarray(mask) > 0).astype('uint8') * 255)
    return image, mask


def geometry(image, mask, resize, size):
    if resize < size or size < 1:
        raise ValueError('Require resize >= image size > 0.')
    image = TF.resize(image, resize, interpolation=InterpolationMode.BILINEAR, antialias=True)
    mask = TF.resize(mask, resize, interpolation=InterpolationMode.NEAREST)
    return TF.center_crop(image, size), TF.center_crop(mask, size)


def audit_record(record, resize, size):
    image, mask = load_pair(record)
    original = np.asarray(mask) > 0
    ratio = float(original.mean())
    group = 'normal' if not record.anomalous else ('small' if ratio <= .01 else 'large')
    resized = TF.resize(mask, resize, interpolation=InterpolationMode.NEAREST)
    cropped = TF.center_crop(resized, size)
    before = int(np.count_nonzero(np.asarray(resized)))
    after = int(np.count_nonzero(np.asarray(cropped)))
    return {
        'sample_id': record.sample_id, 'category': record.category,
        'split': record.split, 'defect_type': record.defect_type,
        'is_anomaly': int(record.anomalous), 'group': group,
        'width': image.width, 'height': image.height,
        'original_defect_pixels': int(original.sum()), 'original_area_ratio': ratio,
        'resize': resize, 'image_size': size,
        'resized_defect_pixels': before, 'transformed_defect_pixels': after,
        'cropped_defect_pixels': before - after,
        'crop_removed_fraction': (before - after) / before if before else 0.0,
        'lost_all_after_transform': bool(record.anomalous and after == 0),
        'lost_during_resize': bool(record.anomalous and before == 0),
    }


class MVTecImages(Dataset):
    def __init__(self, records, resize=256, size=224):
        self.records, self.resize, self.size = records, resize, size

    def __len__(self):
        return len(self.records)

    def __getitem__(self, index):
        record = self.records[index]
        image, mask = load_pair(record)
        image, mask = geometry(image, mask, self.resize, self.size)
        image = TF.normalize(TF.to_tensor(image), [.485, .456, .406], [.229, .224, .225])
        return {
            'image': image,
            'mask': torch.from_numpy((np.asarray(mask) > 0).copy()),
            'is_anomaly': int(record.anomalous), 'sample_id': record.sample_id,
        }
