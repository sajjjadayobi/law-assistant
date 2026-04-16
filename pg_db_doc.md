# Knowledge Base Database Documentation

## Overview

The `knowledge.sql` file is a PostgreSQL database dump containing a comprehensive legal knowledge base. This database stores Iranian legal documents including advisory opinions (نظریه مشورتی), court rulings, and law-related materials organized in a structured relational format.

**Database Size:** ~1.3 GB (789,764 lines)
**PostgreSQL Version:** 16.4
**Owner:** postgres
**Schema:** public

---

## Table 1: `pages` - Core Document Storage

### Purpose
The primary table storing all legal documents and their metadata. Each record represents a single legal page or document.

### Columns

| Column Name | Data Type | Description |
|---|---|---|
| `page_id` | BIGINT (PK) | Unique identifier for each page |
| `content` | TEXT | Full HTML content of the legal document |
| `title` | VARCHAR | Document title in Persian (نظریه مشورتی شماره...) |
| `relations_built` | BOOLEAN | Flag indicating if relations have been processed |
| `created_at` | TIMESTAMP WITH TIMEZONE | Record creation timestamp |
| `relations_in_progress` | BOOLEAN | Flag showing if relation processing is active |
| `relations_started_at` | TIMESTAMP WITH TIMEZONE | Timestamp when relation processing began |
| `http_status` | VARCHAR | HTTP status code (optional field) |

### Key Characteristics
- **Primary Key:** `page_id` (numeric ID like 1635489, 2487369)
- **Content Type:** HTML-formatted legal documents with metadata in Persian
- **Content Structure:** Contains structured HTML with:
  - Post card layout
  - Document titles
  - Summaries (خلاصه متن)
  - Full document text
  - Court rulings and advisory opinions
  - Tags and categorization data

### Sample Data Structure
```
page_id: 1635489
title: نظریه مشورتی شماره 7/97/1596 مورخ 1398/03/25
content: <main><div class="post-card">...</div></main>
relations_built: true
created_at: 2025-12-22 22:06:33.425306+00
relations_in_progress: false
relations_started_at: NULL
http_status: NULL
```

### Example Query
```sql
SELECT page_id, title, relations_built, created_at
FROM pages
WHERE relations_built = true
LIMIT 5;
```

---

## Table 2: `tags` - Document Classification

### Purpose
Categorizes documents using tags that help organize legal materials by subject matter, document type, and other classification criteria.

### Columns

| Column Name | Data Type | Description |
|---|---|---|
| `tag_id` | SERIAL (PK) | Unique identifier for each tag |
| `tag_name` | VARCHAR | Display name of the tag in Persian |
| `category` | VARCHAR | Category type ('subjects', etc.) or NULL |

### Key Characteristics
- **Primary Key:** `tag_id` (numeric, auto-incrementing)
- **Language:** All tags are in Persian
- **Categories:** Can include:
  - `subjects` - Subject matter classification
  - `NULL` - Unclassified tags (like 'آرشیو')

### Sample Tags
```
tag_id: 3  | tag_name: اساسی        | category: subjects
tag_id: 8  | tag_name: اراضی و باغها | category: subjects
tag_id: 37 | tag_name: اداری        | category: subjects
tag_id: 49 | tag_name: آرشیو        | category: NULL
```

### Example Query
```sql
SELECT tag_id, tag_name, category
FROM tags
WHERE category = 'subjects'
ORDER BY tag_id;
```

---

## Table 3: `page_tags` - Document-Tag Association

### Purpose
Junction table implementing a many-to-many relationship between pages and tags, allowing documents to be tagged with multiple classifications.

### Columns

| Column Name | Data Type | Description |
|---|---|---|
| `page_id` | BIGINT (FK) | Reference to pages.page_id |
| `tag_id` | BIGINT (FK) | Reference to tags.tag_id |

### Key Characteristics
- **Primary Key:** Composite (page_id, tag_id)
- **Foreign Keys:**
  - `page_id` → `pages.page_id`
  - `tag_id` → `tags.tag_id`
