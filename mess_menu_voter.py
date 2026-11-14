"""
Mess Menu Voter
===============
Hostel students rate every meal (1-5 stars + mood tags + a short note), and the
app shows the best and worst dishes of the week so the mess can improve.

Advanced Programming Practice mini-project  -  Python 3 + Tkinter + SQLite
Run it:      python mess_menu_voter.py        (nothing extra to install)
Warden PIN:  1234   (change WARDEN_PIN below)

Pages (each one has its own colour theme):
  1. Mess Pass            sunset-gradient login with an animated steaming bowl
  2. Rate Today's Plate   four colour-coded meal cards, hover-preview stars,
                          mood chips, notes and a weekly rating streak
  3. Hall of Fame/Shame   night-sky page: podium for the top 3 dishes, red cards
                          for the worst 3, bar chart of how each day tasted
  4. Taste Heatmap        7 days x 4 meals grid coloured red -> green; click a
                          square to see its star split, moods and notes
  5. Kitchen Control      warden only: edit the menu, complaint radar with fix
                          tips, student notes, demo data and CSV export

Programming paradigms used:
  Object-oriented  classes for data (Vote, User), storage (Database) and every
                   page; inheritance (each page extends Page, ColorButton
                   extends tk.Label)
  Event-driven     clicks, hovers, key presses and window resizes call handler
                   methods; after() timers drive the animations
  Functional       pure statistics functions using map / filter / sorted /
                   lambda, Counter and comprehensions (no side effects)
  Declarative      SQL tables and queries through sqlite3
"""

import csv
import math
import random
import sqlite3
import tkinter as tk
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

DB_FILE = Path(__file__).with_name("mess_votes.db")
WARDEN_PIN = "1234"
FONT = "Helvetica"

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
MEALS = ["Breakfast", "Lunch", "Snacks", "Dinner"]
MEAL_TIMES = {
    "Breakfast": "7:30 - 9:30 AM",
    "Lunch": "12:00 - 2:00 PM",
    "Snacks": "4:30 - 5:30 PM",
    "Dinner": "7:30 - 9:30 PM",
}
MEAL_COLOURS = {
    "Breakfast": "#e67700",  # sunrise orange
    "Lunch": "#e03131",      # chilli red
    "Snacks": "#0ca678",     # mint green
    "Dinner": "#4c6ef5",     # night blue
}
HOSTELS = ["A Block", "B Block", "C Block", "D Block", "Ladies Hostel 1", "Ladies Hostel 2"]
TAGS = ["Loved it", "Too spicy", "Too salty", "Cold food", "Small portion", "Undercooked"]
STAR_WORDS = ["Tap a star to rate", "Terrible", "Not good", "Okay", "Tasty!", "Mind-blowing!"]
LIT_STAR = "#fff3a3"

COMPLAINT_TIPS = {
    "Too spicy": "Cook a mild batch and keep chilli or pickle on the side.",
    "Too salty": "Taste before serving and add salt at the end of cooking.",
    "Cold food": "Use hot cases and cook smaller, fresher batches during service.",
    "Small portion": "Check the serving ladle size and allow one free refill.",
    "Undercooked": "Start cooking earlier and check rice and dal before service.",
}

DEFAULT_MENU = {  # Breakfast, Lunch, Snacks, Dinner
    "Monday": ["Idli & Sambar", "Veg Biryani & Raita", "Samosa & Tea", "Chapati & Paneer Masala"],
    "Tuesday": ["Pongal & Vada", "Sambar Rice & Poriyal", "Onion Bajji & Coffee", "Fried Rice & Gobi Manchurian"],
    "Wednesday": ["Poori & Potato Masala", "Rasam Rice & Kootu", "Sweet Corn Cup", "Masala Dosa & Chutney"],
    "Thursday": ["Upma & Chutney", "Lemon Rice & Chips", "Pani Puri", "Chole Bhature"],
    "Friday": ["Aloo Paratha & Curd", "Veg Pulao & Dal Fry", "Vada Pav", "Hakka Noodles"],
    "Saturday": ["Rava Dosa & Sambar", "Full Meals Thali", "Bonda & Tea", "Kadai Veg & Naan"],
    "Sunday": ["Mini Tiffin", "Sunday Biryani & Gulab Jamun", "Cake & Coffee", "Pav Bhaji"],
}

# How much the imaginary demo students like each dish (out of 5). Others get 3.3.
DEMO_TASTE = {
    "Sunday Biryani & Gulab Jamun": 4.7, "Pani Puri": 4.4, "Chole Bhature": 4.3,
    "Veg Biryani & Raita": 4.1, "Masala Dosa & Chutney": 4.0, "Pav Bhaji": 4.0,
    "Upma & Chutney": 1.8, "Rasam Rice & Kootu": 2.2, "Lemon Rice & Chips": 2.5,
    "Sambar Rice & Poriyal": 2.7,
}
DEMO_GOOD_NOTES = ["Best meal of the week!", "Please make this every Sunday", "Loved it, thank you", "Perfectly cooked"]
DEMO_BAD_NOTES = ["Too watery today", "Food was cold by 8 pm", "Please use less oil", "Not enough quantity", "Rice was undercooked"]


