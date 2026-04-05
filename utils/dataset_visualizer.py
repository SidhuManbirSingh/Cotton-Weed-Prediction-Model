import os
import cv2
import random
import numpy as np
import matplotlib.pyplot as plt
import supervision as sv


def load_yolo_annotations(txt_path, img_width, img_height):
    """
    Converts YOLO format to bounding boxes.
    """
    boxes = []
    class_ids = []

    if not os.path.exists(txt_path):
        return boxes, class_ids

    with open(txt_path, "r") as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) < 5:
                continue

            class_id = int(parts[0])
            cx, cy, bw, bh = map(float, parts[1:5])

            x1 = (cx - bw / 2) * img_width
            y1 = (cy - bh / 2) * img_height
            x2 = (cx + bw / 2) * img_width
            y2 = (cy + bh / 2) * img_height

            boxes.append([x1, y1, x2, y2])
            class_ids.append(class_id)

    return boxes, class_ids


def visualize_dataset(base_path, classes, num_samples=4):
    """
    Randomly samples images and visualizes annotations.
    """

    all_images = [f for f in os.listdir(base_path) if f.endswith(".jpg")]
    sample_images = random.sample(all_images, min(num_samples, len(all_images)))

    box_annotator = sv.BoxAnnotator(thickness=2)
    label_annotator = sv.LabelAnnotator(text_thickness=2, text_scale=1)

    images_to_plot = []
    titles = []

    for img_name in sample_images:
        img_path = os.path.join(base_path, img_name)
        image = cv2.imread(img_path)

        if image is None:
            continue

        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        h, w, _ = image.shape

        txt_path = os.path.join(base_path, img_name.replace(".jpg", ".txt"))

        boxes, class_ids = load_yolo_annotations(txt_path, w, h)

        if len(boxes) > 0:
            detections = sv.Detections(
                xyxy=np.array(boxes, dtype=np.float32),
                class_id=np.array(class_ids, dtype=int)
            )

            labels = [
                classes[c] if c < len(classes) else f"Unknown {c}"
                for c in detections.class_id
            ]

            annotated = box_annotator.annotate(image.copy(), detections)
            annotated = label_annotator.annotate(annotated, detections, labels)

        else:
            annotated = image.copy()

        images_to_plot.append(annotated)
        titles.append(f"{img_name} ({len(boxes)} objects)")

    sv.plot_images_grid(
        images=images_to_plot,
        titles=titles,
        grid_size=(2, 2),
        size=(16, 16)
    )


if __name__ == "__main__":
    base_path = "/path/to/images"
    classes = ["weed", "cotton"]

    visualize_dataset(base_path, classes)
