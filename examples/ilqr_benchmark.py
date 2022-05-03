import os
from datetime import datetime
import numpy as np
import yaml
import pickle
import pprint

from double_pendulum.model.model_parameters import model_parameters
from double_pendulum.controller.ilqr.ilqr_mpc_cpp import ILQRMPCCPPController
from double_pendulum.analysis.benchmark import benchmarker
from double_pendulum.analysis.utils import get_par_list

robot = "acrobot"

# model parameters
cfric = [0., 0.]
motor_inertia = 0.0  # 8.8e-5
if robot == "acrobot":
    torque_limit = [0.0, 4.0]
if robot == "pendubot":
    torque_limit = [4.0, 0.0]

model_par_path = "../data/system_identification/identified_parameters/tmotors_v2.0/model_parameters.yml"
mpar = model_parameters()
mpar.load_yaml(model_par_path)
mpar.set_motor_inertia(motor_inertia)
mpar.set_cfric(cfric)
mpar.set_torque_limit(torque_limit)

# simulation parameter
dt = 0.005
t_final = 4.985
integrator = "runge_kutta"

# controller parameters
N = 100
N_init = 1000
max_iter = 5
max_iter_init = 1000
regu_init = 100
max_regu = 10000.
min_regu = 0.01
break_cost_redu = 1e-6
trajectory_stabilization = True

# acrobot good par
sCu = [89., 89.]
sCp = [40., 0.2]
sCv = [11., 1.0]
sCen = 0.0
fCp = [66000., 210000.]
fCv = [55000., 92000.]
fCen = 0.0
# sCu = [9.97938814e-02, 9.97938814e-02]
# sCp = [2.06969312e-02, 7.69967729e-02]
# sCv = [1.55726136e-04, 5.42226523e-03]
# sCen = 0.0
# fCp = [3.82623819e+02, 7.05315590e+03]
# fCv = [5.89790058e+01, 9.01459500e+01]
# fCen = 0.0

Q = np.array([[sCp[0], 0., 0., 0.],
              [0., sCp[1], 0., 0.],
              [0., 0., sCv[0], 0.],
              [0., 0., 0., sCv[1]]])
Qf = np.array([[fCp[0], 0., 0., 0.],
               [0., fCp[1], 0., 0.],
               [0., 0., fCv[0], 0.],
               [0., 0., 0., fCv[1]]])
R = np.array([[sCu[0], 0.],
              [0., sCu[1]]])

# benchmark parameters
compute_model_robustness = False
mpar_vars = ["Ir",
             "m1r1", "I1", "b1", "cf1",
             "m2r2", "m2", "I2", "b2", "cf2"]

N_var = 3
Ir_var_list = [0.0, 8.8e-5, 2*8.8e-5]
m1r1_var_list = get_par_list(mpar.m[0]*mpar.r[0], 0.5, 1.5, N_var)
I1_var_list = get_par_list(mpar.I[0], 0.5, 1.5, N_var)
b1_var_list = [0.0, 0.081, 0.19]
cf1_var_list = [0.0, 0.093, 0.186]
m2r2_var_list = get_par_list(mpar.m[1]*mpar.r[1], 0.5, 1.5, N_var)
m2_var_list = get_par_list(mpar.m[1], 0.5, 1.5, N_var)
I2_var_list = get_par_list(mpar.I[1], 0.5, 1.5, N_var)
b2_var_list = [0.0, 0.081, 0.19]
cf2_var_list = [0.0, 0.093, 0.186]

modelpar_var_lists = {"Ir": Ir_var_list,
                      "m1r1": m1r1_var_list,
                      "I1": I1_var_list,
                      "b1": b1_var_list,
                      "cf1": cf1_var_list,
                      "m2r2": m2r2_var_list,
                      "m2": m2_var_list,
                      "I2": I2_var_list,
                      "b2": b2_var_list,
                      "cf2": cf2_var_list}

compute_noise_robustness = False
noise_mode = "vel"
noise_amplitudes = [0.0, 0.1, 0.3, 0.5, 0.8, 1.0]
noise_cut = 0.5
noise_vfilter = "lowpass"
noise_vfilter_args = {"alpha": 0.3}

compute_unoise_robustness = False
unoise_amplitudes = [0.0, 0.1, 0.5, 1.0, 2.0, 5.0]

compute_uresponsiveness_robustness = False
u_responses = [1.0, 1.3, 1.5, 2.0]

