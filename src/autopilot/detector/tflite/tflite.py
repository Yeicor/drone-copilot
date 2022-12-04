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

import zipfile
from typing import List, NamedTuple, Optional

import cv2
import numpy as np
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


class ObjectDetectorOptions(NamedTuple):
    """A config to initialize an object detector."""

    enable_edgetpu: bool = False
    """Enable the model to run on EdgeTPU."""

    label_allow_list: List[str] = None
    """The optional allow list of labels."""

    label_deny_list: List[str] = None
    """The optional deny list of labels."""

    num_threads: int = 1
    """The number of CPU threads to be used."""


def edgetpu_lib_name():
    """Returns the library name of EdgeTPU in the current platform."""
    return {
        'Darwin': 'libedgetpu.1.dylib',
        'Linux': 'libedgetpu.so.1',
        'Windows': 'edgetpu.dll',
    }.get(platform.system(), None)


class TFLiteDetector:
    """A wrapper class for a TFLite object detection model."""

    _mean = 127.5
    """Default mean normalization parameter for float model."""
    _std = 127.5
    """Default std normalization parameter for float model."""

    _OUTPUT_LOCATION_NAME = 'location'
    _OUTPUT_CATEGORY_NAME = 'category'
    _OUTPUT_SCORE_NAME = 'score'
    _OUTPUT_NUMBER_NAME = 'number of detections'

    def __init__(
            self,
            model_path: Optional[str] = None,
            options: ObjectDetectorOptions = ObjectDetectorOptions()
    ) -> None:
        """Initialize a TFLite object detection model.

        Args:
            model_path: Path to the TFLite model.
            options: The config to initialize an object detector. (Optional)

        Raises:
            ValueError: If the TFLite model is invalid.
            OSError: If the current OS isn't supported by EdgeTPU.
        """
        if model_path is None:
            if platform == 'android':
                model_path = 'autopilot/detector/tflite/efficientdet_lite0_mobile.tflite'
            elif options.enable_edgetpu:
                model_path = 'autopilot/detector/tflite/efficientdet_lite0_edgetpu.tflite'
            else:
                model_path = 'autopilot/detector/tflite/efficientdet_lite0.tflite'

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
            print(
                'ERROR: Please use models trained with Model Maker or downloaded from TensorFlow Hub.'
            )
            raise ValueError('Invalid TFLite model: no metadata found.')

        # Initialize TFLite model.
        if options.enable_edgetpu:
            if edgetpu_lib_name() is None:
                raise OSError("The current OS isn't supported by Coral EdgeTPU.")
            interpreter = Interpreter(
                model_path=model_path,
                experimental_delegates=[load_delegate(edgetpu_lib_name())],
                num_threads=options.num_threads)
        else:
            interpreter = Interpreter(
                model_path=model_path, num_threads=options.num_threads)

        interpreter.allocate_tensors()
        input_detail = interpreter.get_input_details()[0]

        # From TensorFlow 2.6, the order of the outputs became undefined.
        # Therefore, we need to sort the tensor indices of TFLite outputs and to know
        # exactly the meaning of each output tensor. For example, if
        # output indices are [601, 599, 598, 600], tensor names and indices aligned
        # are:
        #   - location: 598
        #   - category: 599
        #   - score: 600
        #   - detection_count: 601
        # because of the op's ports of TFLITE_DETECTION_POST_PROCESS
        # (https://github.com/tensorflow/tensorflow/blob/a4fe268ea084e7d323133ed7b986e0ae259a2bc7/tensorflow/lite/kernels/detection_postprocess.cc#L47-L50).
        sorted_output_indices = sorted(
            [output['index'] for output in interpreter.get_output_details()])
        self._output_indices = {
            self._OUTPUT_LOCATION_NAME: sorted_output_indices[0],
            self._OUTPUT_CATEGORY_NAME: sorted_output_indices[1],
            self._OUTPUT_SCORE_NAME: sorted_output_indices[2],
            self._OUTPUT_NUMBER_NAME: sorted_output_indices[3],
        }

        self.input_size = input_detail['shape'][2], input_detail['shape'][1]
        self._is_quantized_input = input_detail['dtype'] == np.uint8
        self._interpreter = interpreter
        self._options = options

    def webcam(self, img: np.ndarray, min_confidence: float = 0.5, max_results: int = -1) -> List[Detection]:
        image_height, image_width, _ = img.shape

        input_tensor = self._preprocess(img)

        self._set_input_tensor(input_tensor)
        self._interpreter.invoke()

        # Get all output details
        boxes = self._get_output_tensor(self._OUTPUT_LOCATION_NAME)
        classes = self._get_output_tensor(self._OUTPUT_CATEGORY_NAME)
        scores = self._get_output_tensor(self._OUTPUT_SCORE_NAME)
        count = int(self._get_output_tensor(self._OUTPUT_NUMBER_NAME))

        return self._postprocess(boxes, classes, scores, count, image_width, image_height, min_confidence, max_results)

    def _preprocess(self, input_image: np.ndarray) -> np.ndarray:
        """Preprocess the input image as required by the TFLite model."""

        # Resize the input
        input_tensor = cv2.resize(input_image, self.input_size)

        # Normalize the input if it's a float model (aka. not quantized)
        if not self._is_quantized_input:
            input_tensor = (np.float32(input_tensor) - self._mean) / self._std

        # Add batch dimension
        input_tensor = np.expand_dims(input_tensor, axis=0)

        return input_tensor

    def _set_input_tensor(self, image):
        """Sets the input tensor."""
        tensor_index = self._interpreter.get_input_details()[0]['index']
        input_tensor = self._interpreter.tensor(tensor_index)()[0]
        input_tensor[:, :] = image

    def _get_output_tensor(self, name):
        """Returns the output tensor at the given index."""
        output_index = self._output_indices[name]
        tensor = np.squeeze(self._interpreter.get_tensor(output_index))
        return tensor

    def _postprocess(self, boxes: np.ndarray, classes: np.ndarray, scores: np.ndarray, count: int, image_width: int,
                     image_height: int, min_confidence: float, max_results: int) -> List[Detection]:
        """Post-process the output of TFLite model into a list of Detection objects.

        Args:
            boxes: Bounding boxes of detected objects from the TFLite model.
            classes: Class index of the detected objects from the TFLite model.
            scores: Confidence scores of the detected objects from the TFLite model.
            count: Number of detected objects from the TFLite model.
            image_width: Width of the input image.
            image_height: Height of the input image.

        Returns:
            A list of Detection objects detected by the TFLite model.
        """
        results = []

        # Parse the model output into a list of Detection entities.
        for i in range(count):
            if scores[i] >= min_confidence:
                y_min, x_min, y_max, x_max = boxes[i]
                bounding_box = Rect(top=int(y_min * image_height), left=int(x_min * image_width),
                                    bottom=int(y_max * image_height), right=int(x_max * image_width))
                class_id = int(classes[i])
                category = Category(label=self._label_list[class_id], id=class_id)
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
