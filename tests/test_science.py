"""Scientific correctness checks for masks, subgroup denominators, and PRO."""
from pathlib import Path
import tempfile
import unittest

import numpy as np
from PIL import Image
from scipy import ndimage

from compare_runs import curve_from_counts, sufficient_statistics
from study.data import Record, audit_record, geometry
from study.metrics import aupro, evaluate_groups


def reference_aupro(masks,scores,limit=.3):
    components=[]
    for mask in masks:
        labels,n=ndimage.label(mask,structure=np.ones((3,3)))
        components.append((labels,n))
    points=[(0.,0.)]
    for threshold in sorted(np.unique(scores),reverse=True):
        predicted=scores >= threshold
        fpr=predicted[~masks].mean()
        overlaps=[]
        for i,(labels,n) in enumerate(components):
            for label in range(1,n+1):
                overlaps.append(predicted[i][labels==label].mean())
        points.append((float(fpr),float(np.mean(overlaps))))
    area=0
    for (x1,y1),(x2,y2) in zip(points[:-1],points[1:]):
        if x1 >= limit:
            break
        if x2 > limit:
            y2=y1+(y2-y1)*(limit-x1)/(x2-x1)
            x2=limit
        area+=(x2-x1)*(y1+y2)/2
    return area/limit


class ScientificMetrics(unittest.TestCase):
    def setUp(self):
        self.masks=np.zeros((2,6,6),bool)
        self.masks[0,1,1]=True
        self.masks[1,1:4,1:4]=True

    def test_perfect_inverted_and_tied_scores(self):
        self.assertAlmostEqual(aupro(self.masks,self.masks.astype(float)),1)
        self.assertAlmostEqual(aupro(self.masks,(~self.masks).astype(float)),0)
        self.assertAlmostEqual(aupro(self.masks,np.ones(self.masks.shape)),.15)

    def test_exact_tied_thresholds_against_independent_region_loop(self):
        rng=np.random.default_rng(42)
        for _ in range(10):
            scores=rng.integers(0,5,self.masks.shape).astype(float)
            self.assertAlmostEqual(aupro(self.masks,scores),reference_aupro(self.masks,scores),places=12)

    def test_regions_receive_equal_weight(self):
        # Recover one 1-pixel region and miss a 9-pixel region until all background is positive.
        scores=np.ones(self.masks.shape)
        scores[self.masks]=0
        scores[0,1,1]=2
        self.assertAlmostEqual(aupro(self.masks,scores),.5)

    def test_no_regions_is_undefined(self):
        self.assertIsNone(aupro(np.zeros_like(self.masks),np.ones(self.masks.shape)))

    def test_nonfinite_scores_are_rejected(self):
        with self.assertRaises(ValueError):
            aupro(self.masks,np.full(self.masks.shape,np.nan))

    def test_subgroup_image_auc_uses_normal_images(self):
        masks=np.concatenate([np.zeros((1,6,6),bool),self.masks])
        rows=[{'is_anomaly':0,'group':'normal'},{'is_anomaly':1,'group':'small'},
              {'is_anomaly':1,'group':'large'}]
        result=evaluate_groups(rows,np.array([0.,1.,2.]),masks.astype(float),masks)
        self.assertEqual(result['small']['n_normal'],1)
        self.assertEqual(result['small']['n_anomaly'],1)
        self.assertEqual(result['small']['image_auroc'],1)

    def test_binned_bootstrap_matches_exact_for_discrete_scores(self):
        scores=self.masks.astype(float)
        stats=sufficient_statistics(self.masks,scores,64)
        self.assertAlmostEqual(curve_from_counts(np.ones(2),stats),aupro(self.masks,scores))
        # Duplicate one image: counts must reproduce an actual image-level resample.
        counts=np.array([2,1])
        scores[1,1:4,1:4]=.2
        stats=sufficient_statistics(self.masks,scores,64)
        idx=[0,0,1]
        self.assertAlmostEqual(curve_from_counts(counts,stats),aupro(self.masks[idx],scores[idx]))


class MaskPreprocessing(unittest.TestCase):
    def test_original_area_group_and_crop_loss_are_separate(self):
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp)
            image=Image.new('RGB',(100,100))
            mask=np.zeros((100,100),np.uint8)
            mask[:2,:2]=255
            image.save(folder/'image.png')
            Image.fromarray(mask).save(folder/'mask.png')
            record=Record(folder/'image.png',folder/'mask.png','screw','test','scratch','screw/test/scratch/image.png')
            row=audit_record(record,100,80)
            self.assertEqual(row['group'],'small')
            self.assertAlmostEqual(row['original_area_ratio'],.0004)
            self.assertEqual(row['cropped_defect_pixels'],4)
            self.assertTrue(row['lost_all_after_transform'])

    def test_mask_remains_binary(self):
        mask=np.zeros((100,100),np.uint8)
        mask[40:50,40:50]=255
        image,out=geometry(Image.new('RGB',(100,100)),Image.fromarray(mask),256,224)
        self.assertEqual(image.size,(224,224))
        self.assertLessEqual(set(np.unique(out)),{0,255})


if __name__=='__main__':
    unittest.main()
