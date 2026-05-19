import agibot_gdk
import time
import math
import sys

# All joint names, in order
joint_names= [ 
    "idx01_body_joint1",
    "idx02_body_joint2",
    "idx03_body_joint3",
    "idx04_body_joint4",
    "idx05_body_joint5",
    "idx11_head_joint1",
    "idx13_head_joint3",
    "idx12_head_joint2",
    "idx21_arm_l_joint1",
    "idx22_arm_l_joint2",
    "idx23_arm_l_joint3",
    "idx24_arm_l_joint4",
    "idx25_arm_l_joint5",
    "idx26_arm_l_joint6",
    "idx27_arm_l_joint7",
    "idx61_arm_r_joint1",
    "idx62_arm_r_joint2",
    "idx63_arm_r_joint3",
    "idx64_arm_r_joint4",
    "idx65_arm_r_joint5",
    "idx66_arm_r_joint6",
    "idx67_arm_r_joint7"
]

joint_positions = [0.0] * len(joint_names)

if __name__ == "__main__":
    agibot_gdk.gdk_init()
    robot = agibot_gdk.Robot()
    time.sleep(1)
    
    # Initialize joint angle positions
    joint_control_request = agibot_gdk.JointControlReq()
    joint_control_request.life_time = 0.1
    joint_control_request.joint_names = joint_names
    joint_control_request.joint_positions = joint_positions
    joint_control_request.joint_velocities = [0.3] * len(joint_names)
    robot.joint_control_request(joint_control_request)

    time.sleep(1)
    
    # Move with sine function at 200Hz from current position, amplitude 0.087, frequency 0.5Hz
    joint_states = robot.get_joint_states()
    joint_positions = [s['motor_position'] for s in joint_states['states']]
    # Indices 8-21 are arm joints
    base = joint_positions[8:22]  # 14 arm joint baseline positions

    t = 0.0
    dt = 0.01
    freq = 0.5
    omega = 2*math.pi*freq
    amp = 0.087
    phases = [i*0.2 for i in range(14)]
    fade_duration = 1.0  # Smooth startup duration (s), avoid first sudden change
    
    try:
        while True:
            # Fade in over time, avoid sudden jump between initial target and current value
            fade = min(1.0, t / fade_duration)
            arm_positions = [base[i] + (fade * amp) * math.sin(omega*t + phases[i]) for i in range(14)]
            robot.servo_control_arm_pos(arm_positions, 2)
            t += dt
            time.sleep(dt)
    except KeyboardInterrupt:
        print("Exiting...")
        sys.exit(0)
