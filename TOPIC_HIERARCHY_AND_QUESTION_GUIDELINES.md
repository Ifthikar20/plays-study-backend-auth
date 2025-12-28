# Topic Hierarchy & Question Generation Guidelines

## Overview

This document defines the **strict requirements** for topic hierarchy structure and question generation in PlaysStudy. The goal is to ensure:

1. **Clear hierarchical flow** - Topic → Subtopic → Further Subtopic
2. **No overlapping subtopics** - Each subtopic is distinct and focused
3. **Sufficient questions per topic** - Every leaf node has 15-20 quality questions
4. **Proper organization** - Foundation first, building to advanced concepts

---

## 📊 Hierarchical Structure Rules

### Maximum Depth: 3 Levels

```
Level 1: Category (Container)
  └─ Level 2: Subtopic (Can be leaf or container)
       └─ Level 3: Further Subtopic (MUST be leaf - no deeper nesting)
```

**Examples:**

✅ **CORRECT - Good Hierarchy:**
```
Communication Skills (Category)
  ├─ Verbal Communication (Subtopic - can have questions)
  │   ├─ Active Listening (Leaf - 30 questions)
  │   ├─ Tone and Clarity (Leaf - 28 questions)
  │   └─ Presentation Skills (Leaf - 32 questions)
  │
  └─ Non-Verbal Communication (Subtopic - can have questions)
      ├─ Body Language (Leaf - 25 questions)
      ├─ Facial Expressions (Leaf - 27 questions)
      └─ Eye Contact (Leaf - 30 questions)
```

❌ **INCORRECT - Too Deep:**
```
Communication (Category)
  └─ Verbal (Subtopic)
      └─ Speech (Subtopic)
          └─ Pronunciation (Subtopic)  ❌ Level 4 - NOT ALLOWED!
              └─ Vowels (Subtopic)      ❌ Level 5 - NOT ALLOWED!
```

---

## 🚫 Preventing Overlapping Subtopics

### Rule 1: Distinct Focus

Each subtopic must have a **clear, distinct focus** without overlapping content.

✅ **CORRECT - No Overlap:**
```
Stress Management
  ├─ Stress Sources
  │   ├─ Work-Related Stress        (Different: workplace stressors)
  │   ├─ Personal Life Stress       (Different: relationships, family)
  │   └─ Financial Stress           (Different: money concerns)
  │
  └─ Stress Coping Strategies
      ├─ Problem-Focused Coping     (Different: addressing stressor)
      ├─ Emotion-Focused Coping     (Different: managing emotions)
      └─ Social Support Systems     (Different: relationships for coping)
```

❌ **INCORRECT - Overlapping:**
```
Stress Management
  ├─ Workplace Stress       ❌
  ├─ Job-Related Stress     ❌ OVERLAP with "Workplace Stress"
  ├─ Work Environment Stress ❌ OVERLAP with both above
  └─ Office Stress          ❌ OVERLAP with all above
```

### Rule 2: Hierarchical Containment

**Child topics must be CONTAINED within parent scope.**

✅ **CORRECT - Proper Containment:**
```
Emotional Intelligence (Parent)
  ├─ Self-Awareness         (Child - part of EI)
  ├─ Self-Management        (Child - part of EI)
  ├─ Social Awareness       (Child - part of EI)
  └─ Relationship Management (Child - part of EI)
```

❌ **INCORRECT - Not Contained:**
```
Emotional Intelligence (Parent)
  ├─ Self-Awareness         ✓ (part of EI)
  ├─ Time Management        ❌ NOT part of EI
  ├─ Self-Management        ✓ (part of EI)
  └─ Project Management     ❌ NOT part of EI
```

### Rule 3: Mutually Exclusive Categories

**Sibling topics at the same level must be mutually exclusive.**

