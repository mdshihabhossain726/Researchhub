"""
ResearchHub desktop app - database access layer.

A thin wrapper around psycopg2. Every method commits on success and rolls
back on failure, so the connection never stays in a broken transaction.
"""
import psycopg2


class Database:
    def __init__(self):
        self.conn = None

    # ------------------------------------------------------------------
    # Connection
    # ------------------------------------------------------------------
    def connect(self, host, port, dbname, user, password):
        self.conn = psycopg2.connect(
            host=host,
            port=int(port),
            dbname=dbname,
            user=user,
            password=password,
            connect_timeout=5,
        )
        try:
            # Make sure the ResearchHub schema, views and functions exist.
            self.query("SELECT 1 FROM papers LIMIT 1")
            self.query("SELECT 1 FROM v_paper_details LIMIT 1")
            self.query("SELECT fn_citation_count(0)")
        except Exception:
            self.close()
            raise

    def close(self):
        if self.conn is not None:
            try:
                self.conn.close()
            finally:
                self.conn = None

    # ------------------------------------------------------------------
    # Generic helpers
    # ------------------------------------------------------------------
    def query(self, sql, params=None):
        """Run a SELECT (or INSERT ... RETURNING). Returns (columns, rows)."""
        try:
            with self.conn.cursor() as cur:
                cur.execute(sql, params)
                if cur.description:
                    columns = [d[0] for d in cur.description]
                    rows = cur.fetchall()
                else:
                    columns, rows = [], []
            self.conn.commit()
            return columns, rows
        except Exception:
            self.conn.rollback()
            raise

    def rows(self, sql, params=None):
        """Run a query and return only the rows."""
        return self.query(sql, params)[1]

    def execute(self, sql, params=None):
        """Run INSERT / UPDATE / DELETE / CALL. Returns the affected row count."""
        try:
            with self.conn.cursor() as cur:
                cur.execute(sql, params)
                count = cur.rowcount
            self.conn.commit()
            return count
        except Exception:
            self.conn.rollback()
            raise

    def transaction(self, work):
        """Run work(cursor) as one transaction (all or nothing)."""
        try:
            with self.conn.cursor() as cur:
                result = work(cur)
            self.conn.commit()
            return result
        except Exception:
            self.conn.rollback()
            raise

    # ------------------------------------------------------------------
    # Paper + authors + topics saved together in one transaction
    # ------------------------------------------------------------------
    def save_paper(self, paper_id, title, abstract, year, venue, doi,
                   author_names, topic_ids):
        """
        Insert a new paper (paper_id is None) or update an existing one.
        Authors are matched by name (case-insensitive); unknown authors are
        created. The paper's author and topic links are replaced with the
        lists given.
        """
        def work(cur):
            pid = paper_id
            if pid is None:
                cur.execute(
                    """INSERT INTO papers (title, abstract, publication_year, venue, doi)
                       VALUES (%s, %s, %s, %s, %s) RETURNING paper_id""",
                    (title, abstract, year, venue, doi),
                )
                pid = cur.fetchone()[0]
            else:
                cur.execute(
                    """UPDATE papers
                          SET title = %s, abstract = %s, publication_year = %s,
                              venue = %s, doi = %s
                        WHERE paper_id = %s""",
                    (title, abstract, year, venue, doi, pid),
                )
                cur.execute("DELETE FROM paper_authors WHERE paper_id = %s", (pid,))
                cur.execute("DELETE FROM paper_topics  WHERE paper_id = %s", (pid,))

            for order, name in enumerate(author_names, start=1):
                cur.execute(
                    """SELECT author_id FROM authors
                        WHERE LOWER(full_name) = LOWER(%s)
                        ORDER BY author_id LIMIT 1""",
                    (name,),
                )
                found = cur.fetchone()
                if found:
                    author_id = found[0]
                else:
                    cur.execute(
                        "INSERT INTO authors (full_name) VALUES (%s) RETURNING author_id",
                        (name,),
                    )
                    author_id = cur.fetchone()[0]
                cur.execute(
                    """INSERT INTO paper_authors (paper_id, author_id, author_order)
                       VALUES (%s, %s, %s) ON CONFLICT DO NOTHING""",
                    (pid, author_id, order),
                )

            for topic_id in topic_ids:
                cur.execute(
                    """INSERT INTO paper_topics (paper_id, topic_id)
                       VALUES (%s, %s) ON CONFLICT DO NOTHING""",
                    (pid, topic_id),
                )
            return pid

        return self.transaction(work)
