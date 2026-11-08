-- =====================================================================
-- ResearchHub : Research Paper Management System
-- File   : 01_schema.sql
-- Purpose: Creates all 10 tables with primary keys, foreign keys,
--          unique constraints and check constraints.
-- DBMS   : PostgreSQL (run in pgAdmin 4 -> Query Tool)
--
-- STEP 0 (do once, in pgAdmin 4):
--   Right-click "Databases" -> Create -> Database... -> name: researchhub
--   Then right-click the new database -> Query Tool, and run this file.
-- =====================================================================

-- Drop in reverse dependency order so the script can be re-run safely.
DROP TABLE IF EXISTS paper_notes         CASCADE;
DROP TABLE IF EXISTS citations           CASCADE;
DROP TABLE IF EXISTS literature_reviews  CASCADE;
DROP TABLE IF EXISTS library_papers      CASCADE;
DROP TABLE IF EXISTS paper_topics        CASCADE;
DROP TABLE IF EXISTS topics              CASCADE;
DROP TABLE IF EXISTS paper_authors       CASCADE;
DROP TABLE IF EXISTS authors             CASCADE;
DROP TABLE IF EXISTS papers              CASCADE;
DROP TABLE IF EXISTS users               CASCADE;

-- ---------------------------------------------------------------------
-- 1. users : registered users of the system
-- ---------------------------------------------------------------------
CREATE TABLE users (
    user_id     SERIAL       PRIMARY KEY,
    full_name   VARCHAR(100) NOT NULL,
    email       VARCHAR(150) NOT NULL UNIQUE,
    role        VARCHAR(20)  NOT NULL DEFAULT 'student',
    created_at  TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_users_role  CHECK (role IN ('student', 'researcher', 'faculty')),
    CONSTRAINT chk_users_email CHECK (email LIKE '%_@_%._%')
);

-- ---------------------------------------------------------------------
-- 2. papers : research paper details
-- ---------------------------------------------------------------------
CREATE TABLE papers (
    paper_id          SERIAL       PRIMARY KEY,
    title             VARCHAR(300) NOT NULL,
    abstract          TEXT,
    publication_year  INT          NOT NULL,
    venue             VARCHAR(200),
    doi               VARCHAR(100) UNIQUE,
    CONSTRAINT chk_papers_year CHECK (publication_year BETWEEN 1900 AND 2100)
);

-- ---------------------------------------------------------------------
-- 3. authors : paper authors
-- ---------------------------------------------------------------------
CREATE TABLE authors (
    author_id    SERIAL       PRIMARY KEY,
    full_name    VARCHAR(100) NOT NULL,
    affiliation  VARCHAR(200),
    email        VARCHAR(150) UNIQUE
);

-- ---------------------------------------------------------------------
-- 4. paper_authors : junction table (papers <-> authors), many-to-many
-- ---------------------------------------------------------------------
CREATE TABLE paper_authors (
    paper_id      INT NOT NULL,
    author_id     INT NOT NULL,
    author_order  INT NOT NULL DEFAULT 1,
    PRIMARY KEY (paper_id, author_id),
    CONSTRAINT fk_pa_paper  FOREIGN KEY (paper_id)  REFERENCES papers(paper_id)   ON DELETE CASCADE,
    CONSTRAINT fk_pa_author FOREIGN KEY (author_id) REFERENCES authors(author_id) ON DELETE CASCADE,
    CONSTRAINT chk_pa_order CHECK (author_order > 0)
);

-- ---------------------------------------------------------------------
-- 5. topics : research topics / subject areas
-- ---------------------------------------------------------------------
CREATE TABLE topics (
    topic_id     SERIAL       PRIMARY KEY,
    topic_name   VARCHAR(100) NOT NULL UNIQUE,
    description  TEXT
);

