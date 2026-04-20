-- Test data for Law Agent
-- This file contains sample documents for integration testing
-- Load with: psql -d law_agent -f scripts/load_test_data.sql

-- Disable foreign key constraints temporarily
SET session_replication_role = 'replica';

-- Clear existing test data (keeping schema)
TRUNCATE TABLE relations CASCADE;
DELETE FROM documents WHERE doc_type IN ('law', 'regulation', 'advisory_opinion', 'court_ruling', 'unified_precedent');

-- Re-enable foreign key constraints
SET session_replication_role = 'default';

-- Insert sample laws (base documents)
INSERT INTO documents (doc_id, title, doc_type, date, summary, full_content, tags, search_vector) VALUES
(1001, 'قانون مجازات اسلامی', 'law', '1392-01-01',
 'قانون مجازات اسلامی جمهوری اسلامی ایران که شامل تعریف جرائم و مجازات های مختلف است.',
 'قانون مجازات اسلامی یکی از اصلی ترین قوانین کیفری جمهوری اسلامی ایران است که برای تنظیم و تعیین مجازات های جرائم مختلف وضع شده است. این قانون شامل مقررات جامعی در خصوص انواع جرائم علیه امنیت ملی، شرف و ناموس، جان و سلامت جسمانی، آزادی، حقوق و تملک می باشد.',
 ARRAY['جرم و مجازات', 'قانون کیفری', 'حقوق جزایی'],
 to_tsvector('persian_custom', 'قانون مجازات اسلامی جرم مجازات')),

(1002, 'قانون حمایت از خانواده', 'law', '1391-06-15',
 'قانون حمایت از خانواده در ایران که شامل مسائل زناشویی و حقوق خانوادگی است.',
 'این قانون مربوط به حقوق و تکالیف اعضای خانواده و مسائل مرتبط با ازدواج و طلاق و فرزندان است.',
 ARRAY['خانواده', 'حقوق شخصی', 'ازدواج و طلاق'],
 to_tsvector('persian_custom', 'خانواده حمایت حقوق'));

-- Insert sample regulations
INSERT INTO documents (doc_id, title, doc_type, date, summary, full_content, tags, search_vector) VALUES
(2001, 'آئین‌نامه اجرایی قانون مجازات اسلامی', 'regulation', '1393-09-21',
 'آئین‌نامه اجرایی قانون مجازات اسلامی که جزئیات اجرایی را تعیین می‌کند.',
 'این آئین‌نامه شامل دستورالعمل‌های اجرایی قانون مجازات اسلامی است و نحوه اجرای مقررات این قانون را تشریح می‌کند.',
 ARRAY['اجرایی', 'مجازات', 'دستورالعمل'],
 to_tsvector('persian_custom', 'آئین نامه اجرایی مجازات'));

-- Insert sample advisory opinions
INSERT INTO documents (doc_id, title, doc_type, date, summary, full_content, tags, search_vector) VALUES
(3001, 'نظریهی مشورتی سازمان حقوق بشر درخصوص حقوق زن', 'advisory_opinion', '1393-05-10',
 'نظریهی مشورتی درخصوص حقوق زن در قانون ایران.',
 'سازمان حقوق بشر با توجه به قوانین بین‌المللی نظریهی مشورتی در خصوص حقوق زن و برابری جنسیتی تهیه کرده است.',
 ARRAY['حقوق بشر', 'زن', 'برابری'],
 to_tsvector('persian_custom', 'نظریه حقوق زن'));

-- Insert sample court rulings
INSERT INTO documents (doc_id, title, doc_type, date, summary, full_content, tags, search_vector) VALUES
(4001, 'حکم دادگاه تجدیدنظر درخصوص دعوای میراث', 'court_ruling', '1393-02-15',
 'حکم دادگاه تجدیدنظر درخصوص یک دعوای میراث و تقسیم ترکه.',
 'دادگاه تجدیدنظر با مطالعه پرونده و سند های موجود به این نتیجه رسید که...',
 ARRAY['میراث', 'ترکه', 'حقوق شخصی'],
 to_tsvector('persian_custom', 'دادگاه حکم میراث'));

-- Insert sample unified precedents
INSERT INTO documents (doc_id, title, doc_type, date, summary, full_content, tags, search_vector) VALUES
(5001, 'آرای وحدت رویه دیوان عالی کشور درخصوص قتل عمد', 'unified_precedent', '1390-12-01',
 'آرای وحدت رویه دیوان عالی کشور درخصوص تعریف و مجازات قتل عمد.',
 'دیوان عالی کشور در خصوص یکپارچگی آراء و تفسیر قانون درخصوص قتل عمد نظریه‌ای تحت عنوان وحدت رویه صادر کرده است.',
 ARRAY['قتل', 'مجازات', 'وحدت رویه'],
 to_tsvector('persian_custom', 'دیوان عالی قتل عمد'));

-- Insert sample relations (citations between documents)
INSERT INTO relations (src_doc_id, dst_doc_id, relation_type) VALUES
(2001, 1001, 'قوانین'),      -- Regulation cites Law
(3001, 1001, 'قوانین'),      -- Advisory opinion cites Law
(3001, 1002, 'قوانین'),      -- Advisory opinion cites another Law
(4001, 1001, 'قوانین'),      -- Court ruling cites Law
(4001, 2001, 'آئین‌نامه'),   -- Court ruling applies regulation
(5001, 1001, 'قوانین'),      -- Unified precedent interprets Law
(4001, 1002, 'مواد مرتبط');  -- Related articles

-- Verify data load
SELECT COUNT(*) as total_documents FROM documents;
SELECT COUNT(*) as total_relations FROM relations;

-- Verify by document type
SELECT doc_type, COUNT(*) FROM documents GROUP BY doc_type ORDER BY doc_type;
