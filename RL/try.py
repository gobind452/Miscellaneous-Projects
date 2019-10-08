import gym
import gym_dino
import time
import torch.nn as nn
import torch.optim as optim
import torch
import torch.nn.functional as F
from torch.autograd import Variable
import numpy as np
import gc

episodes = 1000
gamma = 0.9
epsilon = 0.6
batch_size = 50
training_epochs = 10

rewards = []

def discountRewards():
	global rewards
	for i in range(len(rewards)-2,-1,-1):
		rewards[i] = rewards[i] + gamma*rewards[i+1]
	if net.rewards.dim() != 0:
		net.rewards = torch.cat((net.rewards,torch.Tensor(rewards)))
	else:
		net.actions = (torch.Tensor(rewards))
	rewards[:] = []
	return

class Actor(nn.Module):
	def __init__(self):
		super(Actor,self).__init__()
		self.fc1 = nn.Linear(in_features=9,out_features=8)
		self.fc2 = nn.Linear(in_features=8,out_features=6)
		self.fc3 = nn.Linear(in_features=6,out_features=3)
		self.policy_history = torch.Tensor()
		self.rewards = torch.Tensor()

	def forward(self, x):
		x = self.fc3(F.relu(self.fc2(F.relu(self.fc1(x)))))
		x = F.softmax(x, dim=-1)
		return x

	def policy(self,observation):
		prob = self.forward(torch.Tensor(observation))
		dist = prob.detach().numpy()
		action = np.random.choice(a=3,p=dist)
		return action

	def updateTarget(self,observation):
		prob = self.forward(torch.Tensor(observation))
		log_prob = torch.log(prob[action])
		if self.policy_history.dim() != 0:
			self.policy_history = torch.cat((self.policy_history,log_prob.view(-1)))
		else:
			self.policy_history = (log_prob)

class QEstimator(nn.Module):
	def __init__(self):
		super(QEstimator,self).__init__()
		self.fc1 = nn.Linear(in_features=12,out_features=8)
		self.fc2 = nn.Linear(in_features=8,out_features=5)
		self.fc3 = nn.Linear(in_features=5,out_features=1)
		self.prev_states = torch.Tensor()
		self.next_states = torch.Tensor()
		self.rewards = torch.Tensor()
		self.actions = torch.Tensor()

	def forward(self,x,action):
		x = torch.cat((x,torch.eq(action,0).float().view(-1,1),torch.eq(action,1).float().view(-1,1),torch.eq(action,2).float().view(-1,1)),1)
		x = self.fc3(F.relu(self.fc2(F.relu(self.fc1(x)))))
		return x

	def epsilonRandomPolicy(self,observation):
		if np.random.sample() < epsilon:
			action = np.random.choice(a=3)
			return action
		else:
			maxQ = self.forward(torch.Tensor(observation).view(1,-1),torch.Tensor([0]).view(-1))
			choice = 0
			for action in range(1,3):
				Q_hat = self.forward(torch.Tensor(observation).view(1,-1),torch.Tensor([action]).view(-1))
				if torch.gt(Q_hat,maxQ):
					maxQ = Q_hat
					choice = action
			return choice

	def updateTarget(self,reward,prev_observation,next_observation,action):
		if self.prev_states.dim() != 0:
			self.prev_states = torch.cat((self.prev_states,torch.Tensor([prev_observation])),0)
		else:
			self.predictedQValues = (torch.Tensor([prev_observation]))
		if self.next_states.dim() != 0:
			self.next_states = torch.cat((self.next_states,torch.Tensor([next_observation])),0)
		else:
			self.next_states = (torch.Tensor([next_observation]))
		if self.rewards.dim() != 0:
			self.rewards = torch.cat([self.rewards,torch.Tensor([reward])])
		else:
			self.next_states = (torch.Tensor(reward))
		if self.actions.dim() != 0:
			self.actions = torch.cat((self.actions,torch.Tensor([action])))
		else:
			self.actions = (torch.Tensor([action]))
		return