- **Relationship Type:** Many-to-Many
- **Purpose:** Link documents to their subject classifications

### Sample Data
```
page_id: 0123468 | tag_id: 1
page_id: 0123497 | tag_id: 2
page_id: 0123847 | tag_id: 1
page_id: 0127398 | tag_id: 1
```

### Example Query
```sql
SELECT p.page_id, p.title, t.tag_name
FROM pages p
JOIN page_tags pt ON p.page_id = pt.page_id
JOIN tags t ON pt.tag_id = t.tag_id
WHERE t.tag_name = 'اساسی'
LIMIT 10;
```

---

## Table 4: `relations` - Document Cross-References

### Purpose
Tracks relationships between documents, allowing the system to link related legal documents together. Documents can reference other documents they are related to or cite.

### Columns

| Column Name | Data Type | Description |
|---|---|---|
| `id` | SERIAL (PK) | Unique identifier for the relation record |
| `src_id` | BIGINT (FK) | Source page ID (originating document) |
| `dst_id` | BIGINT (FK) | Destination page ID (related document) |
| `relation_name` | VARCHAR | Type of relation in Persian |

### Key Characteristics
- **Primary Key:** `id` (auto-incrementing)
- **Foreign Keys:**
  - `src_id` → `pages.page_id`
  - `dst_id` → `pages.page_id`
- **Directed Graph:** Creates a directed relationship from source to destination
- **Relation Types:** Stored as text in Persian:
  - `مواد مرتبط` (Related Articles/Laws)
  - `قوانین` (Laws/Legislation)
  - Other relation types as needed

### Sample Data
```
id: 1 | src_id: 0123468 | dst_id: 8749056 | relation_name: مواد مرتبط
id: 2 | src_id: 0123468 | dst_id: 5078931 | relation_name: مواد مرتبط
id: 3 | src_id: 0123468 | dst_id: 9673250 | relation_name: قوانین
id: 4 | src_id: 0123468 | dst_id: 5709812 | relation_name: قوانین
id: 5 | src_id: 0123497 | dst_id: 4315628 | relation_name: مواد مرتبط
```

### Example Query
```sql
-- Find all documents related to a specific page
SELECT src_id, dst_id, relation_name
FROM relations
WHERE src_id = 0123468
ORDER BY relation_name, dst_id;

-- Find related articles and laws for a document
SELECT p.title, r.relation_name, p2.title as related_title
FROM relations r
JOIN pages p ON r.src_id = p.page_id
JOIN pages p2 ON r.dst_id = p2.page_id
WHERE r.src_id = 0123468
  AND r.relation_name = 'مواد مرتبط'
LIMIT 10;
```

---

## Database Schema Diagram

```
pages (Core Documents)
  ├── page_id (PK)
  ├── content (HTML)
  ├── title
  ├── relations_built (BOOLEAN)
  ├── created_at (TIMESTAMP)
  ├── relations_in_progress (BOOLEAN)
  ├── relations_started_at (TIMESTAMP)
  └── http_status

       ↓ (FK: page_id)

page_tags (Many-to-Many Junction)
  ├── page_id (FK → pages)
  └── tag_id (FK → tags)

       ↓ (FK: tag_id)

tags (Classification/Categories)
  ├── tag_id (PK)
  ├── tag_name
  └── category

relations (Document Links)
  ├── id (PK)
  ├── src_id (FK → pages)
  ├── dst_id (FK → pages)
  └── relation_name
```

---

## Data Statistics & Observations

### Record Counts (Approximate)
- **Total File Size:** 1.3 GB
- **Total Lines:** 789,764
- **Estimated Pages:** Thousands of legal documents
- **Tags:** Multiple categories for subject classification
- **Relations:** Comprehensive cross-reference network

### Content Domain
The database specializes in Iranian legal materials:
- Advisory opinions (نظریه مشورتی) from the judiciary office
- Court rulings and verdicts
- Legal interpretations
- Case law references
- Administrative law documents

