
# coding: utf-8

# pyMaze expriments

import gym
import numpy as np
import time
#import resource

from diversity_algorithms.controllers import SimpleNeuralController, DNNController
from diversity_algorithms.algorithms import bd_funcs

# Fitness/evaluation function

default_max_step = 2000 # same as C++ sferes experiments


class EvaluationFunctor:
	def __init__(self, env=None, env_name=None, controller=None, controller_type=None, controller_params=None, output='total_reward',max_step=default_max_step, get_behavior_descriptor='auto'):
		global current_serial
		print("Eval functor created")
		#Env
		#Controller
		self.out = output
		self.max_step = max_step
		self.evals = 0
		self.traj=None
		self.controller=controller
		self.controller_type=controller_type
		self.controller_params=controller_params
		if ((env is not None) or (env_name is not None)):
			self.set_env(env,env_name, (get_behavior_descriptor == 'auto'))
		else:
			self.env = None
		if(get_behavior_descriptor != 'auto' and get_behavior_descriptor is not None): #Use provided function
			self.get_behavior_descriptor = get_behavior_descriptor
		
	def set_env(self,env, env_name, with_bd=False):
		if(env is None):
			self.env = gym.make(env_name)
			self.env.reset()
		else:
			self.env = env
		self.env_name = self.env.unwrapped.spec.id
		if(self.controller is None): # Build controller
			if(self.controller_type is None):
				raise RuntimeError("Please either give a controller or specify controller type")
			self.controller = self.controller_type(self.env.observation_space.shape[0],self.env.action_space.shape[0], params=self.controller_params)
		else:
			if(self.controller_type is not None or self.controller_params is not None):
				print("WARNING: EvaluationFunctor built with both controller and controller_type/controller_params. controller_type/controller_params arguments  will be ignored")
		if(with_bd):
			if(self.env_name not in bd_funcs):
				print("WARNING: No BD extraction function known for Gym environment %s." % self.env_name)
				self.get_behavior_descriptor = None
			else:
				self.get_behavior_descriptor = bd_funcs[self.env_name]



	def load_indiv(self, genotype):
		if(self.controller is None):
			print("ERROR: controller is None")
		self.controller.set_parameters(genotype)
	
	
	def evaluate_indiv(self):
		"""
		Evaluate individual genotype (list of controller.n_weights floats) in environment env using
		given controller and max step number, and returns the required output:
		- dist_to_goal: final distance to goal (list of 1 scalar)
		- bd_finalpos: final robot position and orientation (list [x,y,theta])
		- total_reward: cumulated reward on episode (list of 1 scalar)
		"""
		# Inits
		#print("env reset")
		self.evals += 1
		self.traj=[]
		initial_obs = self.env.reset()
		action_scale_factor = self.env.action_space.high # The nn generate an output in ]-1;1[ (tanh out layer); this scales to action space range
		obs = initial_obs
		total_reward = 0.
		# Main loop
		then = time.time()
		for i in range(self.max_step):
			#self.env.render()
			action = action_scale_factor*self.controller(np.array(obs))
			obs, reward, end, info = self.env.step(action) # take a random action
			self.traj.append((obs,reward,end,info))
			total_reward += reward
			#print("Step %d : Obs=%s Action=%s Reward=%f  Dist. to objective=%f  Robot position=%s  End of ep=%s" % (i, str(obs), str(action), reward, info["dist_obj"], str(in	fo["robot_pos"]), str(end)))
			if end:
				break
		now = time.time()
		return reward, end, total_reward, info

        
	def __call__(self, genotype):
		#print("Eval functor CALL")
		# Load genotype
		#print("Load gen")
		if(type(genotype)==tuple):
			gen, ngeneration, idx = genotype
#			print("Start main eval loop -- #%d evals for this functor so far" % self.evals)
#			print("Evaluating indiv %d of gen %d" % (idx, ngeneration))
#			print('Eval thread: memory usage: %s (kb)' % resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
		else:
			gen = genotype
		self.load_indiv(gen)
		# Run eval genotype
		#print("Start eval")
		final_reward, end, total_reward, info = self.evaluate_indiv()
		#print("Eval done !")
		# Select fitness
		
		if(self.out=='total_reward'):
			fitness = [total_reward]
		elif(self.out=='final_reward'):
			fitness = [final_reward]
		elif(self.out==None or self.out=='none'):
			fitness = [None]
		elif(self.out in info.keys):
			fitness = listify(info[self.out])
		else:
			print("ERROR: No known output %s" % output)
			return None
		
		if self.get_behavior_descriptor is None:
			self.traj=None # to avoid taking too much memory
			return fitness
		else:
			bd = self.get_behavior_descriptor(self.traj)
			self.traj=None # to avoid taking too much memory
			return [fitness,bd]

