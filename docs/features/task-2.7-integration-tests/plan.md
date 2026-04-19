# Task 2.7: Write Integration Tests with Real Database

**Phase**: Phase 2 Foundation
**Status**: In Progress
**Goal**: Write and verify comprehensive integration tests that test search tools with the real PostgreSQL database

## What We're Building

Integration tests for the search tools (`search_documents`, `get_document`, `get_related_documents`) that connect to and test against the actual PostgreSQL database with real document data.

## Why It Matters

- **Foundation Validation**: Ensures the database layer, ORM models, and search tools work together correctly in a real environment
- **Confidence**: Provides confidence that the tools behave as expected with actual data from the 47K+ document database
- **Regression Detection**: Catches issues before they reach production
- **End-to-End Coverage**: Tests complete workflows from search → retrieval → following relations

## Current State

- ✅ Integration test file exists: `tests/integration/test_search_tools_integration.py` (360 lines, 23 tests)
- ✅ Tests are well-structured with clear organization into test classes
- ❌ All integration tests currently fail due to database connection issue (postgres role doesn't exist)
- ✅ 92 unit tests passing (config, logging, database, search utilities)
- ✅ 8 tests skipped (require database)

## Design Decisions

### Test Organization
- **By Tool**: Separate test classes for each search tool (`TestSearchDocumentsIntegration`, `TestGetDocumentIntegration`, `TestGetRelatedDocumentsIntegration`)
- **Workflows**: End-to-end integration tests for realistic search patterns (`TestSearchToolsEndToEnd`)
- **Error Handling**: Specific test class for error conditions (`TestSearchToolsErrorHandling`)

### Test Strategy
- **Real Data**: Use actual documents from the law_agent database
- **Graceful Skipping**: Tests skip if no documents found (rather than fail)
- **No Fixtures**: Avoid creating test data; test against real production data
- **Connection Cleanup**: Properly dispose database connections after each test

### Database Access
- Tests assume PostgreSQL is running on localhost:5432
- Tests assume "law_agent" database exists with migrated documents
- Tests assume database credentials in config.yaml or environment

## Key Design Decisions

1. **No Mocking**: Integration tests use real database to catch real issues
2. **Graceful Degradation**: Tests skip rather than fail if data unavailable
3. **Self-Contained**: Each test is independent and can run in any order
4. **Connection Cleanup**: Proper fixture cleanup prevents connection leaks

## Success Criteria

- [ ] PostgreSQL database is accessible with postgres user
- [ ] All 23 integration tests pass with real database
- [ ] Combined unit + integration test count ≥ 115 tests
- [ ] All code quality checks pass (black, ruff, mypy)
- [ ] Test coverage > 80% for search tools module
- [ ] Integration tests run successfully against law_agent database with 47K+ documents

## Dependencies

- PostgreSQL 14+ running with law_agent database
- Documents table populated with migrated data (47K+ documents)
- Relations table populated with document citations
- Configuration file (config.yaml) or environment variables set

## Known Issues

1. **Missing postgres role**: Current error indicates postgres user doesn't exist in PostgreSQL
   - Solution: Create postgres user or use existing user with correct credentials

2. **Database connectivity**: Tests need proper DB configuration
   - Solution: Verify config.yaml has correct connection parameters

## Open Questions

- Should we seed test data into a test database, or use production data?
  - Decision: Use production data (law_agent) - integration tests should validate against real data

- How to handle tests in CI/CD where database might not be available?
  - Solution: Integration tests are marked to skip if database unavailable; unit tests always pass

## Blockers

- PostgreSQL postgres user doesn't exist or password is wrong
- Need to determine correct database credentials

## For Future Developers

1. Integration tests require a running PostgreSQL database with law_agent database
2. Database credentials should be in config.yaml or environment variables
3. Tests are designed to skip gracefully if documents are unavailable
4. Always run `pytest tests/` to verify both unit and integration tests
5. To run only integration tests: `pytest tests/integration/`
6. To debug integration tests, check database connection first: `psql -d law_agent -c "SELECT COUNT(*) FROM documents;"`
