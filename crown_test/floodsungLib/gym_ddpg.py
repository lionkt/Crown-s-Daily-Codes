from floodsungLib.filter_env import *
from floodsungLib.ddpg import *
import gc
import os
gc.enable()

ENV_NAME = 'Pendulum-v0'
EPISODES = 100000
TEST = 10

os.environ["CUDA_DEVICE_ORDER"] = "PCI_BUS_ID"
os.environ["CUDA_VISIBLE_DEVICES"] = "1"


def main():
    # env = makeFilteredEnv(gym.make(ENV_NAME))
    env = gym.make(ENV_NAME)

    state_dim = env.observation_space.shape[0]
    action_dim = env.action_space.shape[0]
    agent = DDPG(state_dim, action_dim)
    env.monitor.start('experiments/' + ENV_NAME,force=True)

    for episode in range(EPISODES):
        state = env.reset()
        print("episode:",episode)
        # Train
        for step in range(env.spec.timestep_limit):
            action = agent.noise_action(state)
            next_state,reward,done,_ = env.step(action)
            agent.perceive(state,action,reward,next_state,done)
            state = next_state
            if done:
                break
        # Testing:
        if episode % 100 == 0 and episode > 100:
            total_reward = 0
            for i in range(TEST):
                state = env.reset()
                for j in range(env.spec.timestep_limit):
                    # env.render()
                    action = agent.action(state)  # direct action for test
                    state, reward, done, _ = env.step(action)
                    total_reward += reward
                    if done:
                        break
            ave_reward = total_reward / TEST
            print('episode: ', episode, 'Evaluation Average Reward:', ave_reward)
    env.monitor.close()

if __name__ == '__main__':
    main()
