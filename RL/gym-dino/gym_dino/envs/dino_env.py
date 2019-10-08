import gym
from gym import error, spaces, utils
from gym.utils import seeding
import pygame
import random
from pygame import *
import gc
import os
import numpy as np

pygame.init()

scr_size = (width,height) = (600,300) # Screen Size
FPS = 60 # Frames Per Second
gravity = 0.6 # Gravity for jumps

black = (0,0,0) 
white = (255,255,255)
background_col = (235,235,235) # Colours

maxSpeed = 11.5
high_score = 0 # Initial High Score

screen = pygame.display.set_mode(scr_size) # Init screen
pygame.display.set_caption("T-Rex Rush") # Caption

def load_image(name,sizex=-1,sizey=-1,colorkey=None,): # Load Images
	fullname = os.path.join('sprites', name)
	image = pygame.image.load(fullname)
	image = image.convert()
	if colorkey is not None:
		if colorkey is -1:
			colorkey = image.get_at((0, 0))
		image.set_colorkey(colorkey, RLEACCEL)
	if sizex != -1 or sizey != -1:
		image = pygame.transform.scale(image, (sizex, sizey))
	return (image, image.get_rect())

def load_sprite_sheet(sheetname,nx,ny,scalex = -1,scaley = -1,colorkey = None,):
	fullname = os.path.join('sprites',sheetname)
	sheet = pygame.image.load(fullname)
	sheet = sheet.convert()
	sheet_rect = sheet.get_rect()
	sprites = []
	sizex = sheet_rect.width/nx
	sizey = sheet_rect.height/ny
	for i in range(0,ny):
		for j in range(0,nx):
			rect = pygame.Rect((j*sizex,i*sizey,sizex,sizey))
			image = pygame.Surface(rect.size)
			image = image.convert()
			image.blit(sheet,(0,0),rect)
			if colorkey is not None:
				if colorkey is -1:
					colorkey = image.get_at((0,0))
				image.set_colorkey(colorkey,RLEACCEL)
			if scalex != -1 or scaley != -1:
				image = pygame.transform.scale(image,(scalex,scaley))
			sprites.append(image)
	sprite_rect = sprites[0].get_rect()
	return sprites,sprite_rect

def extractDigits(number):
	if number > -1:
		digits = []
		i = 0
		while(number/10 != 0):
			digits.append(number%10)
			number = int(number/10)
		digits.append(number%10)
		for i in range(len(digits),5):
			digits.append(0)
		digits.reverse()
		return digits

class Dino():
	def __init__(self,sizex=-1,sizey=-1):
		self.images,self.rect = load_sprite_sheet('dino.png',5,1,sizex,sizey,-1)
		self.images1,self.rect1 = load_sprite_sheet('dino_ducking.png',2,1,59,sizey,-1)
		self.rect.bottom = int(0.98*height)
		self.rect.left = width/15
		self.image = self.images[0]
		self.index = 0
		self.counter = 0
		self.score = 0
		self.isJumping = False
		self.isDead = False
		self.isDucking = False
		self.isBlinking = False
		self.movement = [0,0] # Distance,Velocity ? Right Velocity,Up Velocity
		self.jumpSpeed = 11.5
		self.stand_pos_width = self.rect.width
		self.duck_pos_width = self.rect1.width

	def draw(self):
		screen.blit(self.image,self.rect)

	def checkbounds(self):
		if self.rect.bottom > int(0.98*height): # Check Bounds (Drop the dino)
			self.rect.bottom = int(0.98*height)
			self.isJumping = False
			self.movement[1] = 0

	def update(self): # Updates the game
		if self.isJumping:
			self.movement[1] = self.movement[1] + gravity # Gravity Timestep 
			self.index = 0
		elif self.isBlinking:
			if self.index == 0:
				if self.counter % 400 == 399:
					self.index = (self.index + 1)%2
			else:
				if self.counter % 20 == 19:
					self.index = (self.index + 1)%2
		elif self.isDucking:
			if self.counter % 5 == 0:
				self.index = (self.index + 1)%2
		else:
			if self.counter % 5 == 0:
				self.index = (self.index + 1)%2 + 2
		if self.isDead:
		   self.index = 4
		if not self.isDucking:
			self.image = self.images[self.index]
			self.rect.width = self.stand_pos_width
		else:
			self.image = self.images1[(self.index)%2]
			self.rect.width = self.duck_pos_width
		self.rect = self.rect.move(self.movement)
		self.checkbounds()
		if not self.isDead and self.counter % 7 == 6 and self.isBlinking == False:
			self.score += 1
		self.counter = (self.counter + 1)

	def reset(self):
		self.rect.bottom = int(0.98*height)
		self.rect.left = width/15
		self.image = self.images[0]
		self.index = 0
		self.counter = 0
		self.score = 0
		self.isJumping = False
		self.isDead = False
		self.isDucking = False
		self.isBlinking = False
		self.movement = [0,0] # Distance,Velocity ? Right Velocity,Up Velocity
		self.jumpSpeed = maxSpeed
		self.stand_pos_width = self.rect.width
		self.duck_pos_width = self.rect1.width

