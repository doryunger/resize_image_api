import cv2
import os
import tensorflow as tf
from api import celery
import numpy as np
import base64
from api.logger import init_logger

root_path = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
dir=str(root_path + os.sep + 'Logs')
debug_log_filename = root_path + os.sep + 'Logs' + os.sep + 'service.log'
if os.path.isdir(dir):
	pass
else:
	os.makedirs(dir)
	os.chmod(dir, 0o777)
log = init_logger(debug_log_filename, 'log')

@celery.task()
def videoHandle(img):
    try:
        buf_decode = base64.b64decode(img)
        buf_arr = np.fromstring(buf_decode, dtype=np.uint8)
        image=cv2.imdecode(buf_arr, cv2.IMREAD_UNCHANGED)
    except:
        log.error('binary encoding failed')
    #wrapping the method in a Tensorflow session to improve the perforrmance
    with tf.compat.v1.Session() as sess:
        try:
            height, width, layers = image.shape
            new_h = int(height / 2)
            new_w = int(width / 2)
            resize = cv2.resize(image, (new_w, new_h))
            retval, buffer = cv2.imencode('.jpg', resize)
            img = base64.b64encode(buffer)
        except:
            log.error('conversion failed')
        return img
