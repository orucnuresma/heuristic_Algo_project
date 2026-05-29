import os
import pandas as pd
from mpl_toolkits.mplot3d import Axes3D
import matplotlib.pyplot as plt
plt.style.use("ggplot")


# ============================================================
# KLASOR HAZIRLAMA
# ============================================================

def create_plot_folders():

    os.makedirs("results", exist_ok=True)
    os.makedirs("results/plots", exist_ok=True)


# ============================================================
# PARETO FRONT GRAFIK
# ============================================================

def plot_pareto_front(pareto_front, algorithm_name="NSGA-II"):

    create_plot_folders()

    obj1 = [sol["fitness"][0] for sol in pareto_front]
    obj2 = [sol["fitness"][1] for sol in pareto_front]

    plt.figure(figsize=(10, 7))

    plt.scatter(obj1, obj2, s=80)

    plt.xlabel("Preference Objective")
    plt.ylabel("Cost Objective")

    plt.title(f"Pareto Front - {algorithm_name}")

    plt.grid(True)

    filename = f"results/plots/pareto_{algorithm_name}.png"

    plt.savefig(filename, dpi=300, bbox_inches="tight")

    print(f"Pareto plot kaydedildi: {filename}")

    plt.close()


# ============================================================
# CONVERGENCE CURVE
# ============================================================

def plot_convergence(hv_history, algorithm_name="NSGA-II"):

    create_plot_folders()

    generations = list(range(1, len(hv_history) + 1))

    plt.figure(figsize=(10, 7))

    plt.plot(generations, hv_history)

    plt.xlabel("Generation")
    plt.ylabel("Hypervolume")

    plt.title(f"Convergence Curve - {algorithm_name}")

    plt.grid(True)

    filename = f"results/plots/convergence_{algorithm_name}.png"

    plt.savefig(filename, dpi=300, bbox_inches="tight")

    print(f"Convergence plot kaydedildi: {filename}")

    plt.close()


# ============================================================
# ALGORITHM COMPARISON
# ============================================================

def plot_algorithm_comparison(nsga2_hv, spea2_hv):

    create_plot_folders()

    gen1 = list(range(1, len(nsga2_hv) + 1))
    gen2 = list(range(1, len(spea2_hv) + 1))

    plt.figure(figsize=(10, 7))

    plt.plot(gen1, nsga2_hv, label="NSGA-II")
    plt.plot(gen2, spea2_hv, label="SPEA2")

    plt.xlabel("Generation")
    plt.ylabel("Hypervolume")

    plt.title("Algorithm Comparison")

    plt.legend()

    plt.grid(True)

    filename = "results/plots/algorithm_comparison.png"

    plt.savefig(filename, dpi=300, bbox_inches="tight")

    print(f"Algorithm comparison kaydedildi: {filename}")

    plt.close()
    
# ============================================================
# 3D PARETO FRONT
# ============================================================

def plot_3d_pareto(pareto_front, algorithm_name="NSGA-II"):

    create_plot_folders()

    x = [sol["fitness"][0] for sol in pareto_front]
    y = [sol["fitness"][1] for sol in pareto_front]
    z = [sol["fitness"][2] for sol in pareto_front]

    fig = plt.figure(figsize=(10, 8))

    ax = fig.add_subplot(111, projection='3d')

    ax.scatter(x, y, z, s=80)

    ax.set_xlabel("Preference")
    ax.set_ylabel("Cost")
    ax.set_zlabel("CO2")

    ax.set_title(f"3D Pareto Front - {algorithm_name}")

    filename = f"results/plots/pareto3d_{algorithm_name}.png"

    plt.savefig(filename, dpi=300, bbox_inches="tight")

    print(f"3D Pareto plot kaydedildi: {filename}")

    plt.close()

# ============================================================
# CSV'DEN PARETO PLOT
# ============================================================
# ============================================================
# USER COMPARISON PLOT
# ============================================================

def plot_user_comparison(user1_front, user2_front):

    create_plot_folders()

    u1_x = [sol["fitness"][0] for sol in user1_front]
    u1_y = [sol["fitness"][1] for sol in user1_front]

    u2_x = [sol["fitness"][0] for sol in user2_front]
    u2_y = [sol["fitness"][1] for sol in user2_front]

    plt.figure(figsize=(10, 7))

    plt.scatter(u1_x, u1_y, s=80, label="User 1")
    plt.scatter(u2_x, u2_y, s=80, label="User 2")

    plt.xlabel("Preference")
    plt.ylabel("Cost")

    plt.title("User Comparison")

    plt.legend()

    plt.grid(True)

    filename = "results/plots/user_comparison.png"

    plt.savefig(filename, dpi=300, bbox_inches="tight")

    print(f"User comparison plot kaydedildi: {filename}")

    plt.close()

def plot_pareto_from_csv(csv_path, algorithm_name="NSGA-II"):

    df = pd.read_csv(csv_path)

    x = df["obj_1"]
    y = df["obj_2"]

    plt.figure(figsize=(10, 7))

    plt.scatter(x, y, s=80)

    plt.xlabel("Objective 1")
    plt.ylabel("Objective 2")

    plt.title(f"Pareto Front from CSV - {algorithm_name}")

    plt.grid(True)

    filename = f"results/plots/csv_pareto_{algorithm_name}.png"

    plt.savefig(filename, dpi=300, bbox_inches="tight")

    print(f"CSV Pareto plot kaydedildi: {filename}")

    plt.close()

