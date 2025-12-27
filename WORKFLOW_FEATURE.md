# Workflow/Skill-Tree Study Mode Feature

## Overview

This feature implements a visual workflow/skill-tree study mode with:
- **Flashcard system** with spaced repetition (SM-2 algorithm)
- **Workflow visualization** with position coordinates for skill-tree UI
- **Prerequisite tracking** for topic dependencies
- **Workflow stages** to track learning progression
- **Question and flashcard counts** displayed on workflow nodes

## User Flow

```
1. User uploads study material
2. AI generates:
   - Topics/subtopics (hierarchical)
   - 15-20 quiz questions per topic
   - 3-5 flashcards per topic (NEW!)
3. User sees workflow visualization (skill-tree)
4. User completes quiz for Topic A
5. Topic A flashcard review node unlocks (SEPARATE NODE)
6. User reviews flashcards with spaced repetition
7. Topic A marked as completed
8. Prerequisite topics unlock (if any)
```

## Database Schema Changes

### New Table: `flashcards`

```sql
CREATE TABLE flashcards (
    id SERIAL PRIMARY KEY,
    topic_id INTEGER NOT NULL REFERENCES topics(id) ON DELETE CASCADE,

    -- Flashcard content
    front TEXT NOT NULL,           -- Question/term
    back TEXT NOT NULL,            -- Answer/definition
    hint TEXT,                     -- Optional mnemonic/hint
    order_index INTEGER DEFAULT 0,

    -- Spaced repetition (SM-2 algorithm)
    ease_factor FLOAT DEFAULT 2.5,      -- Difficulty rating (1.3-2.5+)
    interval_days INTEGER DEFAULT 1,    -- Days until next review
    repetitions INTEGER DEFAULT 0,      -- Successful review count
    next_review_date TIMESTAMP,         -- When to review next
    last_reviewed_at TIMESTAMP,         -- Last review time

    -- Statistics
    total_reviews INTEGER DEFAULT 0,    -- Total review attempts
    correct_reviews INTEGER DEFAULT 0,  -- Successful reviews

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_flashcards_topic_id ON flashcards(topic_id);
```

### Updated Table: `topics`

Added workflow visualization fields:

```sql
ALTER TABLE topics ADD COLUMN position_x FLOAT;
ALTER TABLE topics ADD COLUMN position_y FLOAT;
ALTER TABLE topics ADD COLUMN workflow_stage VARCHAR DEFAULT 'locked';
ALTER TABLE topics ADD COLUMN prerequisite_topic_ids INTEGER[];
```

**Workflow Stages:**
- `locked` - Topic not yet accessible (prerequisites not met)
- `quiz_available` - User can start the quiz
- `quiz_completed` - Quiz finished, flashcards available
- `flashcard_review` - User is reviewing flashcards
- `completed` - Both quiz and flashcards completed

## New API Endpoints

### 1. Get Topic Flashcards

**Endpoint:** `GET /api/v1/study-sessions/topics/{topic_id}/flashcards`

**Description:** Get all flashcards for a topic (for post-quiz review)

**Response:**
```json
{
  "topic_id": 123,
  "topic_title": "Multi-tier Application Design",
  "flashcards": [
    {
      "id": 1,
      "front": "What is the definition of load balancing?",
      "back": "Load balancing is the process of distributing network traffic across multiple servers...",
      "hint": "Think about traffic distribution",
      "order_index": 0,
      "ease_factor": 2.5,
      "interval_days": 1,
      "repetitions": 0,
      "next_review_date": "2025-12-28T10:00:00",
      "last_reviewed_at": null,
      "total_reviews": 0,
      "correct_reviews": 0,
      "accuracy": 0.0,
      "is_due": true
    }
  ],
  "total_flashcards": 5,
  "due_for_review": 5
}
```

### 2. Submit Flashcard Review

**Endpoint:** `POST /api/v1/study-sessions/flashcards/{flashcard_id}/review`

**Request Body:**
```json
{
  "quality": 4
}
```

**Quality Ratings:**
- `0-2`: Failed (card will be shown again soon)
- `3`: Hard (passed but difficult)
- `4`: Good (passed with some effort)
- `5`: Easy (passed easily)

