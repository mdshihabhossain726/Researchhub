-- =====================================================================
-- ResearchHub : Research Paper Management System
-- File   : 02_sample_data.sql
-- Purpose: Inserts sample records into all 10 tables for testing.
-- Note   : Run AFTER 01_schema.sql.
--          Paper titles/authors are well-known publications used as
--          illustrative sample data; affiliations and citation links
--          are simplified for demonstration purposes.
--          User names and emails are dummy values (example.com).
--          Serial IDs are assigned in insert order starting from 1,
--          and the junction-table rows below rely on those IDs.
-- =====================================================================

TRUNCATE TABLE paper_notes, citations, literature_reviews, library_papers,
               paper_topics, topics, paper_authors, authors, papers, users
RESTART IDENTITY CASCADE;

-- ---------------------------------------------------------------------
-- users  (IDs 1-4)
-- ---------------------------------------------------------------------
INSERT INTO users (full_name, email, role) VALUES
('Sample Student One',    'student1@example.com',    'student'),     -- 1
('Sample Researcher Two', 'researcher2@example.com', 'researcher'),  -- 2
('Sample Faculty Three',  'faculty3@example.com',    'faculty'),     -- 3
('Sample Student Four',    'student4@example.com',    'student');     -- 4

-- ---------------------------------------------------------------------
-- papers  (IDs 1-8)
-- ---------------------------------------------------------------------
INSERT INTO papers (title, abstract, publication_year, venue) VALUES
('A Relational Model of Data for Large Shared Data Banks',
 'Introduces the relational model of data and the idea of data independence for large shared data banks.',
 1970, 'Communications of the ACM'),                                    -- 1
('ImageNet Classification with Deep Convolutional Neural Networks',
 'Trains a large deep convolutional network for large-scale image classification.',
 2012, 'NeurIPS (NIPS)'),                                                -- 2
('Dropout: A Simple Way to Prevent Neural Networks from Overfitting',
 'Presents dropout, a regularization technique that randomly drops units during training.',
 2014, 'Journal of Machine Learning Research'),                          -- 3
('Adam: A Method for Stochastic Optimization',
 'Presents an adaptive first-order gradient-based optimization algorithm.',
 2014, 'arXiv'),                                                         -- 4
('Deep Residual Learning for Image Recognition',
 'Introduces residual connections that make very deep networks easier to train.',
 2016, 'CVPR'),                                                          -- 5
('Attention Is All You Need',
 'Proposes the Transformer, a model based entirely on attention mechanisms.',
 2017, 'NeurIPS'),                                                       -- 6
('BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding',
 'Presents bidirectional pre-training of Transformers for language understanding tasks.',
 2018, 'arXiv'),                                                         -- 7
('MapReduce: Simplified Data Processing on Large Clusters',
 'Describes a programming model for processing large data sets on clusters of machines.',
 2004, 'OSDI');                                                          -- 8

-- ---------------------------------------------------------------------
-- authors  (IDs 1-26)
-- ---------------------------------------------------------------------
INSERT INTO authors (full_name, affiliation) VALUES
('Edgar F. Codd',          'IBM Research'),            -- 1
('Alex Krizhevsky',        'University of Toronto'),   -- 2
('Ilya Sutskever',         'University of Toronto'),   -- 3
('Geoffrey E. Hinton',     'University of Toronto'),   -- 4
('Nitish Srivastava',      'University of Toronto'),   -- 5
('Ruslan Salakhutdinov',   'University of Toronto'),   -- 6
('Diederik P. Kingma',     'University of Amsterdam'), -- 7
('Jimmy Ba',               'University of Toronto'),   -- 8
('Kaiming He',             'Microsoft Research'),      -- 9
('Xiangyu Zhang',          'Microsoft Research'),      -- 10
('Shaoqing Ren',           'Microsoft Research'),      -- 11
('Jian Sun',               'Microsoft Research'),      -- 12
('Ashish Vaswani',         'Google Brain'),            -- 13
('Noam Shazeer',           'Google Brain'),            -- 14
('Niki Parmar',            'Google Research'),         -- 15
('Jakob Uszkoreit',        'Google Research'),         -- 16
('Llion Jones',            'Google Research'),         -- 17
('Aidan N. Gomez',         'University of Toronto'),   -- 18
('Lukasz Kaiser',          'Google Brain'),            -- 19
('Illia Polosukhin',       NULL),                      -- 20
('Jacob Devlin',           'Google AI Language'),      -- 21
('Ming-Wei Chang',         'Google AI Language'),      -- 22
('Kenton Lee',             'Google AI Language'),      -- 23
('Kristina Toutanova',     'Google AI Language'),      -- 24
('Jeffrey Dean',           'Google'),                  -- 25
('Sanjay Ghemawat',        'Google');                  -- 26

