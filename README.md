EN | [中文](README_zh.md)
# NIC Web Api Kit
Let router equipment obtain the IPv4 IPv6 ASN information of target country by nic.
# How To Run Server
* Install python3,And install expansion package by `pip3 install PyMySQL web.py`
* Edit `nic.py` about mysql db config
* Run `python3 ./nic.py`

# Routing equipment side
## RouterOS
* Suppor IPv4,IPv6 info import.
* paste `nic_for_routeros.rsc` file to `/system script`,and edit config in script.
* in `/system schedule` add timed task `:execute script="your script name"` to auto update