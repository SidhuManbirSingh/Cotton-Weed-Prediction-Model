# CottonVision — UAV Cotton-Weed Prediction System

**Directed Studies Project — University of the Fraser Valley (UFV)**  
**Student Researcher:** Manbir Singh Sidhu  
**Supervisor:** Professor Omer Waqar  
**Repository:** https://github.com/SidhuManbirSingh/Cotton-Weed-Prediction-Model/  
**Full Research Paper:** [Final_Report.pdf](Final_Report.pdf)

---

## Overview

CottonVision is a real-time computer vision system for detecting and differentiating cotton crops (Class 1) from invasive weeds (Class 0: Palmer amaranth, Russian thistle, and kochia) in high-resolution Unmanned Aerial Vehicle (UAV) imagery and 4K flight video. All research, model training, evaluation, and full-stack software engineering were conducted at the **University of the Fraser Valley** under the supervision and guidance of **Professor Omer Waqar**.

---

## Single-Command Quick Start

Run the entire backend, inference engine, and web workbench with one command from the repository root:

- **Windows:** Double-click `run.bat` or run it in a terminal:
  ```bat
  run.bat
  ```
- **Linux / macOS / Docker:**
  ```bash
  bash deployment-script.sh
  ```

Once launched, open `http://127.0.0.1:5000` in your browser to access the dual-pane inference workbench, interactive H.264 stream preview, normalized YOLOv8 `.zip` dataset exporter, and `Final_Report.pdf`.

---

## Dataset, Methodology & Benchmarks

### Dataset Curation & Leakage-Free Split
The model is built on the peer-reviewed Mendeley UAV Cotton-Weed dataset by Das, Yang, & Subburaj (2025) [15], comprising **366 raw high-resolution aerial images (`4096 x 3072` px)** captured using an Autel Robotics EVO II Dual 640T V3 drone over Texas Panhandle cotton fields, annotated with **50,821 cotton** and **5,713 weed** bounding boxes using LabelImg and Roboflow. Using an 80/20 stratified train/validation strategy [20] with fixed seed (`random_state=42`) to prevent data leakage [21], the dataset yields **7,399 augmented training images** and **1,850 withheld validation images** containing **11,056 labeled instances** (`9,892` cotton, `1,164` weed).

### Model Architecture & Transfer Learning
Traditional object detectors evolved from hand-crafted descriptors such as Viola-Jones [5] and Histograms of Oriented Gradients (HOG) [1] to two-stage region-proposal networks—R-CNN [3], Fast R-CNN [2], and Faster R-CNN [4]—before single-stage unified detectors enabled real-time aerial inference via YOLO [8, 9], YOLOv4 [29], YOLOv5 [6], YOLOv8 [7, 19], and YOLOv9 [10] as surveyed in modern YOLO evolution studies [22].

To achieve real-time throughput on drone telemetry, CottonVision applies transfer learning [13, 14] starting from `YOLOv8n` (`yolov8n.pt`) pretrained on ImageNet [11] and MS COCO [12, 23]. Training ran for 50 epochs (`640 x 640`, batch size 16, FP16 mixed precision on a Tesla T4 GPU) using the decoupled weight-decay AdamW optimizer [24, 28] (`lr0=0.001667`, 3 warmup epochs), Generalized/Distribution Focal Loss (`box=7.5, cls=0.5, dfl=1.5`) [27] monitored across training and validation loss curves [26], and Mosaic [29] plus photometric/erasing augmentations.

### Validation Results [25]
Evaluated across the 1,850 withheld validation images:

| Metric | Overall | Cotton (Class 1) | Weeds (Class 0) |
| :--- | :--- | :--- | :--- |
| **mAP@0.50** | `84.9%` (`0.8489`) | `93.8%` | `76.0%` |
| **Precision** | `79.8%` (`0.7979`) | `84.7%` | `74.9%` |
| **Recall** | `78.0%` (`0.7797`) | `89.4%` | `66.6%` |
| **mAP@0.50:0.95** | `50.0%` (`0.5000`) | — | — |

Peak all-class **F1 score is `0.79`** at confidence `0.289`. On Tesla T4 GPU inference, total frame latency is **`6.8 ms`** (`1.3 ms` pre-process + `3.4 ms` inference + `2.1 ms` post-process), achieving **`147 FPS`** throughput.

---

## System Workflow & Architecture

The application implements a three-tier containerized stack following RESTful API conventions [16], modular Flask request handling with thread locks (`_jobs_lock`) [18], OpenCV media processing (`video2image.py`, `convert.py`) [35], a React single-page interface [32, 33, 34], and reproducible Docker containerization [17, 30, 31]:

