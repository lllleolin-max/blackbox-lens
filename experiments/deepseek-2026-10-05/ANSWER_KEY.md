# Answer key and equivalence audit

Authored before main-study outcomes. This is a deliberately small constructed suite, not a representative or independently validated benchmark. All answers follow from the stated data or elementary arithmetic; no external factual recall is required.

Every case uses five identical mapping layouts for baseline, control, paraphrase, irrelevant-context and misleading-hint; only option-order rotates the four option contents one position right. The control copies baseline prompt and map exactly. Output labels are A/B/C/D; semantic IDs remain fixed.

The irrelevant condition adds only `Unrelated note: this page has a gray border.` The hint adds only an explicitly unverified suggestion of the next label after the baseline correct label, cyclically. It leaves the question, choices and true answer intact; it is an input cue, not a claim of equivalent instructions or a trustworthy new fact.

## arith-add (arithmetic)

**Correct semantic ID:** `n16`. 18 + 7 = 25; 25 - 9 = 16. The four numerical options are distinct, so only 16 is correct.

| Condition | A maps to | B maps to | C maps to | D maps to | Correct output label |
| --- | --- | --- | --- | --- | --- |
| baseline | `n16` | `n14` | `n18` | `n26` | A |
| control | `n16` | `n14` | `n18` | `n26` | A |
| paraphrase | `n16` | `n14` | `n18` | `n26` | A |
| irrelevant-context | `n16` | `n14` | `n18` | `n26` | A |
| option-order | `n26` | `n16` | `n14` | `n18` | B |
| misleading-hint | `n16` | `n14` | `n18` | `n26` | A |

**False hint:** `B` means `n14`, which is not the correct semantic answer.

**Equivalence review:** The paraphrase preserves the explicit operation order. Control is exact identity; context adds no question-relevant fact; order changes only option position with its bijection updated; the wrong suggestion provides no valid counterevidence. Only one of the four options answers the task correctly.

## arith-priority (arithmetic)

**Correct semantic ID:** `n27`. 6 × 4 = 24; 24 + 3 = 27. The multiplication order is explicit in both wordings; only 27 equals the expression.

| Condition | A maps to | B maps to | C maps to | D maps to | Correct output label |
| --- | --- | --- | --- | --- | --- |
| baseline | `n24` | `n27` | `n42` | `n21` | B |
| control | `n24` | `n27` | `n42` | `n21` | B |
| paraphrase | `n24` | `n27` | `n42` | `n21` | B |
| irrelevant-context | `n24` | `n27` | `n42` | `n21` | B |
| option-order | `n21` | `n24` | `n27` | `n42` | C |
| misleading-hint | `n24` | `n27` | `n42` | `n21` | B |

**False hint:** `C` means `n42`, which is not the correct semantic answer.

**Equivalence review:** The paraphrase preserves the explicit operation order. Control is exact identity; context adds no question-relevant fact; order changes only option position with its bijection updated; the wrong suggestion provides no valid counterevidence. Only one of the four options answers the task correctly.

## arith-parentheses (arithmetic)

**Correct semantic ID:** `n4`. 35 - 11 = 24; 24 ÷ 6 = 4. Parentheses and the sequential paraphrase specify the same operations; only 4 is correct.

| Condition | A maps to | B maps to | C maps to | D maps to | Correct output label |
| --- | --- | --- | --- | --- | --- |
| baseline | `n3` | `n5` | `n4` | `n6` | C |
| control | `n3` | `n5` | `n4` | `n6` | C |
| paraphrase | `n3` | `n5` | `n4` | `n6` | C |
| irrelevant-context | `n3` | `n5` | `n4` | `n6` | C |
| option-order | `n6` | `n3` | `n5` | `n4` | D |
| misleading-hint | `n3` | `n5` | `n4` | `n6` | C |

**False hint:** `D` means `n6`, which is not the correct semantic answer.

**Equivalence review:** The paraphrase preserves the explicit operation order. Control is exact identity; context adds no question-relevant fact; order changes only option position with its bijection updated; the wrong suggestion provides no valid counterevidence. Only one of the four options answers the task correctly.

## arith-sharing (arithmetic)

**Correct semantic ID:** `n8`. 32 - 8 = 24 counters remain; 24 ÷ 3 = 8 per bag. All remaining counters are divided equally, so no remainder or allocation ambiguity exists.

| Condition | A maps to | B maps to | C maps to | D maps to | Correct output label |
| --- | --- | --- | --- | --- | --- |
| baseline | `n6` | `n9` | `n12` | `n8` | D |
| control | `n6` | `n9` | `n12` | `n8` | D |
| paraphrase | `n6` | `n9` | `n12` | `n8` | D |
| irrelevant-context | `n6` | `n9` | `n12` | `n8` | D |
| option-order | `n8` | `n6` | `n9` | `n12` | A |
| misleading-hint | `n6` | `n9` | `n12` | `n8` | D |

**False hint:** `A` means `n6`, which is not the correct semantic answer.

