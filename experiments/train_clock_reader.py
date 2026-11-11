"""Train a clock-only CTC reader on public EMNIST glyphs and fictional clocks."""
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
import torch
from torch import nn
from torch.nn import functional as F

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
ALPHABET = '0123456789:APM?'
IDS = {char: index + 1 for index, char in enumerate(ALPHABET)}
HEIGHT, WIDTH = 32, 160


class ClockReader(nn.Module):
    def __init__(self):
        super().__init__()
        self.image = nn.Sequential(
            nn.Conv2d(1, 16, 3, padding=1), nn.BatchNorm2d(16), nn.ReLU(), nn.MaxPool2d(2),
            nn.Conv2d(16, 24, 3, padding=1), nn.BatchNorm2d(24), nn.ReLU(), nn.MaxPool2d((2, 1)),
            nn.Conv2d(24, 32, 3, padding=1), nn.BatchNorm2d(32), nn.ReLU(), nn.MaxPool2d(2),
            nn.Conv2d(32, 48, (4, 3), padding=(0, 1)), nn.BatchNorm2d(48), nn.ReLU(),
        )
        self.line = nn.Sequential(
            nn.Conv1d(48, 48, 5, padding=2), nn.ReLU(),
            nn.Conv1d(48, len(ALPHABET) + 1, 3, padding=1),
        )

    def forward(self,pixels):
        return self.line(self.image(pixels).squeeze(2)).transpose(1,2)


def glyphs(source, split):
    image_file = source / f'emnist-balanced-{split}-images-idx3-ubyte.gz'
    label_file = source / f'emnist-balanced-{split}-labels-idx1-ubyte.gz'
    provenance = ROOT / 'experiments/character_training_evaluation.json'
    expected = json.loads(provenance.read_text())['data_sha256']
    for path in (image_file, label_file):
        with path.open('rb') as stream:
            if hashlib.file_digest(stream, 'sha256').hexdigest() != expected[path.name]:
                raise ValueError(f'Unexpected EMNIST file hash for {path.name}')
    with gzip.open(image_file, 'rb') as stream:
        magic, count, height, width = struct.unpack('>IIII', stream.read(16))
        assert (magic, height, width) == (2051, 28, 28)
        raw = np.frombuffer(stream.read(), dtype=np.uint8).reshape(count, height, width)
        images = raw.transpose(0, 2, 1)
    with gzip.open(label_file, 'rb') as stream:
        magic, label_count = struct.unpack('>II', stream.read(8))
        assert (magic, label_count) == (2049, count)
        labels = np.frombuffer(stream.read(), dtype=np.uint8)
    output = {char: [] for char in ALPHABET if char != ':'}
    emnist_uppercase = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    for image, label in zip(images, labels, strict=True):
        if label == 36:
            char = 'A'
        elif label < 36 and emnist_uppercase[label] in output:
            char = emnist_uppercase[label]
        elif label in (11, 12, 13, 14, 15, 16, 17, 20, 23, 26, 27, 28, 29, 31, 33, 34, 35):
            char = '?'
        else:
            continue
        ys, xs = np.nonzero(image > 25)
        if len(ys):
            output[char].append(image[ys.min():ys.max() + 1, xs.min():xs.max() + 1].copy())
    assert all(output.values())
    return output


def sample_text(rng):
    number = rng.random()
    if number < .05:
        return ''
    if number < .12:
        return '?' * int(rng.integers(1, 5))
    hour = int(rng.integers(1, 13)) if rng.random() < .86 else int(rng.integers(0, 24))
    hour_text = f'{hour:02d}' if rng.random() < .26 else str(hour)
    meridiem = rng.choice(('A', 'P')) if 1 <= hour <= 12 and rng.random() < .54 else ''
    if meridiem and rng.random() < .62:
        meridiem += 'M'
    if rng.random() < .14:
        return hour_text + meridiem
    minute = int(rng.choice((0, 15, 30, 45))) if rng.random() < .25 else int(rng.integers(0, 60))
    colon = ':' if rng.random() < .79 else ''
    if not meridiem and rng.random() < .08:
        meridiem = 'M'
    return f'{hour_text}{colon}{minute:02d}{meridiem}'


