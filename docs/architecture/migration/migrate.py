#!/usr/bin/env python3
"""
Complete migration script: PostgreSQL (old HTML schema) → PostgreSQL (clean text schema)

This script:
1. Strips all HTML tags and extracts clean text
2. Parses structured sections (summary, full content, dates, etc.)
3. Removes unnecessary fields
4. Migrates to minimal schema optimized for agent search
"""

import psycopg2
from psycopg2.extras import execute_batch
from bs4 import BeautifulSoup
import re
from typing import Optional, Dict, List, Tuple
from datetime import date
import jdatetime  # pip install jdatetime


# ============================================================================
# HTML PARSING - Extract clean text from HTML
# ============================================================================

def extract_summary_from_html(soup: BeautifulSoup) -> str:
    """
    Extract summary from خلاصه متن section, remove ALL HTML.
    Returns clean text.
    """
    # Find the summary section
    summary_label = soup.find('span', string=re.compile(r'خلاصه متن'))

    if summary_label:
        # Navigate to the content div
        parent = summary_label.find_parent('div')
        if parent:
            # Find the actual text div (has line-clamp class)
            content_div = parent.find('div', class_=re.compile(r'line-clamp'))
            if content_div:
                # Extract text, remove all HTML
                text = content_div.get_text(separator=' ', strip=True)
                return clean_text(text)

    # Fallback: extract first paragraph-like content
    main_content = soup.find('div', class_='post-text')
    if main_content:
        text = main_content.get_text(separator=' ', strip=True)
        # Take first 500 words as summary
        words = text.split()[:500]
        return clean_text(' '.join(words))

    # Last resort: first 500 words from entire document
    full_text = soup.get_text(separator=' ', strip=True)
    words = full_text.split()[:500]
    return clean_text(' '.join(words))


def extract_full_content_from_html(soup: BeautifulSoup) -> str:
    """
    Extract full document text from HTML, completely cleaned.
    Returns all content with proper section structure but no HTML.
    """
    # Find main content area
    content_div = soup.find('div', class_='post-text')

    if not content_div:
        # Fallback to main tag
        content_div = soup.find('main')

    if not content_div:
        # Last resort: entire body
        content_div = soup

    # Remove unwanted elements
    for unwanted in content_div(['script', 'style', 'section', 'wire:effects', 'wire:snapshot']):
        unwanted.decompose()

    # Remove Livewire components (contains JSON metadata)
    for livewire in content_div.find_all('section', class_=re.compile(r'print:hidden')):
        livewire.decompose()

    # Extract text with line breaks preserved
    text = content_div.get_text(separator='\n', strip=True)

    # Clean up
    text = clean_text(text)

    # Remove excessive line breaks (more than 2 consecutive)
    text = re.sub(r'\n{3,}', '\n\n', text)

    return text


def clean_text(text: str) -> str:
    """
    Clean and normalize Persian text.
    - Remove HTML entities
    - Normalize Persian characters
    - Remove extra whitespace
    """
    # Remove HTML entities
    text = text.replace('&nbsp;', ' ')
    text = text.replace('&zwnj;', '‌')  # Persian zero-width non-joiner
    text = text.replace('&lt;', '<')
    text = text.replace('&gt;', '>')
    text = text.replace('<br>', '\n')
    text = text.replace('<br/>', '\n')
    text = text.replace('<br />', '\n')

    # Normalize Persian/Arabic characters
    text = text.replace('ك', 'ک')  # Arabic kaf → Persian kaf
    text = text.replace('ي', 'ی')  # Arabic yeh → Persian yeh
    text = text.replace('ى', 'ی')  # Alef maksura → Persian yeh

    # Remove extra whitespace
    text = re.sub(r' +', ' ', text)  # Multiple spaces → single space
    text = re.sub(r'\n +', '\n', text)  # Leading spaces on lines
    text = re.sub(r' +\n', '\n', text)  # Trailing spaces on lines

    return text.strip()


# ============================================================================
# METADATA EXTRACTION
# ============================================================================

