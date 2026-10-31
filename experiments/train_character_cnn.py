"""Train an offline character experiment on verified public EMNIST data only.

The official test split is evaluated only after the fixed training schedule.
No hotel sheet is an input to training. This model is not a shipped reader.
"""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import struct
import sys
import time

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def canonical_glyph(image):
    ys, xs = np.nonzero(image > 20)
    tile = np.zeros((28, 28), dtype='float32')
    if not len(xs):
        return tile
    ink = image[ys.min():ys.max()+1, xs.min():xs.max()+1]
    h, w = ink.shape
    width, height = max(1, round(w*20/max(w, h))), max(1, round(h*20/max(w, h)))
    resized = cv2.resize(ink, (width, height), interpolation=cv2.INTER_AREA)/255.
    x, y = (28-width)//2, (28-height)//2
    tile[y:y+height, x:x+width] = resized
    return tile


def make_model():
    import torch.nn as nn
    return nn.Sequential(nn.Conv2d(1, 16, 3, padding=1), nn.ReLU(), nn.MaxPool2d(2),
        nn.Conv2d(16, 32, 3, padding=1), nn.ReLU(), nn.MaxPool2d(2), nn.Flatten(),
        nn.Linear(32*7*7, 128), nn.ReLU(), nn.Linear(128, 47))


def read_split(root, split):
    with gzip.open(root/f'emnist-balanced-{split}-images-idx3-ubyte.gz', 'rb') as stream:
        magic, count, height, width = struct.unpack('>IIII', stream.read(16))
        assert magic == 2051 and height == width == 28
        images = np.frombuffer(stream.read(), dtype='uint8').reshape(count, 28, 28).transpose(0, 2, 1)
    with gzip.open(root/f'emnist-balanced-{split}-labels-idx1-ubyte.gz', 'rb') as stream:
        magic, count = struct.unpack('>II', stream.read(8))
        assert magic == 2049
        labels = np.frombuffer(stream.read(), dtype='uint8').astype('int64')
    assert len(labels) == len(images) == count
    return np.stack([canonical_glyph(image) for image in images]), labels


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--data', required=True)
    p.add_argument('--output', required=True)
    p.add_argument('--epochs', type=int, default=6)
    args = p.parse_args()
    from experiments.offline_guard import block_network
    block_network()
    import torch
    from torch.nn import functional as F
    torch.set_num_threads(2)
    torch.manual_seed(67401)
    rng = np.random.default_rng(67401)
    root = Path(args.data)
    model = make_model()
    optimizer = torch.optim.Adam(model.parameters(), lr=.001)
    images, labels = read_split(root, 'train')
    order = rng.permutation(len(labels))
    training, validation = order[11280:], order[:11280]
    x = torch.from_numpy(images[:, None])
    y = torch.from_numpy(labels)
    started = time.perf_counter()
    history = []

    def accuracy(indices):
        good = 0
        model.eval()
        with torch.inference_mode():
            for start in range(0, len(indices), 512):
                ix = indices[start:start+512]
                good += (model(x[ix]).argmax(1) == y[ix]).sum().item()
        return good/len(indices)

    for epoch in range(args.epochs):
        model.train()
        shuffled = rng.permutation(training)
        loss_sum = 0.
        for start in range(0, len(shuffled), 256):
            ix = shuffled[start:start+256]
            batch = x[ix]
            # Small rotations, shear, scale and shifts cover pen slant and crop
            # variation without changing labels or using payroll examples.
            n = len(ix)
            angle = (torch.rand(n)-.5)*.30
            scale = .9+torch.rand(n)*.2
            matrix = torch.zeros(n, 2, 3)
            matrix[:, 0, 0] = angle.cos()*scale
            matrix[:, 1, 1] = angle.cos()*scale
            matrix[:, 0, 1] = -angle.sin()+(torch.rand(n)-.5)*.3
            matrix[:, 1, 0] = angle.sin()
            matrix[:, :, 2] = (torch.rand(n, 2)-.5)*.15
            grid = F.affine_grid(matrix, batch.shape, align_corners=False)
            batch = F.grid_sample(batch, grid, align_corners=False)
            optimizer.zero_grad()
            loss = F.cross_entropy(model(batch), y[ix])
            loss.backward()
            optimizer.step()
            loss_sum += loss.item()*n
        acc = accuracy(validation)
        record = dict(epoch=epoch+1, training_loss=loss_sum/len(training), validation_accuracy=acc)
        history.append(record)
        print(record, 'seconds', round(time.perf_counter()-started, 1), flush=True)

    test_images, test_labels = read_split(root, 'test')
    x = torch.from_numpy(test_images[:, None])
    y = torch.from_numpy(test_labels)
    test_accuracy = accuracy(np.arange(len(test_labels)))
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    torch.save(model.state_dict(), output)
    mapping = [chr(int(line.split()[1])) for line in (root/'emnist-balanced-mapping.txt').read_text().splitlines()]
    report = dict(seed=67401, epochs=args.epochs, training=len(training), validation=len(validation),
        test=len(test_labels), test_accuracy=test_accuracy, history=history, characters=mapping,
        sha256=hashlib.sha256(output.read_bytes()).hexdigest(),
        corpus='EMNIST Balanced',
        data_sha256={p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                     for p in sorted(root.glob('emnist-balanced-*.gz'))},
        archive_sha256='909a2a39c5e86bdd7662425e9b9c4a49bb582bf8d0edad427f3c3a9d0c6f7259',
        archive_source='https://rds.westernsydney.edu.au/Institutes/MARCS/BENS/EMNIST/emnist-gzip.zip',
        source='https://www.nist.gov/itl/products-and-services/emnist-dataset',
        purpose='public-character development experiment, not shipped payroll recognition')
    output.with_suffix('.json').write_text(json.dumps(report, indent=2))
    print('Official test accuracy', test_accuracy, 'checkpoint', output, flush=True)


if __name__ == '__main__':
    main()
