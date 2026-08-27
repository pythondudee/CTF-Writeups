# Pickle Rick CTF — Writeup

**Target:** `10.48.177.187`
**Objective:** Find all 3 Rick and Morty-themed ingredients
**Result:** ✅ All 3 ingredients captured

---

## 1. Reconnaissance — Nmap

Started with a basic Nmap scan to see what was exposed:

```
Nmap scan report for 10.48.177.187
Host is up (0.043s latency).
PORT   STATE SERVICE
22/tcp open  ssh
80/tcp open  http
```

Only SSH and HTTP were open. Nothing to exploit directly here — SSH needs
credentials, so the web server on port 80 was the obvious next stop.

---

## 2. Enumeration — Source Code + Gobuster

Loaded the site and popped open dev tools (**F12**) to check the page source.
Buried in an HTML comment was a **username** — a classic "forgot to strip
the comment before deploying" mistake.

With a username in hand but no password, I ran **Gobuster** to enumerate
hidden directories and files:

```
assets               (Status: 301) → /assets/
robots.txt           (Status: 200)
.htaccess            (Status: 403)
login.php            (Status: 200)
.htpasswd            (Status: 403)
portal.php           (Status: 302) → /login.php
index.html           (Status: 200)
server-status         (Status: 403)
```

Two things stood out immediately:

- **`robots.txt`** — worth checking manually, since it's meant to tell
  search engines what *not* to index (often a breadcrumb to sensitive files).
- **`login.php`** — a login form, and `portal.php` redirects to it when
  unauthenticated, meaning `portal.php` is the real prize once I'm logged in.

Visiting `robots.txt` directly revealed the **password**, sitting there in
plain text.

---

## 3. Gaining Access

With the username (from the HTML comment) and password (from `robots.txt`),
I logged in at `login.php` and landed on `portal.php` — an admin panel that
looked like it was meant to run shell commands.

### The command filter

The panel blocked standard commands — typing `cat` outright just got
filtered/rejected. Rather than being an actual sandboxed shell, it looked
like a naive **blocklist on the string `cat`** (a common weak point in these
"execute a command" web panels).

**Bypass:** splitting the string so the literal word `cat` never appears in
the input, while bash still reassembles it correctly at execution time:

```
c''at <file>
```

Bash treats `''` as an empty string concatenation, so `c''at` is
interpreted as `cat` — but the filter, which is likely just checking for the
substring `"cat"`, never sees it as one contiguous token. Same trick would
work with `c""at`, `c\at`, etc., depending on how naive the filter is.

### First ingredient

Using the panel with this bypass, I read the first ingredient sitting in
the current working directory.

### Second ingredient

Explored the filesystem with `ls` to map out what was around, then found the
second ingredient in Rick's home directory:

```
c''at /home/rick/"second ingredients"
```

(Note the quoted filename — the file itself had spaces in it.)

---

## 4. Privilege Escalation → Third Ingredient

Checked what the current user could run with elevated privileges and found
`sudo` access was permitted for this trick as well. Combining the bypass
with `sudo` gave root-level read access:

```
sudo c''at /root/3rd.txt
```

That pulled the third and final ingredient straight out of `/root`.

Along the way, I also grabbed a second credential/password from a file
discovered while poking around the filesystem with directory traversal
(`../../...`), which helped confirm the escalation path.

---

## 5. Summary

| Stage | Technique | Result |
|---|---|---|
| Recon | Nmap | Found SSH (22) + HTTP (80) |
| Enum | View-source (F12) | Leaked username in HTML comment |
| Enum | Gobuster | Found `robots.txt`, `login.php`, `portal.php` |
| Access | Manual check of `robots.txt` | Leaked password |
| Foothold | Login → `portal.php` command panel | Command execution (filtered) |
| Filter bypass | `c''at` string-splitting trick | Read ingredient #1 |
| Lateral | `ls` + `c''at` on user files | Read ingredient #2 (`/home/rick/`) |
| PrivEsc | `sudo c''at` | Read ingredient #3 (`/root/`) |

**Key takeaway:** the whole box hinges on two classic weak points — secrets
left in places that "shouldn't" be checked (HTML comments, `robots.txt`),
and a command filter that blocks a *literal string* instead of actually
restricting execution, which is trivially bypassed by breaking the string up
in a way the shell will still reassemble.

---

*Raw scan output (Nmap + Gobuster) available in the original `.txt` exports
if you want to cross-reference exact byte sizes / status codes.*