# ----------------------------------------------------------------------------
# Colour and drawing helpers
# ----------------------------------------------------------------------------
def blend(c1, c2, t):
    """Mix two '#rrggbb' colours: t=0 gives c1, t=1 gives c2."""
    a = [int(c1[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(c2[i:i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(x + (y - x) * t):02x}" for x, y in zip(a, b))


def rating_colour(avg):
    """1 star -> red, 3 stars -> yellow, 5 stars -> green."""
    avg = max(1.0, min(5.0, avg))
    if avg <= 3:
        return blend("#ef4444", "#facc15", (avg - 1) / 2)
    return blend("#facc15", "#22c55e", (avg - 3) / 2)


def draw_gradient(canvas, width, height, top, bottom, tag="bg"):
    steps = max(2, int(height // 3))
    band = height / steps
    for i in range(steps):
        canvas.create_rectangle(
            0, i * band, width, (i + 1) * band + 1,
            fill=blend(top, bottom, i / (steps - 1)), outline="", tags=tag,
        )


def round_rect(canvas, x1, y1, x2, y2, r=16, **kw):
    points = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2,
              x2 - r, y2, x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]
    return canvas.create_polygon(points, smooth=True, **kw)


def star_text(stars):
    n = round(stars)
    return "★" * n + "☆" * (5 - n)


def current_week():
    year, week, _ = date.today().isocalendar()
    return f"{year}-W{week:02d}"


def today_name():
    return DAYS[date.today().weekday()]


# ----------------------------------------------------------------------------
# Data model
# ----------------------------------------------------------------------------
@dataclass
class User:
    name: str
    roll: str
    hostel: str
    is_warden: bool = False


@dataclass
class Vote:
    roll: str
    name: str
    day: str
    meal: str
    dish: str
    stars: int
    tags: list
    comment: str
    created: str


# ----------------------------------------------------------------------------
# Functional core: pure functions that turn a list of votes into results
# ----------------------------------------------------------------------------
def average(numbers):
    numbers = list(numbers)
    return sum(numbers) / len(numbers) if numbers else 0.0


def dish_ranking(votes):
    """[(dish, average stars, number of votes)], best dish first."""
    by_dish = defaultdict(list)
    for v in votes:
        by_dish[v.dish].append(v.stars)
    rows = map(lambda item: (item[0], average(item[1]), len(item[1])), by_dish.items())
    return sorted(rows, key=lambda r: (-r[1], -r[2], r[0]))


def best_and_worst(votes, n=3):
    ranking = dish_ranking(votes)
    best = ranking[:n]
    worst = [r for r in reversed(ranking) if r not in best][:n]
    return best, worst


def day_averages(votes):
    return {day: average(v.stars for v in votes if v.day == day) for day in DAYS}


def votes_by_slot(votes):
    slots = defaultdict(list)
    for v in votes:
        slots[(v.day, v.meal)].append(v)
    return slots


def tag_counts(votes):
    return Counter(tag for v in votes for tag in v.tags)


def top_complaint(votes, dish):
    counts = tag_counts(filter(lambda v: v.dish == dish, votes))
    counts.pop("Loved it", None)
    return counts.most_common(1)[0][0] if counts else ""


# ----------------------------------------------------------------------------
# Storage (declarative SQL)
# ----------------------------------------------------------------------------
class Database:
    def __init__(self, path=DB_FILE):
        self.conn = sqlite3.connect(str(path))
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS menu (
                day  TEXT NOT NULL,
                meal TEXT NOT NULL,
                dish TEXT NOT NULL,
                PRIMARY KEY (day, meal)
            );
            CREATE TABLE IF NOT EXISTS votes (
                roll    TEXT NOT NULL,
                name    TEXT NOT NULL,
                week    TEXT NOT NULL,
                day     TEXT NOT NULL,
                meal    TEXT NOT NULL,
                dish    TEXT NOT NULL,
                stars   INTEGER NOT NULL CHECK (stars BETWEEN 1 AND 5),
                tags    TEXT NOT NULL DEFAULT '',
                comment TEXT NOT NULL DEFAULT '',
                created TEXT NOT NULL,
                PRIMARY KEY (roll, week, day, meal)   -- one vote per student per meal
            );
            """
        )
        if self.conn.execute("SELECT COUNT(*) FROM menu").fetchone()[0] == 0:
            self.conn.executemany(
                "INSERT INTO menu (day, meal, dish) VALUES (?, ?, ?)",
                [(day, meal, dish) for day, dishes in DEFAULT_MENU.items()
                 for meal, dish in zip(MEALS, dishes)],
            )
        self.conn.commit()

    # menu
    def menu(self):
        return {(d, m): dish for d, m, dish in self.conn.execute("SELECT day, meal, dish FROM menu")}

    def set_dish(self, day, meal, dish):
        self.conn.execute("INSERT OR REPLACE INTO menu (day, meal, dish) VALUES (?, ?, ?)", (day, meal, dish))
        self.conn.commit()

    # votes
    def save_vote(self, user, week, day, meal, dish, stars, tags, comment):
        self.conn.execute(
            "INSERT OR REPLACE INTO votes VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (user.roll, user.name, week, day, meal, dish, stars, "|".join(tags), comment,
             datetime.now().isoformat(timespec="seconds")),
        )
        self.conn.commit()

    def week_votes(self, week):
        rows = self.conn.execute(
            """SELECT roll, name, day, meal, dish, stars, tags, comment, created
               FROM votes WHERE week = ? ORDER BY created""",
            (week,),
        )
        return [Vote(r, n, d, m, dish, s, t.split("|") if t else [], c, cr)
                for r, n, d, m, dish, s, t, c, cr in rows]

    def student_votes(self, roll, week, day):
        return {v.meal: v for v in self.week_votes(week) if v.roll == roll and v.day == day}

    def rated_days(self, roll, week):
        rows = self.conn.execute("SELECT DISTINCT day FROM votes WHERE roll = ? AND week = ?", (roll, week))
        return {row[0] for row in rows}

    def clear_week(self, week):
        self.conn.execute("DELETE FROM votes WHERE week = ?", (week,))
        self.conn.commit()

    def seed_demo(self, week, students=30):
        """Fill the week with realistic-looking votes so the charts have something to show."""
        rng = random.Random()
        menu = self.menu()
        rows = []
        for i in range(1, students + 1):
            roll, name = f"DEMO{i:03d}", f"Demo Student {i}"
            for day in DAYS:
                for meal in MEALS:
                    if rng.random() < 0.15:  # some students skip some meals
                        continue
                    dish = menu[(day, meal)]
                    stars = max(1, min(5, round(rng.gauss(DEMO_TASTE.get(dish, 3.3), 0.9))))
                    tags = []
                    if stars >= 4 and rng.random() < 0.5:
                        tags.append("Loved it")
                    if stars <= 3 and rng.random() < 0.6:
                        tags += rng.sample(TAGS[1:], k=rng.choice([1, 1, 2]))
                    note = ""
                    if rng.random() < 0.08:
                        note = rng.choice(DEMO_GOOD_NOTES if stars >= 4 else DEMO_BAD_NOTES)
                    created = datetime.now() - timedelta(minutes=rng.randint(0, 9000))
                    rows.append((roll, name, week, day, meal, dish, stars, "|".join(tags), note,
                                 created.isoformat(timespec="seconds")))
        self.conn.executemany("INSERT OR REPLACE INTO votes VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", rows)
        self.conn.commit()
        return len(rows)

    def close(self):
        self.conn.close()


# ----------------------------------------------------------------------------
# Reusable widgets
# ----------------------------------------------------------------------------
class ColorButton(tk.Label):
    """A flat coloured button with a hover effect.

    Built on tk.Label because tk.Button ignores background colours on macOS,
    so this looks the same on Windows, macOS and Linux.
    """

    def __init__(self, master, text, command, bg, fg="#ffffff", hover=None,
                 font=(FONT, 11, "bold"), padx=16, pady=8):
        super().__init__(master, text=text, font=font, padx=padx, pady=pady, cursor="hand2")
        self.command = command
        self.enabled = True
        self.set_colour(bg, fg, hover)
        self.bind("<Enter>", lambda e: self.enabled and self.config(bg=self.hover_bg))
        self.bind("<Leave>", lambda e: self.config(bg=self.normal_bg))
        self.bind("<Button-1>", lambda e: self.enabled and self.command())

    def set_colour(self, bg, fg=None, hover=None):
        self.normal_bg = bg
        self.hover_bg = hover or blend(bg, "#ffffff", 0.18)
        self.config(bg=bg)
        if fg:
            self.config(fg=fg)

    def set_enabled(self, enabled):
        self.enabled = enabled
        self.config(cursor="hand2" if enabled else "arrow")


class MealCard(tk.Frame):
    """One coloured card on the Rate page: dish, 5 stars, mood chips and a note."""

    def __init__(self, master, meal):
        self.colour = MEAL_COLOURS[meal]
        self.dark = blend(self.colour, "#000000", 0.28)
        super().__init__(master, bg=self.colour, padx=16, pady=14)
        self.stars = 0
        self.tags = set()
        self.dish = ""

        tk.Label(self, text=meal.upper(), font=(FONT, 15, "bold"), fg="#ffffff", bg=self.colour).pack(anchor="w")
        tk.Label(self, text=MEAL_TIMES[meal], font=(FONT, 10), fg=blend(self.colour, "#ffffff", 0.7),
                 bg=self.colour).pack(anchor="w")
        self.dish_label = tk.Label(self, font=(FONT, 14, "bold"), fg="#ffffff", bg=self.dark,
                                   wraplength=200, justify="center", pady=12, padx=8)
        self.dish_label.pack(fill="x", pady=(12, 10))

        star_row = tk.Frame(self, bg=self.colour)
        star_row.pack()
        self.star_labels = []
        for i in range(1, 6):
            star = tk.Label(star_row, text="★", font=(FONT, 26), bg=self.colour, fg=self.dark, cursor="hand2")
            star.pack(side="left")
            star.bind("<Enter>", lambda e, i=i: self.paint_stars(i))
            star.bind("<Leave>", lambda e: self.paint_stars(self.stars))
            star.bind("<Button-1>", lambda e, i=i: self.set_stars(i))
            self.star_labels.append(star)
        self.word = tk.Label(self, font=(FONT, 11, "bold"), fg="#ffffff", bg=self.colour)
        self.word.pack(pady=(0, 10))

        chips = tk.Frame(self, bg=self.colour)
        chips.pack(fill="x")
        chips.columnconfigure((0, 1), weight=1)
        self.chip_labels = {}
        for n, tag in enumerate(TAGS):
            chip = tk.Label(chips, text=tag, font=(FONT, 9, "bold"), padx=6, pady=4, cursor="hand2")
            chip.grid(row=n // 2, column=n % 2, sticky="ew", padx=2, pady=2)
            chip.bind("<Button-1>", lambda e, t=tag: self.toggle_tag(t))
            self.chip_labels[tag] = chip

        tk.Label(self, text="Note for the warden (optional)", font=(FONT, 9),
                 fg=blend(self.colour, "#ffffff", 0.75), bg=self.colour).pack(anchor="w", pady=(10, 2))
        self.note = tk.Entry(self, font=(FONT, 11), relief="flat", bg="#ffffff", fg="#111827",
                             insertbackground=self.colour, highlightthickness=0)
        self.note.pack(fill="x", ipady=4)
        self.status = tk.Label(self, font=(FONT, 9, "italic"), fg="#ffffff", bg=self.colour)
        self.status.pack(anchor="w", pady=(6, 0))
        self.load(0, [], "")

    def set_dish(self, dish):
        self.dish = dish
        self.dish_label.config(text=dish)

    def paint_stars(self, n):
        for i, star in enumerate(self.star_labels):
            star.config(fg=LIT_STAR if i < n else self.dark)
        self.word.config(text=STAR_WORDS[n])

    def set_stars(self, n):
        self.stars = n
        self.paint_stars(n)
        self.status.config(text="Not submitted yet")

    def toggle_tag(self, tag):
        self.tags.symmetric_difference_update({tag})
        self.paint_chips()

    def paint_chips(self):
        for tag, chip in self.chip_labels.items():
            if tag in self.tags:
                chip.config(bg="#ffffff", fg=self.colour)
            else:
                chip.config(bg=self.dark, fg="#ffffff")

    def load(self, stars, tags, comment):
        self.stars = stars
        self.tags = set(tags)
        self.paint_stars(stars)
        self.paint_chips()
        self.note.delete(0, "end")
        self.note.insert(0, comment)
        self.status.config(text="Already rated - change it if you like" if stars else "")

    def get(self):
        return self.stars, [t for t in TAGS if t in self.tags], self.note.get().strip()

    def mark_saved(self):
        self.status.config(text="Saved ✓")


# ----------------------------------------------------------------------------
# Pages
# ----------------------------------------------------------------------------
class Page(tk.Frame):
    key = ""
    bg = "#ffffff"

    def __init__(self, app):
        super().__init__(app.container, bg=self.bg)
        self.app = app

    def on_show(self):
        """Called every time the page is opened."""


class LoginPage(Page):
    """Page 1 - Mess Pass: sunset gradient, floating bubbles and a steaming bowl."""

    key = "login"
    TOP, BOTTOM = "#ff5f6d", "#ffc371"

    def __init__(self, app):
        super().__init__(app)
        self.canvas = tk.Canvas(self, highlightthickness=0, bd=0, bg=self.TOP)
        self.canvas.pack(fill="both", expand=True)
        self.name_var, self.roll_var, self.pin_var = tk.StringVar(), tk.StringVar(), tk.StringVar()
        self.hostel_var = tk.StringVar(value=HOSTELS[0])
        self.role = "Student"
        self.steam, self.steam_base, self.phase = [], (0, 0), 0.0

        self.card = tk.Frame(self.canvas, bg="#ffffff", padx=34, pady=24)
        self._build_card()
        self.card_id = self.canvas.create_window(0, 0, window=self.card)
        self.canvas.bind("<Configure>", lambda e: self.layout())
        self.after(60, self.animate)

    def _build_card(self):
        c = self.card
        tk.Label(c, text="Mess Menu Voter", font=(FONT, 26, "bold"), fg=self.TOP, bg="#ffffff").pack()
        tk.Label(c, text="Your plate. Your vote. Better food.", font=(FONT, 11),
                 fg="#6b7280", bg="#ffffff").pack(pady=(2, 16))

        toggle = tk.Frame(c, bg="#ffffff")
        toggle.pack(pady=(0, 14))
        self.role_buttons = {}
        for role in ("Student", "Warden"):
            button = ColorButton(toggle, role, lambda r=role: self.set_role(r), bg="#f3f4f6", padx=24, pady=6)
            button.pack(side="left", padx=4)
            self.role_buttons[role] = button

        self.fields = tk.Frame(c, bg="#ffffff")
        self.fields.pack(fill="x")
        self.student_rows = [
            self._entry_row("Your name", self.name_var),
            self._entry_row("Roll number", self.roll_var),
            self._combo_row("Hostel block", self.hostel_var, HOSTELS),
        ]
        self.warden_rows = [self._entry_row("Warden PIN", self.pin_var, show="*")]

        ColorButton(c, "Enter the Mess  →", self.login, bg=self.TOP, font=(FONT, 13, "bold"),
                    pady=10).pack(fill="x", pady=(14, 0))
        self.hint = tk.Label(c, font=(FONT, 9), fg="#9ca3af", bg="#ffffff")
        self.hint.pack(pady=(8, 0))
        self.set_role("Student")

    def _entry_row(self, label, var, show=""):
        row = tk.Frame(self.fields, bg="#ffffff")
        tk.Label(row, text=label, font=(FONT, 10, "bold"), fg="#374151", bg="#ffffff").pack(anchor="w")
        entry = tk.Entry(row, textvariable=var, font=(FONT, 13), width=28, relief="flat", show=show,
                         bg="#fff1ec", fg="#111827", insertbackground=self.TOP, highlightthickness=2,
                         highlightbackground="#ffd9cc", highlightcolor=self.TOP)
        entry.pack(fill="x", ipady=6, pady=(3, 10))
        entry.bind("<Return>", lambda e: self.login())
        return row

    def _combo_row(self, label, var, values):
        row = tk.Frame(self.fields, bg="#ffffff")
        tk.Label(row, text=label, font=(FONT, 10, "bold"), fg="#374151", bg="#ffffff").pack(anchor="w")
        ttk.Combobox(row, textvariable=var, values=values, state="readonly",
                     font=(FONT, 12)).pack(fill="x", ipady=4, pady=(3, 10))
        return row

    def set_role(self, role):
        self.role = role
        for name, button in self.role_buttons.items():
            if name == role:
                button.set_colour(self.TOP, fg="#ffffff")
            else:
                button.set_colour("#f3f4f6", fg="#374151")
        for row in self.student_rows + self.warden_rows:
            row.pack_forget()
        for row in (self.warden_rows if role == "Warden" else self.student_rows):
            row.pack(fill="x")
        self.hint.config(text="Warden: edit the menu and read complaints" if role == "Warden"
                         else "One vote per meal - you can change it all week")
        self.after_idle(self.layout)

    def layout(self):
        cv = self.canvas
        w, h = cv.winfo_width(), cv.winfo_height()
        if w < 10 or h < 10:
            return
        cv.delete("bg")
        draw_gradient(cv, w, h, self.TOP, self.BOTTOM)
        rng = random.Random(7)  # same bubbles every redraw
        for _ in range(18):
            x, y, r = rng.randint(0, w), rng.randint(0, h), rng.randint(20, 70)
            colour = blend(blend(self.TOP, self.BOTTOM, y / h), "#ffffff", 0.18)
            cv.create_oval(x - r, y - r, x + r, y + r, fill=colour, outline="", tags="bg")

        card_w, card_h = self.card.winfo_reqwidth(), self.card.winfo_reqheight()
        cx, cy = w / 2, h / 2 + 55
        cv.coords(self.card_id, cx, cy)
        round_rect(cv, cx - card_w / 2 - 14, cy - card_h / 2 - 14, cx + card_w / 2 + 14,
                   cy + card_h / 2 + 14, r=30, fill="#ffffff", outline="", tags="bg")
        self.draw_bowl(cx, cy - card_h / 2 - 26)

    def draw_bowl(self, x, bottom):
        cv = self.canvas
        rim = bottom - 46
        cv.create_arc(x - 60, rim - 26, x + 60, rim + 26, start=0, extent=180,
                      style="chord", fill="#ffb347", outline="", tags="bg")           # rice heap
        for dx, dy, colour in ((-28, -10, "#2f9e44"), (6, -18, "#e03131"), (30, -8, "#2f9e44"), (-6, -6, "#f59f00")):
            cv.create_oval(x + dx - 5, rim + dy - 5, x + dx + 5, rim + dy + 5, fill=colour, outline="", tags="bg")
        cv.create_arc(x - 72, rim - 46, x + 72, bottom, start=180, extent=180,
                      style="chord", fill="#ffffff", outline="", tags="bg")           # bowl
        cv.create_arc(x - 62, rim - 38, x + 62, bottom - 8, start=200, extent=140,
                      style="arc", outline=self.TOP, width=5, tags="bg")              # stripe
        cv.create_oval(x - 74, rim - 6, x + 74, rim + 6, fill="#ffe3d3", outline="", tags="bg")  # rim
        self.steam = [cv.create_line(0, 0, 1, 1, fill="#ffffff", width=4, smooth=True,
                                     capstyle="round", tags="bg") for _ in range(3)]
        self.steam_base = (x, rim - 30)

    def animate(self):
        if self.winfo_ismapped() and self.steam:
            self.phase += 0.18
            x0, y0 = self.steam_base
            for i, line in enumerate(self.steam):
                points = []
                for k in range(12):
                    points += [x0 + (i - 1) * 28 + 7 * math.sin(self.phase + k * 0.55 + i * 2), y0 - k * 5]
                self.canvas.coords(line, *points)
        self.after(50, self.animate)

    def on_show(self):
        for var in (self.name_var, self.roll_var, self.pin_var):
            var.set("")
        self.after_idle(self.layout)

    def login(self):
        if self.role == "Warden":
            if self.pin_var.get() != WARDEN_PIN:
                messagebox.showerror("Wrong PIN", "That warden PIN is not correct.")
                return
            user = User("Warden", "WARDEN", "Mess office", is_warden=True)
        else:
            name, roll = self.name_var.get().strip(), self.roll_var.get().strip().upper()
            if not name or not roll:
                messagebox.showerror("Almost there", "Please type your name and roll number.")
                return
            user = User(name, roll, self.hostel_var.get())
        self.app.login(user)


class RatePage(Page):
    """Page 2 - Rate Today's Plate: fresh mint page with four bright meal cards."""

    key = "rate"
    bg = "#e8fbf4"
    ACCENT = "#0d9488"

    def __init__(self, app):
        super().__init__(app)
        self.day = today_name()
        self.toast_job = None

        top = tk.Frame(self, bg=self.bg)
        top.pack(fill="x", padx=24, pady=(18, 6))
        left = tk.Frame(top, bg=self.bg)
        left.pack(side="left")
        tk.Label(left, text="Rate Today's Plate", font=(FONT, 24, "bold"), fg="#064e3b", bg=self.bg).pack(anchor="w")
        self.subtitle = tk.Label(left, font=(FONT, 11), fg="#047857", bg=self.bg)
        self.subtitle.pack(anchor="w")
        right = tk.Frame(top, bg=self.bg)
        right.pack(side="right")
        tk.Label(right, text="Your rating streak this week", font=(FONT, 10, "bold"),
                 fg="#065f46", bg=self.bg).pack(anchor="e")
        self.streak = tk.Label(right, font=(FONT, 18, "bold"), fg=self.ACCENT, bg=self.bg)
        self.streak.pack(anchor="e")

        days = tk.Frame(self, bg=self.bg)
        days.pack(fill="x", padx=24, pady=(4, 10))
        self.day_buttons = {}
        for day in DAYS:
            button = ColorButton(days, day[:3], lambda d=day: self.select_day(d), bg="#ffffff",
                                 fg=self.ACCENT, padx=14, pady=6)
            button.pack(side="left", padx=(0, 6))
            self.day_buttons[day] = button

        cards = tk.Frame(self, bg=self.bg)
        cards.pack(fill="both", expand=True, padx=18)
        cards.rowconfigure(0, weight=1)
        self.cards = {}
        for i, meal in enumerate(MEALS):
            card = MealCard(cards, meal)
            card.grid(row=0, column=i, sticky="nsew", padx=6, pady=4)
            cards.columnconfigure(i, weight=1, uniform="cards")
            self.cards[meal] = card

        bottom = tk.Frame(self, bg=self.bg)
        bottom.pack(fill="x", padx=24, pady=14)
        ColorButton(bottom, "Submit my ratings", self.submit, bg=self.ACCENT, font=(FONT, 14, "bold"),
                    padx=28, pady=10).pack(side="right")
        self.toast = tk.Label(bottom, font=(FONT, 12, "bold"), fg="#047857", bg=self.bg)
        self.toast.pack(side="left")

    def on_show(self):
        self.toast.config(text="")
        self.select_day(today_name())

    def select_day(self, day):
        self.day = day
        today_index = date.today().weekday()
        for i, (name, button) in enumerate(self.day_buttons.items()):
            if name == day:
                button.set_colour(self.ACCENT, fg="#ffffff")
                button.set_enabled(True)
            elif i > today_index:  # can't rate food that hasn't been served yet
                button.set_colour("#e5e7eb", fg="#9ca3af", hover="#e5e7eb")
                button.set_enabled(False)
            else:
                button.set_colour("#ffffff", fg=self.ACCENT)
                button.set_enabled(True)

        menu = self.app.db.menu()
        mine = self.app.db.student_votes(self.app.user.roll, current_week(), day)
        for meal, card in self.cards.items():
            dish = menu[(day, meal)]
            card.set_dish(dish)
            vote = mine.get(meal)
            if vote and vote.dish == dish:
                card.load(vote.stars, vote.tags, vote.comment)
            else:
                card.load(0, [], "")
        label = "Today" if day == today_name() else day
        self.subtitle.config(text=f"{label}'s menu  ·  tap the stars, pick a mood, then submit")
        self.refresh_streak()

    def refresh_streak(self):
        rated = self.app.db.rated_days(self.app.user.roll, current_week())
        dots = " ".join("●" if day in rated else "○" for day in DAYS)
        self.streak.config(text=f"{dots}   {len(rated)}/7")

    def submit(self):
        user = self.app.user
        saved = 0
        for meal, card in self.cards.items():
            stars, tags, comment = card.get()
            if stars:
                self.app.db.save_vote(user, current_week(), self.day, meal, card.dish, stars, tags, comment)
                card.mark_saved()
                saved += 1
        if not saved:
            self.show_toast("Tap at least one star before submitting.", "#b91c1c")
            return
        self.show_toast(f"Saved {saved} rating{'s' if saved > 1 else ''} - thanks, {user.name}!")
        self.refresh_streak()

    def show_toast(self, text, colour="#047857"):
        if self.toast_job:
            self.after_cancel(self.toast_job)
        self.toast.config(text=text, fg=colour)
        self.toast_job = self.after(4000, lambda: self.toast.config(text=""))


class LeaderboardPage(Page):
    """Page 3 - Hall of Fame & Hall of Shame: a twinkling night sky with a podium."""

    key = "hall"
    TOP, BOTTOM = "#140b34", "#3b1a6b"

    def __init__(self, app):
        super().__init__(app)
        self.canvas = tk.Canvas(self, highlightthickness=0, bd=0, bg=self.TOP)
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Configure>", lambda e: self.draw())
        self.sky = []
        self.after(350, self.twinkle)

    def on_show(self):
        self.draw()

    def draw(self):
        cv = self.canvas
        w, h = cv.winfo_width(), cv.winfo_height()
        if w < 100 or h < 100:
            return
        cv.delete("all")
        draw_gradient(cv, w, h, self.TOP, self.BOTTOM)
        rng = random.Random(3)
        self.sky = []
        for _ in range(70):
            x, y, r = rng.randint(0, w), rng.randint(0, h), rng.choice([1, 1, 2])
            self.sky.append(cv.create_oval(x - r, y - r, x + r, y + r, fill="#c4b5fd", outline=""))

        split = w * 0.58
        cv.create_text(40, 44, anchor="w", text="Hall of Fame", font=(FONT, 26, "bold"), fill="#fcd34d")
        cv.create_text(split + 20, 44, anchor="w", text="Hall of Shame", font=(FONT, 26, "bold"), fill="#fb7185")

        votes = self.app.db.week_votes(current_week())
        if not votes:
            cv.create_text(w / 2, h / 2, text="No votes yet this week", font=(FONT, 22, "bold"), fill="#ffffff")
            cv.create_text(w / 2, h / 2 + 34, font=(FONT, 12), fill="#c4b5fd",
                           text="Rate meals on the Rate Today page - the podium fills up as votes come in.")
            return

        students = len({v.roll for v in votes})
        cv.create_text(40, 76, anchor="w", font=(FONT, 11), fill="#c4b5fd",
                       text=f"{len(votes)} votes from {students} students this week  ·  "
                            f"overall {average(v.stars for v in votes):.1f} ★")
        best, worst = best_and_worst(votes)
        chart_top = h * 0.60
        self.draw_podium(cv, best, 40, split - 30, 110, chart_top - 30)
        self.draw_shame(cv, worst, votes, split + 20, w - 40, 100)
        self.draw_day_chart(cv, votes, 40, w - 40, chart_top, h - 28)

    def draw_podium(self, cv, best, x0, x1, y0, base):
        slot = (x1 - x0) / 3
        block_w = slot * 0.72
        tallest = max(60, base - y0 - 95)
        cv.create_line(x0, base, x1, base, fill="#a78bfa", width=2)
        # (position in best list, height ratio, colour) drawn left-to-right as 2nd, 1st, 3rd
        for slot_i, (rank, ratio, colour) in enumerate([(1, 0.72, "#cbd5e1"), (0, 1.0, "#fbbf24"), (2, 0.5, "#d97706")]):
            if rank >= len(best):
                continue
            dish, avg, count = best[rank]
            cx = x0 + slot * slot_i + slot / 2
            top = base - tallest * ratio
            cv.create_rectangle(cx - block_w / 2, top, cx + block_w / 2, base, fill=colour, outline="")
            cv.create_rectangle(cx - block_w / 2, top, cx + block_w / 2, top + 8,
                                fill=blend(colour, "#ffffff", 0.4), outline="")
            cv.create_text(cx, (top + base) / 2 + 4, text=str(rank + 1),
                           font=(FONT, 34, "bold"), fill=blend(colour, "#000000", 0.45))
            cv.create_text(cx, top - 10, anchor="s", text=f"★ {avg:.1f}  ·  {count} votes",
                           font=(FONT, 10), fill="#fde68a")
            name = cv.create_text(cx, top - 30, anchor="s", text=dish, width=slot - 10,
                                  justify="center", font=(FONT, 12, "bold"), fill="#ffffff")
            if rank == 0:  # crown for the winner
                y = cv.bbox(name)[1] - 18
                cv.create_polygon(cx - 22, y + 12, cx - 22, y - 6, cx - 11, y + 3, cx, y - 12,
                                  cx + 11, y + 3, cx + 22, y - 6, cx + 22, y + 12, fill="#fbbf24", outline="")

    def draw_shame(self, cv, worst, votes, x0, x1, y0):
        if not worst:
            cv.create_text(x0, y0 + 20, anchor="w", text="Not enough dishes rated yet.",
                           font=(FONT, 12), fill="#fecdd3")
            return
        card_h = 76
        for i, (dish, avg, count) in enumerate(worst):
            y = y0 + i * (card_h + 12)
            round_rect(cv, x0, y, x1, y + card_h, r=16, fill="#4c0519", outline="#fb7185", width=2)
            cv.create_text(x0 + 18, y + 16, anchor="w", text=f"#{i + 1} LOWEST RATED",
                           font=(FONT, 9, "bold"), fill="#fda4af")
            cv.create_text(x0 + 18, y + 37, anchor="w", text=dish, width=x1 - x0 - 110,
                           font=(FONT, 14, "bold"), fill="#ffffff")
            complaint = top_complaint(votes, dish) or "no complaint tags"
            cv.create_text(x0 + 18, y + 59, anchor="w", text=f"Most said: {complaint}",
                           font=(FONT, 10), fill="#fecdd3")
            cv.create_text(x1 - 18, y + card_h / 2 - 8, anchor="e", text=f"{avg:.1f}★",
                           font=(FONT, 20, "bold"), fill="#fb7185")
            cv.create_text(x1 - 18, y + card_h / 2 + 16, anchor="e", text=f"{count} votes",
                           font=(FONT, 9), fill="#fda4af")

    def draw_day_chart(self, cv, votes, x0, x1, y0, y1):
        cv.create_text(x0, y0, anchor="w", text="How each day tasted  (average stars)",
                       font=(FONT, 13, "bold"), fill="#ffffff")
        top, bottom, left = y0 + 28, y1 - 22, x0 + 28
        for s in range(1, 6):
            y = bottom - (bottom - top) * s / 5
            cv.create_line(left, y, x1, y, fill="#3f2d74", dash=(2, 4))
            cv.create_text(left - 8, y, anchor="e", text=str(s), fill="#a78bfa", font=(FONT, 9))
        cv.create_line(left, bottom, x1, bottom, fill="#a78bfa")
        averages = day_averages(votes)
        best_day = max(averages, key=averages.get)
        slot = (x1 - left) / 7
        for i, day in enumerate(DAYS):
            cx = left + slot * i + slot / 2
            avg = averages[day]
            is_best = day == best_day and avg > 0
            cv.create_text(cx, bottom + 12, text=day[:3] + ("  ★ best" if is_best else ""),
                           fill="#fcd34d" if is_best else "#c4b5fd", font=(FONT, 10, "bold"))
            if not avg:
                cv.create_text(cx, bottom - 10, text="no votes", fill="#7c6fb0", font=(FONT, 9))
                continue
            bar_top = bottom - (bottom - top) * avg / 5
            cv.create_rectangle(cx - slot * 0.28, bar_top, cx + slot * 0.28, bottom,
                                fill=rating_colour(avg), outline="")
            cv.create_text(cx, bar_top - 9, text=f"{avg:.1f}", fill="#ffffff", font=(FONT, 10, "bold"))

    def twinkle(self):
        if self.winfo_ismapped() and len(self.sky) >= 6:
            for dot in random.sample(self.sky, 6):
                self.canvas.itemconfig(dot, fill=random.choice(["#ffffff", "#c4b5fd", "#6d5fa8", "#fde68a"]))
        self.after(350, self.twinkle)


class HeatmapPage(Page):
    """Page 4 - Taste Heatmap: warm cream page, 28 coloured squares, click for details."""

    key = "heatmap"
    bg = "#fff7e8"

    def __init__(self, app):
        super().__init__(app)
        self.slots = {}
        self.selected = None

        head = tk.Frame(self, bg=self.bg)
        head.pack(fill="x", padx=24, pady=(18, 4))
        tk.Label(head, text="Taste Heatmap", font=(FONT, 24, "bold"), fg="#9a3412", bg=self.bg).pack(anchor="w")
        tk.Label(head, font=(FONT, 11), fg="#c2410c", bg=self.bg,
                 text="Every square is one meal this week. Green = loved, red = disliked, "
                      "grey = no votes yet. Click a square for details.").pack(anchor="w")

        body = tk.Frame(self, bg=self.bg)
        body.pack(fill="both", expand=True, padx=18, pady=10)
        self.canvas = tk.Canvas(body, bg=self.bg, highlightthickness=0)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.panel = tk.Frame(body, bg="#ffffff", width=300, padx=18, pady=16)
        self.panel.pack(side="right", fill="y", padx=(12, 6))
        self.panel.pack_propagate(False)
        self.canvas.bind("<Configure>", lambda e: self.draw())

    def on_show(self):
        self.draw()
        self.show_detail(self.selected)

    def draw(self):
        cv = self.canvas
        w, h = cv.winfo_width(), cv.winfo_height()
        if w < 100 or h < 100:
            return
        cv.delete("all")
        self.slots = votes_by_slot(self.app.db.week_votes(current_week()))
        menu = self.app.db.menu()
        left, top, legend_h = 112, 34, 46
        cell_w = (w - left - 8) / 4
        cell_h = (h - top - legend_h) / 7

        for j, meal in enumerate(MEALS):
            cv.create_text(left + cell_w * j + cell_w / 2, top - 16, text=meal.upper(),
                           font=(FONT, 11, "bold"), fill=MEAL_COLOURS[meal])
        for i, day in enumerate(DAYS):
            y = top + cell_h * i
            is_today = day == today_name()
            if is_today:
                round_rect(cv, 0, y + 1, w - 2, y + cell_h - 1, r=14, fill="#fde2bd", outline="")
            cv.create_text(left - 14, y + cell_h / 2, anchor="e", text=day + ("\ntoday" if is_today else ""),
                           justify="right", font=(FONT, 12, "bold"), fill="#7c2d12")
            for j, meal in enumerate(MEALS):
                x = left + cell_w * j
                key = (day, meal)
                cell_votes = self.slots.get(key, [])
                avg = average(v.stars for v in cell_votes)
                tag = f"cell{i}{j}"
                round_rect(cv, x + 4, y + 4, x + cell_w - 4, y + cell_h - 4, r=12,
                           fill=rating_colour(avg) if cell_votes else "#e7e5e4",
                           outline="#1f2937" if key == self.selected else "", width=3, tags=tag)
                cv.create_text(x + cell_w / 2, y + cell_h / 2 - 9, text=menu[key], width=cell_w - 18,
                               justify="center", font=(FONT, 10, "bold"), fill="#1f2937", tags=tag)
                stats = f"★ {avg:.1f}  ·  {len(cell_votes)} votes" if cell_votes else "no votes yet"
                cv.create_text(x + cell_w / 2, y + cell_h / 2 + 12, text=stats,
                               font=(FONT, 9), fill="#374151", tags=tag)
                cv.tag_bind(tag, "<Button-1>", lambda e, k=key: self.select(k))
                cv.tag_bind(tag, "<Enter>", lambda e: cv.config(cursor="hand2"))
                cv.tag_bind(tag, "<Leave>", lambda e: cv.config(cursor=""))

        # colour legend
        ly = h - 22
        cv.create_text(left, ly, anchor="w", text="1★ disliked", font=(FONT, 9, "bold"), fill="#7c2d12")
        bar_x = left + 80
        for k in range(100):
            cv.create_rectangle(bar_x + k * 2.4, ly - 7, bar_x + (k + 1) * 2.4 + 1, ly + 7,
                                fill=rating_colour(1 + 4 * k / 99), outline="")
        cv.create_text(bar_x + 250, ly, anchor="w", text="5★ loved", font=(FONT, 9, "bold"), fill="#7c2d12")
        cv.create_rectangle(bar_x + 340, ly - 7, bar_x + 360, ly + 7, fill="#e7e5e4", outline="")
        cv.create_text(bar_x + 366, ly, anchor="w", text="no votes", font=(FONT, 9, "bold"), fill="#7c2d12")

    def select(self, key):
        self.selected = key
        self.draw()
        self.show_detail(key)

    def show_detail(self, key):
        p = self.panel
        for child in p.winfo_children():
            child.destroy()
        if key is None:
            tk.Label(p, text="Meal details", font=(FONT, 16, "bold"), fg="#9a3412", bg="#ffffff").pack(anchor="w")
            tk.Label(p, text="Click any square to see its star split, the moods students picked "
                             "and their notes.", font=(FONT, 11), fg="#6b7280", bg="#ffffff",
                     wraplength=260, justify="left").pack(anchor="w", pady=8)
            return

        day, meal = key
        votes = self.slots.get(key, [])
        tk.Label(p, text=f"{day.upper()}  ·  {meal.upper()}", font=(FONT, 10, "bold"),
                 fg=MEAL_COLOURS[meal], bg="#ffffff").pack(anchor="w")
        tk.Label(p, text=self.app.db.menu()[key], font=(FONT, 16, "bold"), fg="#1f2937", bg="#ffffff",
                 wraplength=260, justify="left").pack(anchor="w", pady=(2, 10))
        if not votes:
            tk.Label(p, text="No votes yet for this meal.", font=(FONT, 11), fg="#6b7280", bg="#ffffff").pack(anchor="w")
            return

        avg = average(v.stars for v in votes)
        tk.Label(p, text=f"{avg:.1f}", font=(FONT, 36, "bold"), fg=blend(rating_colour(avg), "#000000", 0.3),
                 bg="#ffffff").pack(anchor="w")
        tk.Label(p, text=f"{star_text(avg)}   {len(votes)} votes", font=(FONT, 12),
                 fg="#b45309", bg="#ffffff").pack(anchor="w")

        split = Counter(v.stars for v in votes)
        most = max(split.values())
        bars = tk.Canvas(p, bg="#ffffff", width=260, height=112, highlightthickness=0)
        bars.pack(anchor="w", pady=(10, 8))
        for row, s in enumerate(range(5, 0, -1)):
            y = row * 22 + 4
            bar_w = 180 * split.get(s, 0) / most
            bars.create_text(0, y + 7, anchor="w", text=f"{s}★", font=(FONT, 10, "bold"), fill="#374151")
            bars.create_rectangle(34, y, 34 + max(bar_w, 2), y + 14, fill=rating_colour(s), outline="")
            bars.create_text(40 + bar_w, y + 7, anchor="w", text=str(split.get(s, 0)), font=(FONT, 9), fill="#6b7280")

        moods = tag_counts(votes).most_common(3)
        if moods:
            tk.Label(p, text="Top moods", font=(FONT, 10, "bold"), fg="#9a3412", bg="#ffffff").pack(anchor="w")
            for tag, count in moods:
                colour = "#dcfce7" if tag == "Loved it" else "#fee2e2"
                tk.Label(p, text=f"{tag}  ×{count}", font=(FONT, 10, "bold"), bg=colour, fg="#1f2937",
                         padx=8, pady=3).pack(anchor="w", pady=2)
        notes = [v for v in reversed(votes) if v.comment][:2]
        if notes:
            tk.Label(p, text="Latest notes", font=(FONT, 10, "bold"), fg="#9a3412", bg="#ffffff").pack(anchor="w", pady=(8, 0))
            for v in notes:
                tk.Label(p, text=f'"{v.comment}"', font=(FONT, 10, "italic"), fg="#374151", bg="#ffffff",
                         wraplength=260, justify="left").pack(anchor="w")


class KitchenPage(Page):
    """Page 5 - Kitchen Control (warden only): dark dashboard with cyan accents."""

    key = "kitchen"
    bg = "#0f172a"
    CARD = "#1e293b"
    ACCENT = "#22d3ee"
    TEXT = "#e2e8f0"
    MUTED = "#94a3b8"

    def __init__(self, app):
        super().__init__(app)
        self.complaints, self.loved = [], 0

        head = tk.Frame(self, bg=self.bg)
        head.pack(fill="x", padx=24, pady=(18, 8))
        tk.Label(head, text="Kitchen Control", font=(FONT, 24, "bold"), fg=self.ACCENT, bg=self.bg).pack(anchor="w")
        tk.Label(head, text="Warden dashboard: change the menu, spot complaints early and read students' notes.",
                 font=(FONT, 11), fg=self.MUTED, bg=self.bg).pack(anchor="w")

        tiles = tk.Frame(self, bg=self.bg)
        tiles.pack(fill="x", padx=18)
        self.tiles = {}
        tile_info = [("votes", "Votes this week", "#22d3ee"), ("students", "Students who voted", "#a78bfa"),
                     ("avg", "Average rating", "#4ade80"), ("complaint", "Top complaint", "#fb7185")]
        for i, (key, label, colour) in enumerate(tile_info):
            tile = tk.Frame(tiles, bg=self.CARD, padx=16, pady=10)
            tile.grid(row=0, column=i, sticky="nsew", padx=6)
            tiles.columnconfigure(i, weight=1, uniform="tiles")
            value = tk.Label(tile, text="-", font=(FONT, 22, "bold"), fg=colour, bg=self.CARD)
            value.pack(anchor="w")
            tk.Label(tile, text=label, font=(FONT, 10), fg=self.MUTED, bg=self.CARD).pack(anchor="w")
            self.tiles[key] = value

        body = tk.Frame(self, bg=self.bg)
        body.pack(fill="both", expand=True, padx=18, pady=12)
        body.rowconfigure(0, weight=1)
        for i in range(3):
            body.columnconfigure(i, weight=1, uniform="body")
        self._build_menu_editor(self._card(body, 0, "Edit the weekly menu"))

        radar = self._card(body, 1, "Complaint radar")
        self.radar = tk.Canvas(radar, bg=self.CARD, height=190, highlightthickness=0)
        self.radar.pack(fill="x")
        self.radar.bind("<Configure>", lambda e: self.draw_radar())
        self.tip = tk.Label(radar, font=(FONT, 11), fg=self.TEXT, bg=self.CARD, wraplength=290, justify="left")
        self.tip.pack(anchor="w", pady=(8, 0))

        notes = self._card(body, 2, "Student notes (latest first)")
        self.notes = tk.Text(notes, bg=self.bg, fg=self.TEXT, relief="flat", wrap="word", font=(FONT, 11),
                             padx=10, pady=8, highlightthickness=0, width=30, height=10)
        self.notes.pack(fill="both", expand=True)
        self.notes.tag_configure("stars", foreground="#fbbf24")
        self.notes.tag_configure("dish", foreground="#ffffff", font=(FONT, 11, "bold"))
        self.notes.tag_configure("text", foreground=self.TEXT, font=(FONT, 11, "italic"))
        self.notes.tag_configure("meta", foreground=self.MUTED, font=(FONT, 9))

        bar = tk.Frame(self, bg=self.bg)
        bar.pack(fill="x", padx=24, pady=(0, 16))
        ColorButton(bar, "Load demo votes", self.load_demo, bg="#22d3ee", fg="#0f172a").pack(side="left")
        ColorButton(bar, "Export week report (CSV)", self.export_csv, bg="#8b5cf6").pack(side="left", padx=8)
        ColorButton(bar, "Clear this week's votes", self.clear_week, bg="#e11d48").pack(side="right")
        self.bar_status = tk.Label(bar, font=(FONT, 11, "bold"), fg="#4ade80", bg=self.bg)
        self.bar_status.pack(side="left", padx=12)

    def _card(self, parent, column, title):
        card = tk.Frame(parent, bg=self.CARD, padx=18, pady=14)
        card.grid(row=0, column=column, sticky="nsew", padx=6)
        tk.Label(card, text=title, font=(FONT, 14, "bold"), fg="#ffffff", bg=self.CARD).pack(anchor="w", pady=(0, 10))
        return card

    def _build_menu_editor(self, card):
        self.edit_day = tk.StringVar(value=today_name())
        self.edit_meal = tk.StringVar(value=MEALS[0])
        self.edit_dish = tk.StringVar()
        for label, var, values in (("Day", self.edit_day, DAYS), ("Meal", self.edit_meal, MEALS)):
            tk.Label(card, text=label, font=(FONT, 10, "bold"), fg=self.MUTED, bg=self.CARD).pack(anchor="w")
            combo = ttk.Combobox(card, textvariable=var, values=values, state="readonly",
                                 style="Dark.TCombobox", font=(FONT, 12))
            combo.pack(fill="x", ipady=3, pady=(2, 8))
            combo.bind("<<ComboboxSelected>>", lambda e: self.load_dish())
        tk.Label(card, text="Dish name", font=(FONT, 10, "bold"), fg=self.MUTED, bg=self.CARD).pack(anchor="w")
        entry = tk.Entry(card, textvariable=self.edit_dish, font=(FONT, 12), bg=self.bg, fg=self.TEXT,
                         insertbackground=self.ACCENT, relief="flat", highlightthickness=1,
                         highlightbackground="#334155", highlightcolor=self.ACCENT)
        entry.pack(fill="x", ipady=5, pady=(2, 10))
        entry.bind("<Return>", lambda e: self.save_dish())
        ColorButton(card, "Save dish", self.save_dish, bg="#22d3ee", fg="#0f172a").pack(anchor="w")
        tk.Label(card, text="Today's menu", font=(FONT, 11, "bold"), fg="#ffffff",
                 bg=self.CARD).pack(anchor="w", pady=(16, 4))
        self.today_box = tk.Frame(card, bg=self.CARD)
        self.today_box.pack(fill="x")

    def on_show(self):
        self.bar_status.config(text="")
        self.refresh()

    def refresh(self):
        votes = self.app.db.week_votes(current_week())
        counts = tag_counts(votes)
        self.loved = counts.pop("Loved it", 0)
        self.complaints = sorted(((t, counts.get(t, 0)) for t in TAGS[1:]), key=lambda item: -item[1])
        worst_tag = self.complaints[0] if self.complaints and self.complaints[0][1] else None

        self.tiles["votes"].config(text=str(len(votes)))
        self.tiles["students"].config(text=str(len({v.roll for v in votes})))
        self.tiles["avg"].config(text=f"{average(v.stars for v in votes):.1f} ★" if votes else "-")
        self.tiles["complaint"].config(text=worst_tag[0] if worst_tag else "None")

        self.draw_radar()
        if worst_tag:
            ranking = dish_ranking(votes)
            lowest = ranking[-1]
            self.tip.config(text=f"Fix first: {worst_tag[0]} ({worst_tag[1]} votes)\n"
                                 f"Tip: {COMPLAINT_TIPS[worst_tag[0]]}\n\n"
                                 f"Lowest rated dish: {lowest[0]} ({lowest[1]:.1f}★)")
        else:
            self.tip.config(text="No complaints yet - nice work, kitchen team!")

        self.notes.config(state="normal")
        self.notes.delete("1.0", "end")
        noted = sorted((v for v in votes if v.comment), key=lambda v: v.created, reverse=True)[:40]
        if not noted:
            self.notes.insert("end", "No notes from students yet.", "meta")
        for v in noted:
            self.notes.insert("end", star_text(v.stars) + "  ", "stars")
            self.notes.insert("end", v.dish + "\n", "dish")
            self.notes.insert("end", f'"{v.comment}"\n', "text")
            self.notes.insert("end", f"{v.name}  ·  {v.day[:3]} {v.meal}\n\n", "meta")
        self.notes.config(state="disabled")

        self.load_dish()
        self.refresh_today_menu()

    def draw_radar(self):
        cv = self.radar
        cv.delete("all")
        w = max(cv.winfo_width(), 260)
        items = self.complaints + [("Loved it", self.loved)]
        most = max([count for _, count in items] + [1])
        for row, (tag, count) in enumerate(items):
            y = 6 + row * 30
            colour = "#4ade80" if tag == "Loved it" else "#fb7185"
            bar_w = (w - 150) * count / most
            cv.create_text(0, y + 9, anchor="w", text=tag, fill=self.TEXT, font=(FONT, 10))
            cv.create_rectangle(100, y + 2, 100 + max(bar_w, 2), y + 16, fill=colour, outline="")
            cv.create_text(106 + bar_w, y + 9, anchor="w", text=str(count), fill=self.MUTED, font=(FONT, 10, "bold"))

    def load_dish(self):
        self.edit_dish.set(self.app.db.menu()[(self.edit_day.get(), self.edit_meal.get())])

    def save_dish(self):
        dish = self.edit_dish.get().strip()
        if not dish:
            messagebox.showerror("Empty dish", "Please type a dish name.")
            return
        self.app.db.set_dish(self.edit_day.get(), self.edit_meal.get(), dish)
        self.bar_status.config(text=f"Saved: {self.edit_day.get()} {self.edit_meal.get()} → {dish}")
        self.refresh_today_menu()

    def refresh_today_menu(self):
        for child in self.today_box.winfo_children():
            child.destroy()
        menu = self.app.db.menu()
        for meal in MEALS:
            row = tk.Frame(self.today_box, bg=self.CARD)
            row.pack(fill="x", pady=1)
            tk.Label(row, text=meal, width=9, anchor="w", font=(FONT, 10, "bold"),
                     fg=blend(MEAL_COLOURS[meal], "#ffffff", 0.3), bg=self.CARD).pack(side="left")
            tk.Label(row, text=menu[(today_name(), meal)], font=(FONT, 10), fg=self.TEXT, bg=self.CARD).pack(side="left")

    def load_demo(self):
        added = self.app.db.seed_demo(current_week())
        self.refresh()
        self.bar_status.config(text=f"Added {added} demo votes from 30 imaginary students")

    def clear_week(self):
        if messagebox.askyesno("Clear votes", "Delete ALL votes for this week? This cannot be undone."):
            self.app.db.clear_week(current_week())
            self.refresh()
            self.bar_status.config(text="This week's votes were cleared")

    def export_csv(self):
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv")],
                                            initialfile=f"mess-report-{current_week()}.csv")
        if path:
            rows = self.write_report(path)
            self.bar_status.config(text=f"Report saved with {rows} dishes")

    def write_report(self, path):
        votes = self.app.db.week_votes(current_week())
        ranking = dish_ranking(votes)
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Rank", "Dish", "Average stars", "Votes", "Top complaint"])
            for rank, (dish, avg, count) in enumerate(ranking, start=1):
                writer.writerow([rank, dish, f"{avg:.2f}", count, top_complaint(votes, dish)])
        return len(ranking)


# ----------------------------------------------------------------------------
# Navigation bar and main window
# ----------------------------------------------------------------------------
class NavBar(tk.Frame):
    BG = "#111827"
    # (page key, label, accent colour, who can see it)
    ITEMS = [("rate", "Rate Today", "#0d9488", "student"),
             ("hall", "Hall of Fame", "#a855f7", "all"),
             ("heatmap", "Taste Heatmap", "#f97316", "all"),
             ("kitchen", "Kitchen Control", "#06b6d4", "warden")]

    def __init__(self, app):
        super().__init__(app, bg=self.BG, padx=16, pady=10)
        brand = tk.Frame(self, bg=self.BG)
        brand.pack(side="left")
        for meal in MEALS:
            tk.Label(brand, text="●", fg=MEAL_COLOURS[meal], bg=self.BG, font=(FONT, 14)).pack(side="left")
        tk.Label(brand, text=" Mess Menu Voter", fg="#ffffff", bg=self.BG,
                 font=(FONT, 15, "bold")).pack(side="left", padx=(2, 24))
        self.pill_area = tk.Frame(self, bg=self.BG)
        self.pill_area.pack(side="left")
        self.pills = {}
        for key, text, colour, who in self.ITEMS:
            button = ColorButton(self.pill_area, text, lambda k=key: app.show(k), bg="#1f2937",
                                 fg="#d1d5db", padx=14, pady=6)
            self.pills[key] = (button, colour, who)
        ColorButton(self, "Log out", app.logout, bg="#374151", padx=12, pady=6).pack(side="right")
        self.user_label = tk.Label(self, fg="#9ca3af", bg=self.BG, font=(FONT, 11))
        self.user_label.pack(side="right", padx=12)

    def set_user(self, user):
        for button, _, who in self.pills.values():
            button.pack_forget()
            if who == "all" or (who == "warden") == user.is_warden:
                button.pack(side="left", padx=3)
        self.user_label.config(text="Warden" if user.is_warden else f"{user.name}  ·  {user.roll}  ·  {user.hostel}")

    def highlight(self, key):
        for name, (button, colour, _) in self.pills.items():
            if name == key:
                button.set_colour(colour, fg="#ffffff")
            else:
                button.set_colour("#1f2937", fg="#d1d5db")


class App(tk.Tk):
    def __init__(self, db_path=DB_FILE):
        super().__init__()
        self.title("Mess Menu Voter")
        self.geometry("1120x720")
        self.minsize(1040, 680)
        self.configure(bg="#111827")
        self.db = Database(db_path)
        self.user = None
        self._style()

        self.nav = NavBar(self)
        self.container = tk.Frame(self, bg="#111827")
        self.container.pack(fill="both", expand=True)
        self.pages = {page.key: page(self) for page in
                      (LoginPage, RatePage, LeaderboardPage, HeatmapPage, KitchenPage)}
        self.current = None
        self.show("login")
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def _style(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("Dark.TCombobox", fieldbackground="#0f172a", background="#334155",
                        foreground="#e2e8f0", arrowcolor="#22d3ee", bordercolor="#334155")
        style.map("Dark.TCombobox",
                  fieldbackground=[("readonly", "#0f172a")], foreground=[("readonly", "#e2e8f0")],
                  selectbackground=[("readonly", "#0f172a")], selectforeground=[("readonly", "#e2e8f0")])
        self.option_add("*TCombobox*Listbox.font", (FONT, 11))

    def show(self, key):
        if self.current is not None:
            self.current.pack_forget()
        self.current = self.pages[key]
        self.current.pack(fill="both", expand=True)
        self.current.on_show()
        self.nav.highlight(key)

    def login(self, user):
        self.user = user
        self.nav.set_user(user)
        self.nav.pack(side="top", fill="x", before=self.container)
        self.show("kitchen" if user.is_warden else "rate")

    def logout(self):
        self.user = None
        self.nav.pack_forget()
        self.show("login")

    def on_close(self):
        self.db.close()
        self.destroy()


if __name__ == "__main__":
    App().mainloop()
