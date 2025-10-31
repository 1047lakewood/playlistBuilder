#!/usr/bin/env python3
xml_content = r'''<?xml version="1.0" encoding="utf-8"?>
<PLAYER name="RadioBOSS" version="7.1.1.4">
<TRACK ARTIST="Rav Asher Weiss" TITLE="Yomtov Sheni Shel Galiyot M" ALBUM="" YEAR="" GENRE="" COMMENT="" FILENAME="G:\Shiurim\R Asher Weiss\rabbi_osher_weiss_yomtov-sheni-shel-galiyot M.mp3" DURATION="53:03" STARTED="2025-09-29 14:23:35" PLAYCOUNT="1" LASTPLAYED="2025-09-29 14:23:35" INTRO="0.00" OUTRO="0.00" LANGUAGE="" RATING="0" BPM="" TAGS="" PUBLISHER="" ALBUMARTIST="" COMPOSER="" COPYRIGHT="" TRACKNUMBER="" F1="" F2="" F3="" F4="" F5="" CASTTITLE="Rav Asher Weiss - Yomtov Sheni Shel Galiyot M" LISTENERS="0" LYRICS="" />
<NEXTTRACK><TRACK ARTIST="Rav Ficshel Schachter" TITLE="Parashat V Etchanan From Slippers To Shoes H" ALBUM="" YEAR="" GENRE="" COMMENT="" FILENAME="G:\Shiurim\R Ficshel Schachter\parashat_v_etchanan.mp3" DURATION="45:20" PLAYCOUNT="1" LASTPLAYED="2025-09-29 14:20:00" INTRO="0.00" OUTRO="0.00" LANGUAGE="" RATING="0" BPM="" TAGS="" PUBLISHER="" ALBUMARTIST="" COMPOSER="" COPYRIGHT="" TRACKNUMBER="" F1="" F2="" F3="" F4="" F5="" LYRICS="" CASTTITLE="Rav Ficshel Schachter - Parashat V Etchanan From Slippers To Shoes H" /></NEXTTRACK>
<PREVTRACK><TRACK ARTIST="Avremi Roth" TITLE="Doidi Yorad Leganoi ID21366" ALBUM="Malachei Hashores" YEAR="2003" GENRE="Shabbos" COMMENT="Doidi Yorad Leganoi" FILENAME="G:\Shiurim\Dopplet 3 weeks\NEW Elul USB from PD 5785\Elul songs\Avremi Roth-Malachei Hashores-10-Doidi Yorad Leganoi ID21366.mp3" DURATION="05:39" PLAYCOUNT="3" LASTPLAYED="2025-09-29 14:20:00" INTRO="0.00" OUTRO="0.00" LANGUAGE="" RATING="0" BPM="" TAGS="" PUBLISHER="" ALBUMARTIST="Avremi Roth" COMPOSER="" COPYRIGHT="" TRACKNUMBER="10" F1="" F2="" F3="" F4="" F5="" LYRICS="" CASTTITLE="Avremi Roth - Doidi Yorad Leganoi ID21366" /></PREVTRACK>
</PLAYER>'''

with open(r'G:\To_RDS\nowplaying_test.xml', 'w', encoding='utf-8') as f:
    f.write(xml_content)

print("✅ Fixed test XML file with proper content!")
print("📁 File: G:\\To_RDS\\nowplaying_test.xml")
print("🎵 Current: Rav Asher Weiss - Yomtov Sheni Shel Galiyot M")
print("⏭️  Next: Rav Ficshel Schachter - Parashat V Etchanan From Slippers To Shoes H")
print("✅ Next track should be detected as a lecture (starts with 'R')")

