#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
@author : Romain Graux
@date : Sunday, 22 March 2020
"""

import random
import numpy as np
import tensorflow as tf
from collections import namedtuple

from stockBot.memory import Memory
from .neural_network_base import Reinforcement_Network
from stockBot.reward_strategies import Reward_Strategy, Simple_Reward_Strategy

DQNTransition = namedtuple('DQNTransition', ['state', 'action', 'reward', 'next_state', 'done'])

class Deep_Q_Learning(Reinforcement_Network):

    def __init__(self, input_shape=None, layer_size=200, load_name=None, output_size=None):
        self.output_size = output_size
        super().__init__(input_shape=input_shape, layer_size=layer_size, load_name=load_name)

    def build_model(self, distribution=tf.initializers.GlorotNormal(), bias=tf.constant_initializer(0.01)):
        self.input_layer    = tf.keras.Input(shape=self.input_shape, name='Input', dtype='float32')
        self.conv1d_1       = tf.keras.layers.Conv1D(filters=64,
                                           kernel_size=6,
                                           kernel_initializer=distribution,
                                           bias_initializer=bias,
                                           padding='same',
                                           activation='tanh',
                                           name='Conv_1')(self.input_layer)
        self.maxpooling_1   = tf.keras.layers.MaxPooling1D(pool_size=2,
                                                           name='MaxPooling_1')(self.conv1d_1)
        self.conv1d_2       = tf.keras.layers.Conv1D(filters=32,
                                           kernel_size=3,
                                           kernel_initializer=distribution,
                                           bias_initializer=bias,
                                           padding='same',
                                           activation='tanh',
                                           name='Conv_2')(self.maxpooling_1)
        self.maxpooling_2   = tf.keras.layers.MaxPooling1D(pool_size=2,
                                                           name='MaxPooling_2')(self.conv1d_2)
        self.flatten        = tf.keras.layers.Flatten(name='Flatten')(self.maxpooling_2)
        self.feed_layer     = tf.keras.layers.Dense(self.output_size,
                                           kernel_initializer=distribution,
                                           bias_initializer=bias,
                                           activation='sigmoid',
                                           name='Dense')(self.flatten)
        self.decision_layer = tf.keras.layers.Dense(self.output_size,
                                           kernel_initializer=distribution,
                                           bias_initializer=bias,
                                           activation='softmax',
                                           name='Decision')(self.feed_layer)
        self.model          = tf.keras.models.Model(inputs=[self.input_layer],
                                          outputs=[self.decision_layer],
                                          name='Policy_Network')

    def act(self, state, epsilon=0):
        if epsilon > random.random():
            return np.random.choice(self.output_size)
        else:
            decision = self.predict(np.expand_dims(state, 0))
            return np.argmax(decision)
