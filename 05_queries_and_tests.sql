-- =====================================================================
-- ResearchHub : Research Paper Management System
-- File   : 05_queries_and_tests.sql
-- Purpose: Demonstrates the SQL concepts listed in the proposal.
-- Note   : Run AFTER files 01 to 04. Run each query one at a time
--          (select the query text, then press F5 in pgAdmin 4).
-- =====================================================================

-- =====================================================================
-- PART A : INSERT, UPDATE, DELETE
-- =====================================================================

-- A1. INSERT a new paper (temporary demo row)
INSERT INTO papers (title, abstract, publication_year, venue)
VALUES ('Sample Paper for DML Demo', 'Temporary row used to demonstrate INSERT, UPDATE and DELETE.', 2026, 'Demo Venue')
RETURNING paper_id, title;

-- A2. UPDATE that paper
UPDATE papers
SET venue = 'Updated Demo Venue'
WHERE title = 'Sample Paper for DML Demo'
RETURNING paper_id, title, venue;

-- A3. DELETE that paper (cleans up the demo row)
DELETE FROM papers
WHERE title = 'Sample Paper for DML Demo'
RETURNING paper_id, title;

-- A4. UPDATE a reading status
UPDATE library_papers
SET reading_status = 'completed'
WHERE user_id = 1 AND paper_id = 6;

-- =====================================================================
-- PART B : SELECT, WHERE, ORDER BY
-- =====================================================================

-- B1. All papers, newest first
SELECT paper_id, title, publication_year, venue
FROM papers
ORDER BY publication_year DESC, title;

-- B2. Papers published after 2014
SELECT title, publication_year
FROM papers
WHERE publication_year > 2014
ORDER BY publication_year;

-- B3. Keyword search in the title (case-insensitive)
SELECT paper_id, title
FROM papers
WHERE title ILIKE '%network%'
ORDER BY title;

-- B4. Papers published between 2012 and 2016
SELECT title, publication_year
FROM papers
WHERE publication_year BETWEEN 2012 AND 2016
ORDER BY publication_year;

-- =====================================================================
-- PART C : INNER JOIN and LEFT JOIN
-- =====================================================================

-- C1. INNER JOIN: papers with their authors in author order
SELECT p.title, a.full_name AS author, pa.author_order
FROM papers p
INNER JOIN paper_authors pa ON pa.paper_id  = p.paper_id
INNER JOIN authors a        ON a.author_id  = pa.author_id
ORDER BY p.title, pa.author_order;

-- C2. INNER JOIN: all papers written by a given author
SELECT p.title, p.publication_year
FROM authors a
INNER JOIN paper_authors pa ON pa.author_id = a.author_id
INNER JOIN papers p         ON p.paper_id   = pa.paper_id
WHERE a.full_name = 'Geoffrey E. Hinton'
ORDER BY p.publication_year;

-- C3. LEFT JOIN: every topic with its paper count (including topics with no papers)
SELECT t.topic_name, COUNT(pt.paper_id) AS paper_count
FROM topics t
LEFT JOIN paper_topics pt ON pt.topic_id = t.topic_id
GROUP BY t.topic_name
ORDER BY paper_count DESC, t.topic_name;

-- C4. LEFT JOIN: every user with the number of saved papers (including users with none)
SELECT u.full_name, COUNT(lp.library_id) AS saved_papers
FROM users u
LEFT JOIN library_papers lp ON lp.user_id = u.user_id
GROUP BY u.user_id, u.full_name
ORDER BY saved_papers DESC, u.full_name;

-- C5. LEFT JOIN + IS NULL: papers that are never cited
SELECT p.title, p.publication_year
FROM papers p
LEFT JOIN citations c ON c.cited_paper_id = p.paper_id
WHERE c.citation_id IS NULL
ORDER BY p.publication_year;

-- C6. Self-join on papers via citations: who cites whom
SELECT citing.title AS citing_paper, cited.title AS cited_paper
FROM citations c
INNER JOIN papers citing ON citing.paper_id = c.citing_paper_id
INNER JOIN papers cited  ON cited.paper_id  = c.cited_paper_id
ORDER BY citing.publication_year, citing.title;

-- C7. Notes with user name and paper title
SELECT u.full_name AS user_name, p.title AS paper_title, n.note_text, n.created_at
FROM paper_notes n
INNER JOIN users  u ON u.user_id  = n.user_id
INNER JOIN papers p ON p.paper_id = n.paper_id
ORDER BY u.full_name, p.title;

-- =====================================================================
-- PART D : GROUP BY, HAVING and aggregate functions
-- =====================================================================

-- D1. Number of papers per publication year
SELECT publication_year, COUNT(*) AS papers_published
FROM papers
GROUP BY publication_year
ORDER BY publication_year;

-- D2. Topics that contain at least 2 papers (HAVING)
SELECT t.topic_name, COUNT(*) AS paper_count
FROM topics t
INNER JOIN paper_topics pt ON pt.topic_id = t.topic_id
GROUP BY t.topic_name
HAVING COUNT(*) >= 2
ORDER BY paper_count DESC;

-- D3. Average rating and number of reviews per paper
SELECT p.title, COUNT(r.review_id) AS review_count, ROUND(AVG(r.rating), 2) AS avg_rating
FROM papers p
INNER JOIN literature_reviews r ON r.paper_id = p.paper_id
GROUP BY p.title
ORDER BY avg_rating DESC, p.title;

