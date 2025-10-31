# Comprehensive Ad Test Guide

**Generated:** October 3, 2025, 02:47 AM  
**Backup File:** `messages_backup_20251003_024725.json`

## Test Configuration Overview

A comprehensive ad test configuration has been applied to your system with **42 test ads** covering various scheduling scenarios.

### Test Categories

#### 1. Always-On Ads (2 ads)
- `TEST_AlwaysOn_1`
- `TEST_AlwaysOn_2`

**Expected behavior:** These should play in EVERY ad break, regardless of time or day.

#### 2. Time-Based Ads (5 ads)
- `TEST_Morning_6to9` - Plays 6am-9am every day
- `TEST_Midday_12to13` - Plays noon-1pm every day
- `TEST_Afternoon_15to17` - Plays 3pm-5pm every day
- `TEST_Evening_19to21` - Plays 7pm-9pm every day
- `TEST_Night_22to23` - Plays 10pm-11pm every day

**Expected behavior:** Should only play during specified hours, every day of the week.

#### 3. Day-Based Ads (3 ads)
- `TEST_Weekdays_Only` - Monday through Friday only
- `TEST_Weekend_Only` - Saturday and Sunday only
- `TEST_Friday_Only` - Friday only

**Expected behavior:** Should play every hour on specified days, never on other days.

#### 4. Combined Day+Time Ads (3 ads)
- `TEST_Weekday_Morning_Commute` - Mon-Fri at 7am-8am
- `TEST_Weekday_Evening_Commute` - Mon-Fri at 5pm-6pm
- `TEST_Weekend_Brunch` - Sat-Sun at 10am-11am

**Expected behavior:** Should only play when BOTH day and time conditions are met.

#### 5. Immediate Verification Ads (3 ads)
- `TEST_Hour_02_VerifySoon` - Should play at 2am on Friday
- `TEST_Hour_03_VerifySoon` - Should play at 3am on Friday
- `TEST_Hour_04_VerifySoon` - Should play at 4am on Friday

**Expected behavior:** These are set for the next few hours so you can verify quickly.

#### 6. Full 24-Hour Coverage (24 ads)
- `TEST_Every_Hour_0000` through `TEST_Every_Hour_2300`

**Expected behavior:** One ad for each hour of the day, every day.

#### 7. Disabled Ads (2 ads)
- `TEST_DISABLED_Never_Play_1`
- `TEST_DISABLED_Never_Play_2`

**Expected behavior:** These should NEVER play, even though one has a full schedule.

## Testing Instructions

### Day 1-2: Monitor and Verify

1. **Restart the application** to load the new configuration
2. **Check hourly** for the first few hours to verify immediate ads
3. **Open Ad Statistics window** periodically to see play counts
4. **Review logs** for any scheduling errors

### What to Look For

✅ **Success Indicators:**
- TEST_AlwaysOn ads appear in every ad break
- Time-specific ads only play during their scheduled hours
- Day-specific ads respect day restrictions
- Combined ads only play when both conditions are met
- DISABLED ads never appear in logs or statistics

❌ **Issues to Watch For:**
- Ads playing outside their scheduled times
- Ads playing on wrong days
- Disabled ads playing (critical issue)
- Always-on ads NOT playing every hour
- Missing ads during scheduled times

### Expected Hourly Breakdown (Today - Friday)

**Current Hour (2am-3am):** 6 ads should play
- TEST_AlwaysOn_1
- TEST_AlwaysOn_2
- TEST_Weekdays_Only
- TEST_Friday_Only
- TEST_Hour_02_VerifySoon
- TEST_Every_Hour_0200

**Next Hour (3am-4am):** 6 ads should play
- TEST_AlwaysOn_1
- TEST_AlwaysOn_2
- TEST_Weekdays_Only
- TEST_Friday_Only
- TEST_Hour_03_VerifySoon
- TEST_Every_Hour_0300

**Morning Commute (7am-8am):** 7+ ads should play
- All always-on and Friday-specific ads
- TEST_Morning_6to9
- TEST_Weekday_Morning_Commute
- TEST_Every_Hour_0700

## Verifying Results

### Using Ad Statistics Window

1. Open the Ad Statistics window in your application
2. Check the play counts for test ads
3. Verify dates of last plays
4. Export reports to CSV for detailed analysis

### Checking Logs

Look for log entries like:
```
Successfully logged X/Y ad plays
Ad 'TEST_AlwaysOn_1' play logged successfully
```

### Expected Play Counts After 24 Hours

- **Always-On ads:** ~24 plays each (every hour)
- **Morning ads (6-9am):** ~4 plays
- **Friday-only ads:** ~24 plays (if running on Friday)
- **Weekend ads:** 0 plays (if running on Friday)
- **DISABLED ads:** 0 plays (always)

## Restoring Original Configuration

When testing is complete:

1. Stop the application
2. Copy the backup file: `messages_backup_20251003_024725.json`
3. Rename it to `messages.json` (overwrite the test config)
4. Restart the application

**Command line method:**
```bash
copy messages_backup_20251003_024725.json messages.json
```

## Troubleshooting

### No Ads Playing
- Check if ad scheduler is running
- Verify MP3 files exist at specified paths
- Check logs for errors

### Ads Playing at Wrong Times
- Verify system time is correct
- Check hour-based scheduling logic
- Review scheduler logs for timing calculations

### All Ads Playing All The Time
- Could indicate scheduling logic not being applied
- Check "Scheduled" flag in configuration
- Review lecture detector integration

## Files Involved

- **Test Config:** `messages.json` (modified)
- **Backup:** `messages_backup_20251003_024725.json`
- **Generator Script:** `generate_ad_test.py`
- **Statistics:** `ad_play_statistics.json`
- **This Guide:** `AD_TEST_GUIDE.md`

## Notes

- Test was generated for current day: **Friday**
- Current hour at generation: **2am**
- Total MP3 files used: **2**
- Test configuration includes edge cases and comprehensive coverage

---

**Good luck with your testing!** 🎵📻

