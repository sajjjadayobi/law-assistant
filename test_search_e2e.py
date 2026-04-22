#!/usr/bin/env python3
"""
End-to-End Test for Search Tools

This script tests the three core search tools directly:
1. search_documents() - Full-text search
2. get_document() - Document retrieval
3. get_related_documents() - Citation traversal

Run with: python test_search_e2e.py
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from law_agent.tools.search import get_document, get_related_documents, search_documents


def test_search_tools():
    """Test all three search tools end-to-end."""

    print("=" * 80)
    print("E2E Test: Search Tools")
    print("=" * 80)
    print()

    # Test 1: Search for "بیمه" (insurance)
    print("Test 1: search_documents('بیمه', limit=5)")
    print("-" * 80)

    try:
        results = search_documents("بیمه", limit=5)
        print(f"✅ Found {len(results)} results")

        if len(results) == 0:
            print("❌ FAIL: Expected at least 1 result for 'بیمه'")
            return False

        print("\nTop result:")
        print(f"  - doc_id: {results[0].doc_id}")
        print(f"  - title: {results[0].title[:100]}...")
        print(f"  - doc_type: {results[0].doc_type}")
        print(f"  - relevance_score: {results[0].relevance_score:.3f}")

        # Store first result for next tests
        first_doc_id = results[0].doc_id

    except Exception as e:
        print(f"❌ FAIL: {type(e).__name__}: {e}")
        return False

    print()

    # Test 2: Get full document
    print(f"Test 2: get_document({first_doc_id})")
    print("-" * 80)

    try:
        doc = get_document(first_doc_id)

        if doc is None:
            print(f"❌ FAIL: Document {first_doc_id} not found")
            return False

        print("✅ Retrieved document successfully")
        print(f"  - doc_id: {doc.doc_id}")
        print(f"  - title: {doc.title[:100]}...")
        print(f"  - doc_type: {doc.doc_type}")
        print(f"  - content length: {len(doc.full_content)} characters")
        print(f"  - tags: {doc.tags[:3] if doc.tags else 'None'}...")
        print(f"  - relations count: {doc.relations_count}")

    except Exception as e:
        print(f"❌ FAIL: {type(e).__name__}: {e}")
        return False

    print()

    # Test 3: Get related documents
    print(f"Test 3: get_related_documents({first_doc_id}, limit=5)")
    print("-" * 80)

    try:
        related = get_related_documents(first_doc_id, limit=5)
        print(f"✅ Found {len(related)} related documents")

        if len(related) > 0:
            print("\nFirst related document:")
            print(f"  - doc_id: {related[0].doc_id}")
            print(f"  - title: {related[0].title[:100]}...")
            print(f"  - doc_type: {related[0].doc_type}")
        else:
            print("  (No related documents found - this is OK)")

    except Exception as e:
        print(f"❌ FAIL: {type(e).__name__}: {e}")
        return False

    print()

    # Test 4: Search with filters
    print("Test 4: search_documents('قانون', doc_types=['law'], limit=3)")
    print("-" * 80)

    try:
        laws = search_documents("قانون", doc_types=["law"], limit=3)
        print(f"✅ Found {len(laws)} laws")

        if len(laws) > 0:
            # Verify all results are laws
            all_laws = all(doc.doc_type == "law" for doc in laws)
            if all_laws:
                print("✅ All results are of type 'law'")
            else:
                print("❌ FAIL: Some results are not laws")
                return False

        for i, law in enumerate(laws[:3], 1):
            print(f"\nLaw {i}:")
            print(f"  - title: {law.title[:80]}...")

    except Exception as e:
        print(f"❌ FAIL: {type(e).__name__}: {e}")
        return False

    print()

    # Test 5: Empty search
    print("Test 5: search_documents('xyzabc123nonsense', limit=5)")
    print("-" * 80)

    try:
        no_results = search_documents("xyzabc123nonsense", limit=5)
        print(f"✅ Search completed (found {len(no_results)} results)")

        if len(no_results) == 0:
            print("✅ Correctly returned empty results for nonsense query")
        else:
            print(f"  (Found {len(no_results)} results - may be partial matches)")

    except Exception as e:
        print(f"❌ FAIL: {type(e).__name__}: {e}")
        return False

    print()
    print("=" * 80)
    print("✅ ALL SEARCH TOOL TESTS PASSED!")
    print("=" * 80)

    return True


if __name__ == "__main__":
    success = test_search_tools()
    sys.exit(0 if success else 1)
