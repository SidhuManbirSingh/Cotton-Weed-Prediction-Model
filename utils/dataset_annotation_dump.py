import os


def dump_annotations(base_path, sample_images):
    """
    Prints raw YOLO annotation files for debugging.
    """

    print("Annotation File Dump:\n")

    for img_name in sample_images:
        txt_name = img_name.replace(".jpg", ".txt")
        txt_path = os.path.join(base_path, txt_name)

        print(f"\n--- {txt_name} ---")

        if os.path.exists(txt_path):
            with open(txt_path, "r") as f:
                content = f.read().strip()
                print(content if content else "[EMPTY FILE]")
        else:
            print("File not found")


if __name__ == "__main__":
    base_path = "/path/to/images"

    sample_images = [
        f for f in os.listdir(base_path) if f.endswith(".jpg")
    ][:5]

    dump_annotations(base_path, sample_images)