def infer_doc_type(title: str, content: str) -> str:
    """
    Infer document type from title and content patterns.
    Returns: 'law', 'regulation', 'advisory_opinion', 'court_ruling', 'unified_precedent'
    """
    title_lower = title.lower()
    content_preview = content[:800].lower()

    # Advisory opinion (most common)
    if 'نظریه مشورتی' in title or 'نظریه مشورتی' in content_preview:
        return 'advisory_opinion'

    # Court ruling
    if any(kw in title_lower for kw in ['دادنامه', 'رای دادگاه', 'حکم', 'شعبه']):
        return 'court_ruling'

    if any(kw in content_preview for kw in ['رای دادگاه', 'دادگاه بدوی', 'دادگاه تجدیدنظر']):
        return 'court_ruling'

    # Unified precedent
    if 'رای وحدت رویه' in title or 'آرای وحدت رویه' in content_preview:
        return 'unified_precedent'

    # Regulation
    if 'آیین‌نامه' in title or 'مقررات' in title:
        return 'regulation'

    # Law (قانون in title but NOT نظریه)
    if 'قانون' in title_lower and 'نظریه' not in title_lower:
        return 'law'

    # Default: advisory opinion (majority of corpus)
    return 'advisory_opinion'


def extract_date_from_document(title: str, content: str) -> Optional[date]:
    """
    Extract Persian date and convert to Gregorian.
    Looks for patterns like: 1398/03/25 or ۱۳۹۸/۰۳/۲۵
    """
    # Pattern: YYYY/MM/DD in Latin or Persian digits
    pattern = r'(\d{4})/(\d{2})/(\d{2})|([۰-۹]{4})/([۰-۹]{2})/([۰-۹]{2})'

    # Try title first (most reliable)
    match = re.search(pattern, title)

    if not match:
        # Try first 300 chars of content
        match = re.search(pattern, content[:300])

    if match:
        date_str = match.group(0)

        # Convert Persian digits to Latin
        persian_to_latin = str.maketrans('۰۱۲۳۴۵۶۷۸۹', '0123456789')
        date_str = date_str.translate(persian_to_latin)

        try:
            # Parse: YYYY/MM/DD
            year, month, day = map(int, date_str.split('/'))

            # Convert Persian (Jalali) to Gregorian
            persian_date = jdatetime.date(year, month, day)
            gregorian = persian_date.togregorian()

            return gregorian

        except (ValueError, Exception):
            # Invalid date, return None
            return None

    return None


# ============================================================================
# MAIN PARSING FUNCTION
# ============================================================================

def parse_html_document(page_id: int, html_content: str, title: str) -> Dict:
    """
    Main function: Parse HTML document and extract all clean fields.

    Returns dict ready for insertion into new schema:
    {
        'doc_id': int,
        'title': str,
        'doc_type': str,
        'date': date or None,
        'summary': str (clean text),
        'full_content': str (clean text)
    }
    """
    soup = BeautifulSoup(html_content, 'html.parser')

    # Extract clean text (no HTML)
    summary = extract_summary_from_html(soup)
    full_content = extract_full_content_from_html(soup)

    # Infer metadata
    doc_type = infer_doc_type(title, full_content)
    doc_date = extract_date_from_document(title, full_content)

    return {
        'doc_id': page_id,
        'title': title.strip(),
        'doc_type': doc_type,
        'date': doc_date,
        'summary': summary,
        'full_content': full_content
    }


# ============================================================================
# DATABASE MIGRATION
# ============================================================================

