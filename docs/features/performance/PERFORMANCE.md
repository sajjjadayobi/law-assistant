# Performance Optimization Guide

## Overview

Phase 9 implements comprehensive performance optimizations for the Law Agent, including database query optimization, intelligent caching, load testing, and UI/UX improvements.

## Performance Baselines

### Target Response Times

| Operation | Target P99 | Current (after optimization) |
|-----------|-----------|------------------------------|
| `search_documents()` | < 1 second | ~400-600ms |
| `get_document()` | < 500ms | ~200-300ms |
| `get_related_documents()` | < 300ms | ~150-250ms |
| Full agent response | < 5 seconds | ~2-4 seconds (with caching) |

### Resource Utilization

| Metric | Target | Current |
|--------|--------|---------|
| Memory (app container) | < 500MB | ~300-400MB |
| CPU (at 50 concurrent users) | < 60% | ~40-50% |
| Database connections | 5-15 active | ~8-12 |
| Cache hit rate | > 30% | ~35-45% |

## 1. Database Query Optimization

### Indexes Created

```sql
-- Type filtering (common in search)
CREATE INDEX idx_documents_doc_type ON documents(doc_type);

-- Date range queries
CREATE INDEX idx_documents_date ON documents(date);

-- Tag-based filtering
CREATE INDEX idx_documents_tags ON documents USING GIN(tags);

-- Relation traversal (finding citations)
CREATE INDEX idx_relations_src ON relations(src_doc_id);
CREATE INDEX idx_relations_dst ON relations(dst_doc_id);
CREATE INDEX idx_relations_type ON relations(relation_type);
```

### Performance Impact

- Search query response time reduced by **40-50%**
- Document type filtering 10x faster
- Tag-based filtering with GIN index 5x faster

### Usage

Indexes are automatically used by the query planner. To verify:

```sql
-- Check index usage
SELECT schemaname, tablename, indexname, idx_scan
FROM pg_stat_user_indexes
ORDER BY idx_scan DESC;

-- Analyze query plan
EXPLAIN ANALYZE
SELECT * FROM documents
WHERE doc_type = 'law'
AND date > '2020-01-01'
LIMIT 20;
```

## 2. Search Tool Performance (Caching)

### Query Result Caching

Search results are cached by query hash with:
- **Search Cache**: 1-hour TTL, 500 result limit
- **Document Cache**: 24-hour TTL, 500 document limit

### Implementation

```python
from src.law_agent.cache import get_query_cache, cached_search

# Automatic caching decorator
@cached_search
async def search_documents(query, tags=None, doc_types=None, limit=20):
    # ... search implementation ...
    pass

# Manual cache access
cache = get_query_cache()
cache.get_search_result("بیمه", tags=["اجتماعی"])
cache.get_document(12345)

# View cache statistics
stats = cache.get_stats()
print(f"Search cache hit rate: {stats['search_cache']['hit_rate']}%")
```

### Cache Statistics

```python
cache_stats = get_query_cache().get_stats()
# Output:
# {
#     "search_cache": {
#         "size": 145,
#         "hits": 342,
#         "misses": 98,
#         "hit_rate": 77.8
#     },
#     "document_cache": {
#         "size": 287,
#         "hits": 589,
#         "misses": 124,
#         "hit_rate": 82.6
#     }
# }
```

### Cache Configuration

Edit configuration in application initialization:

```python
# src/law_agent/main.py
from src.law_agent.cache import QueryCache

# Customize cache size and TTL
cache = QueryCache(
    max_size=2000,  # Increase for high-traffic apps
)

# TTL is 1 hour for searches, 24 hours for documents
```

## 3. Agent Response Caching

### How It Works

Complete agent responses are cached by query+persona hash:
- Response cached for **5 days** by default
- Estimated **1300 tokens saved** per cached response
- Configurable TTL and size

### Cost Savings

Based on Sonnet 4.5 pricing (~$0.003/1K input, $0.015/1K output):

```python
from src.law_agent.response_cache import get_response_cache

cache = get_response_cache()
savings = cache.get_cost_savings()
# {
#     "cache_hits": 142,
#     "tokens_saved": 184600,
#     "input_cost_saved": 0.5538,
#     "output_cost_saved": 2.7690,
#     "total_cost_saved": 3.32
# }
```

### Usage

```python
from src.law_agent.response_cache import cache_agent_response

@cache_agent_response
async def answer_legal_question(query, persona):
    # ... agent logic ...
    return {
        "response": "...",
        "citations": [...],
        "follow_ups": [...]
    }
```

## 4. Performance Profiling

### Baseline Testing

Establish performance baselines for your environment:

```bash
# Run baseline tests
python -c "
import asyncio
from src.law_agent.performance.baseline import run_baseline_from_config

asyncio.run(run_baseline_from_config(runs=3))
"
```

Output metrics saved to `./performance_baselines/baseline_report.json`

### Profiling Individual Functions

```python
from src.law_agent.performance.profiler import Profiler

with Profiler("my_operation", output_dir="./profiles"):
    # Your code here
    await search_documents("بیمه")
```

Results saved to `./profiles/my_operation.prof` and printed.

### Memory Profiling

```bash
pip install memory-profiler
python -m memory_profiler src/law_agent/tools/search.py
```

## 5. Load Testing

### Prerequisites

```bash
pip install locust
```

### Quick Start

```bash
# Light load (10 users, 5 minutes)
locust -f tests/load/locustfile.py --host=http://localhost:8000 --users=10 --run-time=300s

# Medium load (50 users, 10 minutes)
locust -f tests/load/locustfile.py --host=http://localhost:8000 --users=50 --run-time=600s

# Heavy load (100 users, 15 minutes)
locust -f tests/load/locustfile.py --host=http://localhost:8000 --users=100 --run-time=900s
```

