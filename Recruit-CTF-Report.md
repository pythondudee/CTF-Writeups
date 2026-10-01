# TryHackMe: Recruit; Penetration Test Report

**Analyst:** pythondudee
**Target:** 10.48.151.78
**Room:** Recruit (TryHackMe)
**Objective:** Full compromise via web exploitation, capturing all flags

---

## Summary

The Recruit web application was compromised through chained vulnerabilities: an insecure file-read endpoint (LFI) used to leak application source code and hardcoded credentials, followed by SQL injection to extract sensitive data from the backend database. Multiple attack vectors were chained together to achieve full system compromise and flag capture.

---

## 1. Reconnaissance

A directory brute force with gobuster against the web root identified the application structure:

```
gobuster dir -u http://10.48.151.78/ -w /usr/share/wordlists/SecLists/Discovery/Web-Content/common.txt
```

Key results:

| Path | Status | Notes |
|---|---|---|
| index.php | 200 | Login page |
| phpmyadmin | 301 | DB admin panel |
| mail | 301 | Mail directory |
| sitemap.xml | 200 | Site map |

The login page linked to an "Access API" page (`api.php`) documenting a file-fetch endpoint for candidate CVs:

```
/file.php?cv=<URL>
```

![API endpoint disclosure](./screenshots/recruit-CTF/01-api-disclosure.png)

---

## 2. SSRF / LFI Testing

### 2.1 SSRF attempt

A listener was set up on the attacker VPN IP to test whether `file.php` performed server-side requests.

![Attacker IP](./screenshots/recruit-CTF/02-attacker-ip.png)

The endpoint did make outbound requests, but they timed out. This ruled out external SSRF but suggested internal file access was possible.

### 2.2 LFI payload testing

Testing local file inclusion with common paths:

![SSRF test](./screenshots/recruit-CTF/03-ssrf-test.png)

Attempting `/etc/passwd`:
```
http://10.48.151.78/file.php?cv=file:///etc/passwd
```

Access was initially blocked. However, after discovering the application structure through directory enumeration, the path `/var/www/html/` became the target.

---

## 3. Source Code Disclosure via LFI

### 3.1 Leaking index.php

The LFI endpoint was exploited to read the application's PHP source code:

```
http://10.48.151.78/file.php?cv=file:///var/www/html/index.php
```

Response revealed hardcoded database credentials:
```php
$servername = "localhost";
$username = "recruit_user";
$password = "recruit_pass123";
$dbname = "recruit_db";
```

### 3.2 Invalid login attempts

![Login invalid](./screenshots/recruit-CTF/04-login-invalid.png)

Initial login attempts with the disclosed credentials failed on the web interface, suggesting the credentials were for database access rather than the web application.

### 3.3 FAQ restrictions discovered

![FAQ restrictions](./screenshots/recruit-CTF/05-faq-restrictions.png)

The FAQ page revealed file upload restrictions and path traversal mitigations, hinting that input validation was in place.

---

## 4. SQL Injection Discovery

### 4.1 Initial bypass attempt

![Bypass attempt](./screenshots/recruit-CTF/06-bypass-attempt.png)

SQL injection was tested on the login form using basic payloads. Initial attempts to bypass authentication were blocked.

### 4.2 Access denied response

![Access denied](./screenshots/recruit-CTF/07-access-denied.png)

The application enforced strict access controls, returning "Access Denied" for unauthorized users.

### 4.3 Apache error enumeration

![Apache 404](./screenshots/recruit-CTF/08-apache-404.png)

Directory traversal attempts revealed Apache's default 404 error page, providing information disclosure about the server.

---

## 5. Database Exploitation

### 5.1 HR module access

After gaining initial access to the application through SQLi, the HR module was discovered:

![HR flag](./screenshots/recruit-CTF/09-hr-flag.png)

First flag captured: `Flag{...}`

### 5.2 ORDER BY column enumeration

To determine the number of columns in the target SQL query:

![ORDER BY test](./screenshots/recruit-CTF/10-orderby-test.png)

Testing revealed **5 columns** in the query.

### 5.3 UNION-based SQL injection

Crafting a UNION SELECT payload to extract data:

![UNION SELECT](./screenshots/recruit-CTF/11-union-select.png)

Payload:
```sql
' UNION SELECT 1,2,3,4,5 -- -
```

### 5.4 Database enumeration

Extracting table names from `information_schema`:

![Tables found](./screenshots/recruit-CTF/12-tables-found.png)

Key tables identified:
- `users`
- `credentials`
- `flags`
- `hr_data`

### 5.5 Column extraction

Enumerating columns in the `users` table:

![Columns found](./screenshots/recruit-CTF/13-columns-found.png)

Columns:
- `id`
- `username`
- `password`
- `role`
- `email`

### 5.6 Credential dumping

Extracting user credentials from the database:

![Credentials dumped](./screenshots/recruit-CTF/14-creds-dumped.png)

Dumped credentials:
```
admin | admin_password_hash | admin
recruiter | recruiter_pass | recruiter
user | user_pass | user
```

---

## 6. Admin Access & Flag Extraction

### 6.1 Admin flag retrieval

Using admin credentials obtained via SQL injection to log in and extract the final flag:

![Admin flag](./screenshots/recruit-CTF/15-admin-flag.png)

Final flag: `Flag{...}`

---

## Summary of Vulnerabilities

| Vulnerability | Severity | Impact |
|---|---|---|
| Local File Inclusion (LFI) | Critical | Source code & credential disclosure |
| Hardcoded Credentials | Critical | Database access compromise |
| SQL Injection | Critical | Full database access & data exfiltration |
| Weak Input Validation | High | Allows SSRF/LFI/SQLi attacks |
| Information Disclosure | Medium | Server & application details leaked |

---

## Remediation

1. **Remove hardcoded credentials** — use environment variables or secrets management
2. **Implement parameterized queries** — prevent SQL injection
3. **Validate and sanitize all input** — especially file paths and SQL parameters
4. **Use WAF rules** — detect and block common injection patterns
5. **Apply principle of least privilege** — limit database user permissions
6. **Enable logging & monitoring** — detect anomalous SQL queries

---

**Report Generated:** 2026-10-01
**Status:** Exploitation Complete
