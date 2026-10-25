import re

import easyocr
import numpy as np

MISREAD_PERIOD = re.compile(r"(?<=\w)_(?=\s+[A-Z]|$)")


class OCREngine:
    def __init__(self, languages=None, gpu=True):
        if languages is None:
            languages = ['en']
        print(f"EasyOCR yukleniyor: diller={languages}, GPU={gpu}...")
        try:
            self.reader = easyocr.Reader(languages, gpu=gpu)
        except Exception as e:
            if gpu:
                print(f"GPU ile yukleme basarisiz, CPU'ya geciliyor: {e}")
                self.reader = easyocr.Reader(languages, gpu=False)
            else:
                raise
        print("EasyOCR yuklendi.")

    def extract_paragraphs(self, image):
        """
        Extracts text from a PIL Image or numpy array as a list of paragraphs.
        """
        if not isinstance(image, np.ndarray):
            image = np.array(image.convert("RGB"))

        paragraphs = self.reader.readtext(image, detail=0, paragraph=True)
        # EasyOCR often reads a sentence-ending "." as "_" ("saved_ Do you")
        return [MISREAD_PERIOD.sub(".", p) for p in paragraphs]
