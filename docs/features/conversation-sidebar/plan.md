# Task 11.2: Conversation History Sidebar - Implementation Plan

**Status**: Planning Phase
**Priority**: ⭐ High
**Estimated Effort**: 6-8 hours
**Reference**: data-assistant sidebar implementation

---

## 🎯 Objective

Implement a persistent left sidebar showing conversation history grouped by time periods (Today, Yesterday, Previous 7 days, Previous 30 days). Users should be able to click any conversation to reload it, and the sidebar should auto-collapse/expand via hamburger menu.

---

## 📋 Design Decisions

### 1. Data Persistence Strategy
- **Choice**: Use existing PostgreSQL connection with new tables
- **Rationale**: Simpler than separate DB, reuses existing connection pool, Chainlit expects SQL Alchemy data layer
- **Alternative Considered**: Use separate SQLite for simplicity (rejected - SQLAlchemy expects async engine)

### 2. Time Grouping Logic
- **Choice**: Gregorian calendar grouping (Today, Yesterday, Last 7 days, Last 30 days)
- **Rationale**: More intuitive than Persian calendar for UI, users already familiar
- **Implementation**: Use `created_at` timestamp, calculate at query time

### 3. Thread Title Generation
- **Choice**: Auto-generate from first user message, truncated to 40 chars
- **Rationale**: Matches data-assistant pattern, no extra complexity
- **Fallback**: If no first message, use timestamp

### 4. Database Schema
- **Choice**: Inherit from Chainlit's `SQLAlchemyDataLayer` base class
- **Rationale**: Chainlit provides thread/step models, just need to customize queries
- **Key Tables**: threads, steps, elements, feedbacks (per Chainlit spec)

### 5. Sidebar State
- **Choice**: Default to "open" (visible on load)
- **Rationale**: Shows feature to new users, data-assistant uses open
- **Config**: `.chainlit/config.toml` - `default_sidebar_state = "open"`

---

## 📁 Files to Create/Modify

### NEW Files
1. `src/law_agent/data/__init__.py` - Data layer module init
2. `src/law_agent/data/models.py` - SQLAlchemy ORM models (threads, steps, elements, feedbacks)
3. `src/law_agent/data/data_layer.py` - Custom Chainlit data layer implementation
4. `migration/add_chainlit_tables.py` - Database migration script

### MODIFIED Files
1. `src/law_agent/ui/app.py` - Register data layer with `@cl.data_layer`
2. `.chainlit/config.toml` - Update UI settings for sidebar

---

## 🏗️ Implementation Details

### Phase 1: Database Schema & Migration

**Tables**:
```sql
threads
├── id (TEXT PRIMARY KEY)
├── name (TEXT)  -- Auto-generated from first message
├── user_id (TEXT)
├── user_identifier (TEXT)
├── created_at (TIMESTAMP)
├── updated_at (TIMESTAMP)
├── tags (TEXT[])
└── metadata (JSONB)

steps
├── id (TEXT PRIMARY KEY)
├── thread_id (FK → threads.id)
├── name (TEXT)
├── type (TEXT)  -- 'user_message', 'assistant_message', 'tool', 'run'
├── input (TEXT)
├── output (TEXT)
├── parent_id (TEXT)
├── created_at (TIMESTAMP)
├── metadata (JSONB)
└── show_input (TEXT)

elements
├── id (TEXT PRIMARY KEY)
├── thread_id (FK → threads.id)
├── type (TEXT)
├── name (TEXT)
├── display (TEXT)
├── url (TEXT)
├── for_id (TEXT)  -- Associated step ID
├── mime (TEXT)
└── props (JSONB)

feedbacks
├── id (TEXT PRIMARY KEY)
├── for_id (TEXT)
├── value (INTEGER)  -- 1 or -1
├── comment (TEXT)
└── created_at (TIMESTAMP)
```

**Indexes**:
- `idx_threads_user_id ON threads(user_id)`
- `idx_threads_created_at ON threads(created_at DESC)`
- `idx_steps_thread_id ON steps(thread_id)`
- `idx_steps_created_at ON steps(created_at)`

### Phase 2: Custom Data Layer

