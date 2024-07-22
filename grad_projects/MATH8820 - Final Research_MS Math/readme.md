# Brain Tumor Detection using RetinaNet

## Project Overview

This project explores the application of modern object detection techniques to identify brain tumors in MRI scans. We implemented RetinaNet using the Detectron2 framework, focusing on understanding object detection architectures, preprocessing medical images, and evaluating model performance.

## Key Features

- Dataset: 1,229 preprocessed and augmented brain MRI images
- Model: RetinaNet with ResNet-50 backbone and Feature Pyramid Network (FPN)
- Framework: Detectron2
- Environment: Google Colab Pro with NVIDIA A100 GPU

## Results - Training for 2000 iterations

| Metric | IoU 0.5 | IoU 0.75 | IoU 0.5:0.95 |
|--------|---------|----------|--------------|
| mAP    | 0.940   | 0.910    | 0.797        |
| Recall | -       | -        | 0.856        |

## Challenges

- GPU memory constraints in Google Colab
- Adapting pre-trained models to medical imaging tasks
- Implementing YOLOv3 from scratch (initial attempt)

## Learning Outcomes

- Gained theoretical knowledge of object detection models
- Acquired hands-on experience with Detectron2 and RetinaNet
- Developed skills in working with large-scale datasets and GPU acceleration
- Learned to evaluate and interpret object detection results

## Future Work

- Develop a more comprehensive understanding of the entire object detection pipeline
- Create custom loss functions and dataloaders
- Investigate ensemble methods to improve accuracy
