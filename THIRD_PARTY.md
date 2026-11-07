# Sources and attribution

- PatchCore paper: Karsten Roth et al., *Towards Total Recall in Industrial Anomaly Detection*, CVPR 2022. https://arxiv.org/abs/2106.08265
- Official implementation: https://github.com/amazon-science/patchcore-inspection
  - Vendored checkout: `vendor/patchcore-inspection`.
  - Pinned commit: `fcaa92f124fb1ad74a7acf56726decd4b27cbcad`.
  - Original source is unchanged. Original Apache-2.0 LICENSE and NOTICE are retained.
  - The study wrapper supplies a modern torchvision ImageNet V1 backbone, freezes its parameters, provides its own dataset loader and evaluation, and subclasses MeanMapper to perform an identical CPU adaptive-pooling operation when MPS does not implement a non-divisible shape. This device transfer is included in latency.
- Dataset: Paul Bergmann et al., *MVTec AD: A Comprehensive Real-World Dataset for Unsupervised Anomaly Detection*, CVPR 2019.
  - https://www.mvtec.com/research-teaching/datasets/mvtec-ad
  - Download links are taken from https://www.mvtec.com/research-teaching/datasets/mvtec-ad/downloads
  - Dataset license: CC BY-NC-SA 4.0. Download manifests record archive URLs and local SHA-256 checksums; no official checksum comparison is claimed.
- AUPRO protocol reference: https://github.com/open-edge-platform/anomalib/blob/main/src/anomalib/metrics/aupro.py
  - `study/metrics.py` independently implements region-balanced PRO with global background FPR, tied thresholds, 8-connected components, and normalized integration to FPR 0.3. It does not import Anomalib.

The comparison and analysis are the contribution of this course project. PatchCore and its existing multiscale fusion are prior work.