-- ---------------------------------------------------------------------
-- 6. paper_topics : junction table (papers <-> topics), many-to-many
-- ---------------------------------------------------------------------
CREATE TABLE paper_topics (
    paper_id  INT NOT NULL,
    topic_id  INT NOT NULL,
    PRIMARY KEY (paper_id, topic_id),
    CONSTRAINT fk_pt_paper FOREIGN KEY (paper_id) REFERENCES papers(paper_id) ON DELETE CASCADE,
    CONSTRAINT fk_pt_topic FOREIGN KEY (topic_id) REFERENCES topics(topic_id) ON DELETE CASCADE
);

-- ---------------------------------------------------------------------
-- 7. library_papers : papers saved by users (personal library)
-- ---------------------------------------------------------------------
CREATE TABLE library_papers (
    library_id      SERIAL      PRIMARY KEY,
    user_id         INT         NOT NULL,
    paper_id        INT         NOT NULL,
    reading_status  VARCHAR(20) NOT NULL DEFAULT 'to_read',
    added_date      DATE        NOT NULL DEFAULT CURRENT_DATE,
    CONSTRAINT fk_lib_user  FOREIGN KEY (user_id)  REFERENCES users(user_id)   ON DELETE CASCADE,
    CONSTRAINT fk_lib_paper FOREIGN KEY (paper_id) REFERENCES papers(paper_id) ON DELETE CASCADE,
    CONSTRAINT uq_lib_user_paper UNIQUE (user_id, paper_id),
    CONSTRAINT chk_lib_status CHECK (reading_status IN ('to_read', 'reading', 'completed'))
);

-- ---------------------------------------------------------------------
-- 8. literature_reviews : a user's short review of a paper
-- ---------------------------------------------------------------------
CREATE TABLE literature_reviews (
    review_id    SERIAL PRIMARY KEY,
    user_id      INT    NOT NULL,
    paper_id     INT    NOT NULL,
    summary      TEXT   NOT NULL,
    rating       INT,
    review_date  DATE   NOT NULL DEFAULT CURRENT_DATE,
    CONSTRAINT fk_rev_user  FOREIGN KEY (user_id)  REFERENCES users(user_id)   ON DELETE CASCADE,
    CONSTRAINT fk_rev_paper FOREIGN KEY (paper_id) REFERENCES papers(paper_id) ON DELETE CASCADE,
    CONSTRAINT uq_rev_user_paper UNIQUE (user_id, paper_id),
    CONSTRAINT chk_rev_rating CHECK (rating BETWEEN 1 AND 5)
);

-- ---------------------------------------------------------------------
-- 9. citations : which paper cites which paper (self-referencing M:N)
-- ---------------------------------------------------------------------
CREATE TABLE citations (
    citation_id      SERIAL PRIMARY KEY,
    citing_paper_id  INT    NOT NULL,
    cited_paper_id   INT    NOT NULL,
    CONSTRAINT fk_cit_citing FOREIGN KEY (citing_paper_id) REFERENCES papers(paper_id) ON DELETE CASCADE,
    CONSTRAINT fk_cit_cited  FOREIGN KEY (cited_paper_id)  REFERENCES papers(paper_id) ON DELETE CASCADE,
    CONSTRAINT uq_cit_pair   UNIQUE (citing_paper_id, cited_paper_id),
    CONSTRAINT chk_cit_not_self CHECK (citing_paper_id <> cited_paper_id)
);

-- ---------------------------------------------------------------------
-- 10. paper_notes : personal notes written by a user about a paper
-- ---------------------------------------------------------------------
CREATE TABLE paper_notes (
    note_id     SERIAL    PRIMARY KEY,
    user_id     INT       NOT NULL,
    paper_id    INT       NOT NULL,
    note_text   TEXT      NOT NULL,
    created_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,  -- maintained by a trigger
    CONSTRAINT fk_note_user  FOREIGN KEY (user_id)  REFERENCES users(user_id)   ON DELETE CASCADE,
    CONSTRAINT fk_note_paper FOREIGN KEY (paper_id) REFERENCES papers(paper_id) ON DELETE CASCADE
);

-- Quick check: list all tables created in the public schema.
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
ORDER BY table_name;