def draw_clock(rng, text, glyph_bank):
    staging = np.zeros((HEIGHT, 300), dtype=np.uint8)
    height = int(rng.integers(15, 28))
    base_y = int(rng.integers(height, 31))
    pen = float(rng.uniform(.45, 1.))
    x = int(rng.integers(3, 18))
    for ch in text:
        if ch == ':':
            glyph = np.zeros((height, max(3, round(height * .16))), np.uint8)
            radius = max(1, int(rng.integers(1, 3)))
            for y in (round(height * .34), round(height * .68)):
                cv2.circle(glyph, (glyph.shape[1] // 2, y), radius, 255, -1)
        else:
            pool = glyph_bank[ch]
            glyph = pool[int(rng.integers(len(pool)))]
            actual_height = max(7, min(29, height + int(rng.integers(-4, 5))))
            stretch = float(rng.uniform(.83, 1.18))
            scaled_width = actual_height * glyph.shape[1] / glyph.shape[0] * stretch
            actual_width = max(3, min(33, round(scaled_width)))
            size = (actual_width, actual_height)
            glyph = cv2.resize(glyph, size, interpolation=cv2.INTER_LINEAR)
            if rng.random() < .42:
                center = (actual_width / 2, actual_height / 2)
                affine = cv2.getRotationMatrix2D(center, float(rng.uniform(-9, 9)), 1)
                affine[0, 1] += float(rng.uniform(-.12, .12))
                glyph = cv2.warpAffine(glyph, affine, size)
        glyph_height, glyph_width = glyph.shape
        top = max(0, min(HEIGHT - glyph_height, base_y - glyph_height + int(rng.integers(-2, 3))))
        strength = float(rng.uniform(.84, 1.16)) * pen
        crop = np.uint8(np.clip(glyph.astype(np.float32) * strength, 0, 255))
        region = staging[top:top + glyph_height, x:x + glyph_width]
        np.maximum(region, crop, out=region)
        x += glyph_width + int(rng.integers(-1, 6))
    if x > WIDTH - 4:
        pixels = np.zeros((HEIGHT, WIDTH), dtype=np.uint8)
        pixels[:, :WIDTH - 3] = cv2.resize(staging[:, :x + 2], (WIDTH - 3, HEIGHT))
    else:
        pixels = staging[:, :WIDTH].copy()
    if rng.random() < .20:
        y = int(rng.choice([0, 1, 2, 30, 31]))
        cv2.line(pixels, (0, y), (WIDTH - 1, y + int(rng.integers(-1, 2))),
                 int(rng.integers(5, 60)), 1)
    if rng.random() < .15:
        pixels = cv2.GaussianBlur(pixels, (3, 3), .64)
    if rng.random() < .16:
        noise = rng.integers(0, 13, size=pixels.shape, dtype=np.uint8)
        pixels = cv2.add(pixels, noise)
    return pixels


def synthesize(bank, size, seed):
    rng = np.random.default_rng(seed)
    images = np.empty((size, 1, HEIGHT, WIDTH), np.uint8)
    texts = []
    for i in range(size):
        text = sample_text(rng)
        images[i, 0] = draw_clock(rng, text, bank)
        texts.append(text)
    return images, texts


def ctc_read(logits):
    labels = logits.argmax(dim=-1).numpy()
    texts = []
    for row in labels:
        emitted = np.r_[True, row[1:] != row[:-1]] & (row != 0)
        texts.append(''.join(ALPHABET[i - 1] for i in row[emitted]))
    return texts


def train(source):
    rng = np.random.default_rng(67401)
    model = ClockReader()
    optimizer = torch.optim.AdamW(model.parameters(), lr=.0025)
    train_images, train_text = synthesize(glyphs(source, 'train'), 48000, 67401)
    validation_images, validation_text = synthesize(glyphs(source, 'test'), 3500, 147)
    examples = torch.from_numpy(train_images)
    validation = torch.from_numpy(validation_images)
    tokens = [torch.tensor([IDS[char] for char in line], dtype=torch.long) for line in train_text]
    lengths = torch.tensor([len(line) for line in train_text], dtype=torch.long)
    started = time.monotonic()
    for epoch in range(8):
        order = rng.permutation(len(train_text))
        model.train()
        loss_total = 0.
        for start in range(0, len(order), 128):
            ids = order[start:start + 128]
            images = examples[ids].float() / 255
            logits = model(images)
            target = torch.cat([tokens[i] for i in ids])
            input_lengths = torch.full((len(ids),), logits.shape[1], dtype=torch.long)
            loss = F.ctc_loss(logits.log_softmax(-1).transpose(0, 1), target, input_lengths,
                              lengths[ids], zero_infinity=True)
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            loss_total += float(loss.detach()) * len(ids)
        model.eval()
        hits = 0
        with torch.inference_mode():
            for start in range(0, len(validation_text), 128):
                batch = validation[start:start + 128].float() / 255
                output = ctc_read(model(batch))
                hits += sum(predicted == expected for predicted, expected
                            in zip(output, validation_text[start:start + 128], strict=True))
        print(f'Epoch {epoch + 1}: loss {loss_total / len(order):.3f}; '
              f'synthetic validation {hits}/{len(validation_text)}; '
              f'{round(time.monotonic() - started)} seconds', flush=True)
        if epoch == 4:
            for group in optimizer.param_groups:
                group['lr'] *= .52
    return model


class WithProbabilities(nn.Module):
    def __init__(self, model):
        super().__init__()
        self.model = model

    def forward(self, pixels):
        return self.model(pixels).softmax(-1)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', required=True, type=Path,
                        help='Directory of the four SHA-256 pinned EMNIST Balanced gzip files')
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()

    from experiments.offline_guard import block_network
    block_network()
    cv2.setNumThreads(1)
    torch.set_num_threads(5)
    torch.set_num_interop_threads(1)
    torch.manual_seed(67401)

    model = train(args.data)
    torch.onnx.export(WithProbabilities(model).eval(), torch.zeros(2, 1, HEIGHT, WIDTH),
                      args.output, input_names=['pixels'], output_names=['probabilities'],
                      dynamic_axes={'pixels': {0: 'batch'}, 'probabilities': {0: 'batch'}},
                      opset_version=17, dynamo=False)
    with args.output.open('rb') as stream:
        print(hashlib.file_digest(stream, 'sha256').hexdigest())


if __name__ == '__main__':
    main()
