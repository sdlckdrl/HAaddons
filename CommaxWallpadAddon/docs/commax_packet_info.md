#commax 패킷 분석


### 1. Light (조명)

**Command 패킷**

| 바이트 | 의미 | 가능한 값 |
|--------|------|-----------|
| 1 | 헤더 | "31" |
| 2 | deviceId | "01"부터 |
| 3 | power | "01" (on), "00" (off) |
| 4-7 | empty | - |
| 8 | checksum | - |

**State 패킷**

| 바이트 | 의미 | 가능한 값 |
|--------|------|-----------|
| 1 | 헤더 | "B0" |
| 2 | power | "01" (on), "00" (off) |
| 3 | deviceId | - |
| 4-7 | empty | - |
| 8 | checksum | - |

### 2. LightBreaker (조명 차단기)

**Command 패킷**

| 바이트 | 의미 | 가능한 값 |
|--------|------|-----------|
| 1 | 헤더 | "22" |
| 2 | deviceId | - |
| 3 | power | "01" (on), "00" (off) |
| 4 | fixed | "01" |
| 5-7 | empty | - |
| 8 | checksum | - |

**State 패킷**

| 바이트 | 의미 | 가능한 값 |
|--------|------|-----------|
| 1 | 헤더 | "A0" |
| 2 | power | "01" (on), "00" (off) |
| 3 | deviceId | - |
| 4-5 | empty | - |
| 6 | fixed | "15" |
| 7 | empty | - |
| 8 | checksum | - |

### 3. Thermo (온도조절기)

**Command 패킷**

| 바이트 | 의미 | 가능한 값 |
|--------|------|-----------|
| 1 | 헤더 | "04" |
| 2 | deviceId | - |
| 3 | commandType | "04" (power), "03" (change) |
| 4 | value | "81" (on), "00" (off), "18" (target) |
| 5-7 | empty | - |
| 8 | checksum | - |

**State 패킷**

| 바이트 | 의미 | 가능한 값 |
|--------|------|-----------|
| 1 | 헤더 | "82" |
| 2 | power | "81" (idle), "80" (off), "83" (heating) |
| 3 | deviceId | - |
| 4 | currentTemp | - |
| 5 | targetTemp | - |
| 6-7 | empty | - |
| 8 | checksum | - |

### 4. Gas (가스)

**Command 패킷**

| 바이트 | 의미 | 가능한 값 |
|--------|------|-----------|
| 1 | 헤더 | "11" |
| 2 | deviceId | - |
| 3 | power | "80" (off) |
| 4-7 | empty | - |
| 8 | checksum | - |

**State 패킷**

| 바이트 | 의미 | 가능한 값 |
|--------|------|-----------|
| 1 | 헤더 | "90" |
| 2 | power | "A0" (on), "50" (off) |
| 3 | powerRepeat | - |
| 4-7 | empty | - |
| 8 | checksum | - |

### 5. Outlet (콘센트)

**Command 패킷**

| 바이트 | 의미 | 가능한 값 |
|--------|------|-----------|
| 1 | 헤더 | "7A" |
| 2 | deviceId | - |
| 3 | deviceIdRepeat | - |
| 4 | power | "01" (on), "00" (off) |
| 5-7 | empty | - |
| 8 | checksum | - |

**State 패킷**

| 바이트 | 의미 | 가능한 값 |
|--------|------|-----------|
| 1 | 헤더 | "F9" |
| 2 | power | "01" (on), "00" (off) |
| 3 | deviceId | - |
| 4 | fixed1 | "11" |
| 5 | fixed2 | "10" |
| 6-7 | empty | - |
| 8 | checksum | - |

### 6. 환기장치

**Command 패킷**

| 바이트 | 의미 | 가능한 값 |
|--------|------|-----------|
| 1 | 헤더 | "78" |
| 2 | deviceId | - |
| 3 | commandType | "01" (power), "02" (setSpeed) |
| 4 | value | "00" (off/low), "01" (medium), "02" (high), "04" (on) |
| 5-7 | empty | - |
| 8 | checksum | - |

**State 패킷**

| 바이트 | 의미 | 가능한 값 |
|--------|------|-----------|
| 1 | 헤더 | "F6" |
| 2 | power | "04" (on), "00" (off) |
| 3 | deviceId | - |
| 4 | speed | "00" (low), "01" (medium), "02" (high) |
| 5-7 | empty | - |
| 8 | checksum | - |

### 7. EV (엘리베이터)

**Command 패킷**

| 바이트 | 의미 | 가능한 값 |
|--------|------|-----------|
| 1 | 헤더 | "A0" |
| 2 | deviceId | - |
| 3 | power | "01" (on) |
| 4 | fixed1 | "00" |
| 5 | fixed2 | "08" |
| 6 | fixed3 | "15" |
| 7 | fixed4 | "00" |
| 8 | checksum | - |

**State 패킷**

| 바이트 | 의미 | 가능한 값 |
|--------|------|-----------|
| 1 | 헤더 | "23" |
| 2 | power | "01" (on) |
| 3 | deviceId | - |
| 4-7 | empty | - |
| 8 | checksum | - |

