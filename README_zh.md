[EN](README.md) | 中文
# 网络信息中心 WEB API 套件
让自己的路由器设备通过网络信息中心(NIC)获取各个地区国家的ASN,IPv4,IPv6等网络信息.并支持增量更新!
# 如何启用服务端
* 安装Python3,并通过pip3安装服务的所需的对应的扩展包 `pip3 install PyMySQL web.py`
* 修改 `nic.py` 中的关于Mysql数据库配置的代码
* 启动服务 `python3 ./nic.py`
# 路由器设备端
## RouterOS
* 支持IPv4,IPv6的信息导入
* 将 `nic_for_routeros.rsc` 黏贴到 `/system script` 中,修改脚本中的配置,关于服务器地址,所需要的国家,和地址类型
* 在 `/system schedule` 中添加对应的定时任务 `:execute script="你的脚本名"` 进行定时更新
