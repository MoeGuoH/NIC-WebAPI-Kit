#!/usr/bin/python3
from os import mkdir
from typing import List, Text
import requests
import hashlib
import re
import math
import datetime
import os
import time
import pymysql
import threading
from datetime import datetime
import web

from requests.sessions import HTTPAdapter

_db_host = "localhost"
_db_user = "root"
_db_passwd = "toor"
_db_name = "nic"

_table_cache_path = "./cache/"

_nic_table_urls = [
    {
        "name": "afrinic",
        "url": "https://ftp.apnic.net/stats/afrinic/delegated-afrinic-latest",
        "md5": "",
        "needUpdate": False
    },
    {
        "name": "apnic",
        "url": "https://ftp.apnic.net/stats/apnic/delegated-apnic-latest",
        "md5": "",
        "needUpdate": False
    },
    {
        "name": "arin",
        "url": "https://ftp.apnic.net/stats/arin/delegated-arin-extended-latest",
        "md5": "",
        "needUpdate": False
    },
    # {
    #     "name": "iana",
    #     "url": "https://ftp.apnic.net/stats/iana/delegated-iana-latest",
    #     "md5": "",
    #     "needUpdate": False
    # },
    {
        "name": "lacnic",
        "url": "https://ftp.apnic.net/stats/lacnic/delegated-lacnic-latest",
        "md5": "",
        "needUpdate": False
    },
    {
        "name": "ripencc",
        "url": "https://ftp.apnic.net/stats/ripe-ncc/delegated-ripencc-latest",
        "md5": "",
        "needUpdate": False
    },
]

