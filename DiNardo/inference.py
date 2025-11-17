"""
TFLite model wrapper for real-time inference.
Handles input shape mismatch by transposing image axes.
"""
import numpy as np
import tflite_runtime.interpreter as tflite

class TFLiteModel:
    def __init__(self, model_path, num_threads):
        self.interpreter = tflite.Interpreter(model_path=model_path,
                                              num_threads=num_threads)
        self.interpreter.allocate_tensors()
        self.input_details = self.interpreter.get_input_details()
        self.output_details = self.interpreter.get_output_details()

    def predict(self, image):
        # Convert PIL image to numpy array
        arr = np.array(image, dtype=np.float32)
        # arr shape: (height, width)
        # transpose to (width, height) if model expects that
        arr = arr.T
        # add batch and channel dims: (1, width, height, 1)
        arr = arr[None, :, :, None]
        self.interpreter.set_tensor(self.input_details[0]['index'], arr)
        self.interpreter.invoke()
        return self.interpreter.get_tensor(self.output_details[0]['index'])[0][0]

