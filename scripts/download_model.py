from huggingface_hub import snapshot_download

MODEL_ID = "helizac/dots.ocr-4bit"
snapshot_download(
    repo_id=MODEL_ID,
    local_dir="model/snapshot",
    local_dir_use_symlinks=False
)

print("✅ Model snapshot saved to model/snapshot")