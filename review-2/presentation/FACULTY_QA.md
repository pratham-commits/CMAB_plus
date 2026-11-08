# Review II — faculty Q&A (brutal examiner cheat sheet)

Use with [`../details.md`](../details.md). Answers are **one paragraph + pointer** unless they ask for code.

---

### “You said BBR breaks CMAB. So BBR is bad for live streaming?”

**No.** BBR broke CMAB **only under a misconfigured trace shaper + the paper’s aggressive CMAB control path**. Under **`SHAPER=clock`** (Review I–class emulation), CMAB @ 3 s is **3.29 s / 0% rebuffer on BBR** vs **3.19 s / 0% on CUBIC** — same class. The old **7.2 s / 28%** row is **`emulation-bbr` trace**, not the canonical rerun. See `details.md` §5 and §8.

---

### “How do I know you actually ran BBR and not CUBIC by mistake?”

Deliverable `meta/nginx-tcp_cc.txt` = `bbr`. VM checks: `docker exec dashjs-nginx cat /proc/sys/net/ipv4/tcp_congestion_control`. Batch prefix **1017-0606**, 160/160 sessions, `summary_stats.txt`. We do **not** rely on a single screenshot.

---

### “Review I was September, Review II October — different Docker image. Your comparison is invalid.”

That was **RC7**. We closed it by (1) fixing shaper parity **`SHAPER=clock`**, (2) RC7 validation runs (CUBIC 0523 / BBR 0538) showing healthy CMAB on both CCs, (3) full **160-run BBR clock** matrix. Residual image drift is documented; **mechanism** is proven in code (RC1–RC3) independent of date.

---

### “Prove the 3.19 s and 3.29 s numbers — not from your plots.”

`python3 review-2/scripts/verify_cmab_claims.py` recomputes from **`playback_latency.json`**, drops first 20% of samples (same as paper scripts). Session list printed; any session path auditable.

---

### “What is rebuffer 2.52% on CUBIC CMAB @ 5 s target?”

One round with elevated stall samples in `buffer.json` (level ≤ 0.05 s). Mean over n=10; visible in zoom rebuffer plot. **Not** BBR-specific; BBR clock @ 5 s CMAB is 0% mean.

---

### “Why does L2A have no red CUBIC line on your bitrate plot?”

**Identical means** — both CCs at **6000 kbps** all targets. Lines overlapped; plot script now offsets X and dashes CUBIC. Data exists in JSON.

---

### “Dynamic dropped to 619 kbps on BBR — why didn’t CMAB?”

**RC1:** CMAB uses **`SwitchRequest.PRIORITY.STRONG`** with **no** `min(arm, throughput-feasible arm)`. Dynamic obeys throughput estimate \(\hat{T}\). Same logs, same matrix — **`FACULTY_VERIFICATION_CMAB_BBR.md` §5.6**.

---

### “Arm 7 dominates on BBR trace — is LinTS stupid?”

**RC2:** Before LinTS runs each 15 s timeslot, code **forces arm |A|-1** for the first |A|-1 decisions. That is **not** LinTS; it is handover bootstrap in `CMABAbrController.js` 415–416.

---

### “So is CMAB theory wrong?”

**No.** The implementation removes **feasibility constraints** any sane live ABR needs. LinTS assumes stationary linear rewards; here reward also **misreports stalls** in P.1203 JSON (RC3). Failure is **control + learning plumbing**, not “contextual bandits don’t work.”

---

### “What is your actual Review II contribution?”

1. **Transport extension:** first BBR matrix on same artifact.  
2. **Forensics:** why trace+BBR looked catastrophic (shaper + RC1–RC3).  
3. **Fair baseline:** clock BBR 160-run vs Review I CUBIC — **small CC effect on CMAB**, **CMAB-only sensitivity**.  
4. **Forward work:** **CMAB+** hardening plan (feasibility + bootstrap), not a new ABR family.

---

### “Why not rerun CUBIC on October stack?”

Ideal factorial; **cost/time**. We used Review I CUBIC as historical baseline + RC7 spot checks on October stack. Claims limited to: “under clock shaper, BBR vs CUBIC delta is small for CMAB”; catastrophic BBR attributed to **trace + implementation**.

---

### “Show me one file that proves shaper was wrong.”

`docs/SHAPER_ROOT_CAUSE.md` + fixed `tc-trace.py` (HTB root, `tc_del`). Symptom: CMAB **~28 arm logs** vs Review I **~800+** on same nominal CUBIC.

---

### “What will you implement next?”

**CMAB+ v1:** (P1) clamp arm to \(\kappa \hat{T}\), (P2) remove max-arm bootstrap, (P3) conditional STRONG. Ablation 4–8 runs before any new 160 matrix. **`details.md` §12**.

---

### “If CMAB+ works, do you beat the paper?”

We **harden the same algorithm** for BBR/trace stress — extension to artifact, not claiming new SOTA without full re-emulation and paper figure comparison.
