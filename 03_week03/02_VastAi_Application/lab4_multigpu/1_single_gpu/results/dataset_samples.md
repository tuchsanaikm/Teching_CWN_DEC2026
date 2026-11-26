# ตัวอย่างข้อมูล b-mc2/sql-create-context

สับด้วย seed 0 · Training Set 4,000 ตัวอย่าง · Test Set 200 ตัวอย่าง (จากทั้งหมด 78,577) · ตัวอย่างด้านล่างคือ 6 รายการแรกของ Training Set

| # | คำถาม (question) | โครงสร้างตาราง (context) | SQL เฉลย (answer) |
|---|---|---|---|
| 1 | What is the lowest unlock order for the athens circuit? | `CREATE TABLE table_24463470_1 (unlock_order INTEGER, circuit VARCHAR)` | `SELECT MIN(unlock_order) FROM table_24463470_1 WHERE circuit = "Athens"` |
| 2 | What is the highest pick number of a defensive back with less than 136 overall points? | `CREATE TABLE table_name_99 (pick__number INTEGER, overall VARCHAR, position VARCHAR)` | `SELECT MAX(pick__number) FROM table_name_99 WHERE overall < 136 AND position = "defensive back"` |
| 3 | Which engine has a year larger than 1956? | `CREATE TABLE table_name_74 (engine VARCHAR, year INTEGER)` | `SELECT engine FROM table_name_74 WHERE year > 1956` |
| 4 | What is the average Attendance, when Venue is "Candlestick Park", and when Date is "December 27"? | `CREATE TABLE table_name_71 (attendance INTEGER, venue VARCHAR, date VARCHAR)` | `SELECT AVG(attendance) FROM table_name_71 WHERE venue = "candlestick park" AND date = "december 27"` |
| 5 | What is the Netflix number having a segment D, of NED can corn? | `CREATE TABLE table_name_2 (netflix VARCHAR, segment_d VARCHAR)` | `SELECT netflix FROM table_name_2 WHERE segment_d = "ned can corn"` |
| 6 | What is the smallest number of fastest laps listed? | `CREATE TABLE table_19312274_3 (fastest_laps INTEGER)` | `SELECT MIN(fastest_laps) FROM table_19312274_3` |
