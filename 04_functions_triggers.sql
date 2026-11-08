-- =====================================================================
-- ResearchHub : Research Paper Management System
-- File   : 04_functions_triggers.sql
-- Purpose: Basic PL/pgSQL functions, one procedure and two triggers.
-- Note   : Run AFTER 01_schema.sql and 02_sample_data.sql.
-- =====================================================================

-- ---------------------------------------------------------------------
-- FUNCTION 1: fn_citation_count(paper_id)
-- Returns how many times a paper has been cited.
-- ---------------------------------------------------------------------
CREATE OR REPLACE FUNCTION fn_citation_count(p_paper_id INT)
RETURNS INT
LANGUAGE plpgsql
AS $$
DECLARE
    v_count INT;
BEGIN
    SELECT COUNT(*)
      INTO v_count
      FROM citations
     WHERE cited_paper_id = p_paper_id;

    RETURN v_count;
END;
$$;

-- ---------------------------------------------------------------------
-- FUNCTION 2: fn_user_library_count(user_id, status)
-- Returns the number of papers in a user's library.
-- If p_status is NULL, all saved papers are counted.
-- ---------------------------------------------------------------------
CREATE OR REPLACE FUNCTION fn_user_library_count(p_user_id INT, p_status VARCHAR DEFAULT NULL)
RETURNS INT
LANGUAGE plpgsql
AS $$
DECLARE
    v_count INT;
BEGIN
    SELECT COUNT(*)
      INTO v_count
      FROM library_papers
     WHERE user_id = p_user_id
       AND (p_status IS NULL OR reading_status = p_status);

    RETURN v_count;
END;
$$;

-- ---------------------------------------------------------------------
-- FUNCTION 3: fn_average_rating(paper_id)
-- Returns the average review rating of a paper (NULL if never reviewed).
-- ---------------------------------------------------------------------
CREATE OR REPLACE FUNCTION fn_average_rating(p_paper_id INT)
RETURNS NUMERIC
LANGUAGE plpgsql
AS $$
DECLARE
    v_avg NUMERIC;
BEGIN
    SELECT ROUND(AVG(rating), 2)
      INTO v_avg
      FROM literature_reviews
     WHERE paper_id = p_paper_id;

    RETURN v_avg;
END;
$$;

-- ---------------------------------------------------------------------
-- PROCEDURE: sp_add_to_library(user_id, paper_id, status)
-- Adds a paper to a user's library, or updates the reading status if the
-- paper is already saved.  Requires PostgreSQL 11 or later.
-- ---------------------------------------------------------------------
CREATE OR REPLACE PROCEDURE sp_add_to_library(
    p_user_id  INT,
    p_paper_id INT,
    p_status   VARCHAR DEFAULT 'to_read'
)
LANGUAGE plpgsql
AS $$
BEGIN
    INSERT INTO library_papers (user_id, paper_id, reading_status)
    VALUES (p_user_id, p_paper_id, p_status)
    ON CONFLICT (user_id, paper_id)
    DO UPDATE SET reading_status = EXCLUDED.reading_status;
END;
$$;

-- ---------------------------------------------------------------------
-- TRIGGER 1: keep paper_notes.updated_at current
-- Fires before every UPDATE on paper_notes.
-- ---------------------------------------------------------------------
CREATE OR REPLACE FUNCTION trg_fn_set_note_updated_at()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.updated_at := CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_paper_notes_updated_at ON paper_notes;
CREATE TRIGGER trg_paper_notes_updated_at
BEFORE UPDATE ON paper_notes
FOR EACH ROW
EXECUTE FUNCTION trg_fn_set_note_updated_at();

-- ---------------------------------------------------------------------
-- TRIGGER 2: validate citations
-- A paper cannot cite a paper that was published in a LATER year.
-- Fires before INSERT or UPDATE on citations.
-- ---------------------------------------------------------------------
CREATE OR REPLACE FUNCTION trg_fn_validate_citation()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    v_citing_year INT;
    v_cited_year  INT;
BEGIN
    SELECT publication_year INTO v_citing_year FROM papers WHERE paper_id = NEW.citing_paper_id;
    SELECT publication_year INTO v_cited_year  FROM papers WHERE paper_id = NEW.cited_paper_id;

    IF v_citing_year < v_cited_year THEN
        RAISE EXCEPTION
            'Invalid citation: paper % (year %) cannot cite paper % (year %), which was published later.',
            NEW.citing_paper_id, v_citing_year, NEW.cited_paper_id, v_cited_year;
    END IF;

    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_citations_validate ON citations;
CREATE TRIGGER trg_citations_validate
BEFORE INSERT OR UPDATE ON citations
FOR EACH ROW
EXECUTE FUNCTION trg_fn_validate_citation();

-- ---------------------------------------------------------------------
-- Quick checks
-- ---------------------------------------------------------------------
SELECT fn_citation_count(4)       AS times_paper4_cited;   -- expected: 3
SELECT fn_user_library_count(2)   AS user2_total_saved;    -- expected: 4
SELECT fn_average_rating(6)       AS paper6_avg_rating;    -- expected: 5.00