### Key Features
1. **Multi-language Support:** Primary content in Persian (Farsi)
2. **Rich Content:** HTML-formatted documents with structured metadata
3. **Relationship Tracking:** Documents linked through multiple relation types
4. **Temporal Metadata:** Records include timestamps for tracking
5. **Processing Flags:** Indicates document processing status

---

## Common Query Patterns

### 1. Find Documents by Title
```sql
SELECT page_id, title, created_at
FROM pages
WHERE title LIKE '%نظریه مشورتی%'
LIMIT 10;
```

### 2. Get Documents with Specific Tags
```sql
SELECT DISTINCT p.page_id, p.title
FROM pages p
JOIN page_tags pt ON p.page_id = pt.page_id
JOIN tags t ON pt.tag_id = t.tag_id
WHERE t.tag_name IN ('اساسی', 'اداری');
```

### 3. Trace Document Relations
```sql
WITH RECURSIVE doc_relations AS (
  SELECT src_id, dst_id, relation_name, 1 as depth
  FROM relations
  WHERE src_id = 0123468

  UNION ALL

  SELECT r.src_id, r.dst_id, r.relation_name, depth + 1
  FROM relations r
  JOIN doc_relations dr ON r.src_id = dr.dst_id
  WHERE depth < 3
)
SELECT * FROM doc_relations
ORDER BY depth, relation_name;
```

### 4. Find Unprocessed Documents
```sql
SELECT page_id, title, created_at
FROM pages
WHERE relations_built = false
ORDER BY created_at DESC;
```

---

## Relationships & Integrity

### Foreign Key Relationships
1. **page_tags → pages:** Many-to-One (each tag reference must have a valid page)
2. **page_tags → tags:** Many-to-One (each tag reference must have a valid tag)
3. **relations → pages:** Two Many-to-One relationships
   - `src_id` must exist in `pages.page_id`
   - `dst_id` must exist in `pages.page_id`

### Referential Integrity
- Tags are independent entities that can exist without being assigned to pages
- Pages can exist without tags
- Relations create explicit links between pages
- The `relations_built` flag indicates if the page's relations have been fully processed

## Notes for Developers

1. **Content Format:** Pages contain raw HTML with embedded Persian text and metadata
2. **Character Encoding:** UTF-8 encoding for Persian language support
3. **Temporal Data:** All timestamps use UTC timezone (specified as +00)
4. **Processing Pipeline:** The `relations_started_at` and `relations_in_progress` fields suggest an asynchronous relation-building process
5. **Null Handling:** Fields like `http_status` and `relations_started_at` can be NULL for unprocessed or initial states

---

---

## Document Relationship Structure & Tree Analysis

### Overview
The database forms a **Directed Acyclic Graph (DAG)** of legal documents connected through the `relations` table. This structure enables complex legal research by linking related laws, precedents, and interpretations.

### Relationship Types

The `relations` table tracks two primary types of document relationships:

#### 1. **مواد مرتبط (Related Articles)**
- Documents that reference or are mentioned in related contexts
- Lateral connections between similar or complementary legal materials
- Example: Advisory opinion referencing related administrative laws

#### 2. **قوانین (Laws/Legislation)**
- Parent-child relationships where a document cites or implements a specific law
- Hierarchical link from specific rulings to broader legislative frameworks
- Example: Court ruling citing the parent law it's based on

### Document Relationship Graph Structure

