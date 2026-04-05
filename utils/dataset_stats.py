import os
from collections import Counter
import pandas as pd


def count_classes(label_dir: str) -> Counter:
    """
    Counts YOLO-format class IDs in .txt annotation files.
    """
    stats = Counter()

    for filename in os.listdir(label_dir):
        if filename.endswith(".txt"):
            file_path = os.path.join(label_dir, filename)

            with open(file_path, "r") as f:
                for line in f:
                    parts = line.strip().split()
                    if len(parts) > 0:
                        class_id = parts[0]
                        stats[class_id] += 1

    return stats


def generate_stats_table(label_dir: str, class_map: dict):
    """
    Returns a pandas DataFrame of dataset statistics.
    """

    results = count_classes(label_dir)

    data = {
        "Class ID": [],
        "Label": [],
        "Number of Annotations": []
    }

    total = 0

    for class_id, label in class_map.items():
        count = results.get(str(class_id), 0)
        data["Class ID"].append(class_id)
        data["Label"].append(label)
        data["Number of Annotations"].append(count)
        total += count

    # Add total row
    data["Class ID"].append("Total")
    data["Label"].append("All Annotations")
    data["Number of Annotations"].append(total)

    df = pd.DataFrame(data)
    return df


if __name__ == "__main__":
    label_dir = "/path/to/labels"

    class_map = {
        0: "Weed",
        1: "Cotton"
    }

    df = generate_stats_table(label_dir, class_map)

    print("\nDataset Statistics:\n")
    print(df.to_markdown(index=False))
