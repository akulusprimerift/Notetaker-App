# Illustrative computer science notes

This manually authored example accompanies the [Phase 2 student experience](phase-2-student-experience.md). All lecture text and timestamps below are synthetic. There is no source recording, executed model, or measured transcription result. The example demonstrates the desired content and source presentation; it is not a Phase 4 evaluation dataset.

## Synthetic source transcript, revision 1

**S1, 00:00–00:30:** "Binary search finds a target in a sorted array. We will use a half-open search interval: lo is included, hi is excluded. Start lo at zero and hi at the array length. While lo is less than hi, compute mid as lo plus the floor of half the difference between hi and lo. If the value at mid equals the target, return mid. If it is smaller, set lo to mid plus one. Otherwise set hi to mid. If the loop ends without a match, return minus one."

**S2, 00:30–01:00:** "For the array two, five, eight, twelve, sixteen, look for twelve. Initially lo is zero and hi is five. The first mid is two; eight is too small, so lo becomes three. Next mid is four; sixteen is too large, so hi becomes four. Next mid is three, and twelve matches. Return index three."

**S3, 01:00–01:20:** "With constant-time array indexing, each iteration roughly halves the remaining interval. Worst-case time is logarithmic in n. This iterative version uses constant auxiliary space. Do not include sorting in that search-only runtime. If your input is not sorted, you cannot just apply this algorithm as stated."

**S4, 01:20–01:35:** "Duplicates are allowed, but this version returns whichever match it encounters. It does not promise the first occurrence. For the exam, keep track of whether hi is included or excluded. The invariant written on the board explains why the updates are safe."

## Example detailed notes, revision 1

Course: Algorithms and data structures

Topic: Binary search with a half-open interval

Status: Notes for the synthetic excerpt only. One missing-visual issue needs review.

### Purpose and precondition

**Lecture paraphrase.** Binary search locates a target in a sorted array. This version maintains the search interval `[lo, hi)`: `lo` is included and `hi` is excluded. The algorithm must not be applied to unsorted input as stated. Sources: [S1], [S3].

### Procedure

**Lecture paraphrase, expressed as pseudocode from the dictated steps.** This is not a verbatim board transcription. Source: [S1].

```text
lo = 0
hi = length(array)
while lo < hi:
    mid = lo + floor((hi - lo) / 2)
    if array[mid] == target:
        return mid
    if array[mid] < target:
        lo = mid + 1
    else:
        hi = mid
return -1
```

### Worked example

**Lecture paraphrase.** Find `12` in `[2, 5, 8, 12, 16]`. Indices start at zero. Source: [S2].

| Step | Interval before comparison | mid | Value | Result |
| --- | --- | --- | --- | --- |
| 1 | [0, 5) | 2 | 8 | Too small; set lo to 3. |
| 2 | [3, 5) | 4 | 16 | Too large; set hi to 4. |
| 3 | [3, 4) | 3 | 12 | Match; return index 3. |

### Reasoning and complexity

**Lecture paraphrase.** Each iteration roughly halves the remaining interval. With constant-time array indexing, the search has worst-case time `O(log n)` and this iterative version uses `O(1)` auxiliary space. These claims describe the search; sorting cost is excluded. Source: [S3].

### Qualifications and professor emphasis

- **Lecture paraphrase:** Duplicates are allowed, but the returned index is not guaranteed to be the first occurrence. Source: [S4].
- **Exact quote:** "For the exam, keep track of whether hi is included or excluded." Source: [S4].
- **Missing visual evidence:** The professor referred to a board invariant. Its wording and proof are not available in this transcript. Do not fill in a proof and attribute it to the lecture. Source: [S4].

### Source appendix presentation

In an exported note, each label above must resolve to a source appendix entry containing the transcript revision, interval, and cited excerpt, as illustrated in the synthetic transcript section. A real app may also offer playback when source audio is retained. This design example has no audio and must not display a working-playback claim.

## What this example is intended to verify in design review

- The notes preserve intermediate reasoning and example steps rather than reducing the lecture to "binary search is fast."
- Boundary conventions, sorted-input requirements, sorting-cost exclusions, and duplicate behavior survive condensation.
- Pseudocode derived from spoken instructions is distinguished from an exact source quotation.
- Exam emphasis is attributable, and unavailable board content remains visibly unavailable.
- No extra AI explanation is required to make the detailed notes useful. If an explanation is added later, it must have its own label and must not inherit lecture attribution.