```
┌─────────────────────────────────────────────────────────────┐
│              Legal Knowledge Base - DAG Structure            │
└─────────────────────────────────────────────────────────────┘

Level 0: Constitution & Foundational Laws
  └─→ نظام اساسی جمهوری اسلامی (Constitutional Laws)

Level 1: Primary Laws & Legislation
  ├─→ قانون مبارزه با مواد مخدر (Drug Laws)
  ├─→ قانون مجازات اسلامی (Islamic Penal Code)
  ├─→ قانون مالیاتهای مستقیم (Tax Laws)
  ├─→ قانون مدیریت خدمات کشوری (Civil Service Management Laws)
  └─→ قانون جنگلها و مراتع (Forest & Pasture Laws)

Level 2: Amendments & Executive Regulations
  ├─→ اصلاحات قانونی (Law Amendments)
  ├─→ آیین‌نامه‌های اجرایی (Executive Regulations)
  └─→ تبصره‌ها (Law Clarifications)

Level 3: Advisory Opinions & Interpretations
  ├─→ نظریه مشورتی اداره کل حقوقی (Advisory Opinions)
  └─→ تفاسیر قانونی (Legal Interpretations)

Level 4: Court Rulings & Verdicts
  ├─→ احکام دیوان عدالت اداری (Administrative Court Rulings)
  ├─→ احکام دادگاه انقلاب (Revolutionary Court Rulings)
  ├─→ احکام دادگاه تجدیدنظر (Appeal Court Decisions)
  └─→ احکام دادگاه‌های عمومی (General Court Verdicts)
```

### Relationship Patterns

#### Pattern 1: Linear Citation Chain
```
Advisory Opinion (Doc A)
  ↓ (قوانین / Laws)
Primary Law (Doc B)
  ↓ (مواد مرتبط / Related Articles)
Related Amendment (Doc C)
  ↓ (قوانین / Laws)
Court Ruling (Doc D)
```

**Example from database:**
- Advisory Opinion نظریه مشورتی شماره 7/97/3183
  ↓ cites
- قانون تشدید مجازات مرتکبین ارتشاء (Law on Embezzlement Penalties)
  ↓ relates to
- قانون مدیریت خدمات کشوری (Civil Service Management Law)

#### Pattern 2: Multi-Source Convergence
```
Multiple Primary Laws
  ↓ ↓ ↓
Advisory Opinion (integrates all)
  ↓
Court Ruling (applies)
```

**Example:**
- قانون مواد مخدر + قانون قاچاق کالا + قوانین تعزیرات حکومتی
  ↓ integrated by
- نظریه مشورتی شماره 7/97/3253
  ↓ applied in
- Court Rulings on Drug Trafficking Cases

#### Pattern 3: Hierarchical Dependency
```
Constitutional Law (اساسی)
  ├─→ Civil Service Law
  │    ├─→ Employment Regulations
  │    └─→ Benefits Rules
  │         ↓
  │    Advisory Opinions
  │         ↓
  │    Court Precedents
  │
  └─→ Criminal Law
       ├─→ Drug Laws
       ├─→ Islamic Penalties
       └─→ Court Verdicts
```

### Tree Structure Analysis

#### Document Hierarchy Depth

**Root Nodes (No incoming relations):**
- Constitutional Laws
- Primary Legislative Acts
- Foundational Laws (صریح)

**Mid-Level Nodes (2-4 incoming/outgoing relations):**
- Amendments
- Executive Regulations
- Advisory Opinions

**Leaf Nodes (Mostly outgoing, few incoming):**
- Court Rulings
- Specific Case Verdicts
- Individual Administrative Decisions

#### Connectivity Metrics

| Metric | Description | Significance |
|--------|-------------|--------------|
| **In-degree** | Number of documents citing a document | Legal importance/precedent value |
| **Out-degree** | Number of documents cited by a document | Document completeness/comprehensiveness |
| **Path Depth** | Maximum distance from root to leaf | Legal framework complexity |
| **Branching Factor** | Average documents per level | Knowledge base structure density |

### Multi-Branch Trees

The database is **NOT a simple tree** but a **forest with cross-branch connections**:

```
Tree 1: Criminal Law Branch
  Constitutional Law
    ↓
  Islamic Penal Code
    ├─→ Drug Laws
    ├─→ Embezzlement Laws
    └─→ Traffic Offense Laws

Tree 2: Civil Law Branch
  Constitutional Law
    ↓
  Civil Service Management Law
    ├─→ Employment Rules
    ├─→ Pension Rules
    └─→ Service Credit Laws

Cross-Branch Links:
  Drug Laws ←→ Tax Evasion Laws (مواد مرتبط)
  Penal Code ←→ Civil Service Law (implementation)
```

