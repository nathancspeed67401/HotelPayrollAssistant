"""Pinned public recognition weights; never downloaded while reading a sheet."""
from pathlib import Path

LINE_MODEL_NAME = 'PP-OCRv6_rec_medium.onnx'
LINE_MODEL_SHA256 = 'eef444829dbbe18d7fea59a3f6eb75647518d2b3a9568d27c92e42940204894b'
LINE_MODEL_URL = ('https://www.modelscope.cn/models/RapidAI/RapidOCR/resolve/'
                  'v3.10.0/onnx/PP-OCRv6/rec/' + LINE_MODEL_NAME)
LINE_MODEL = Path(__file__).resolve().parent / 'assets' / LINE_MODEL_NAME
