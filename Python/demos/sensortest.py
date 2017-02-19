from klampt import vis
from klampt import *
from klampt.math import so3,se3,vectorops
from klampt.vis.glcommon import *
from klampt.model import sensing
import time
import random

import matplotlib.pyplot as plt

firsttime = True
images = []

def processDepthSensor(sensor):
	"""
	#manual processing
	data = sensor.getMeasurements()
	w = int(sensor.getSetting("xres"))
	h = int(sensor.getSetting("yres"))
	#first, RGB then depth
	mind,maxd = float('inf'),float('-inf')
	for i in range(h):
		for j in range(w):
			pixelofs = (j+i*w)
			rgb = int(data[pixelofs])
			depth = data[pixelofs+w*h]
			mind = min(depth,mind)
			maxd = max(depth,maxd)
	print "Depth range",mind,maxd
	"""
	rgb,depth = sensing.camera_to_images(sensor)
	return rgb,depth

world = WorldModel()
world.readFile("../../data/simulation_test_worlds/sensortest.xml")
#world.readFile("../../data/tx90scenario0.xml")
robot = world.robot(0)

vis.add("world",world)

sim = Simulator(world)
sensor = sim.controller(0).sensor("rgbd_camera")
print sensor.getSetting("link")
print sensor.getSetting("Tsensor")
#T = (so3.sample(),[0,0,1.0])
T = ([1,0,0, 0,0,-1,  0,1,0],[0,-2.0,0.5])
sensing.set_sensor_xform(sensor,T,link=-1)

vis.add("sensor",sensor)

read_local = True

#Note: GLEW sensor simulation only runs if it occurs in the visualization thread (e.g., the idle loop)
class SensorTestWorld (GLPluginInterface):
	def __init__(self):
		GLPluginInterface.__init__(self)
		robot.randomizeConfig()
		#sensor.kinematicSimulate(world,0.01)
		sim.controller(0).setPIDCommand(robot.getConfig(),[0.0]*7)

		self.rgb=None
		self.depth=None
		self.compute_pc = False
		self.pc = None
		self.pc_appearance = None

		def randomize():
			robot.randomizeConfig()
			sim.controller(0).setPIDCommand(robot.getConfig(),[0.0]*7)
		def plot_rgb():
			if self.rgb is not None:
				plt.imshow(self.rgb)
				plt.show()
		def plot_depth():
			if self.depth is not None:
				plt.imshow(self.depth)
				plt.show()
		def toggle_point_cloud():
			self.compute_pc = not self.compute_pc

		self.add_action(randomize,'Randomize configuration',' ')
		self.add_action(plot_rgb,'Plot color','c')
		self.add_action(plot_depth,'Plot depth','d')
		self.add_action(toggle_point_cloud,'Toggle point cloud drawing','p')

	def idle(self):
		#print "Idle..."
		#this uses the simulation
		sim.simulate(0.01)
		sim.updateWorld()
		#this commented out line just uses the world and kinematic simulation
		#sensor.kinematicSimulate(world,0.01)
		try:
			#self.rgb,self.depth = processDepthSensor(sensor)
			if self.compute_pc:
				t0 = time.time()
				if read_local:
					#local point cloud
					#self.pc = sensing.camera_to_points(sensor,points_format='numpy',color_format='rgb')
					#self.pc = sensing.camera_to_points(sensor,points_format='native')
					self.pc = sensing.camera_to_points(sensor,points_format='Geometry3D',all_points=True,color_format='rgb')
					self.pc.setCurrentTransform(*T)
					self.pc_appearance = Appearance()
				else:
					#world point cloud
					#self.pc = sensing.camera_to_points_world(sensor,robot,points_format='numpy')
					self.pc = sensing.camera_to_points_world(sensor,robot,points_format='Geometry3D',color_format='rgb')
					self.pc_appearance = Appearance()
				print "Read and process PC time",time.time()-t0
		except Exception as e:
			print e
			import traceback
			traceback.print_exc()
			exit(-1)
		return True

	def display(self):
		GLPluginInterface.display(self)
		if self.pc is not None and self.compute_pc:
			#manual drawing of native or numpy point clouds
			t0 = time.time()
			if isinstance(self.pc,Geometry3D):
				#Geometry3D drawing
				self.pc_appearance.drawWorldGL(self.pc)
			else:
				glDisable(GL_LIGHTING)
				glPointSize(5.0)
				glColor3f(0,0,0)
				glBegin(GL_POINTS)
				for pt in self.pc:
					if len(pt) == 6:
						glColor3f(*pt[3:6])
					if read_local:
						glVertex3fv(se3.apply(T,pt[0:3]))
					else:
						glVertex3fv(pt[0:3])
				glEnd()
			print "Draw PC time",time.time()-t0
		return True

vis.pushPlugin(SensorTestWorld())
vis.show()
while vis.shown():
	time.sleep(0.1)
vis.kill()

"""
#Note: GLEW doesn't work in this thread.  This code falls back to the non-accelerated sensor simulation

vis.show()
time.sleep(0.5)

for sample in range(10):
	vis.lock()
	robot.randomizeConfig()
	#sensor.kinematicSimulate(world,0.01)
	sim.controller(0).setPIDCommand(robot.getConfig(),[0.0]*7)
	vis.unlock()
	for i in range(100):
		sim.simulate(0.01)
		vis.lock()
		sim.updateWorld()
		vis.unlock()
		time.sleep(0.002)

	processDepthSensor()
	raw_input()

vis.hide()
vis.kill()
"""
