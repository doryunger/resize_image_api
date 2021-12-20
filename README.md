# Resize Image API

### Overview:
The video resize app is a service that allows clients to resize single video frames. The
service is based on flask as a REST API and celery for managing asynchronous task
queue/job queue (having RabbitMQ as broker). The video processing is made by 'opencv' library which except for being useful for processing video files it also includes an inner
class (UMat) which utilizes some 'open-cl' components.

### Functionality:
The service is having only one method which converting a single data frame and returning
a resized frame to the client. The method checks whether the frame has been encoded
or not and decodes them respectively.

### Performance:
For the sake of efficiency, I used UMat class for the critical computation of the frames'
conversion. Since the class 'wrapping up' open-cl components it also allows utilization of
GPU (in case the machine equipped with a GPU). The images undergo a decoding
process in order to diminish their size (the images encoded to their original format only
when saved to disk as they should be human-readable). 

### Testing:
The service's performance and functionality have been tested by a designated program.
The program operates as a CLI which gets 3 variables (all of them are required for the
operation):
1. Number of instances (-N)
2. The interval between the execution of each instance (in seconds) (-M)
3. The file path (the program will only process video files) (-P)
The program initializes the instances parallelly, which imitates concurrent use in the
service. The process of each instance includes the extraction of a single video frame and
storing them on the disk. The output of the test is a csv file with a runtime metrics of each
instance. 