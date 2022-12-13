import os
import time

import plyer
from PIL import Image
from kivy import Logger


def save_image_to_pictures(img: Image, kind='screenshot'):
    start_time = time.time()
    pictures_dir = plyer.storagepath.get_pictures_dir()
    if 'DroneCopilot' not in os.listdir(pictures_dir):
        os.mkdir(os.path.join(pictures_dir, 'DroneCopilot'))
    if kind not in os.listdir(os.path.join(pictures_dir, 'DroneCopilot')):
        os.mkdir(os.path.join(pictures_dir, 'DroneCopilot', kind))
    filename = time.strftime('%Y%m%d-%H%M%S') + '.jpg'
    filepath = os.path.join(pictures_dir, 'DroneCopilot', kind, filename)
    img.save(filepath)
    Logger.info('DroneCopilotApp: App screenshot saved at "%s" in %f seconds' % (filepath, time.time() - start_time))
