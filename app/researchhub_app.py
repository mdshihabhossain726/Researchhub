"""
ResearchHub - Research Paper Management System (desktop app)

A small Tkinter front end for the ResearchHub PostgreSQL database.
All data lives in the database; this program only sends SQL to it.

Run:  python researchhub_app.py
"""
import os
import traceback
import tkinter as tk
from tkinter import ttk, messagebox

import psycopg2

try:  # optional: read connection settings from a .env file
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from db import Database

READING_STATUSES = ["to_read", "reading", "completed"]
ROLES = ["student", "researcher", "faculty"]
RATINGS = ["1", "2", "3", "4", "5"]

COLUMN_WIDTHS = {
    "paper_id": 70, "author_id": 70, "topic_id": 70, "review_id": 70,
    "note_id": 70, "citation_id": 80,
    "title": 360, "paper": 300, "citing_paper": 300, "cited_paper": 300,
    "abstract": 400, "summary": 380, "note_text": 380, "authors": 260,
    "topics": 200, "venue": 170, "publication_year": 110, "full_name": 200,
    "affiliation": 220, "topic_name": 200, "description": 300,
}


# ======================================================================
# Helpers
# ======================================================================
def error_text(exc):
    """Short, readable text for a database error."""
    diag = getattr(exc, "diag", None)
    message = getattr(diag, "message_primary", None) or str(exc).strip().split("\n")[0]
    detail = getattr(diag, "message_detail", None)
    return message + (f"\n{detail}" if detail else "")


def parse_id(text):
    """'6 - Some title' -> 6"""
    return int(text.split(" - ")[0])


def show_text(parent, title, text):
    win = tk.Toplevel(parent)
    win.title(title)
    win.geometry("640x460")
    box = tk.Text(win, wrap="word", padx=10, pady=10)
    box.insert("1.0", text)
    box.configure(state="disabled")
    box.pack(fill="both", expand=True)
    ttk.Button(win, text="Close", command=win.destroy).pack(pady=8)


