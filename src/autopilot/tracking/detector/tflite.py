# Copyright 2021 The TensorFlow Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# ==============================================================================
#
# This file was modified, it is not the original to work.
#

"""A module to run object detection with a TensorFlow Lite model."""
import abc
import typing
import zipfile
from threading import Thread, Lock
from typing import List, NamedTuple, Optional

import cv2
import numpy as np
from kivy import Logger
from kivy.utils import platform

from autopilot.tracking.detector.api import Detector, Detection, Category, Rect
from util.filesystem import download_or_cache

# pylint: disable=g-import-not-at-top
try:
    # Import TFLite interpreter from tflite_runtime package if it's available.
    from tflite_runtime.interpreter import Interpreter
    from tflite_runtime.interpreter import load_delegate
except ImportError:
    # If not, fallback to use the TFLite interpreter from the full TF package.
    import tensorflow as tf

    Interpreter = tf.lite.Interpreter
    load_delegate = tf.lite.experimental.load_delegate


# pylint: enable=g-import-not-at-top


class TFLiteDetectorOptions(NamedTuple):
    """A config to initialize an object detector."""

    enable_edgetpu: bool = False
    """Enable the model to run on EdgeTPU."""

    label_allow_list: List[str] = None
    """The optional allow list of labels."""

    label_deny_list: List[str] = None
    """The optional deny list of labels."""

    num_threads: int = 4
    """The number of CPU threads to be used."""


def libedgetpu_name():
    """Returns the library name of EdgeTPU in the current platform."""
    return {
        'Darwin': 'libedgetpu.1.dylib',
        'Linux': 'libedgetpu.so.1',
        'Windows': 'edgetpu.dll',
    }.get(platform.system(), None)


def resize_and_pad(img: np.ndarray, w: int, h: int) -> (np.ndarray, float, float, float, float):
    """
    Resize and pad (with gray) an image to a target size.
    """
    img_h, img_w = img.shape[:2]
    scale = min(w / img_w, h / img_h)
    resized = cv2.resize(img, (int(img_w * scale), int(img_h * scale)))
    padded = np.full((h, w, 3), 128, dtype=np.uint8)
    padded[:resized.shape[0], :resized.shape[1]] = resized
    added_x, scaled_x, added_y, scaled_y = 0, 1, 0, 1  # Used to scale the bounding box back to the original image
    if img_w > img_h:
        scaled_y = scale / (h / img_h)
        # added_y = (1 - scaled_y) / 2  # Actually, the padded image is not centered, so we don't need this
    elif img_w < img_h:
        scaled_x = scale / (w / img_w)
        # added_x = (1 - scaled_x) / 2  # Actually, the padded image is not centered, so we don't need this
    # Logger.info(f"resize_and_pad: {img_w}x{img_h} -> {resized.shape[1]}x{resized.shape[0]} -> {w}x{h}")
    # Logger.info(f"resize_and_pad: added_x={added_x}, scaled_x={scaled_x}, added_y={added_y}, scaled_y={scaled_y}")
    return padded, added_x, scaled_x, added_y, scaled_y


