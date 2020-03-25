#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
@author : Romain Graux
@date : Saturday, 21 March 2020
"""
import numpy as np
from typing import Optional, List
from abc import ABC
import tensorflow as tf
import timeit


from stockBot.wallets import Portfolio, Transaction
from .models import Neural_Network, Deep_Q_Learning, DQNTransition
from .rewards import Reward_Strategy, Simple_Reward_Strategy
from .memory import Memory
from .actions import Action_Strategy, Simple_Action_Strategy
from stockBot.data import Data_Streamer
from stockBot.wallets import Wallet
from stockBot.brokers import Broker, Fake_Broker
from stockBot.environment import Environment

class Agent():

    def __init__(self, broker:Broker, wallet:Wallet=None, env:Environment=None, data_streamer:Data_Streamer=None, neural_network:Neural_Network=None, reward_strategy:Reward_Strategy=None, action_strategy:Action_Strategy=None):
        self.broker          = broker
        self.wallet          = wallet or self.broker.wallet
        self.action_strategy = action_strategy or Simple_Action_Strategy()
        self.env             = env or Environment(self.broker, action_strategy=self.action_strategy)
        self.data_streamer   = data_streamer or Data_Streamer('SPCE')
        self.neural_network  = neural_network or Deep_Q_Learning(self.env.observation_space.shape)
        self.target_network = tf.keras.models.clone_model(self.neural_network.model)
        # self.target_network.name = 'Target Network'
        self.target_network.trainable = False
        self.reward_strategy = reward_strategy or Simple_Reward_Strategy()
        self.broker          = broker or Fake_Broker(self.wallet)

        # A REMPLACER EN PREMIER

        self.action_space = (3)
        self.n_actions = 3



    def train(self, data=None, reward_strategy:Reward_Strategy=None, epochs:int=None, batch_size:int=128, memory_capacity:int=1000, learning_rate:float=0.001, discount_factor:float=0.05, max_steps:Optional=None, update_target_every:int=None) -> List[float]:

        memory = Memory(memory_capacity, DQNTransition)
        reward_strategy = self.reward_strategy
        max_steps = max_steps or np.iinfo(np.int32).max
        epochs = epochs or 25
        update_target_every = update_target_every or 1000

        eps_max = 0.9
        eps_min = 0.05
        eps_constant = 200

        episode = 0
        total_reward = 0
        rewards = []

        default_ticker_name = self.data_streamer.ticker_names[0]
        long_steps = 0

        while episode < epochs:
            state = self.env.reset(default_ticker_name)
            done = False
            steps = 0
            loss_values = []

            while not done:

                epsilon = eps_min + (eps_max - eps_min)*np.exp(-steps/eps_constant)

                decision = self.neural_network.act(state, epsilon=epsilon)

                next_state, reward, done, info = self.env.step(decision, default_ticker_name)

                balance  = self.wallet.balance
                self.neural_network.summary_histogram('decision', decision, long_steps)
                self.neural_network.summary_scalar('balance', balance, long_steps)
                long_steps += 1

                memory.push(state, decision, reward, next_state, done)

                state = next_state
                total_reward += reward
                rewards.append(reward)

                steps += 1

                if steps % 100 == 0:
                    print(steps)

                if len(memory) < batch_size:
                    continue

                loss_value = self._fit_memory(memory, batch_size, learning_rate, discount_factor)
                loss_values.append(loss_value)

                if update_target_every % steps == 0:
                    self.target_network.set_weights(self.neural_network.model.get_weights())
                    # self.target_network = tf.keras.models.clone_model(self.neural_network.model)
                    # self.target_network.trainable = False

                if max_steps and steps > max_steps:
                    done = True

                # self.env.render(episode)
            mean_loss = np.mean(loss_values)

            self.neural_network.summary_scalar('loss', mean_loss, episode)

            print('episode %d'%episode)
            if episode == epochs - 1:
                self.neural_network.save(episode)

            episode += 1

        return rewards


    def _fit_memory(self, memory:Memory, batch_size:int, learning_rate:float, discount_factor:float):
        optimizer = tf.keras.optimizers.Adam(learning_rate)
        loss = tf.keras.losses.Huber()

        transitions = memory.sample(batch_size)
        batch = DQNTransition(*zip(*transitions))

        state_batch = tf.convert_to_tensor(batch.state)
        action_batch = tf.convert_to_tensor(batch.action)
        reward_batch = tf.convert_to_tensor(batch.reward)
        next_state_batch = tf.convert_to_tensor(batch.next_state)
        done_batch = tf.convert_to_tensor(batch.done)

        with tf.GradientTape() as g:
            state_action_values = tf.math.reduce_sum(
                self.neural_network.model(state_batch) * tf.one_hot(action_batch, 3),
                axis=1
            )
            next_state_values = tf.where(
                done_batch,
                tf.zeros(batch_size),
                tf.math.reduce_max(self.target_network(next_state_batch), axis=1)
            )

            expected_state_action_values = reward_batch + (discount_factor * next_state_values)
            loss_value = loss(expected_state_action_values, state_action_values)


        variables = self.neural_network.model.trainable_variables
        gradients = g.gradient(loss_value, variables)
        optimizer.apply_gradients(zip(gradients, variables))

        return loss_value
