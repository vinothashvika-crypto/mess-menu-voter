# Mess Menu Voter

**Your plate. Your vote. Better food.**

A desktop app where hostel students rate every mess meal (1–5 stars, mood tags and a short note), and the app shows the **best and worst dishes of the week** so the mess can improve.

Advanced Programming Practice (APP) mini-project, built with **Python, Tkinter and SQLite**.

## Features

The app has five pages, each with its own colour theme:

| Page | What it does |
|---|---|
| **Mess Pass** | Login page with a sunset gradient and an animated steaming bowl. Log in as a student or as the warden. |
| **Rate Today's Plate** | Four colour-coded meal cards (Breakfast, Lunch, Snacks, Dinner) with hover-preview stars, mood chips, notes and a weekly rating streak. |
| **Hall of Fame & Shame** | A podium for the top 3 dishes, red cards for the worst 3 with their most common complaint, and a bar chart of each day's average. |
| **Taste Heatmap** | A 7 days × 4 meals grid coloured red → yellow → green. Click a square to see its star split, moods and notes. |
| **Kitchen Control** (warden only) | Summary tiles, a complaint chart with fix tips, students' notes, a menu editor, demo data and CSV report export. |

## How to run

You need **Python 3** with Tkinter. Nothing else to install.

```bash
python3 mess_menu_voter.py
```

- **Warden login:** choose *Warden* and enter the demo PIN `1234` (change `WARDEN_PIN` in the code).
- **Demo data:** log in as warden and click **Load demo votes** to fill the charts with ratings from 30 pretend students.

> **macOS note:** the Python that comes with macOS uses an old Tk version that shows a blank window. Install Python from [python.org](https://www.python.org/downloads/) and run the app with `/usr/local/bin/python3 mess_menu_voter.py`.

Votes are saved in `mess_votes.db` (SQLite), created next to the script the first time it runs.

## Programming paradigms used

| Paradigm | Where in the code |
|---|---|
| **Object-oriented** | Every page is a class built on a shared `Page` class; `User`, `Vote` and `Database` are classes; `ColorButton` extends `tk.Label`. |
| **Event-driven** | Clicks, hovers, key presses and window resizes call handler methods; `after()` timers run the animations. |
| **Functional** | Pure functions such as `dish_ranking()`, `day_averages()` and `top_complaint()` use `map`, `filter`, `sorted`, `lambda` and `Counter`. |
| **Declarative** | SQL `CREATE TABLE`, `INSERT`, `SELECT` and `DELETE` queries through `sqlite3`. |

## Database

- `menu(day, meal, dish)`, primary key `(day, meal)`
- `votes(roll, name, week, day, meal, dish, stars, tags, comment, created)`, primary key `(roll, week, day, meal)`, so each student gets one vote per meal per week. Voting again replaces the old vote.

## Team

- Ashvika VK
- Akshaya P

CSE Core, SRM Institute of Science and Technology. Guided by Dr. Vathana Rufush.
