from pathlib import Path
import re

md_path = Path('recruit-writeup/Recruit-CTF-Report.md')
backup_path = md_path.with_suffix('.md.bak')

screenshot_paths = [
    './screenshots/01-api-disclosure.png',
    './screenshots/02-attacker-ip.png',
    './screenshots/03-ssrf-test.png',
    './screenshots/04-login-invalid.png',
    './screenshots/05-faq-restrictions.png',
    './screenshots/06-bypass-attempt.png',
    './screenshots/07-access-denied.png',
    './screenshots/08-apache-404.png',
    './screenshots/09-hr-flag.png',
    './screenshots/10-orderby-test.png',
    './screenshots/11-union-select.png',
    './screenshots/12-tables-found.png',
    './screenshots/13-columns-found.png',
    './screenshots/14-creds-dumped.png',
    './screenshots/15-admin-flag.png',
]

pattern = re.compile(r'!\[[^\]]*\]\(data:image/png;base64,[^)]+\)')

text = md_path.read_text(encoding='utf-8')
if 'data:image/png;base64' not in text:
    print('No embedded PNG data URLs found; nothing to fix.')
    raise SystemExit(0)

matches = list(pattern.finditer(text))
if not matches:
    print('No embedded PNG data URLs found; nothing to fix.')
    raise SystemExit(0)

if len(matches) > len(screenshot_paths):
    raise ValueError(f'Found {len(matches)} embedded images but only {len(screenshot_paths)} screenshot files are available.')

backup_path.write_text(text, encoding='utf-8')
result = text
for i, match in enumerate(matches):
    alt_text = match.group(0).split('](', 1)[0][2:]
    replacement = f'![{alt_text}]({screenshot_paths[i]})'
    result = result.replace(match.group(0), replacement, 1)

md_path.write_text(result, encoding='utf-8')
print(f'Updated {md_path} with {len(matches)} screenshot links. Backup stored at {backup_path}.')