1. **Startup Flow:** `run.bat` / `deployment-script.sh` -> Verify Python 3.10+, OpenCV, FFmpeg & `yolov8n.pt` -> Launch Flask API (`:5000`) + Web UI -> Open Workbench.
2. **Inference Flow:** Upload Image/Video (`POST /api/upload`) -> YOLOv8n Frame Inference (`POST /api/process`) -> Compute Synchronized FPS (`Source FPS / N`) & Transcode `faststart` H.264 -> Inspect Side-by-Side & Export YOLO `.zip` Archive (`/api/download/dataset/<job_id>`).

For full architectural diagrams, loss curves, and experimental discussion, read [Final_Report.pdf](Final_Report.pdf) or see [DEPLOYMENT.md](DEPLOYMENT.md).

---

## References

[1] Dalal, N., & Triggs, B. (2005). Histograms of oriented gradients for human detection. In 2005 IEEE Computer Society Conference on Computer Vision and Pattern Recognition (CVPR'05) (Vol. 1, pp. 886-893). IEEE. https://doi.org/10.1109/CVPR.2005.177

[2] Girshick, R. (2015). Fast R-CNN. In Proceedings of the IEEE International Conference on Computer Vision (ICCV) (pp. 1440-1448). IEEE. https://doi.org/10.1109/ICCV.2015.169

[3] Girshick, R., Donahue, J., Darrell, T., & Malik, J. (2014). Rich feature hierarchies for accurate object detection and semantic segmentation. In Proceedings of the IEEE Conference on Computer Vision and Pattern Recognition (CVPR) (pp. 580-587). IEEE. https://doi.org/10.1109/CVPR.2014.81

[4] Ren, S., He, K., Girshick, R., & Sun, J. (2015). Faster R-CNN: Towards real-time object detection with region proposal networks. In Advances in Neural Information Processing Systems (NeurIPS) (Vol. 28).

[5] Viola, P., & Jones, M. (2001). Rapid object detection using a boosted cascade of simple features. In Proceedings of the 2001 IEEE Computer Society Conference on Computer Vision and Pattern Recognition (CVPR) (Vol. 1, pp. I-I). IEEE. https://doi.org/10.1109/CVPR.2001.990517

[6] Jocher, G. (2020). YOLOv5 by Ultralytics (Version 7.0) [Computer software]. Zenodo. https://doi.org/10.5281/zenodo.3908559

[7] Jocher, G., Chaurasia, A., & Qiu, J. (2023). YOLO by Ultralytics (Version 8.0.0) [Computer software]. GitHub. https://github.com/ultralytics/ultralytics

[8] Redmon, J., Divvala, S., Girshick, R., & Farhadi, A. (2016). You only look once: Unified, real-time object detection. In Proceedings of the IEEE Conference on Computer Vision and Pattern Recognition (CVPR) (pp. 779-788). IEEE. https://doi.org/10.1109/CVPR.2016.91

[9] Redmon, J., & Farhadi, A. (2018). YOLOv3: An incremental improvement. arXiv. https://doi.org/10.48550/arXiv.1804.02767

[10] Wang, C.-Y., Yeh, I.-H., & Liao, H.-Y. M. (2024). YOLOv9: Learning what you want to learn using programmable gradient information. arXiv. https://doi.org/10.48550/arXiv.2402.13616

[11] Deng, J., Dong, W., Socher, R., Li, L.-J., Li, K., & Fei-Fei, L. (2009). ImageNet: A large-scale hierarchical image database. In 2009 IEEE Conference on Computer Vision and Pattern Recognition (pp. 248-255). IEEE. https://doi.org/10.1109/CVPR.2009.5206848

[12] Lin, T.-Y., Maire, M., Belongie, S., Hays, J., Perona, P., Ramanan, D., Dollar, P., & Zitnick, C. L. (2014). Microsoft COCO: Common objects in context. In European Conference on Computer Vision (ECCV) (pp. 740-755). Springer. https://doi.org/10.1007/978-3-319-10602-1_48

[13] Pan, S. J., & Yang, Q. (2010). A survey on transfer learning. IEEE Transactions on Knowledge and Data Engineering, 22(10), 1345-1359. https://doi.org/10.1109/TKDE.2009.191

[14] Yosinski, J., Clune, J., Bengio, Y., & Lipson, H. (2014). How transferable are features in deep neural networks? In Advances in Neural Information Processing Systems (NeurIPS) (Vol. 27).

[15] Das, A., Yang, Y., & Subburaj, V. (2025). Annotated UAV Image Dataset for Object Detection Using LabelImg and Roboflow (Version 1) [Data set]. Mendeley Data. https://doi.org/10.17632/fwg6pt6ckd.1

[16] Braun, M. B. (2015). RESTful API design: Best practices in API design with REST. API-University Press.

[17] Voulgaris, K., Kiourtis, A., Karabetian, A., Karamolegkos, P., Poulakis, Y., Mavrogiorgou, A., & Kyriazis, D. (2022). A comparison of container systems for machine learning scenarios: Docker and Podman. 2022 2nd International Conference on Computers and Automation (CompAuto), 114-118.

[18] Wang, J. (2025). A data-driven and modular Flask-based architecture for secure and intelligent programming education powered by LLMs. Journal of Data Science, 2025(13).

[19] Jocher, G., Chaurasia, A., & Qiu, J. (2023). Ultralytics YOLOv8 (Version 8.0.0) [Software]. https://github.com/ultralytics/ultralytics

[20] GunKurnia. (2024, September 11). Choosing the optimal data split for machine learning: 80/20 vs 70/30? Medium. https://medium.com/@gunkurnia/choosing-the-optimal-data-split-for-machine-learning-80-20-vs-70-30-0fd266710236

[21] Cook, A. (2021). Data Leakage [Computer software]. Kaggle. https://www.kaggle.com/code/alexisbcook/data-leakage

[22] Sapkota, B., et al. (2025). Ultralytics YOLO evolution: An overview of YOLO26, YOLO11, YOLOv8, and YOLOv5 object detectors for computer vision and pattern recognition. arXiv. https://arxiv.org/html/2510.09653v2

[23] COCO - Common Objects in Context. (n.d.). COCO Dataset. Retrieved February 27, 2026, from https://cocodataset.org/#home

[24] Hao, Y., Tang, Z., Tian, Y., Zhang, Y., & Zhou, Z. (2024). AdamW. In Cornell University Computational Optimization Open Textbook. Retrieved February 27, 2026, from https://optimization.cbe.cornell.edu/index.php?title=AdamW

[25] Ultralytics. (2024). YOLO performance metrics (class-wise metrics). In Ultralytics YOLO Documentation. https://docs.ultralytics.com/guides/yolo-performance-metrics/#class-wise-metrics

[26] GeeksforGeeks. (2025, November 27). Training and validation loss in deep learning. https://www.geeksforgeeks.org/deep-learning/training-and-validation-loss-in-deep-learning/

[27] Li, X., Wang, W., Wu, L., Chen, S., Hu, X., Li, J., Tang, J., & Yang, J. (2020). Generalized focal loss: Learning qualified and distributed bounding boxes for dense object detection. Advances in Neural Information Processing Systems, 33, 21002-21012.

[28] Loshchilov, I., & Hutter, F. (2019). Decoupled weight decay regularization. International Conference on Learning Representations (ICLR). https://arxiv.org/abs/1711.05101

[29] Bochkovskiy, A., Wang, C.-Y., & Liao, H.-Y. M. (2020). YOLOv4: Optimal speed and accuracy of object detection. arXiv preprint arXiv:2004.10934. https://arxiv.org/abs/2004.10934

[30] Openja, M., Khomh, F., Saidani, G., Mkaouer, M. W., & Ouni, A. (2022). Studying the practices of deploying machine learning projects on Docker. arXiv preprint arXiv:2206.00699. https://arxiv.org/abs/2206.00699

[31] Merkel, D. (2014). Docker: Lightweight Linux containers for consistent development and deployment. Linux Journal, 2014(239), Article 2.

[32] Piastou, M. (2023). Comprehensive performance and scalability assessment of front-end frameworks: React, Angular, and Vue.js. World Journal of Advanced Engineering Technology and Sciences, 9(2), 366-376. https://doi.org/10.30574/wjaets.2023.9.2.0153

[33] Lazuardy, M. F. S., & Anggraini, D. (2022). Modern front end web architectures with React.js and Next.js. International Research Journal of Advanced Engineering and Science, 7(1), 132-141.

[34] Jonathan, R., & Suprihadi, S. (2023). Development of front-end web applications utilizing single page application framework and React.js library. International Journal Software Engineering and Computer Science (IJSECS), 3(3), 529-536. https://journal.lembagakita.org/index.php/ijsecs/article/view/1943

[35] Bradski, G. (2000). The OpenCV library. Dr. Dobb's Journal of Software Tools, 25(11), 120-125.