✅ **CORRECT - Mutually Exclusive:**
```
Communication Types
  ├─ Verbal Communication    (Spoken words only)
  ├─ Non-Verbal Communication (Body language, gestures)
  └─ Written Communication   (Text, emails, documents)
```

❌ **INCORRECT - Not Mutually Exclusive:**
```
Communication Types
  ├─ Face-to-Face Communication  ❌ Includes verbal + non-verbal
  ├─ Verbal Communication        ❌ OVERLAP: F2F includes verbal
  └─ Body Language               ❌ OVERLAP: F2F includes body language
```

### Rule 4: Appropriate Granularity

**Topics should be granular enough for questions, but not so narrow they lack content.**

✅ **CORRECT - Appropriate Granularity:**
```
Memory Systems
  ├─ Working Memory        (30 questions possible: definition, capacity, examples)
  ├─ Long-Term Memory      (35 questions possible: types, encoding, retrieval)
  └─ Sensory Memory        (28 questions possible: duration, types, examples)
```

❌ **INCORRECT - Too Granular:**
```
Memory Systems
  ├─ Working Memory
  │   ├─ Working Memory Definition      ❌ Too narrow (only 1-2 questions)
  │   ├─ Working Memory Duration        ❌ Too narrow (only 1-2 questions)
  │   └─ Working Memory Examples        ❌ Too narrow (only 1-2 questions)
  └─ Long-Term Memory
      └─ Long-Term Memory Storage Time  ❌ Too narrow (only 1-2 questions)
```

---

## 📝 Question Generation Requirements

### Minimum Questions Per Leaf Topic

**EVERY leaf topic MUST have 15-20 high-quality questions.**

**Formula:**
```
Leaf Topic Questions = 15-20 questions
  ├─ Multiple Choice: All 15-20
  ├─ 4 plausible options each
  └─ Detailed explanations with source text
```

### Question Distribution by Topic Type

#### 1. Category Topics (Container with Children)

**Purpose:** Overview and synthesis questions

**Question Types:**
- Big-picture understanding
- Integration across subtopics
- Comparison between subtopics
- Synthesis questions

**Example:**
```
Topic: "Stress Management" (Category)
Subtopics: Stress Sources, Coping Mechanisms, Prevention

Sample Questions for Category:
1. "Which combination of stress management strategies is most effective?"
2. "How do different stress sources require different coping mechanisms?"
3. "What is the relationship between stress prevention and coping strategies?"
```

**Requirement:** 15-20 synthesis questions

#### 2. Leaf Topics (No Children)

**Purpose:** Deep, specific knowledge

**Question Types:**
- Definition questions
- Application questions
- Example-based questions
- Mechanism/process questions
- Comparison questions

**Example:**
```
Topic: "Problem-Focused Coping" (Leaf)

Sample Questions:
1. "What is the definition of problem-focused coping?"
2. "Which scenario demonstrates problem-focused coping?" (Example-based)
3. "When is problem-focused coping most appropriate?"
4. "Which of the following is NOT a problem-focused coping strategy?"
```

**Requirement:** 15-20 detailed questions

### Question Quality Standards

**Each Question Must Include:**

1. ✅ **Clear question text** (complete sentence, specific)
2. ✅ **Exactly 4 plausible options** (all seem correct to uninformed reader)
3. ✅ **Integer correctAnswer** (0, 1, 2, or 3)
4. ✅ **Detailed explanation** (why correct + why others wrong)
5. ✅ **Source text** (verbatim from study material with context)
6. ✅ **Source page** (if applicable, null otherwise)

**Example Question Structure:**
```json
{
  "question": "According to the SRRS, what stress score indicates an 80% chance of getting sick?",
  "options": [
    "Less than 150",
    "151-299",
    "300 or More",
    "500 or More"
  ],
  "correctAnswer": 2,
  "explanation": "The SRRS indicates that a score of 300 or more corresponds to an 80% chance of becoming ill due to stress. Scores below 150 indicate low chance, and 151-299 indicates 50% chance.",
  "sourceText": "Score Breakdown\n\n150 or Less\nLow chance of getting sick due to stress\n\n151 to 299\n50% chance of getting sick due to stress\n\n300 or More\n80% chance of getting sick due to stress",
  "sourcePage": null
}
```