**Response:**
```json
{
  "flashcard_id": 1,
  "quality": 4,
  "next_review_date": "2025-12-30T10:00:00",
  "interval_days": 2,
  "ease_factor": 2.5,
  "repetitions": 1,
  "total_reviews": 1,
  "correct_reviews": 1,
  "accuracy": 100.0
}
```

**Spaced Repetition Algorithm (SM-2):**
- First review: 1 day
- Second review: 6 days
- Subsequent reviews: interval × ease_factor
- Failed reviews (quality 0-2): Reset to 1 day

### 3. Get Workflow Visualization

**Endpoint:** `GET /api/v1/study-sessions/sessions/{session_id}/workflow`

**Description:** Get workflow visualization data for skill-tree UI

**Response:**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "title": "Cloud Architecture Study",
  "progress": 35,
  "workflow_nodes": [
    {
      "topic_id": 1,
      "title": "Load Balancing",
      "description": "Understanding traffic distribution",
      "is_category": false,
      "parent_topic_id": null,
      "order_index": 0,
      "workflow_stage": "quiz_completed",
      "position_x": 100.0,
      "position_y": 50.0,
      "prerequisite_topic_ids": [],
      "question_count": 15,
      "flashcard_count": 3,
      "completed": false,
      "score": 80,
      "current_question_index": 15
    },
    {
      "topic_id": 2,
      "title": "Auto Scaling",
      "description": "Dynamic resource allocation",
      "is_category": false,
      "parent_topic_id": null,
      "order_index": 1,
      "workflow_stage": "locked",
      "position_x": 250.0,
      "position_y": 50.0,
      "prerequisite_topic_ids": [1],
      "question_count": 15,
      "flashcard_count": 4,
      "completed": false,
      "score": null,
      "current_question_index": 0
    }
  ],
  "total_nodes": 2
}
```

## AI Prompt Changes

The AI now generates both questions AND flashcards:

```json
{
  "subtopics": {
    "0": {
      "questions": [
        {
          "question": "What is load balancing?",
          "options": ["A", "B", "C", "D"],
          "correctAnswer": 0,
          "explanation": "...",
          "sourceText": "...",
          "sourcePage": 1
        }
      ],
      "flashcards": [
        {
          "front": "Load Balancing",
          "back": "Process of distributing network traffic across multiple servers",
          "hint": "Think about traffic distribution"
        }
      ]
    }
  }
}
```

**Flashcard Generation Guidelines:**
- 3-5 flashcards per topic
- Focus on KEY DEFINITIONS, CONCEPTS, TERMS
- Front: Concise question or term
- Back: Comprehensive but digestible answer
- Hint: Optional mnemonic or memory aid

## Frontend Integration Guide

### 1. Workflow Visualization (Skill-Tree UI)

**Recommended Library:** React Flow, D3.js, or Cytoscape.js

**Basic Implementation:**

```typescript
interface WorkflowNode {
  topic_id: number;
  title: string;
  position_x: number;
  position_y: number;
  workflow_stage: 'locked' | 'quiz_available' | 'quiz_completed' | 'flashcard_review' | 'completed';
  question_count: number;
  flashcard_count: number;
  prerequisite_topic_ids: number[];
}

// Fetch workflow data
const workflow = await axios.get(`/api/v1/study-sessions/sessions/${sessionId}/workflow`);

