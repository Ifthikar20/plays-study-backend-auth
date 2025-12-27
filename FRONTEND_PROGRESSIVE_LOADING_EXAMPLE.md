# Progressive Loading UI - Complete Implementation Example

## Step-by-Step Flow

### 1. Initial Session Creation

When the user uploads a file, you'll get this response **in 5-10 seconds**:

```typescript
// API Call
const response = await axios.post('/api/v1/study-sessions', {
  title: 'My Study Session',
  content: base64EncodedFile,
  progressive_load: true  // This is now the default
});

// Response (returns quickly!)
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "title": "Cloud Architecture Study",
  "extractedTopics": [
    {
      "id": "topic-1",
      "title": "Load Balancing",
      "questions": [/* 15 questions */]  // ✅ Has questions (generated immediately)
    },
    {
      "id": "topic-2",
      "title": "Auto Scaling",
      "questions": [/* 18 questions */]  // ✅ Has questions (generated immediately)
    },
    {
      "id": "topic-3",
      "title": "Database Replication",
      "questions": [/* 12 questions */]  // ✅ Has questions (generated immediately)
    },
    {
      "id": "topic-4",
      "title": "CDN Configuration",
      "questions": []  // ❌ No questions yet (will load progressively)
    },
    {
      "id": "topic-5",
      "title": "Monitoring & Logging",
      "questions": []  // ❌ No questions yet (will load progressively)
    }
    // ... 6 more topics without questions
  ],
  "progressiveLoad": true,     // 🔔 Progressive loading is enabled
  "questionsRemaining": 11,    // 🔔 11 topics still need questions
  "progress": 0
}
```

**Key Points:**
- Response arrives in **5-10 seconds** (not 30-60 seconds!)
- First 3 topics have questions ready to use
- Remaining 11 topics have empty `questions` arrays
- `questionsRemaining: 11` tells you how many topics need loading

---

### 2. Show Loading Indicator Immediately

**React Component Example:**

```typescript
// components/StudySessionPage.tsx
import { useState, useEffect } from 'react';
import axios from 'axios';

interface Session {
  id: string;
  title: string;
  extractedTopics: Topic[];
  progressiveLoad: boolean;
  questionsRemaining: number;
}

const StudySessionPage = () => {
  const [session, setSession] = useState<Session | null>(null);
  const [questionsRemaining, setQuestionsRemaining] = useState(0);
  const [loadingProgress, setLoadingProgress] = useState(0);

  // Step 1: Create session (fast - 5-10s)
  const createSession = async (file: File) => {
    const response = await axios.post('/api/v1/study-sessions', {
      title: file.name,
      content: await fileToBase64(file),
      progressive_load: true
    });

    const data: Session = response.data;

    setSession(data);
    setQuestionsRemaining(data.questionsRemaining || 0);

    // Step 2: Start loading remaining questions in background
    if (data.questionsRemaining > 0) {
      loadRemainingQuestions(data.id, data.extractedTopics.length);
    }
  };

  // Step 3: Poll for remaining questions
  const loadRemainingQuestions = async (sessionId: string, totalTopics: number) => {
    while (questionsRemaining > 0) {
      // Wait 2 seconds between requests
      await new Promise(resolve => setTimeout(resolve, 2000));

      try {
        // Call /generate-more-questions endpoint
        const response = await axios.post(
          `/api/v1/study-sessions/${sessionId}/generate-more-questions`
        );

        const updatedSession: Session = response.data;

        // Update session with newly loaded questions
        setSession(updatedSession);
        setQuestionsRemaining(updatedSession.questionsRemaining || 0);

        // Calculate progress percentage
        const loaded = totalTopics - (updatedSession.questionsRemaining || 0);
        const progress = (loaded / totalTopics) * 100;
        setLoadingProgress(progress);

        console.log(`📊 Progress: ${loaded}/${totalTopics} topics loaded (${Math.round(progress)}%)`);

        // Stop when all questions are loaded
        if (updatedSession.questionsRemaining === 0) {
          console.log('✅ All questions loaded!');
          break;
        }
      } catch (error) {
        console.error('Failed to load more questions:', error);
        // Retry after 5 seconds on error
        await new Promise(resolve => setTimeout(resolve, 5000));
      }
    }
  };

  return (
    <div>
      {/* Show the skill tree immediately */}
      {session && (
        <>
          <h1>{session.title}</h1>

          {/* 🔔 THIS IS THE LOADING INDICATOR */}
          {questionsRemaining > 0 && (
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-4">
              <div className="flex items-center gap-2">
                <Spinner className="w-4 h-4 animate-spin" />
                <p className="text-sm font-medium">
                  Loading more questions... ({questionsRemaining} remaining)
                </p>
              </div>

              {/* Progress bar */}
              <div className="mt-2 w-full bg-gray-200 rounded-full h-2">
                <div
                  className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                  style={{ width: `${loadingProgress}%` }}
                />
              </div>

              <p className="text-xs text-gray-600 mt-1">
                {Math.round(loadingProgress)}% complete
              </p>
            </div>
          )}

          {/* Render workflow/skill-tree */}
          <WorkflowCanvas topics={session.extractedTopics} />
        </>
      )}
    </div>
  );
};
```