# ======================================================================
# Reusable widgets
# ======================================================================
class DataTable(ttk.Frame):
    """A Treeview with scrollbars that can display any query result."""

    def __init__(self, parent, height=12):
        super().__init__(parent)
        self.tree = ttk.Treeview(self, show="headings", height=height, selectmode="browse")
        ysb = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        xsb = ttk.Scrollbar(self, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=ysb.set, xscrollcommand=xsb.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        ysb.grid(row=0, column=1, sticky="ns")
        xsb.grid(row=1, column=0, sticky="ew")
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

    def load(self, columns, rows):
        self.tree.delete(*self.tree.get_children())
        self.tree["columns"] = list(columns)
        for col in columns:
            self.tree.heading(col, text=col.replace("_", " ").title())
            self.tree.column(col, width=COLUMN_WIDTHS.get(col, 120), minwidth=60, stretch=False)
        for row in rows:
            values = ["" if v is None else str(v).replace("\n", " ") for v in row]
            self.tree.insert("", "end", values=values)

    def selected(self):
        """Values of the selected row as a list of strings, or None."""
        selection = self.tree.selection()
        if not selection:
            return None
        return [str(v) for v in self.tree.item(selection[0], "values")]

    def selected_id(self):
        """The first column of the selected row as an int, or None."""
        row = self.selected()
        return int(row[0]) if row else None


class FormDialog(tk.Toplevel):
    """
    A simple modal form.
    fields: list of (key, label, kind[, options])
      kind = "entry" | "password" | "text" | "combo" | "multi"
      combo: options is a list of strings
      multi: options is a list of (id, label); the result is a list of ids
    """

    def __init__(self, parent, title, fields, initial=None):
        super().__init__(parent)
        self.title(title)
        self.resizable(False, False)
        if parent.winfo_viewable():
            self.transient(parent)
        self.fields = fields
        self.result = None
        self.widgets = {}
        self.multi_options = {}
        initial = initial or {}

        body = ttk.Frame(self, padding=14)
        body.pack(fill="both", expand=True)

        for row, field in enumerate(fields):
            key, label, kind = field[0], field[1], field[2]
            options = field[3] if len(field) > 3 else None
            ttk.Label(body, text=label).grid(row=row, column=0, sticky="ne", padx=(0, 10), pady=5)

            if kind in ("entry", "password"):
                widget = ttk.Entry(body, width=52, show="*" if kind == "password" else "")
                widget.insert(0, "" if initial.get(key) is None else str(initial.get(key)))
            elif kind == "text":
                widget = tk.Text(body, width=52, height=6, wrap="word")
                widget.insert("1.0", initial.get(key) or "")
            elif kind == "combo":
                widget = ttk.Combobox(body, values=options, state="readonly", width=49)
                default = initial.get(key)
                widget.set(str(default) if default is not None else (options[0] if options else ""))
            elif kind == "multi":
                widget = tk.Listbox(body, selectmode="multiple", height=6, width=52,
                                    exportselection=False)
                self.multi_options[key] = options
                chosen = set(initial.get(key) or [])
                for index, (option_id, option_label) in enumerate(options):
                    widget.insert("end", option_label)
                    if option_id in chosen:
                        widget.selection_set(index)
            else:
                raise ValueError(f"Unknown field kind: {kind}")

            widget.grid(row=row, column=1, sticky="w", pady=5)
            self.widgets[key] = widget

        buttons = ttk.Frame(body)
        buttons.grid(row=len(fields), column=0, columnspan=2, sticky="e", pady=(12, 0))
        ttk.Button(buttons, text="Cancel", command=self.destroy).pack(side="right", padx=(6, 0))
        ttk.Button(buttons, text="OK", command=self._ok).pack(side="right")

        first = self.widgets[fields[0][0]]
        first.focus_set()
        self.update_idletasks()
        self.geometry(f"+{parent.winfo_rootx() + 60}+{parent.winfo_rooty() + 60}")
        self.wait_visibility()
        try:
            self.grab_set()
        except tk.TclError:
            pass

    def _ok(self):
        out = {}
        for field in self.fields:
            key, kind = field[0], field[2]
            widget = self.widgets[key]
            if kind in ("entry", "password"):
                out[key] = widget.get().strip()
            elif kind == "text":
                out[key] = widget.get("1.0", "end").strip()
            elif kind == "combo":
                out[key] = widget.get()
            elif kind == "multi":
                options = self.multi_options[key]
                out[key] = [options[i][0] for i in widget.curselection()]
        self.result = out
        self.destroy()


def ask_form(parent, title, fields, initial=None):
    dialog = FormDialog(parent, title, fields, initial)
    parent.wait_window(dialog)
    return dialog.result


# ======================================================================
# Tabs
# ======================================================================
class PapersTab(ttk.Frame):
    """Search, add, edit and delete papers; save to library; review; note."""

    SEARCH_SQL = """
        SELECT d.paper_id, d.title, d.publication_year, d.venue, d.authors, d.topics
          FROM v_paper_details d
         WHERE (%(kw)s = '' OR d.title ILIKE %(pat)s OR COALESCE(d.authors, '') ILIKE %(pat)s)
           AND (%(topic)s IS NULL OR EXISTS (
                  SELECT 1 FROM paper_topics pt
                   WHERE pt.paper_id = d.paper_id AND pt.topic_id = %(topic)s))
         ORDER BY d.publication_year DESC, d.title
    """

    def __init__(self, parent, app):
        super().__init__(parent, padding=8)
        self.app = app
        self.topics = []

        bar = ttk.Frame(self)
        bar.pack(fill="x", pady=(0, 6))
        ttk.Label(bar, text="Search (title / author):").pack(side="left")
        self.keyword = tk.StringVar()
        entry = ttk.Entry(bar, textvariable=self.keyword, width=30)
        entry.pack(side="left", padx=6)
        entry.bind("<Return>", lambda e: self.refresh())
        ttk.Label(bar, text="Topic:").pack(side="left", padx=(8, 0))
        self.topic_box = ttk.Combobox(bar, state="readonly", width=28)
        self.topic_box.pack(side="left", padx=6)
        ttk.Button(bar, text="Search", command=self.refresh).pack(side="left", padx=(6, 0))
        ttk.Button(bar, text="Clear", command=self.clear).pack(side="left", padx=6)

        self.table = DataTable(self)
        self.table.pack(fill="both", expand=True)

        actions = ttk.Frame(self)
        actions.pack(fill="x", pady=(6, 0))
        for text, command in [
            ("Add Paper", self.add), ("Edit", self.edit), ("Delete", self.delete),
            ("Details", self.details), ("Save to My Library", self.save_to_library),
            ("Write Review", self.review), ("Add Note", self.note),
        ]:
            ttk.Button(actions, text=text, command=command).pack(side="left", padx=(0, 6))

    # ------------------------------------------------------------------
    def load_topics(self):
        self.topics = self.app.db.rows("SELECT topic_id, topic_name FROM topics ORDER BY topic_name")
        names = ["All topics"] + [t[1] for t in self.topics]
        current = self.topic_box.get() or "All topics"
        self.topic_box["values"] = names
        self.topic_box.set(current if current in names else "All topics")

    def refresh(self):
        self.load_topics()
        keyword = self.keyword.get().strip()
        topic_id = None
        for tid, name in self.topics:
            if name == self.topic_box.get():
                topic_id = tid
        columns, rows = self.app.db.query(
            self.SEARCH_SQL, {"kw": keyword, "pat": f"%{keyword}%", "topic": topic_id})
        self.table.load(columns, rows)

    def clear(self):
        self.keyword.set("")
        self.topic_box.set("All topics")
        self.refresh()

    def _selected_paper(self):
        paper_id = self.table.selected_id()
        if paper_id is None:
            messagebox.showinfo("Select a paper", "Please select a paper in the table first.")
        return paper_id

    # ------------------------------------------------------------------
    def add(self):
        self._paper_form(None)

    def edit(self):
        paper_id = self._selected_paper()
        if paper_id is not None:
            self._paper_form(paper_id)

    def _paper_form(self, paper_id):
        db = self.app.db
        topic_options = db.rows("SELECT topic_id, topic_name FROM topics ORDER BY topic_name")
        initial = {}
        if paper_id is not None:
            title, abstract, year, venue, doi = db.rows(
                "SELECT title, abstract, publication_year, venue, doi FROM papers WHERE paper_id = %s",
                (paper_id,))[0]
            authors = [r[0] for r in db.rows(
                """SELECT a.full_name FROM paper_authors pa
                     JOIN authors a ON a.author_id = pa.author_id
                    WHERE pa.paper_id = %s ORDER BY pa.author_order""", (paper_id,))]
            topic_ids = [r[0] for r in db.rows(
                "SELECT topic_id FROM paper_topics WHERE paper_id = %s", (paper_id,))]
            initial = {"title": title, "abstract": abstract, "year": year, "venue": venue,
                       "doi": doi, "authors": ", ".join(authors), "topics": topic_ids}

        fields = [
            ("title", "Title", "entry"),
            ("year", "Publication year", "entry"),
            ("venue", "Venue (journal / conference)", "entry"),
            ("doi", "DOI (optional)", "entry"),
            ("authors", "Authors (comma-separated, in order)", "entry"),
            ("abstract", "Abstract", "text"),
            ("topics", "Topics (click to select)", "multi", topic_options),
        ]
        values = ask_form(self, "Edit Paper" if paper_id is not None else "Add Paper", fields, initial)
        if not values:
            return
        if not values["title"]:
            messagebox.showwarning("Missing title", "Title is required.")
            return
        try:
            year = int(values["year"])
        except ValueError:
            messagebox.showwarning("Invalid year", "Publication year must be a number.")
            return
        if not 1900 <= year <= 2100:
            messagebox.showwarning("Invalid year", "Publication year must be between 1900 and 2100.")
            return
        names = list(dict.fromkeys(n.strip() for n in values["authors"].split(",") if n.strip()))

        ok, _ = self.app.attempt(lambda: db.save_paper(
            paper_id, values["title"], values["abstract"] or None, year,
            values["venue"] or None, values["doi"] or None, names, values["topics"]))
        if ok:
            self.app.refresh_all()

    def delete(self):
        paper_id = self._selected_paper()
        if paper_id is None:
            return
        title = self.table.selected()[1]
        if not messagebox.askyesno(
                "Delete paper",
                f"Delete this paper?\n\n{title}\n\nIts library entries, reviews, notes and "
                "citation links will also be deleted."):
            return
        ok, _ = self.app.attempt(
            lambda: self.app.db.execute("DELETE FROM papers WHERE paper_id = %s", (paper_id,)))
        if ok:
            self.app.refresh_all()

    def details(self):
        paper_id = self._selected_paper()
        if paper_id is None:
            return
        row = self.app.db.rows(
            """SELECT p.title, p.abstract, p.publication_year, p.venue, p.doi,
                      d.authors, d.topics,
                      fn_citation_count(p.paper_id), fn_average_rating(p.paper_id)
                 FROM papers p
                 JOIN v_paper_details d ON d.paper_id = p.paper_id
                WHERE p.paper_id = %s""", (paper_id,))[0]
        rating = row[8] if row[8] is not None else "not reviewed yet"
        text = (f"Title: {row[0]}\nAuthors: {row[5] or '-'}\nYear: {row[2]}\n"
                f"Venue: {row[3] or '-'}\nDOI: {row[4] or '-'}\nTopics: {row[6] or '-'}\n"
                f"Times cited: {row[7]}\nAverage rating: {rating}\n\nAbstract:\n{row[1] or '-'}")
        show_text(self, "Paper Details", text)

    def save_to_library(self):
        paper_id = self._selected_paper()
        if paper_id is not None:
            self.app.add_to_library(paper_id)

    def review(self):
        paper_id = self._selected_paper()
        if paper_id is not None:
            self.app.review_dialog(paper_id)

    def note(self):
        paper_id = self._selected_paper()
        if paper_id is not None:
            self.app.note_dialog(paper_id=paper_id)


class LibraryTab(ttk.Frame):
    """The current user's saved papers."""

    def __init__(self, parent, app):
        super().__init__(parent, padding=8)
        self.app = app
        self.summary = tk.StringVar()
        ttk.Label(self, textvariable=self.summary, font=("TkDefaultFont", 10, "bold")).pack(
            anchor="w", pady=(0, 6))
        self.table = DataTable(self)
        self.table.pack(fill="both", expand=True)
        actions = ttk.Frame(self)
        actions.pack(fill="x", pady=(6, 0))
        for text, command in [
            ("Change Status", self.change_status), ("Remove from Library", self.remove),
            ("Write / Edit Review", self.review), ("Add Note", self.note),
        ]:
            ttk.Button(actions, text=text, command=command).pack(side="left", padx=(0, 6))

    def refresh(self):
        user_id = self.app.current_user_id
        if user_id is None:
            self.table.load([], [])
            self.summary.set("")
            return
        columns, rows = self.app.db.query(
            """SELECT paper_id, title, publication_year, reading_status, added_date
                 FROM v_user_library
                WHERE user_id = %s
                ORDER BY added_date, title""", (user_id,))
        self.table.load(columns, rows)
        total, to_read, reading, done = self.app.db.rows(
            """SELECT fn_user_library_count(%s),
                      fn_user_library_count(%s, 'to_read'),
                      fn_user_library_count(%s, 'reading'),
                      fn_user_library_count(%s, 'completed')""", (user_id,) * 4)[0]
        self.summary.set(f"Saved: {total}    To read: {to_read}    Reading: {reading}    Completed: {done}")

    def _selected_paper(self):
        paper_id = self.table.selected_id()
        if paper_id is None:
            messagebox.showinfo("Select a paper", "Please select a paper in the table first.")
        return paper_id

    def change_status(self):
        paper_id = self._selected_paper()
        if paper_id is None:
            return
        current = self.table.selected()[3]
        self.app.add_to_library(paper_id, current_status=current)

    def remove(self):
        paper_id = self._selected_paper()
        if paper_id is None:
            return
        if not messagebox.askyesno("Remove paper", "Remove this paper from your library?"):
            return
        ok, _ = self.app.attempt(lambda: self.app.db.execute(
            "DELETE FROM library_papers WHERE user_id = %s AND paper_id = %s",
            (self.app.current_user_id, paper_id)))
        if ok:
            self.app.refresh_all()

    def review(self):
        paper_id = self._selected_paper()
        if paper_id is not None:
            self.app.review_dialog(paper_id)

    def note(self):
        paper_id = self._selected_paper()
        if paper_id is not None:
            self.app.note_dialog(paper_id=paper_id)


class ReviewsNotesTab(ttk.Frame):
    """The current user's literature reviews and personal notes."""

    def __init__(self, parent, app):
        super().__init__(parent, padding=8)
        self.app = app

        reviews = ttk.LabelFrame(self, text="My Literature Reviews", padding=6)
        reviews.pack(fill="both", expand=True)
        self.review_table = DataTable(reviews, height=6)
        self.review_table.pack(fill="both", expand=True)
        bar = ttk.Frame(reviews)
        bar.pack(fill="x", pady=(6, 0))
        ttk.Button(bar, text="New Review", command=lambda: app.review_dialog()).pack(side="left", padx=(0, 6))
        ttk.Button(bar, text="Edit", command=self.edit_review).pack(side="left", padx=(0, 6))
        ttk.Button(bar, text="Delete", command=self.delete_review).pack(side="left")

        notes = ttk.LabelFrame(self, text="My Notes", padding=6)
        notes.pack(fill="both", expand=True, pady=(8, 0))
        self.note_table = DataTable(notes, height=6)
        self.note_table.pack(fill="both", expand=True)
        bar = ttk.Frame(notes)
        bar.pack(fill="x", pady=(6, 0))
        ttk.Button(bar, text="New Note", command=lambda: app.note_dialog()).pack(side="left", padx=(0, 6))
        ttk.Button(bar, text="Edit", command=self.edit_note).pack(side="left", padx=(0, 6))
        ttk.Button(bar, text="Delete", command=self.delete_note).pack(side="left")

    def refresh(self):
        user_id = self.app.current_user_id
        if user_id is None:
            self.review_table.load([], [])
            self.note_table.load([], [])
            return
        db = self.app.db
        self.review_table.load(*db.query(
            """SELECT r.review_id, p.title AS paper, r.rating, r.summary, r.review_date
                 FROM literature_reviews r
                 JOIN papers p ON p.paper_id = r.paper_id
                WHERE r.user_id = %s
                ORDER BY r.review_date DESC, r.review_id DESC""", (user_id,)))
        self.note_table.load(*db.query(
            """SELECT n.note_id, p.title AS paper, n.note_text, n.created_at, n.updated_at
                 FROM paper_notes n
                 JOIN papers p ON p.paper_id = n.paper_id
                WHERE n.user_id = %s
                ORDER BY n.updated_at DESC, n.note_id DESC""", (user_id,)))

    # Reviews
    def edit_review(self):
        review_id = self.review_table.selected_id()
        if review_id is None:
            messagebox.showinfo("Select a review", "Please select a review first.")
            return
        paper_id = self.app.db.rows(
            "SELECT paper_id FROM literature_reviews WHERE review_id = %s", (review_id,))[0][0]
        self.app.review_dialog(paper_id)

    def delete_review(self):
        review_id = self.review_table.selected_id()
        if review_id is None:
            messagebox.showinfo("Select a review", "Please select a review first.")
            return
        if not messagebox.askyesno("Delete review", "Delete this review?"):
            return
        ok, _ = self.app.attempt(lambda: self.app.db.execute(
            "DELETE FROM literature_reviews WHERE review_id = %s", (review_id,)))
        if ok:
            self.app.refresh_all()

    # Notes
    def edit_note(self):
        note_id = self.note_table.selected_id()
        if note_id is None:
            messagebox.showinfo("Select a note", "Please select a note first.")
            return
        text = self.app.db.rows("SELECT note_text FROM paper_notes WHERE note_id = %s", (note_id,))[0][0]
        self.app.note_dialog(note_id=note_id, text=text)

    def delete_note(self):
        note_id = self.note_table.selected_id()
        if note_id is None:
            messagebox.showinfo("Select a note", "Please select a note first.")
            return
        if not messagebox.askyesno("Delete note", "Delete this note?"):
            return
        ok, _ = self.app.attempt(lambda: self.app.db.execute(
            "DELETE FROM paper_notes WHERE note_id = %s", (note_id,)))
        if ok:
            self.app.refresh_all()


class CitationsTab(ttk.Frame):
    """Citation links between papers and per-paper citation statistics."""

    def __init__(self, parent, app):
        super().__init__(parent, padding=8)
        self.app = app

        top = ttk.LabelFrame(self, text="Who cites whom", padding=6)
        top.pack(fill="both", expand=True)
        self.table = DataTable(top, height=7)
        self.table.pack(fill="both", expand=True)
        bar = ttk.Frame(top)
        bar.pack(fill="x", pady=(6, 0))
        ttk.Button(bar, text="Add Citation", command=self.add).pack(side="left", padx=(0, 6))
        ttk.Button(bar, text="Delete Citation", command=self.delete).pack(side="left")

        bottom = ttk.LabelFrame(self, text="Citation statistics per paper", padding=6)
        bottom.pack(fill="both", expand=True, pady=(8, 0))
        self.stats = DataTable(bottom, height=7)
        self.stats.pack(fill="both", expand=True)

    def refresh(self):
        db = self.app.db
        self.table.load(*db.query(
            """SELECT c.citation_id, citing.title AS citing_paper, cited.title AS cited_paper
                 FROM citations c
                 JOIN papers citing ON citing.paper_id = c.citing_paper_id
                 JOIN papers cited  ON cited.paper_id  = c.cited_paper_id
                ORDER BY c.citation_id"""))
        self.stats.load(*db.query(
            """SELECT paper_id, title, publication_year, times_cited, references_made
                 FROM v_paper_citation_stats
                ORDER BY times_cited DESC, title"""))

    def add(self):
        options = self.app.paper_options()
        if len(options) < 2:
            messagebox.showinfo("Not enough papers", "Add at least two papers first.")
            return
        values = ask_form(self, "Add Citation", [
            ("citing", "Citing paper (the one that cites)", "combo", options),
            ("cited", "Cited paper (the one being cited)", "combo", options),
        ])
        if not values:
            return
        citing, cited = parse_id(values["citing"]), parse_id(values["cited"])
        if citing == cited:
            messagebox.showwarning("Invalid citation", "A paper cannot cite itself.")
            return
        ok, _ = self.app.attempt(lambda: self.app.db.execute(
            "INSERT INTO citations (citing_paper_id, cited_paper_id) VALUES (%s, %s)",
            (citing, cited)))
        if ok:
            self.app.refresh_all()

    def delete(self):
        citation_id = self.table.selected_id()
        if citation_id is None:
            messagebox.showinfo("Select a citation", "Please select a citation first.")
            return
        if not messagebox.askyesno("Delete citation", "Delete this citation link?"):
            return
        ok, _ = self.app.attempt(lambda: self.app.db.execute(
            "DELETE FROM citations WHERE citation_id = %s", (citation_id,)))
        if ok:
            self.app.refresh_all()


class AuthorsTopicsTab(ttk.Frame):
    """Manage authors and research topics."""

    def __init__(self, parent, app):
        super().__init__(parent, padding=8)
        self.app = app
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        left = ttk.LabelFrame(self, text="Authors", padding=6)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        self.authors = DataTable(left)
        self.authors.pack(fill="both", expand=True)
        bar = ttk.Frame(left)
        bar.pack(fill="x", pady=(6, 0))
        ttk.Button(bar, text="Add", command=self.add_author).pack(side="left", padx=(0, 6))
        ttk.Button(bar, text="Edit", command=self.edit_author).pack(side="left", padx=(0, 6))
        ttk.Button(bar, text="Delete", command=self.delete_author).pack(side="left")

        right = ttk.LabelFrame(self, text="Topics", padding=6)
        right.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        self.topics = DataTable(right)
        self.topics.pack(fill="both", expand=True)
        bar = ttk.Frame(right)
        bar.pack(fill="x", pady=(6, 0))
        ttk.Button(bar, text="Add", command=self.add_topic).pack(side="left", padx=(0, 6))
        ttk.Button(bar, text="Edit", command=self.edit_topic).pack(side="left", padx=(0, 6))
        ttk.Button(bar, text="Delete", command=self.delete_topic).pack(side="left")

    def refresh(self):
        db = self.app.db
        self.authors.load(*db.query(
            """SELECT a.author_id, a.full_name, a.affiliation, COUNT(pa.paper_id) AS papers
                 FROM authors a
                 LEFT JOIN paper_authors pa ON pa.author_id = a.author_id
                GROUP BY a.author_id, a.full_name, a.affiliation
                ORDER BY a.full_name"""))
        self.topics.load(*db.query(
            """SELECT t.topic_id, t.topic_name, t.description, COUNT(pt.paper_id) AS papers
                 FROM topics t
                 LEFT JOIN paper_topics pt ON pt.topic_id = t.topic_id
                GROUP BY t.topic_id, t.topic_name, t.description
                ORDER BY t.topic_name"""))

    # Authors
    def _author_form(self, author_id):
        initial = {}
        if author_id is not None:
            row = self.authors.selected()
            initial = {"name": row[1], "affiliation": row[2]}
        values = ask_form(self, "Edit Author" if author_id is not None else "Add Author", [
            ("name", "Full name", "entry"),
            ("affiliation", "Affiliation", "entry"),
        ], initial)
        if not values:
            return
        if not values["name"]:
            messagebox.showwarning("Missing name", "Author name is required.")
            return
        if author_id is None:
            sql, params = ("INSERT INTO authors (full_name, affiliation) VALUES (%s, %s)",
                           (values["name"], values["affiliation"] or None))
        else:
            sql, params = ("UPDATE authors SET full_name = %s, affiliation = %s WHERE author_id = %s",
                           (values["name"], values["affiliation"] or None, author_id))
        ok, _ = self.app.attempt(lambda: self.app.db.execute(sql, params))
        if ok:
            self.app.refresh_all()

    def add_author(self):
        self._author_form(None)

    def edit_author(self):
        author_id = self.authors.selected_id()
        if author_id is None:
            messagebox.showinfo("Select an author", "Please select an author first.")
            return
        self._author_form(author_id)

    def delete_author(self):
        author_id = self.authors.selected_id()
        if author_id is None:
            messagebox.showinfo("Select an author", "Please select an author first.")
            return
        name = self.authors.selected()[1]
        if not messagebox.askyesno(
                "Delete author",
                f"Delete author '{name}'?\nThe author will be removed from all papers "
                "(the papers themselves stay)."):
            return
        ok, _ = self.app.attempt(lambda: self.app.db.execute(
            "DELETE FROM authors WHERE author_id = %s", (author_id,)))
        if ok:
            self.app.refresh_all()

    # Topics
    def _topic_form(self, topic_id):
        initial = {}
        if topic_id is not None:
            row = self.topics.selected()
            initial = {"name": row[1], "description": row[2]}
        values = ask_form(self, "Edit Topic" if topic_id is not None else "Add Topic", [
            ("name", "Topic name", "entry"),
            ("description", "Description", "text"),
        ], initial)
        if not values:
            return
        if not values["name"]:
            messagebox.showwarning("Missing name", "Topic name is required.")
            return
        if topic_id is None:
            sql, params = ("INSERT INTO topics (topic_name, description) VALUES (%s, %s)",
                           (values["name"], values["description"] or None))
        else:
            sql, params = ("UPDATE topics SET topic_name = %s, description = %s WHERE topic_id = %s",
                           (values["name"], values["description"] or None, topic_id))
        ok, _ = self.app.attempt(lambda: self.app.db.execute(sql, params))
        if ok:
            self.app.refresh_all()

    def add_topic(self):
        self._topic_form(None)

    def edit_topic(self):
        topic_id = self.topics.selected_id()
        if topic_id is None:
            messagebox.showinfo("Select a topic", "Please select a topic first.")
            return
        self._topic_form(topic_id)

    def delete_topic(self):
        topic_id = self.topics.selected_id()
        if topic_id is None:
            messagebox.showinfo("Select a topic", "Please select a topic first.")
            return
        name = self.topics.selected()[1]
        if not messagebox.askyesno(
                "Delete topic",
                f"Delete topic '{name}'?\nPapers keep existing, but lose this topic."):
            return
        ok, _ = self.app.attempt(lambda: self.app.db.execute(
            "DELETE FROM topics WHERE topic_id = %s", (topic_id,)))
        if ok:
            self.app.refresh_all()


class ReportsTab(ttk.Frame):
    """Ready-made reports (GROUP BY, HAVING, joins and subqueries)."""

    REPORTS = {
        "Papers per topic": """
            SELECT t.topic_name, COUNT(pt.paper_id) AS paper_count
              FROM topics t
              LEFT JOIN paper_topics pt ON pt.topic_id = t.topic_id
             GROUP BY t.topic_name
             ORDER BY paper_count DESC, t.topic_name""",
        "Topics with 2 or more papers": """
            SELECT t.topic_name, COUNT(*) AS paper_count
              FROM topics t
              JOIN paper_topics pt ON pt.topic_id = t.topic_id
             GROUP BY t.topic_name
            HAVING COUNT(*) >= 2
             ORDER BY paper_count DESC""",
        "Papers per publication year": """
            SELECT publication_year, COUNT(*) AS papers_published
              FROM papers
             GROUP BY publication_year
             ORDER BY publication_year""",
        "Most cited papers": """
            SELECT title, publication_year, times_cited, references_made
              FROM v_paper_citation_stats
             ORDER BY times_cited DESC, title""",
        "Papers never cited": """
            SELECT p.title, p.publication_year
              FROM papers p
              LEFT JOIN citations c ON c.cited_paper_id = p.paper_id
             WHERE c.citation_id IS NULL
             ORDER BY p.publication_year""",
        "Average rating per paper": """
            SELECT p.title, COUNT(r.review_id) AS review_count,
                   ROUND(AVG(r.rating), 2) AS avg_rating
              FROM papers p
              JOIN literature_reviews r ON r.paper_id = p.paper_id
             GROUP BY p.title
             ORDER BY avg_rating DESC, p.title""",
        "Papers not saved by any user": """
            SELECT title, publication_year
              FROM papers
             WHERE paper_id NOT IN (SELECT paper_id FROM library_papers)
             ORDER BY title""",
        "Authors with more than one paper": """
            SELECT a.full_name, COUNT(pa.paper_id) AS paper_count
              FROM authors a
              JOIN paper_authors pa ON pa.author_id = a.author_id
             GROUP BY a.author_id, a.full_name
            HAVING COUNT(pa.paper_id) > 1
             ORDER BY paper_count DESC, a.full_name""",
        "Reading status summary": """
            SELECT reading_status, COUNT(*) AS total
              FROM library_papers
             GROUP BY reading_status
             ORDER BY total DESC""",
    }

    def __init__(self, parent, app):
        super().__init__(parent, padding=8)
        self.app = app
        bar = ttk.Frame(self)
        bar.pack(fill="x", pady=(0, 6))
        ttk.Label(bar, text="Report:").pack(side="left")
        self.box = ttk.Combobox(bar, state="readonly", width=40, values=list(self.REPORTS))
        self.box.pack(side="left", padx=6)
        self.box.current(0)
        self.box.bind("<<ComboboxSelected>>", lambda e: self.refresh())
        ttk.Button(bar, text="Run", command=self.refresh).pack(side="left")
        self.table = DataTable(self)
        self.table.pack(fill="both", expand=True)

    def refresh(self):
        self.table.load(*self.app.db.query(self.REPORTS[self.box.get()]))


# ======================================================================
# Main application
# ======================================================================
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("ResearchHub - Research Paper Management System")
        self.geometry("1150x680")
        self.minsize(950, 520)
        self.withdraw()
        try:
            ttk.Style().theme_use("clam")
        except tk.TclError:
            pass
        self.db = Database()
        self.users = []
        self.tabs = []

    # ------------------------------------------------------------------
    # Startup
    # ------------------------------------------------------------------
    def connect_dialog(self):
        fields = [
            ("host", "Host", "entry"),
            ("port", "Port", "entry"),
            ("dbname", "Database", "entry"),
            ("user", "User", "entry"),
            ("password", "Password", "password"),
        ]
        initial = {
            "host": os.environ.get("PGHOST", "localhost"),
            "port": os.environ.get("PGPORT", "5432"),
            "dbname": os.environ.get("PGDATABASE", "researchhub"),
            "user": os.environ.get("PGUSER", "postgres"),
            "password": os.environ.get("PGPASSWORD", ""),
        }
        # If a password is set (for example in .env), try to connect directly.
        if initial["password"]:
            try:
                self.db.connect(**initial)
                return True
            except (psycopg2.Error, ValueError):
                pass  # fall back to the connection window below
        while True:
            values = ask_form(self, "Connect to PostgreSQL", fields, initial)
            if values is None:
                return False
            try:
                self.db.connect(**values)
                return True
            except (psycopg2.Error, ValueError) as exc:
                initial = values
                messagebox.showerror(
                    "Connection failed",
                    f"{error_text(exc)}\n\nCheck that PostgreSQL is running, the connection "
                    "details are correct, and SQL scripts 01 to 04 have been run in this database.")

    def build_ui(self):
        header = ttk.Frame(self, padding=(12, 8))
        header.pack(fill="x")
        ttk.Label(header, text="ResearchHub", font=("TkDefaultFont", 16, "bold")).pack(side="left")
        ttk.Button(header, text="New User", command=self.new_user).pack(side="right")
        self.user_box = ttk.Combobox(header, state="readonly", width=42)
        self.user_box.pack(side="right", padx=8)
        ttk.Label(header, text="Current user:").pack(side="right")
        self.user_box.bind("<<ComboboxSelected>>", lambda e: self.refresh_all())

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        for title, tab_class in [
            ("Papers", PapersTab),
            ("My Library", LibraryTab),
            ("Reviews & Notes", ReviewsNotesTab),
            ("Citations", CitationsTab),
            ("Authors & Topics", AuthorsTopicsTab),
            ("Reports", ReportsTab),
        ]:
            tab = tab_class(self.notebook, self)
            self.notebook.add(tab, text=title)
            self.tabs.append(tab)

        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.load_users()
        if not self.users:
            messagebox.showinfo("Welcome", "There are no users yet. Please create one to start.")
            self.new_user()

    def on_close(self):
        self.db.close()
        self.destroy()

    # ------------------------------------------------------------------
    # Users
    # ------------------------------------------------------------------
    @property
    def current_user_id(self):
        text = self.user_box.get()
        return parse_id(text) if text else None

    def load_users(self, select_id=None):
        previous = select_id if select_id is not None else self.current_user_id
        self.users = self.db.rows("SELECT user_id, full_name, role FROM users ORDER BY user_id")
        labels = [f"{u[0]} - {u[1]} ({u[2]})" for u in self.users]
        self.user_box["values"] = labels
        if labels:
            index = 0
            for i, user in enumerate(self.users):
                if user[0] == previous:
                    index = i
            self.user_box.current(index)
        else:
            self.user_box.set("")
        self.refresh_all()

    def new_user(self):
        values = ask_form(self, "New User", [
            ("full_name", "Full name", "entry"),
            ("email", "Email", "entry"),
            ("role", "Role", "combo", ROLES),
        ], {"role": "student"})
        if not values:
            return
        if not values["full_name"] or not values["email"]:
            messagebox.showwarning("Missing data", "Full name and email are required.")
            return
        ok, rows = self.attempt(lambda: self.db.rows(
            "INSERT INTO users (full_name, email, role) VALUES (%s, %s, %s) RETURNING user_id",
            (values["full_name"], values["email"], values["role"])))
        if ok:
            self.load_users(select_id=rows[0][0])

    def require_user(self):
        if self.current_user_id is None:
            messagebox.showinfo("No user", "Please create or select a user first.")
            return False
        return True

    # ------------------------------------------------------------------
    # Shared helpers and dialogs
    # ------------------------------------------------------------------
    def attempt(self, func):
        """Run a database action; show a friendly message if it fails."""
        try:
            return True, func()
        except psycopg2.Error as exc:
            messagebox.showerror("Database error", error_text(exc))
            return False, None

    def refresh_all(self):
        for tab in self.tabs:
            tab.refresh()

    def paper_options(self):
        return [f"{r[0]} - {r[1]}" for r in
                self.db.rows("SELECT paper_id, title FROM papers ORDER BY title")]

    def add_to_library(self, paper_id, current_status="to_read"):
        if not self.require_user():
            return
        values = ask_form(self, "Reading status", [
            ("status", "Reading status", "combo", READING_STATUSES),
        ], {"status": current_status})
        if not values:
            return
        ok, _ = self.attempt(lambda: self.db.execute(
            "CALL sp_add_to_library(%s, %s, %s)",
            (self.current_user_id, paper_id, values["status"])))
        if ok:
            self.refresh_all()

    def review_dialog(self, paper_id=None):
        if not self.require_user():
            return
        user_id = self.current_user_id
        fields, initial = [], {}
        if paper_id is None:
            options = self.paper_options()
            if not options:
                messagebox.showinfo("No papers", "Add a paper first.")
                return
            fields.append(("paper", "Paper", "combo", options))
        else:
            existing = self.db.rows(
                "SELECT summary, rating FROM literature_reviews WHERE user_id = %s AND paper_id = %s",
                (user_id, paper_id))
            if existing:
                initial = {"summary": existing[0][0], "rating": existing[0][1]}
        fields += [("rating", "Rating (1-5)", "combo", RATINGS),
                   ("summary", "Review", "text")]
        values = ask_form(self, "Literature Review", fields, initial)
        if not values:
            return
        if not values["summary"]:
            messagebox.showwarning("Missing review", "Please write a short review.")
            return
        target = paper_id if paper_id is not None else parse_id(values["paper"])
        ok, _ = self.attempt(lambda: self.db.execute(
            """INSERT INTO literature_reviews (user_id, paper_id, summary, rating)
               VALUES (%s, %s, %s, %s)
               ON CONFLICT (user_id, paper_id)
               DO UPDATE SET summary = EXCLUDED.summary,
                             rating = EXCLUDED.rating,
                             review_date = CURRENT_DATE""",
            (user_id, target, values["summary"], int(values["rating"]))))
        if ok:
            self.refresh_all()

    def note_dialog(self, paper_id=None, note_id=None, text=""):
        if not self.require_user():
            return
        fields = []
        if paper_id is None and note_id is None:
            options = self.paper_options()
            if not options:
                messagebox.showinfo("No papers", "Add a paper first.")
                return
            fields.append(("paper", "Paper", "combo", options))
        fields.append(("note", "Note", "text"))
        values = ask_form(self, "Edit Note" if note_id is not None else "New Note",
                          fields, {"note": text})
        if not values:
            return
        if not values["note"]:
            messagebox.showwarning("Empty note", "Please write something in the note.")
            return
        if note_id is not None:
            action = lambda: self.db.execute(
                "UPDATE paper_notes SET note_text = %s WHERE note_id = %s",
                (values["note"], note_id))
        else:
            target = paper_id if paper_id is not None else parse_id(values["paper"])
            action = lambda: self.db.execute(
                "INSERT INTO paper_notes (user_id, paper_id, note_text) VALUES (%s, %s, %s)",
                (self.current_user_id, target, values["note"]))
        ok, _ = self.attempt(action)
        if ok:
            self.refresh_all()

    # ------------------------------------------------------------------
    # Unhandled errors inside Tk callbacks
    # ------------------------------------------------------------------
    def report_callback_exception(self, exc_type, exc_value, exc_tb):
        if isinstance(exc_value, psycopg2.Error):
            messagebox.showerror("Database error", error_text(exc_value))
        else:
            traceback.print_exception(exc_type, exc_value, exc_tb)
            messagebox.showerror("Unexpected error", str(exc_value))


def main():
    app = App()
    if app.connect_dialog():
        app.build_ui()
        app.deiconify()
        app.mainloop()
    else:
        app.destroy()


if __name__ == "__main__":
    main()
