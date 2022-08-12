import os
from datetime import datetime
import numpy as np
import pandas as pd

from double_pendulum.model.symbolic_plant import SymbolicDoublePendulum
from double_pendulum.model.model_parameters import model_parameters
from double_pendulum.simulation.simulation import Simulator
from double_pendulum.controller.tvlqr.tvlqr_controller_drake import TVLQRController
from double_pendulum.utils.plotting import plot_timeseries
from double_pendulum.utils.csv_trajectory import save_trajectory, load_trajectory

# model parameters
urdf_path = "../data/urdfs/acrobot.urdf"
robot = "acrobot"

# mass = [0.608, 0.630]
# length = [0.3, 0.2]
# com = [0.275, 0.166]
# damping = [0.081, 0.0]
# cfric = [0.093, 0.186]
cfric = [0., 0.]
# gravity = 9.81
# inertia = [0.05472, 0.02522]
motor_inertia = 0.
torque_limit = [0.0, 6.0]

model_par_path = "../data/system_identification/identified_parameters/tmotors_v1.0/model_parameters.yml"
mpar = model_parameters()
mpar.load_yaml(model_par_path)
mpar.set_motor_inertia(motor_inertia)
# mpar.set_damping(damping)
mpar.set_cfric(cfric)
mpar.set_torque_limit(torque_limit)

# trajectory parameters
# csv_path = "../data/trajectories/acrobot/dircol/acrobot_tmotors_swingup_1000Hz.csv"
# read_with = "pandas"  # for dircol traj
# keys = "shoulder-elbow"

#csv_path = "../data/trajectories/acrobot/ilqr_v1.0/trajectory.csv"
latest_dir = sorted(os.listdir(os.path.join("data", robot, "ilqr", "trajopt")))[-1]
csv_path = os.path.join("data", robot, "ilqr", "trajopt", latest_dir, "trajectory.csv")
read_with = "numpy"
keys = ""

# simulation parameters
x0 = [0.0, 0.0, 0.0, 0.0]

process_noise_sigmas = [0., 0., 0., 0.]
meas_noise_sigmas = [0., 0., 0., 0.]
meas_noise_cut = 0.0
meas_noise_vfilter = "none"
meas_noise_vfilter_args = {"alpha": [1., 1., 1., 1.]}
delay_mode = "None"
delay = 0.0
u_noise_sigmas = [0., 0.]
u_responsiveness = 1.0
perturbation_times = []
perturbation_taus = []
# controller parameters
# Q = np.diag([10.0, 10.0, 1.0, 1.0])  # for dircol traj
# R = 0.1*np.eye(1)
# Q = np.diag([100.0, 100.0, 10.0, 10.0]) # for ilqr traj
# R = 1.0*np.eye(1)

Q = np.diag([0.64, 0.56, 0.13, 0.037])
R = np.eye(1)*0.82

# Qf = np.zeros((4, 4))
Qf = np.copy(Q)
# Qf = np.array([[6500., 1600., 1500.,  0.],
#                [1600.,  400.,  370.,  0.],
#                [1500.,  370.,  350.,  0.],
#                [   0.,    0.,    0., 30.]])


# init plant, simulator and controller
plant = SymbolicDoublePendulum(model_pars=mpar)

sim = Simulator(plant=plant)
sim.set_process_noise(process_noise_sigmas=process_noise_sigmas)
sim.set_measurement_parameters(meas_noise_sigmas=meas_noise_sigmas,
                               delay=delay,
                               delay_mode=delay_mode)
sim.set_filter_parameters(meas_noise_cut=meas_noise_cut,
                          meas_noise_vfilter=meas_noise_vfilter,
                          meas_noise_vfilter_args=meas_noise_vfilter_args)
sim.set_motor_parameters(u_noise_sigmas=u_noise_sigmas,
                         u_responsiveness=u_responsiveness)

controller = TVLQRController(csv_path=csv_path,
                             urdf_path=urdf_path,
                             read_with=read_with,
                             torque_limit=torque_limit,
                             robot=robot)

controller.set_cost_parameters(Q=Q, R=R, Qf=Qf)
controller.init()

# load reference trajectory
T_des, X_des, U_des = load_trajectory(csv_path, read_with)
dt = T_des[1] - T_des[0]
t_final = T_des[-1] + 5

# simulate
T, X, U = sim.simulate_and_animate(t0=0.0, x0=x0,
                                   tf=t_final, dt=dt, controller=controller,
                                   integrator="runge_kutta",
                                   plot_inittraj=True)
# if imperfections:
X_meas = sim.meas_x_values
X_filt = sim.filt_x_values
U_con = sim.con_u_values
# else:
#    X_meas = None
#    U_con = None

# saving and plotting
timestamp = datetime.today().strftime("%Y%m%d-%H%M%S")
save_dir = os.path.join("data", robot, "tvlqr_drake", timestamp)
os.makedirs(save_dir)

os.system(f"cp {csv_path} " + os.path.join(save_dir, "init_trajectory.csv"))
save_trajectory(os.path.join(save_dir, "trajectory.csv"), T, X, U)

plot_timeseries(T, X, U, None,
                plot_energy=False,
                pos_y_lines=[0.0, np.pi],
                T_des=T_des,
                X_des=X_des,
                U_des=U_des,
                X_meas=X_meas,
                U_con=U_con)