class NICTableManage:
    def __init__(self) -> None:
        self._db = pymysql.connect(
            host=_db_host, user=_db_user, password=_db_passwd, db=_db_name)
        self.__httpClient: requests.Session = requests.session()
        self.__httpClient.mount("http://", HTTPAdapter(max_retries=10))
        self.__httpClient.mount("https://", HTTPAdapter(max_retries=10))
        self.__init_db()
        self.__loopThread = threading.Thread(target=self.__update_loop)
        self.__loopThread.start()
        pass

    def __update_loop(self):
        while True:
            updateZoneCount = self.__update_zone_cache()
            if updateZoneCount>0:
                self.__update_zone_to_db()
            wait_time = 60*60*(4+24-time.localtime().tm_hour)
            self.__log(f"sleep {wait_time}s.")
            time.sleep(wait_time)
            pass

    def __update_zone_cache(self) -> int:
        result: int = 0
        cur = self._db.cursor()
        cur.execute(self.__sql["nic_zone_info"]["all_zone"])
        zoneInfoList: List = cur.fetchall()
        for (zone, md5, zone_url, zone_update_time) in zoneInfoList:
            _md5Str = re.findall(r'(?i)(?<![a-z0-9])[a-f0-9]{32}(?![a-z0-9])', self.__httpClient.get(
                zone_url+".md5", timeout=(10, 300)).text)[0]
            _fileMD5 = ""
            if os.path.exists(_table_cache_path+zone+".txt"):
                with open(_table_cache_path+zone+".txt", "r") as f:
                    _t = f.read()
                    _h = hashlib.md5()
                    _h.update(_t.encode(encoding="utf-8"))
                    _fileMD5 = _h.hexdigest()
            if md5 != _md5Str or _fileMD5 != _md5Str:
                table_text = self.__httpClient.get(
                    zone_url, timeout=(10, 300)).text
                _h = hashlib.md5()
                _h.update(table_text.encode(encoding="utf-8"))
                if _md5Str == _h.hexdigest():
                    with open(_table_cache_path+zone+".txt", "w+") as f:
                        f.write(table_text)
                    cur.execute(
                        self.__sql["nic_zone_info"]["update_zone"], (_md5Str, int(time.time()), zone))
                    self._db.commit()
                    result += 1
                    self.__log(
                        f"[zone.cache]:{zone} update {md5} to {_md5Str}")
                else:
                    self.__log(
                        f"[zone.cache]:{zone} update {md5} download file md5 check error!")
                    raise Exception("md5 check error!")
            else:
                self.__log(f"[zone.cache]:{zone} {md5} already last!")

            pass
        cur.close()
        return result

    def __update_zone_to_db(self):
        cur = self._db.cursor()
        cur.execute(self.__sql["nic_zone_info"]["all_zone"])
        zoneInfoList: List = cur.fetchall()
        for (zone, md5, zone_url, zone_update_time) in zoneInfoList:
            zone_update_time = int(time.time())
            # md5 hash check
            if not os.path.exists(_table_cache_path+zone+".txt"):
                self.__log(f"[zone.db]:{zone} cache not found!")
                continue
            _fileMD5 = ""
            _cacheText = ""
            if os.path.exists(_table_cache_path+zone+".txt"):
                with open(_table_cache_path+zone+".txt", "r") as f:
                    _cacheText = f.read()
                    _h = hashlib.md5()
                    _h.update(_cacheText.encode(encoding="utf-8"))
                    _fileMD5 = _h.hexdigest()
            if md5 != _fileMD5 or _fileMD5 == "":
                self.__log(f"[zone.db]:{zone} cache md5 error!")
                continue
            # loop item
            for lineText in _cacheText.split('\n'):
                # filter data
                rows = lineText.split("|")
                if len(rows) < 7:
                    continue
                (itemZone, itemCountry, itemType, itemAddress,
                 itemMask, itemUpdateTime, itemState) = tuple(rows[0:7])
                if itemType not in ['ipv6', 'ipv4', 'asn']:
                    continue
                if itemUpdateTime == '':
                    itemUpdateTime = '-1'
                if itemMask == '':
                    itemMask = '-1'
                # try renew flag
                cur.execute(self.__sql["nic_address_table"]["update_last_flag"], (zone_update_time,
                            itemZone, itemCountry, itemType, itemAddress, itemMask, itemUpdateTime, itemState))
                if cur.rowcount <= 0:
                    # insert item
                    self.__log(
                        f"insert item {(itemZone, itemCountry,itemType, itemAddress, itemMask, itemUpdateTime, itemState, zone_update_time)}")
                    cur.execute(self.__sql["nic_address_table"]["insert_address"], (itemZone, itemCountry,
                                itemType, itemAddress, itemMask, itemUpdateTime, itemState, zone_update_time))
                    cur.execute(self.__sql["nic_address_commit_info"]["inser_commit"], (itemZone, itemCountry,
                                itemType, itemAddress, itemMask, itemUpdateTime, itemState, int(time.time()), "append"))
            # remove old item
            cur.execute(self.__sql["nic_address_table"]
                        ["find_diff_flag"], (zone, zone_update_time))
            oldList = cur.fetchall()
            for oldItem in oldList:
                self.__log(f"remove old item {oldItem}")
                oldItemRows = list(oldItem)[0:7]
                oldItemRows.append(int(time.time()))
                oldItemRows.append("remove")
                __insertCommitData = tuple(oldItemRows)
                cur.execute(self.__sql["nic_address_commit_info"]
                            ["inser_commit"], __insertCommitData)
            cur.execute(self.__sql["nic_address_table"]
                        ["delete_old_data"], (zone, zone_update_time))
            self._db.commit()
        cur.close()
        pass

    def __init_db(self):
        __init_tables_sql = '''#######
CREATE TABLE IF NOT EXISTS `nic_address_commit_info`  (
  `zone` varchar(16) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
  `country` char(2) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
  `type` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
  `address` varchar(512) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
  `mask` int NULL DEFAULT NULL,
  `update_time` int NULL DEFAULT NULL,
  `state` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
  `action_time` int NULL DEFAULT NULL,
  `action` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
  INDEX `zone`(`zone`) USING BTREE,
  INDEX `zone_country`(`zone`, `country`) USING BTREE,
  INDEX `last_flag`(`action`) USING BTREE,
  INDEX `all`(`zone`, `country`, `type`, `address`, `mask`, `update_time`, `state`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = DYNAMIC;
#######
CREATE TABLE IF NOT EXISTS `nic_address_table`  (
  `zone` varchar(16) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
  `country` char(2) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
  `type` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
  `address` varchar(512) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
  `mask` int NULL DEFAULT NULL,
  `update_time` int NULL DEFAULT NULL,
  `state` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
  `last_flag` int NULL DEFAULT NULL,
  INDEX `zone`(`zone`) USING BTREE,
  INDEX `zone_country`(`zone`, `country`) USING BTREE,
  INDEX `last_flag`(`last_flag`) USING BTREE,
  INDEX `all`(`zone`, `country`, `type`, `address`, `mask`, `update_time`, `state`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = Dynamic;
#######
CREATE TABLE IF NOT EXISTS `nic_log`  (
  `zone` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
  `message` text CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL,
  `time` int NULL DEFAULT NULL
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = Dynamic;
#######
CREATE TABLE IF NOT EXISTS `nic_zone_info`  (
  `zone` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
  `md5` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
  `url` text CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL,
  `update_time` int NULL DEFAULT NULL
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = Dynamic;
        '''
        cur = self._db.cursor()
        for _sql in __init_tables_sql.split("#######"):
            if _sql != '':
                cur.execute(_sql)
        self.__sql = {
            "nic_zone_info": {
                "all_zone": 'SELECT * FROM nic_zone_info',
                "find_zone": 'SELECT COUNT(*) FROM nic_zone_info WHERE zone=%s;',
                "insert_zone": 'INSERT INTO nic_zone_info VALUES(%s, %s, %s, %s)',
                'update_zone': 'UPDATE nic_zone_info SET md5=%s,update_time=%s WHERE zone=%s'
            },
            "nic_address_table": {
                "update_last_flag": "UPDATE nic_address_table SET last_flag=%s WHERE zone=%s and country=%s and type=%s and address=%s and mask=%s and update_time=%s and state=%s",
                "insert_address": "INSERT INTO nic_address_table VALUES(%s, %s, %s, %s, %s, %s, %s, %s)",
                "find_diff_flag": 'SELECT * FROM nic_address_table WHERE zone=%s and last_flag!=%s',
                "delete_old_data": 'DELETE FROM nic_address_table  WHERE zone=%s and last_flag!=%s'
            },
            "nic_address_commit_info": {
                "inser_commit": "INSERT INTO nic_address_commit_info VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s)"
            }
        }

        for item in _nic_table_urls:
            cur.execute(self.__sql["nic_zone_info"]
                        ["find_zone"], (item['name']))
            (count,) = cur.fetchone()
            if count <= 0:
                cur.execute(self.__sql["nic_zone_info"]["insert_zone"],
                            (item['name'], "", item['url'], int(time.time())))
        self._db.commit()
        cur.close()

    def __log(self, message: str):
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]:{message}")

    def GET(self,country:Text,lasttime:int=0):
        print(country)
        pass