-- ---------------------------------------------------------------------
-- paper_authors  (paper_id, author_id, author_order)
-- ---------------------------------------------------------------------
INSERT INTO paper_authors (paper_id, author_id, author_order) VALUES
(1, 1, 1),
(2, 2, 1), (2, 3, 2), (2, 4, 3),
(3, 5, 1), (3, 4, 2), (3, 2, 3), (3, 3, 4), (3, 6, 5),
(4, 7, 1), (4, 8, 2),
(5, 9, 1), (5, 10, 2), (5, 11, 3), (5, 12, 4),
(6, 13, 1), (6, 14, 2), (6, 15, 3), (6, 16, 4), (6, 17, 5), (6, 18, 6), (6, 19, 7), (6, 20, 8),
(7, 21, 1), (7, 22, 2), (7, 23, 3), (7, 24, 4),
(8, 25, 1), (8, 26, 2);

-- ---------------------------------------------------------------------
-- topics  (IDs 1-7)   -- topic 7 intentionally has no papers
-- ---------------------------------------------------------------------
INSERT INTO topics (topic_name, description) VALUES
('Databases',                  'Data models, storage and query processing'),          -- 1
('Deep Learning',              'Neural networks with many layers'),                   -- 2
('Computer Vision',            'Understanding images and video'),                     -- 3
('Natural Language Processing','Computational analysis of human language'),           -- 4
('Optimization',               'Methods for minimizing or maximizing objectives'),    -- 5
('Distributed Systems',        'Computation and storage across multiple machines'),   -- 6
('Quantum Computing',          'Computation using quantum-mechanical phenomena');     -- 7

-- ---------------------------------------------------------------------
-- paper_topics  (paper_id, topic_id)
-- ---------------------------------------------------------------------
INSERT INTO paper_topics (paper_id, topic_id) VALUES
(1, 1),
(2, 2), (2, 3),
(3, 2),
(4, 2), (4, 5),
(5, 2), (5, 3),
(6, 2), (6, 4),
(7, 2), (7, 4),
(8, 6), (8, 1);

-- ---------------------------------------------------------------------
-- library_papers  (user_id, paper_id, reading_status, added_date)
-- ---------------------------------------------------------------------
INSERT INTO library_papers (user_id, paper_id, reading_status, added_date) VALUES
(1, 6, 'reading',   '2026-09-05'),
(1, 7, 'to_read',   '2026-09-06'),
(1, 5, 'completed', '2026-09-10'),
(2, 6, 'completed', '2026-09-12'),
(2, 7, 'completed', '2026-09-15'),
(2, 4, 'reading',   '2026-09-20'),
(2, 1, 'to_read',   '2026-09-21'),
(3, 1, 'completed', '2026-10-01'),
(3, 2, 'completed', '2026-10-02'),
(3, 6, 'to_read',   '2026-10-05');

-- ---------------------------------------------------------------------
-- literature_reviews  (user_id, paper_id, summary, rating, review_date)
-- ---------------------------------------------------------------------
INSERT INTO literature_reviews (user_id, paper_id, summary, rating, review_date) VALUES
(1, 5, 'Residual connections make very deep networks easier to train and improve accuracy.', 5, '2026-09-11'),
(2, 6, 'Proposes the Transformer, relying on attention instead of recurrence or convolution.', 5, '2026-09-13'),
(2, 7, 'Bidirectional pre-training gives strong results across many language understanding tasks.', 4, '2026-09-16'),
(3, 1, 'Foundational paper that introduced the relational model used by modern databases.', 5, '2026-10-03'),
(3, 2, 'Shows that deep convolutional networks can excel at large-scale image classification.', 4, '2026-10-04');

-- ---------------------------------------------------------------------
-- citations  (citing_paper_id, cited_paper_id)  -- illustrative links
-- ---------------------------------------------------------------------
INSERT INTO citations (citing_paper_id, cited_paper_id) VALUES
(3, 2),
(5, 2), (5, 4),
(6, 3), (6, 4), (6, 5),
(7, 4), (7, 6);

-- ---------------------------------------------------------------------
-- paper_notes  (user_id, paper_id, note_text)
-- ---------------------------------------------------------------------
INSERT INTO paper_notes (user_id, paper_id, note_text) VALUES
(1, 6, 'Understand multi-head attention before implementing the model.'),
(1, 5, 'Skip connection idea: output = F(x) + x.'),
(2, 7, 'Compare masked language modelling with next-word prediction.'),
(2, 6, 'Re-read the positional encoding section.'),
(3, 1, 'Use as a reference for the normalization lecture.');

-- Quick check: row count of every table.
SELECT 'users' AS table_name, COUNT(*) AS row_count FROM users
UNION ALL SELECT 'papers',             COUNT(*) FROM papers
UNION ALL SELECT 'authors',            COUNT(*) FROM authors
UNION ALL SELECT 'paper_authors',      COUNT(*) FROM paper_authors
UNION ALL SELECT 'topics',             COUNT(*) FROM topics
UNION ALL SELECT 'paper_topics',       COUNT(*) FROM paper_topics
UNION ALL SELECT 'library_papers',     COUNT(*) FROM library_papers
UNION ALL SELECT 'literature_reviews', COUNT(*) FROM literature_reviews
UNION ALL SELECT 'citations',          COUNT(*) FROM citations
UNION ALL SELECT 'paper_notes',        COUNT(*) FROM paper_notes;