compute_delay_robustness = True
delay_mode = "vel"
delays = [0.0, dt, 2*dt, 5*dt, 10*dt]

# init trajectory
#latest_dir = sorted(os.listdir(os.path.join("data", robot, "ilqr", "trajopt")))[-1]
#init_csv_path = os.path.join("data", robot, "ilqr", "trajopt", latest_dir, "trajectory.csv")
init_csv_path = "../data/trajectories/acrobot/ilqr/trajectory.csv"
read_with = "numpy"

# swingup parameters
start = [0., 0., 0., 0.]
goal = [np.pi, 0., 0., 0.]

# create save directory
timestamp = datetime.today().strftime("%Y%m%d-%H%M%S")
save_dir = os.path.join("data", robot, "ilqr", "mpc_benchmark", timestamp)
os.makedirs(save_dir)

# construct simulation objects
controller = ILQRMPCCPPController(model_pars=mpar)
controller.set_start(start)
controller.set_goal(goal)
controller.set_parameters(N=N,
                          dt=dt,
                          max_iter=max_iter,
                          regu_init=regu_init,
                          max_regu=max_regu,
                          min_regu=min_regu,
                          break_cost_redu=break_cost_redu,
                          integrator=integrator,
                          trajectory_stabilization=trajectory_stabilization)
controller.set_cost_parameters(sCu=sCu,
                               sCp=sCp,
                               sCv=sCv,
                               sCen=sCen,
                               fCp=fCp,
                               fCv=fCv,
                               fCen=fCen)
controller.load_init_traj(csv_path=init_csv_path)

ben = benchmarker(controller=controller,
                  x0=start,
                  dt=dt,
                  t_final=t_final,
                  goal=goal,
                  integrator=integrator,
                  save_dir=save_dir)
ben.set_model_parameter(model_pars=mpar)
ben.set_init_traj(init_csv_path, read_with=read_with)
ben.set_cost_par(Q=Q, R=R, Qf=Qf)
ben.compute_ref_cost()
res = ben.benchmark(compute_model_robustness=compute_model_robustness,
                    compute_noise_robustness=compute_noise_robustness,
                    compute_unoise_robustness=compute_unoise_robustness,
                    compute_uresponsiveness_robustness=compute_uresponsiveness_robustness,
                    compute_delay_robustness=compute_delay_robustness,
                    mpar_vars=mpar_vars,
                    modelpar_var_lists=modelpar_var_lists,
                    noise_mode=noise_mode,
                    noise_amplitudes=noise_amplitudes,
                    noise_cut=noise_cut,
                    noise_vfilter=noise_vfilter,
                    noise_vfilter_args=noise_vfilter_args,
                    unoise_amplitudes=unoise_amplitudes,
                    u_responses=u_responses,
                    delay_mode=delay_mode,
                    delays=delays)
pprint.pprint(res)

# saving
f = open(os.path.join(save_dir, "results.pkl"), 'wb')
pickle.dump(res, f)
f.close()

os.system(f"cp {init_csv_path} " + os.path.join(save_dir, "init_trajectory.csv"))
mpar.save_dict(os.path.join(save_dir, "model_parameters.yml"))

par_dict = {
            "dt": dt,
            "t_final": t_final,
            "integrator": integrator,
            "start_pos1": start[0],
            "start_pos2": start[1],
            "start_vel1": start[2],
            "start_vel2": start[3],
            "goal_pos1": goal[0],
            "goal_pos2": goal[1],
            "goal_vel1": goal[2],
            "goal_vel2": goal[3],
            "N": N,
            "N_init": N_init,
            "max_iter": max_iter,
            "max_iter_init": max_iter_init,
            "regu_init": regu_init,
            "max_regu": max_regu,
            "min_regu": min_regu,
            "break_cost_redu": break_cost_redu,
            "trajectory_stabilization": trajectory_stabilization,
            "sCu1": sCu[0],
            "sCu2": sCu[1],
            "sCp1": sCp[0],
            "sCp2": sCp[1],
            "sCv1": sCv[0],
            "sCv2": sCv[1],
            "sCen": sCen,
            "fCp1": fCp[0],
            "fCp2": fCp[1],
            "fCv1": fCv[0],
            "fCv2": fCv[1],
            "fCen": fCen
            }

with open(os.path.join(save_dir, "parameters.yml"), 'w') as f:
    yaml.dump(par_dict, f)
