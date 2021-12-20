import argparse
import pathlib
import shutil
import csv
from time import sleep
import time
import logging
from logging.handlers import RotatingFileHandler
import requests
import os
import inspect
import sys
from threading import Thread, Event, Timer
import queue
import cv2
import base64
import numpy as np
from api.logger import init_logger

root_path = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
debug_log_filename = root_path + os.sep + 'Logs' + os.sep + 'debug.log'
log = init_logger(debug_log_filename, 'log')

ALLOWED_EXTENSIONS = set(['wmv','mp4','mov','avi','mpeg','mpg'])
requestStatus={}
def allowed_file(filename):
    if '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS:
        return True
    else:
        return False

class api_test:

    def __init__(self):
        self.queue_results = queue.Queue()

        # test start and end time
        self.start_time = 0
        self.end_time = 0

        # request per second
        # self.rps_min = 0
        self.rps_mean = 0
        # self.rps_max = 0
        self.total_tested_requests = 0
        self.total_tested_time = 0
        self.total_pass_requests = 0

        # time per request
        self.tpr_min = 999
        self.tpr_mean = 0
        self.tpr_max = 0
        self.sum_response_time = 0

        self.total_fail_requests = 0
        self.total_exception_requests = 0


        self.event_test_done = Event()



    # start mock service first: python flask_mock_service.py
    # Then run the tests.
    def service_test(self,image):
        log.info('Calling %s.' % inspect.stack()[0][3])
        url = 'http://127.0.0.1:5000/file-upload'
        file = {'file':image}
        resp = requests.post(url, files=file)
        if resp == None:
            log.error('Test %s failed with exception.' % inspect.stack()[0][3])
            return 'exception', None
        elif resp.status_code == 400:
            log.error('Test %s failed with response status code %s.' % (inspect.stack()[0][3], resp.status_code))
            return 'fail', resp.elapsed.total_seconds()
        elif resp.status_code == 500:
            log.error('Test %s failed with response status code %s.' % (inspect.stack()[0][3], resp.status_code))
            return 'fail', resp.elapsed.total_seconds()
        # elif resp.json()["code"] != 1:
        #     log.error('Test %s failed with code %s != 1.' % (inspect.stack()[0][3], resp.json()["code"]))
        #     return 'fail', resp.elapsed.total_seconds()
        else:
            #print(resp.elapsed.total_seconds())
            data = resp.json()
            img=data['file']
            #print(data)
            log.info('Test %s passed.' % inspect.stack()[0][3])
            return 'pass', resp.elapsed.total_seconds(),img

    def instance_test(self,instance_num ):
        start_time_instance = time.time()
        current_location = pathlib.Path(__file__).parent.absolute()
        num = int(instance_num) + 1
        path=args.path
        dir=str(current_location)+'/converted frames/instance'+str(num)
        if os.path.isdir(dir):
            shutil.rmtree(dir)
        os.makedirs(dir)
        os.chmod(dir, 0o777)
        instance='instance: '+str(num)
        try:
            vidcap = cv2.VideoCapture(path)
        except:
            log.error('Video file is courrupted')
        success, image = vidcap.read()
        count = 0;
        average=0
        duration=0
        array=[]
        success = True
        while success:
            try:
                session_start_time=time.time()
                retval, buffer = cv2.imencode('.jpg', image)
                img = base64.b64encode(buffer)
            except:
                log.error('Binary conversion failed')
            test_result, elapsed_time,img = self.service_test(img)
            buf_decode = base64.b64decode(img)
            buf_arr = np.fromstring(buf_decode, dtype=np.uint8)
            image = cv2.imdecode(buf_arr, cv2.IMREAD_UNCHANGED)
            try:
                cv2.imwrite(dir+'/'+"frame%03d.jpg" % count, image)
            except:
                log.error("Couldn't write file to disk at this path %d" %dir)
            session_end_time = time.time()
            session_duration=(time.asctime(), session_end_time - session_start_time)
            self.queue_results.put(['service_test', test_result, session_duration[1], instance])
            success, image = vidcap.read()
            count+=1
            duration = duration + average
            average = (session_duration[1] + duration) / count
        count-=1
        end_time_instance = time.time()
        self.queue_results.put(['total',start_time_instance,end_time_instance,average,duration,count,instance])

    def stats_accumlation(self,instances=0):
        """ calculate statistics """
        end_time = time.time()
        current_instance = 1
        dict={}
        arr=[]
        arr_time=[]
        if instances > 0:
            for n in range(0,instances):
                dict['instance: '+str(n+1)]=[]
        # get the approximate queue size
        qsize = self.queue_results.qsize()
        loop = 0
        for i in range(qsize):
            try:
                result = self.queue_results.get_nowait()
                loop += 1
            except queue.Empty:
                break
            if result[1] == 'exception':
                self.total_exception_requests += 1
            elif result[1] == 'fail':
                self.total_fail_requests += 1
            elif result[1] == 'pass':
                self.total_pass_requests += 1
                self.sum_response_time += result[2]
                if result[2] < self.tpr_min:
                    self.tpr_min = result[2]
                if result[2] > self.tpr_max:
                    self.tpr_max = result[2]
            if result[0] == 'total':
                dict[result[6]].append(result[3])
            if result[0]=='total':
                dict[result[6]].append(time.strftime('%H:%M:%S', time.localtime(result[2])))
            if result[0]=='total':
                dict[result[6]].append(result[4])
            if result[0] == 'total':
                dict[result[6]].append(result[5])

        self.total_tested_requests += loop
        self.total_tested_requests=self.total_tested_requests-(instances*2)
        self.total_pass_requests=self.total_pass_requests-(instances)
        # time per requests mean (avg)
        if self.total_pass_requests != 0:
            self.tpr_mean = self.sum_response_time / self.total_pass_requests
        # requests per second
        if self.start_time == 0:
            log.error('stats: self.start_time is not set, skipping rps stats.')
        else:
            # calc the tested time so far.
            tested_time = end_time - self.start_time
            self.rps_mean = self.total_pass_requests / tested_time

        # print stats
        print('\n-----------------Test Statistics---------------')
        print(time.asctime())
        print('Total requests: %s, pass: %s, fail: %s, exception: %s'
              % (self.total_tested_requests, self.total_pass_requests, self.total_fail_requests,
                 self.total_exception_requests)
              )
        if self.total_pass_requests > 0:
            print('For pass requests:')
            print('Request per Second - mean: %.2f' % self.rps_mean)
            print('Time per Request   - mean: %.2f, min: %.2f, max: %.2f'
                  % (self.tpr_mean, self.tpr_min, self.tpr_max)
                  )
        with open('Test_Results.csv','w',newline='') as file:
            writer=csv.writer(file)
            writer.writerow(['Test API Results'])
            writer.writerow(['Results Per Instance'])
            writer.writerow(['Instance Number','Average Frame Conversion Time','End Time','Duration','Total Converted Frames'])
            for n in range(0,instances):
                num=n+1
                writer.writerow(['Instance '+str(num),str(round(dict['instance: '+str(num)][0],2))+' seconds',dict['instance: '+str(num)][1],str(round(dict['instance: '+str(num)][2],2))+' seconds',dict['instance: '+str(num)][3]])
            writer.writerow(['General Statistics'])
            writer.writerow(['Total Requests: ',self.total_tested_requests])
            writer.writerow(['Pass: ',self.total_pass_requests])
            writer.writerow(['Fail: ', self.total_fail_requests])
            writer.writerow(['Exception: ', self.total_exception_requests])
            writer.writerow([''])
            writer.writerow(['Request per Second (mean): ',str(round(self.rps_mean,2))+' seconds'])
            writer.writerow(['Time per Request (mean): ', str(round(self.tpr_mean,2))+' seconds', 'min: ',str(round(self.tpr_min,2))+' seconds','max: ',str(round(self.tpr_max,2))+' seconds'])
            writer.writerow([''])
            writer.writerow(['Exuction Details: ','Number of Instances', args.instances, 'Interval Between Instances',args.interval])


    def iterate_stats(self, interval=1):
        # while True:
        while (self.event_test_done.is_set()):
            sleep(interval)
            self.stats_accumlation()