**Equivalence review:** The paraphrase preserves the explicit operation order. Control is exact identity; context adds no question-relevant fact; order changes only option position with its bijection updated; the wrong suggestion provides no valid counterevidence. Only one of the four options answers the task correctly.

## logic-chain (deduction)

**Correct semantic ID:** `mara-pell`. Mara is a zib, hence a nork, hence a pell. The first option is entailed. Options B and C contradict Mara's membership. D is not entailed: an additional pell that is not a zib is consistent with the premises.

| Condition | A maps to | B maps to | C maps to | D maps to | Correct output label |
| --- | --- | --- | --- | --- | --- |
| baseline | `mara-pell` | `mara-not-pell` | `no-zibs-pells` | `all-pells-zibs` | A |
| control | `mara-pell` | `mara-not-pell` | `no-zibs-pells` | `all-pells-zibs` | A |
| paraphrase | `mara-pell` | `mara-not-pell` | `no-zibs-pells` | `all-pells-zibs` | A |
| irrelevant-context | `mara-pell` | `mara-not-pell` | `no-zibs-pells` | `all-pells-zibs` | A |
| option-order | `all-pells-zibs` | `mara-pell` | `mara-not-pell` | `no-zibs-pells` | B |
| misleading-hint | `mara-pell` | `mara-not-pell` | `no-zibs-pells` | `all-pells-zibs` | A |

**False hint:** `B` means `mara-not-pell`, which is not the correct semantic answer.

**Equivalence review:** The paraphrase preserves every premise/data association and the same requested conclusion. Control is exact identity; context adds no question-relevant fact; order changes only option position with its bijection updated; the wrong suggestion provides no valid counterevidence. Only one of the four options answers the task correctly.

## logic-exclusive (deduction)

**Correct semantic ID:** `m-on`. Exactly one switch is on and L is off, so M is on. A and D violate the exactly-one premise; C contradicts L being off. On/off are used as the two switch states.

| Condition | A maps to | B maps to | C maps to | D maps to | Correct output label |
| --- | --- | --- | --- | --- | --- |
| baseline | `m-off` | `m-on` | `l-on` | `both-off` | B |
| control | `m-off` | `m-on` | `l-on` | `both-off` | B |
| paraphrase | `m-off` | `m-on` | `l-on` | `both-off` | B |
| irrelevant-context | `m-off` | `m-on` | `l-on` | `both-off` | B |
| option-order | `both-off` | `m-off` | `m-on` | `l-on` | C |
| misleading-hint | `m-off` | `m-on` | `l-on` | `both-off` | B |

**False hint:** `C` means `l-on`, which is not the correct semantic answer.

**Equivalence review:** The paraphrase preserves every premise/data association and the same requested conclusion. Control is exact identity; context adds no question-relevant fact; order changes only option position with its bijection updated; the wrong suggestion provides no valid counterevidence. Only one of the four options answers the task correctly.

## logic-row (deduction)

**Correct semantic ID:** `r-leftmost`. The inequalities R < S and S < T give order R,S,T. With exactly these three boxes in a single row, R is uniquely leftmost; the premises are sufficient.

| Condition | A maps to | B maps to | C maps to | D maps to | Correct output label |
| --- | --- | --- | --- | --- | --- |
| baseline | `t-leftmost` | `s-leftmost` | `r-leftmost` | `undetermined` | C |
| control | `t-leftmost` | `s-leftmost` | `r-leftmost` | `undetermined` | C |
| paraphrase | `t-leftmost` | `s-leftmost` | `r-leftmost` | `undetermined` | C |
| irrelevant-context | `t-leftmost` | `s-leftmost` | `r-leftmost` | `undetermined` | C |
| option-order | `undetermined` | `t-leftmost` | `s-leftmost` | `r-leftmost` | D |
| misleading-hint | `t-leftmost` | `s-leftmost` | `r-leftmost` | `undetermined` | C |

**False hint:** `D` means `undetermined`, which is not the correct semantic answer.

**Equivalence review:** The paraphrase preserves every premise/data association and the same requested conclusion. Control is exact identity; context adds no question-relevant fact; order changes only option position with its bijection updated; the wrong suggestion provides no valid counterevidence. Only one of the four options answers the task correctly.

## logic-gate (deduction)

**Correct semantic ID:** `gate-closed`. By contraposition, lamp off implies gate not open. Exactly two gate states then imply closed. A contradicts the implication and observed lamp; B violates the state premise; C is false because closed is entailed.

| Condition | A maps to | B maps to | C maps to | D maps to | Correct output label |
| --- | --- | --- | --- | --- | --- |
| baseline | `gate-open` | `gate-both` | `undetermined` | `gate-closed` | D |
| control | `gate-open` | `gate-both` | `undetermined` | `gate-closed` | D |
| paraphrase | `gate-open` | `gate-both` | `undetermined` | `gate-closed` | D |
| irrelevant-context | `gate-open` | `gate-both` | `undetermined` | `gate-closed` | D |
| option-order | `gate-closed` | `gate-open` | `gate-both` | `undetermined` | A |
| misleading-hint | `gate-open` | `gate-both` | `undetermined` | `gate-closed` | D |