class Cactus(pygame.sprite.Sprite):
	def __init__(self,speed=5,sizex=-1,sizey=-1):
		pygame.sprite.Sprite.__init__(self,self.containers)
		self.images,self.rect = load_sprite_sheet('cacti-small.png',3,1,sizex,sizey,-1)
		self.rect.bottom = int(0.98*height)
		self.rect.left = width + self.rect.width
		self.image = self.images[random.randrange(0,3)]
		self.movement = [-1*speed,0]

	def draw(self):
		screen.blit(self.image,self.rect)

	def update(self):
		self.rect = self.rect.move(self.movement)
		if self.rect.right < 0:
			self.kill()

class Ptera(pygame.sprite.Sprite):
	def __init__(self,speed=5,sizex=-1,sizey=-1):
		pygame.sprite.Sprite.__init__(self,self.containers)
		self.images,self.rect = load_sprite_sheet('ptera.png',2,1,sizex,sizey,-1)
		self.ptera_height = [height*0.82,height*0.75,height*0.60]
		self.rect.centery = self.ptera_height[random.randrange(0,3)]
		self.rect.left = width + self.rect.width
		self.image = self.images[0]
		self.movement = [-1*speed,0]
		self.index = 0
		self.counter = 0

	def draw(self):
		screen.blit(self.image,self.rect)

	def update(self):
		if self.counter % 10 == 0:
			self.index = (self.index+1)%2
		self.image = self.images[self.index]
		self.rect = self.rect.move(self.movement)
		self.counter = (self.counter + 1)
		if self.rect.right < 0:
			self.kill()

class Scoreboard():
	def __init__(self,x=-1,y=-1):
		self.score = 0
		self.tempimages,self.temprect = load_sprite_sheet('numbers.png',12,1,11,int(11*6/5),-1)
		self.image = pygame.Surface((55,int(11*6/5)))
		self.rect = self.image.get_rect()
		if x == -1:
			self.rect.left = width*0.89
		else:
			self.rect.left = x
		if y == -1:
			self.rect.top = height*0.1
		else:
			self.rect.top = y

	def draw(self):
		screen.blit(self.image,self.rect)

	def update(self,score):
		score_digits = extractDigits(score)
		self.image.fill(background_col)
		for s in score_digits:
			self.image.blit(self.tempimages[s],self.temprect)
			self.temprect.left += self.temprect.width
		self.temprect.left = 0


scb = Scoreboard()
highsc = Scoreboard(width*0.78)
temp_images,temp_rect = load_sprite_sheet('numbers.png',12,1,11,int(11*6/5),-1)
HI_image = pygame.Surface((22,int(11*6/5)))
HI_rect = HI_image.get_rect()
HI_image.fill(background_col)
HI_image.blit(temp_images[10],temp_rect)
temp_rect.left += temp_rect.width
HI_image.blit(temp_images[11],temp_rect)
HI_rect.top = height*0.1
HI_rect.left = width*0.73