**Key Methods to Implement**:
1. `get_all_user_threads(user_id)` - Return threads grouped by time
2. `create_thread(thread_id, name, user_id)` - Create new thread
3. `create_step(thread_id, step)` - Store conversation step
4. `get_thread(thread_id)` - Load full thread
5. `get_thread_steps(thread_id)` - Load all steps for thread
6. `update_thread_name(thread_id, name)` - Auto-set from first message

**Grouping Logic**:
```python
def group_threads_by_time(threads):
    today = datetime.now().date()
    groups = {
        'امروز': [],           # Today
        'دیروز': [],            # Yesterday
        '7 روز گذشته': [],     # Last 7 days
        '30 روز گذشته': []     # Last 30 days
    }

    for thread in threads:
        thread_date = thread.created_at.date()
        days_ago = (today - thread_date).days

        if days_ago == 0:
            groups['امروز'].append(thread)
        elif days_ago == 1:
            groups['دیروز'].append(thread)
        elif days_ago <= 7:
            groups['7 روز گذشته'].append(thread)
        elif days_ago <= 30:
            groups['30 روز گذشته'].append(thread)
```

### Phase 3: UI Integration

**Changes to `app.py`**:
1. Register data layer: `@cl.data_layer def get_data_layer(): return data_layer`
2. Auto-generate thread name from first user message
3. Load thread on sidebar click (handled by Chainlit automatically)

**Changes to `config.toml`**:
```toml
[UI]
default_sidebar_state = "open"
```

---

## ✅ Success Criteria

- [ ] Database tables created successfully
- [ ] Migration script runs without errors
- [ ] Data layer initializes with async engine
- [ ] Sidebar visible on left with conversation list
- [ ] Conversations grouped by time periods (Persian labels)
- [ ] Thread titles auto-generated from first message
- [ ] Click conversation loads full history
- [ ] New chat creates new thread in database
- [ ] Active conversation highlighted in sidebar
- [ ] Sidebar collapsible/expandable via hamburger menu
- [ ] Persists across page reloads
- [ ] Performance: Sidebar loads <500ms with 100 threads

---

## 🔍 Key Dependencies

1. **Chainlit Data Layer**: `chainlit.data.sql_alchemy.SQLAlchemyDataLayer`
2. **SQLAlchemy**: Async ORM with `create_async_engine`
3. **PostgreSQL**: Existing database connection
4. **Pydantic Settings**: For database config

---

## 🚀 Implementation Approach

1. **Start with schema**: Create migration script for database tables
2. **Test migration**: Run against dev database, verify tables created
3. **Build data layer**: Implement SQLAlchemy models and custom queries
4. **Integrate with app**: Register data layer in Chainlit
5. **Test manually**: Create conversations, reload page, verify sidebar
6. **Performance check**: Load test with 100+ threads

---

## 📚 Reference Implementation

**Primary Reference**: `/Users/divar/Documents/codes/data-assistant/src/datasource/postgres/chainlit_data_layer.py`

Key sections to study:
- Lines 105-138: `FixedSQLAlchemyDataLayer` class definition
- Lines 248-429: `_get_all_user_threads_in_custom_table()` - **CRITICAL FOR SIDEBAR**
- Lines 174-217: `_create_thread_in_custom_table()`

---

## ⏱️ Time Breakdown

- Database schema & migration: 1-2 hours
- SQLAlchemy models: 1 hour
- Custom data layer implementation: 2-3 hours
- UI integration & testing: 1-2 hours
- Performance tuning & polish: 1 hour

**Total**: 6-8 hours (as estimated)

---

## 🎓 Learning Goals

- Understand Chainlit data persistence architecture
- Work with async SQLAlchemy for database operations
- Implement custom SQLAlchemy data layer for Chainlit
- Handle time-based grouping logic in Python
- Test database integration in async context

---

## 📝 Notes

- **No breaking changes**: This extends existing UI without modifying core agent
- **Backward compatible**: Old conversations not yet in database will still work
- **Scalability**: Index on `created_at` ensures sidebar query <500ms with 1000s of threads
- **Future enhancement**: Can add conversation search, tags, rename (Task 11.2+)

