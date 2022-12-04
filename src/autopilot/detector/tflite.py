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
import zipfile
from typing import List, NamedTuple, Optional

import cv2
import numpy as np
import plyer
from kivy import Logger
from kivy.utils import platform

from autopilot.detector.api import Detection, Category, Rect

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


class TFLiteDetector:
    """A wrapper class for a TFLite object detection model."""

    def __init__(self, model_path: str, labels: Optional[List[str]] = None,
                 options: TFLiteDetectorOptions = TFLiteDetectorOptions()) -> None:
        """Initialize a TFLite object detection model.

        :param model_path: Path to the TFLite model.
        :param labels: List of labels for the model. They will be automatically retrieved from the model if available.
        :param options: The config to initialize an object detector.
        """
        self._options = options

        # Download the model if it's a remote URL.
        if model_path.startswith('http'):
            model_path = tf.keras.utils.get_file(origin=model_path, cache_subdir='.models',
                                                 cache_dir=plyer.storagepath.get_application_dir())

        # Load label list from metadata.
        try:
            with zipfile.ZipFile(model_path) as model_with_metadata:
                if not model_with_metadata.namelist():
                    raise ValueError('Invalid TFLite model: no label file found.')

                file_name = model_with_metadata.namelist()[0]
                with model_with_metadata.open(file_name) as label_file:
                    label_list = label_file.read().splitlines()
                    self._label_list = [label.decode('ascii') for label in label_list]
        except zipfile.BadZipFile:
            Logger.warn('No metadata found in the model, using the provided label list or no labels.')
            self._label_list = labels or []

        Logger.info("TFLiteDetector: labels: %s" % self._label_list)

        # Initialize TFLite model.
        if options.enable_edgetpu:
            if libedgetpu_name() is None:
                raise OSError("The current OS isn't supported by Coral EdgeTPU.")
            self._interpreter = Interpreter(model_path=model_path, num_threads=options.num_threads,
                                            experimental_delegates=[load_delegate(libedgetpu_name())])
        else:
            self._interpreter = Interpreter(model_path=model_path, num_threads=options.num_threads)

        self._interpreter.allocate_tensors()

        self.input_size, self._is_quantized_input = self._on_load_model(self._interpreter)
        Logger.info('TFLiteDetector: input_size: %s' % str(self.input_size))

    @abc.abstractmethod
    def _on_load_model(self, interpreter: Interpreter) -> ((int, int), bool):
        """A hook to be called when the model is loaded. Returns the input size of the model."""
        input_detail = interpreter.get_input_details()[0]
        return (input_detail['shape'][2], input_detail['shape'][1]), input_detail['dtype'] == np.uint8

    def detect(self, img: np.ndarray, min_confidence: float = 0.5, max_results: int = -1) -> List[Detection]:
        image_height, image_width, _ = img.shape

        # Prepare input tensor.
        input_tensor = self._preprocess(img)
        self._set_input_tensor(input_tensor)

        # Run inference.
        self._interpreter.invoke()

        # Get all output details
        boxes, classes, scores, count = self._get_output_tensors()

        # Postprocess detections and return the result.
        return self._postprocess(boxes, classes, scores, count, image_width, image_height, min_confidence, max_results)

    def _preprocess(self, input_image: np.ndarray) -> np.ndarray:
        """Preprocess the input image as required by the TFLite model."""

        # Resize the input (if needed)
        if input_image.shape[:2] == self.input_size:
            preprocessed = input_image
        else:
            preprocessed = cv2.resize(input_image, self.input_size)

        # Normalize the input if it's a float model (aka. not quantized)
        if not self._is_quantized_input:
            preprocessed = (np.float32(preprocessed) - 127.5) / 127.5  # uint8 --> float32 [0, 1]

        return preprocessed

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

    def _postprocess(self, boxes: np.ndarray, classes: np.ndarray, scores: np.ndarray, count: int, image_width: int,
                     image_height: int, min_confidence: float, max_results: int) -> List[Detection]:
        """Post-process the output of TFLite model into a list of Detection objects.

        :param boxes: Bounding boxes of detected objects from the TFLite model.
        :param classes: Class index of the detected objects from the TFLite model.
        :param scores: Confidence scores of the detected objects from the TFLite model.
        :param count: Number of detected objects from the TFLite model.
        :param image_width: Width of the input image.
        :param image_height: Height of the input image.
        :param min_confidence: Minimum confidence score of the detected objects.
        :param max_results: Maximum number of the detected objects.

        :return A list of Detection objects detected by the TFLite model.
        """
        results = []

        # Parse the model output into a list of Detection entities.
        for i in range(count):
            if scores[i] >= min_confidence:
                y_min, x_min, y_max, x_max = boxes[i]
                bounding_box = Rect(top=int(y_min * image_height), left=int(x_min * image_width),
                                    bottom=int(y_max * image_height), right=int(x_max * image_width))
                class_id = int(classes[i])
                category = Category(label=self._label_list[class_id] if 0 <= class_id < len(self._label_list) else "",
                                    id=class_id)
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