class DinoEnv(gym.Env):  
	metadata = {'render.modes': ['human']}   
	def __init__(self):
		super(DinoEnv,self).__init__()
		self.gamespeed = 4
		self.playerDino = Dino(44,47)
		self.counter = 0
		self.cacti = pygame.sprite.Group()
		self.pteras = pygame.sprite.Group()
		self.last_obstacle = pygame.sprite.Group()
		Cactus.containers = self.cacti
		Ptera.containers = self.pteras
		self.action_space = spaces.Discrete(3) # Nothing,Jump And Down 
		self.observation_space = spaces.Box(low=-width,high=width,shape=(7,)) # GameSpeed, UpSpeed, Height and Distance to next obstacle
		self.gameOver = False
		self.passed = False

	def step(self, action,algo):
		global high_score
		if action == 0:
			self.playerDino.isDucking = False
		if action == 1: # Jump
			if self.playerDino.rect.bottom == int(0.98*height):
				self.playerDino.isJumping = True
				self.playerDino.isDucking = False
				self.playerDino.movement[1] = -1*self.playerDino.jumpSpeed
		if action == 2: # Duck
			if self.playerDino.isJumping and not self.playerDino.isDead:
				self.playerDino.movement[1]+= 2*gravity
				self.playerDino.isDucking = True
			if not (self.playerDino.isJumping and self.playerDino.isDead):
				self.playerDino.isDucking = True
		for c in self.cacti:
			c.movement[0] = -1*self.gamespeed
			if pygame.sprite.collide_mask(self.playerDino,c):
				self.playerDino.isDead = True
		for p in self.pteras:
			p.movement[0] = -1*self.gamespeed
			if pygame.sprite.collide_mask(self.playerDino,p):
				self.playerDino.isDead = True
		if len(self.cacti) < 2:
			if len(self.cacti) == 0:
				self.last_obstacle.empty()
				self.last_obstacle.add(Cactus(self.gamespeed,40,40))
			else:
				for l in self.last_obstacle:
					if l.rect.right < width*0.7 and random.randrange(0,50) == 10:
						self.last_obstacle.empty()
						self.last_obstacle.add(Cactus(self.gamespeed, 40, 40))
		if len(self.pteras) == 0 and random.randrange(0,50) == 10 and 1 == 0:
			for l in self.last_obstacle:
				if l.rect.right < width*0.8:
					self.last_obstacle.empty()
					self.last_obstacle.add(Ptera(self.gamespeed, 46, 40))
		self.playerDino.update()
		self.cacti.update()
		self.pteras.update()
		for c in self.cacti:
			if c.rect.right <= self.playerDino.rect.left:
				self.passed = True
				self.cacti.remove(c)
				break
		for p in self.pteras:
			if p.rect.right <= self.playerDino.rect.left:
				self.passed = True
				self.pteras.remove(p)
				break
		scb.update(self.playerDino.score)
		highsc.update(high_score)
		if self.counter%700 == 699:
			self.gamespeed += 1
		self.counter = self.counter+1
		obs,reward = self.getObservations()
		if self.playerDino.isDead == 1:
			self.gameOver = True
			if self.playerDino.score > high_score:
				high_score = self.playerDino.score
		if algo == 1:
			if self.playerDino.isDead == True:
				reward = -10
			else:
				reward = 0.1
			if self.passed == True:
				reward+=10
				self.passed = False
		return obs,reward,self.playerDino.isDead,{}

	def render(self, mode='human', close=False):
		if pygame.display.get_surface() != None:
			screen.fill(background_col)
			scb.draw()
			if high_score != 0:
				highsc.draw()
				screen.blit(HI_image,HI_rect)
			self.cacti.draw(screen)
			self.pteras.draw(screen)
			self.playerDino.draw()
			pygame.display.update()

	def reset(self):
		highsc.update(high_score)
		self.playerDino.reset()
		del self.cacti
		del self.pteras
		del self.last_obstacle
		self.cacti = pygame.sprite.Group()
		self.pteras = pygame.sprite.Group()
		self.last_obstacle = pygame.sprite.Group()
		Cactus.containers = self.cacti
		Ptera.containers = self.pteras
		self.gameOver = False
		self.counter = 0

	def getObservations(self): #RightSpeed,UpSpeed,Top,Bottom,Obstacle Top,Obstacle Bottom,Obstacle Left,Obstacle Right,Collision Distance
		obs = [0,0,0,0,-1,-1,-1,-1,2]
		obs[0] = self.gamespeed
		obs[1] = -1*round(self.playerDino.movement[1]/maxSpeed,3)
		obs[2] = round(1-self.playerDino.rect.top/height,3)
		obs[3] = round(1-self.playerDino.rect.bottom/height,3)
		temp = 0
		for c in self.cacti:
			distance = self._calculateDistance(self.playerDino.rect,c.rect)
			if distance < obs[8]:
				temp = c.rect
				obs[8] = round(distance,3)
		for p in self.pteras:
			distance = self._calculateDistance(self.playerDino.rect,p.rect)
			if distance < obs[8]:
				temp = p.rect
				obs[8] = round(distance,3)
		if type(temp) == int:
			return obs,0
		obs[4] = round(1-temp.top/height,3)
		obs[5] = round(1-temp.bottom/height,3)
		obs[6] = round(temp.left/width,3)
		obs[7] = round(temp.right/width,3)
		if obs[8] > 0.15:
			reward =  0
		else:
			reward =  5*(obs[8]-0.15)
		return obs,reward

	def _calculateDistance(self,dino,obstacle):
		y_distance = int(dino.bottom<obstacle.top)*np.power((dino.bottom-obstacle.top)/height,2)+int(obstacle.bottom<dino.top)*np.power((dino.top-obstacle.bottom)/height,2)
		y_distance+=(y_distance==0)*np.power((dino.bottom+dino.top-(obstacle.top+obstacle.bottom))/(2*height),2)
		x_distance = int(dino.left>obstacle.right)*np.power((dino.left-obstacle.right)/width,2)+int(obstacle.left>dino.right)*np.power((dino.right-obstacle.left)/width,2)
		x_distance+=(x_distance==0)*np.power((dino.left+dino.right-(obstacle.left+obstacle.right))/(2*width),2)
		return np.sqrt(x_distance+y_distance)

	def close(self):
		pygame.quit()