---

## 🔄 Proper Topic Flow Guidelines

### Principle: Foundation → Application → Advanced

**Always organize topics from:**
1. **Foundational concepts** (definitions, basic principles)
2. **Application concepts** (how to use, examples)
3. **Advanced concepts** (complex interactions, synthesis)

**Example Flow:**

```
Psychology of Stress (Subject)
│
├─ 1. Understanding Stress (Foundation)
│   ├─ What is Stress (Definition)
│   ├─ Types of Stress (Categories)
│   └─ Stress Response Systems (Mechanisms)
│
├─ 2. Sources of Stress (Application)
│   ├─ Work-Related Stress
│   ├─ Personal Life Stress
│   └─ Environmental Stress
│
└─ 3. Managing Stress (Advanced)
    ├─ Coping Strategies
    ├─ Prevention Techniques
    └─ Building Resilience
```

### Principle: Specific → General (Alternative)

For some subjects, reverse order works better:

```
Communication Skills
│
├─ 1. Specific Skills (Concrete)
│   ├─ Active Listening
│   ├─ Eye Contact
│   └─ Tone of Voice
│
├─ 2. Communication Types (Categories)
│   ├─ Verbal Communication
│   └─ Non-Verbal Communication
│
└─ 3. Communication Theory (Abstract)
    └─ Communication Models
```

---

## 🎯 AI Prompt Requirements

### Current Topic Extraction Prompt

**Location:** `app/api/study_sessions.py:838-890`

**Key Requirements Already in Place:**
```python
1. Create approximately {num_categories} major categories
2. Within each category, break down into focused subtopics (2-3 levels maximum)
3. Prioritize QUALITY over excessive nesting
4. Each leaf node should support 15-20 quality questions
5. Clear titles and descriptions at ALL levels
6. Organize logically (foundational → advanced)
7. Approximately {initial_topics} total LEAF topics
8. Avoid unnecessary intermediate categories
9. Focus on core concepts first
10. Keep structure simple (2-3 levels maximum)
```

### Recommended Enhancement

**Add these rules to the AI prompt:**

```python
CRITICAL HIERARCHY RULES:
1. NO OVERLAPPING SUBTOPICS - Each subtopic must be distinct and mutually exclusive
   Example: Don't create both "Workplace Stress" and "Job-Related Stress" - they overlap!

2. PROPER CONTAINMENT - Child topics must be fully contained within parent scope
   Example: Under "Emotional Intelligence", don't include "Time Management"

3. APPROPRIATE GRANULARITY - Each leaf topic must support 15-20 quality questions
   Example: Don't create "Definition of X" as a topic - too narrow (only 1-2 questions)

4. SUBJECT FLOW - Organize within same subject domain
   Example: Don't mix "Math Concepts" with "History Events" under same category

5. VALIDATE BEFORE RETURNING:
   - Check each sibling pair for overlap
   - Ensure each leaf can generate 15-20 questions
   - Verify parent-child containment
   - Confirm proper depth (max 3 levels)
```

---

## 🧪 Validation Checklist

### Before Generating Questions, Verify:

**Hierarchy Structure:**
- [ ] Maximum depth is 3 levels
- [ ] All leaf topics have empty subtopics: `[]`
- [ ] All container topics have non-empty subtopics

**Distinctness:**
- [ ] No overlapping sibling topics
- [ ] Each topic has unique focus
- [ ] Mutually exclusive categories

**Containment:**
- [ ] All children fit within parent scope
- [ ] No cross-category contamination
- [ ] Logical parent-child relationships

**Granularity:**
- [ ] Each leaf topic can generate 15-20 questions
- [ ] Not too broad (unfocused)
- [ ] Not too narrow (insufficient content)