---

### 3. How Detection Works

**The key is checking `questionsRemaining` in the API response:**

```typescript
// After creating session
if (response.data.questionsRemaining > 0) {
  // 🔔 SHOW LOADING INDICATOR
  // Questions are still loading in background
  setShowLoadingIndicator(true);
  setRemainingCount(response.data.questionsRemaining);
} else {
  // ✅ ALL QUESTIONS LOADED
  // No need to show loading indicator
  setShowLoadingIndicator(false);
}
```

**During polling:**

```typescript
// Every 2 seconds, call /generate-more-questions
const updatedSession = await generateMoreQuestions(sessionId);

// Update remaining count
setRemainingCount(updatedSession.questionsRemaining);

// Check if done
if (updatedSession.questionsRemaining === 0) {
  // ✅ HIDE LOADING INDICATOR
  setShowLoadingIndicator(false);
  stopPolling();
}
```

---

### 4. Visual Timeline

```
Time 0s: User uploads file
  ↓
Time 5s: API returns session with first 3 topics having questions
  ↓
  UI shows: "Loading more questions... (11 remaining)" + Progress bar at 21%
  ↓
Time 7s: Frontend calls /generate-more-questions (first poll)
  ↓
Time 12s: Response comes back with 2 more topics loaded
  ↓
  UI updates: "Loading more questions... (9 remaining)" + Progress bar at 36%
  ↓
Time 14s: Frontend calls /generate-more-questions (second poll)
  ↓
Time 19s: Response comes back with 2 more topics loaded
  ↓
  UI updates: "Loading more questions... (7 remaining)" + Progress bar at 50%
  ↓
... (continues every 2 seconds)
  ↓
Time 45s: Final poll returns questionsRemaining: 0
  ↓
  UI hides loading indicator ✅
```

---

### 5. Complete Custom Hook (Recommended)

**Create a reusable hook:**

