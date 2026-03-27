# OpenEnv Hackathon: Master Idea Generation Prompt

Copy and paste the block below into any AI assistant (ChatGPT, Claude, Gemini, etc.) to generate high-quality, hackathon-ready project ideas.

---

### [START OF PROMPT]

**Role:** You are acting as a Senior AI Architect and RL Environment Designer.
**Mission:** Generate 5-8 high-impact, original project ideas for the **Meta PyTorch OpenEnv Hackathon**.

**Context:**
The goal is NOT to train an AI model. The goal is to build a **RL Environment (the "Gym")** using the **OpenEnv framework**. In this framework:
1. The **Environment** (Server) provides **Observations** (data) to an **Agent** (Client).
2. The **Agent** sends back **Actions**.
3. The **Environment** returns a **Reward** (float between 0.0 and 1.0) based on how "correct" the action was.
4. Communication happens via **WebSockets** (`/ws`) using a standard `reset()`, `step()`, `state` interface.

**Hard Constraints for Ideas:**
1. **Real-World Relevance:** No classic games (Chess, Tic-Tac-Toe, etc.). Must solve a practical problem (Healthcare, Logistics, DevTools, Finance, Education).
2. **Progressive Difficulty:** Each idea must have 3 distinct tasks (Easy, Medium, Hard) that increase in complexity.
3. **Partial Credit Rewards:** The reward function must NEVER be binary (0/1). It must provide a granular score (e.g., 0.5 for a partially correct answer).
4. **Pure Python Simulation:** The `step()` logic must run in pure Python (no external APIs, no GPUs in the simulation).
5. **Relatable for Students:** The problems should be ones that university students have first-hand experience with.

**For each idea, provide:**
1. **Domain Name & Hook:** A catchy, professional name.
2. **Problem Statement:** What real-world student/campus/academic problem are we solving?
3. **Observation Space (JSON Schema):** What does the AI see? (e.g., Student Profile, Course Data, Financial Record).
4. **Action Space (JSON Schema):** What can the AI do? (e.g., Assign a Triage Level, Select a Course, Flag a Bias).
5. **Reward Logic:** A detailed formula for how the environment calculates the `float` score (0.0 to 1.0).
6. **Task Definitions:**
    - **Easy:** Solvable by random guess ~30% of the time.
    - **Medium:** Requires basic logic/heuristics.
    - **Hard:** Requires deep reasoning/planning.
7. **Judging Advantage:** Why would this win (Novelty, Social Impact, or Technical Depth)?

**Style Tone:** Professional, innovative, and technically precise. Focus on ideas where a human can easily tell what is "right" or "wrong" based on intuition.

### [END OF PROMPT]
