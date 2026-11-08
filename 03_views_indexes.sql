-- =====================================================================
-- ResearchHub : Research Paper Management System
-- File   : 03_views_indexes.sql
-- Purpose: Creates views (to simplify common queries) and indexes
--          (to speed up searches and joins).
-- Note   : Run AFTER 01_schema.sql and 02_sample_data.sql.
-- =====================================================================

-- ---------------------------------------------------------------------
-- VIEW 1: v_paper_details
-- One row per paper with its authors (in author order) and topics.
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW v_paper_details AS
SELECT
    p.paper_id,
    p.title,
    p.publication_year,
    p.venue,
    (SELECT string_agg(a.full_name, ', ' ORDER BY pa.author_order)
       FROM paper_authors pa
       JOIN authors a ON a.author_id = pa.author_id
      WHERE pa.paper_id = p.paper_id) AS authors,
    (SELECT string_agg(t.topic_name, ', ' ORDER BY t.topic_name)
       FROM paper_topics pt
       JOIN topics t ON t.topic_id = pt.topic_id
      WHERE pt.paper_id = p.paper_id) AS topics
FROM papers p;

-- ---------------------------------------------------------------------
-- VIEW 2: v_user_library
-- Each user's saved papers with reading status.
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW v_user_library AS
SELECT
    u.user_id,
    u.full_name AS user_name,
    p.paper_id,
    p.title,
    p.publication_year,
    lp.reading_status,
    lp.added_date
FROM library_papers lp
INNER JOIN users  u ON u.user_id  = lp.user_id
INNER JOIN papers p ON p.paper_id = lp.paper_id;

-- ---------------------------------------------------------------------
-- VIEW 3: v_paper_citation_stats
-- For every paper: how many times it is cited and how many papers it cites.
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW v_paper_citation_stats AS
SELECT
    p.paper_id,
    p.title,
    p.publication_year,
    (SELECT COUNT(*) FROM citations c WHERE c.cited_paper_id  = p.paper_id) AS times_cited,
    (SELECT COUNT(*) FROM citations c WHERE c.citing_paper_id = p.paper_id) AS references_made
FROM papers p;

-- ---------------------------------------------------------------------
-- VIEW 4: v_review_summary
-- Reviews with reviewer name and paper title.
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW v_review_summary AS
SELECT
    r.review_id,
    u.full_name AS reviewer,
    p.title     AS paper_title,
    r.rating,
    r.summary,
    r.review_date
FROM literature_reviews r
INNER JOIN users  u ON u.user_id  = r.user_id
INNER JOIN papers p ON p.paper_id = r.paper_id;

-- ---------------------------------------------------------------------
-- INDEXES
-- Primary keys and UNIQUE constraints already create indexes
-- automatically, so only additional useful ones are added here.
-- ---------------------------------------------------------------------

-- Searching / sorting papers
CREATE INDEX IF NOT EXISTS idx_papers_title ON papers (title);
CREATE INDEX IF NOT EXISTS idx_papers_year  ON papers (publication_year);

-- Authors / topics lookups from the "other" side of the junction tables
CREATE INDEX IF NOT EXISTS idx_paper_authors_author ON paper_authors (author_id);
CREATE INDEX IF NOT EXISTS idx_paper_topics_topic   ON paper_topics (topic_id);

-- Library, reviews, notes
CREATE INDEX IF NOT EXISTS idx_library_paper    ON library_papers (paper_id);
CREATE INDEX IF NOT EXISTS idx_reviews_paper    ON literature_reviews (paper_id);
CREATE INDEX IF NOT EXISTS idx_notes_user_paper ON paper_notes (user_id, paper_id);

-- Citations: finding who cites a given paper
CREATE INDEX IF NOT EXISTS idx_citations_cited ON citations (cited_paper_id);

-- Check the views work.
SELECT * FROM v_paper_details ORDER BY publication_year;

-- List all indexes of the project tables.
SELECT tablename, indexname
FROM pg_indexes
WHERE schemaname = 'public'
ORDER BY tablename, indexname;
