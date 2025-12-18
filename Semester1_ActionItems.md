# ✅ Action Items from Kedziora

### 1. Clarify Data Representation
- Model tasks as **time series** rather than static snapshots to capture dynamic changes in CPU/IO intensity.
- Explore approaches like **Hidden Markov Models (HMM)** or similar state-based models to represent transitions between IO-bound and CPU-bound states.

### 2. Modeling Strategy
- Investigate **regression-based approaches** (continuous outputs for CPU and IO intensity) instead of categorical binning.
- Try **multi-class modeling** with combined CPU/IO states (e.g., 9 possible combinations) to capture correlations.
- Benchmark **larger models** (e.g., lightweight deep learning) for comparison, even if they break runtime constraints, to understand trade-offs.

### 3. Model Selection
- Consider **tree ensembles** (Random Forest, Gradient Boosted Trees) instead of a single decision tree for better performance.
- Compare performance and inference cost of these models against current decision tree and SVM approaches.

### 4. Overfitting vs. Generalization
- If the deployment context is narrow (e.g., 3D printing), **overfitting may be acceptable and even optimal**.
- If aiming for broader applicability, prioritize generalization—but recognize the trade-off.

### 5. Benchmarking Trade-offs
- Explicitly measure and report the **accuracy vs. runtime trade-off** for different models.
- Include **scheduler overhead impact on starvation metrics** in future evaluations.

---

# ✅ Action Items from Retert

### 1. Dynamic Classification
- Address the fact that processes can **switch between IO-bound and CPU-bound states** during execution.
- Consider localized statistics (e.g., idle time in recent intervals) rather than cumulative metrics since process start.

### 2. Feature Engineering
- When collapsing IO calls into bins, ensure features still capture meaningful distinctions.
- Explore adding **localized performance metrics** to improve dynamic adaptability.

### 3. Benchmarking
- Incorporate **scheduler overhead** into starvation measurements for a more realistic performance picture.

---

# ✅ Overall Next Steps
- **Experiment with time-series/state-based models** (e.g., HMM) and compare to static classification.
- **Try regression or multi-class approaches** for CPU/IO intensity prediction.
- **Benchmark advanced models** (tree ensembles, lightweight neural nets) for accuracy vs. runtime trade-offs.
- **Decide on deployment strategy**: overfit for specific systems or generalize for broader use cases.
- **Enhance benchmarking framework** to include overhead and starvation impact.
