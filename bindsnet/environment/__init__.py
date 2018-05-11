import os
import sys
import gym
import torch
import numpy as np
import matplotlib.pyplot as plt

from ..datasets.preprocess import *
from ..encoding            import *
from ..datasets            import *


class DatasetEnvironment:
	'''
	A wrapper around any object from the :code:`datasets` module to pass to the :code:`Pipeline` object.
	'''
	def __init__(self, dataset=MNIST, train=True, time=350, **kwargs):
		'''
		Initializes the environment wrapper around the dataset.
		
		Inputs:
		
			| :code:`dataset` (:code:`bindsnet.dataset.Dataset`): Object from datasets module.
			| :code:`train` (:code:`bool`): Whether to use train or test dataset.
			| :code:`time` (:code:`time`): Length of spike train per example.
			| :code:`intensity` (:code:`intensity`): Raw data is multiplied by this value.
		'''
		self.dataset = dataset
		self.train = train
		self.time = time
		
		if 'intensity' in kwargs:
			self.intensity = kwargs['intensity']
		else:
			self.intensity = 1
		
		if 'max_prob' in kwargs:
			self.max_prob = max_prob
		else:
			self.max_prob = 1
		
		if train:
			self.data, self.labels = self.dataset.get_train()
			self.label_loader = iter(self.labels)
		else:
			self.data, self.labels = self.dataset.get_test()
			self.label_loader = iter(self.labels)
		
		self.env = iter(self.data)
	
	def step(self, a=None):
		'''
		Dummy function for OpenAI Gym environment's :code:`step()` function.
		
		Inputs:
		
			| :code:`a` (:code:`None`): There is no interaction of the network with the MNIST dataset.

		Returns:

			| :code:`obs` (:code:`torch.Tensor`): Observation from the environment (spike train-encoded MNIST digit).
			| :code:`reward` (:code:`float`): Fixed to :code:`0`.
			| :code:`done` (:code:`bool`): Fixed to :code:`False`.
			| :code:`info` (:code:`dict`): Contains label of MNIST digit.
		'''
		try:
			# Attempt to fetch the next observation.
			self.obs = next(self.env)
		except StopIteration:
			# If out of samples, reload data and label generators.
			self.env = iter(data)
			self.label_loader = iter(self.labels)
			self.obs = next(self.env)
		
		# Preprocess observation.
		self.preprocess()
		
		# Info dictionary contains label of MNIST digit.
		info = {'label' : next(self.label_loader)}
		
		return self.obs, 0, False, info
	
	def reset(self):
		'''
		Dummy function for OpenAI Gym environment's :code:`reset()` function.
		'''
		# Reload data and label generators.
		self.env = iter(self.data)
		self.label_loader = iter(self.labels)
	
	def render(self):
		'''
		Dummy function for OpenAI Gym environment's :code:`render()` function.
		'''
		pass

	def close(self):
		'''
		Dummy function for OpenAI Gym environment's :code:`close()` function.
		'''
		pass
	
	def preprocess(self):
		'''
		Preprocessing step for a state specific to the MNIST dataset.

		Inputs:

			| (:code:`numpy.array`): Observation from the environment.

		Returns:

			| (:code:`torch.Tensor`): Pre-processed observation.
		'''
		self.obs = self.obs.view(-1)
		self.obs *= self.intensity


class GymEnvironment:
	'''
	A wrapper around the OpenAI :code:`gym` environments.
	'''
	def __init__(self, name, **kwargs):
		'''
		Initializes the environment wrapper.

		Inputs:

			| :code:`name` (:code:`str`): The name of an OpenAI :code:`gym` environment.
			| :code:`max_prob` (:code:`float`): Maximum spiking probability.
		'''
		self.name = name
		self.env = gym.make(name)
		self.action_space = self.env.action_space
		
		if 'max_prob' in kwargs:
			self.max_prob = kwargs['max_prob']
		else:
			self.max_prob = 1
		
		assert self.max_prob > 0 and self.max_prob <= 1, 'Maximum spiking probability must be in (0, 1].'

	def step(self, a):
		'''
		Wrapper around the OpenAI Gym environment :code:`step()` function.

		Inputs:

			| :code:`a` (:code:`int`): Action to take in SpaceInvaders environment.

		Returns:

			| :code:`obs` (:code:`torch.Tensor`): Observation from the environment.
			| :code:`reward` (:code:`float`): Reward signal from the environment.
			| :code:`done` (:code:`bool`): Indicates whether the simulation has finished.
			| :code:`info` (:code:`dict`): Current information about the environment.
		'''
		# Call gym's environment step function.
		self.obs, self.reward, done, info = self.env.step(a)
		self.preprocess()

		# Return converted observations and other information.
		return self.obs, self.reward, done, info

	def reset(self):
		'''
		Wrapper around the OpenAI Gym environment :code:`reset()` function.

		Returns:

			| :code:`obs` (:code:`torch.Tensor`): Observation from the environment.
		'''
		# Call gym's environment reset function.
		self.obs = self.env.reset()
		self.preprocess()
		
		return self.obs

	def render(self):
		'''
		Wrapper around the OpenAI Gym environment :code:`render()` function.
		'''
		self.env.render()

	def close(self):
		'''
		Wrapper around the OpenAI Gym environment :code:`close()` function.
		'''
		self.env.close()

	def preprocess(self):
		'''
		Preprocessing step for an observation from the Space Invaders environment.
		'''
		if self.name == 'CartPole-v0':
			self.obs = np.array([self.obs[0] + 2.4, -min(self.obs[1], 0), max(self.obs[1], 0),
								 self.obs[2] + 41.8, -min(self.obs[3], 0), max(self.obs[3], 0)])
		elif self.name == 'SpaceInvaders-v0':
			self.obs = subsample(gray_scale(self.obs), 84, 110)
			self.obs = self.obs[26:104, :]
			self.obs = binary_image(self.obs)
			self.obs_shape = (78, 84)
		else:
			assert self.obs.shape == (210, 160, 3), 'Environment not supported.'
			
			self.obs = subsample(gray_scale(self.obs), 84, 110)
			self.obs = binary_image(self.obs)
			self.obs_shape = (110, 84)
		
		self.obs = torch.from_numpy(self.obs).view(-1).float()