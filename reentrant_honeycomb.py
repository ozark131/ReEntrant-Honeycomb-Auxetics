# reentrant honeycomb shading overhang - geometry + motion
# x = along the wall, y = out from the wall, units in m and degrees
#
# cell width  X = 2*l*cos(theta)
# row pitch   p = h + l*sin(theta)     (theta < 0 -> reentrant / auxetic)

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from matplotlib import animation

DEG = np.pi / 180

# ---------------- inputs ----------------
h = 0.60            # straight rib (carries a plate)
l = 0.35            # inclined rib
theta_closed = -40  # closed
theta_open = -5     # open
n_cols = 14
n_rows = 5
wall_gap = 0.18


def cell_width(theta):
    return 2 * l * np.cos(theta * DEG)


def row_pitch(theta):
    return h + l * np.sin(theta * DEG)


def build_lattice(theta):
    X = cell_width(theta)
    p = row_pitch(theta)
    nodes = []
    members = []  # (i, j, type)
    B = {}
    T = {}

    for r in range(n_rows):
        off = (r % 2) * X / 2   # every other row shifted half a cell
        for c in range(n_cols):
            x = (c - (n_cols - 1) / 2) * X + off - X / 4
            y = wall_gap + r * p
            B[r, c] = len(nodes)
            nodes.append((x, y))
            T[r, c] = len(nodes)
            nodes.append((x, y + h))
            members.append((B[r, c], T[r, c], "straight"))

    # inclined ribs: top of each straight rib -> bottom of the 2 ribs in the next row
    for r in range(n_rows - 1):
        off2 = ((r + 1) % 2) * X / 2
        for c in range(n_cols):
            xT = nodes[T[r, c]][0]
            for side in (-1, 1):
                tx = xT + side * X / 2
                c2 = round((tx - off2 + X / 4) / X + (n_cols - 1) / 2)
                if 0 <= c2 < n_cols:
                    members.append((T[r, c], B[r + 1, c2], "inclined"))

    return np.array(nodes), members


def lengths(nodes, members):
    return np.array([np.linalg.norm(nodes[j] - nodes[i]) for i, j, _ in members])


# plates - sized so they tile when closed (brick pattern)
plate_w = cell_width(theta_closed) / 2 * 0.96
plate_L = 2 * row_pitch(theta_closed) * 0.97


def open_area(theta):
    return 1 - (cell_width(theta_closed) * row_pitch(theta_closed)) / (cell_width(theta) * row_pitch(theta))


def poisson(theta):
    # gibson & ashby
    s = np.sin(theta * DEG)
    return np.cos(theta * DEG) ** 2 / ((h / l + s) * s)


def poisson_numeric(theta, d=1e-4):
    ex = (cell_width(theta + d) - cell_width(theta)) / cell_width(theta)
    ey = (row_pitch(theta + d) - row_pitch(theta)) / row_pitch(theta)
    return -ey / ex


def draw(ax, theta):
    nodes, members = build_lattice(theta)
    k = 0
    for i, j, kind in members:
        if kind == "straight":
            cx, cy = (nodes[i] + nodes[j]) / 2
            col = "#b08a52" if (k // n_cols) % 2 == 0 else "#cdb68a"
            ax.add_patch(Rectangle((cx - plate_w / 2, cy - plate_L / 2), plate_w, plate_L,
                                   color=col, alpha=0.5))
            k += 1
    for i, j, kind in members:
        ax.plot(*zip(nodes[i], nodes[j]), color="k" if kind == "straight" else "teal", lw=1.2)
    ax.plot(nodes[:, 0], nodes[:, 1], ".", color="teal", ms=4)
    ax.axhline(0, color="k", lw=4)  # wall
    ax.set_aspect("equal")
    ax.set_xlim(-6, 6)
    ax.set_ylim(-0.3, 3.6)
    ax.set_title(f"theta = {theta:.0f}  open = {open_area(theta)*100:.0f}%")


if __name__ == "__main__":
    import os
    os.makedirs("images", exist_ok=True)

    nodes, members = build_lattice(theta_closed)
    print(len(nodes), "nodes,", len(members), "members")

    # check that rib lengths don't change (should be ~0)
    L0 = lengths(*build_lattice(theta_closed))
    worst = max(np.max(np.abs(lengths(*build_lattice(t)) - L0)) for t in np.linspace(theta_closed, theta_open, 10))
    print("max rib length change:", worst)

    t = np.linspace(theta_closed, theta_open, 200)
    print("poisson ratio:", round(poisson(t).max(), 2), "to", round(poisson(t).min(), 2))
    print("max diff vs formula:", np.max(np.abs(poisson(t) - poisson_numeric(t))))
    print("open area at full open:", round(open_area(theta_open) * 100), "%")
    print("width:", round(n_cols * cell_width(theta_closed), 2), "->", round(n_cols * cell_width(theta_open), 2))
    print("depth:", round(wall_gap + (n_rows - 1) * row_pitch(theta_closed) + h, 2), "->",
          round(wall_gap + (n_rows - 1) * row_pitch(theta_open) + h, 2))

    # closed / mid / open
    fig, axs = plt.subplots(3, 1, figsize=(10, 10))
    for ax, th in zip(axs, [theta_closed, (theta_closed + theta_open) / 2, theta_open]):
        draw(ax, th)
    plt.tight_layout()
    plt.savefig("images/states.png", dpi=120)

    # poisson ratio + open area
    fig, axs = plt.subplots(1, 2, figsize=(10, 4))
    axs[0].plot(t, poisson(t), label="formula")
    axs[0].plot(t, poisson_numeric(t), "--", label="model")
    axs[0].set_xlabel("theta")
    axs[0].set_ylabel("poisson ratio")
    axs[0].legend()
    axs[1].plot(t, open_area(t) * 100)
    axs[1].set_xlabel("theta")
    axs[1].set_ylabel("% open")
    plt.tight_layout()
    plt.savefig("images/poisson_open_area.png", dpi=120)

    # gif
    fig, ax = plt.subplots(figsize=(9, 3.5))
    frames = list(np.linspace(theta_closed, theta_open, 30)) + list(np.linspace(theta_open, theta_closed, 30))

    def update(th):
        ax.clear()
        draw(ax, th)

    anim = animation.FuncAnimation(fig, update, frames=frames)
    anim.save("images/opening.gif", writer=animation.PillowWriter(fps=15), dpi=80)
    print("saved images/")