def migrate_documents(
    old_conn: psycopg2.extensions.connection,
    new_conn: psycopg2.extensions.connection,
    batch_size: int = 500
):
    """
    Migrate all documents from old schema to new schema.
    Extracts HTML, cleans text, removes unnecessary fields.
    """
    old_cur = old_conn.cursor()
    new_cur = new_conn.cursor()

    print("=" * 80)
    print("MIGRATING DOCUMENTS")
    print("=" * 80)

    # Count total
    old_cur.execute("SELECT COUNT(*) FROM pages WHERE relations_built = true")
    total = old_cur.fetchone()[0]
    print(f"Total documents to migrate: {total:,}")

    # Read from old database (only documents with relations built)
    old_cur.execute("""
        SELECT page_id, content, title
        FROM pages
        WHERE relations_built = true
        ORDER BY page_id
    """)

    batch = []
    processed = 0
    errors = 0

    for row in old_cur:
        page_id, html_content, title = row

        try:
            # Parse HTML and extract clean data
            doc = parse_html_document(page_id, html_content, title)

            # Validate minimum content
            if len(doc['summary']) < 50:
                print(f"  ⚠ Warning: Doc {page_id} has very short summary, skipping")
                errors += 1
                continue

            batch.append((
                doc['doc_id'],
                doc['title'],
                doc['doc_type'],
                doc['date'],
                doc['summary'],
                doc['full_content']
            ))

            # Insert batch
            if len(batch) >= batch_size:
                execute_batch(new_cur, """
                    INSERT INTO documents (doc_id, title, doc_type, date, summary, full_content)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (doc_id) DO NOTHING
                """, batch)
                new_conn.commit()

                processed += len(batch)
                progress = (processed / total) * 100
                print(f"  ✓ Migrated {processed:,}/{total:,} documents ({progress:.1f}%)")

                batch = []

        except Exception as e:
            print(f"  ✗ Error processing doc {page_id}: {str(e)[:100]}")
            errors += 1
            continue

    # Insert remaining batch
    if batch:
        execute_batch(new_cur, """
            INSERT INTO documents (doc_id, title, doc_type, date, summary, full_content)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (doc_id) DO NOTHING
        """, batch)
        new_conn.commit()
        processed += len(batch)

    print(f"\n✓ Documents migration complete!")
    print(f"  - Migrated: {processed:,}")
    print(f"  - Errors: {errors:,}")
    print()


def migrate_tags(
    old_conn: psycopg2.extensions.connection,
    new_conn: psycopg2.extensions.connection
):
    """
    Migrate tags from old page_tags junction table to new tags array.
    Only keeps 'subjects' category tags.
    """
    old_cur = old_conn.cursor()
    new_cur = new_conn.cursor()

    print("=" * 80)
    print("MIGRATING TAGS")
    print("=" * 80)

    # Get all tags grouped by page
    old_cur.execute("""
        SELECT pt.page_id, array_agg(t.tag_name) as tags
        FROM page_tags pt
        JOIN tags t ON pt.tag_id = t.tag_id
        WHERE t.category = 'subjects'  -- Only subject tags
        GROUP BY pt.page_id
    """)

    batch = []
    for row in old_cur:
        page_id, tags = row
        batch.append((tags, page_id))

        if len(batch) >= 1000:
            execute_batch(new_cur, """
                UPDATE documents
                SET tags = %s
                WHERE doc_id = %s
            """, batch)
            new_conn.commit()
            print(f"  ✓ Updated tags for {len(batch)} documents")
            batch = []

    if batch:
        execute_batch(new_cur, """
            UPDATE documents
            SET tags = %s
            WHERE doc_id = %s
        """, batch)
        new_conn.commit()

    print("✓ Tags migration complete!\n")


def migrate_relations(
    old_conn: psycopg2.extensions.connection,
    new_conn: psycopg2.extensions.connection
):
    """
    Migrate relations table (already clean, just copy).
    """
    old_cur = old_conn.cursor()
    new_cur = new_conn.cursor()

    print("=" * 80)
    print("MIGRATING RELATIONS")
    print("=" * 80)

    # Count total
    old_cur.execute("SELECT COUNT(*) FROM relations")
    total = old_cur.fetchone()[0]
    print(f"Total relations to migrate: {total:,}")

    # Direct copy
    old_cur.execute("""
        SELECT src_id, dst_id, relation_name
        FROM relations
    """)

    batch = []
    processed = 0

    for row in old_cur:
        src_id, dst_id, relation_type = row
        batch.append((src_id, dst_id, relation_type))

        if len(batch) >= 5000:
            execute_batch(new_cur, """
                INSERT INTO relations (src_doc_id, dst_doc_id, relation_type)
                VALUES (%s, %s, %s)
                ON CONFLICT DO NOTHING
            """, batch)
            new_conn.commit()
            processed += len(batch)
            print(f"  ✓ Migrated {processed:,}/{total:,} relations")
            batch = []

    if batch:
        execute_batch(new_cur, """
            INSERT INTO relations (src_doc_id, dst_doc_id, relation_type)
            VALUES (%s, %s, %s)
            ON CONFLICT DO NOTHING
        """, batch)
        new_conn.commit()
        processed += len(batch)

    print(f"✓ Relations migration complete! ({processed:,} total)\n")


# ============================================================================
# VALIDATION
# ============================================================================