// Render nodes
workflow.workflow_nodes.forEach(node => {
  // Create node at position (position_x, position_y)
  // Show node title
  // Show question count in tiny letters: "15 questions"
  // If quiz completed, show flashcard review node separately
  // Connect prerequisites with lines/arrows
  // Apply stage-based styling (locked = gray, available = green, etc.)
});
```

### 2. Flashcard Review UI

**Recommended Flow:**
1. User completes quiz for Topic A
2. Show "Review Flashcards" button/node
3. On click, fetch flashcards: `GET /topics/{topicId}/flashcards`
4. Show flashcard front
5. User flips card (show back)
6. User rates difficulty (0-5)
7. Submit review: `POST /flashcards/{id}/review`
8. Show next flashcard or completion message

**Example Component:**

```typescript
const FlashcardReview = ({ topicId }) => {
  const [flashcards, setFlashcards] = useState([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [showBack, setShowBack] = useState(false);

  useEffect(() => {
    // Fetch flashcards
    axios.get(`/api/v1/study-sessions/topics/${topicId}/flashcards`)
      .then(res => setFlashcards(res.data.flashcards));
  }, [topicId]);

  const submitReview = async (quality: number) => {
    const flashcard = flashcards[currentIndex];
    await axios.post(`/api/v1/study-sessions/flashcards/${flashcard.id}/review`, { quality });

    // Move to next card
    if (currentIndex < flashcards.length - 1) {
      setCurrentIndex(currentIndex + 1);
      setShowBack(false);
    } else {
      // All flashcards reviewed!
      alert('Great job! Come back tomorrow for more reviews.');
    }
  };

  const current = flashcards[currentIndex];

  return (
    <div className="flashcard">
      <div className="card">
        <div className="front">{current.front}</div>
        {showBack && (
          <>
            <div className="back">{current.back}</div>
            {current.hint && <div className="hint">💡 {current.hint}</div>}
          </>
        )}
      </div>

      {!showBack ? (
        <button onClick={() => setShowBack(true)}>Show Answer</button>
      ) : (
        <div className="rating-buttons">
          <button onClick={() => submitReview(0)}>Failed (0)</button>
          <button onClick={() => submitReview(3)}>Hard (3)</button>
          <button onClick={() => submitReview(4)}>Good (4)</button>
          <button onClick={() => submitReview(5)}>Easy (5)</button>
        </div>
      )}
    </div>
  );
};
```

### 3. Workflow Node Display

**Topic Node (Quiz):**
```jsx
<div className="workflow-node">
  <h3>{node.title}</h3>
  <span className="tiny">{node.question_count} questions</span>
  <StatusBadge stage={node.workflow_stage} />
</div>
```

**Flashcard Review Node (SEPARATE):**
```jsx
{node.workflow_stage === 'quiz_completed' && (
  <div className="workflow-node flashcard-node">
    <h3>Review Flashcards</h3>
    <span className="tiny">{node.flashcard_count} cards</span>
    <button onClick={() => startFlashcardReview(node.topic_id)}>
      Start Review
    </button>
  </div>
)}
```

## Database Migration

**Run migration before deployment:**

```bash
python migrations/add_flashcards_and_workflow.py
```

This will:
1. Create `flashcards` table
2. Add workflow fields to `topics` table
3. Initialize `workflow_stage` for existing topics
4. Create necessary indexes

## Testing Checklist

- [ ] Create study session - verify flashcards are generated
- [ ] Check cache hit - verify flashcards are restored from cache
- [ ] GET /topics/{id}/flashcards - verify response format
- [ ] POST /flashcards/{id}/review - verify spaced repetition calculation
- [ ] GET /sessions/{id}/workflow - verify workflow visualization data
- [ ] Test prerequisite unlocking logic
- [ ] Verify workflow_stage transitions
- [ ] Test spaced repetition algorithm (quality 0-2 vs 3-5)

## Cost Impact

**AI Generation:**
- No additional cost per session (flashcards generated alongside questions)
- Uses same AI call, just extended prompt (~200 extra tokens per topic)
- Estimated cost increase: ~$0.001 per session (negligible)

**Storage:**
- Flashcards table: ~500 bytes per flashcard
- 5 flashcards × 20 topics = 100 flashcards per session = ~50KB
- Negligible storage cost

## Next Steps

1. **Frontend Implementation**
   - Implement skill-tree visualization
   - Build flashcard review UI
   - Add prerequisite unlock logic

2. **Backend Enhancements** (Future)
   - Auto-calculate optimal topic positions using graph layout algorithm
   - Add flashcard review reminders (email/push notifications)
   - Analytics dashboard for spaced repetition effectiveness

3. **Mobile App** (Future)
   - Daily flashcard review notifications
   - Offline flashcard review support
   - Gamification (streaks, badges for consistent reviews)

## Support

For questions or issues, refer to:
- API documentation: `/docs` endpoint
- Database schema: `app/models/`
- Migration script: `migrations/add_flashcards_and_workflow.py`
