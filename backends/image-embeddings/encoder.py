"""SigLIP inference; imported only when the embedding service starts."""
import hashlib
import importlib.metadata
import json
import os


class SiglipEncoder:
    def __init__(self):
        import open_clip
        import torch
        self.torch = torch
        model_name = os.getenv('IMAGE_EMBEDDING_BACKEND_MODEL', 'ViT-B-16-SigLIP')
        pretrained = os.getenv('IMAGE_EMBEDDING_BACKEND_PRETRAINED', 'webli')
        self.device = os.getenv('EMBEDDING_DEVICE', 'cuda')
        if self.device.startswith('cuda') and not torch.cuda.is_available():
            raise RuntimeError('CUDA is unavailable; configure a GPU or EMBEDDING_DEVICE=cpu')
        model, _, self.preprocess = open_clip.create_model_and_transforms(
            model_name, pretrained=pretrained, device='cpu')
        model.eval()
        # Fingerprint actual weights and preprocessing, not just a mutable model name.
        digest = hashlib.sha256()
        metadata = dict(input_transform="exif-rgb-v1", model=model_name, pretrained=pretrained, preprocess=repr(self.preprocess),
                        open_clip=importlib.metadata.version('open_clip_torch'),
                        torch=torch.__version__, torchvision=importlib.metadata.version('torchvision'),
                        pillow=importlib.metadata.version('Pillow'))
        digest.update(json.dumps(metadata, sort_keys=True).encode())
        for name, tensor in sorted(model.state_dict().items()):
            digest.update(name.encode())
            digest.update(str((tuple(tensor.shape), tensor.dtype)).encode())
            digest.update(tensor.detach().contiguous().reshape(-1).view(torch.uint8).numpy().tobytes())
        self.model_version = f'{model_name}:{digest.hexdigest()}'
        self.model = model.to(self.device)

    def encode(self, images):
        torch = self.torch
        with torch.inference_mode():
            batch = torch.stack([self.preprocess(image) for image in images]).to(self.device)
            features = self.model.encode_image(batch).float()
            features = torch.nn.functional.normalize(features, dim=-1)
            return features.cpu().numpy()