class TFLiteDetector(Detector):
    """A wrapper class for a TFLite object detection model."""

    def __init__(self, model_path: str, labels: Optional[List[str]] = None,
                 options: TFLiteDetectorOptions = TFLiteDetectorOptions()) -> None:
        """Initialize a TFLite object detection model.

        :param model_path: Path to the TFLite model.
        :param labels: List of labels for the model. They will be automatically retrieved from the model if available.
        :param options: The config to initialize an object detector.
        """
        self._model_path = model_path
        self._labels = labels
        self._options = options
        self._interpreter: Optional[Interpreter] = None
        self._interpreter_lock = Lock()

    def load(self, callback: typing.Callable[[float], None] = None):
        Thread(target=self._load, args=(callback,)).start()

    def _load(self, callback: typing.Callable[[float], None] = None):
        # Download the model if it's a remote URL.
        callback(0.01)
        if self._model_path.startswith('http'):
            self._model_path = download_or_cache(url=self._model_path, progress=lambda p: callback(p * 0.9))
        callback(0.9)

        # Load label list from metadata.
        try:
            with zipfile.ZipFile(self._model_path) as model_with_metadata:
                if not model_with_metadata.namelist():
                    raise ValueError('Invalid TFLite model: no label file found.')

                file_name = model_with_metadata.namelist()[0]
                with model_with_metadata.open(file_name) as label_file:
                    label_list = label_file.read().splitlines()
                    self._label_list = [label.decode('ascii') for label in label_list]
        except zipfile.BadZipFile:
            Logger.warn('No metadata found in the model, using the provided label list or no labels.')
            self._label_list = self._labels or []

        Logger.info("TFLiteDetector: model labels: %s" % self._label_list)

        # Initialize TFLite model.
        with self._interpreter_lock:
            if self._options.enable_edgetpu:
                if libedgetpu_name() is None:
                    raise OSError("The current OS isn't supported by Coral EdgeTPU.")
                self._interpreter = Interpreter(model_path=self._model_path, num_threads=self._options.num_threads,
                                                experimental_delegates=[load_delegate(libedgetpu_name())])
            else:
                self._interpreter = Interpreter(model_path=self._model_path, num_threads=self._options.num_threads)

            self._interpreter.allocate_tensors()

            self.input_size, self._dtype = self._on_load_model(self._interpreter)
            Logger.info('TFLiteDetector: input_size: %s, dtype: %s' % (str(self.input_size), self._dtype))
            callback(1)

    @abc.abstractmethod
    def _on_load_model(self, interpreter: Interpreter) -> ((int, int), typing.Any):
        """A hook to be called when the model is loaded. Returns the input size of the model."""
        input_detail = interpreter.get_input_details()[0]
        return (input_detail['shape'][2], input_detail['shape'][1]), input_detail['dtype']

    def detect(self, img: np.ndarray, min_confidence: float = 0.5, max_results: int = -1) -> List[Detection]:
        with self._interpreter_lock:
            if self._interpreter is None:
                raise ValueError('The model is not loaded yet.')

            # Prepare input tensor.
            input_tensor, add_x, scale_x, add_y, scale_y = self._preprocess(img)
            self._set_input_tensor(input_tensor)

            # Run inference.
            self._interpreter.invoke()

            # Get all output details
            boxes, classes, scores, count = self._get_output_tensors()

            # Postprocess detections and return the result.
            return self._postprocess(boxes, classes, scores, count, min_confidence, max_results,
                                     add_x, scale_x, add_y, scale_y)

    def _preprocess(self, input_image: np.ndarray) -> (np.ndarray, float, float, float, float):
        """Preprocess the input image as required by the TFLite model."""

        # Resize the input (if needed)
        added_x, scaled_x, added_y, scaled_y = 0, 1, 0, 1
        if input_image.shape[:2] == self.input_size:
            preprocessed = input_image
        else:
            preprocessed, added_x, scaled_x, added_y, scaled_y = resize_and_pad(
                input_image, self.input_size[0], self.input_size[1])

        if self._dtype == np.float32 and preprocessed.dtype == np.uint8:
            preprocessed = (np.float32(preprocessed) - 127.5) / 127.5  # uint8 --> float32 [0, 1]
        elif self._dtype == np.uint8 and preprocessed.dtype == np.float32:
            preprocessed = (preprocessed * 127.5 + 127.5).astype(np.uint8)  # float32 [0, 1] --> uint8
        elif self._dtype != preprocessed.dtype:
            raise ValueError('The dtype of the input image is not supported by the model.')

        return preprocessed, added_x, scaled_x, added_y, scaled_y

    def _set_input_tensor(self, image):
        """Sets the input tensor."""
        tensor_index = self._interpreter.get_input_details()[0]['index']
        # Add batch dimension
        image = np.expand_dims(image, axis=0)
        self._interpreter.set_tensor(tensor_index, image)

    def _get_output_tensor(self, index):
        """Returns the output tensor at the given index."""
        tensor = self._interpreter.get_tensor(index)
        # Remove batch dimension
        tensor = np.squeeze(tensor)

        return tensor

    @abc.abstractmethod
    def _get_output_tensors(self) -> (np.ndarray, np.ndarray, np.ndarray, np.ndarray):
        """Returns the output tensors."""
        pass

    def _postprocess(self, boxes: np.ndarray, classes: np.ndarray, scores: np.ndarray, count: int,
                     min_confidence: float, max_results: int,
                     added_x: float, scaled_x: float, added_y: float, scaled_y: float) -> List[Detection]:
        """Post-process the output of TFLite model into a list of Detection objects.

        :param boxes: Bounding boxes of detected objects from the TFLite model.
        :param classes: Class index of the detected objects from the TFLite model.
        :param scores: Confidence scores of the detected objects from the TFLite model.
        :param count: Number of detected objects from the TFLite model.
        :param min_confidence: Minimum confidence score of the detected objects.
        :param max_results: Maximum number of the detected objects.

        :return A list of Detection objects detected by the TFLite model.
        """
        results = []

        # Parse the model output into a list of Detection entities.
        for i in range(count):
            if scores[i] >= min_confidence:
                y_min, x_min, y_max, x_max = boxes[i]
                bounding_box = Rect(x_min=(x_min - added_x) / scaled_x, y_min=(y_min - added_y) / scaled_y,
                                    x_max=(x_max - added_x) / scaled_x, y_max=(y_max - added_y) / scaled_y)
                category_id = int(classes[i])
                category_label = self._label_list[category_id] if 0 <= category_id < len(self._label_list) else ""
                category = Category(label=category_label, id=category_id)
                result = Detection(bounding_box=bounding_box, confidence=scores[i], category=category)
                results.append(result)

        # Sort detection results by score ascending
        sorted_results = sorted(results, key=lambda detection: detection.confidence, reverse=True)

        # Filter out detections in deny list
        filtered_results = sorted_results
        if self._options.label_deny_list is not None:
            filtered_results = list(filter(
                lambda detection: detection.categories[0].label not in self._options.label_deny_list, filtered_results))

        # Keep only detections in allow list
        if self._options.label_allow_list is not None:
            filtered_results = list(filter(
                lambda detection: detection.categories[0].label in self._options.label_allow_list, filtered_results))

        # Only return maximum of max_results detection.
        if max_results > 0:
            result_count = min(len(filtered_results), max_results)
            filtered_results = filtered_results[:result_count]

        return filtered_results


class TFLiteEfficientDetDetector(TFLiteDetector):
    """A TFLite detector for EfficientDet models."""

    def __init__(self, model_path: str = 'https://github.com/Yeicor/drone-copilot/releases/download/models/'
                                         'efficientdet_lite0.tflite', options=TFLiteDetectorOptions()):
        super().__init__(model_path, None, options)

    def _on_load_model(self, interpreter: Interpreter) -> ((int, int), bool):
        sorted_output_details_by_index = sorted(interpreter.get_output_details(), key=lambda detail: detail['index'])
        self._output_location_index = sorted_output_details_by_index[0]['index']
        self._output_category_index = sorted_output_details_by_index[1]['index']
        self._output_score_index = sorted_output_details_by_index[2]['index']
        self._output_number_index = sorted_output_details_by_index[3]['index']
        return super()._on_load_model(interpreter)

    def _get_output_tensors(self) -> (np.ndarray, np.ndarray, np.ndarray, np.ndarray):
        return (
            self._get_output_tensor(self._output_location_index),
            self._get_output_tensor(self._output_category_index),
            self._get_output_tensor(self._output_score_index),
            int(self._get_output_tensor(self._output_number_index))
        )
