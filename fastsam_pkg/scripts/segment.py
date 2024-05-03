#!/usr/bin/env python3
import sys
import rospy, rospkg
from sensor_msgs.msg import Image
package_path = rospkg.RosPack().get_path("fastsam_pkg")
sys.path.append(package_path  + "/FastSAM/")
from fastsam import FastSAM, FastSAMPrompt
from fastsam_pkg.srv import prompt 
from cv_bridge import CvBridge, CvBridgeError
import  pathlib

'''
Example
class SamNode:
    def __init__(self):
        self.server
        self.subscriber
        self.SAM
        self.publisher
        self.objext_name = None

    def callbackfunction(self, image):
        result_image = self.SAM(image, self.object_name)
        self.publisher..

    def serverfunction(self, request):
        self.object_name = request.object_name

'''

class Segmenter():
    def __init__(self):
        # ROS Parameters
        self._weights = pathlib.Path(rospy.get_param("~weights", 'FastSAM-x.pt'))
        if not self._weights.is_absolute():
            self._weights = pathlib.Path(__file__).absolute().parent.parent / self._weights
        if not self._weights.exists():
            rospy.logerr(f"Weights '{self._weights.as_posix()}' do not exist!")
            rospy.signal_shutdown(f"Weights '{self._weights.as_posix()}' do not exist!")
            sys.exit(1)

        self._imgsz = rospy.get_param("~image_size", 1024)
        self._conf_thr = rospy.get_param("~confidence_threshold", 0.4)
        self._iou_thr = rospy.get_param("~iou_threshold", 0.9)
        self._device = rospy.get_param("~device", "cuda")

        self.bridge = CvBridge()

        # Model
        self.model = FastSAM(self._weights)

        # Add Subscriber and publisher
        self.in_topic = "head_camera/rgb/image_rect_color"
        self.out_topic = "head_camera/seg/image_rect_color"
        self.image_sub = rospy.Subscriber(self.in_topic, Image, self.callback)
        self.image_pub = rospy.Publisher(self.out_topic, Image, queue_size = 10)
        
        self.prompt_service = rospy.Service("set_prompt", prompt, self.set_prompt)
        self.prompt = None 

        # Making the algorithm faster
        self.counter = 0
        self.run_every = 10
    
    def callback(self, msg):
        if self.counter % self.run_every == 0:
            img = self.bridge.imgmsg_to_cv2(msg, desired_encoding="passthrough")
            results = self.model(img, device=self._device, imgsz=self._imgsz, \
                                conf=self._conf_thr, iou=self._iou_thr)
            prompt_process = FastSAMPrompt(img, results, device=self._device)
            if self.prompt:
                annotations = prompt_process.text_prompt(text=self.prompt)
            else:
                annotations = prompt_process.everything_prompt()

            res_img = prompt_process.plot_to_result(annotations=annotations, withContours=False)
            self.result = self.bridge.cv2_to_imgmsg(res_img, "passthrough")

        # Publish the image
        self.image_pub.publish(self.result)
        self.counter += 1
    
    def set_prompt(self, request):
        if request.name == "None":
            self.prompt = None 
            return
        self.prompt = request.name
        return True

if __name__ == "__main__":
    print("Node initialized")
    
    rospy.init_node('segment', anonymous=True)
    segmenter = Segmenter()
    
    while not rospy.is_shutdown():
        rospy.spin()