#!/usr/bin/python3
import requests
import routeros_api
import hashlib
import re
import math
import datetime
import time

address = "*.*.*.*" #RouterOS API IP Address
username = "admin" #UserName
password = "****" #Password


def GetRawApnic_lastest():
    apnic_text = requests.get(
        "https://ftp.apnic.net/apnic/stats/apnic/delegated-apnic-latest").text
    apnic_md5 = requests.get(
        "https://ftp.apnic.net/apnic/stats/apnic/delegated-apnic-latest.md5").text
    h = hashlib.md5()
    h.update(apnic_text.encode(encoding="utf-8"))
    check_md5 = h.hexdigest()
    if apnic_md5.index(check_md5) > -1:
        return apnic_text
    else:
        return GetRawApnic_lastest()


def UpdateScript(Area = "CN"):
    apnic_text = GetRawApnic_lastest()
    cn_zone_ipv4 = re.findall(
        Area+r"\|ipv4\|([0-9\.]*)\|([0-9]*)\|", apnic_text, re.M)
    cn_zone_ipv6 = re.findall(
        Area+r"\|ipv6\|([0-9a-f\:\.]*)\|([0-9]*)\|", apnic_text, re.M)
    connection = routeros_api.RouterOsApiPool(
        address,
        username=username,
        password=password,
        plaintext_login=True,
    )
    api = connection.get_api()
    del_count, add_count = 0, 0
    ipv4_list = api.get_resource("/ip/firewall/address-list")
    old_cn_ipv4_address = list(
        map(lambda x: x["address"], ipv4_list.get(list=Area+".zone")))
    new_cn_ipv4_address = list(
        map(lambda x: x[0]+"/"+str(32-int(math.log(int(x[1]), 2))), cn_zone_ipv4))

    for old_ip in old_cn_ipv4_address:
        if old_ip not in new_cn_ipv4_address:
            ipv4_list.remove(id=ipv4_list.get(address=old_ip)[0]["id"])
            print("[Info]:Remove IP:%s" % (old_ip))
            del_count += 1
            pass
    pass
    for new_ip in new_cn_ipv4_address:
        if new_ip not in old_cn_ipv4_address:
            ipv4_list.add(
                address=new_ip,
                list=Area+".zone"
            )
            print("[Info]:Insert IP:%s" % (new_ip))
            add_count += 1
            pass
    pass

    ipv6_list = api.get_resource("/ipv6/firewall/address-list")
    old_cn_ipv6_address = list(
        map(lambda x: x["address"], ipv6_list.get(list=Area+".zone"))
    )
    new_cn_ipv6_address = list(
        map(lambda x: x[0]+"/"+x[1], cn_zone_ipv6)
    )

    for old_ipv6 in old_cn_ipv6_address:
        if old_ipv6 not in new_cn_ipv6_address:
            ipv6_list.remove(id=ipv6_list.get(address=old_ipv6)[0]["id"])
            print("[Info]:Remove IPv6:%s" % (old_ipv6))
            del_count += 1
    for new_ipv6 in new_cn_ipv6_address:
        if new_ipv6 not in old_cn_ipv6_address:
            ipv6_list.add(
                address=new_ipv6,
                list=Area+".zone"
            )
            print("[Info]:Insert IPv6:%s" % (new_ipv6))
            add_count += 1
    print(
        "[Info]:Delete Count:%s,Insert Count:%s\n[Info]:Time:%s" %
        (del_count, add_count, datetime.datetime.now())
    )


if __name__ == "__main__":
    while True:
        UpdateScript("CN")
        wait_time = 60*60*(4+24-time.localtime().tm_hour)
        print("[Info]:WaitTime:%sH"%(wait_time/60/60))
        time.sleep(wait_time)
    pass