class NicWeb:
    def __init__(self) -> None:
        self._db = pymysql.connect(host=_db_host, user=_db_user, password=_db_passwd, db=_db_name)
        pass
    def GET(self,path)->None:
        args = web.input()
        if path=='ros':
            return self.__ros(args)
        pass
    def __ros(self,args):
        country:str = ""
        lastTime:str = ""
        _type:str = ""
        if "country" in args:
            country = args['country']
        else:
            return "country is empty!"
        if "lastTime" in  args:
            lastTime = args['lastTime']
        if "type" in args:
            _type = args['type']
        else:
            return "country is type!"
        _sql:str = ""
        _sqlArgs:List = list()
        cur = self._db.cursor()
        if lastTime=="":
            _sql = "SELECT zone,country,type,address,mask,update_time,state,'append' FROM nic_address_table WHERE state!='reserved'"
        else:
            _sql = "SELECT zone,country,type,address,mask,update_time,state,action FROM nic_address_commit_info WHERE state!='reserved' and action_time>%s"
            _sqlArgs.append(lastTime)
        
        if country !="":
            _sql += " and country=%s"
            _sqlArgs.append(country)
        
        if _type !="":
            _sql += " and type=%s"
            _sqlArgs.append(_type)
        cur.execute(_sql,tuple(_sqlArgs))
        data = cur.fetchall()
        cur.close()
        respond:str = str()
        if _type == 'ipv4':
            respond+="/ip firewall address-list\n"
            for (zone,itemCountry,type,address,mask,update_time,state,action) in data:
                if action=="append":
                    respond += f''':if ([/ip firewall address-list find address={address}/{32-int(math.log(mask,2))} list=nic.{itemCountry}]) do='''
                    respond += "{} else={"
                    respond += f"add address={address}/{32-int(math.log(mask,2))} disabled=no list=nic.{itemCountry}"+"}\n"
                    pass
                elif action=="remove":
                    respond += f''':if ([/ip firewall address-list find address={address}/{32-int(math.log(mask,2))} list=nic.{itemCountry}]) do='''
                    respond += "{"
                    respond += f"remove [/ip firewall address-list find address={address}/{32-int(math.log(mask,2))} list=nic.{itemCountry}]"
                    respond += "}\n"
                    pass
                pass
        if _type == 'ipv6':
            respond+="/ipv6 firewall address-list\n"
            for (zone,itemCountry,type,address,mask,update_time,state,action) in data:
                if action=="append":
                    respond += f"add address={address}/{mask} disabled=no list=nic.{itemCountry}\n"
                    pass
                elif action=="remove":
                    respond += f"remove [/ipv6 firewall address-list find address={address}/{mask} list=nic.{itemCountry}]\n"
                    pass
                pass
        respond += f"/file print file=nic_{_type}_{country}\n"
        respond += f":delay delay-time=2\n"
        respond += f"/file set nic_{_type}_{country} contents={int(time.time())}\n"
        respond += '\n'
        return respond


urls = (
  '/(.*)', 'NicWeb'
)


if __name__ == "__main__":
    if not os.path.exists(_table_cache_path):
        mkdir(_table_cache_path)
    nic = NICTableManage()
    app = web.application(urls, globals())
    app.run()
    input()
