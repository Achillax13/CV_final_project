"""Create a heatmap for one image using a completed experiment's memory bank."""
import argparse
import json
import os
from pathlib import Path

from study.io import ROOT, write_json
os.environ.setdefault('TORCH_HOME',str(ROOT/'.cache/torch'))
os.environ.setdefault('MPLCONFIGDIR',str(ROOT/'.cache/matplotlib'))

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image
import torch
from torchvision.transforms import functional as TF

from study.data import geometry
from study.model import make_model,resolve_device


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run',type=Path,required=True)
    p.add_argument('--image',type=Path,required=True)
    p.add_argument('--device',default='auto')
    p.add_argument('--output',type=Path,default=Path('results/demo'))
    args=p.parse_args()
    if not (args.run/'complete.json').exists():
        raise ValueError('Select a completed run.')
    config=json.loads((args.run/'config.json').read_text())
    device=resolve_device(args.device)
    torch.set_num_threads(config['threads'])
    model=make_model(config,device)
    model.anomaly_scorer.load(str(args.run/'model'))
    with Image.open(args.image) as f:
        image=f.convert('RGB')
    image,_=geometry(image,Image.new('L',image.size),config['resize'],config['image_size'])
    tensor=TF.normalize(TF.to_tensor(image),[.485,.456,.406],[.229,.224,.225]).unsqueeze(0)
    with torch.inference_mode():
        scores,maps=model.predict(tensor)
    args.output.mkdir(parents=True,exist_ok=True)
    np.save(args.output/'anomaly_map.npy',maps[0])
    fig,axes=plt.subplots(1,3,figsize=(10,3))
    axes[0].imshow(image)
    axes[1].imshow(maps[0],cmap='inferno')
    axes[2].imshow(image)
    axes[2].imshow(maps[0],cmap='inferno',alpha=.5)
    for ax,title in zip(axes,['Preprocessed input','Anomaly map','Overlay']):
        ax.set_title(title)
        ax.axis('off')
    fig.suptitle(f'Uncalibrated anomaly score: {scores[0]:.4f}')
    fig.tight_layout()
    fig.savefig(args.output/'prediction.png',dpi=160)
    plt.close(fig)
    result={'image':str(args.image),'run':str(args.run),'score':float(scores[0]),
            'debug_model':config['debug_subset'],'decision':'No binary threshold calibrated; score is not a probability.'}
    write_json(args.output/'prediction.json',result)
    print(json.dumps(result,indent=2))