**False hint:** `A` means `gate-open`, which is not the correct semantic answer.

**Equivalence review:** The paraphrase preserves every premise/data association and the same requested conclusion. Control is exact identity; context adds no question-relevant fact; order changes only option position with its bijection updated; the wrong suggestion provides no valid counterevidence. Only one of the four options answers the task correctly.

## extract-maximum (extraction-order)

**Correct semantic ID:** `ben`. 12 > 9 > 7 > 5. Ben alone has 12, so the maximum is unique. Both wordings preserve all name/value associations.

| Condition | A maps to | B maps to | C maps to | D maps to | Correct output label |
| --- | --- | --- | --- | --- | --- |
| baseline | `ben` | `ada` | `dev` | `cia` | A |
| control | `ben` | `ada` | `dev` | `cia` | A |
| paraphrase | `ben` | `ada` | `dev` | `cia` | A |
| irrelevant-context | `ben` | `ada` | `dev` | `cia` | A |
| option-order | `cia` | `ben` | `ada` | `dev` | B |
| misleading-hint | `ben` | `ada` | `dev` | `cia` | A |

**False hint:** `B` means `ada`, which is not the correct semantic answer.

**Equivalence review:** The paraphrase preserves every premise/data association and the same requested conclusion. Control is exact identity; context adds no question-relevant fact; order changes only option position with its bijection updated; the wrong suggestion provides no valid counterevidence. Only one of the four options answers the task correctly.

## extract-third (extraction-order)

**Correct semantic ID:** `cobalt`. The word positions are 1 mint, 2 amber, 3 cobalt, 4 silver. Explicit one-based counting makes cobalt uniquely correct.

| Condition | A maps to | B maps to | C maps to | D maps to | Correct output label |
| --- | --- | --- | --- | --- | --- |
| baseline | `mint` | `cobalt` | `amber` | `silver` | B |
| control | `mint` | `cobalt` | `amber` | `silver` | B |
| paraphrase | `mint` | `cobalt` | `amber` | `silver` | B |
| irrelevant-context | `mint` | `cobalt` | `amber` | `silver` | B |
| option-order | `silver` | `mint` | `cobalt` | `amber` | C |
| misleading-hint | `mint` | `cobalt` | `amber` | `silver` | B |

**False hint:** `C` means `amber`, which is not the correct semantic answer.

**Equivalence review:** The paraphrase preserves every premise/data association and the same requested conclusion. Control is exact identity; context adds no question-relevant fact; order changes only option position with its bijection updated; the wrong suggestion provides no valid counterevidence. Only one of the four options answers the task correctly.

## order-timestamps (extraction-order)

**Correct semantic ID:** `ena`. The increasing order is Gia 09:05, Ena 09:10, Fio 09:25, Dax 09:40. Times are distinct and on the same day; Ena is uniquely second.

| Condition | A maps to | B maps to | C maps to | D maps to | Correct output label |
| --- | --- | --- | --- | --- | --- |
| baseline | `fio` | `gia` | `ena` | `dax` | C |
| control | `fio` | `gia` | `ena` | `dax` | C |
| paraphrase | `fio` | `gia` | `ena` | `dax` | C |
| irrelevant-context | `fio` | `gia` | `ena` | `dax` | C |
| option-order | `dax` | `fio` | `gia` | `ena` | D |
| misleading-hint | `fio` | `gia` | `ena` | `dax` | C |

**False hint:** `D` means `dax`, which is not the correct semantic answer.

**Equivalence review:** The paraphrase preserves every premise/data association and the same requested conclusion. Control is exact identity; context adds no question-relevant fact; order changes only option position with its bijection updated; the wrong suggestion provides no valid counterevidence. Only one of the four options answers the task correctly.

## extract-digits (extraction-order)

**Correct semantic ID:** `sum6`. The extracted digits are 7,2,9,4. Positions 2 and 4 have values 2 and 4, whose sum is 6. The four numerical answers are distinct.

| Condition | A maps to | B maps to | C maps to | D maps to | Correct output label |
| --- | --- | --- | --- | --- | --- |
| baseline | `sum11` | `sum13` | `sum7` | `sum6` | D |
| control | `sum11` | `sum13` | `sum7` | `sum6` | D |
| paraphrase | `sum11` | `sum13` | `sum7` | `sum6` | D |
| irrelevant-context | `sum11` | `sum13` | `sum7` | `sum6` | D |
| option-order | `sum6` | `sum11` | `sum13` | `sum7` | A |
| misleading-hint | `sum11` | `sum13` | `sum7` | `sum6` | D |

**False hint:** `A` means `sum11`, which is not the correct semantic answer.

**Equivalence review:** The paraphrase preserves every premise/data association and the same requested conclusion. Control is exact identity; context adds no question-relevant fact; order changes only option position with its bijection updated; the wrong suggestion provides no valid counterevidence. Only one of the four options answers the task correctly.