**Flow:**
- [ ] Foundation → Application → Advanced
- [ ] OR Specific → General (when appropriate)
- [ ] Logical progression within subject

**Questions:**
- [ ] 15-20 questions per leaf topic
- [ ] All questions have 4 options
- [ ] Detailed explanations
- [ ] Source text included
- [ ] No duplicate questions

---

## ❌ Common Mistakes to Avoid

### 1. Overlapping Siblings

**BAD:**
```json
{
  "title": "Communication",
  "subtopics": [
    {"title": "Verbal Communication"},
    {"title": "Spoken Communication"},  // OVERLAP: Same as verbal
    {"title": "Oral Communication"}     // OVERLAP: Same as verbal
  ]
}
```

**GOOD:**
```json
{
  "title": "Communication",
  "subtopics": [
    {"title": "Verbal Communication"},
    {"title": "Non-Verbal Communication"},
    {"title": "Written Communication"}
  ]
}
```

### 2. Improper Containment

**BAD:**
```json
{
  "title": "Psychology",
  "subtopics": [
    {"title": "Cognitive Psychology"},   // ✓ Psychology subtopic
    {"title": "Mathematical Logic"},     // ✗ NOT psychology
    {"title": "Social Psychology"}       // ✓ Psychology subtopic
  ]
}
```

**GOOD:**
```json
{
  "title": "Psychology",
  "subtopics": [
    {"title": "Cognitive Psychology"},
    {"title": "Social Psychology"},
    {"title": "Developmental Psychology"}
  ]
}
```

### 3. Too Deep Nesting

**BAD (4+ levels):**
```json
{
  "title": "Science",
  "subtopics": [{
    "title": "Biology",
    "subtopics": [{
      "title": "Cell Biology",
      "subtopics": [{
        "title": "Organelles",      // Level 4 - TOO DEEP!
        "subtopics": [{
          "title": "Mitochondria"   // Level 5 - TOO DEEP!
        }]
      }]
    }]
  }]
}
```

**GOOD (Max 3 levels):**
```json
{
  "title": "Biology",
  "subtopics": [{
    "title": "Cell Biology",
    "subtopics": [
      {"title": "Cell Structure", "subtopics": []},   // Level 3 - Leaf
      {"title": "Cell Functions", "subtopics": []},   // Level 3 - Leaf
      {"title": "Cell Division", "subtopics": []}     // Level 3 - Leaf
    ]
  }]
}
```

### 4. Insufficient Question Potential

**BAD (Too Narrow):**
```json
{
  "title": "Memory",
  "subtopics": [
    {"title": "Memory Definition"},        // Only 1-2 questions possible
    {"title": "Memory Duration"},          // Only 1-2 questions possible
    {"title": "Memory Types"}              // Only 1-2 questions possible
  ]
}
```

**GOOD (Appropriate Scope):**
```json
{
  "title": "Memory",
  "subtopics": [
    {"title": "Working Memory"},           // 15-20 questions possible
    {"title": "Long-Term Memory"},         // 15-20 questions possible
    {"title": "Sensory Memory"}            // 15-20 questions possible
  ]
}
```

---

## 📋 Implementation Checklist

### For Backend Developers:

- [ ] Update AI prompt to include NO OVERLAP rule
- [ ] Update AI prompt to require 15-20 questions per leaf
- [ ] Add validation after topic extraction to check for overlaps
- [ ] Enforce max depth of 3 levels
- [ ] Log warnings for topics with insufficient questions
- [ ] Add post-processing to merge overlapping topics

### For Frontend Developers:

- [ ] Display hierarchy clearly (indent levels)
- [ ] Show question counts per topic
- [ ] Highlight leaf vs. container topics
- [ ] Indicate quiz availability (workflow stages)
- [ ] Allow navigation through hierarchy

---

## 🔧 Code References