```typescript
// hooks/useProgressiveLoading.ts
import { useState, useEffect } from 'react';
import axios from 'axios';

export const useProgressiveLoading = (
  sessionId: string,
  initialQuestionsRemaining: number,
  totalTopics: number
) => {
  const [questionsRemaining, setQuestionsRemaining] = useState(initialQuestionsRemaining);
  const [progress, setProgress] = useState(0);
  const [isLoading, setIsLoading] = useState(initialQuestionsRemaining > 0);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // If no questions remaining, don't poll
    if (questionsRemaining === 0) {
      setIsLoading(false);
      return;
    }

    let isMounted = true;

    const pollForQuestions = async () => {
      while (isMounted && questionsRemaining > 0) {
        // Wait 2 seconds between polls
        await new Promise(resolve => setTimeout(resolve, 2000));

        try {
          const response = await axios.post(
            `/api/v1/study-sessions/${sessionId}/generate-more-questions`
          );

          if (!isMounted) break;

          const remaining = response.data.questionsRemaining || 0;
          setQuestionsRemaining(remaining);

          // Calculate progress
          const loaded = totalTopics - remaining;
          const progressPercent = (loaded / totalTopics) * 100;
          setProgress(progressPercent);

          if (remaining === 0) {
            setIsLoading(false);
            break;
          }
        } catch (err) {
          console.error('Failed to load questions:', err);
          setError('Failed to load some questions. Retrying...');
          // Retry after 5 seconds on error
          await new Promise(resolve => setTimeout(resolve, 5000));
        }
      }
    };

    pollForQuestions();

    // Cleanup
    return () => {
      isMounted = false;
    };
  }, [sessionId, initialQuestionsRemaining, totalTopics]);

  return {
    isLoading,
    questionsRemaining,
    progress,
    error
  };
};
```

**Usage:**

```typescript
const StudySessionPage = ({ sessionId, session }: Props) => {
  const { isLoading, questionsRemaining, progress, error } = useProgressiveLoading(
    sessionId,
    session.questionsRemaining,
    session.extractedTopics.length
  );

  return (
    <>
      {/* Loading Indicator - Automatically shows/hides */}
      {isLoading && (
        <div className="alert alert-info">
          <Spinner />
          <span>Loading more questions... ({questionsRemaining} remaining)</span>
          <progress value={progress} max={100} />
          {error && <p className="text-red-500">{error}</p>}
        </div>
      )}

      <WorkflowCanvas topics={session.extractedTopics} />
    </>
  );
};
```

---

## 6. Testing the Implementation

**Test Scenario 1: Fast Upload (3 topics)**
- Creates session
- All 3 topics get questions immediately
- `questionsRemaining: 0`
- **No loading indicator shown** ✅

**Test Scenario 2: Large Upload (14 topics)**
- Creates session in 5-10s
- First 3 topics have questions
- `questionsRemaining: 11`
- **Loading indicator appears immediately**
- Polls every 2 seconds
- Progress bar updates from 21% → 36% → 50% → ... → 100%
- Loading indicator disappears when done ✅

**Test Scenario 3: Network Error**
- Loading fails midway
- Shows error message
- Retries after 5 seconds
- Continues loading ✅

---

## 7. Key Detection Points

**How do you KNOW questions are loading?**

```typescript
// 1️⃣ Check initial response
if (session.progressiveLoad && session.questionsRemaining > 0) {
  // Questions are still loading!
  showLoadingIndicator = true;
}

// 2️⃣ Check during polling
const response = await generateMoreQuestions(sessionId);
if (response.questionsRemaining > 0) {
  // Still loading...
  keepPolling = true;
} else {
  // Done!
  hideLoadingIndicator = true;
}

// 3️⃣ Check each topic individually
session.extractedTopics.forEach(topic => {
  if (topic.questions.length === 0) {
    // This topic is still loading
    disableTopicButton(topic.id);
  } else {
    // This topic is ready!
    enableTopicButton(topic.id);
  }
});
```

---

## Summary

**Detection Logic:**
```typescript
const shouldShowLoadingIndicator = session.questionsRemaining > 0;
const remainingText = `${session.questionsRemaining} remaining`;
const progressPercent = ((totalTopics - session.questionsRemaining) / totalTopics) * 100;
```

**Polling Logic:**
```typescript
setInterval(async () => {
  const updated = await generateMoreQuestions(sessionId);
  if (updated.questionsRemaining === 0) {
    stopPolling();
    hideIndicator();
  }
}, 2000);
```

**That's it!** The backend sends you `questionsRemaining` in every response. When it's > 0, show the indicator. When it reaches 0, hide it.
