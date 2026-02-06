import easyocr
import numpy as np

class OCREngine:
    def __init__(self, languages=['en'], gpu=True):
        print(f"Loading EasyOCR model for languages: {languages} (GPU={gpu})...")
        self.reader = easyocr.Reader(languages, gpu=gpu)
        print("EasyOCR model loaded.")

    def extract_text(self, image):
        """
        Extracts text from a PIL Image or numpy array.
        Args:
            image: PIL.Image or numpy array.
        Returns:
            str: Combined extracted text.
        """
        # EasyOCR supports file path, numpy array, or bytes. 
        # If PIL image, convert to numpy array
        if not isinstance(image, np.ndarray):
            image = np.array(image)

        # detail=0 returns just the text list
        result = self.reader.readtext(image, detail=0, paragraph=True)
        
        return " ".join(result)

if __name__ == "__main__":
    # Test stub
    pass
