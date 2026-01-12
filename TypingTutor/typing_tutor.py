# ===================== IMPORTS ===================== #
import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3, random, time, threading
import pyttsx3
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

# ===================== CONFIG ===================== #
DB_NAME = "tutor.db"
USERS = ["Amar", "Sindhu", "Vihu", "Jashu"]
CERT_MILESTONES = [30, 45, 60]

LESSONS = [
    ["f","j"], ["d","k"], ["s","l"], ["a",";"], ["g","h"],
    ["r","u"], ["e","i"], ["w","o"], ["q","p"], ["t","y"],
    ["z","x"], ["c","v"], ["b","n"], ["m"]
]

KEYBOARD_ROWS = [
    list("qwertyuiop"),
    list("asdfghjkl;"),
    list("zxcvbnm")
]

BASE_CORPUS = """
the sun is warm and the sky is blue
we walk on the road and feel happy
a small fish swims in clear water
the wind is soft and calm today
"""

# ===================== DATABASE ===================== #
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS key_stats (
        user TEXT, key TEXT,
        correct INTEGER DEFAULT 0,
        wrong INTEGER DEFAULT 0,
        PRIMARY KEY (user, key)
    )""")

    c.execute("""
    CREATE TABLE IF NOT EXISTS sessions (
        user TEXT, wpm REAL, accuracy REAL,
        date TEXT
    )""")

    c.execute("""
    CREATE TABLE IF NOT EXISTS certificates (
        user TEXT, wpm INTEGER, date TEXT,
        PRIMARY KEY (user, wpm)
    )""")

    conn.commit()
    conn.close()

# ===================== SPEECH ===================== #
class SpeechCoach:
    def __init__(self, mode="Adult"):
        self.engine = pyttsx3.init()
        voices = self.engine.getProperty("voices")
        self.set_mode(mode, voices)

    def set_mode(self, mode, voices):
        self.engine.setProperty("rate", 200 if mode == "Kids" else 160)
        self.engine.setProperty("voice", voices[0].id)

    def speak(self, text):
        threading.Thread(
            target=lambda: (self.engine.say(text), self.engine.runAndWait()),
            daemon=True
        ).start()

# ===================== AI TEXT ===================== #
def build_markov(text):
    model = {}
    for i in range(len(text)-1):
        model.setdefault(text[i], []).append(text[i+1])
    return model

MARKOV = build_markov(BASE_CORPUS)

def generate_ai_text(allowed, weak_keys, length=300):
    pool = list(allowed) + weak_keys * 2
    current = random.choice(pool)
    out = [current]

    for _ in range(length):
        choices = [c for c in MARKOV.get(current, pool) if c in allowed]
        current = random.choice(choices if choices else pool)
        out.append(current)

    return " ".join("".join(out).split())

# ===================== APP ===================== #
class TypingTutor(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Typing Tutor Pro")
        self.set_geometry()
        self.dark_mode = False
        self.user = None
        self.lesson_index = 0
        self.allowed_keys = set()
        self.voice_mode = "Adult"
        self.voice = SpeechCoach(self.voice_mode)
        self.reset_stats()
        self.show_login()

    # ---------- WINDOW ---------- #
    def set_geometry(self):
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"{int(sw*0.9)}x{int(sh*0.9)}")

    # ---------- LOGIN ---------- #
    def show_login(self):
        self.clear()
        f = tk.Frame(self)
        f.pack(expand=True)
        ttk.Label(f, text="Typing Tutor Pro", font=("Segoe UI", 30)).pack(pady=20)

        self.user_box = ttk.Combobox(f, values=USERS, state="readonly")
        self.user_box.pack()

        ttk.Button(f, text="Start", command=self.start_user).pack(pady=10)

    def start_user(self):
        self.user = self.user_box.get()
        self.build_ui()
        self.load_lesson(0)

    # ---------- UI ---------- #
    def build_ui(self):
        self.clear()
        self.left = tk.Frame(self, width=200)
        self.left.pack(side="left", fill="y")
        self.right = tk.Frame(self)
        self.right.pack(side="right", expand=True, fill="both")

        ttk.Button(self.left, text="🌙 Dark Mode",
                   command=self.toggle_dark).pack(pady=5)

        ttk.Button(self.left, text="📊 Progress",
                   command=self.show_progress).pack(pady=5)

        ttk.Button(self.left, text="🎙️ Voice Mode",
                   command=self.toggle_voice).pack(pady=5)

        self.tree = ttk.Treeview(self.left, show="tree")
        self.tree.pack(expand=True, fill="y")
        for i in range(len(LESSONS)):
            self.tree.insert("", "end", iid=i, text=f"Lesson {i+1}")
        self.tree.bind("<<TreeviewSelect>>", self.on_select)

        self.title_lbl = ttk.Label(self.right, font=("Segoe UI", 18))
        self.title_lbl.pack(pady=10)

        self.text_lbl = ttk.Label(self.right, wraplength=900,
                                  font=("Consolas", 15))
        self.text_lbl.pack(pady=10)

        self.entry = tk.Text(self.right, height=3,
                             font=("Consolas", 15))
        self.entry.pack()
        self.entry.bind("<Key>", self.key_press)

        self.stats_lbl = ttk.Label(self.right)
        self.stats_lbl.pack(pady=10)

    # ---------- DARK MODE ---------- #
    def toggle_dark(self):
        self.dark_mode = not self.dark_mode
        self.configure(bg="#2c2c2c" if self.dark_mode else "#ffffff")

    # ---------- VOICE ---------- #
    def toggle_voice(self):
        self.voice_mode = "Kids" if self.voice_mode == "Adult" else "Adult"
        self.voice = SpeechCoach(self.voice_mode)
        self.voice.speak(f"{self.voice_mode} mode activated")

    # ---------- LESSON ---------- #
    def compute_allowed(self, idx):
        s = set()
        for i in range(idx+1):
            s.update(LESSONS[i])
        return s

    def weakest_keys(self):
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("""
            SELECT key FROM key_stats
            WHERE user=? AND wrong > correct
        """, (self.user,))
        keys = [r[0] for r in c.fetchall()]
        conn.close()
        return keys

    def load_lesson(self, idx):
        self.lesson_index = idx
        self.allowed_keys = self.compute_allowed(idx)
        weak = self.weakest_keys()
        self.target = generate_ai_text(self.allowed_keys, weak)
        self.title_lbl.config(text=f"Lesson {idx+1}")
        self.text_lbl.config(text=self.target)
        self.reset_stats()
        self.voice.speak("Start typing")

    # ---------- INPUT ---------- #
    def key_press(self, e):
        if e.keysym == "BackSpace":
            return "break"
        if not e.char:
            return

        expected = self.target[self.typed] if self.typed < len(self.target) else ""
        self.typed += 1

        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO key_stats VALUES (?, ?, 0, 0)",
                  (self.user, e.char))

        if e.char == expected:
            c.execute("UPDATE key_stats SET correct=correct+1 WHERE user=? AND key=?",
                      (self.user, e.char))
        else:
            self.errors += 1
            self.voice.speak("Careful")

        conn.commit()
        conn.close()

        elapsed = max(time.time() - self.start_time, 1)
        wpm = (self.typed / 5) / (elapsed / 60)
        acc = (self.typed - self.errors) / self.typed * 100

        self.stats_lbl.config(text=f"WPM {int(wpm)} | Accuracy {int(acc)}%")

        self.save_session(wpm, acc)
        self.check_certificate(wpm)

    # ---------- CERTIFICATE ---------- #
    def check_certificate(self, wpm):
        for c in CERT_MILESTONES:
            if wpm >= c:
                conn = sqlite3.connect(DB_NAME)
                cur = conn.cursor()
                cur.execute("""
                INSERT OR IGNORE INTO certificates VALUES (?, ?, ?)
                """, (self.user, c, datetime.now().isoformat()))
                conn.commit()
                conn.close()
                self.voice.speak(f"Congratulations. {c} words per minute achieved.")

    # ---------- PROGRESS ---------- #
    def show_progress(self):
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        since = (datetime.now() - timedelta(days=7)).isoformat()
        c.execute("""
        SELECT date, wpm FROM sessions WHERE user=? AND date>?
        """, (self.user, since))
        data = c.fetchall()
        conn.close()

        if not data:
            messagebox.showinfo("Progress", "No data yet")
            return

        dates = [d[0][:10] for d in data]
        wpms = [d[1] for d in data]

        plt.figure()
        plt.plot(dates, wpms)
        plt.title("WPM Progress")
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.show()

    # ---------- STORAGE ---------- #
    def save_session(self, wpm, acc):
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("""
        INSERT INTO sessions VALUES (?, ?, ?, ?)
        """, (self.user, wpm, acc, datetime.now().isoformat()))
        conn.commit()
        conn.close()

    # ---------- UTIL ---------- #
    def reset_stats(self):
        self.typed = self.errors = 0
        self.start_time = time.time()

    def on_select(self, e):
        self.load_lesson(int(self.tree.selection()[0]))

    def clear(self):
        for w in self.winfo_children():
            w.destroy()

# ===================== RUN ===================== #
if __name__ == "__main__":
    init_db()
    TypingTutor().mainloop()