def validate_migration(new_conn: psycopg2.extensions.connection):
    """
    Validate the migration with sanity checks.
    """
    cur = new_conn.cursor()

    print("=" * 80)
    print("VALIDATING MIGRATION")
    print("=" * 80)

    # Check 1: Document count
    cur.execute("SELECT COUNT(*) FROM documents")
    doc_count = cur.fetchone()[0]
    print(f"✓ Total documents: {doc_count:,}")

    # Check 2: Document types distribution
    cur.execute("""
        SELECT doc_type, COUNT(*) as count
        FROM documents
        GROUP BY doc_type
        ORDER BY count DESC
    """)
    print("\n  Document types:")
    for row in cur.fetchall():
        doc_type, count = row
        pct = (count / doc_count) * 100
        print(f"    - {doc_type}: {count:,} ({pct:.1f}%)")

    # Check 3: Documents with dates
    cur.execute("SELECT COUNT(*) FROM documents WHERE date IS NOT NULL")
    with_dates = cur.fetchone()[0]
    pct = (with_dates / doc_count) * 100
    print(f"\n  Documents with dates: {with_dates:,} ({pct:.1f}%)")

    # Check 4: Documents with tags
    cur.execute("SELECT COUNT(*) FROM documents WHERE array_length(tags, 1) > 0")
    with_tags = cur.fetchone()[0]
    pct = (with_tags / doc_count) * 100
    print(f"  Documents with tags: {with_tags:,} ({pct:.1f}%)")

    # Check 5: Relations count
    cur.execute("SELECT COUNT(*) FROM relations")
    rel_count = cur.fetchone()[0]
    print(f"  Total relations: {rel_count:,}")

    # Check 6: Sample document (show clean text)
    cur.execute("""
        SELECT doc_id, title, doc_type, LEFT(summary, 200) as summary_preview
        FROM documents
        LIMIT 1
    """)
    row = cur.fetchone()
    print(f"\n  Sample document:")
    print(f"    - ID: {row[0]}")
    print(f"    - Title: {row[1]}")
    print(f"    - Type: {row[2]}")
    print(f"    - Summary preview: {row[3]}...")

    # Check 7: Search vector created
    cur.execute("""
        SELECT COUNT(*)
        FROM documents
        WHERE search_vector IS NOT NULL
    """)
    with_vectors = cur.fetchone()[0]
    print(f"\n  Documents with search vectors: {with_vectors:,} (should be 100%)")

    print("\n✓ Validation complete!")


# ============================================================================
# MAIN
# ============================================================================

def main():
    """Main migration workflow"""

    print("\n")
    print("╔" + "═" * 78 + "╗")
    print("║" + " " * 20 + "LAW AGENT DATABASE MIGRATION" + " " * 30 + "║")
    print("║" + " " * 15 + "HTML → Clean Text + Minimal Schema" + " " * 28 + "║")
    print("╚" + "═" * 78 + "╝")
    print("\n")

    # Database connections
    OLD_DB = {
        'host': 'localhost',
        'database': 'knowledge',  # Old database name
        'user': 'postgres',
        'password': 'your_password'
    }

    NEW_DB = {
        'host': 'localhost',
        'database': 'law_agent',  # New clean database
        'user': 'postgres',
        'password': 'your_password'
    }

    try:
        # Connect to databases
        print("Connecting to databases...")
        old_conn = psycopg2.connect(**OLD_DB)
        new_conn = psycopg2.connect(**NEW_DB)
        print("✓ Connected\n")

        # Phase 1: Migrate documents (HTML → clean text)
        migrate_documents(old_conn, new_conn, batch_size=500)

        # Phase 2: Migrate tags
        migrate_tags(old_conn, new_conn)

        # Phase 3: Migrate relations
        migrate_relations(old_conn, new_conn)

        # Phase 4: Validate
        validate_migration(new_conn)

        # Close connections
        old_conn.close()
        new_conn.close()

        print("\n" + "=" * 80)
        print("✓ MIGRATION COMPLETE!")
        print("=" * 80)
        print("\nYour new database is ready for the agent!")
        print("All HTML has been cleaned, unnecessary fields removed.")
        print("\nNext steps:")
        print("  1. Run: ANALYZE documents;")
        print("  2. Test search: SELECT * FROM documents WHERE search_vector @@ to_tsquery('persian_custom', 'بیمه');")
        print("  3. Start building your agent!\n")

    except Exception as e:
        print(f"\n✗ Migration failed: {e}")
        raise


if __name__ == '__main__':
    main()
