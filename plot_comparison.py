"""Place the same test image's heatmaps from several completed runs side by side."""
import argparse
import json
import os
from pathlib import Path

from study.io import ROOT
os.environ.setdefault('MPLCONFIGDIR',str(ROOT/'.cache/matplotlib'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

from study.data import discover,geometry,load_pair


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--runs',nargs='+',type=Path,required=True)
    p.add_argument('--sample-id')
    p.add_argument('--data',type=Path,default=Path('data/mvtec'))
    p.add_argument('--output',type=Path,default=Path('results/comparison.png'))
    a=p.parse_args()
    configs=[json.loads((r/'config.json').read_text()) for r in a.runs]
    manifests=[json.loads((r/'samples.json').read_text()) for r in a.runs]
    sample_id=a.sample_id or next(r['sample_id'] for r in manifests[0] if r['group']=='small')
    if len({c['category'] for c in configs}) != 1:
        raise ValueError('Choose runs of the same category.')
    record=next(r for r in discover(a.data,configs[0]['category'],'test') if r.sample_id==sample_id)
    image,mask=load_pair(record)
    image,mask=geometry(image,mask,configs[0]['resize'],configs[0]['image_size'])
    fig,axes=plt.subplots(1,len(a.runs)+2,figsize=(3*(len(a.runs)+2),3))
    axes[0].imshow(image)
    axes[0].set_title('Input')
    axes[1].imshow(mask,cmap='gray')
    axes[1].set_title('Ground truth')
    for ax,run,config,rows in zip(axes[2:],a.runs,configs,manifests):
        index=next(i for i,row in enumerate(rows) if row['sample_id']==sample_id)
        with np.load(run/'predictions.npz',allow_pickle=False) as data:
            if data['sample_ids'][index] != sample_id:
                raise ValueError('Prediction ordering mismatch.')
            heatmap=data['maps'][index]
        ax.imshow(heatmap,cmap='inferno')
        ax.set_title(f"{config['layers']} / {config['image_size']}")
    for ax in axes:
        ax.axis('off')
    fig.suptitle(f'{sample_id}\nColors scaled per panel for viewing; metrics use raw scores.',fontsize=9)
    fig.tight_layout()
    a.output.parent.mkdir(parents=True,exist_ok=True)
    fig.savefig(a.output,dpi=160)
    plt.close(fig)
    print(a.output)
