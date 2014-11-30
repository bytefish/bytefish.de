title: How to secure your workstation with iptables
date: 2011-06-01 11:33
tags: linux
slug: iptables
author: Philipp Wagner
summary: Some iptable rules I use for my boxes.

Linux comes with a great [firewall](http://en.wikipedia.org/wiki/Firewall_%28computing%29) and with the help of [iptables](http://www.netfilter.org/projects/iptables/index.html) it's easy to secure a workstation. 

[iptables](http://www.netfilter.org/projects/iptables/index.html) makes it possible to define chains of rules that an incoming or outgoing packet has to pass for getting dropped or accepted. 
If no rule applies a default policy (either drop or accept) is applied.

You can see your current iptables rules by typing (you must be root to configure iptables, so use [sudo](http://xkcd.com/149)):

```sh
iptables -L
```

If you didn't configure anything yet the output is like:

```
philipp@banana:~$ sudo iptables -L
Chain INPUT (policy ACCEPT)
target     prot opt source               destination         

Chain FORWARD (policy ACCEPT)
target     prot opt source               destination         

Chain OUTPUT (policy ACCEPT)
target     prot opt source               destination
```

This means: no rules are specified for incoming (``INPUT``) and outgoing (``OUTPUT``) packets. Every packet is accepted, because the default policy for all chains is ``ACCEPT``. 
This is not a desirable setup for a workstation or a server connected to the Internet. There are two options now: you either set the default policies to ``ACCEPT`` and define 
rules to selectively ``DROP`` packets or you set the default policies to ``DROP`` and selectively ``ACCEPT`` packets.

I've decided to use the second way and instead of teaching you how to write iptables rules at this point (the iptables man page is really exhaustive) I am posting the script to append the rules:

```sh
#!/bin/bash
 
# forget old rules
iptables -F
iptables -X
iptables -Z
 
# set default policy to drop
iptables -P INPUT DROP
iptables -P OUTPUT DROP
iptables -P FORWARD DROP
 
# allow loopback
iptables -A INPUT -i lo -j ACCEPT
iptables -A OUTPUT -o lo -j ACCEPT

# drop invalid packets
iptables -A INPUT  -m state --state INVALID -j DROP
iptables -A OUTPUT -m state --state INVALID -j DROP
iptables -A FORWARD -m state --state INVALID -j DROP
 
# allow established, related packets we've already seen
iptables -A INPUT -m state --state ESTABLISHED,RELATED -j ACCEPT
iptables -A OUTPUT -m state --state ESTABLISHED,RELATED -j ACCEPT

# output chain
iptables -A OUTPUT -p tcp -m tcp --dport 22 -m comment --comment "SSH" -j ACCEPT
iptables -A OUTPUT -p tcp -m tcp --dport 53 -m comment --comment "DNS-TCP" -j ACCEPT
iptables -A OUTPUT -p udp -m udp --dport 53 -m comment --comment "DNS-UDP" -j ACCEPT
iptables -A OUTPUT -p udp -m udp --dport 67:68 -m comment --comment "DHCP" -j ACCEPT
iptables -A OUTPUT -p tcp -m tcp --dport 80 -m comment --comment "HTTP" -j ACCEPT
iptables -A OUTPUT -p tcp -m tcp --dport 443 -m comment --comment "HTTPS" -j ACCEPT
iptables -A OUTPUT -p tcp -m tcp --dport 465 -m comment --comment "SMTPS" -j ACCEPT
iptables -A OUTPUT -p tcp -m tcp --dport 587 -m comment --comment "SMTPS" -j ACCEPT
iptables -A OUTPUT -p tcp -m tcp --dport 993 -m comment --comment "IMAPS" -j ACCEPT
iptables -A OUTPUT -p tcp -m tcp --dport 995 -m comment --comment "POP3S" -j ACCEPT
iptables -A OUTPUT -p tcp -m tcp --dport 5222 -m comment --comment "JABBER" -j ACCEPT
iptables -A OUTPUT -p tcp -m tcp --dport 8001 -m comment --comment "IRC" -j ACCEPT
iptables -A OUTPUT -p tcp -m tcp --dport 8010 -m comment --comment "JABBER FT" -j ACCEPT
 
# allow icmp packets (e.g. ping...)
iptables -A INPUT -p icmp -m state --state NEW -j ACCEPT
```

Save the script to ``iptables.sh`` and execute it (*as root*). This will create the rules for the iptables chains:

```sh
bash iptables.sh 
```

If you type:

```sh
iptables -L -v
```

again you should see all the above rules. 

But note that the rules get lost if you reboot, so make them persistent:

```sh
iptables-save > /etc/iptables.rules
```

These rules should be loaded on (network) startup. If you are in [Debian](http://www.debian.org) or [Ubuntu](http://www.ubuntu.com) create a script in ``/etc/network/if-pre-up.d/`` with the following 
content (I'll give it the filename ``iptablesload`` in this example):

```sh
#!/bin/sh
iptables-restore < /etc/iptables.rules
exit 0
```

And make it executable:

```sh
chmod +x /etc/network/if-pre-up.d/iptablesload
```

You are done! Writing a startup script for loading the rules is possible of course, but my advise is to look for the preferred solution of your distribution.
