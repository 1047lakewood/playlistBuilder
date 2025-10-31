# Ad Scheduler Logic Documentation

## Core Principle
**Ads scheduled for an hour MUST play during that hour, with at least 3 minutes safety margin before the hour ends.**

## Decision Flow

### When Hourly Check Triggers

```
START: Hourly check triggered (or simulate)
  ↓
1. SAFETY CHECK: < 3 minutes left in hour?
   YES → Play INSTANT immediately (no time to wait!)
   NO → Continue
  ↓
2. Does current track end THIS hour?
   NO (ends next hour) → Play INSTANT immediately
   YES → Continue
  ↓
3. Is NEXT track a lecture?
   YES → Check timing:
         - Lecture starts within hour? → Play SCHEDULED
         - Lecture starts next hour? → Play INSTANT
   NO → Continue
  ↓
4. Calculate: Minutes left after current track ends
   < 3 minutes? → Play INSTANT now (too risky to wait)
   ≥ 3 minutes? → WAIT for track to change
```

### When Track Changes (While Waiting)

```
TRACK CHANGED → Re-run the ENTIRE check from step 1!
  ↓
1. SAFETY CHECK: < 3 minutes left in hour?
   YES → Play INSTANT (time ran out!)
   NO → Continue
  ↓
2. Does NEW current track end THIS hour?
   NO (ends next hour) → Play INSTANT immediately
   YES → Continue
  ↓
3. Is NEXT track a lecture?
   YES → Play SCHEDULED (found a lecture!)
   NO → Continue
  ↓
4. Calculate: Minutes left after NEW track ends
   < 3 minutes? → Play INSTANT (cutting it close)
   ≥ 3 minutes? → WAIT AGAIN for next track change
```

## Example Scenario (Your Example)

**Time: 3:00 PM**
- Current track: Ends 3:08
- Next track: NOT a lecture
- Action: Calculate → After 3:08, still 52 min left → **WAIT**

**Time: 3:08 PM (Track Changed)**
- New current track: Ends 3:12  
- Next track: NOT a lecture
- Action: Calculate → After 3:12, still 48 min left → **WAIT AGAIN**

**Time: 3:12 PM (Track Changed)**
- New current track: Ends 3:35
- Next track: **IS a lecture**
- Action: Lecture starts within hour → **Play SCHEDULED** (will play before lecture at 3:35!)

**Recursive waiting continues until:**
1. ✅ Find a lecture → Schedule before it
2. ⚠️ Track ends next hour → Play instant
3. ⚠️ < 3 minutes left → Play instant immediately

## Safety Mechanisms

### 1. Time Safety Margin
- Always check if < 3 minutes left
- If yes, play immediately (no more waiting)
- Ensures ads play even if perfect timing isn't possible

### 2. Error Handling
- Any error calculating time → Play instant (safe fallback)
- Any error detecting lectures → Play instant (safe fallback)
- Better to play ads than miss the hour

### 3. Hourly Guarantee
- Every error path defaults to playing instant
- Waiting only happens when safe margin exists
- Ads WILL play every scheduled hour

## API Usage

### Scheduled API (schedule&type=run)
- Used when lecture is found and starts within hour
- mAirList will schedule ad to play before the lecture
- Optimal timing: plays naturally before lecture

### Instant API (instant play)
- Used when no lecture found or time running out
- Plays ad immediately at current position
- Ensures ad plays this hour even without perfect timing

## Configuration

### Safety Margin
- Default: 3 minutes
- Can be adjusted in code if needed
- Conservative to account for processing time

### Hourly Check Interval
- Triggers automatically at the **top of each hour** (e.g., 1:00, 2:00, 3:00, etc.)
- Detects hour boundary changes (not just elapsed time)
- Ensures ads scheduled for an hour always get checked during that hour
- Can be manually triggered via "Simulate Hour Start" button

## Testing

### Manual Test
1. Open Options → Debug tab
2. Click "Simulate Hour Start"
3. Watch logs to see decision process

### What to Look For in Logs
```
INFO - Minutes remaining in current hour: 52.3
INFO - Current track ends within this hour: True
INFO - Next track is lecture: False
INFO - Minutes remaining after current track ends: 48.5
INFO - Safe to wait (48.5 min margin) - waiting for track change.
```

Then when track changes:
```
INFO - Track changed from 'Artist A - Title' to 'Artist B - Title'
INFO - Track boundary detected - re-evaluating with new track.
INFO - Minutes remaining in current hour: 48.2
INFO - Current track ends within this hour: True
INFO - Next track is lecture: True
INFO - Lecture will start within hour: True
INFO - Next lecture will start within current hour - running schedule service.
```

## Summary

The scheduler is **opportunistic but guaranteed**:
- **Tries** to find the best timing (before lectures)
- **Waits** through multiple tracks if safe
- **Guarantees** ads play every hour with safety margin
- **Never risks** missing the hour for perfect timing