def tester(args):
    concurrent_users = args.instances
    # test stops whenever loop_times or test_time is met first.
    loop_times = 1
    #test_time = 3600  # time in seconds, e.g. 36000
    stats_interval = 5
    path=args.path
    ramp_up = args.interval  # total time in secs to ramp up. default 0, no wait
    count=0
    api_test_script = api_test()
    workers = []
    start_time = time.time()
    api_test_script.start_time = start_time
    print('Tests started at %s.' % time.asctime())
    # start stats thread
    stats_thread = Thread(target=api_test_script.iterate_stats(), args=[stats_interval], daemon=True)
    stats_thread.start()

    # start concurrent user threads
    for i in range(concurrent_users):
        #print(i)
        thread = Thread(target=api_test_script.instance_test(i),kwargs={'path':path}, daemon=True)
        thread.start()
        workers.append(thread)
        # ramp up wait
        sleep(ramp_up)

    for py_worker in workers:
        py_worker.join()

    end_time = time.time()
    api_test_script.end_time = end_time
    api_test_script.stats_accumlation(instances=concurrent_users)

    print('\nTests ended at %s.\nTotal test time: %.2f seconds.' % (time.asctime(), end_time - start_time))


def parse_args():
    current_location = pathlib.Path(__file__).parent.absolute()
    parser=argparse.ArgumentParser(description="Process API test")
    parser.add_argument('-N','--instances',action='store',type=int,default=5,help='number of instances (deafult=5)',required=True)
    parser.add_argument('-M', '--interval', action='store', type=int, default=10,help='interval duration between instances (deafult=10)',required=True)
    parser.add_argument('-P', '--path', action='store', type=str,default=current_location ,help='location of the video file (deafult= ./)',required=True)
    return parser.parse_args()

if __name__ == '__main__':
    args=parse_args()
    tester(args)
