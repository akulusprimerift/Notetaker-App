# Broker outage synthetic speech — no microphone

Generated study notes · Revision 2

Model: qwen3:4b

AI-generated; check important claims against the sources.

## Binary Search Fundamentals

Evidence: lecture paraphrase

Binary search is a search algorithm that operates on a sorted array to efficiently locate a target value by repeatedly dividing the search interval in half\.

Sources: [1], [2]

## Search Procedure

Evidence: lecture paraphrase

The binary search procedure maintains a lower bound and an upper bound that define the current search interval\. At each iteration, the algorithm compares the target value with the middle element of the interval\. If the target matches, it returns the position\. If the target is smaller, the upper bound is adjusted to the position before the middle; otherwise, the lower bound is adjusted to the position after the middle\. This process continues until the target is found or the interval is exhausted\.

Sources: [3], [4], [5], [6], [7]

## Loop Invariant and Time Complexity

Evidence: lecture paraphrase

The loop invariant ensures that any matching element, if it exists, remains within the current search interval\. This invariant guarantees that the algorithm will find the target if it is present\. The time complexity of binary search is logarithmic \(O\(log n\)\), as each iteration reduces the search space by approximately half\. This is significantly more efficient than a linear scan, which may inspect every element in the worst case\.

Sources: [8], [9], [10], [11]

## Edge Cases and Special Cases

Evidence: lecture paraphrase

For an empty array, binary search returns 'not found'\. When dealing with repeated values, the standard binary search may return any matching position, not necessarily the first occurrence\. To find the first occurrence of a value, the algorithm must continue searching toward the left after a match\.

Sources: [13], [14], [15]

## Review needed

- omitted: This generated draft did not use this passage; review the source for missing detail\. (source [12])

## Source appendix

### [1] Recording 1, 0.00–1.52 seconds

Source version: d9fbf615-0cb3-4be3-8248-3b254685e0d4

Binary search requires a sorted array\.

### [2] Recording 1, 2.24–3.60 seconds

Source version: 835d943e-9bf6-4d2c-b69c-38552f804f2e

Distinct elements alone are not sufficient\.

### [3] Recording 1, 4.28–6.60 seconds

Source version: 1c1a570a-5c80-42bc-b454-5c1a8fe034ca

We keep a lower bound and an upper bound on the remaining search interval\.

### [4] Recording 1, 7.20–9.46 seconds

Source version: 63e52c3b-c0fa-41fb-bc5c-38236997ce21

At each step, compare the target with the middle element\.

### [5] Recording 1, 10.10–11.68 seconds

Source version: b347cef9-f7eb-4eba-8a45-4cc7b6631818

If they are equal, return that position\.

### [6] Recording 1, 12.30–15.28 seconds

Source version: ab51a2c3-d171-47d8-87b1-d22f4d5d858e

If the target is smaller, move the upper bound to the position before the middle\.

### [7] Recording 1, 15.86–18.32 seconds

Source version: c10ef03a-7716-4a7c-a710-f40afc985bdc

Otherwise, move the lower bound to the position after the middle\.

### [8] Recording 1, 18.86–21.90 seconds

Source version: 645842d7-4b61-466c-b453-29ac9b9c64a9

The loop invariant is that any matching element must remain inside the search interval\.

### [9] Recording 1, 22.56–24.52 seconds

Source version: 5fe4dee9-160e-4008-bcfa-2fecd802dea4

Each iteration removes about half of the remaining candidates\.

### [10] Recording 1, 25.34–26.96 seconds

Source version: 1dc4dc7c-3094-432e-864d-0b7778469c58

Therefore the time complexity is logarithmic,

### [11] Recording 1, 27.26–31.64 seconds

Source version: 8dfc485c-11b2-4afb-8db4-9247cfd18660

and the iterative implementation uses constant extra space\. A linear scan is different, it

### [12] Recording 1, 31.64–36.16 seconds

Source version: 869abafa-d4cd-44e3-bd93-17a49c9af193

may inspect every element\. Do not confuse logarithmic time with constant time\. For an

### [13] Recording 1, 36.16–40.72 seconds

Source version: 09aa706e-7a7b-4f85-8459-b717740b9d53

empty array, return not found\. For repeated values, ordinary binary search may return

### [14] Recording 1, 40.72–44.92 seconds

Source version: eb326b81-ce8d-495c-8d7c-3449714df05d

any matching position, not necessarily the first\. Finding the first occurrence requires

### [15] Recording 1, 44.92–46.42 seconds

Source version: bb8c65e5-9133-4ff4-95ab-28d8dd05f447

continuing toward the left after a match\.