### Topic Extraction Prompt

**File:** `app/api/study_sessions.py`
**Lines:** 838-890
**Function:** `create_study_session_with_ai()`

### Recursive Topic Creation

**File:** `app/api/study_sessions.py`
**Lines:** 976-1060
**Function:** `create_topics_recursive()`

### Hierarchy Building

**File:** `app/api/study_sessions.py`
**Lines:** 43-130
**Function:** `build_topic_hierarchy()`

---

## 📊 Examples of Perfect Hierarchies

### Example 1: Business Communication

```
Business Communication (Subject)
│
├─ Written Communication (Category)
│   ├─ Email Etiquette (Leaf - 30Q)
│   ├─ Report Writing (Leaf - 28Q)
│   └─ Memo Writing (Leaf - 25Q)
│
├─ Verbal Communication (Category)
│   ├─ Meeting Facilitation (Leaf - 32Q)
│   ├─ Presentation Skills (Leaf - 30Q)
│   └─ Active Listening (Leaf - 27Q)
│
└─ Non-Verbal Communication (Category)
    ├─ Body Language (Leaf - 29Q)
    ├─ Facial Expressions (Leaf - 26Q)
    └─ Personal Space (Leaf - 25Q)
```

**Why This Works:**
- ✅ Max 3 levels
- ✅ No overlapping categories (Written vs. Verbal vs. Non-Verbal)
- ✅ Each leaf has 25+ questions
- ✅ Clear containment (all children fit parent)
- ✅ Logical flow (written → verbal → non-verbal)

### Example 2: Stress Psychology

```
Stress and Wellness (Subject)
│
├─ Understanding Stress (Category - Foundation)
│   ├─ Definition and Types (Leaf - 28Q)
│   ├─ Biological Response (Leaf - 32Q)
│   └─ Measurement Tools (Leaf - 25Q)
│
├─ Sources of Stress (Category - Application)
│   ├─ Workplace Stressors (Leaf - 30Q)
│   ├─ Personal Life Stressors (Leaf - 27Q)
│   └─ Environmental Factors (Leaf - 26Q)
│
└─ Stress Management (Category - Advanced)
    ├─ Coping Mechanisms (Subtopic)
    │   ├─ Problem-Focused Coping (Leaf - 29Q)
    │   └─ Emotion-Focused Coping (Leaf - 28Q)
    │
    └─ Prevention Strategies (Subtopic)
        ├─ Lifestyle Changes (Leaf - 30Q)
        └─ Social Support (Leaf - 27Q)
```

**Why This Works:**
- ✅ Foundation → Application → Advanced flow
- ✅ No overlap (Understanding vs. Sources vs. Management)
- ✅ Proper containment (Coping and Prevention under Management)
- ✅ All leaf topics have 25+ questions
- ✅ Clear, distinct focus for each topic

---

## 🎯 Summary

### Key Principles:

1. **Max 3 Levels** - No deeper nesting allowed
2. **No Overlap** - Sibling topics must be mutually exclusive
3. **Proper Containment** - Children must fit within parent scope
4. **15-20 Questions** - Every leaf topic must support this many
5. **Logical Flow** - Foundation → Application → Advanced

### Quality Checks:

Before finalizing any topic hierarchy:
1. Check for overlapping siblings
2. Verify parent-child containment
3. Confirm max depth of 3
4. Ensure each leaf can generate 15-20 questions
5. Validate logical progression

### Remember:

> **Quality over Quantity**
>
> It's better to have 5 well-defined, distinct topics with 30 quality questions each
> than 20 overlapping, poorly-scoped topics with 10 mediocre questions each.

---

**Last Updated:** 2025-12-27
**Related Documentation:**
- `FLASHCARD_COMPLETION_AND_PROGRESSIVE_LOADING.md` - Backend progressive loading
- `SSE_REAL_TIME_UPDATES_FRONTEND.md` - Frontend SSE implementation