net = Actor()
optimizer = optim.Adam(net.parameters(),lr=0.01)
#loss = nn.MSELoss(reduction='sum')

def updateQEstimator():
	p = np.random.permutation(len(net.prev_states))
	net.prev_states = net.prev_states[p]
	net.next_states = net.next_states[p]
	net.actions = net.actions[p]
	net.rewards = net.rewards[p]
	batches = int(net.next_states.shape[0]/batch_size)
	for epoch in range(training_epochs):
		for batch in range(batches):
			predictedQ = net.forward(net.prev_states[batch*batch_size:(batch+1)*batch_size],net.actions[batch*batch_size:(batch+1)*batch_size])
			actualQ = []
			for action in range(3):
				actualQ.append(net.forward(net.next_states[batch*batch_size:(batch+1)*batch_size],torch.mul(action,torch.ones(batch_size))))
			maxQ = torch.max(actualQ[0],actualQ[1])
			maxQ = torch.max(actualQ[2],maxQ)
			maxQ = torch.add(torch.mul(gamma,maxQ),net.rewards[batch*batch_size:(batch+1)*batch_size].view(-1,1))
			optimizer.zero_grad()
			curr_loss = loss(maxQ,predictedQ)
			curr_loss.backward()
			optimizer.step()
	net.prev_states = Variable(torch.Tensor())
	net.next_states = Variable(torch.Tensor())
	net.rewards = Variable(torch.Tensor())
	net.actions = Variable(torch.Tensor())
	return

def updateActor():
	#print(net.rewards)
	net.rewards = (net.rewards - net.rewards.mean()) / (net.rewards.std() + 1e-9)
	policy_gradient = torch.sum(torch.mul(net.policy_history.view(-1),net.rewards).mul(-1),-1)
	loss = torch.sum(torch.mul(torch.exp(net.policy_history.view(-1)),net.rewards),-1)
	optimizer.zero_grad()
	policy_gradient.backward()
	optimizer.step()
	net.policy_history = torch.Tensor()
	net.rewards = torch.Tensor()

def annealParameters(episode):
	global epsilon
	epsilon = 0.6-episode/800
	if epsilon < 0:
		epsilon = 0

env = gym.make('Dino-v0')

''' Q-Estimator
for i_episode in range(episodes):
	env.reset()
	env.render()
	observation,_ = env.getObservations()
	t = 0
	action = 0
	curr_reward = 0
	Q_hat = 0
	prev_observation = observation
	while 1:
		if t%4 == 0: #Every 5 steps
			prev_observation = observation
			curr_reward = 0
			action = net.epsilonRandomPolicy(observation)
		observation, reward, done, info = env.step(action,1)
		curr_reward+=reward
		env.render()
		time.sleep(0.01)
		if t%4 == 3: #After a cycle
			net.updateTarget(curr_reward,prev_observation,observation,action)
		if done == True:
			env.reset()
			print("Episode Length",t)
			break
		t+=1
	if i_episode%5 == 4:
		annealParameters(i_episode)
		updateQEstimator()
		gc.collect()
		print(i_episode,epsilon)
env.close()
'''

for i_episode in range(episodes):
	env.reset()
	env.render()
	observation,_ = env.getObservations()
	t = 0
	action = 0
	curr_reward = 0
	Q_hat = 0
	prev_observation = observation
	while 1:
		if t%4 == 0: #Every 4 steps
			prev_observation = observation
			curr_reward = 0
			action = net.policy(observation)
		observation, reward, done, info = env.step(action,1)
		curr_reward+=reward
		#env.render()
		#time.sleep(0.01)
		if t%4 == 3: #After a cycle
			net.updateTarget(prev_observation)
			rewards.append(curr_reward)
		if done == True:
			if t%4 !=3:
				net.updateTarget(prev_observation)
				rewards.append(curr_reward)
			env.reset()
			print("Episode Length",t)
			break
		t+=1
	discountRewards()
	if i_episode%2 == 0:
		#annealParameters(i_episode)
		updateActor()
		gc.collect()
		print(i_episode)
env.close()
