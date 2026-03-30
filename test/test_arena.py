from transformers import pipeline
import librosa
import torch

# Model test file for DF Arena 1B
pipeline_device = 0 if torch.cuda.is_available() else -1
print("Using pipeline device:", "cuda" if pipeline_device == 0 else "cpu")

pipe = pipeline(
    "antispoofing",
    model="Speech-Arena-2025/DF_Arena_1B_V_1",
    trust_remote_code=True,
    device=pipeline_device,
)

audio, sr = librosa.load("sample.wav", sr=16000)
result = pipe(audio)
print("DF Arena 1B result:", result)
# Example Output:
# {'label': 'spoof', 'logits': [[1.5515458583831787, -1.2254822254180908]], 'score': 0.9414217472076416, 'all_scores': {'spoof': 0.9414217472076416, 'bonafide': 0.05857823044061661}}
