# OpenEnv Hackathon: Student-Centric Domain Triage

Based on your goal for **relatable problem statements** where you have high intuition, here is the official triage of our 4 student-centric ideas.

---

| Rank | Domain | Why it Wins | Technical Ease | Relatability |
| :--- | :--- | :--- | :--- | :--- |
| **#1** | **Campus Placement Matcher** | **High Impact.** Judges love "AI for Jobs." Very easy to explain and demo. | **High.** Logic is pure string/float matching. | **10/10.** You know exactly what a good CV looks like. |
| **#2** | **Peer-Review Bias Detector** | **Novelty.** Most teams won't think of this. Shows very clever reasoning. | **Medium.** Needs a bit more logic for "outlier" detection. | **9/10.** You've definitely seen "that one lazy grader." |
| **#3** | **Course Scheduler** | **Algorithm Heavy.** Shows high technical depth. | **Low.** Solving time-clashes in pure Python is a bit tricky. | **8/10.** Relatable but can be frustrating to code. |
| **#4** | **Scholarship Triage** | **Social Impact.** Very noble project. | **High.** Essentially a rules-based ranking engine. | **7/10.** Relatable but maybe "less fun" than the matching/bias ideas. |

---

### Deep Dive: Why "Campus Placement Matcher" is the Smartest Choice

1.  **Complexity Scaling:** We can start with a simple "Skills vs Job" logic (Easy Task), then move to "Skill Gaps & CGPA Cutoffs" (Medium Task), and finally "Mass Hiring Filter with specific quotas" (Hard Task). This fits the OpenEnv **Progressive Difficulty** rule perfectly.
2.  **Reward Logic:** You can easily reward an AI `+0.8` for identifying the right fit and `+0.2` for correctly identifying the "Missing Skill." This satisfies the **Partial Credit** judging rule.
3.  **No Hallucinations:** Unlike medical triage (where we aren't doctors), in Placement Matching, you are the expert. You'll know immediately if the agent's reward is wrong.

**Shall we lock in the "Campus Placement Matcher"?** If yes, I will run `openenv init placement_env` and we can start designing the first `StudentProfile` model.
