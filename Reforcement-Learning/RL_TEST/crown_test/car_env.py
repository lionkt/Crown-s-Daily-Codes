import numpy as np
import scipy as sp

# define boundary
MAX_CAR_NUMBER = 5  # 最大的车辆数目
MIN_ACC = -10.0
MAX_ACC = 6.0
MAX_V = 60 / 3.6
TURN_MAX_V = 4.2
ROAD_LENGTH = MAX_V * 60
CAR_LENGTH = 5
LANE_WIDTH = 3.5
AI_DT = 0.2

DES_PLATOON_INTER_DISTANCE = 5  # 车队的理想间距
ROLE_SPACE = ['leader', 'follower']
FOLLOW_STRATEGY = ['ACC', 'CACC', 'RL']


# define car
class car(object):
    def __init__(
            self,
            id,
            role,
            tar_interDis,
            tar_speed,
            location=None,
            ingaged_in_platoon=None,
            leader=None,
            previousCar=None,
            car_length=None
    ):
        self.id = id
        self.role = role
        self.speed = 0.0
        self.acc = 0.0
        if not location:
            self.location = np.zeros((1, 2))
        else:
            self.location = location[:]

        self.target_interDis = tar_interDis
        self.target_speed = tar_speed
        self.ingaged_in_platoon = ingaged_in_platoon if ingaged_in_platoon else False  # 默认不参加
        self.leader = leader
        self.previousCar = previousCar
        self.length = CAR_LENGTH if not car_length else car_length

        # 暂时用来存储，方便画图
        self.accData = []
        self.speedData = []
        self.locationData = []

    # 用acc-speed curve做限幅
    def __engine_speed_up_acc_curve(self, speed, p):
        acc_max = MAX_ACC
        v_max = MAX_V
        m = (v_max * p - v_max + v_max * sp.sqrt(1 - p)) / p
        k = (1 - p) * acc_max / m / m
        calcValue = -k * (speed - m) * (speed - m) + acc_max
        return calcValue

    # 用acc-speed curve做限幅
    def __engine_slow_down_acc_curve(self, speed, p):
        acc_max = MAX_ACC
        v_max = MAX_V
        m = v_max / (sp.sqrt(p) + 1)
        k = -MIN_ACC / m / m
        calcValue = k * (speed - m) * (speed - m) + MIN_ACC
        return calcValue

    # 启动运行的函数
    def __excute_foward(self):
        if self.speed >= MAX_V:
            self.acc = 0
        else:
            temp_a = car.__engine_speed_up_acc_curve(self, self.speed, p=0.3)
            self.acc = temp_a

    # 单纯计算前车和自己的距离，不含车长
    def __calc_pure_interDistance(self, previous):
        if (not previous):
            return ROAD_LENGTH - self.location[1]
        # assert  previous.__class__
        return previous.location[1] - self.location[1] - self.length / 2 - previous.length / 2

    # ACC的跟驰方法
    def __follow_car_ACC(self, pure_interval, previous):
        assert previous, 'ACC跟驰前车为空'  # 如果previous为空则报警
        v1 = self.speed  # 自己的速度
        v2 = previous.speed + AI_DT * previous.acc  # 前车的速度
        lam_para = 0.1
        epsilon = v1 - v2
        T = DES_PLATOON_INTER_DISTANCE / (1.0 * MAX_V)

        # 固定车头时距的跟驰方式
        sigma = -pure_interval + T * v1
        tem_a = -(epsilon + lam_para + sigma) / T
        # 限幅
        if (tem_a > MAX_ACC):
            self.acc = MAX_ACC
        elif (tem_a < MIN_ACC):
            self.acc = MIN_ACC
        else:
            self.acc = tem_a

    # CACC的跟驰方法
    def __follow_car_CACC(self, pure_interval, previous):
        assert previous, 'CACC跟驰前车为空'  # 如果previous为空则报警
        assert self.leader, 'CACC不存在leader'
        gap = DES_PLATOON_INTER_DISTANCE
        C_1 = 0.5
        w_n = 0.2
        xi = 1
        # 系数
        alpha_1 = 1 - C_1
        alpha_2 = C_1
        alpha_3 = -(2 * xi - C_1 * (xi + sp.sqrt(xi * xi - 1))) * w_n
        alpha_4 = - C_1 * (xi + sp.sqrt(xi * xi - 1)) * w_n
        alpha_5 = -w_n * w_n
        pre_acc = previous.acc
        leader_acc = self.leader.acc
        epsilon_i = -pure_interval + gap
        d_epsilon_i = self.speed - previous.speed
        # 核心公式
        tem_a = alpha_1 * pre_acc + alpha_2 * leader_acc + alpha_3 * d_epsilon_i + alpha_4 * (
            self.speed - previous.speed) + alpha_5 * epsilon_i
        # 限幅
        if (tem_a > MAX_ACC):
            self.acc = MAX_ACC
        elif (tem_a < MIN_ACC):
            self.acc = MIN_ACC
        else:
            self.acc = tem_a

    def __follow_car_for_platoon(self, STRATEGY, previous):
        temp_a = MAX_ACC
        if (not previous):
            # 如果前车为空，说明自己是leader
            if (self.speed <= TURN_MAX_V):
                temp_a = car.__engine_speed_up_acc_curve(self, self.speed, p=0.3)
            elif (self.speed > MAX_V):
                delta_v = np.abs(self.speed - MAX_V)
                temp_a = -car.__engine_speed_up_acc_curve(self, self.speed - delta_v, p=0.3) * 0.5
        else:
            v1 = self.speed  # 自己的速度
            v2 = previous.speed  # 前车的速度
            if (previous.acc < 0.0):
                v2 += AI_DT * previous.acc
            v1 = v1 if v1 > 0 else 0.0
            v2 = v2 if v2 > 0 else 0.0
            s = car.__calc_pure_interDistance(self, previous)

            # 根据策略选择跟驰的方式
            assert self.ingaged_in_platoon, '在follow_car_for_platoon中，ingaged_in_platoon出现了错误'
            # 如果参加了车队
            if STRATEGY == 'ACC':
                car.__follow_car_ACC(self, s, previous)
            elif STRATEGY == 'CACC':
                if (not self.leader) or (self.id == self.leader.id):
                    car.__follow_car_ACC(self, s, previous)  # 调用ACC来补救
                else:
                    car.__follow_car_CACC(self, s, previous)  # 调用正宗的CACC
            elif STRATEGY == 'RL':
                ''

        # 限幅
        if temp_a > MAX_ACC:
            self.acc = MAX_ACC
        elif temp_a < MIN_ACC:
            self.acc = MIN_ACC
        if temp_a < self.acc:
            self.acc = temp_a

    # 不参与车队的跟驰
    def __follow_car(self, previous):
        temp_a = MAX_ACC
        if not previous:
            # 如果前车为空，说明自己是leader
            if self.speed <= TURN_MAX_V:
                temp_a = car.__engine_speed_up_acc_curve(self, self.speed, p=0.3)
            elif self.speed > MAX_V:
                delta_v = sp.abs(self.speed - MAX_V)
                temp_a = -car.__engine_speed_up_acc_curve(self, self.speed - delta_v, p=0.3) * 0.5
        else:
            v1 = self.speed  # 自己的速度
            v2 = previous.speed  # 前车的速度
            if previous.acc < 0.0:
                v2 += AI_DT * previous.acc
            v1 = v1 if v1 > 0 else 0.0
            v2 = v2 if v2 > 0 else 0.0
            s = car.__calc_pure_interDistance(self, previous)
            safer_distance = DES_PLATOON_INTER_DISTANCE
            follow_dis = self.length / 4.47 * v1 + safer_distance
            s -= follow_dis
            if s <= 0.0:
                temp_a = MIN_ACC
            else:
                temp_a = 2.0 * (s / 2.0 - v1 * AI_DT) / (AI_DT * AI_DT)

            if s <= follow_dis:
                if temp_a > 0.0:
                    temp_a /= 2.0

        # 限幅
        if temp_a > MAX_ACC:
            self.acc = MAX_ACC
        elif temp_a < MIN_ACC:
            self.acc = MIN_ACC
        if temp_a < self.acc:
            self.acc = temp_a

    # 获取前车--为了简化起见，直接判断ID，目前假定车辆的是头车ID=0，然后后面的车依次递增
    def __get_previous_car(self, CarList):
        ''
        if self.id == 0:
            return None
        else:
            index = self.id - 1
            return CarList[index]

    # 车辆运动学的主函数
    def calculate(self, CarList, STARTEGEY):
        # 存储上次的数据
        self.accData.append(self.acc)
        self.speedData.append(self.speed)
        loc = self.location[:]
        self.locationData.append(loc)

        old_acc = self.acc
        alpha = 0.6  # 动窗口的系数
        # 启动车辆
        car.__excute_foward(self)
        # 车辆跟驰
        precar = car.__get_previous_car(self, CarList)
        if self.ingaged_in_platoon:
            car.__follow_car_for_platoon(self, STARTEGEY, precar)  # 先默认车队的跟驰成员采用ACC方法
        else:
            car.__follow_car(self, precar)

        # 减速限制函数，控制在包络线的范围内
        if self.acc < 0.0:
            low_ = car.__engine_slow_down_acc_curve(self, self.speed, p=0.6)
            if self.acc < low_ and low_ <= 0.0:
                self.acc = low_
            if self.acc < MIN_ACC:
                self.acc = MIN_ACC
            if np.abs(self.acc - MIN_ACC) <= 0.0:
                self.acc = old_acc * alpha + (1 - alpha) * self.acc  # 窗口平滑处理
        # 添加jerk限制函数
        beta = 0.7
        jerk_cur = (self.acc - old_acc) / AI_DT
        MAX_jerk = beta * MAX_ACC / AI_DT
        if np.abs(jerk_cur) > MAX_jerk:
            if self.acc <= 0.0:
                self.acc = -MAX_jerk * AI_DT + old_acc
            else:
                self.acc = MAX_jerk * AI_DT + old_acc
        if self.acc < MIN_ACC:
            self.acc = MIN_ACC
        if self.acc > MAX_ACC:
            self.acc = MAX_ACC

            # 限制加速的幅度
            # high_ = car.__engine_speed_up_acc_curve(self, self.speed, p=0.3)
            # if (self.acc > high_*1.5):
            #     self.acc = high_

    # 更新车辆的运动学信息
    def update_car_info(self, time_per_dida_I):
        last_acc = self.accData[-1]
        last_speed = self.speedData[-1]
        self.speed = self.speed + time_per_dida_I * self.acc
        if self.speed <= 0:
            self.speed = 0
        self.location[1] = self.location[1] + self.speed * time_per_dida_I