-- D4. Users who have completed at least 2 papers (HAVING)
SELECT u.full_name, COUNT(*) AS completed_papers
FROM users u
INNER JOIN library_papers lp ON lp.user_id = u.user_id
WHERE lp.reading_status = 'completed'
GROUP BY u.full_name
HAVING COUNT(*) >= 2;

-- D5. MIN, MAX, AVG and COUNT on papers
SELECT COUNT(*)                          AS total_papers,
       MIN(publication_year)             AS oldest_year,
       MAX(publication_year)             AS newest_year,
       ROUND(AVG(publication_year), 1)   AS average_year
FROM papers;

-- D6. Papers per author (authors with more than one paper)
SELECT a.full_name, COUNT(pa.paper_id) AS paper_count
FROM authors a
INNER JOIN paper_authors pa ON pa.author_id = a.author_id
GROUP BY a.author_id, a.full_name
HAVING COUNT(pa.paper_id) > 1
ORDER BY paper_count DESC, a.full_name;

-- D7. Library status summary
SELECT reading_status, COUNT(*) AS total
FROM library_papers
GROUP BY reading_status
ORDER BY total DESC;

-- =====================================================================
-- PART E : Subqueries
-- =====================================================================

-- E1. Papers not saved in anybody's library
SELECT title
FROM papers
WHERE paper_id NOT IN (SELECT paper_id FROM library_papers)
ORDER BY title;

-- E2. Papers published after the average publication year
SELECT title, publication_year
FROM papers
WHERE publication_year > (SELECT AVG(publication_year) FROM papers)
ORDER BY publication_year;

-- E3. Papers that have been cited at least twice
SELECT title
FROM papers
WHERE paper_id IN (
    SELECT cited_paper_id
    FROM citations
    GROUP BY cited_paper_id
    HAVING COUNT(*) >= 2
);

-- E4. Papers reviewed with the highest rating (rating = max rating)
SELECT p.title, r.rating
FROM literature_reviews r
INNER JOIN papers p ON p.paper_id = r.paper_id
WHERE r.rating = (SELECT MAX(rating) FROM literature_reviews);

-- E5. Users who have written at least one note (EXISTS)
SELECT full_name
FROM users u
WHERE EXISTS (SELECT 1 FROM paper_notes n WHERE n.user_id = u.user_id);

-- =====================================================================
-- PART F : Views
-- =====================================================================

-- F1. Paper details with authors and topics
SELECT * FROM v_paper_details ORDER BY publication_year;

-- F2. A user's personal library
SELECT * FROM v_user_library WHERE user_id = 2 ORDER BY added_date;

-- F3. Citation statistics (most cited first)
SELECT * FROM v_paper_citation_stats ORDER BY times_cited DESC, title;

-- F4. Reviews summary
SELECT * FROM v_review_summary ORDER BY review_date;

-- =====================================================================
-- PART G : Functions and procedure
-- =====================================================================

-- G1. Citation count for every paper using the function
SELECT paper_id, title, fn_citation_count(paper_id) AS times_cited
FROM papers
ORDER BY times_cited DESC, title;

-- G2. Library counts for user 2 (all, and only completed)
SELECT fn_user_library_count(2)              AS total_saved,
       fn_user_library_count(2, 'completed') AS completed;

-- G3. Average rating of paper 6
SELECT fn_average_rating(6) AS avg_rating;

-- G4. Procedure: add a paper to user 4's library, then change its status
CALL sp_add_to_library(4, 6, 'to_read');
CALL sp_add_to_library(4, 6, 'reading');
SELECT * FROM v_user_library WHERE user_id = 4;

-- =====================================================================
-- PART H : Trigger tests
-- =====================================================================

-- H1. updated_at trigger: updating a note refreshes updated_at
UPDATE paper_notes
SET note_text = note_text || ' (revised)'
WHERE note_id = 1;

SELECT note_id, note_text, created_at, updated_at
FROM paper_notes
WHERE note_id = 1;

-- H2. citation trigger: this should FAIL
--     (paper 1 is from 1970 and cannot cite paper 6 from 2017).
--     Remove the leading "--" to run it and see the error message.
-- INSERT INTO citations (citing_paper_id, cited_paper_id) VALUES (1, 6);

-- =====================================================================
-- PART I : Constraint tests (each of these should FAIL)
--          Remove the leading "--" on ONE line at a time to test.
-- =====================================================================

-- I1. Duplicate email (UNIQUE)
-- INSERT INTO users (full_name, email, role) VALUES ('Duplicate', 'student1@example.com', 'student');

-- I2. Invalid role (CHECK)
-- INSERT INTO users (full_name, email, role) VALUES ('Bad Role', 'badrole@example.com', 'manager');

-- I3. Invalid publication year (CHECK)
-- INSERT INTO papers (title, publication_year) VALUES ('Future Paper', 3000);

-- I4. Invalid rating (CHECK)
-- INSERT INTO literature_reviews (user_id, paper_id, summary, rating) VALUES (4, 1, 'Test', 9);

-- I5. Self-citation (CHECK)
-- INSERT INTO citations (citing_paper_id, cited_paper_id) VALUES (2, 2);

-- I6. Same paper saved twice by the same user (UNIQUE)
-- INSERT INTO library_papers (user_id, paper_id) VALUES (1, 6);

-- I7. Non-existing user (FOREIGN KEY)
-- INSERT INTO paper_notes (user_id, paper_id, note_text) VALUES (999, 1, 'No such user');

-- =====================================================================
-- PART J : Index usage (optional)
-- =====================================================================

-- J1. See the query plan for a search by year
EXPLAIN SELECT * FROM papers WHERE publication_year = 2017;
