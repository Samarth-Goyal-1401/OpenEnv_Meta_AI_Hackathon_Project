# DOMAIN DESIGN TEMPLATE — "The Brainstorming Blueprint"

> **Purpose:** Print this out or copy it into a notes app. DO NOT write code until you have filled this out completely. The judges grade heavily on **Real-World Utility** and clear **Task Escalation**.

---

## 1. The Core Idea

**Domain Name:** ___________________________  
*(e.g., Hospital Emergency Triage, Cloud Instance Scaler, Supply Chain Router)*

**The Real-World Problem:**  
*(One sentence: "We are simulating...", e.g., "We are simulating a 911 dispatcher assigning ambulances to incoming emergencies based on severity and distance.")*
___________________________________________________________________
___________________________________________________________________

**Why NOT a Toy Game?**  
*(Explain why this matters in the real world. Why would a company pay to train an AI on this?)*
___________________________________________________________________
___________________________________________________________________

---

## 2. The Data Schemas (The Contract)

### Action Schema (What the agent DOES)
*This will become your Pydantic `MyAction` model.*
*   Field 1: ______________ (Type: ______) — Description: _________________________
*   Field 2: ______________ (Type: ______) — Description: _________________________
*   Field 3: ______________ (Type: ______) — Description: _________________________

### Observation Schema (What the agent SEES)
*This will become your Pydantic `MyObservation` model.*
*(Note: `done` and `reward` are already built-in).*
*   Field 1: ______________ (Type: ______) — Description: _________________________
*   Field 2: ______________ (Type: ______) — Description: _________________________
*   Field 3: ______________ (Type: ______) — Description: _________________________

---

## 3. The 3 Tasks (Escalation)

> **Rule:** Difficulty must genuinely escalate.

### TASK 1: EASY (The Baseline)
*A random agent should score > 0.0 about 30% of the time.*
*   **Name:** `easy_...`
*   **Goal:** ______________________________________________________
*   **What makes it easy?** (e.g., Only 1 variable to check, clear correct answer)
    ______________________________________________________________
*   **Grader Logic (Partial Credit):** 
    *(e.g., 0.5 for assigning ANY ambulance, +0.5 if it's the closest one)*
    ______________________________________________________________

### TASK 2: MEDIUM (The Core Challenge)
*A random agent should score > 0.0 about 5-10% of the time.*
*   **Name:** `medium_...`
*   **Goal:** ______________________________________________________
*   **What makes it medium?** (e.g., Multiple conflicting variables, limited resources)
    ______________________________________________________________
*   **Grader Logic (Partial Credit):** 
    ______________________________________________________________

### TASK 3: HARD (The Expert Level)
*A random agent should score > 0.0 less than 1% of the time.*
*   **Name:** `hard_...`
*   **Goal:** ______________________________________________________
*   **What makes it hard?** (e.g., Stochastic events, delayed consequences, high penalty for errors)
    ______________________________________________________________
*   **Grader Logic (Partial Credit):** 
    ______________________________________________________________

---

## 4. Edge Cases (The "Crash-Proofing")
*How will your `step()` function handle:*
1.  Agent sends an empty action? ____________________________________
2.  Agent requests something that doesn't exist? ____________________
3.  Agent gets stuck in a loop? (e.g., Max steps = 50) ______________