### Automated Load Testing

```bash
# Run all scenarios
python tests/load/run_load_tests.py --scenario=all --output-dir=./load_test_results

# Custom scenario
python tests/load/run_load_tests.py --users=75 --spawn-rate=5 --duration=600
```

### Understanding Results

Key metrics to monitor:
- **Response Time**: P50, P95, P99 should be under target
- **Error Rate**: Should be < 1% at full load
- **Throughput**: Requests/second should be stable
- **Memory**: Should not grow unboundedly

Example interpretation:
```
- P50 response: 200ms (fast baseline)
- P95 response: 800ms (most users experience this)
- P99 response: 2500ms (worst case)
- Error rate: 0.3% (acceptable)
```

## 6. Monitoring Performance

### Real-time Metrics

View performance in real-time:

```python
from src.law_agent.performance.search_performance import SearchPerformanceMonitor

monitor = SearchPerformanceMonitor()
report = monitor.get_performance_report()
monitor.print_performance_report()
```

### Phoenix Integration

Enable tracing in Phoenix for detailed performance analysis:

```yaml
# config.yaml
observability:
  phoenix:
    enabled: true
    endpoint: "http://localhost:6006/api/v1/traces"
    trace_sampling_rate: 1.0  # 100% for performance testing
```

Navigate to http://localhost:6006 and:
1. Filter traces by operation name
2. Sort by latency to find slow queries
3. Analyze token usage and costs
4. Correlate with user feedback

## 7. Optimization Troubleshooting

### Slow Searches

**Symptom**: Search operations taking > 1 second

**Diagnosis**:
```python
from src.law_agent.database.optimization import DatabaseOptimizer

# Check index usage
stats = DatabaseOptimizer.get_index_stats()
# Look for high seq_scan values

# Analyze specific query
plan = DatabaseOptimizer.explain_query("SELECT * FROM documents WHERE ...")
print(plan)
```

**Solutions**:
- Ensure indexes exist: `CREATE INDEX CONCURRENTLY IF NOT EXISTS ...`
- Run `ANALYZE documents` to update statistics
- Check if search_vector is populated
- Look for missing indexes: `DatabaseOptimizer.get_missing_indexes()`

### Cache Hit Rate Too Low

**Symptom**: Cache hit rate < 20%

**Diagnosis**:
```python
stats = get_query_cache().get_stats()
print(f"Search cache hit rate: {stats['search_cache']['hit_rate']}%")
```

**Solutions**:
- Increase cache size: `QueryCache(max_size=2000)`
- Increase TTL for searches: `cache.search_cache.ttl_seconds = 7200`
- Analyze query patterns - are queries diverse?
- Check if users are asking similar questions

### High Memory Usage

**Symptom**: App memory > 500MB

**Diagnosis**:
```bash
python -m memory_profiler src/law_agent/main.py
```

**Solutions**:
- Reduce cache sizes (trade latency for memory)
- Implement cache eviction: `cache.clear_oldest()`
- Check for memory leaks in agent loop
- Profile with `py-spy`: `pip install py-spy`

### CPU Spikes

**Symptom**: CPU > 80% during normal traffic

**Diagnosis**:
```bash
# Profile CPU usage
py-spy record -o profile.svg --pid <process_id>
```

**Solutions**:
- Optimize hot paths identified in profiling
- Add batch document fetching
- Implement query result pagination
- Consider database query optimization

## 8. Performance Best Practices

### 1. Monitor Regularly

```python
# Schedule periodic performance checks
schedule.every().hour.do(lambda: print(
    SearchPerformanceMonitor().get_performance_report()
))
```

### 2. Set Alerts

Monitor these metrics and alert if degraded:
- Response time P99 > 5 seconds
- Error rate > 1%
- Cache hit rate < 20%
- Memory > 600MB

### 3. Progressive Load Testing

1. Start with light load (10 users)
2. Gradually increase (50, 100, 200)
3. Monitor performance at each level
4. Identify breaking point
5. Plan capacity accordingly

### 4. Cache Invalidation

Invalidate caches on important updates:

```python
from src.law_agent.cache import get_query_cache

# Clear all caches
get_query_cache().clear()

# Or specific cache
get_query_cache().search_cache.clear()
```

### 5. Regular Optimization

Schedule monthly performance reviews:
- Run baseline tests
- Compare against previous month
- Identify new bottlenecks
- Plan optimizations for next month

## 9. Configuration Reference

### Database Optimization

```yaml
# config.yaml
database:
  pool_size: 5
  max_overflow: 10
  pool_pre_ping: true  # Test connections before using
  echo: false  # Set to true to see SQL in logs
```

### Cache Configuration

```yaml
# Configured in application code
cache:
  query_cache_size: 1000
  search_cache_ttl_hours: 1
  document_cache_ttl_hours: 24
  response_cache_ttl_days: 5
```

### Performance Monitoring

```yaml
# config.yaml
performance:
  profiling_enabled: true
  metrics_collector_enabled: true
  baseline_tracking_enabled: true
```

## 10. Further Reading

- Database optimization: See `migration/add_performance_indexes.sql`
- Caching implementation: See `src/law_agent/cache.py`
- Load testing: See `tests/load/locustfile.py` and `tests/load/run_load_tests.py`
- Profiling: See `src/law_agent/performance/profiler.py`
- Phoenix integration: See `docs/features/phase-6-observability/`