### Query Patterns for Tree Traversal

#### Find All Ancestors of a Document
```sql
-- Find all laws cited by a court ruling (top-to-bottom)
WITH RECURSIVE ancestors AS (
  SELECT src_id, dst_id, relation_name, 1 as depth
  FROM relations
  WHERE src_id = [court_ruling_id]

  UNION ALL

  SELECT r.src_id, r.dst_id, r.relation_name, a.depth + 1
  FROM relations r
  JOIN ancestors a ON r.src_id = a.dst_id
  WHERE a.depth < 10
)
SELECT * FROM ancestors
ORDER BY depth;
```

#### Find All Descendants of a Document
```sql
-- Find all rulings that apply a specific law (bottom-to-top)
WITH RECURSIVE descendants AS (
  SELECT src_id, dst_id, relation_name, 1 as depth
  FROM relations
  WHERE dst_id = [law_id]

  UNION ALL

  SELECT r.src_id, r.dst_id, r.relation_name, d.depth + 1
  FROM relations r
  JOIN descendants d ON r.dst_id = d.src_id
  WHERE d.depth < 10
)
SELECT * FROM descendants
ORDER BY depth;
```

#### Find Related Documents at Same Level
```sql
-- Find all documents sharing similar relations (horizontal links)
SELECT DISTINCT p.page_id, p.title, t.tag_name
FROM pages p
JOIN page_tags pt ON p.page_id = pt.page_id
JOIN tags t ON pt.tag_id = t.tag_id
WHERE t.tag_name IN (
  SELECT t2.tag_name
  FROM page_tags pt2
  JOIN tags t2 ON pt2.tag_id = t2.tag_id
  WHERE pt2.page_id = [reference_doc_id]
);
```

### Relationship Impact on Agent Design

For the Law Agent to work effectively:

1. **Context Expansion:** When retrieving a document, automatically fetch connected ancestors (primary laws) and descendants (related rulings)
2. **Relationship-Based Search:** Use `relations` table as primary search path, not just full-text
3. **Precedent Chains:** Follow citation chains to build legal arguments
4. **Cross-Reference Resolution:** Link amendments to original laws for complete understanding
5. **Tree Depth Limitation:** Cap recursive queries at 3-4 levels to manage token usage

### Practical Document Flow Example

**User Query:** "What are the rules about service credit for contract employees?"

**Agent Navigation:**

```
Step 1: Search → Find Document
  → "سابقه خدمت کارکنان شرکتی" (Service Credit for Contract Employees)

Step 2: Follow Ancestors (Laws cited)
  → قانون نحوه تاثیر سوابق خدمت غیردولتی (Law on Non-Government Service Credit)
  → قانون مدیریت خدمات کشوری (Civil Service Management Law)
  → اساسی (Constitutional basis if applicable)

Step 3: Follow Descendants (Related rulings)
  → احکام دیوان عدالت اداری (Related Administrative Court Rulings)
  → آرای تجدیدنظر (Appeal Court Decisions)

Step 4: Cross-References (Similar context)
  → Other service credit advisory opinions
  → Related employment law rulings

Step 5: Compile Answer
  → Primary law definition + amendments + precedents + related cases
```

---

## Conclusion

The `knowledge.sql` database is a well-structured legal knowledge base designed to store, categorize, and interlink Iranian legal documents. Its four-table structure efficiently manages documents, classifications, and relationships while maintaining data integrity through foreign key constraints. The system supports complex legal research and relationship discovery through its comprehensive tagging and relation-tracking capabilities.

The **directed acyclic graph (DAG) structure** of document relationships creates a multi-level hierarchy from constitutional laws down to individual court rulings, enabling sophisticated legal research and precedent-based reasoning suitable for an AI agent application.

