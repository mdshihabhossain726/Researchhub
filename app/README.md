# ResearchHub Desktop App

A small desktop interface (Python + Tkinter) for the ResearchHub PostgreSQL database.
The app stores nothing itself: every action runs SQL against the database, so it
shows the tables, views, functions, procedure and triggers working together.

## Setup

1. Create the database and run SQL scripts `01` to `04` first (see `../README.md`).
   Script `02` (sample data) is optional but recommended.
2. Install Python 3.8 or later. Tkinter comes with the Windows and macOS installers.
   On Linux: `sudo apt install python3-tk`.
3. Install the PostgreSQL driver:

   ```
   pip install -r requirements.txt
   ```

4. Start the app from this folder:

   ```
   python researchhub_app.py
   ```

5. In the connection window enter your PostgreSQL host, port, database (`researchhub`),
   user and password (the same ones you use in pgAdmin 4).

## Keeping the password out of GitHub (.env)

1. In the `app` folder, copy `.env.example` and name the copy `.env`.
2. Open `.env` and put your own PostgreSQL password after `PGPASSWORD=`.
3. Run `pip install -r requirements.txt` again (it now includes `python-dotenv`).
4. Start the app. If the `.env` values are correct it connects directly, without the connection window. If they are wrong, the connection window opens as usual.

The `.gitignore` file in the project root already excludes `.env`, so your password is not uploaded when you push the repository. Only `.env.example` (with a fake password) is shared.

If a real password was ever committed, changing the password is the safe fix, because deleting the file later does not remove it from Git history.

## What each tab does

| Tab | Features | Database objects used |
|---|---|---|
| Papers | Search by title/author/topic, add, edit, delete, details, save to library, review, note | `papers`, `authors`, `topics`, junction tables, `v_paper_details`, `fn_citation_count`, `fn_average_rating` |
| My Library | Saved papers of the current user, change reading status, remove | `library_papers`, `v_user_library`, `sp_add_to_library`, `fn_user_library_count` |
| Reviews & Notes | Create, edit and delete reviews and notes | `literature_reviews`, `paper_notes`, trigger `trg_paper_notes_updated_at` |
| Citations | Add and delete citations, citation statistics | `citations`, `v_paper_citation_stats`, trigger `trg_citations_validate` |
| Authors & Topics | Manage authors and topics | `authors`, `topics` |
| Reports | Nine ready-made reports | GROUP BY, HAVING, LEFT JOIN, subqueries |
| (header) | Choose the current user, create a new user | `users` |

## Things worth showing in the demo

- Add a citation where an older paper cites a newer one: the **trigger** rejects it and the message appears in a dialog.
- Add a paper with a year of 3000 or a duplicate email for a user: the **CHECK / UNIQUE constraints** reject it.
- Edit a note, then look at the *Updated At* column: the **trigger** refreshed it.
- Change a paper's reading status in *My Library*: it calls the **procedure** `sp_add_to_library`.

## Optional: make a standalone .exe (Windows)

```
pip install pyinstaller
pyinstaller --onefile --windowed researchhub_app.py
```

The executable appears in the `dist` folder.

## Files

| File | Purpose |
|---|---|
| `researchhub_app.py` | The Tkinter user interface |
| `db.py` | Database access layer (psycopg2) |
| `requirements.txt` | Python dependency |
