
                          Python Wechat-JIRA Service

Part of this project forked from Python CLI for JIRA
http://www.pobox.com/~doar

I did some modification in the class of create and getissues, mainly for adopting Chinese in Jira system. This should worked on JIRA versions from 3.4 to 4.4. The program worked on both CLI and Python Program, although my implementation is a bit tricky. I will keep on improving the work.

Currently, I am mainly working on the communication between wechat and service. The destination is to implement a service, recording company events. Most of the data are inputed from Wechat and stored in Jira side, then shown in Wechat on demond.
